# Research: ADKAdapter Implementation

**Feature**: 008-adk-adapter  
**Date**: 2026-01-10  
**Status**: Complete

## Overview

This document captures research findings for implementing `ADKAdapter`, a concrete implementation of the `AsyncGEPAAdapter` protocol that bridges GEPA's evaluation patterns to Google ADK's agent/runner architecture.

---

## 1. Google ADK Architecture

### Decision: Use Runner with Event Loop Pattern
**Rationale**: ADK's `Runner` class is the primary orchestrator for agent execution. It manages the event loop, coordinates with services (SessionService), and yields events as the agent executes. This is the correct pattern for async evaluation.

**Alternatives Considered**:
- Direct `agent.run_async()` call: Not recommended. The Runner handles session management, event processing, and state commitment.
- Synchronous `runner.run()`: Blocked async event loop. ADK is fundamentally async-first.

### Key ADK Components

| Component | Module | Purpose |
|-----------|--------|---------|
| `LlmAgent` | `google.adk.agents` | The agent being evaluated (accepts `instruction` parameter) |
| `Runner` | `google.adk.runners` | Orchestrates agent execution, yields Events |
| `InMemorySessionService` | `google.adk.sessions` | Manages session state in memory |
| `Event` | `google.adk.events` | Container for agent outputs, tool calls, state deltas |
| `Content` | `google.genai.types` | Wraps user/agent message content |

### Runner.run_async() Pattern

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Setup
session_service = InMemorySessionService()
session = await session_service.create_session(
    app_name="eval", user_id="eval_user", session_id="unique_id"
)
runner = Runner(agent=agent, app_name="eval", session_service=session_service)

# Execute
content = types.Content(role='user', parts=[types.Part(text=input_text)])
async for event in runner.run_async(
    user_id="eval_user", session_id="unique_id", new_message=content
):
    if event.is_final_response() and event.content:
        output = event.content.parts[0].text
```

---

## 2. Instruction Override Strategy

### Decision: Temporarily Modify agent.instruction Attribute
**Rationale**: The `LlmAgent.instruction` attribute is a string that can be modified at runtime. We save the original, apply the candidate's instruction, execute, then restore.

**Pattern**:
```python
original_instruction = agent.instruction
try:
    if "instruction" in candidate.components:
        agent.instruction = candidate.components["instruction"]
    # Execute evaluation
finally:
    agent.instruction = original_instruction
```

**Alternatives Considered**:
- Clone the agent: More memory overhead, complex lifecycle
- Create new agent per evaluation: Expensive, loses tool configuration
- Use instruction templates with `{var}` syntax: Doesn't work for full instruction replacement

---

## 3. Session Isolation Strategy

### Decision: Create Fresh Session Per Batch Example
**Rationale**: Each batch example must start with clean state to prevent cross-contamination. Creating a new session (with unique session_id) per example ensures isolation.

**Pattern**:
```python
import uuid

for i, example in enumerate(batch):
    session_id = f"eval_{uuid.uuid4()}"
    session = await session_service.create_session(
        app_name="gepa_eval",
        user_id="eval_user",
        session_id=session_id,
    )
    # Execute with this isolated session
    # Delete session after (optional cleanup)
```

**Alternatives Considered**:
- Reuse session with state reset: ADK doesn't provide a clean state reset API
- Single session for batch: State bleeds between examples, corrupting evaluation

---

## 4. Trace Capture Strategy

### Decision: Collect Events with Tool Calls and State Deltas
**Rationale**: When `capture_traces=True`, we collect all events yielded by the runner, extracting:
- Tool calls from `event.content.parts` containing `function_call`
- Tool results from `event.content.parts` containing `function_response`
- State changes from `event.actions.state_delta`
- Token usage from model response metadata (if available)

**Trajectory Structure**:
```python
@dataclass
class ADKTrajectory:
    tool_calls: list[dict]      # {name, args, result}
    state_deltas: list[dict]    # Accumulated state changes
    token_usage: dict | None    # {input_tokens, output_tokens}
    events: list[dict]          # Raw event summaries
```

**Alternatives Considered**:
- Only capture final response: Loses tool call visibility
- Capture raw Event objects: Not serializable, too much internal detail

---

## 5. Scoring Integration

### Decision: Use Scorer Protocol with async_score Method
**Rationale**: The `Scorer` protocol (from gepa_adk.ports.scorer) provides both sync and async scoring methods. We use `async_score()` to maintain async flow.

**Pattern**:
```python
score, metadata = await self.scorer.async_score(
    input_text=example["input"],
    output=output_text,
    expected=example.get("expected"),
)
```

**Alternatives Considered**:
- Sync scoring with to_thread: Adds complexity, breaks async flow
- Multiple scorer support: Scope creep, single scorer sufficient for MVP

---

## 6. Error Handling Strategy

### Decision: Graceful Degradation with Score of 0.0
**Rationale**: Agent execution failures should not abort the entire batch. Instead, capture the error, assign a score of 0.0, and include error details in metadata for debugging.

**Pattern**:
```python
try:
    output = await self._execute_agent(example)
    score, metadata = await self.scorer.async_score(...)
except Exception as e:
    output = ""
    score = 0.0
    metadata = {"error": str(e), "error_type": type(e).__name__}
    logger.warning("Agent execution failed", error=str(e), example_idx=i)
```

**Alternatives Considered**:
- Raise exception on failure: One bad example kills entire evaluation
- Skip failed examples: Misaligns output/score list lengths with batch

---

## 7. Reflective Dataset Format

### Decision: Follow GEPA's Expected Format
**Rationale**: The `make_reflective_dataset()` method must return a mapping compatible with GEPA's proposer. Based on the AsyncGEPAAdapter protocol and GEPA patterns:

**Format**:
```python
{
    "instruction": [
        {
            "Inputs": {"example_input": "..."},
            "Generated Outputs": "agent output text",
            "Feedback": "score: 0.85, metadata: {...}",
        },
        # More examples...
    ]
}
```

**Alternatives Considered**:
- Custom format: Would break GEPA compatibility
- Include trajectories in dataset: Scope creep, not needed for basic reflection

---

## 8. Dependencies Verification

### Existing Dependencies (from pyproject.toml)
- `google-adk>=1.22.0` ✅ Already installed
- `structlog>=25.5.0` ✅ Already installed

### ADK Import Verification
```python
# All needed imports verified available
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
```

### No New Dependencies Required
The ADK provides all necessary components. No additional packages needed.

---

## 9. Testing Strategy

### Contract Tests (tests/contracts/test_adk_adapter_contracts.py)
- Protocol compliance with `AsyncGEPAAdapter`
- Method signatures match protocol
- Return types are correct

### Unit Tests (tests/unit/adapters/test_adk_adapter.py)
- Mock ADK components (`LlmAgent`, `Runner`, `SessionService`)
- Test instruction override logic
- Test error handling
- Test trajectory capture
- Test reflective dataset generation

### Integration Tests (tests/integration/test_adk_adapter_integration.py)
- Real ADK agent execution (marked `@pytest.mark.slow`, `@pytest.mark.api`)
- Requires Gemini API key
- Verifies end-to-end flow

---

## 10. Open Questions Resolved

| Question | Resolution |
|----------|------------|
| How to override instruction? | Direct attribute modification with try/finally restore |
| Session isolation? | Fresh session per batch example |
| Trace format? | Custom ADKTrajectory dataclass |
| Error handling? | Graceful degradation, score=0.0 |
| Dataset format? | GEPA-compatible mapping structure |

---

## References

- [ADK Runtime Documentation](https://google.github.io/adk-docs/runtime/)
- [LlmAgent Documentation](https://google.github.io/adk-docs/agents/llm-agents/)
- [Sessions Documentation](https://google.github.io/adk-docs/sessions/session/)
- `gepa_adk.ports.adapter` - AsyncGEPAAdapter protocol
- `gepa_adk.ports.scorer` - Scorer protocol

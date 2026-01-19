# Research: Unified Agent Executor

**Feature**: 124-unified-agent-executor
**Date**: 2026-01-19
**Status**: Complete

## Executive Summary

This research consolidates findings from three areas:
1. Google ADK Runner API capabilities
2. agent-workflow-suite patterns (inspiration, not parity)
3. Current gepa-adk execution paths and DRY violations

**Key Finding**: ~18-19% of current code is duplicated across three agent execution paths. A unified AgentExecutor can eliminate ~130+ lines of duplication while enabling feature parity.

---

## 1. ADK Runner API Analysis

### Decision: Use Runner.run_async() as Core Execution Engine

**Rationale**: The ADK Runner provides a complete, well-tested execution framework with:
- Async event streaming via `AsyncGenerator[Event, None]`
- Session lifecycle management (create, retrieve, append events)
- State management with scoped keys (app:, user:, session-level)
- Plugin architecture for extensibility
- Invocation context for execution state

**Alternatives Considered**:
- Direct LlmAgent.run_async() - Bypasses session management
- Custom execution loop - Reinvents the wheel, loses ADK improvements

### Key API Patterns

**Runner Initialization**:
```python
runner = Runner(
    agent=agent,
    app_name="gepa_adk",
    session_service=session_service,  # Required
)
```

**Execution Loop**:
```python
async for event in runner.run_async(
    user_id=user_id,
    session_id=session_id,
    new_message=Content(role="user", parts=[Part(text=input_text)]),
    state_delta=state_delta,  # Optional initial state
    run_config=run_config,    # Optional runtime config
):
    captured_events.append(event)
```

**Session State Injection**: ADK supports `{key}` template substitution from session.state in agent instructions, enabling stateful reflection.

---

## 2. agent-workflow-suite Inspirational Patterns

### Pattern: ExecutionResult Dataclass

**Decision**: Adopt a simplified ExecutionResult pattern

**Rationale**: Provides consistent return type across all agent executions with:
- Status enum (SUCCESS/FAILED/TIMEOUT)
- Extracted output value
- Captured events for debugging
- Execution timing metadata

**Simplified for gepa-adk**:
```python
@dataclass
class ExecutionResult:
    status: ExecutionStatus
    session_id: str
    extracted_value: str | None = None
    error_message: str | None = None
    execution_time_seconds: float = 0.0
    captured_events: list[Any] | None = None
```

**Note**: We omit `output_id`, `output_ids`, `adk_invocation_id` as gepa-adk doesn't persist outputs to a database.

### Pattern: Parameter Object for Execution

**Decision**: Consider ExecutionContext-style parameter grouping for future API evolution

**Rationale**: agent-workflow-suite uses `ExecutionContext` to bundle 12+ parameters. For now, gepa-adk can use keyword arguments, but the pattern is available if API complexity grows.

**Alternatives Considered**:
- Full ExecutionContext DTO - Over-engineering for current needs
- Multiple method overloads - Poor discoverability

### Pattern: Timeout as Status (Not Exception)

**Decision**: Return TIMEOUT status instead of raising TimeoutError

**Rationale**:
- Allows caller to handle timeouts gracefully
- Consistent with other status values
- Captured events still available even on timeout

---

## 3. Current gepa-adk DRY Violations

### Violation Analysis

| Component | ADKAdapter | CriticScorer | Reflection | Unified |
|-----------|-----------|-------------|-----------|---------|
| Runner instantiation | Lines 735-738 | Lines 522-527 | Lines 312-317 | **Single location** |
| Session creation | Lines 748-752 | Lines 494-520 | Lines 305-310 | **SessionManager** |
| Event collection loop | Lines 759-769 | Lines 533-538 | Lines 337-345 | **Single loop** |
| Output extraction | extract_final_output | extract_final_output | extract_output_from_state | **Unified extractor** |
| Tool call extraction | Lines 459-532 | N/A | N/A | **Move to utils** |
| State delta extraction | Lines 534-559 | N/A | N/A | **Move to utils** |
| Token usage extraction | Lines 561-585 | N/A | N/A | **Move to utils** |

**Total Duplicated Code**: ~400 lines across 2,135 lines (18-19%)

### Decision: Extract to AgentExecutor Protocol + Adapter

**Rationale**:
- Single execution path for all agent types
- Features added once benefit all agents
- Consistent error handling and event capture
- Easier testing (mock one component)

**Implementation Approach**:
1. Define `AgentExecutorProtocol` in ports layer (no external imports)
2. Implement `AgentExecutor` adapter with Runner integration
3. Migrate ADKAdapter, CriticScorer, and reflection to use AgentExecutor
4. Deprecate direct Runner usage in feature code

---

## 4. Technical Decisions Summary

### Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Execution interface | Protocol-based (AgentExecutorProtocol) | Hexagonal architecture compliance |
| Result type | ExecutionResult dataclass | Consistent, type-safe returns |
| Timeout handling | Status enum, not exception | Graceful handling, events preserved |
| Session management | Optional reuse via session_id | Supports critic accessing generator state |
| State injection | Use ADK's native template substitution | Already supported, no custom parsing |
| Event capture | Always capture, optionally return | Debugging and trajectory support |

### What NOT to Copy from agent-workflow-suite

| Feature | Reason to Skip |
|---------|---------------|
| Database persistence | gepa-adk is in-memory only |
| WorkflowEventHandler | gepa-adk doesn't support workflow agents yet |
| ExecutionContext DTO | Over-engineering for current API |
| Error enhancement factory | Provider-specific messages not needed now |
| OpenTelemetry integration | Out of scope for this feature |

---

## 5. Implementation Scope

### In Scope (This Feature)

1. **AgentExecutorProtocol** in `src/gepa_adk/ports/agent_executor.py`
   - `execute_agent()` method signature
   - ExecutionStatus enum
   - ExecutionResult dataclass

2. **AgentExecutor** adapter in `src/gepa_adk/adapters/agent_executor.py`
   - Runner integration
   - Session management (create/reuse)
   - Event capture
   - Output extraction (state-based + event fallback)
   - Timeout handling
   - Instruction/schema override support

3. **Migration** of existing code:
   - ADKAdapter → use AgentExecutor for generator evaluation
   - CriticScorer → use AgentExecutor for critic evaluation
   - adk_reflection.py → use AgentExecutor for reflection

4. **Backward Compatibility**:
   - Existing `evolve()` and `evolve_sync()` API unchanged
   - Internal implementation detail, not public API change

### Out of Scope

- Workflow agent support (SequentialAgent, ParallelAgent, LoopAgent)
- Database persistence of execution results
- OpenTelemetry tracing
- Provider-specific error enhancement
- Tool validation callbacks (deferred to #133)
- Lifecycle callbacks (deferred to #134)

---

## 6. Risk Assessment

### Low Risk (Proceed)
- Extracting Runner pattern - Straightforward, well-understood
- ExecutionResult dataclass - Simple data structure
- Session reuse parameter - Already in CriticScorer

### Medium Risk (Careful Implementation)
- Output extraction unification - Different strategies exist (event vs state)
- Instruction override mechanics - Must preserve original agent

### Mitigations
- Comprehensive unit tests for each extraction path
- Integration tests verifying all three agent types
- Backward compatibility tests for existing evolution API

---

## 7. File Changes Summary

| File | Action | Purpose |
|------|--------|---------|
| `src/gepa_adk/ports/agent_executor.py` | Create | Protocol + types |
| `src/gepa_adk/adapters/agent_executor.py` | Create | Implementation |
| `src/gepa_adk/adapters/adk_adapter.py` | Modify | Use AgentExecutor |
| `src/gepa_adk/adapters/critic_scorer.py` | Modify | Use AgentExecutor |
| `src/gepa_adk/engine/adk_reflection.py` | Modify | Use AgentExecutor |
| `src/gepa_adk/utils/events.py` | Modify | Consolidate extraction |
| `tests/unit/ports/test_agent_executor_protocol.py` | Create | Protocol tests |
| `tests/unit/adapters/test_agent_executor.py` | Create | Adapter tests |
| `tests/integration/test_unified_execution.py` | Create | Feature parity tests |

---

## 8. Dependencies

### Existing Dependencies (No Changes)
- google-adk >= 1.22.0 (Runner, Session, Event types)
- structlog (logging)
- Standard library (dataclasses, enum, typing)

### New Dependencies
- None required

---

## References

- [Google ADK Runner Source](.venv/Lib/site-packages/google/adk/runners.py)
- [Google ADK Sessions](.venv/Lib/site-packages/google/adk/sessions/)
- [agent-workflow-suite AgentExecutor](C:/Users/alber/source/repos/agent-workflow-suite/src/agent_workflow_suite/adapters/services/agent_executor.py)
- [gepa-adk Comparison Doc](docs/architecture/unified-agent-execution-comparison.md)

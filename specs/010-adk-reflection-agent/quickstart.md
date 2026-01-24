# Quickstart: ADK-First Reflection Agent Support

**Feature**: 010-adk-reflection-agent
**Date**: 2026-01-10

## Prerequisites

- Python 3.12+
- gepa-adk installed with dependencies (`google-adk>=1.22.0`)
- Valid Gemini API key (for ADK agent)

## Quick Example

### 1. Create a Reflection Agent

```python
from google.adk.agents import LlmAgent

# Define reflection agent with state injection placeholders
reflection_agent = LlmAgent(
    name="InstructionReflector",
    model="gemini-2.5-flash",
    instruction="""You are an expert at improving AI agent instructions.

Current Instruction:
{current_instruction}

Execution Feedback:
{execution_feedback}

Based on this feedback, propose an improved instruction that:
1. Addresses issues identified in negative feedback
2. Preserves elements that worked well
3. Maintains clarity and specificity

Return ONLY the improved instruction text, with no additional commentary."""
)
```

### 2. Create Reflection Function and Proposer

```python
from gepa_adk.engine.proposer import (
    AsyncReflectiveMutationProposer,
    create_adk_reflection_fn,
)

# Create the ADK reflection function
adk_reflection_fn = create_adk_reflection_fn(reflection_agent)

# Create proposer with ADK reflection
proposer = AsyncReflectiveMutationProposer(
    adk_reflection_fn=adk_reflection_fn,
)
```

### 3. Use in Evolution Loop

```python
import asyncio

async def main():
    # Current candidate instruction
    candidate = {"instruction": "Be helpful and concise"}

    # Reflective dataset from evaluation
    reflective_dataset = {
        "instruction": [
            {
                "Inputs": {"instruction": "Be helpful and concise"},
                "Generated Outputs": "Here's the answer...",
                "Feedback": "score: 0.65, tool_calls: 0"
            },
            {
                "Inputs": {"instruction": "Be helpful and concise"},
                "Generated Outputs": "I can help with that...",
                "Feedback": "score: 0.80, tool_calls: 1"
            }
        ]
    }

    # Generate improved instruction via ADK agent
    result = await proposer.propose(
        candidate=candidate,
        reflective_dataset=reflective_dataset,
        components_to_update=["instruction"],
    )

    if result:
        print(f"Improved instruction: {result['instruction']}")

asyncio.run(main())
```

## Custom Session Service

For production deployments, inject a persistent session service:

```python
from google.adk.sessions import DatabaseSessionService

# Use database-backed sessions
db_session_service = DatabaseSessionService(
    db_url="sqlite+aiosqlite:///reflection_sessions.db"
)

adk_reflection_fn = create_adk_reflection_fn(
    reflection_agent=reflection_agent,
    session_service=db_session_service,
)
```

## Fallback to LiteLLM

To use LiteLLM instead of ADK (backwards compatible):

```python
# Simply omit adk_reflection_fn - defaults to None
proposer = AsyncReflectiveMutationProposer(
    model="gemini/gemini-2.5-flash",
    temperature=0.7,
)
# This uses litellm.acompletion() as before
```

## Integration with AsyncGEPAEngine

```python
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.adapters import ADKAdapter

# Setup adapter and proposer with ADK reflection
adapter = ADKAdapter(agent=my_agent, scorer=my_scorer)
proposer = AsyncReflectiveMutationProposer(
    adk_reflection_fn=create_adk_reflection_fn(reflection_agent)
)

# Create engine with ADK-powered evolution
engine = AsyncGEPAEngine(
    adapter=adapter,
    proposer=proposer,
)

# Run evolution
result = await engine.evolve(
    initial_candidate={"instruction": "Be helpful"},
    evaluation_batch=batch,
    max_iterations=10,
)
```

## Observability

ADK reflection provides full observability via ADK's built-in tracing:

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

# Reflection operations emit structured logs:
# {"event": "reflection.start", "instruction_length": 42, ...}
# {"event": "reflection.complete", "duration_ms": 1234, ...}
```

## Troubleshooting

### Empty Response from Reflection

If the reflection agent returns empty, the proposer falls back to the original instruction:

```python
# This is automatic - no action needed
# Check logs for: "reflection.fallback_to_original"
```

### API Key Issues

Ensure `GOOGLE_API_KEY` environment variable is set:

```bash
export GOOGLE_API_KEY="your-api-key"
```

### Session Creation Errors

If you see "Session not found" errors, ensure async/await is used correctly:

```python
# Correct - await the session service methods
session = await session_service.create_session(...)

# Wrong - missing await causes errors
session = session_service.create_session(...)  # Coroutine not awaited!
```

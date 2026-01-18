# Contract: Session State Management

**Feature**: 122-adk-session-state
**Date**: 2026-01-18

## Overview

Defines the contract for session state usage in reflection operations, including required keys, types, and lifecycle management.

## State Keys Contract

### Required Input Keys

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `component_text` | `str` | Yes | Component text being evolved |
| `trials` | `str` | Yes | JSON-serialized trial records |

### Output Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `proposed_instruction` | `str` | Default output_key | Agent's proposed improvement |

## Session Lifecycle Contract

### Creation Phase

```python
# Contract: Session must be created with initial state
session = await session_service.create_session(
    app_name="gepa_reflection",     # Required: application identifier
    user_id="reflection",            # Required: user identifier
    session_id=unique_id,            # Required: unique session ID
    state={                          # Required: initial state
        "component_text": str,       # Non-empty string
        "trials": str,               # Valid JSON string
    },
)
```

### Execution Phase

```python
# Contract: Agent instruction contains template placeholders
agent.instruction = """
Improve this: {component_text}
Based on: {trials}
"""

# ADK automatically:
# 1. Calls inject_session_state() to substitute {key} placeholders
# 2. Stores agent output to session.state[output_key] on final response
```

### Retrieval Phase

```python
# Contract: Retrieve output from session state
session = await session_service.get_session(
    app_name="gepa_reflection",
    user_id="reflection",
    session_id=session_id,
)

# Output available at session.state[output_key]
if session and output_key in session.state:
    output = str(session.state[output_key])
```

## Template Substitution Contract

### Syntax Rules

| Syntax | Behavior | Example |
|--------|----------|---------|
| `{key}` | Required - raises KeyError if missing | `{component_text}` |
| `{key?}` | Optional - returns empty string if missing | `{optional_context?}` |
| `{artifact.name}` | Load from artifact service | `{artifact.config.json}` |

### Validation Rules

1. Key names must be valid Python identifiers
2. Keys must exist in session.state unless marked optional
3. Values are converted to string via `str()`
4. `None` values become empty string

## Error Handling Contract

### Session Creation Errors

| Error | Cause | Handling |
|-------|-------|----------|
| `ValueError` | Invalid session parameters | Propagate to caller |
| `RuntimeError` | Session service unavailable | Propagate to caller |

### Template Substitution Errors

| Error | Cause | Handling |
|-------|-------|----------|
| `KeyError` | Required key missing from state | Propagate (ADK behavior) |
| Silent empty | Optional key missing (`{key?}`) | Return empty string |

### Output Retrieval Errors

| Scenario | Handling |
|----------|----------|
| Session not found | Fallback to event extraction |
| output_key not in state | Fallback to event extraction |
| State value is None | Return empty string |

## Test Contract

### Session Creation Test

```python
@pytest.mark.asyncio
async def test_session_creation_contract():
    """Session must be created with required state keys."""
    from google.adk.sessions import InMemorySessionService

    service = InMemorySessionService()

    session = await service.create_session(
        app_name="gepa_reflection",
        user_id="reflection",
        session_id="test_123",
        state={
            "component_text": "Be helpful",
            "trials": '[{"input": "hi", "output": "hello", "feedback": {"score": 0.5}}]',
        },
    )

    assert session.id == "test_123"
    assert "component_text" in session.state
    assert "trials" in session.state
```

### State Retrieval Test

```python
@pytest.mark.asyncio
async def test_state_retrieval_contract():
    """Output must be retrievable from session.state[output_key]."""
    from google.adk.sessions import InMemorySessionService

    service = InMemorySessionService()

    # Create session
    session = await service.create_session(
        app_name="gepa_reflection",
        user_id="reflection",
        session_id="test_456",
        state={"component_text": "text", "trials": "[]"},
    )

    # Simulate ADK storing output
    session.state["proposed_instruction"] = "Improved text"

    # Retrieve session
    retrieved = await service.get_session(
        app_name="gepa_reflection",
        user_id="reflection",
        session_id="test_456",
    )

    assert retrieved is not None
    assert retrieved.state["proposed_instruction"] == "Improved text"
```

## Compatibility Notes

### ADK Version Requirements

- Minimum: google-adk >= 1.22.0
- Required features: `LlmAgent.output_key`, `inject_session_state()`

### Existing Code Compatibility

| Component | Compatibility |
|-----------|---------------|
| `AsyncReflectiveMutationProposer` | Unchanged interface |
| `create_adk_reflection_fn` | Extended with output_key parameter |
| `extract_final_output` | Used as fallback |

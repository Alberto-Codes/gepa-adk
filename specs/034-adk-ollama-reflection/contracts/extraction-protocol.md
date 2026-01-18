# Contract: ADK Reflection Function

**Date**: 2026-01-17
**Feature**: 034-adk-ollama-reflection
**Status**: Implemented

## Purpose

Defines the contract for `create_adk_reflection_fn()` and the reflection function it produces.

## ReflectionFn Protocol

```python
ReflectionFn = Callable[[str, list[dict[str, Any]]], Awaitable[str]]
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `component_text` | `str` | Current text to improve |
| `trials` | `list[dict]` | Performance records with feedback and trajectory |

### Return Value

| Type | Description |
|------|-------------|
| `str` | Proposed improved text |

## create_adk_reflection_fn() Contract

### Signature

```python
def create_adk_reflection_fn(
    reflection_agent: Any,  # LlmAgent
    session_service: Any | None = None,  # BaseSessionService
) -> ReflectionFn:
```

### Behavior

1. **Session Creation**: Creates a new session per invocation for isolation
2. **Data Passing**: Sends component_text and trials in user message
3. **Event Extraction**: Uses `extract_final_output()` for response extraction
4. **Error Handling**: Logs errors and propagates exceptions

## Trial Structure Contract

Each trial MUST contain:

```python
{
    "feedback": {
        "score": float,         # Required: 0.0-1.0
        "feedback_text": str,   # Required
        # Optional fields:
        "feedback_guidance": str | None,
        "feedback_dimensions": dict | None,
    },
    "trajectory": {
        "input": str,           # Required
        "output": str,          # Required
        # Optional:
        "trace": {
            "tool_calls": int,
            "tokens": int,
            "error": str | None,
        } | None,
    },
}
```

## Test Cases

### TC-001: Basic Reflection

**Given**: Reflection agent and valid trials
**When**: `reflect(component_text, trials)` is called
**Then**: Returns proposed text string

### TC-002: Empty Response Handling

**Given**: Reflection agent returns empty response
**When**: `reflect()` is called
**Then**: Returns empty string, logs warning

### TC-003: Session Isolation

**Given**: Multiple concurrent reflection calls
**When**: Each creates its own session
**Then**: Sessions are isolated (unique session_id per call)

### TC-004: Error Propagation

**Given**: Reflection agent throws exception
**When**: `reflect()` is called
**Then**: Exception is logged and propagated

## Logging Contract

The reflection function MUST log:

```python
# On start
logger.info(
    "reflection.start",
    session_id=str,
    component_text_length=int,
    trial_count=int,
)

# On complete
logger.info(
    "reflection.complete",
    session_id=str,
    response_length=int,
)

# On empty response
logger.warning(
    "reflection.empty_response",
    session_id=str,
)

# On error
logger.error(
    "reflection.error",
    session_id=str,
    error=str,
    error_type=str,
)
```

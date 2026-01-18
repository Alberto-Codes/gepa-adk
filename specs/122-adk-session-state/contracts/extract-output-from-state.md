# Contract: extract_output_from_state Utility

**Feature**: 122-adk-session-state
**Date**: 2026-01-18

## Overview

The `extract_output_from_state()` function is a shared utility for extracting agent output from ADK session state using the `output_key` mechanism. It complements the existing `extract_final_output()` function.

## Function Signature

```python
def extract_output_from_state(
    session_state: dict[str, Any],
    output_key: str | None,
) -> str | None:
    """Extract output from session state using output_key.

    Args:
        session_state: ADK session state dictionary.
        output_key: Key where agent stored its output, or None.

    Returns:
        Output string if found in state, None otherwise.
        Caller should implement fallback logic when None is returned.
    """
```

## Contract Requirements

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_state` | `dict[str, Any]` | Yes | Session state dictionary from ADK |
| `output_key` | `str \| None` | Yes | State key for output, or None if not configured |

### Return Value

| Condition | Return Value |
|-----------|--------------|
| `output_key` is `None` | `None` |
| `output_key` not in `session_state` | `None` |
| `session_state[output_key]` is `None` | `None` |
| `session_state[output_key]` exists | `str(value)` |

### Behavioral Contract

**Pre-conditions**:
1. `session_state` is a valid dictionary (may be empty)
2. `output_key` is either a string or None

**Post-conditions**:
1. Returns `str` if output found, `None` otherwise
2. Does NOT raise exceptions for missing keys
3. Does NOT modify `session_state`
4. Converts non-string values to string via `str()`

**Invariants**:
- Function is pure (no side effects)
- Function is synchronous (not async)
- Function never raises KeyError

## Implementation

```python
from typing import Any

def extract_output_from_state(
    session_state: dict[str, Any],
    output_key: str | None,
) -> str | None:
    """Extract output from session state using output_key.

    Args:
        session_state: ADK session state dictionary.
        output_key: Key where agent stored its output, or None.

    Returns:
        Output string if found in state, None otherwise.
        Caller should implement fallback logic when None is returned.

    Examples:
        Basic extraction:

        ```python
        state = {"proposed_instruction": "Be helpful and concise"}
        result = extract_output_from_state(state, "proposed_instruction")
        # result == "Be helpful and concise"
        ```

        Missing key returns None:

        ```python
        state = {"other_key": "value"}
        result = extract_output_from_state(state, "proposed_instruction")
        # result is None
        ```

        None output_key returns None:

        ```python
        state = {"proposed_instruction": "text"}
        result = extract_output_from_state(state, None)
        # result is None
        ```

    Note:
        This function is designed for use with ADK's output_key mechanism.
        Callers should implement fallback logic (e.g., extract_final_output)
        when this function returns None.
    """
    if not output_key:
        return None
    if output_key in session_state:
        value = session_state[output_key]
        if value is not None:
            return str(value)
    return None
```

## Usage Pattern

### With Fallback

```python
from gepa_adk.utils.events import extract_output_from_state, extract_final_output

# Primary: try state extraction
output = extract_output_from_state(session.state, output_key)

# Fallback: use event extraction
if output is None:
    output = extract_final_output(events)
```

### In multi_agent.py (Refactored)

```python
def _extract_primary_output(
    self, pipeline_output: str, session_state: dict[str, Any], primary_agent: LlmAgent
) -> str:
    output_key = getattr(primary_agent, "output_key", None)
    result = extract_output_from_state(session_state, output_key)
    if result is not None:
        return result
    return pipeline_output  # Fallback
```

### In adk_reflection.py

```python
# After agent execution
session = await session_service.get_session(...)

output = None
if session:
    output = extract_output_from_state(session.state, output_key)

if output is None:
    output = extract_final_output(events)
```

## Test Contract

```python
import pytest
from typing import Any

def test_extract_output_from_state_found():
    """Returns string when output_key exists in state."""
    state = {"proposed_instruction": "Be helpful"}
    result = extract_output_from_state(state, "proposed_instruction")
    assert result == "Be helpful"

def test_extract_output_from_state_missing_key():
    """Returns None when output_key not in state."""
    state = {"other_key": "value"}
    result = extract_output_from_state(state, "proposed_instruction")
    assert result is None

def test_extract_output_from_state_none_output_key():
    """Returns None when output_key is None."""
    state = {"proposed_instruction": "text"}
    result = extract_output_from_state(state, None)
    assert result is None

def test_extract_output_from_state_none_value():
    """Returns None when state value is None."""
    state = {"proposed_instruction": None}
    result = extract_output_from_state(state, "proposed_instruction")
    assert result is None

def test_extract_output_from_state_empty_state():
    """Returns None for empty state dict."""
    state: dict[str, Any] = {}
    result = extract_output_from_state(state, "proposed_instruction")
    assert result is None

def test_extract_output_from_state_converts_to_string():
    """Converts non-string values to string."""
    state = {"count": 42}
    result = extract_output_from_state(state, "count")
    assert result == "42"
    assert isinstance(result, str)
```

## Compliance Notes

### Hexagonal Architecture

- Located in `utils/` layer (accessible from both adapters/ and engine/)
- Does NOT import from adapters/ or engine/
- Only imports from stdlib (`typing`)

### DRY Principle

- Single implementation shared by:
  - `adapters/multi_agent.py`
  - `engine/adk_reflection.py`
- Eliminates duplicate extraction logic

### Separation of Concerns

- Pure extraction logic, no business logic
- Caller handles fallback strategy
- No coupling to specific use cases

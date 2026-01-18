# Contract: ReflectionFn Protocol

**Feature**: 122-adk-session-state
**Date**: 2026-01-18

## Overview

The `ReflectionFn` protocol defines the interface for reflection functions that generate improved component text based on trials. This contract remains **unchanged** by the session state feature.

## Protocol Definition

```python
from collections.abc import Awaitable, Callable
from typing import Any

ReflectionFn = Callable[[str, list[dict[str, Any]]], Awaitable[str]]
"""Async callable: (component_text: str, trials: list[dict]) -> str.

Takes current component text and trials, returns proposed component text.
"""
```

## Contract Requirements

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `component_text` | `str` | Yes | The current text content of the component being evolved |
| `trials` | `list[dict[str, Any]]` | Yes | List of trial records containing performance data |

### Trial Record Structure

```python
trial: dict[str, Any] = {
    "input": str,        # Required: Input given to the system
    "output": str,       # Required: Output produced by the system
    "feedback": {        # Required: Critic evaluation
        "score": float,           # Required: Numeric score
        "feedback_text": str,     # Optional: Human-readable feedback
        "feedback_guidance": str, # Optional: Improvement guidance
        "feedback_dimensions": dict, # Optional: Multi-dimensional scores
    },
    "trajectory": dict,  # Optional: Execution trace
}
```

### Output Requirements

| Requirement | Description |
|-------------|-------------|
| Return type | `str` |
| Non-empty | Must return non-empty string on success |
| Stripped | Should not have leading/trailing whitespace |
| Exception on failure | May raise `EvolutionError` on failure |

## Behavioral Contract

### Pre-conditions

1. `component_text` is a non-empty string
2. `trials` is a list (may be empty)
3. Each trial in `trials` has at least `input`, `output`, and `feedback` keys

### Post-conditions

1. Returns a string representing the proposed improved component text
2. If input trials are empty, implementation MAY return original text unchanged
3. If LLM/agent call fails, raises `EvolutionError`

### Invariants

- Function is async (returns `Awaitable[str]`)
- Function does not modify input parameters
- Function is stateless between calls

## Implementation Compliance

### create_adk_reflection_fn Compliance

The factory function `create_adk_reflection_fn()` returns a `ReflectionFn`-compliant callable:

```python
async def reflect(
    component_text: str,
    trials: list[dict[str, Any]],
) -> str:
    """Implements ReflectionFn protocol using ADK session state."""
    # 1. Create session with state
    # 2. Run agent (ADK handles template substitution)
    # 3. Retrieve output from session.state[output_key]
    # 4. Return proposed component text
```

### Contract Verification Points

| Check | Location | Description |
|-------|----------|-------------|
| Signature | Function definition | Matches `Callable[[str, list[dict]], Awaitable[str]]` |
| Return type | Function return | Returns `str` |
| Non-empty return | Validation | Raises `EvolutionError` if empty |
| Async behavior | Awaitable | Returns coroutine |

## Test Contract

```python
import pytest
from typing import Any, Callable, Awaitable

# Protocol signature test
def test_reflection_fn_signature():
    """ReflectionFn must accept (str, list[dict]) and return Awaitable[str]."""
    from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

    # Create reflection function
    reflection_fn = create_adk_reflection_fn(mock_agent)

    # Verify callable
    assert callable(reflection_fn)

    # Verify async
    result = reflection_fn("text", [])
    assert hasattr(result, "__await__")

# Contract compliance test
@pytest.mark.asyncio
async def test_reflection_fn_contract():
    """ReflectionFn must return non-empty string for valid input."""
    from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

    reflection_fn = create_adk_reflection_fn(mock_agent)

    result = await reflection_fn(
        "Original instruction",
        [{"input": "hi", "output": "hello", "feedback": {"score": 0.5}}]
    )

    assert isinstance(result, str)
    assert len(result.strip()) > 0
```

## Backward Compatibility

This contract is **unchanged** from the existing implementation. The session state feature only changes the internal implementation, not the external interface.

| Aspect | Before | After |
|--------|--------|-------|
| Signature | `(str, list[dict]) -> Awaitable[str]` | Same |
| Input handling | Session state injection | Same |
| Output retrieval | Event extraction | State extraction (with fallback) |
| Error handling | EvolutionError | Same |

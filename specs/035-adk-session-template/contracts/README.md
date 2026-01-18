# Contracts: ADK Session State Template Substitution

**Branch**: `035-adk-session-template` | **Date**: 2026-01-18

## Overview

This feature does not introduce new API contracts. It is an internal implementation change to how the reflection agent passes data to the LLM.

## Existing Contracts (No Changes)

### ReflectionFn Protocol

The `ReflectionFn` protocol signature remains unchanged:

```python
class ReflectionFn(Protocol):
    """Protocol for reflection functions that propose improved component text."""

    async def __call__(
        self,
        component_text: str,
        trials: list[dict[str, Any]],
    ) -> str:
        """
        Propose improved component text based on trial feedback.

        Args:
            component_text: The current component text to improve.
            trials: List of trial results with feedback.

        Returns:
            Proposed improved component text.
        """
        ...
```

### create_adk_reflection_fn Signature

The factory function signature remains unchanged:

```python
def create_adk_reflection_fn(
    reflection_agent: LlmAgent,
    session_service: BaseSessionService | None = None,
) -> ReflectionFn:
    """
    Create a reflection function from an ADK LlmAgent.

    Args:
        reflection_agent: The ADK LlmAgent to use for reflection.
        session_service: Optional session service (defaults to InMemorySessionService).

    Returns:
        A ReflectionFn that uses the agent for proposing improvements.
    """
```

## Why No New Contracts

1. **Internal Implementation**: Template substitution is an internal detail of how `create_adk_reflection_fn` prepares the agent instruction
2. **Backward Compatible**: The function signature and return type are unchanged
3. **No New Public APIs**: This feature enhances existing functionality without adding new interfaces

## Contract Tests

Existing contract tests in `tests/contracts/` verify that:
- `ReflectionFn` implementations accept `(str, list[dict])` and return `str`
- The factory function returns a valid `ReflectionFn`

No new contract tests needed for this feature.

# Contract: ComponentHandler Protocol

**Feature**: 162-component-handlers
**Date**: 2026-01-20
**Type**: Python Protocol Definition

## Protocol Signature

```python
from typing import Protocol, Any, runtime_checkable

@runtime_checkable
class ComponentHandler(Protocol):
    """Handles serialization/application of one component type."""

    def serialize(self, agent: LlmAgent) -> str:
        """Extract component value from agent as string for evolution.

        Args:
            agent: The LlmAgent instance to extract component from.

        Returns:
            String representation of the component value.
            Returns empty string if component is not set.

        Examples:
            >>> handler.serialize(agent)
            'You are a helpful assistant.'
        """
        ...

    def apply(self, agent: LlmAgent, value: str) -> Any:
        """Apply evolved value to agent, return original for restore.

        Args:
            agent: The LlmAgent instance to modify.
            value: The new component value as string.

        Returns:
            The original component value (type depends on component).

        Note:
            If application fails (e.g., invalid schema), logs warning
            and returns original without modifying agent.

        Examples:
            >>> original = handler.apply(agent, 'New instruction')
            >>> agent.instruction
            'New instruction'
        """
        ...

    def restore(self, agent: LlmAgent, original: Any) -> None:
        """Restore original value after evaluation.

        Args:
            agent: The LlmAgent instance to restore.
            original: The original value returned by apply().

        Note:
            Handles None original by resetting to component default.

        Examples:
            >>> handler.restore(agent, 'Original instruction')
            >>> agent.instruction
            'Original instruction'
        """
        ...
```

## Compliance Requirements

1. **Runtime Checkable**: `isinstance(handler, ComponentHandler)` must return `True`
2. **Serialization**: `serialize` must return valid string, never raise for missing components
3. **Idempotent Restore**: `apply` then `restore` must leave agent unchanged
4. **Error Safety**: `apply` must not raise on invalid values; log and skip instead

## Test Contract

```python
def test_protocol_compliance(handler: ComponentHandler, agent: LlmAgent) -> None:
    """Verify handler implements ComponentHandler protocol."""
    # 1. Protocol check
    assert isinstance(handler, ComponentHandler)

    # 2. Serialize returns string
    serialized = handler.serialize(agent)
    assert isinstance(serialized, str)

    # 3. Apply returns original
    original = handler.apply(agent, "test value")
    # original type depends on handler

    # 4. Restore is idempotent
    handler.restore(agent, original)
    assert handler.serialize(agent) == serialized
```

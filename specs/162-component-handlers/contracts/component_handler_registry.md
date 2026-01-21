# Contract: ComponentHandlerRegistry

**Feature**: 162-component-handlers
**Date**: 2026-01-20
**Type**: Python Class Definition

## Class Signature

```python
class ComponentHandlerRegistry:
    """Registry for component handlers with O(1) lookup."""

    def __init__(self) -> None:
        """Initialize empty registry.

        Examples:
            >>> registry = ComponentHandlerRegistry()
        """
        ...

    def register(self, name: str, handler: ComponentHandler) -> None:
        """Register a handler for a component name.

        Args:
            name: Component name (e.g., "instruction", "output_schema").
            handler: Handler implementing ComponentHandler protocol.

        Raises:
            ValueError: If name is empty or None.
            TypeError: If handler doesn't implement ComponentHandler.

        Note:
            Replaces existing handler if name already registered.

        Examples:
            >>> registry.register("instruction", InstructionHandler())
        """
        ...

    def get(self, name: str) -> ComponentHandler:
        """Retrieve handler for component name.

        Args:
            name: Component name to look up.

        Returns:
            The registered ComponentHandler.

        Raises:
            ValueError: If name is empty or None.
            KeyError: If no handler registered for name.

        Examples:
            >>> handler = registry.get("instruction")
        """
        ...

    def has(self, name: str) -> bool:
        """Check if handler exists for component name.

        Args:
            name: Component name to check.

        Returns:
            True if handler registered, False otherwise.

        Note:
            Returns False for empty/None names (no ValueError).

        Examples:
            >>> registry.has("instruction")
            True
            >>> registry.has("unknown")
            False
        """
        ...
```

## Convenience Functions

```python
# Module-level default registry
component_handlers: ComponentHandlerRegistry

def get_handler(name: str) -> ComponentHandler:
    """Get handler from default registry.

    Args:
        name: Component name to look up.

    Returns:
        The registered ComponentHandler.

    Raises:
        ValueError: If name is empty or None.
        KeyError: If no handler registered for name.

    Examples:
        >>> handler = get_handler("instruction")
    """
    return component_handlers.get(name)


def register_handler(name: str, handler: ComponentHandler) -> None:
    """Register handler in default registry.

    Args:
        name: Component name to register.
        handler: Handler implementing ComponentHandler.

    Raises:
        ValueError: If name is empty or None.
        TypeError: If handler doesn't implement ComponentHandler.

    Examples:
        >>> register_handler("my_component", MyHandler())
    """
    component_handlers.register(name, handler)
```

## Error Behavior

| Method | Input | Exception | Message |
|--------|-------|-----------|---------|
| `register` | `name=""` | `ValueError` | `"Component name must be a non-empty string"` |
| `register` | `name=None` | `ValueError` | `"Component name must be a non-empty string"` |
| `register` | invalid handler | `TypeError` | `"Handler does not implement ComponentHandler protocol"` |
| `get` | `name=""` | `ValueError` | `"Component name must be a non-empty string"` |
| `get` | `name=None` | `ValueError` | `"Component name must be a non-empty string"` |
| `get` | unregistered | `KeyError` | `"No handler registered for component: {name}"` |
| `has` | any invalid | `False` | No exception, returns False |

## Test Contract

```python
def test_registry_operations() -> None:
    """Verify registry CRUD operations."""
    registry = ComponentHandlerRegistry()

    # 1. Initially empty
    assert not registry.has("instruction")

    # 2. Register adds handler
    handler = InstructionHandler()
    registry.register("instruction", handler)
    assert registry.has("instruction")

    # 3. Get returns registered handler
    assert registry.get("instruction") is handler

    # 4. Re-register replaces
    new_handler = InstructionHandler()
    registry.register("instruction", new_handler)
    assert registry.get("instruction") is new_handler


def test_registry_errors() -> None:
    """Verify error behavior."""
    registry = ComponentHandlerRegistry()

    # Empty name
    with pytest.raises(ValueError, match="non-empty string"):
        registry.register("", InstructionHandler())

    # Invalid handler
    with pytest.raises(TypeError, match="ComponentHandler protocol"):
        registry.register("test", object())

    # Missing handler
    with pytest.raises(KeyError, match="No handler registered"):
        registry.get("unknown")
```

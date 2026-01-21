# Internal API Contracts: Component Handler Migration

**Feature**: 163-component-handler-migration
**Date**: 2026-01-20

## Overview

This feature modifies internal (private) methods only. No public API changes. These contracts document the internal method signatures for testing purposes.

## ADKAdapter Internal Methods

### _apply_candidate

**Signature Change**: `tuple[str, Any]` → `dict[str, Any]`

```python
def _apply_candidate(self, candidate: dict[str, str]) -> dict[str, Any]:
    """Apply candidate components to agent via registry dispatch.

    Args:
        candidate: Component name to evolved text mapping.
            Example: {"instruction": "Be helpful", "output_schema": "class ..."}

    Returns:
        Dictionary mapping component names to their original values.
        Original values are typed per handler (str for instruction,
        type[BaseModel] or None for output_schema).

    Raises:
        KeyError: If candidate contains unregistered component name.

    Example:
        >>> originals = adapter._apply_candidate({
        ...     "instruction": "New prompt",
        ...     "output_schema": "class X(BaseModel): ..."
        ... })
        >>> originals
        {"instruction": "Original prompt", "output_schema": <class 'OriginalSchema'>}
    """
```

### _restore_agent

**Signature Change**: Positional args → `dict[str, Any]`

```python
def _restore_agent(self, originals: dict[str, Any]) -> None:
    """Restore agent to original state via registry dispatch.

    Args:
        originals: Component name to original value mapping,
            as returned by _apply_candidate().

    Raises:
        KeyError: If originals contains unregistered component name.

    Example:
        >>> adapter._restore_agent({
        ...     "instruction": "Original prompt",
        ...     "output_schema": OriginalSchema
        ... })
        # agent.instruction == "Original prompt"
        # agent.output_schema == OriginalSchema
    """
```

## Registry Access

### get_handler

```python
def get_handler(name: str) -> ComponentHandler:
    """Get handler from default registry.

    Args:
        name: Component name (e.g., "instruction", "output_schema").

    Returns:
        Registered ComponentHandler instance.

    Raises:
        ValueError: If name is empty or None.
        KeyError: If no handler registered for name.

    Example:
        >>> handler = get_handler("instruction")
        >>> original = handler.apply(agent, "New value")
    """
```

## Contract Tests

The following contract tests verify the internal behavior:

### Test: _apply_candidate returns dict with all component originals

```python
def test_apply_candidate_returns_dict():
    adapter = create_adapter_with_mock_agent()
    candidate = {"instruction": "new", "output_schema": "class X(BaseModel): x: str"}

    originals = adapter._apply_candidate(candidate)

    assert isinstance(originals, dict)
    assert "instruction" in originals
    assert "output_schema" in originals
```

### Test: _apply_candidate raises KeyError for unknown component

```python
def test_apply_candidate_unknown_component_raises():
    adapter = create_adapter_with_mock_agent()
    candidate = {"unknown_component": "value"}

    with pytest.raises(KeyError):
        adapter._apply_candidate(candidate)
```

### Test: _restore_agent accepts dict format

```python
def test_restore_agent_accepts_dict():
    adapter = create_adapter_with_mock_agent()
    originals = {"instruction": "orig", "output_schema": None}

    # Should not raise
    adapter._restore_agent(originals)
```

### Test: evaluate() backward compatible

```python
def test_evaluate_backward_compatible():
    """Existing evaluate() behavior unchanged."""
    adapter = create_adapter()
    batch = [{"input": "test"}]
    candidate = {"instruction": "Be helpful"}

    result = await adapter.evaluate(batch, candidate)

    assert isinstance(result, EvaluationBatch)
    assert len(result.outputs) == 1
    # Agent instruction restored to original after evaluation
    assert adapter.agent.instruction == original_instruction
```

# Quickstart: Component Handler Migration

**Feature**: 163-component-handler-migration
**Date**: 2026-01-20

## Overview

This feature is an internal refactor with no user-facing changes. After migration, ADKAdapter uses the ComponentHandler registry for component application instead of hardcoded if/elif logic.

## For Library Users

**No action required.** This is a transparent refactor:

- `ADKAdapter.evaluate()` works exactly the same
- Candidate format unchanged (`dict[str, str]`)
- EvaluationBatch return type unchanged
- All existing code continues to work

## For Library Developers

### Understanding the Change

**Before** (hardcoded):
```python
def _apply_candidate(self, candidate: dict[str, str]) -> tuple[str, Any]:
    original_instruction = str(self.agent.instruction)
    original_output_schema = getattr(self.agent, "output_schema", None)

    if "instruction" in candidate:
        self.agent.instruction = candidate["instruction"]

    if "output_schema" in candidate:
        schema_text = candidate["output_schema"]
        new_schema = deserialize_schema(schema_text)
        self.agent.output_schema = new_schema

    return original_instruction, original_output_schema
```

**After** (registry dispatch):
```python
def _apply_candidate(self, candidate: dict[str, str]) -> dict[str, Any]:
    originals = {}
    for component_name, value in candidate.items():
        handler = get_handler(component_name)
        originals[component_name] = handler.apply(self.agent, value)
    return originals
```

### Adding New Component Types

The refactor enables extensible component handling. To add a new component:

1. **Create handler** implementing `ComponentHandler`:
```python
class TemperatureHandler:
    def serialize(self, agent: LlmAgent) -> str:
        config = getattr(agent, "generate_content_config", None)
        return str(config.temperature) if config else "1.0"

    def apply(self, agent: LlmAgent, value: str) -> Any:
        config = getattr(agent, "generate_content_config", None)
        original = config.temperature if config else 1.0
        if config:
            config.temperature = float(value)
        return original

    def restore(self, agent: LlmAgent, original: Any) -> None:
        config = getattr(agent, "generate_content_config", None)
        if config:
            config.temperature = original
```

2. **Register handler**:
```python
from gepa_adk.adapters.component_handlers import register_handler

register_handler("temperature", TemperatureHandler())
```

3. **Use in evolution**:
```python
candidate = {"instruction": "Be concise", "temperature": "0.3"}
result = await adapter.evaluate(batch, candidate)
```

No changes to ADKAdapter needed!

## Testing the Migration

Run existing tests to verify backward compatibility:

```bash
# All existing tests should pass unchanged
uv run pytest tests/unit/adapters/test_adk_adapter.py -v
uv run pytest tests/contracts/test_adk_adapter_contracts.py -v
uv run pytest tests/integration/adapters/ -v --slow
```

## Key Files

| File | Role |
|------|------|
| `src/gepa_adk/adapters/adk_adapter.py` | Modified to use registry |
| `src/gepa_adk/adapters/component_handlers.py` | Existing handlers (no changes) |
| `src/gepa_adk/ports/component_handler.py` | Protocol definition (no changes) |

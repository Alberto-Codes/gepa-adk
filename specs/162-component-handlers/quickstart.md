# Quickstart: ComponentHandler Protocol and Registry

**Feature**: 162-component-handlers
**Date**: 2026-01-20
**Status**: Complete

## Overview

The ComponentHandler system provides an extensible way to serialize, apply, and restore agent components during evolution. Instead of hardcoded if/elif branches, handlers are registered in a registry and looked up by component name.

## Basic Usage

### Using Built-in Handlers

```python
from gepa_adk.adapters import get_handler, InstructionHandler, OutputSchemaHandler
from google.adk.agents import LlmAgent

# Create an agent
agent = LlmAgent(name="test", model="gemini-2.0-flash", instruction="Be helpful.")

# Get the instruction handler
handler = get_handler("instruction")

# Serialize current instruction
original_text = handler.serialize(agent)
# Returns: "Be helpful."

# Apply new instruction (returns original for later restore)
original = handler.apply(agent, "Be concise and technical.")
# agent.instruction is now "Be concise and technical."
# original contains "Be helpful."

# Restore original after evaluation
handler.restore(agent, original)
# agent.instruction is back to "Be helpful."
```

### Registering Custom Handlers

```python
from typing import Any
from gepa_adk.ports import ComponentHandler
from gepa_adk.adapters import register_handler
from google.adk.agents import LlmAgent

class TemperatureHandler:
    """Handler for model temperature configuration."""

    def serialize(self, agent: LlmAgent) -> str:
        # Access temperature from agent's generate_content_config
        config = getattr(agent, "generate_content_config", None)
        if config and hasattr(config, "temperature"):
            return str(config.temperature)
        return "1.0"  # default

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

# Register the custom handler
register_handler("temperature", TemperatureHandler())

# Now use it like built-in handlers
handler = get_handler("temperature")
```

### Using Custom Registry

```python
from gepa_adk.adapters import (
    ComponentHandlerRegistry,
    InstructionHandler,
    OutputSchemaHandler,
)

# Create isolated registry for testing
test_registry = ComponentHandlerRegistry()

# Register handlers
test_registry.register("instruction", InstructionHandler())
test_registry.register("output_schema", OutputSchemaHandler())

# Use the registry
if test_registry.has("instruction"):
    handler = test_registry.get("instruction")
```

## Integration Pattern

The handlers are designed for use in try/finally blocks:

```python
def evaluate_candidate(agent: LlmAgent, candidate: dict[str, str]) -> float:
    """Evaluate a candidate by temporarily applying its components."""
    originals = {}

    try:
        # Apply all candidate components
        for component_name, value in candidate.items():
            if component_handlers.has(component_name):
                handler = get_handler(component_name)
                originals[component_name] = handler.apply(agent, value)

        # Run evaluation with modified agent
        return run_evaluation(agent)

    finally:
        # Always restore original state
        for component_name, original in originals.items():
            handler = get_handler(component_name)
            handler.restore(agent, original)
```

## Built-in Handlers

| Component Name | Handler | Description |
|----------------|---------|-------------|
| `"instruction"` | `InstructionHandler` | Agent's system instruction |
| `"output_schema"` | `OutputSchemaHandler` | Agent's output schema (Pydantic model) |

## Error Handling

```python
from gepa_adk.adapters import get_handler, register_handler

# Missing handler
try:
    handler = get_handler("unknown")
except KeyError as e:
    print(f"Handler not found: {e}")

# Invalid registration
try:
    register_handler("", InstructionHandler())
except ValueError as e:
    print(f"Invalid name: {e}")

try:
    register_handler("test", object())  # Not a ComponentHandler
except TypeError as e:
    print(f"Invalid handler: {e}")
```

## Migration from Hardcoded Branches

Before (hardcoded):
```python
def _apply_candidate(self, candidate: dict[str, str]) -> tuple[str, Any]:
    original_instruction = self.agent.instruction
    original_schema = self.agent.output_schema

    if "instruction" in candidate:
        self.agent.instruction = candidate["instruction"]

    if "output_schema" in candidate:
        schema = deserialize_schema(candidate["output_schema"])
        self.agent.output_schema = schema

    return original_instruction, original_schema
```

After (handler-based):
```python
def _apply_candidate(self, candidate: dict[str, str]) -> dict[str, Any]:
    originals = {}
    for name, value in candidate.items():
        handler = get_handler(name)
        originals[name] = handler.apply(self.agent, value)
    return originals

def _restore_agent(self, originals: dict[str, Any]) -> None:
    for name, original in originals.items():
        handler = get_handler(name)
        handler.restore(self.agent, original)
```

## Next Steps

1. **Add new component**: Implement `ComponentHandler`, call `register_handler()`
2. **Test handler**: Use contract tests in `tests/contracts/`
3. **Integrate**: The adapter will automatically use registered handlers

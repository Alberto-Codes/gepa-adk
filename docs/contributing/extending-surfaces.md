# Extending Evolvable Surfaces

This guide explains how to add new evolvable surfaces to gepa-adk by implementing the `ComponentHandler` protocol.

!!! tip "When to Use"
    Create a custom `ComponentHandler` when you need to evolve an agent attribute
    beyond the built-in surfaces (instruction, output_schema, generate_content_config).
    For example, evolving temperature, tool configurations, or custom metadata.

## Available Built-in Handlers

| Handler | Component | Purpose |
|---------|-----------|---------|
| `InstructionHandler` | `instruction` | Agent system prompt |
| `OutputSchemaHandler` | `output_schema` | Pydantic output schema |
| `GenerateContentConfigHandler` | `generate_content_config` | LLM generation parameters |

## Protocol Definition

The `ComponentHandler` protocol defines three methods for the serialize/apply/restore cycle:

```python
from gepa_adk import ComponentHandler

class ComponentHandler(Protocol):
    def serialize(self, agent: LlmAgent) -> str:
        """Extract current component value as a string."""
        ...

    def apply(self, agent: LlmAgent, value: str) -> Any:
        """Apply a new value to the agent, return the original for restoration."""
        ...

    def restore(self, agent: LlmAgent, original: Any) -> None:
        """Reinstate the original value after evaluation."""
        ...
```

!!! note "Contract"
    - `serialize()` must never raise exceptions — return empty string for missing values.
    - `apply()` must never raise exceptions — log a warning and keep the original on failure.
    - `restore()` must always succeed — None values reset to the component default.
    - All methods are synchronous — no I/O operations.

## Step-by-Step Implementation

Here is a `TemperatureHandler` that evolves the `generate_content_config.temperature` parameter:

```python
from gepa_adk import ComponentHandler  # verify structural subtyping


class TemperatureHandler:
    """Handler for evolving the temperature parameter."""

    def serialize(self, agent) -> str:
        config = getattr(agent, "generate_content_config", None)
        if config and config.temperature is not None:
            return str(config.temperature)
        return "1.0"

    def apply(self, agent, value: str):
        config = getattr(agent, "generate_content_config", None)
        original = config.temperature if config else 1.0
        try:
            new_temp = float(value)
            if config:
                config.temperature = new_temp
        except (ValueError, TypeError):
            pass  # keep original on invalid input
        return original

    def restore(self, agent, original) -> None:
        config = getattr(agent, "generate_content_config", None)
        if config:
            config.temperature = original
```

Note that `TemperatureHandler` is a **plain class** — it does not inherit from `ComponentHandler`.
gepa-adk uses structural subtyping (ADR-002): any class with matching method signatures
satisfies the protocol automatically.

## Registration

Register your handler with the `ComponentHandlerRegistry` so the evolution engine discovers it:

```python
from gepa_adk.adapters import register_handler

register_handler("temperature", TemperatureHandler())
```

The engine uses `get_handler()` to look up handlers by component name:

```python
from gepa_adk.adapters import get_handler

handler = get_handler("temperature")
original = handler.apply(agent, "0.5")
# ... evaluate agent ...
handler.restore(agent, original)
```

You can also create a dedicated registry if you need isolation from the global default:

```python
from gepa_adk.adapters import ComponentHandlerRegistry

my_registry = ComponentHandlerRegistry()
my_registry.register("temperature", TemperatureHandler())
```

## Runnable Example

This example demonstrates the full serialize/apply/restore cycle without requiring an LLM API key:

```python
from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

from gepa_adk import ComponentHandler
from gepa_adk.adapters import register_handler


class TemperatureHandler:
    def serialize(self, agent) -> str:
        config = getattr(agent, "generate_content_config", None)
        if config and config.temperature is not None:
            return str(config.temperature)
        return "1.0"

    def apply(self, agent, value: str):
        config = getattr(agent, "generate_content_config", None)
        original = config.temperature if config else 1.0
        try:
            new_temp = float(value)
            if config:
                config.temperature = new_temp
        except (ValueError, TypeError):
            pass
        return original

    def restore(self, agent, original) -> None:
        config = getattr(agent, "generate_content_config", None)
        if config:
            config.temperature = original


# Verify protocol compliance
handler = TemperatureHandler()
assert isinstance(handler, ComponentHandler)

# Create a test agent
agent = LlmAgent(
    name="demo",
    model="gemini-2.5-flash",
    instruction="Be helpful",
    generate_content_config=GenerateContentConfig(temperature=0.7),
)

# Serialize → Apply → Restore cycle
print(f"Original: {handler.serialize(agent)}")  # "0.7"

original = handler.apply(agent, "0.3")
print(f"After apply: {handler.serialize(agent)}")  # "0.3"

handler.restore(agent, original)
print(f"After restore: {handler.serialize(agent)}")  # "0.7"

# Register for use in evolution
register_handler("temperature", handler)
```

To integrate with `evolve()`, include the component name in your candidate:

```python
from gepa_adk import Candidate, EvolutionConfig, evolve, run_sync

# Register handler before evolution
register_handler("temperature", TemperatureHandler())

config = EvolutionConfig(max_iterations=5)
candidate = Candidate(components={"temperature": "0.7"})

result = run_sync(evolve(agent, trainset, config=config, seed=candidate))
```

## Common Pitfalls

!!! warning "Avoid These Mistakes"
    **Raising exceptions instead of returning defaults.** The `serialize()` and `apply()`
    methods must never raise. On failure, `serialize()` should return an empty string and
    `apply()` should log a warning and keep the original value.

    **Forgetting to restore.** Always implement `restore()`. The evolution engine calls it
    after every evaluation to reset the agent to its original state. A missing or broken
    `restore()` causes state corruption across iterations.

    **Not handling `None` values.** Agent attributes may be `None` (e.g., no
    `generate_content_config` set). Guard with `getattr()` and `None` checks.

    **Inheriting from the Protocol.** Do NOT write `class MyHandler(ComponentHandler):`.
    gepa-adk uses structural subtyping (ADR-002) — just implement the methods with
    matching signatures. Inheriting from a Protocol is misleading and unnecessary.

## Contract Test Skeleton

When adding a new handler, write contract tests to verify protocol compliance. This skeleton
follows the three-class template established in the project.

!!! note "Exemplar Reference"
    This skeleton follows the pattern in `tests/contracts/test_component_handler_protocol.py`
    — always check the latest exemplar before starting.

```python
import pytest

from gepa_adk import ComponentHandler

pytestmark = pytest.mark.contract


class TestMyHandlerRuntimeCheckable:
    """Positive compliance: isinstance checks."""

    def test_satisfies_component_handler_protocol(self):
        handler = MyHandler()
        assert isinstance(handler, ComponentHandler)

    def test_protocol_has_required_methods(self):
        handler = MyHandler()
        assert hasattr(handler, "serialize")
        assert hasattr(handler, "apply")
        assert hasattr(handler, "restore")


class TestMyHandlerBehavior:
    """Behavioral expectations: return types, state transitions."""

    def test_serialize_returns_string(self):
        handler = MyHandler()
        result = handler.serialize(agent)
        assert isinstance(result, str)

    def test_apply_returns_original(self):
        handler = MyHandler()
        original = handler.apply(agent, "new_value")
        # original should be the previous value

    def test_apply_restore_idempotent(self):
        handler = MyHandler()
        original_value = handler.serialize(agent)
        returned = handler.apply(agent, "new_value")
        handler.restore(agent, returned)
        assert handler.serialize(agent) == original_value

    def test_serialize_returns_empty_for_missing(self):
        handler = MyHandler()
        result = handler.serialize(agent_without_component)
        assert result == ""


class TestMyHandlerNonCompliance:
    """Negative cases: missing methods fail isinstance."""

    def test_missing_apply_fails(self):
        class Incomplete:
            def serialize(self, agent):
                return ""

            def restore(self, agent, original):
                pass

        assert not isinstance(Incomplete(), ComponentHandler)

    def test_missing_restore_fails(self):
        class Incomplete:
            def serialize(self, agent):
                return ""

            def apply(self, agent, value):
                return None

        assert not isinstance(Incomplete(), ComponentHandler)
```

## API Reference

- [`ComponentHandler`][gepa_adk.ports.component_handler.ComponentHandler] — Protocol definition
- [`ComponentHandlerRegistry`][gepa_adk.adapters.components.component_handlers.ComponentHandlerRegistry] — Handler registry
- [`get_handler()`][gepa_adk.adapters.components.component_handlers.get_handler] — Default registry lookup
- [`register_handler()`][gepa_adk.adapters.components.component_handlers.register_handler] — Default registry registration

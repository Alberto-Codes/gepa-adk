"""Unit tests for ComponentHandlerRegistry and handler implementations.

This module tests the registry CRUD operations, error handling,
and handler implementations for instruction and output_schema components.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

    from gepa_adk.ports.component_handler import ComponentHandler


# =============================================================================
# US2: Registry CRUD Operations Tests
# =============================================================================


class TestComponentHandlerRegistryCRUD:
    """Unit tests for ComponentHandlerRegistry CRUD operations."""

    def test_registry_initially_empty(self) -> None:
        """New registry should have no handlers."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()
        assert not registry.has("instruction")
        assert not registry.has("output_schema")

    def test_register_adds_handler(self) -> None:
        """register() should add handler to registry."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()

        class MockHandler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        handler = MockHandler()
        registry.register("test", handler)
        assert registry.has("test")

    def test_get_returns_registered_handler(self) -> None:
        """get() should return the registered handler."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()

        class MockHandler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        handler = MockHandler()
        registry.register("test", handler)
        assert registry.get("test") is handler

    def test_register_replaces_existing_handler(self) -> None:
        """Re-registering should replace the old handler."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()

        class MockHandler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        handler1 = MockHandler()
        handler2 = MockHandler()

        registry.register("test", handler1)
        assert registry.get("test") is handler1

        registry.register("test", handler2)
        assert registry.get("test") is handler2

    def test_has_returns_true_for_registered(self) -> None:
        """has() should return True for registered handlers."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()

        class MockHandler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        registry.register("test", MockHandler())
        assert registry.has("test") is True

    def test_has_returns_false_for_unregistered(self) -> None:
        """has() should return False for unregistered handlers."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()
        assert registry.has("unknown") is False


class TestComponentHandlerRegistryErrors:
    """Unit tests for registry error handling."""

    def test_get_raises_keyerror_for_missing(self) -> None:
        """get() should raise KeyError for unregistered handlers."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()
        with pytest.raises(KeyError, match="No handler registered for component"):
            registry.get("unknown")

    def test_register_empty_name_raises_valueerror(self) -> None:
        """register() with empty name should raise ValueError."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()

        class MockHandler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        with pytest.raises(ValueError, match="non-empty string"):
            registry.register("", MockHandler())

    def test_register_none_name_raises_valueerror(self) -> None:
        """register() with None name should raise ValueError."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()

        class MockHandler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        with pytest.raises(ValueError, match="non-empty string"):
            registry.register(None, MockHandler())  # type: ignore[arg-type]

    def test_get_empty_name_raises_valueerror(self) -> None:
        """get() with empty name should raise ValueError."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()
        with pytest.raises(ValueError, match="non-empty string"):
            registry.get("")

    def test_get_none_name_raises_valueerror(self) -> None:
        """get() with None name should raise ValueError."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()
        with pytest.raises(ValueError, match="non-empty string"):
            registry.get(None)  # type: ignore[arg-type]

    def test_register_invalid_handler_raises_typeerror(self) -> None:
        """register() with non-protocol handler should raise TypeError."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()

        class InvalidHandler:
            # Missing required methods
            pass

        with pytest.raises(TypeError, match="ComponentHandler protocol"):
            registry.register("test", InvalidHandler())  # type: ignore[arg-type]

    def test_has_returns_false_for_empty_name(self) -> None:
        """has() with empty name should return False (no exception)."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()
        assert registry.has("") is False

    def test_has_returns_false_for_none_name(self) -> None:
        """has() with None name should return False (no exception)."""
        from gepa_adk.adapters.component_handlers import ComponentHandlerRegistry

        registry = ComponentHandlerRegistry()
        assert registry.has(None) is False  # type: ignore[arg-type]


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_handler_uses_default_registry(self) -> None:
        """get_handler() should use the default registry."""
        from gepa_adk.adapters.component_handlers import (
            get_handler,
            register_handler,
        )

        class MockHandler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        handler = MockHandler()
        register_handler("test_convenience", handler)
        assert get_handler("test_convenience") is handler

    def test_register_handler_uses_default_registry(self) -> None:
        """register_handler() should add to default registry."""
        from gepa_adk.adapters.component_handlers import (
            component_handlers,
            register_handler,
        )

        class MockHandler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        handler = MockHandler()
        register_handler("test_default", handler)
        assert component_handlers.has("test_default")


# =============================================================================
# US3: Handler Implementation Tests
# =============================================================================


class TestInstructionHandler:
    """Unit tests for InstructionHandler."""

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create InstructionHandler instance."""
        from gepa_adk.adapters.component_handlers import InstructionHandler

        return InstructionHandler()

    @pytest.fixture
    def agent(self) -> "LlmAgent":
        """Create test agent with instruction."""
        from google.adk.agents import LlmAgent

        return LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Original instruction",
        )

    def test_serialize_returns_instruction(
        self, handler: "ComponentHandler", agent: "LlmAgent"
    ) -> None:
        """serialize() should return agent.instruction as string."""
        result = handler.serialize(agent)
        assert result == "Original instruction"

    def test_serialize_returns_empty_for_empty_instruction(
        self, handler: "ComponentHandler"
    ) -> None:
        """serialize() should return empty string if instruction is empty."""
        from google.adk.agents import LlmAgent

        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="",
        )
        result = handler.serialize(agent)
        assert result == ""

    def test_apply_sets_instruction(
        self, handler: "ComponentHandler", agent: "LlmAgent"
    ) -> None:
        """apply() should set agent.instruction to new value."""
        handler.apply(agent, "New instruction")
        assert agent.instruction == "New instruction"

    def test_apply_returns_original(
        self, handler: "ComponentHandler", agent: "LlmAgent"
    ) -> None:
        """apply() should return original instruction."""
        original = handler.apply(agent, "New instruction")
        assert original == "Original instruction"

    def test_restore_sets_instruction(
        self, handler: "ComponentHandler", agent: "LlmAgent"
    ) -> None:
        """restore() should set agent.instruction back to original."""
        original = handler.apply(agent, "Temp instruction")
        handler.restore(agent, original)
        assert agent.instruction == "Original instruction"


class TestOutputSchemaHandler:
    """Unit tests for OutputSchemaHandler."""

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create OutputSchemaHandler instance."""
        from gepa_adk.adapters.component_handlers import OutputSchemaHandler

        return OutputSchemaHandler()

    @pytest.fixture
    def test_schema(self) -> type:
        """Create a test schema class."""
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            result: str
            value: int

        return TestSchema

    @pytest.fixture
    def agent_with_schema(self, test_schema: type) -> "LlmAgent":
        """Create test agent with output schema."""
        from google.adk.agents import LlmAgent

        return LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test",
            output_schema=test_schema,
        )

    @pytest.fixture
    def agent_without_schema(self) -> "LlmAgent":
        """Create test agent without output schema."""
        from google.adk.agents import LlmAgent

        return LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test",
        )

    def test_serialize_returns_schema_text(
        self, handler: "ComponentHandler", agent_with_schema: "LlmAgent"
    ) -> None:
        """serialize() should return schema as Python source."""
        result = handler.serialize(agent_with_schema)
        assert isinstance(result, str)
        assert "TestSchema" in result or "class" in result

    def test_serialize_returns_empty_for_none(
        self, handler: "ComponentHandler", agent_without_schema: "LlmAgent"
    ) -> None:
        """serialize() should return empty string if no schema."""
        result = handler.serialize(agent_without_schema)
        assert result == ""

    def test_apply_sets_schema(
        self, handler: "ComponentHandler", agent_with_schema: "LlmAgent"
    ) -> None:
        """apply() should set agent.output_schema to deserialized schema."""
        new_schema_text = """
class NewSchema(BaseModel):
    output: str
"""
        handler.apply(agent_with_schema, new_schema_text)
        assert agent_with_schema.output_schema is not None
        assert agent_with_schema.output_schema.__name__ == "NewSchema"

    def test_apply_returns_original_schema(
        self,
        handler: "ComponentHandler",
        agent_with_schema: "LlmAgent",
        test_schema: type,
    ) -> None:
        """apply() should return original schema."""
        new_schema_text = """
class NewSchema(BaseModel):
    output: str
"""
        original = handler.apply(agent_with_schema, new_schema_text)
        assert original is test_schema

    def test_apply_keeps_original_on_invalid_schema(
        self,
        handler: "ComponentHandler",
        agent_with_schema: "LlmAgent",
        test_schema: type,
    ) -> None:
        """apply() should keep original schema on invalid input."""
        # Invalid schema text
        original = handler.apply(agent_with_schema, "invalid schema")
        # Agent should still have original schema
        assert agent_with_schema.output_schema is test_schema
        # Should return the original
        assert original is test_schema

    def test_restore_sets_schema(
        self,
        handler: "ComponentHandler",
        agent_with_schema: "LlmAgent",
        test_schema: type,
    ) -> None:
        """restore() should set agent.output_schema back to original."""
        new_schema_text = """
class NewSchema(BaseModel):
    output: str
"""
        original = handler.apply(agent_with_schema, new_schema_text)
        handler.restore(agent_with_schema, original)
        assert agent_with_schema.output_schema is test_schema


class TestGenerateContentConfigHandler:
    """Unit tests for GenerateContentConfigHandler."""

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create GenerateContentConfigHandler instance."""
        from gepa_adk.adapters.component_handlers import GenerateContentConfigHandler

        return GenerateContentConfigHandler()

    @pytest.fixture
    def agent_with_config(self) -> "LlmAgent":
        """Create test agent with generate_content_config."""
        from google.adk.agents import LlmAgent
        from google.genai.types import GenerateContentConfig

        return LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test",
            generate_content_config=GenerateContentConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=1024,
            ),
        )

    @pytest.fixture
    def agent_without_config(self) -> "LlmAgent":
        """Create test agent without generate_content_config."""
        from google.adk.agents import LlmAgent

        return LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test",
        )

    def test_serialize_returns_yaml_string(
        self, handler: "ComponentHandler", agent_with_config: "LlmAgent"
    ) -> None:
        """serialize() should return YAML string with config parameters."""
        import yaml

        result = handler.serialize(agent_with_config)
        assert isinstance(result, str)
        assert "temperature" in result

        # Should be parseable YAML
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)
        assert parsed["temperature"] == 0.7

    def test_serialize_none_returns_empty(
        self, handler: "ComponentHandler", agent_without_config: "LlmAgent"
    ) -> None:
        """serialize() should return empty string if config is None."""
        result = handler.serialize(agent_without_config)
        assert result == ""

    def test_apply_updates_agent_config(
        self, handler: "ComponentHandler", agent_with_config: "LlmAgent"
    ) -> None:
        """apply() should update agent's generate_content_config."""
        handler.apply(agent_with_config, "temperature: 0.5")
        assert agent_with_config.generate_content_config.temperature == 0.5

    def test_apply_returns_original(
        self, handler: "ComponentHandler", agent_with_config: "LlmAgent"
    ) -> None:
        """apply() should return original config."""
        original_config = agent_with_config.generate_content_config
        returned = handler.apply(agent_with_config, "temperature: 0.5")
        assert returned is original_config

    def test_apply_invalid_keeps_original(
        self, handler: "ComponentHandler", agent_with_config: "LlmAgent"
    ) -> None:
        """apply() should keep original config on validation failure."""
        original_temp = agent_with_config.generate_content_config.temperature
        # Out of range - should be rejected
        handler.apply(agent_with_config, "temperature: 999")
        assert agent_with_config.generate_content_config.temperature == original_temp

    def test_apply_malformed_yaml_keeps_original(
        self, handler: "ComponentHandler", agent_with_config: "LlmAgent"
    ) -> None:
        """apply() should keep original config on malformed YAML."""
        original_temp = agent_with_config.generate_content_config.temperature
        # Invalid YAML - should be rejected
        handler.apply(agent_with_config, "{{{{invalid yaml")
        assert agent_with_config.generate_content_config.temperature == original_temp

    def test_restore_reverts_config(
        self, handler: "ComponentHandler", agent_with_config: "LlmAgent"
    ) -> None:
        """restore() should revert agent's config to original."""
        original = handler.apply(agent_with_config, "temperature: 0.5")
        assert agent_with_config.generate_content_config.temperature == 0.5

        handler.restore(agent_with_config, original)
        assert agent_with_config.generate_content_config.temperature == 0.7

    def test_restore_handles_none(
        self, handler: "ComponentHandler", agent_with_config: "LlmAgent"
    ) -> None:
        """restore() should handle None original value."""
        handler.restore(agent_with_config, None)
        assert agent_with_config.generate_content_config is None

    def test_apply_partial_config_merges(
        self, handler: "ComponentHandler", agent_with_config: "LlmAgent"
    ) -> None:
        """apply() with partial config should preserve existing values."""
        # Apply only temperature, top_p should be preserved
        handler.apply(agent_with_config, "temperature: 0.5")
        assert agent_with_config.generate_content_config.temperature == 0.5
        assert agent_with_config.generate_content_config.top_p == 0.9

    def test_serialize_excludes_non_evolvable(
        self, handler: "ComponentHandler", agent_with_config: "LlmAgent"
    ) -> None:
        """serialize() should exclude non-evolvable parameters."""
        result = handler.serialize(agent_with_config)
        # system_instruction is NOT an evolvable param
        assert "system_instruction" not in result


class TestCustomHandlerRegistration:
    """Tests for registering and using custom handlers."""

    def test_custom_handler_can_be_registered(self) -> None:
        """Custom handlers should be registrable."""
        from gepa_adk.adapters.component_handlers import (
            ComponentHandlerRegistry,
        )

        class CustomHandler:
            def serialize(self, agent: Any) -> str:
                return "custom"

            def apply(self, agent: Any, value: str) -> Any:
                return "original"

            def restore(self, agent: Any, original: Any) -> None:
                pass

        registry = ComponentHandlerRegistry()
        handler = CustomHandler()
        registry.register("custom_component", handler)

        assert registry.has("custom_component")
        assert registry.get("custom_component") is handler

    def test_custom_handler_works_correctly(self) -> None:
        """Custom handlers should function correctly."""
        from gepa_adk.adapters.component_handlers import (
            ComponentHandlerRegistry,
        )

        class TemperatureHandler:
            def serialize(self, agent: Any) -> str:
                return str(getattr(agent, "_temp", 1.0))

            def apply(self, agent: Any, value: str) -> Any:
                original = getattr(agent, "_temp", 1.0)
                agent._temp = float(value)
                return original

            def restore(self, agent: Any, original: Any) -> None:
                agent._temp = original

        registry = ComponentHandlerRegistry()
        handler = TemperatureHandler()
        registry.register("temperature", handler)

        # Mock agent
        agent = MagicMock()
        agent._temp = 0.7

        # Test serialize
        assert handler.serialize(agent) == "0.7"

        # Test apply
        original = handler.apply(agent, "0.9")
        assert original == 0.7
        assert agent._temp == 0.9

        # Test restore
        handler.restore(agent, original)
        assert agent._temp == 0.7

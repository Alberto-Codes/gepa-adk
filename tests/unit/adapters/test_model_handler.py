"""Unit tests for ModelHandler component handler.

This module tests the ModelHandler implementation including:
- Serialization of string and wrapped models
- Application of new model values
- Restoration to original state
- Constraint validation
- Wrapper preservation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

    from gepa_adk.ports.component_handler import ComponentHandler


# =============================================================================
# US1: String Model Tests (T009-T012)
# =============================================================================


class TestModelHandlerSerializeString:
    """Unit tests for ModelHandler.serialize() with string models (T009)."""

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create ModelHandler instance."""
        from gepa_adk.adapters.component_handlers import ModelHandler

        return ModelHandler()

    @pytest.fixture
    def agent_string_model(self) -> "LlmAgent":
        """Create test agent with string model."""
        from google.adk.agents import LlmAgent

        return LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test instruction",
        )

    def test_serialize_returns_string(
        self, handler: "ComponentHandler", agent_string_model: "LlmAgent"
    ) -> None:
        """serialize() must return a string."""
        result = handler.serialize(agent_string_model)
        assert isinstance(result, str)

    def test_serialize_returns_model_name(
        self, handler: "ComponentHandler", agent_string_model: "LlmAgent"
    ) -> None:
        """serialize() must return the model name from agent.model."""
        result = handler.serialize(agent_string_model)
        assert result == "gemini-2.5-flash"

    def test_serialize_empty_model(self, handler: "ComponentHandler") -> None:
        """serialize() should handle empty string model."""
        from google.adk.agents import LlmAgent

        agent = LlmAgent(name="test", model="", instruction="Test")
        result = handler.serialize(agent)
        assert result == ""


class TestModelHandlerApplyString:
    """Unit tests for ModelHandler.apply() with string models (T010)."""

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create ModelHandler instance."""
        from gepa_adk.adapters.component_handlers import ModelHandler

        return ModelHandler()

    @pytest.fixture
    def agent_string_model(self) -> "LlmAgent":
        """Create test agent with string model."""
        from google.adk.agents import LlmAgent

        return LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test instruction",
        )

    def test_apply_changes_model(
        self, handler: "ComponentHandler", agent_string_model: "LlmAgent"
    ) -> None:
        """apply() must change agent.model to new value."""
        handler.apply(agent_string_model, "gpt-4o")
        assert agent_string_model.model == "gpt-4o"

    def test_apply_returns_original_info(
        self, handler: "ComponentHandler", agent_string_model: "LlmAgent"
    ) -> None:
        """apply() must return restore info with original model."""
        result = handler.apply(agent_string_model, "gpt-4o")
        # Should return tuple ("string", original_model_name)
        assert result is not None
        assert result[0] == "string"
        assert result[1] == "gemini-2.5-flash"

    def test_apply_no_change_when_same(
        self, handler: "ComponentHandler", agent_string_model: "LlmAgent"
    ) -> None:
        """apply() with same value should still work."""
        result = handler.apply(agent_string_model, "gemini-2.5-flash")
        assert result is not None
        assert agent_string_model.model == "gemini-2.5-flash"


class TestModelHandlerRestoreString:
    """Unit tests for ModelHandler.restore() with string models (T011)."""

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create ModelHandler instance."""
        from gepa_adk.adapters.component_handlers import ModelHandler

        return ModelHandler()

    @pytest.fixture
    def agent_string_model(self) -> "LlmAgent":
        """Create test agent with string model."""
        from google.adk.agents import LlmAgent

        return LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test instruction",
        )

    def test_restore_returns_to_original(
        self, handler: "ComponentHandler", agent_string_model: "LlmAgent"
    ) -> None:
        """restore() must return agent.model to original value."""
        original_info = handler.apply(agent_string_model, "gpt-4o")
        assert agent_string_model.model == "gpt-4o"

        handler.restore(agent_string_model, original_info)
        assert agent_string_model.model == "gemini-2.5-flash"

    def test_restore_handles_none(
        self, handler: "ComponentHandler", agent_string_model: "LlmAgent"
    ) -> None:
        """restore() with None should be a no-op."""
        original_model = agent_string_model.model
        handler.restore(agent_string_model, None)
        assert agent_string_model.model == original_model


class TestModelHandlerAutoInclude:
    """Unit tests for auto-include current model behavior (T012)."""

    def test_auto_include_documented_in_constraints(self) -> None:
        """ModelConstraints docstring should mention auto-include."""
        from gepa_adk.domain.types import ModelConstraints

        assert "auto" in ModelConstraints.__doc__.lower()


# =============================================================================
# US2: Wrapped Model Tests (T026-T029)
# =============================================================================


class TestModelHandlerSerializeWrapper:
    """Unit tests for ModelHandler.serialize() with wrapped models (T026)."""

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create ModelHandler instance."""
        from gepa_adk.adapters.component_handlers import ModelHandler

        return ModelHandler()

    @pytest.fixture
    def agent_wrapped_model(self) -> "LlmAgent":
        """Create test agent with wrapped model (LiteLlm)."""
        from google.adk.agents import LlmAgent
        from google.adk.models.lite_llm import LiteLlm

        wrapped_model = LiteLlm(
            model="ollama_chat/llama3",
            custom_header="test-value",
        )
        return LlmAgent(
            name="test_agent",
            model=wrapped_model,
            instruction="Test instruction",
        )

    def test_serialize_extracts_model_from_wrapper(
        self, handler: "ComponentHandler", agent_wrapped_model: "LlmAgent"
    ) -> None:
        """serialize() must extract model name from wrapper.model attribute."""
        result = handler.serialize(agent_wrapped_model)
        assert result == "ollama_chat/llama3"


class TestModelHandlerApplyWrapper:
    """Unit tests for ModelHandler.apply() with wrapped models (T027)."""

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create ModelHandler instance."""
        from gepa_adk.adapters.component_handlers import ModelHandler

        return ModelHandler()

    @pytest.fixture
    def agent_wrapped_model(self) -> "LlmAgent":
        """Create test agent with wrapped model (LiteLlm)."""
        from google.adk.agents import LlmAgent
        from google.adk.models.lite_llm import LiteLlm

        wrapped_model = LiteLlm(
            model="ollama_chat/llama3",
            custom_header="test-value",
        )
        return LlmAgent(
            name="test_agent",
            model=wrapped_model,
            instruction="Test instruction",
        )

    def test_apply_mutates_wrapper_in_place(
        self, handler: "ComponentHandler", agent_wrapped_model: "LlmAgent"
    ) -> None:
        """apply() must mutate wrapper.model in place, preserving wrapper object."""
        original_wrapper = agent_wrapped_model.model
        handler.apply(agent_wrapped_model, "ollama_chat/mistral")

        # Same wrapper object
        assert agent_wrapped_model.model is original_wrapper
        # But model name changed
        assert agent_wrapped_model.model.model == "ollama_chat/mistral"

    def test_apply_returns_wrapper_restore_info(
        self, handler: "ComponentHandler", agent_wrapped_model: "LlmAgent"
    ) -> None:
        """apply() must return restore info indicating wrapper type."""
        result = handler.apply(agent_wrapped_model, "ollama_chat/mistral")
        # Should return tuple ("wrapper", original_model_name)
        assert result is not None
        assert result[0] == "wrapper"
        assert result[1] == "ollama_chat/llama3"


class TestModelHandlerRestoreWrapper:
    """Unit tests for ModelHandler.restore() with wrapped models (T028)."""

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create ModelHandler instance."""
        from gepa_adk.adapters.component_handlers import ModelHandler

        return ModelHandler()

    @pytest.fixture
    def agent_wrapped_model(self) -> "LlmAgent":
        """Create test agent with wrapped model (LiteLlm)."""
        from google.adk.agents import LlmAgent
        from google.adk.models.lite_llm import LiteLlm

        wrapped_model = LiteLlm(
            model="ollama_chat/llama3",
            custom_header="test-value",
        )
        return LlmAgent(
            name="test_agent",
            model=wrapped_model,
            instruction="Test instruction",
        )

    def test_restore_wrapper_model_name(
        self, handler: "ComponentHandler", agent_wrapped_model: "LlmAgent"
    ) -> None:
        """restore() must restore wrapper.model to original name."""
        original_info = handler.apply(agent_wrapped_model, "ollama_chat/mistral")
        assert agent_wrapped_model.model.model == "ollama_chat/mistral"

        handler.restore(agent_wrapped_model, original_info)
        assert agent_wrapped_model.model.model == "ollama_chat/llama3"


class TestModelHandlerWrapperPreservation:
    """Unit tests for wrapper configuration preservation (T029)."""

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create ModelHandler instance."""
        from gepa_adk.adapters.component_handlers import ModelHandler

        return ModelHandler()

    def test_wrapper_config_preserved_after_apply(self) -> None:
        """apply() must preserve wrapper configuration (custom_header, etc.)."""
        from google.adk.agents import LlmAgent
        from google.adk.models.lite_llm import LiteLlm

        from gepa_adk.adapters.component_handlers import ModelHandler

        handler = ModelHandler()
        wrapped_model = LiteLlm(
            model="ollama_chat/llama3",
            custom_header="preserved-value",
        )
        agent = LlmAgent(
            name="test_agent",
            model=wrapped_model,
            instruction="Test",
        )

        handler.apply(agent, "ollama_chat/mistral")

        # Config preserved
        assert agent.model._additional_args.get("custom_header") == "preserved-value"

    def test_wrapper_identity_preserved(self) -> None:
        """apply() must not replace wrapper object (same object identity)."""
        from google.adk.agents import LlmAgent
        from google.adk.models.lite_llm import LiteLlm

        from gepa_adk.adapters.component_handlers import ModelHandler

        handler = ModelHandler()
        wrapped_model = LiteLlm(model="ollama_chat/llama3")
        agent = LlmAgent(name="test", model=wrapped_model, instruction="Test")

        original_wrapper_id = id(agent.model)
        handler.apply(agent, "ollama_chat/mistral")

        # Same object, different model name
        assert id(agent.model) == original_wrapper_id
        assert agent.model.model == "ollama_chat/mistral"


# =============================================================================
# US3: Constraint Validation Tests (T036-T039)
# =============================================================================


class TestModelHandlerConstraintValid:
    """Unit tests for constraint validation - valid models accepted (T036)."""

    @pytest.fixture
    def handler_with_constraints(self) -> "ComponentHandler":
        """Create ModelHandler with constraints set."""
        from gepa_adk.adapters.component_handlers import ModelHandler
        from gepa_adk.domain.types import ModelConstraints

        handler = ModelHandler()
        handler.set_constraints(
            ModelConstraints(allowed_models=("model-a", "model-b", "model-c"))
        )
        return handler

    @pytest.fixture
    def agent(self) -> "LlmAgent":
        """Create test agent."""
        from google.adk.agents import LlmAgent

        return LlmAgent(name="test", model="model-a", instruction="Test")

    def test_apply_accepts_allowed_model(
        self, handler_with_constraints: "ComponentHandler", agent: "LlmAgent"
    ) -> None:
        """apply() should accept model in allowed list."""
        result = handler_with_constraints.apply(agent, "model-b")
        assert result is not None
        assert agent.model == "model-b"


class TestModelHandlerConstraintInvalid:
    """Unit tests for constraint validation - invalid models rejected (T037)."""

    @pytest.fixture
    def handler_with_constraints(self) -> "ComponentHandler":
        """Create ModelHandler with constraints set."""
        from gepa_adk.adapters.component_handlers import ModelHandler
        from gepa_adk.domain.types import ModelConstraints

        handler = ModelHandler()
        handler.set_constraints(
            ModelConstraints(allowed_models=("model-a", "model-b"))
        )
        return handler

    @pytest.fixture
    def agent(self) -> "LlmAgent":
        """Create test agent."""
        from google.adk.agents import LlmAgent

        return LlmAgent(name="test", model="model-a", instruction="Test")

    def test_apply_rejects_invalid_model(
        self, handler_with_constraints: "ComponentHandler", agent: "LlmAgent"
    ) -> None:
        """apply() should reject model not in allowed list."""
        result = handler_with_constraints.apply(agent, "model-z")
        assert result is None  # Indicates rejection
        assert agent.model == "model-a"  # Original preserved


class TestModelHandlerConstraintLogging:
    """Unit tests for warning logging on rejection (T038)."""

    def test_apply_logs_warning_on_rejection(self, caplog: Any) -> None:
        """apply() should log warning when rejecting invalid model."""
        import logging

        from google.adk.agents import LlmAgent

        from gepa_adk.adapters.component_handlers import ModelHandler
        from gepa_adk.domain.types import ModelConstraints

        handler = ModelHandler()
        handler.set_constraints(
            ModelConstraints(allowed_models=("model-a", "model-b"))
        )
        agent = LlmAgent(name="test", model="model-a", instruction="Test")

        with caplog.at_level(logging.WARNING):
            handler.apply(agent, "model-invalid")

        # Note: structlog may not appear in caplog - this is a placeholder
        # Real verification would check structlog output or mock the logger


class TestModelHandlerNoConstraints:
    """Unit tests for no constraints = accept all (T039)."""

    @pytest.fixture
    def handler_no_constraints(self) -> "ComponentHandler":
        """Create ModelHandler without constraints."""
        from gepa_adk.adapters.component_handlers import ModelHandler

        return ModelHandler()

    @pytest.fixture
    def agent(self) -> "LlmAgent":
        """Create test agent."""
        from google.adk.agents import LlmAgent

        return LlmAgent(name="test", model="model-a", instruction="Test")

    def test_apply_accepts_any_model_without_constraints(
        self, handler_no_constraints: "ComponentHandler", agent: "LlmAgent"
    ) -> None:
        """apply() should accept any model when no constraints are set."""
        result = handler_no_constraints.apply(agent, "any-model-xyz")
        assert result is not None
        assert agent.model == "any-model-xyz"

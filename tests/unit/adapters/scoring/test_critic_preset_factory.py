"""Tests for create_critic() factory and critic_presets dict."""

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters.scoring.critic_scorer import (
    CriticOutput,
    create_critic,
    critic_presets,
)
from gepa_adk.domain.exceptions import ConfigurationError

pytestmark = pytest.mark.unit


class TestCreateCriticPresets:
    """Tests for each preset returning a correctly configured LlmAgent."""

    def test_create_critic_structured_output_returns_llm_agent(self) -> None:
        """Structured output preset returns LlmAgent with CriticOutput schema."""
        agent = create_critic("structured_output")
        assert isinstance(agent, LlmAgent)
        assert agent.name == "structured_output_critic"
        assert agent.output_schema == CriticOutput
        assert "dimension_scores" in agent.instruction.lower()
        assert "actionable_guidance" in agent.instruction.lower()

    def test_create_critic_accuracy_returns_llm_agent(self) -> None:
        """Accuracy preset returns LlmAgent with factual evaluation instruction."""
        agent = create_critic("accuracy")
        assert isinstance(agent, LlmAgent)
        assert agent.name == "accuracy_critic"
        assert agent.output_schema == CriticOutput
        assert "factual" in agent.instruction.lower()

    def test_create_critic_relevance_returns_llm_agent(self) -> None:
        """Relevance preset returns LlmAgent with relevance evaluation instruction."""
        agent = create_critic("relevance")
        assert isinstance(agent, LlmAgent)
        assert agent.name == "relevance_critic"
        assert agent.output_schema == CriticOutput
        assert "relevant" in agent.instruction.lower()


class TestCreateCriticErrorHandling:
    """Tests for invalid preset name error handling."""

    def test_create_critic_invalid_name_raises_configuration_error(self) -> None:
        """Invalid preset name raises ConfigurationError listing valid presets."""
        with pytest.raises(ConfigurationError) as exc_info:
            create_critic("nonexistent")
        assert exc_info.value.constraint is not None
        assert "structured_output" in exc_info.value.constraint
        assert "accuracy" in exc_info.value.constraint
        assert "relevance" in exc_info.value.constraint


class TestCreateCriticModelOverride:
    """Tests for model passthrough behavior."""

    def test_create_critic_with_model_passes_through(self) -> None:
        """Model kwarg is forwarded to LlmAgent constructor."""
        agent = create_critic("accuracy", model="some/model")
        assert isinstance(agent, LlmAgent)
        assert agent.model == "some/model"


class TestCriticPresetsDict:
    """Tests for critic_presets dict and re-exports."""

    def test_critic_presets_is_dict_with_three_entries(self) -> None:
        """critic_presets contains exactly three preset names."""
        assert isinstance(critic_presets, dict)
        assert len(critic_presets) == 3
        assert set(critic_presets.keys()) == {
            "structured_output",
            "accuracy",
            "relevance",
        }

    def test_create_critic_reexported_from_package(self) -> None:
        """create_critic and critic_presets are importable from gepa_adk."""
        from gepa_adk import create_critic as top_create_critic
        from gepa_adk import critic_presets as top_critic_presets

        assert callable(top_create_critic)
        assert isinstance(top_critic_presets, dict)

"""Contract tests for AsyncReflectiveMutationProposer.

This module tests the behavioral guarantees and contracts of the mutation
proposer, ensuring it meets its API specification requirements. These tests
focus on the proposer's promises to callers rather than implementation details.

Note:
    These contract tests verify behavior across all user stories, using mocked
    LLM calls to isolate the proposer's logic from external API dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer


class TestProposerInitialization:
    """Test proposer initialization and validation."""

    def test_default_initialization(self):
        """Verify proposer initializes with default values."""
        proposer = AsyncReflectiveMutationProposer()
        assert proposer.model == "ollama/gpt-oss:20b"
        assert proposer.temperature == 0.7
        assert proposer.max_tokens == 2048

    def test_custom_initialization(self):
        """Verify proposer accepts custom configuration."""
        proposer = AsyncReflectiveMutationProposer(
            model="gemini/gemini-2.5-flash",
            temperature=0.5,
            max_tokens=1024,
        )
        assert proposer.model == "gemini/gemini-2.5-flash"
        assert proposer.temperature == 0.5
        assert proposer.max_tokens == 1024

    def test_empty_model_raises_error(self):
        """Verify empty model string raises ValueError."""
        with pytest.raises(ValueError, match="model must be non-empty"):
            AsyncReflectiveMutationProposer(model="")

    def test_temperature_below_range_raises_error(self):
        """Verify temperature below 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="temperature must be between"):
            AsyncReflectiveMutationProposer(temperature=-0.1)

    def test_temperature_above_range_raises_error(self):
        """Verify temperature above 2.0 raises ValueError."""
        with pytest.raises(ValueError, match="temperature must be between"):
            AsyncReflectiveMutationProposer(temperature=2.1)

    def test_zero_max_tokens_raises_error(self):
        """Verify max_tokens <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            AsyncReflectiveMutationProposer(max_tokens=0)

    def test_negative_max_tokens_raises_error(self):
        """Verify negative max_tokens raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            AsyncReflectiveMutationProposer(max_tokens=-100)


class TestUserStory1ProposeReturnsDict:
    """Test US1: Proposer returns dict with mutated text given valid input."""

    @pytest.mark.asyncio
    async def test_propose_returns_dict_with_mutated_text(self):
        """Verify propose returns dict with mutated instruction."""
        proposer = AsyncReflectiveMutationProposer()
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [
                {"input": "What is 2+2?", "feedback": "Add explanations"}
            ]
        }

        # Mock litellm.acompletion to return improved text
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Be helpful and explain your reasoning"))
        ]

        with patch("gepa_adk.engine.proposer.acompletion", new=AsyncMock(return_value=mock_response)):
            result = await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )

        assert result is not None
        assert isinstance(result, dict)
        assert "instruction" in result
        assert result["instruction"] == "Be helpful and explain your reasoning"


class TestUserStory1ConfiguredModel:
    """Test US1: Proposer uses configured model for LLM calls."""

    @pytest.mark.asyncio
    async def test_propose_uses_configured_model(self):
        """Verify propose calls LLM with the configured model."""
        proposer = AsyncReflectiveMutationProposer(model="gemini/gemini-2.5-flash")
        candidate = {"instruction": "Be concise"}
        reflective_dataset = {
            "instruction": [{"input": "test", "feedback": "good"}]
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Be concise and clear"))
        ]

        with patch("gepa_adk.engine.proposer.acompletion", new=AsyncMock(return_value=mock_response)) as mock_acompletion:
            await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )

            # Verify the model parameter was passed correctly
            mock_acompletion.assert_called_once()
            call_kwargs = mock_acompletion.call_args[1]
            assert call_kwargs["model"] == "gemini/gemini-2.5-flash"


class TestUserStory3EmptyDataset:
    """Test US3: Proposer returns None for empty reflective dataset."""

    @pytest.mark.asyncio
    async def test_propose_returns_none_for_empty_dict(self):
        """Verify propose returns None when reflective_dataset is empty dict."""
        proposer = AsyncReflectiveMutationProposer()
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {}  # Empty

        with patch("gepa_adk.engine.proposer.acompletion", new=AsyncMock()) as mock_acompletion:
            result = await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )

            assert result is None
            # Verify no LLM calls were made (cost optimization)
            mock_acompletion.assert_not_called()

    @pytest.mark.asyncio
    async def test_propose_returns_none_for_empty_feedback_list(self):
        """Verify propose returns None when component has empty feedback list."""
        proposer = AsyncReflectiveMutationProposer()
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {"instruction": []}  # Empty list

        with patch("gepa_adk.engine.proposer.acompletion", new=AsyncMock()) as mock_acompletion:
            result = await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )

            assert result is None
            mock_acompletion.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_llm_calls_when_returning_none(self):
        """Verify no LLM calls made when returning None (cost optimization)."""
        proposer = AsyncReflectiveMutationProposer()
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {}

        with patch("gepa_adk.engine.proposer.acompletion", new=AsyncMock()) as mock_acompletion:
            result = await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )

            assert result is None
            mock_acompletion.assert_not_called()


class TestEdgeCaseEmptyLLMResponse:
    """Test edge case: Empty LLM response returns original text."""

    @pytest.mark.asyncio
    async def test_empty_llm_response_returns_original_text(self):
        """Verify empty LLM response falls back to original candidate text."""
        proposer = AsyncReflectiveMutationProposer()
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [{"input": "test", "feedback": "good"}]
        }

        # Mock LLM returning empty string
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=""))]

        with patch("gepa_adk.engine.proposer.acompletion", new=AsyncMock(return_value=mock_response)):
            result = await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )

            assert result is not None
            assert result["instruction"] == "Be helpful"  # Original text


class TestEdgeCaseNoneLLMContent:
    """Test edge case: None LLM content returns original text."""

    @pytest.mark.asyncio
    async def test_none_llm_content_returns_original_text(self):
        """Verify None LLM content falls back to original candidate text."""
        proposer = AsyncReflectiveMutationProposer()
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [{"input": "test", "feedback": "good"}]
        }

        # Mock LLM returning None content
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]

        with patch("gepa_adk.engine.proposer.acompletion", new=AsyncMock(return_value=mock_response)):
            result = await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction"],
            )

            assert result is not None
            assert result["instruction"] == "Be helpful"  # Original text


class TestEdgeCaseComponentNotInCandidate:
    """Test edge case: Component not in candidate is skipped silently."""

    @pytest.mark.asyncio
    async def test_component_not_in_candidate_is_skipped(self):
        """Verify component not in candidate dict is skipped without error."""
        proposer = AsyncReflectiveMutationProposer()
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [{"input": "test", "feedback": "good"}],
            "context": [{"input": "test2", "feedback": "ok"}],  # Not in candidate
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Be helpful and clear"))
        ]

        with patch("gepa_adk.engine.proposer.acompletion", new=AsyncMock(return_value=mock_response)):
            result = await proposer.propose(
                candidate=candidate,
                reflective_dataset=reflective_dataset,
                components_to_update=["instruction", "context"],
            )

            # Should only have instruction, context skipped
            assert result is not None
            assert "instruction" in result
            assert "context" not in result


class TestEdgeCaseLiteLLMExceptionsPropagateUnchanged:
    """Test edge case: LiteLLM exceptions propagate unchanged (fail-fast)."""

    @pytest.mark.asyncio
    async def test_authentication_error_propagates(self):
        """Verify AuthenticationError propagates unchanged."""
        # Import the exception type we'll be mocking
        import litellm

        proposer = AsyncReflectiveMutationProposer()
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [{"input": "test", "feedback": "good"}]
        }

        # Mock LLM raising AuthenticationError with required arguments
        mock_error = litellm.AuthenticationError(
            message="Invalid API key",
            llm_provider="test",
            model="test-model",
        )
        with patch("gepa_adk.engine.proposer.acompletion", new=AsyncMock(side_effect=mock_error)):
            with pytest.raises(litellm.AuthenticationError, match="Invalid API key"):
                await proposer.propose(
                    candidate=candidate,
                    reflective_dataset=reflective_dataset,
                    components_to_update=["instruction"],
                )

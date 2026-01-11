"""Unit tests for CriticScorer implementation.

These tests verify the business logic of CriticScorer using mocked dependencies
to isolate the scorer behavior from external ADK services.

Note:
    Unit tests use mocked ADK agents and runners to avoid real API calls.
    Integration tests (in tests/integration/) use real ADK services.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters.critic_scorer import CriticScorer
from gepa_adk.domain.exceptions import (
    CriticOutputParseError,
    MissingScoreFieldError,
    ScoringError,
)


@pytest.fixture
def mock_agent() -> LlmAgent:
    """Create a mock ADK agent for testing."""
    # Use a real LlmAgent instance for testing
    return LlmAgent(
        name="test_critic",
        model="gemini-2.0-flash",
        instruction="Test critic agent",
    )


@pytest.fixture
def mock_session_service() -> MagicMock:
    """Create a mock session service for testing."""
    service = MagicMock()
    mock_session = MagicMock()
    mock_session.session_id = "test_session_123"
    service.create_session = AsyncMock(return_value=mock_session)
    return service


@pytest.fixture
def scorer(mock_agent: LlmAgent, mock_session_service: MagicMock) -> CriticScorer:
    """Create a CriticScorer instance for testing."""
    return CriticScorer(
        critic_agent=mock_agent,
        session_service=mock_session_service,
        app_name="test_app",
    )


@pytest.mark.unit
class TestCriticScorerConstructor:
    """Unit tests for CriticScorer constructor."""

    def test_constructor_validates_agent_type(self) -> None:
        """Verify constructor rejects non-BaseAgent objects."""
        with pytest.raises(TypeError, match="critic_agent must be BaseAgent"):
            CriticScorer(critic_agent="not_an_agent")  # type: ignore

    def test_constructor_validates_app_name(self, mock_agent: LlmAgent) -> None:
        """Verify constructor rejects empty app_name."""
        with pytest.raises(ValueError, match="app_name cannot be empty"):
            CriticScorer(critic_agent=mock_agent, app_name="")

    def test_constructor_creates_default_session_service(
        self, mock_agent: LlmAgent
    ) -> None:
        """Verify constructor creates InMemorySessionService if not provided."""
        scorer = CriticScorer(critic_agent=mock_agent)
        assert scorer._session_service is not None

    def test_constructor_uses_provided_session_service(
        self, mock_agent: LlmAgent, mock_session_service: MagicMock
    ) -> None:
        """Verify constructor uses provided session service."""
        scorer = CriticScorer(
            critic_agent=mock_agent, session_service=mock_session_service
        )
        assert scorer._session_service is mock_session_service


@pytest.mark.unit
class TestFormatCriticInput:
    """Unit tests for _format_critic_input() helper method."""

    def test_format_without_expected(self, scorer: CriticScorer) -> None:
        """Verify formatting without expected output."""
        result = scorer._format_critic_input(
            input_text="What is 2+2?",
            output="4",
            expected=None,
        )

        assert "Input Query:" in result
        assert "What is 2+2?" in result
        assert "Agent Output:" in result
        assert "4" in result
        assert "Expected Output:" not in result

    def test_format_with_expected(self, scorer: CriticScorer) -> None:
        """Verify formatting with expected output."""
        result = scorer._format_critic_input(
            input_text="What is 2+2?",
            output="4",
            expected="4",
        )

        assert "Input Query:" in result
        assert "What is 2+2?" in result
        assert "Agent Output:" in result
        assert "4" in result
        assert "Expected Output:" in result


@pytest.mark.unit
class TestParseCriticOutput:
    """Unit tests for _parse_critic_output() helper method."""

    def test_parse_valid_output_with_score(self, scorer: CriticScorer) -> None:
        """Verify parsing valid JSON with score field."""
        output = '{"score": 0.75, "feedback": "Good"}'
        score, metadata = scorer._parse_critic_output(output)

        assert score == 0.75
        assert metadata["feedback"] == "Good"

    def test_parse_output_with_dimension_scores(self, scorer: CriticScorer) -> None:
        """Verify parsing output with dimension_scores."""
        output = '{"score": 0.8, "dimension_scores": {"accuracy": 0.9, "clarity": 0.7}}'
        score, metadata = scorer._parse_critic_output(output)

        assert score == 0.8
        assert "dimension_scores" in metadata
        assert metadata["dimension_scores"]["accuracy"] == 0.9
        assert metadata["dimension_scores"]["clarity"] == 0.7

    def test_parse_output_with_actionable_guidance(
        self, scorer: CriticScorer
    ) -> None:
        """Verify parsing output with actionable_guidance."""
        output = '{"score": 0.6, "actionable_guidance": "Be more concise"}'
        score, metadata = scorer._parse_critic_output(output)

        assert score == 0.6
        assert metadata["actionable_guidance"] == "Be more concise"

    def test_parse_output_preserves_additional_fields(
        self, scorer: CriticScorer
    ) -> None:
        """Verify parsing preserves additional fields in metadata."""
        output = '{"score": 0.7, "custom_field": "value", "nested": {"key": "val"}}'
        score, metadata = scorer._parse_critic_output(output)

        assert score == 0.7
        assert metadata["custom_field"] == "value"
        assert metadata["nested"] == {"key": "val"}

    def test_parse_invalid_json_raises_error(self, scorer: CriticScorer) -> None:
        """Verify parsing invalid JSON raises CriticOutputParseError."""
        output = "not valid json"

        with pytest.raises(CriticOutputParseError) as exc_info:
            scorer._parse_critic_output(output)

        assert exc_info.value.raw_output == output

    def test_parse_non_dict_json_raises_error(self, scorer: CriticScorer) -> None:
        """Verify parsing non-dict JSON raises CriticOutputParseError."""
        output = '["not", "a", "dict"]'

        with pytest.raises(CriticOutputParseError) as exc_info:
            scorer._parse_critic_output(output)

        assert "JSON object" in str(exc_info.value)

    def test_parse_missing_score_raises_error(self, scorer: CriticScorer) -> None:
        """Verify parsing JSON without score field raises MissingScoreFieldError."""
        output = '{"feedback": "Good but no score"}'

        with pytest.raises(MissingScoreFieldError) as exc_info:
            scorer._parse_critic_output(output)

        assert "score" in exc_info.value.available_fields or len(
            exc_info.value.available_fields
        ) == 1

    def test_parse_non_numeric_score_raises_error(
        self, scorer: CriticScorer
    ) -> None:
        """Verify parsing JSON with non-numeric score raises MissingScoreFieldError."""
        output = '{"score": "not a number"}'

        with pytest.raises(MissingScoreFieldError):
            scorer._parse_critic_output(output)


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncScore:
    """Unit tests for async_score() method (US1)."""

    async def test_async_score_with_mock_agent(
        self, scorer: CriticScorer, mock_session_service: MagicMock
    ) -> None:
        """Verify async_score() executes critic agent and returns score."""
        # Mock runner and events
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_part = MagicMock()
        mock_part.text = '{"score": 0.75, "feedback": "Good"}'
        mock_event.actions.response_content = [mock_part]  # type: ignore

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        with patch("gepa_adk.adapters.critic_scorer.Runner") as MockRunner:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run_async = mock_run_async
            MockRunner.return_value = mock_runner_instance

            score, metadata = await scorer.async_score(
                input_text="What is 2+2?",
                output="4",
                expected="4",
            )

        assert score == 0.75
        assert metadata["feedback"] == "Good"

    async def test_async_score_creates_isolated_session(
        self, scorer: CriticScorer, mock_session_service: MagicMock
    ) -> None:
        """Verify async_score() creates isolated session when session_id is None."""
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_part = MagicMock()
        mock_part.text = '{"score": 0.5}'
        mock_event.actions.response_content = [mock_part]  # type: ignore

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        with patch("gepa_adk.adapters.critic_scorer.Runner") as MockRunner:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run_async = mock_run_async
            MockRunner.return_value = mock_runner_instance

            await scorer.async_score(
                input_text="test",
                output="test",
            )

        # Verify session was created
        mock_session_service.create_session.assert_called_once()

    async def test_async_score_reuses_existing_session(
        self, scorer: CriticScorer, mock_session_service: MagicMock
    ) -> None:
        """Verify async_score() reuses session when session_id is provided."""
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_part = MagicMock()
        mock_part.text = '{"score": 0.5}'
        mock_event.actions.response_content = [mock_part]  # type: ignore

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        with patch("gepa_adk.adapters.critic_scorer.Runner") as MockRunner:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run_async = mock_run_async
            MockRunner.return_value = mock_runner_instance

            await scorer.async_score(
                input_text="test",
                output="test",
                session_id="existing_session",
            )

        # Verify session was created/reused with provided session_id
        call_args = mock_session_service.create_session.call_args
        assert call_args is not None
        assert call_args.kwargs.get("session_id") == "existing_session"

    async def test_async_score_handles_parse_error(
        self, scorer: CriticScorer, mock_session_service: MagicMock
    ) -> None:
        """Verify async_score() raises CriticOutputParseError for invalid JSON."""
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_part = MagicMock()
        mock_part.text = "not valid json"
        mock_event.actions.response_content = [mock_part]  # type: ignore

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        with patch("gepa_adk.adapters.critic_scorer.Runner") as MockRunner:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run_async = mock_run_async
            MockRunner.return_value = mock_runner_instance

            with pytest.raises(CriticOutputParseError):
                await scorer.async_score(
                    input_text="test",
                    output="test",
                )

    async def test_async_score_handles_missing_score_error(
        self, scorer: CriticScorer, mock_session_service: MagicMock
    ) -> None:
        """Verify async_score() raises MissingScoreFieldError when score missing."""
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_part = MagicMock()
        mock_part.text = '{"feedback": "Good but no score"}'
        mock_event.actions.response_content = [mock_part]  # type: ignore

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        with patch("gepa_adk.adapters.critic_scorer.Runner") as MockRunner:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run_async = mock_run_async
            MockRunner.return_value = mock_runner_instance

            with pytest.raises(MissingScoreFieldError):
                await scorer.async_score(
                    input_text="test",
                    output="test",
                )

    async def test_async_score_handles_execution_error(
        self, scorer: CriticScorer, mock_session_service: MagicMock
    ) -> None:
        """Verify async_score() raises ScoringError when agent execution fails."""
        async def mock_run_async(*args, **kwargs):
            raise RuntimeError("Agent execution failed")

        with patch("gepa_adk.adapters.critic_scorer.Runner") as MockRunner:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run_async = mock_run_async
            MockRunner.return_value = mock_runner_instance

            with pytest.raises(ScoringError) as exc_info:
                await scorer.async_score(
                    input_text="test",
                    output="test",
                )

            assert "execution failed" in str(exc_info.value).lower()

    async def test_async_score_handles_empty_output(
        self, scorer: CriticScorer, mock_session_service: MagicMock
    ) -> None:
        """Verify async_score() raises ScoringError when agent returns empty output."""
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.actions.response_content = []  # type: ignore

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        with patch("gepa_adk.adapters.critic_scorer.Runner") as MockRunner:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run_async = mock_run_async
            MockRunner.return_value = mock_runner_instance

            with pytest.raises(ScoringError) as exc_info:
                await scorer.async_score(
                    input_text="test",
                    output="test",
                )

            assert "empty output" in str(exc_info.value).lower()


@pytest.mark.unit
class TestScoreSyncWrapper:
    """Unit tests for score() sync wrapper (US1)."""

    def test_score_calls_async_score(self, scorer: CriticScorer) -> None:
        """Verify score() calls async_score() via asyncio.run()."""
        with patch.object(scorer, "async_score", new_callable=AsyncMock) as mock_async:
            mock_async.return_value = (0.75, {"feedback": "Good"})

            score, metadata = scorer.score(
                input_text="test",
                output="test",
            )

            assert score == 0.75
            assert metadata["feedback"] == "Good"
            mock_async.assert_called_once_with("test", "test", None)

    def test_score_passes_expected_parameter(self, scorer: CriticScorer) -> None:
        """Verify score() passes expected parameter to async_score()."""
        with patch.object(scorer, "async_score", new_callable=AsyncMock) as mock_async:
            mock_async.return_value = (1.0, {})

            scorer.score(
                input_text="test",
                output="test",
                expected="expected",
            )

            mock_async.assert_called_once_with("test", "test", "expected")


@pytest.mark.unit
@pytest.mark.asyncio
class TestSequentialAgentSupport:
    """Unit tests for SequentialAgent critic support (US2)."""

    async def test_async_score_with_sequential_agent(
        self, mock_session_service: MagicMock
    ) -> None:
        """Verify async_score() works with SequentialAgent critic."""
        from google.adk.agents import SequentialAgent, LlmAgent

        # Create a SequentialAgent with sub-agents
        sub_agent = LlmAgent(
            name="scorer",
            model="gemini-2.0-flash",
            instruction="Score the output",
        )
        sequential_agent = SequentialAgent(
            name="workflow_critic",
            sub_agents=[sub_agent],
        )

        scorer = CriticScorer(
            critic_agent=sequential_agent,
            session_service=mock_session_service,
        )

        # Mock runner and events (final event from last sub-agent)
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_part = MagicMock()
        mock_part.text = '{"score": 0.85, "feedback": "Workflow completed"}'
        mock_event.actions.response_content = [mock_part]  # type: ignore

        async def mock_run_async(*args, **kwargs):
            yield mock_event

        with patch("gepa_adk.adapters.critic_scorer.Runner") as MockRunner:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run_async = mock_run_async
            MockRunner.return_value = mock_runner_instance

            score, metadata = await scorer.async_score(
                input_text="test",
                output="test",
            )

        assert score == 0.85
        assert metadata["feedback"] == "Workflow completed"


@pytest.mark.unit
class TestMultiDimensionalScoring:
    """Unit tests for multi-dimensional scoring (US3)."""

    def test_dimension_scores_extraction_already_tested(
        self, scorer: CriticScorer
    ) -> None:
        """Verify dimension_scores extraction (covered by test_parse_output_with_dimension_scores)."""
        # This is already tested in TestParseCriticOutput.test_parse_output_with_dimension_scores
        pass

    def test_actionable_guidance_extraction_already_tested(
        self, scorer: CriticScorer
    ) -> None:
        """Verify actionable_guidance extraction (covered by test_parse_output_with_actionable_guidance)."""
        # This is already tested in TestParseCriticOutput.test_parse_output_with_actionable_guidance
        pass

    def test_non_numeric_dimension_scores_passthrough(
        self, scorer: CriticScorer
    ) -> None:
        """Verify non-numeric dimension_scores values are preserved (US3)."""
        # Test that dimension_scores can contain non-numeric values and are passed through
        output = '{"score": 0.7, "dimension_scores": {"accuracy": 0.9, "note": "string_value"}}'
        score, metadata = scorer._parse_critic_output(output)

        assert score == 0.7
        assert metadata["dimension_scores"]["accuracy"] == 0.9
        assert metadata["dimension_scores"]["note"] == "string_value"


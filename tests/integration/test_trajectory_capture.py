"""Integration tests for trajectory capture functionality.

Tests verify end-to-end trajectory extraction with ADKAdapter integration,
including redaction, truncation, and configuration behavior.
"""

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters.adk_adapter import ADKAdapter
from gepa_adk.adapters.agent_executor import AgentExecutor
from gepa_adk.domain.trajectory import ADKTrajectory
from gepa_adk.domain.types import TrajectoryConfig
from tests.conftest import MockScorer

pytestmark = [pytest.mark.integration, pytest.mark.api, pytest.mark.requires_gemini]


@pytest.fixture
def mock_agent() -> LlmAgent:
    """Create a real LlmAgent for testing."""
    return LlmAgent(
        name="test_agent",
        model="gemini-2.0-flash",
        instruction="Test instruction",
    )


@pytest.fixture
def reflection_agent() -> LlmAgent:
    """Create a reflection agent for ADKAdapter."""
    return LlmAgent(name="reflector", model="gemini-2.0-flash")


@pytest.fixture
def mock_scorer() -> MockScorer:
    """Create a mock scorer with fixed 0.5 score for trajectory tests."""
    return MockScorer(score_value=0.5)


@pytest.fixture
def integration_executor() -> AgentExecutor:
    """Create an AgentExecutor for integration tests."""
    return AgentExecutor()


class TestTrajectoryCapture:
    """Integration tests for full trajectory capture with ADKAdapter."""

    @pytest.mark.asyncio
    async def test_adapter_with_default_trajectory_config(
        self, mock_agent, mock_scorer, integration_executor, reflection_agent
    ) -> None:
        """ADKAdapter uses default TrajectoryConfig when none provided."""
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=integration_executor,
            reflection_agent=reflection_agent,
        )

        assert adapter.trajectory_config is not None
        assert adapter.trajectory_config.include_tool_calls is True
        assert adapter.trajectory_config.redact_sensitive is True
        assert adapter.trajectory_config.max_string_length == 10000

    @pytest.mark.asyncio
    async def test_adapter_with_custom_trajectory_config(
        self, mock_agent, mock_scorer, integration_executor, reflection_agent
    ) -> None:
        """ADKAdapter accepts custom TrajectoryConfig."""
        config = TrajectoryConfig(
            include_tool_calls=False,
            redact_sensitive=False,
            max_string_length=5000,
        )
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=integration_executor,
            reflection_agent=reflection_agent,
            trajectory_config=config,
        )

        assert adapter.trajectory_config.include_tool_calls is False
        assert adapter.trajectory_config.redact_sensitive is False
        assert adapter.trajectory_config.max_string_length == 5000

    @pytest.mark.asyncio
    async def test_trajectory_with_redaction(
        self, mock_agent, mock_scorer, integration_executor, reflection_agent, mocker
    ) -> None:
        """Build trajectory with redaction applied."""
        config = TrajectoryConfig(redact_sensitive=True, sensitive_keys=("password",))
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=integration_executor,
            reflection_agent=reflection_agent,
            trajectory_config=config,
        )

        # Create mock event with sensitive data
        mock_fc = mocker.MagicMock()
        mock_fc.name = "auth"
        mock_fc.args = {"username": "alice", "password": "secret"}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]
        mock_actions.state_delta = None

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions
        mock_event.usage_metadata = None

        # Build trajectory
        trajectory = adapter._build_trajectory(
            events=[mock_event],
            final_output="Success",
        )

        assert isinstance(trajectory, ADKTrajectory)
        assert len(trajectory.tool_calls) == 1
        assert trajectory.tool_calls[0].arguments["username"] == "alice"
        assert trajectory.tool_calls[0].arguments["password"] == "[REDACTED]"

    @pytest.mark.asyncio
    async def test_trajectory_with_truncation(
        self, mock_agent, mock_scorer, integration_executor, reflection_agent, mocker
    ) -> None:
        """Build trajectory with truncation applied."""
        config = TrajectoryConfig(max_string_length=100)
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=integration_executor,
            reflection_agent=reflection_agent,
            trajectory_config=config,
        )

        # Create mock event with large data
        mock_fc = mocker.MagicMock()
        mock_fc.name = "process"
        mock_fc.args = {"data": "x" * 200}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]
        mock_actions.state_delta = None

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions
        mock_event.usage_metadata = None

        # Build trajectory
        trajectory = adapter._build_trajectory(
            events=[mock_event],
            final_output="Success",
        )

        assert isinstance(trajectory, ADKTrajectory)
        assert len(trajectory.tool_calls) == 1
        result = trajectory.tool_calls[0].arguments["data"]
        assert len(result) == 124  # 100 chars + "...[truncated 100 chars]" (24 chars)
        assert "truncated 100 chars" in result

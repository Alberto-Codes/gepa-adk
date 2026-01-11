"""Integration tests for trajectory capture functionality.

Tests verify end-to-end trajectory extraction with ADKAdapter integration,
including redaction, truncation, and configuration behavior.
"""

import pytest

from gepa_adk.adapters.adk_adapter import ADKAdapter
from gepa_adk.domain.trajectory import ADKTrajectory
from gepa_adk.domain.types import TrajectoryConfig

pytestmark = pytest.mark.integration


class TestTrajectoryCapture:
    """Integration tests for full trajectory capture with ADKAdapter."""

    @pytest.mark.asyncio
    async def test_adapter_with_default_trajectory_config(self, mocker) -> None:
        """ADKAdapter uses default TrajectoryConfig when none provided."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "test_agent"
        mock_agent.instruction = "Test"

        mock_scorer = mocker.MagicMock()
        mock_scorer.score = mocker.MagicMock(return_value=0.5)
        mock_scorer.async_score = mocker.AsyncMock(return_value=0.5)

        adapter = ADKAdapter(agent=mock_agent, scorer=mock_scorer)

        assert adapter.trajectory_config is not None
        assert adapter.trajectory_config.include_tool_calls is True
        assert adapter.trajectory_config.redact_sensitive is True
        assert adapter.trajectory_config.max_string_length == 10000

    @pytest.mark.asyncio
    async def test_adapter_with_custom_trajectory_config(self, mocker) -> None:
        """ADKAdapter accepts custom TrajectoryConfig."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "test_agent"
        mock_agent.instruction = "Test"

        mock_scorer = mocker.MagicMock()
        mock_scorer.score = mocker.MagicMock(return_value=0.5)
        mock_scorer.async_score = mocker.AsyncMock(return_value=0.5)

        config = TrajectoryConfig(
            include_tool_calls=False,
            redact_sensitive=False,
            max_string_length=5000,
        )
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            trajectory_config=config,
        )

        assert adapter.trajectory_config.include_tool_calls is False
        assert adapter.trajectory_config.redact_sensitive is False
        assert adapter.trajectory_config.max_string_length == 5000

    @pytest.mark.asyncio
    async def test_trajectory_with_redaction(self, mocker) -> None:
        """Build trajectory with redaction applied."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "test_agent"
        mock_agent.instruction = "Test"

        mock_scorer = mocker.MagicMock()
        mock_scorer.score = mocker.MagicMock(return_value=0.5)
        mock_scorer.async_score = mocker.AsyncMock(return_value=0.5)

        config = TrajectoryConfig(redact_sensitive=True, sensitive_keys=("password",))
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            trajectory_config=config,
        )

        # Create mock event with sensitive data
        mock_fc = mocker.MagicMock()
        mock_fc.name = "auth"
        mock_fc.args = {"username": "alice", "password": "secret"}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

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
    async def test_trajectory_with_truncation(self, mocker) -> None:
        """Build trajectory with truncation applied."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "test_agent"
        mock_agent.instruction = "Test"

        mock_scorer = mocker.MagicMock()
        mock_scorer.score = mocker.MagicMock(return_value=0.5)
        mock_scorer.async_score = mocker.AsyncMock(return_value=0.5)

        config = TrajectoryConfig(max_string_length=100)
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            trajectory_config=config,
        )

        # Create mock event with large data
        mock_fc = mocker.MagicMock()
        mock_fc.name = "process"
        mock_fc.args = {"data": "x" * 200}

        mock_actions = mocker.MagicMock()
        mock_actions.function_calls = [mock_fc]

        mock_event = mocker.MagicMock()
        mock_event.actions = mock_actions

        # Build trajectory
        trajectory = adapter._build_trajectory(
            events=[mock_event],
            final_output="Success",
        )

        assert isinstance(trajectory, ADKTrajectory)
        assert len(trajectory.tool_calls) == 1
        result = trajectory.tool_calls[0].arguments["data"]
        assert len(result) == 126  # 100 chars + "...[truncated 100 chars]"
        assert "truncated 100 chars" in result

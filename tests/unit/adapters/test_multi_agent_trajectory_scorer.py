"""MultiAgentAdapter sends the trajectory to scorers that declare it.

A scorer whose ``async_score`` declares ``trajectory`` receives an
``ADKTrajectory`` built from the captured pipeline events, even when the
engine evaluates with ``capture_traces=False``. The batch keeps
``trajectories=None`` in that case. A three-argument scorer receives exactly
``(input_text, output, expected)`` and no keyword arguments.

Examples:
    ```bash
    uv run pytest tests/unit/adapters/test_multi_agent_trajectory_scorer.py -q
    ```

See Also:
    - [`gepa_adk.adapters.evolution.multi_agent`][gepa_adk.adapters.evolution.multi_agent]:
        Adapter under test.
    - [`gepa_adk.ports.scorer`][gepa_adk.ports.scorer]: ``scorer_accepts_trajectory``.

Notes:
    The executor is mocked, so no agent or LLM runs.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from google.adk.agents import LlmAgent
from pytest_mock import MockerFixture

from gepa_adk.adapters import MultiAgentAdapter
from gepa_adk.domain.trajectory import ADKTrajectory
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

pytestmark = pytest.mark.unit


class _TrajectoryScorer:
    """Scorer that records the trajectory it receives.

    Attributes:
        received (list[ADKTrajectory | None]): Trajectories passed per call.
    """

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.received: list[ADKTrajectory | None] = []

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        *,
        trajectory: ADKTrajectory | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Record the trajectory and return a fixed score.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.
            trajectory: Recorded.

        Returns:
            A score of 1.0 with empty metadata.
        """
        self.received.append(trajectory)
        return 1.0, {}

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        *,
        trajectory: ADKTrajectory | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Record the trajectory and return a fixed score.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.
            trajectory: Recorded.

        Returns:
            A score of 1.0 with empty metadata.
        """
        return self.score(input_text, output, expected, trajectory=trajectory)


class _ThreeArgScorer:
    """Scorer with the three-argument signature that records every call.

    Attributes:
        calls (list[tuple[tuple[Any, ...], dict[str, Any]]]): Positional and
            keyword arguments of each ``async_score`` call.
    """

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Return a fixed score.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.

        Returns:
            ``(0.25, {})``.
        """
        return 0.25, {}

    async def async_score(
        self, *args: Any, **kwargs: Any
    ) -> tuple[float, dict[str, Any]]:
        """Record the call arguments and return a fixed score.

        Args:
            *args: Recorded positional arguments.
            **kwargs: Recorded keyword arguments.

        Returns:
            ``(0.25, {})``.
        """
        self.calls.append((args, kwargs))
        return 0.25, {}


def _tool_event(mocker: MockerFixture, name: str) -> Any:
    """Build a fake ADK event carrying one function call.

    Args:
        mocker: pytest-mock fixture.
        name: Function call name.

    Returns:
        A mock event with ``actions.function_calls`` set.
    """
    event = mocker.MagicMock()
    event.is_final_response = lambda: False
    event.author = None
    event.actions = mocker.MagicMock(
        function_calls=[SimpleNamespace(name=name, args={"q": "ünïcode"})]
    )
    return event


def _adapter(
    scorer: Any, mocker: MockerFixture, mock_proposer: Any, events: list[Any]
) -> MultiAgentAdapter:
    """Build a two-agent adapter over a mocked executor.

    Args:
        scorer: Scorer under test.
        mocker: pytest-mock fixture.
        mock_proposer: Proposer fixture.
        events: Events the executor reports as captured.

    Returns:
        The configured MultiAgentAdapter.
    """
    executor = mocker.MagicMock()
    executor.execute_agent = mocker.AsyncMock(
        return_value=ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            extracted_value="final",
            session_id="s",
            error_message=None,
            captured_events=events,
        )
    )
    agents = {
        "generator": LlmAgent(
            name="generator", model="gemini-3.8-flash", instruction="g"
        ),
        "critic": LlmAgent(name="critic", model="gemini-3.8-flash", instruction="c"),
    }
    return MultiAgentAdapter(
        agents=agents,
        primary="generator",
        components={"generator": ["instruction"], "critic": []},
        scorer=scorer,
        proposer=mock_proposer,
        executor=executor,
    )


class TestMultiAgentAdapterPassesTrajectory:
    """The multi-agent adapter sends a trajectory only to declaring scorers.

    Non-declaring scorers are checked both through a mock and through a
    recording class that captures positional and keyword arguments.
    """

    async def test_declaring_scorer_receives_trajectory_without_capture_traces(
        self, mocker: MockerFixture, mock_proposer: Any
    ) -> None:
        """Tool calls reach the scorer while the batch carries no trajectories."""
        scorer = _TrajectoryScorer()
        events = [_tool_event(mocker, "ask_x"), _tool_event(mocker, "lookup")]
        adapter = _adapter(scorer, mocker, mock_proposer, events)

        batch = await adapter.evaluate(
            [{"input": "hi", "expected": "final"}],
            {"generator.instruction": "g"},
            capture_traces=False,
        )

        assert len(scorer.received) == 1
        trajectory = scorer.received[0]
        assert isinstance(trajectory, ADKTrajectory)
        assert [c.name for c in trajectory.tool_calls] == ["ask_x", "lookup"]
        assert trajectory.tool_calls[0].arguments == {"q": "ünïcode"}
        assert trajectory.final_output == "final"
        assert batch.trajectories is None
        assert batch.scores == [1.0]

    async def test_declaring_scorer_receives_trajectory_with_capture_traces(
        self, mocker: MockerFixture, mock_proposer: Any
    ) -> None:
        """With traces on, the scorer still gets a trajectory and the batch keeps its own."""
        scorer = _TrajectoryScorer()
        adapter = _adapter(
            scorer, mocker, mock_proposer, [_tool_event(mocker, "ask_x")]
        )

        batch = await adapter.evaluate(
            [{"input": "hi"}], {"generator.instruction": "g"}, capture_traces=True
        )

        assert batch.trajectories is not None
        assert len(batch.trajectories) == 1
        received = scorer.received[0]
        assert received is not None
        assert [c.name for c in received.tool_calls] == ["ask_x"]

    async def test_three_argument_scorer_is_called_unchanged(
        self, mocker: MockerFixture, mock_proposer: Any
    ) -> None:
        """A scorer without ``trajectory`` gets exactly three positional arguments."""
        scorer = mocker.MagicMock(spec=["score", "async_score"])
        scorer.async_score = mocker.AsyncMock(return_value=(0.5, {}))
        adapter = _adapter(
            scorer, mocker, mock_proposer, [_tool_event(mocker, "ask_x")]
        )

        batch = await adapter.evaluate(
            [{"input": "hi", "expected": "e"}],
            {"generator.instruction": "g"},
            capture_traces=False,
        )

        scorer.async_score.assert_awaited_once_with("hi", "final", "e")
        assert batch.scores == [0.5]

    async def test_three_argument_scorer_gets_no_trajectory_keyword(
        self, mocker: MockerFixture, mock_proposer: Any
    ) -> None:
        """A non-declaring scorer sees exactly (input, output, expected) and no keywords."""
        scorer = _ThreeArgScorer()
        adapter = _adapter(
            scorer, mocker, mock_proposer, [_tool_event(mocker, "ask_x")]
        )

        batch = await adapter.evaluate(
            [{"input": "hi", "expected": "e"}],
            {"generator.instruction": "g"},
            capture_traces=True,
        )

        assert scorer.calls == [(("hi", "final", "e"), {})]
        assert batch.scores == [0.25]

"""Acceptance tests for a Scorer that sees the trajectory.

A scorer whose ``async_score`` declares a ``trajectory`` parameter receives
the row's ``ADKTrajectory`` from the adapter on every evaluation, including
the valset pass that does not capture traces for the engine. A scorer with
the three-argument signature is called exactly as before. ``RequireToolScorer``
wraps an inner scorer and scores 0.0 when a named tool did not run.

Examples:
    ```bash
    uv run pytest tests/unit/adapters/test_trajectory_scorer.py -q
    ```

See Also:
    - [`gepa_adk.ports.scorer`][gepa_adk.ports.scorer]: ``scorer_accepts_trajectory``.
    - [`gepa_adk.adapters.scoring.require_tool`][gepa_adk.adapters.scoring.require_tool]:
        ``RequireToolScorer``.

Notes:
    The executor is mocked, so no agent or LLM runs.
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
from pytest_mock import MockerFixture

from gepa_adk.adapters import ADKAdapter
from gepa_adk.domain.trajectory import ADKTrajectory, ToolCallRecord
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

pytestmark = pytest.mark.unit


class TrajectoryScorer:
    """Scorer that declares a keyword-only ``trajectory`` parameter.

    Attributes:
        received (list[ADKTrajectory | None]): Trajectory passed on each call.
    """

    def __init__(self) -> None:
        """Start with no recorded trajectories."""
        self.received: list[ADKTrajectory | None] = []

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        *,
        trajectory: ADKTrajectory | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Record the trajectory and return a fixed synchronous score.

        Args:
            input_text: Input given to the agent.
            output: Agent output text.
            expected: Label from the row, if any.
            trajectory: Row trajectory from the caller, recorded.

        Returns:
            ``(1.0, {"sync": True})``.
        """
        self.received.append(trajectory)
        return 1.0, {"sync": True}

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        *,
        trajectory: ADKTrajectory | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Record the trajectory and return a fixed asynchronous score.

        Args:
            input_text: Input given to the agent.
            output: Agent output text.
            expected: Label from the row, if any.
            trajectory: Row trajectory from the adapter, recorded.

        Returns:
            ``(1.0, {"sync": False})``.
        """
        self.received.append(trajectory)
        return 1.0, {"sync": False}


class ThreeArgScorer:
    """Scorer with the pre-existing three-argument signature.

    Attributes:
        calls (list[tuple[str, str, str | None]]): Arguments of each call.
    """

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.calls: list[tuple[str, str, str | None]] = []

    def score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Record the three arguments and return a fixed score.

        Args:
            input_text: Input given to the agent.
            output: Agent output text.
            expected: Label from the row, if any.

        Returns:
            ``(0.5, {})``.
        """
        self.calls.append((input_text, output, expected))
        return 0.5, {}

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Record the three arguments and return a fixed score.

        Args:
            input_text: Input given to the agent.
            output: Agent output text.
            expected: Label from the row, if any.

        Returns:
            ``(0.5, {})``.
        """
        self.calls.append((input_text, output, expected))
        return 0.5, {}


def _tool_event(mocker: MockerFixture, name: str) -> Any:
    """Build a fake ADK event carrying one function call named ``name``.

    Args:
        mocker: pytest-mock fixture.
        name: Function call name.

    Returns:
        A mock event whose ``actions.function_calls`` holds one call.
    """
    from types import SimpleNamespace

    event = mocker.MagicMock()
    event.is_final_response = lambda: False
    event.actions = mocker.MagicMock(
        function_calls=[SimpleNamespace(name=name, args={"q": "ünïcode"})]
    )
    return event


def _adapter(
    scorer: Any, mocker: MockerFixture, mock_proposer: Any, events: list[Any]
) -> ADKAdapter:
    """Build an ADKAdapter over a mocked executor.

    Args:
        scorer: Scorer under test.
        mocker: pytest-mock fixture.
        mock_proposer: Proposer fixture.
        events: Events the executor reports as captured.

    Returns:
        The configured ADKAdapter.
    """
    executor = mocker.MagicMock()
    executor.execute_agent = mocker.AsyncMock(
        return_value=ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            extracted_value='{"label": "spam"}',
            session_id="s",
            error_message=None,
            captured_events=events,
        )
    )
    agent = LlmAgent(name="a", model="gemini-3.8-flash", instruction="i")
    return ADKAdapter(
        agent=agent, scorer=scorer, executor=executor, proposer=mock_proposer
    )


class TestAdapterPassesTrajectory:
    """The adapter sends the trajectory only to scorers that declare it."""

    async def test_declaring_scorer_receives_trajectory_without_capture_traces(
        self, mocker: MockerFixture, mock_proposer: Any
    ) -> None:
        """A declaring scorer sees tool calls on the valset-style pass without traces."""
        scorer = TrajectoryScorer()
        adapter = _adapter(
            scorer, mocker, mock_proposer, [_tool_event(mocker, "ask_x")]
        )

        batch = await adapter.evaluate(
            [{"input": "hi", "expected": "spam"}],
            {"instruction": "i"},
            capture_traces=False,
        )

        assert len(scorer.received) == 1
        trajectory = scorer.received[0]
        assert isinstance(trajectory, ADKTrajectory)
        assert [c.name for c in trajectory.tool_calls] == ["ask_x"]
        assert trajectory.tool_calls[0].arguments == {"q": "ünïcode"}
        assert trajectory.final_output == '{"label": "spam"}'
        # The engine contract is unchanged: no trajectories on the batch.
        assert batch.trajectories is None
        assert batch.scores == [1.0]

    async def test_declaring_scorer_receives_trajectory_with_capture_traces(
        self, mocker: MockerFixture, mock_proposer: Any
    ) -> None:
        """With traces on, the scorer receives the same trajectory the batch carries."""
        scorer = TrajectoryScorer()
        adapter = _adapter(
            scorer, mocker, mock_proposer, [_tool_event(mocker, "ask_x")]
        )

        batch = await adapter.evaluate(
            [{"input": "hi"}], {"instruction": "i"}, capture_traces=True
        )

        assert batch.trajectories is not None
        assert len(batch.trajectories) == 1
        assert scorer.received == [batch.trajectories[0]]

    async def test_three_argument_scorer_is_called_unchanged(
        self, mocker: MockerFixture, mock_proposer: Any
    ) -> None:
        """A three-argument scorer is called positionally, without ``trajectory``."""
        scorer = ThreeArgScorer()
        adapter = _adapter(
            scorer, mocker, mock_proposer, [_tool_event(mocker, "ask_x")]
        )

        batch = await adapter.evaluate(
            [{"input": "hi", "expected": "spam"}],
            {"instruction": "i"},
            capture_traces=True,
        )

        assert scorer.calls == [("hi", '{"label": "spam"}', "spam")]
        assert batch.scores == [0.5]


class TestRequireToolScorer:
    """RequireToolScorer scores 0.0 when the named tool did not run."""

    @staticmethod
    def _trajectory(*names: str) -> ADKTrajectory:
        """Build a trajectory with one tool call per name.

        Args:
            *names: Tool call names in order.

        Returns:
            An ADKTrajectory carrying the tool calls.
        """
        return ADKTrajectory(
            tool_calls=tuple(
                ToolCallRecord(name=n, arguments={}, result=None, timestamp=0.0)
                for n in names
            ),
            state_deltas=(),
            token_usage=None,
            final_output='{"label": "spam"}',
            error=None,
        )

    def test_exported_from_root_and_scoring(self) -> None:
        """The root, adapters and scoring exports are one class."""
        from gepa_adk import RequireToolScorer as Root
        from gepa_adk.adapters import RequireToolScorer as Adapters
        from gepa_adk.adapters.scoring import RequireToolScorer

        assert Root is RequireToolScorer
        assert Adapters is RequireToolScorer

    def test_satisfies_scorer_protocol(self) -> None:
        """The wrapper satisfies the runtime-checkable Scorer protocol."""
        from gepa_adk import LabelAgreementScorer, RequireToolScorer, Scorer

        scorer = RequireToolScorer(LabelAgreementScorer(field="label"), tool="ask_x")
        assert isinstance(scorer, Scorer)

    @pytest.mark.parametrize("tool", ["", "   "])
    def test_rejects_blank_tool_name(self, tool: str) -> None:
        """A blank tool name is a ValueError naming ``tool``."""
        from gepa_adk import LabelAgreementScorer, RequireToolScorer

        with pytest.raises(ValueError, match="tool"):
            RequireToolScorer(LabelAgreementScorer(), tool=tool)

    async def test_scores_zero_when_tool_absent(self) -> None:
        """A trajectory without the tool scores 0.0 with ``tool_not_called``."""
        from gepa_adk import LabelAgreementScorer, RequireToolScorer

        scorer = RequireToolScorer(LabelAgreementScorer(field="label"), tool="ask_x")
        score, metadata = await scorer.async_score(
            "hi", '{"label": "spam"}', "spam", trajectory=self._trajectory("other_tool")
        )

        assert score == 0.0
        assert metadata["reason"] == "tool_not_called"
        assert metadata["required_tool"] == "ask_x"
        assert metadata["tool_called"] is False

    async def test_scores_zero_when_trajectory_missing(self) -> None:
        """No trajectory scores 0.0 with ``trajectory_unavailable``."""
        from gepa_adk import LabelAgreementScorer, RequireToolScorer

        scorer = RequireToolScorer(LabelAgreementScorer(field="label"), tool="ask_x")
        score, metadata = await scorer.async_score("hi", '{"label": "spam"}', "spam")

        assert score == 0.0
        assert metadata["reason"] == "trajectory_unavailable"
        assert metadata["tool_called"] is False

    async def test_delegates_when_tool_present(self) -> None:
        """With the tool present, the inner score and metadata come through."""
        from gepa_adk import LabelAgreementScorer, RequireToolScorer

        scorer = RequireToolScorer(LabelAgreementScorer(field="label"), tool="ask_x")
        score, metadata = await scorer.async_score(
            "hi",
            '{"label": "spam"}',
            "spam",
            trajectory=self._trajectory("ask_ÿ", "ask_x"),
        )

        assert score == 1.0
        assert metadata["agreement"] is True
        assert metadata["required_tool"] == "ask_x"
        assert metadata["tool_called"] is True

    async def test_forwards_trajectory_to_inner_that_declares_it(self) -> None:
        """An inner scorer that declares ``trajectory`` receives it."""
        from gepa_adk import RequireToolScorer

        inner = TrajectoryScorer()
        scorer = RequireToolScorer(inner, tool="ask_x")
        trajectory = self._trajectory("ask_x")

        await scorer.async_score("hi", "out", None, trajectory=trajectory)
        scorer.score("hi", "out", None, trajectory=trajectory)

        assert inner.received == [trajectory, trajectory]

    def test_sync_matches_async(self) -> None:
        """The synchronous method gates the same way as the async one."""
        from gepa_adk import LabelAgreementScorer, RequireToolScorer

        scorer = RequireToolScorer(LabelAgreementScorer(field="label"), tool="ask_x")
        missing = scorer.score(
            "hi", '{"label": "spam"}', "spam", trajectory=self._trajectory()
        )
        present = scorer.score(
            "hi", '{"label": "spam"}', "spam", trajectory=self._trajectory("ask_x")
        )

        assert missing[0] == 0.0
        assert missing[1]["reason"] == "tool_not_called"
        assert present[0] == 1.0

    async def test_end_to_end_through_adapter(
        self, mocker: MockerFixture, mock_proposer: Any
    ) -> None:
        """Through the adapter, a run without the tool scores 0.0."""
        from gepa_adk import LabelAgreementScorer, RequireToolScorer

        scorer = RequireToolScorer(LabelAgreementScorer(field="label"), tool="ask_x")
        adapter = _adapter(
            scorer, mocker, mock_proposer, [_tool_event(mocker, "lookup")]
        )

        batch = await adapter.evaluate(
            [{"input": "hi", "expected": "spam"}],
            {"instruction": "i"},
            capture_traces=False,
        )

        assert batch.scores == [0.0]
        assert batch.metadata[0]["reason"] == "tool_not_called"

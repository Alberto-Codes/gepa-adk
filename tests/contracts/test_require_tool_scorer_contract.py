"""Contract tests for RequireToolScorer protocol compliance.

These tests ensure RequireToolScorer satisfies the Scorer protocol, declares
the optional ``trajectory`` parameter the adapters detect, validates its
constructor arguments, wraps a bare-float inner result, and forwards
``trajectory`` to each inner method only when that method declares it.

Examples:
    ```bash
    uv run pytest tests/contracts/test_require_tool_scorer_contract.py -q
    ```

See Also:
    - [`gepa_adk.adapters.scoring.require_tool`][gepa_adk.adapters.scoring.require_tool]:
        Module under test.

Notes:
    The scorer is pure Python, so no agents or LLM calls are needed.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from gepa_adk.adapters.scoring import LabelAgreementScorer, RequireToolScorer
from gepa_adk.domain.trajectory import ADKTrajectory, ToolCallRecord
from gepa_adk.ports.scorer import Scorer, scorer_accepts_trajectory

pytestmark = pytest.mark.contract


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
        final_output="",
        error=None,
    )


class _FloatScorer:
    """Inner scorer that returns a bare float."""

    def score(self, input_text: str, output: str, expected: str | None = None) -> Any:
        """Return a bare float.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.

        Returns:
            The float 0.75.
        """
        return 0.75

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> Any:
        """Return a bare float.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.

        Returns:
            The float 0.75.
        """
        return 0.75


class TestRequireToolScorerContract:
    """Protocol compliance and constructor validation."""

    def test_is_runtime_checkable_scorer(self) -> None:
        """The wrapper satisfies the Scorer protocol at runtime."""
        assert isinstance(RequireToolScorer(LabelAgreementScorer(), tool="t"), Scorer)

    def test_declares_trajectory(self) -> None:
        """The adapters detect the wrapper as trajectory-aware."""
        scorer = RequireToolScorer(LabelAgreementScorer(), tool="t")
        assert scorer_accepts_trajectory(scorer) is True

    @pytest.mark.parametrize("method", ["score", "async_score"])
    def test_method_signature(self, method: str) -> None:
        """Both methods take the three protocol arguments plus keyword-only trajectory."""
        sig = inspect.signature(
            getattr(RequireToolScorer(LabelAgreementScorer(), tool="t"), method)
        )
        params = sig.parameters
        assert list(params) == ["input_text", "output", "expected", "trajectory"]
        assert params["expected"].default is None
        assert params["trajectory"].kind is inspect.Parameter.KEYWORD_ONLY
        assert params["trajectory"].default is None

    def test_async_score_is_coroutine_function(self) -> None:
        """The async method must be awaitable."""
        scorer = RequireToolScorer(LabelAgreementScorer(), tool="t")
        assert inspect.iscoroutinefunction(scorer.async_score)

    def test_stores_inner_and_tool(self) -> None:
        """The constructor keeps both arguments as public attributes."""
        inner = LabelAgreementScorer()
        scorer = RequireToolScorer(inner, tool="ask_x")
        assert scorer.inner is inner
        assert scorer.tool == "ask_x"

    def test_rejects_non_string_tool(self) -> None:
        """A non-string tool name is a ValueError naming ``tool``."""
        with pytest.raises(ValueError, match="tool"):
            RequireToolScorer(LabelAgreementScorer(), tool=None)

    def test_rejects_inner_without_scorer_methods(self) -> None:
        """An inner object lacking the protocol methods is a TypeError."""
        with pytest.raises(TypeError, match="inner"):
            RequireToolScorer(object(), tool="t")


class TestRequireToolScorerBehavior:
    """Return shape across the three outcomes."""

    async def test_bare_float_inner_is_wrapped(self) -> None:
        """A bare-float inner result becomes (float, metadata) with tool keys."""
        scorer = RequireToolScorer(_FloatScorer(), tool="t")

        async_result = await scorer.async_score("q", "o", trajectory=_trajectory("t"))
        sync_result = scorer.score("q", "o", trajectory=_trajectory("t"))

        expected = (0.75, {"required_tool": "t", "tool_called": True})
        assert async_result == expected
        assert sync_result == expected

    @pytest.mark.parametrize(
        ("trajectory", "reason"),
        [(None, "trajectory_unavailable"), (_trajectory(), "tool_not_called")],
    )
    def test_zero_results_carry_exact_metadata(
        self, trajectory: ADKTrajectory | None, reason: str
    ) -> None:
        """Failed gates return 0.0 and exactly three metadata keys."""
        scorer = RequireToolScorer(LabelAgreementScorer(), tool="t")

        result = scorer.score("q", "o", "o", trajectory=trajectory)

        assert result == (
            0.0,
            {"reason": reason, "required_tool": "t", "tool_called": False},
        )

    def test_inner_metadata_is_not_mutated(self) -> None:
        """The wrapper copies the inner metadata before adding its keys."""
        shared: dict[str, Any] = {"k": 1}

        class _Shared:
            """Inner scorer returning the same metadata dict every call."""

            def score(self, *args: Any) -> tuple[float, dict[str, Any]]:
                """Return the shared metadata.

                Args:
                    *args: Unused.

                Returns:
                    A score of 1.0 with the shared dict.
                """
                return 1.0, shared

            async def async_score(self, *args: Any) -> tuple[float, dict[str, Any]]:
                """Return the shared metadata.

                Args:
                    *args: Unused.

                Returns:
                    A score of 1.0 with the shared dict.
                """
                return 1.0, shared

        scorer = RequireToolScorer(_Shared(), tool="t")
        score, metadata = scorer.score("q", "o", trajectory=_trajectory("t"))

        assert score == 1.0
        assert metadata == {"k": 1, "required_tool": "t", "tool_called": True}
        assert shared == {"k": 1}


class _AsyncOnlyTrajectory:
    """Inner scorer declaring ``trajectory`` only on ``async_score``.

    Attributes:
        received (list[Any]): Trajectories passed to ``async_score``.
    """

    def __init__(self) -> None:
        """Start with no recorded trajectories."""
        self.received: list[Any] = []

    def score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Return a fixed score without a trajectory parameter.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.

        Returns:
            ``(1.0, {"path": "sync"})``.
        """
        return 1.0, {"path": "sync"}

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        *,
        trajectory: Any = None,
    ) -> tuple[float, dict[str, Any]]:
        """Record the trajectory and return a fixed score.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.
            trajectory: Recorded.

        Returns:
            ``(1.0, {"path": "async"})``.
        """
        self.received.append(trajectory)
        return 1.0, {"path": "async"}


class _SyncOnlyTrajectory:
    """Inner scorer declaring ``trajectory`` only on ``score``.

    Attributes:
        received (list[Any]): Trajectories passed to ``score``.
    """

    def __init__(self) -> None:
        """Start with no recorded trajectories."""
        self.received: list[Any] = []

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        *,
        trajectory: Any = None,
    ) -> tuple[float, dict[str, Any]]:
        """Record the trajectory and return a fixed score.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.
            trajectory: Recorded.

        Returns:
            ``(1.0, {})``.
        """
        self.received.append(trajectory)
        return 1.0, {}

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Return a fixed score without a trajectory parameter.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.

        Returns:
            ``(1.0, {})``.
        """
        return 1.0, {}


class TestRequireToolScorerPerMethodForwarding:
    """Sync and async paths inspect their own inner method."""

    async def test_async_only_declaration_does_not_break_sync_score(self) -> None:
        """Sync ``score`` calls the three-argument inner ``score`` without error."""
        inner = _AsyncOnlyTrajectory()
        scorer = RequireToolScorer(inner, tool="t")
        trajectory = _trajectory("t")

        sync_score, sync_meta = scorer.score("q", "o", trajectory=trajectory)
        await scorer.async_score("q", "o", trajectory=trajectory)

        assert sync_score == 1.0
        assert sync_meta["path"] == "sync"
        assert inner.received == [trajectory]

    async def test_sync_only_declaration_receives_trajectory_in_score(self) -> None:
        """An inner ``score`` declaring ``trajectory`` receives it; async does not raise."""
        inner = _SyncOnlyTrajectory()
        scorer = RequireToolScorer(inner, tool="t")
        trajectory = _trajectory("t")

        scorer.score("q", "o", trajectory=trajectory)
        async_score, _ = await scorer.async_score("q", "o", trajectory=trajectory)

        assert inner.received == [trajectory]
        assert async_score == 1.0

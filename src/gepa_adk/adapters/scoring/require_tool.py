"""Scorer wrapper that requires a named tool to appear in the trajectory.

This module provides ``RequireToolScorer``, which wraps another ``Scorer``
and scores 0.0 unless the agent called a named tool during the row's run.
It declares the optional ``trajectory`` parameter, so the evolution adapters
send it the row's ``ADKTrajectory`` on every evaluation.

Attributes:
    RequireToolScorer (class): Scores 0.0 when the required tool did not run,
        otherwise delegates to the wrapped scorer.

Examples:
    Require a lookup tool before a label counts:

    ```python
    from gepa_adk.adapters.scoring import LabelAgreementScorer, RequireToolScorer

    scorer = RequireToolScorer(LabelAgreementScorer(field="label"), tool="ask_x")
    ```

See Also:
    - [`gepa_adk.ports.scorer`][gepa_adk.ports.scorer]: Protocol that
        RequireToolScorer implements, and ``scorer_accepts_trajectory``.
    - [`gepa_adk.adapters.scoring.label_agreement`][gepa_adk.adapters.scoring.label_agreement]:
        Deterministic scorer commonly wrapped by RequireToolScorer.

Notes:
    The tool check compares ``ToolCallRecord.name`` with the required name
    exactly. A row scored without a trajectory scores 0.0 with
    ``metadata["reason"] == "trajectory_unavailable"``. The inner scorer's
    ``score`` and ``async_score`` are inspected separately, and each receives
    ``trajectory=`` only when it declares that parameter by keyword.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from gepa_adk.ports.scorer import scorer_accepts_trajectory

if TYPE_CHECKING:
    from gepa_adk.domain.trajectory import ADKTrajectory
    from gepa_adk.ports.scorer import Scorer

__all__ = ["RequireToolScorer"]


def _method_accepts_trajectory(method: Any) -> bool:
    """Report whether one scorer method takes ``trajectory`` by keyword.

    Args:
        method: Bound ``score`` or ``async_score`` method.

    Returns:
        True when the method has a positional-or-keyword or keyword-only
        parameter named ``trajectory``, else False, including when its
        signature cannot be read.
    """
    try:
        parameter = inspect.signature(method).parameters.get("trajectory")
    except (TypeError, ValueError):
        return False
    return parameter is not None and parameter.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    )


class RequireToolScorer:
    """Scorer that gates an inner scorer on a required tool call.

    Attributes:
        inner (Scorer): Wrapped scorer consulted when the tool ran.
        tool (str): Name of the tool that must appear in the trajectory.

    Examples:
        ```python
        from gepa_adk import LabelAgreementScorer, RequireToolScorer, evolve

        scorer = RequireToolScorer(LabelAgreementScorer(field="label"), tool="ask_x")
        result = await evolve(agent, trainset, scorer=scorer)
        ```

    Notes:
        Adheres to the Scorer protocol. Metadata always carries
        ``required_tool`` and ``tool_called``. The score is 0.0 with
        ``metadata["reason"]`` set to ``"trajectory_unavailable"`` when no
        trajectory was given and ``"tool_not_called"`` when the tool is
        absent. Otherwise the inner scorer's score and metadata are returned.
    """

    def __init__(self, inner: Scorer, tool: str) -> None:
        """Store the wrapped scorer and the required tool name.

        Args:
            inner: Scorer to delegate to when the tool ran.
            tool: Name of the tool that must appear in the trajectory.

        Raises:
            ValueError: If ``tool`` is not a non-blank string.
            TypeError: If ``inner`` lacks ``score`` or ``async_score``.

        Notes:
            Records separately whether ``inner.score`` and
            ``inner.async_score`` accept ``trajectory`` by keyword.
        """
        if not isinstance(tool, str) or not tool.strip():
            raise ValueError(f"tool must be a non-blank string, got {tool!r}")
        if not hasattr(inner, "score") or not hasattr(inner, "async_score"):
            raise TypeError(
                f"inner must implement the Scorer protocol, got {type(inner)}"
            )
        self.inner = inner
        self.tool = tool
        # Each method is inspected separately: an inner scorer may declare
        # ``trajectory`` on one and not the other.
        self._inner_async_accepts_trajectory = scorer_accepts_trajectory(inner)
        self._inner_sync_accepts_trajectory = _method_accepts_trajectory(inner.score)

    def _gate(
        self, trajectory: ADKTrajectory | None
    ) -> tuple[float, dict[str, Any]] | None:
        """Return the zero result when the tool check fails.

        Args:
            trajectory: Row trajectory, or ``None`` when unavailable.

        Returns:
            ``(0.0, metadata)`` when the trajectory is missing or lacks the
            tool, else ``None`` to signal delegation.
        """
        if trajectory is None:
            reason = "trajectory_unavailable"
        elif any(call.name == self.tool for call in trajectory.tool_calls):
            return None
        else:
            reason = "tool_not_called"
        return 0.0, {
            "reason": reason,
            "required_tool": self.tool,
            "tool_called": False,
        }

    def _merge(self, result: Any) -> tuple[float, dict[str, Any]]:
        """Attach the tool metadata to the inner scorer's result.

        Args:
            result: Inner result, either ``(score, metadata)`` or a bare float.

        Returns:
            The inner score with its metadata plus ``required_tool`` and
            ``tool_called``.
        """
        if isinstance(result, tuple):
            score, metadata = result[0], dict(result[1] or {})
        else:
            score, metadata = float(result), {}
        metadata["required_tool"] = self.tool
        metadata["tool_called"] = True
        return score, metadata

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        *,
        trajectory: ADKTrajectory | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score synchronously, requiring the tool before delegating.

        Args:
            input_text: Input given to the agent.
            output: Agent output text.
            expected: Label from the trainset row, if any.
            trajectory: Row trajectory from the adapter, if available.

        Returns:
            ``(0.0, metadata)`` when the tool did not run, else the inner
            scorer's result with the tool metadata added.

        Notes:
            Forwards ``trajectory`` only when the corresponding inner method
            declares it.
        """
        gated = self._gate(trajectory)
        if gated is not None:
            return gated
        if self._inner_sync_accepts_trajectory:
            # The Scorer protocol omits ``trajectory``; the inner scorer
            # declared it, so call through an untyped reference.
            inner: Any = self.inner
            result = inner.score(input_text, output, expected, trajectory=trajectory)
        else:
            result = self.inner.score(input_text, output, expected)
        return self._merge(result)

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        *,
        trajectory: ADKTrajectory | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score asynchronously, requiring the tool before delegating.

        Args:
            input_text: Input given to the agent.
            output: Agent output text.
            expected: Label from the trainset row, if any.
            trajectory: Row trajectory from the adapter, if available.

        Returns:
            ``(0.0, metadata)`` when the tool did not run, else the inner
            scorer's result with the tool metadata added.

        Notes:
            Forwards ``trajectory`` only when the corresponding inner method
            declares it.
        """
        gated = self._gate(trajectory)
        if gated is not None:
            return gated
        if self._inner_async_accepts_trajectory:
            # The Scorer protocol omits ``trajectory``; the inner scorer
            # declared it, so call through an untyped reference.
            inner: Any = self.inner
            result = await inner.async_score(
                input_text, output, expected, trajectory=trajectory
            )
        else:
            result = await self.inner.async_score(input_text, output, expected)
        return self._merge(result)

"""Unit tests for ``scorer_accepts_trajectory``.

The adapters send the row's trajectory only to a scorer whose
``async_score`` declares a parameter named ``trajectory`` that can be passed
by keyword. A ``**kwargs`` catch-all, a positional-only ``trajectory`` and a
``**trajectory`` catch-all do not count.

Examples:
    ```bash
    uv run pytest tests/unit/ports/test_scorer_accepts_trajectory.py -q
    ```

See Also:
    - [`gepa_adk.ports.scorer`][gepa_adk.ports.scorer]: Module under test.

Notes:
    Pure signature inspection; no agents or LLM calls.
"""

from __future__ import annotations

from typing import Any

import pytest

from gepa_adk.ports.scorer import scorer_accepts_trajectory

pytestmark = pytest.mark.unit


class _KeywordOnly:
    """Scorer declaring a keyword-only ``trajectory``."""

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        *,
        trajectory: Any = None,
    ) -> tuple[float, dict[str, Any]]:
        """Return a fixed score.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.
            trajectory: Unused.

        Returns:
            A zero score with empty metadata.
        """
        return 0.0, {}


class _Positional:
    """Scorer declaring ``trajectory`` as a positional-or-keyword parameter."""

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        trajectory: Any = None,
    ) -> tuple[float, dict[str, Any]]:
        """Return a fixed score.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.
            trajectory: Unused.

        Returns:
            A zero score with empty metadata.
        """
        return 0.0, {}


class _ThreeArg:
    """Scorer with the three-argument signature."""

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Return a fixed score.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.

        Returns:
            A zero score with empty metadata.
        """
        return 0.0, {}


class _KwargsOnly:
    """Scorer whose only catch-all is ``**kwargs``."""

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        **kwargs: Any,
    ) -> tuple[float, dict[str, Any]]:
        """Return a fixed score.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.
            **kwargs: Unused.

        Returns:
            A zero score with empty metadata.
        """
        return 0.0, {}


class _PositionalOnly:
    """Scorer whose ``trajectory`` is positional-only."""

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        trajectory: Any = None,
        /,
    ) -> tuple[float, dict[str, Any]]:
        """Return a fixed score.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.
            trajectory: Unused.

        Returns:
            A zero score with empty metadata.
        """
        return 0.0, {}


class _VarKeywordNamedTrajectory:
    """Scorer whose catch-all is spelled ``**trajectory``."""

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        **trajectory: Any,
    ) -> tuple[float, dict[str, Any]]:
        """Return a fixed score.

        Args:
            input_text: Unused.
            output: Unused.
            expected: Unused.
            **trajectory: Unused.

        Returns:
            A zero score with empty metadata.
        """
        return 0.0, {}


class TestScorerAcceptsTrajectory:
    """Signature detection for the optional ``trajectory`` parameter, by kind."""

    def test_true_for_keyword_only_trajectory(self) -> None:
        """A keyword-only ``trajectory`` counts."""
        assert scorer_accepts_trajectory(_KeywordOnly()) is True

    def test_true_for_positional_trajectory(self) -> None:
        """A positional-or-keyword ``trajectory`` also counts."""
        assert scorer_accepts_trajectory(_Positional()) is True

    def test_false_for_three_argument_signature(self) -> None:
        """The pre-existing signature does not receive a trajectory."""
        assert scorer_accepts_trajectory(_ThreeArg()) is False

    def test_false_for_kwargs_only(self) -> None:
        """A ``**kwargs`` catch-all is not a declaration."""
        assert scorer_accepts_trajectory(_KwargsOnly()) is False

    def test_false_for_positional_only_trajectory(self) -> None:
        """A positional-only ``trajectory`` cannot be passed by keyword."""
        assert scorer_accepts_trajectory(_PositionalOnly()) is False

    def test_false_for_var_keyword_named_trajectory(self) -> None:
        """A ``**trajectory`` catch-all is not a declaration."""
        assert scorer_accepts_trajectory(_VarKeywordNamedTrajectory()) is False

    def test_false_without_async_score(self) -> None:
        """An object with no ``async_score`` does not accept a trajectory."""
        assert scorer_accepts_trajectory(object()) is False

    def test_false_for_uninspectable_callable(self) -> None:
        """A callable whose signature cannot be read does not count."""

        class _BadSignature:
            """Callable whose ``__signature__`` is not a Signature."""

            __signature__ = "not a signature"

            def __call__(self) -> None:
                """Do nothing."""

        class _Holder:
            """Scorer-like holder whose ``async_score`` cannot be inspected."""

            async_score = _BadSignature()

        assert scorer_accepts_trajectory(_Holder()) is False

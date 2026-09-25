"""Unit tests for validating the proposer's reflection retry backoff.

``AsyncReflectiveMutationProposer`` takes ``retry_backoff_seconds``, the
wait before retrying a retryable reflection error. It must be a finite,
non-negative int or float; anything else raises ``ValueError`` at
construction.

Examples:
    Run these tests on their own:

    ```bash
    uv run pytest tests/unit/engine/test_proposer_backoff.py -q
    ```

See Also:
    - [`gepa_adk.engine.proposer`][gepa_adk.engine.proposer]: The proposer
      that validates and applies the backoff.
"""

from __future__ import annotations

from typing import Any

import pytest

from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

pytestmark = pytest.mark.unit


async def _reflect(
    component_text: str, trials: list[dict[str, Any]], component: str
) -> tuple[str, str | None]:
    """Return a fixed proposal.

    Args:
        component_text: Current text (unused).
        trials: Trial records (unused).
        component: Component name (unused).

    Returns:
        A fixed proposal and no reasoning.
    """
    return "Better", None


class TestRetryBackoffValidation:
    """The backoff must be a finite, non-negative number."""

    @pytest.mark.parametrize("value", [0, 0.0, 1, 2.5])
    def test_accepts_non_negative_numbers(self, value: float) -> None:
        """Zero and positive ints and floats are stored as given."""
        proposer = AsyncReflectiveMutationProposer(
            adk_reflection_fn=_reflect, retry_backoff_seconds=value
        )

        assert proposer.retry_backoff_seconds == value

    @pytest.mark.parametrize(
        "value", [-1, -0.5, True, False, "2", None, float("nan"), float("inf")]
    )
    def test_rejects_invalid_values(self, value: Any) -> None:
        """Negative, boolean, non-numeric and non-finite values raise."""
        with pytest.raises(ValueError, match="retry_backoff_seconds"):
            AsyncReflectiveMutationProposer(
                adk_reflection_fn=_reflect, retry_backoff_seconds=value
            )

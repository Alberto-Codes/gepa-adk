"""Protocol definition for candidate selection strategies."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gepa_adk.domain.state import ParetoState


@runtime_checkable
class CandidateSelectorProtocol(Protocol):
    """Async protocol for candidate selection strategies."""

    async def select_candidate(self, state: ParetoState) -> int:
        """Select a candidate index for mutation.

        Args:
            state: Current evolution state with Pareto frontier tracking.

        Returns:
            Index of selected candidate.

        Raises:
            NoCandidateAvailableError: If state has no candidates.
        """
        ...

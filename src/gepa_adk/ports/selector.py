"""Protocol definition for candidate selection strategies.

Note:
    This module defines the async contract for candidate selection strategies.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gepa_adk.domain.state import ParetoState


@runtime_checkable
class CandidateSelectorProtocol(Protocol):
    """Async protocol for candidate selection strategies.

    Note:
        A selector protocol standardizes how candidates are chosen for mutation.

    Examples:
        ```python
        class Selector:
            async def select_candidate(self, state: ParetoState) -> int:
                return 0
        ```
    """

    async def select_candidate(self, state: ParetoState) -> int:
        """Select a candidate index for mutation.

        Args:
            state: Current evolution state with Pareto frontier tracking.

        Returns:
            Index of selected candidate.

        Raises:
            NoCandidateAvailableError: If state has no candidates.

        Examples:
            ```python
            candidate_idx = await selector.select_candidate(state)
            ```
        """
        ...


@runtime_checkable
class ComponentSelectorProtocol(Protocol):
    """Async protocol for component selection strategies.

    Note:
        A selector protocol standardizes how components are chosen for update.

    Examples:
        ```python
        class MySelector:
            async def select_components(
                self, components: list[str], iteration: int, candidate_idx: int
            ) -> list[str]:
                return components[:1]
        ```
    """

    async def select_components(
        self, components: list[str], iteration: int, candidate_idx: int
    ) -> list[str]:
        """Select components to update for the current iteration.

        Args:
            components: List of available component keys (e.g. ["instruction", "input_schema"]).
            iteration: Current global iteration number (0-based).
            candidate_idx: Index of the candidate being evolved.

        Returns:
            List of component keys to update.

        Raises:
            ValueError: If components list is empty.

        Examples:
            ```python
            selected = await selector.select_components(
                components=["instruction", "schema"], iteration=1, candidate_idx=0
            )
            ```
        """
        ...

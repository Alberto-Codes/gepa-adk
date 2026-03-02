"""Adapter implementations for component selection strategies.

This module provides concrete implementations of the ComponentSelectorProtocol,
allowing different strategies for selecting which components of a candidate
to update during evolution.

Attributes:
    RoundRobinComponentSelector (class): Cycles through components sequentially.
    AllComponentSelector (class): Selects all components every time.

Examples:
    Creating a selector via factory:

    ```python
    from gepa_adk.adapters.component_selector import create_component_selector

    selector = create_component_selector("round_robin")
    ```

    Using a selector directly:

    ```python
    from gepa_adk.adapters.component_selector import AllComponentSelector

    selector = AllComponentSelector()
    components = await selector.select_components(["a", "b"], 1, 0)
    ```

Note:
    These adapters implement component selection strategies that may maintain
    internal state for cycling (like RoundRobin) while remaining stateless with
    respect to the engine.
"""

from collections import defaultdict

from gepa_adk.ports.component_selector import ComponentSelectorProtocol


class RoundRobinComponentSelector:
    """Selects components in a round-robin fashion.

    This selector cycles through the list of components one by one, maintaining
    state per candidate index to ensure consistent rotation.

    Attributes:
        _next_index (dict[int, int]): Mapping of candidate_idx to next component index.

    Examples:
        ```python
        selector = RoundRobinComponentSelector()
        # First call selects first component
        c1 = await selector.select_components(["a", "b"], 1, 0)  # ["a"]
        # Second call selects second component
        c2 = await selector.select_components(["a", "b"], 2, 0)  # ["b"]
        ```

    Note:
        Alternates through components sequentially, ensuring balanced evolution
        across all candidate parts.
    """

    def __init__(self) -> None:
        """Initialize the round-robin selector.

        Note:
            Creates empty index tracking dictionary for per-candidate rotation state.
        """
        self._next_index: dict[int, int] = defaultdict(int)

    async def select_components(
        self, components: list[str], iteration: int, candidate_idx: int
    ) -> list[str]:
        """Select a single component to update using round-robin logic.

        Args:
            components: List of available component keys.
            iteration: Current global iteration number (unused by this strategy).
            candidate_idx: Index of the candidate being evolved.

        Returns:
            List containing the single selected component key.

        Raises:
            ValueError: If components list is empty.

        Examples:
            ```python
            selected = await selector.select_components(["a", "b"], 1, 0)
            ```

        Note:
            Outputs one component per call, advancing the rotation index for
            the specified candidate.
        """
        if not components:
            raise ValueError("No components provided for selection")

        # Get current index for this candidate
        current_idx = self._next_index[candidate_idx]

        # Select component
        selected = components[current_idx % len(components)]

        # Advance index for next time
        self._next_index[candidate_idx] = (current_idx + 1) % len(components)

        return [selected]


class AllComponentSelector:
    """Selects all available components for simultaneous update.

    This selector returns the full list of components every time, enabling
    simultaneous evolution of all parts of the candidate.

    Examples:
        ```python
        selector = AllComponentSelector()
        all_comps = await selector.select_components(["a", "b"], 1, 0)
        # Returns ["a", "b"]
        ```

    Note:
        Always returns all components, enabling comprehensive mutations
        across the entire candidate in a single iteration.
    """

    async def select_components(
        self, components: list[str], iteration: int, candidate_idx: int
    ) -> list[str]:
        """Select all components to update.

        Args:
            components: List of available component keys.
            iteration: Current global iteration number (unused).
            candidate_idx: Index of the candidate being evolved (unused).

        Returns:
            List containing all component keys.

        Raises:
            ValueError: If components list is empty.

        Examples:
            ```python
            selected = await selector.select_components(["a", "b"], 1, 0)
            ```

        Note:
            Outputs the complete component list unchanged, enabling
            simultaneous evolution of all candidate parts.
        """
        if not components:
            raise ValueError("No components provided for selection")

        return list(components)


def create_component_selector(selector_type: str) -> ComponentSelectorProtocol:
    """Create a component selector strategy from a string alias.

    Args:
        selector_type: Name of the selector strategy.
            Supported values:
            - 'round_robin', 'roundrobin': Round-robin cycling.
            - 'all', 'all_components': All components simultaneously.

    Returns:
        Instance of requested component selector.

    Raises:
        ValueError: If selector_type is unknown.

    Examples:
        ```python
        # Create round-robin selector
        selector = create_component_selector("round_robin")

        # Create all-components selector
        selector = create_component_selector("all")
        ```

    Note:
        Supports flexible string aliases with normalization for common
        variations (underscores, hyphens, case-insensitive).
    """
    normalized = selector_type.lower().replace("_", "").replace("-", "")

    if normalized == "roundrobin":
        return RoundRobinComponentSelector()
    elif normalized in ("all", "allcomponents"):
        return AllComponentSelector()

    raise ValueError(f"Unknown component selector: {selector_type}")


__all__ = [
    "RoundRobinComponentSelector",
    "AllComponentSelector",
    "create_component_selector",
]

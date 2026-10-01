"""Adapter implementations for component selection strategies.

This module provides concrete implementations of the ComponentSelectorProtocol,
allowing different strategies for selecting which components of a candidate
to update during evolution.

Attributes:
    RoundRobinComponentSelector (class): Cycles through components sequentially.
        Defined in `gepa_adk.ports.defaults` and re-exported here.
    AllComponentSelector (class): Selects all components every time.
    create_component_selector (function): Create a component selector strategy from a
        string alias.

Examples:
    Creating a selector via factory:

    ```python
    from gepa_adk.adapters.selection.component_selector import create_component_selector

    selector = create_component_selector("round_robin")
    ```

    Using a selector directly:

    ```python
    from gepa_adk.adapters.selection.component_selector import AllComponentSelector

    selector = AllComponentSelector()
    components = await selector.select_components(["a", "b"], 1, 0)
    ```

See Also:
    - [`ComponentSelectorProtocol`][gepa_adk.ports.component_selector.ComponentSelectorProtocol]:
      Port protocol these adapters implement.

Notes:
    RoundRobinComponentSelector is the engine's default, so it lives beside its
    protocol in `gepa_adk.ports.defaults`, where both the engine and the
    adapters may import it under ADR-000; this module re-exports it so its
    import path and `isinstance` checks keep working.

    These adapters implement component selection strategies that may maintain
    internal state for cycling (like RoundRobin) while remaining stateless with
    respect to the engine.
"""

from gepa_adk.ports.component_selector import ComponentSelectorProtocol
from gepa_adk.ports.defaults import RoundRobinComponentSelector


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

    Notes:
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

        Notes:
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

    Notes:
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
    "AllComponentSelector",
    "RoundRobinComponentSelector",
    "create_component_selector",
]

"""Protocol definition for component selection strategies.

Attributes:
    ComponentSelectorProtocol: Async protocol for component selection strategies.

Examples:
    Implement a round-robin component selector:

    ```python
    from gepa_adk.ports.component_selector import ComponentSelectorProtocol


    class RoundRobinSelector:
        async def select_components(
            self, components: list[str], iteration: int, candidate_idx: int
        ) -> list[str]:
            idx = iteration % len(components)
            return [components[idx]]


    selector = RoundRobinSelector()
    assert isinstance(selector, ComponentSelectorProtocol)
    ```

See Also:
    - [`gepa_adk.adapters.selection`][gepa_adk.adapters.selection]: Built-in
        component selection strategy implementations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ComponentSelectorProtocol(Protocol):
    """Async protocol for component selection strategies.

    Note:
        Adapters implementing this protocol determine which candidate components
        to update during mutation, enabling flexible evolution strategies.

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

        Note:
            Outputs a list of component keys to update, enabling selective
            mutation of specific candidate components.

        Examples:
            ```python
            selected = await selector.select_components(
                components=["instruction", "schema"], iteration=1, candidate_idx=0
            )
            ```
        """
        ...


__all__ = ["ComponentSelectorProtocol"]

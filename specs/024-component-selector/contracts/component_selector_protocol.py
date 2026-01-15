"""Contract specification for ComponentSelectorProtocol.

This file defines the expected interface contract for component selectors
in gepa-adk. It serves as documentation and a reference for implementers.

Note:
    This is a specification contract, not the actual implementation.
    The actual protocol will be defined in src/gepa_adk/ports/selector.py.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ComponentSelectorProtocol(Protocol):
    """Async protocol for component selection strategies.

    Component selectors determine which candidate components to mutate
    during each evolution iteration. This enables multi-component
    evolution where different components (instruction, output_schema,
    per-agent prompts) can be evolved in a controlled manner.

    Implementations must be stateful for round-robin cycling or
    stateless for all-at-once selection.

    Examples:
        Implementing a custom selector:

        ```python
        class RandomComponentSelector:
            def __init__(self, rng: random.Random | None = None) -> None:
                self._rng = rng or random.Random()

            async def select_components(
                self,
                components: list[str],
                iteration: int,
                candidate_idx: int,
            ) -> list[str]:
                # Select random single component
                return [self._rng.choice(components)]
        ```

        Using with evolve():

        ```python
        from gepa_adk import evolve
        from gepa_adk.adapters.component_selector import RoundRobinComponentSelector

        result = await evolve(
            agent=my_agent,
            trainset=data,
            component_selector=RoundRobinComponentSelector(),
        )
        ```

    Note:
        Selectors should be deterministic when given the same inputs
        (for reproducibility), unless randomness is explicitly desired.
    """

    async def select_components(
        self,
        components: list[str],
        iteration: int,
        candidate_idx: int,
    ) -> list[str]:
        """Select component(s) to mutate in this iteration.

        Args:
            components: Available component names from the candidate.
                Must be non-empty list. Example: ["instruction", "output_schema"]
            iteration: Current evolution iteration number (1-indexed).
                Used for deterministic round-robin cycling.
            candidate_idx: Index of the candidate being mutated.
                Used for per-candidate state tracking in Pareto scenarios.

        Returns:
            List of component names to mutate. Must be non-empty and
            a subset of the input components list.

        Raises:
            ValueError: If components list is empty.
            ValueError: If returned list is empty or contains unknown components.

        Examples:
            Round-robin selection:

            ```python
            # Iteration 1: ["instruction"]
            # Iteration 2: ["output_schema"]
            # Iteration 3: ["instruction"] (cycles back)
            result = await selector.select_components(
                components=["instruction", "output_schema"],
                iteration=1,
                candidate_idx=0,
            )
            assert result == ["instruction"]
            ```

            All-at-once selection:

            ```python
            result = await selector.select_components(
                components=["instruction", "output_schema"],
                iteration=1,
                candidate_idx=0,
            )
            assert result == ["instruction", "output_schema"]
            ```

        Note:
            The iteration and candidate_idx parameters enable stateful
            selectors to maintain independent cycling for each candidate.
        """
        ...


# Contract test expectations (for tests/contracts/test_component_selector_protocol.py)

CONTRACT_EXPECTATIONS = {
    "protocol_methods": ["select_components"],
    "method_signatures": {
        "select_components": {
            "params": ["components", "iteration", "candidate_idx"],
            "param_types": {"components": "list[str]", "iteration": "int", "candidate_idx": "int"},
            "return_type": "list[str]",
            "is_async": True,
        },
    },
    "invariants": [
        "Output must be non-empty list",
        "Output must be subset of input components",
        "Given same inputs, output should be deterministic (unless randomized)",
    ],
}
"""Contract test expectations for ComponentSelectorProtocol implementations."""

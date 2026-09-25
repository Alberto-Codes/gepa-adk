"""Async reflective mutation proposer for GEPA evolution.

This module provides the AsyncReflectiveMutationProposer class that generates
text mutations via LLM reflection. It takes a component's current text and
component feedback containing performance data, then uses async LLM calls to
propose improved text.

Terminology:
    - **component**: An evolvable unit with a name and text (like a gear in a machine)
    - **component_text**: The current text content of a component being evolved
    - **trial**: One performance record containing:
        - input: What was given to the system
        - output: What the system produced
        - feedback: Critic evaluation (score, feedback_text, feedback_*)
        - trajectory: Execution record (tool calls, state, events)
    - **trials**: Collection of trial records for reflection
    - **proposed_component_text**: The improved text for the same component

Attributes:
    AsyncReflectiveMutationProposer (class): Main proposer class that generates
        text mutations via LLM reflection.
    ReflectionFn (type alias): Async callable signature for reflection functions:
        ``(component_text, trials, component_name) -> (proposed_text, reasoning)``.
    ReflectiveDataset (type alias): Mapping of component names to trial sequences.
    ProposalResult (type alias): Dictionary of proposed mutations or None.

Examples:
    Basic proposer usage with ADK reflection:

    ```python
    from gepa_adk.engine import (
        AsyncReflectiveMutationProposer,
        create_adk_reflection_fn,
    )

    reflection_fn = create_adk_reflection_fn(reflection_agent, executor)
    proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=reflection_fn)
    result = await proposer.propose(
        candidate={"instruction": "Be helpful"},
        reflective_dataset={"instruction": [trials]},
        components_to_update=["instruction"],
    )
    ```

See Also:
    - [`gepa_adk.ports.proposer`][gepa_adk.ports.proposer]: Proposer protocol definition.
    - [`gepa_adk.engine.async_engine`][gepa_adk.engine.async_engine]: Evolution engine
      that uses proposers.
    - [`gepa_adk.engine.adk_reflection`][gepa_adk.engine.adk_reflection]: ADK-based
      reflection function factory.

Notes:
    This module requires an ADK reflection function for proposing mutations.
    Use `create_adk_reflection_fn()` from `gepa_adk.engine.adk_reflection` to
    create a reflection function from an ADK LlmAgent. An empty reflection
    response is retried once; a second empty response raises
    `EmptyProposalError`.
"""

__all__ = [
    "AsyncReflectiveMutationProposer",
    "ReflectionFn",
    "ReflectiveDataset",
    "ProposalResult",
]

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

import structlog

from gepa_adk.domain.exceptions import EmptyProposalError, EvolutionError

logger = structlog.get_logger(__name__)

# Type aliases for cleaner signatures
ReflectiveDataset = Mapping[str, Sequence[Mapping[str, Any]]]
ProposalResult = dict[str, str] | None
ReflectionFn = Callable[
    [str, list[dict[str, Any]], str], Awaitable[tuple[str, str | None]]
]
"""Async callable for reflection.

Signature: (component_text: str, trials: list[dict], component_name: str)
    -> tuple[str, str | None]

Takes current component text, trials, and component name. Returns a tuple
of (proposed_component_text, reasoning). The reasoning is None when the
model does not provide thought/reasoning output.
"""


class AsyncReflectiveMutationProposer:
    """Generates text mutations via LLM reflection.

    This proposer takes a candidate's current component texts and feedback
    data, then uses an ADK reflection function to generate improved versions.
    It handles empty datasets gracefully by returning None without making
    LLM calls, and retries an empty reflection response once before raising
    EmptyProposalError.

    Terminology:
        - component: Evolvable unit with name + text (the "gear" being tuned)
        - component_text: The text content of a component
        - trial: One record {input, output, feedback, trajectory}
        - trials: Collection of trial records for reflection
        - proposed_component_text: The improved text for the same component

    Attributes:
        adk_reflection_fn (ReflectionFn): ADK reflection function for proposing
            mutations. Created via `create_adk_reflection_fn()`.

    Examples:
        Standard usage with ADK reflection agent:

        ```python
        from gepa_adk.engine import create_adk_reflection_fn

        reflection_fn = create_adk_reflection_fn(reflection_agent, executor)
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=reflection_fn)
        result = await proposer.propose(
            candidate={"instruction": "Be helpful"},
            reflective_dataset={"instruction": [trials]},
            components_to_update=["instruction"],
        )
        ```

    Notes:
        ADK-based reflection via `adk_reflection_fn` is the only supported
        approach. Use `create_adk_reflection_fn()` from
        `gepa_adk.engine.adk_reflection` to create the reflection function.
    """

    def __init__(
        self,
        adk_reflection_fn: ReflectionFn,
    ) -> None:
        """Initialize the mutation proposer.

        Args:
            adk_reflection_fn: Async callable for ADK-based reflection.
                Takes (component_text, trials, component_name) and returns
                (proposed_text, reasoning) tuple. Create with
                `create_adk_reflection_fn()` from
                `gepa_adk.engine.adk_reflection`.

        Raises:
            ValueError: If adk_reflection_fn is None.

        Examples:
            ```python
            from gepa_adk.engine import create_adk_reflection_fn

            reflection_fn = create_adk_reflection_fn(reflection_agent, executor)
            proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=reflection_fn)
            ```

        Notes:
            Configuration validation happens immediately to fail fast rather
            than waiting until the first propose() call. After each
            ``propose()`` call, ``self.last_reasoning`` holds the most
            recent non-None reasoning string (or None).
        """
        if adk_reflection_fn is None:
            raise ValueError(
                "adk_reflection_fn is required. Use create_adk_reflection_fn() "
                "from gepa_adk.engine.adk_reflection to create one."
            )

        self.adk_reflection_fn = adk_reflection_fn
        self.last_reasoning: str | None = None

        # Log proposer initialization
        logger.info("proposer_initialized", reflection_method="adk")

    async def propose(
        self,
        candidate: dict[str, str],
        reflective_dataset: ReflectiveDataset,
        components_to_update: list[str],
    ) -> ProposalResult:
        """Propose mutated component text via LLM reflection.

        Args:
            candidate (dict[str, str]): Current candidate component texts.
                Keys are component names, values are component text.
                Example: {"instruction": "Be helpful and concise"}
            reflective_dataset (ReflectiveDataset): Trials per component name.
                Each trial contains input, output, feedback, and optional
                trajectory.
                Example: {"instruction": [{
                    "input": "Hello",
                    "output": "Hi there!",
                    "feedback": {"score": 0.75, "feedback_text": "Could be more formal"},
                    "trajectory": {...}
                }]}
            components_to_update (list[str]): Component names to generate
                proposals for. Components missing from the candidate or the
                reflective dataset (or with empty trials) are silently
                skipped. Example: ["instruction"]

        Returns:
            ProposalResult: Dictionary mapping component names to proposed
                component text, or None if the reflective dataset is empty
                or has no entries for the requested components.

        Raises:
            EmptyProposalError: If ADK reflection returns an empty or
                whitespace-only response twice for the same component.
            EvolutionError: If ADK reflection returns a non-string response,
                or if the reflection function raises an unexpected exception
                (wrapped in EvolutionError).

        Examples:
            ```python
            result = await proposer.propose(
                candidate={"instruction": "Be helpful"},
                reflective_dataset={
                    "instruction": [
                        {
                            "input": "I am the King",
                            "output": "Hey!",
                            "feedback": {"score": 0.3, "feedback_text": "Too casual"},
                            "trajectory": {...},
                        }
                    ]
                },
                components_to_update=["instruction"],
            )
            # result: {"instruction": "Greet users formally..."}
            ```

        Notes:
            Calls the reflection function directly with
            ``(component_text, trials, component_name)``. The function
            returns ``(proposed_text, reasoning)``; reasoning is stored
            in ``self.last_reasoning`` (last non-None value wins). An empty
            response is retried once (logged as ``proposer.empty_retry``);
            a second empty response raises EmptyProposalError, which the
            engine records as a skipped iteration. Non-string responses
            raise EvolutionError.
        """
        # Reset reasoning at start of each propose() call
        self.last_reasoning = None

        # Early return for empty dataset (no LLM calls)
        if not reflective_dataset:
            return None

        proposals = {}

        for component in components_to_update:
            # Skip if component not in reflective_dataset or has empty feedback
            if component not in reflective_dataset:
                continue

            trials: list[dict[str, Any]] = [
                dict(t) for t in reflective_dataset[component]
            ]
            if not trials:
                continue

            # Skip component not in candidate
            if component not in candidate:
                continue

            component_text = candidate[component]

            logger.debug(
                "proposer.reflection_path",
                method="adk",
                component=component,
            )

            proposals[component] = await self._reflect_with_retry(
                component_text, trials, component
            )

        # Return None if no valid proposals generated
        if not proposals:
            return None

        return proposals

    async def _reflect_with_retry(
        self,
        component_text: str,
        trials: list[dict[str, Any]],
        component: str,
    ) -> str:
        """Call reflection, retrying once when the response is empty.

        Args:
            component_text: Current text of the component.
            trials: Trial records for reflection.
            component: Name of the component being evolved.

        Returns:
            The stripped, non-empty proposed component text.

        Raises:
            EmptyProposalError: If both attempts return empty or
                whitespace-only text.
        """
        for attempt in (1, 2):
            proposed = await self._reflect_once(component_text, trials, component)
            if proposed:
                return proposed
            if attempt == 1:
                logger.warning(
                    "proposer.empty_retry",
                    component=component,
                    attempt=attempt,
                )
        raise EmptyProposalError(component)

    async def _reflect_once(
        self,
        component_text: str,
        trials: list[dict[str, Any]],
        component: str,
    ) -> str:
        """Call the reflection function once and validate its output type.

        Args:
            component_text: Current text of the component.
            trials: Trial records for reflection.
            component: Name of the component being evolved.

        Returns:
            The stripped proposed text, which may be empty.

        Raises:
            EvolutionError: If the response is not a string, or if the
                reflection function raises (wrapped in EvolutionError).
        """
        try:
            proposed_component_text, reasoning = await self.adk_reflection_fn(
                component_text, trials, component
            )
        except EvolutionError:
            raise
        except Exception as e:
            raise EvolutionError(
                f"Reflection agent raised exception: {type(e).__name__}: {str(e)}"
            ) from e

        # Store the last non-None reasoning
        if reasoning is not None:
            self.last_reasoning = reasoning

        if not isinstance(proposed_component_text, str):
            raise EvolutionError(
                "Reflection agent must return a string, got "
                f"{type(proposed_component_text).__name__}."
            )
        return proposed_component_text.strip()

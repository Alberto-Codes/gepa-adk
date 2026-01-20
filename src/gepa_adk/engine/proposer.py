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
        `(component_text: str, trials: list[dict]) -> str`.
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

Note:
    This module requires an ADK reflection function for proposing mutations.
    Use `create_adk_reflection_fn()` from `gepa_adk.engine.adk_reflection` to
    create a reflection function from an ADK LlmAgent.
"""

__all__ = [
    "AsyncReflectiveMutationProposer",
    "ReflectionFn",
    "ReflectiveDataset",
    "ProposalResult",
]

import inspect
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

import structlog

from gepa_adk.domain.exceptions import EvolutionError

logger = structlog.get_logger(__name__)

# Type aliases for cleaner signatures
ReflectiveDataset = Mapping[str, Sequence[Mapping[str, Any]]]
ProposalResult = dict[str, str] | None
ReflectionFn = Callable[[str, list[dict[str, Any]]], Awaitable[str]]
"""Async callable for reflection.

Signature: (component_text: str, trials: list[dict]) -> str

Optionally supports: (component_text, trials, component_name: str | None) -> str

Takes current component text and trials, optionally with component name,
returns proposed component text. The component_name parameter (when
supported) enables component-aware auto-selection of reflection agents.

Note:
    For backward compatibility, reflection functions can accept either:
    - 2 parameters: (component_text, trials)
    - 3 parameters: (component_text, trials, component_name)

    The proposer will inspect the function signature and call appropriately.
"""


class AsyncReflectiveMutationProposer:
    """Generates text mutations via LLM reflection.

    This proposer takes a candidate's current component texts and feedback
    data, then uses an ADK reflection function to generate improved versions.
    It handles empty datasets gracefully by returning None without making
    LLM calls.

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

    Note:
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
                Takes (component_text, trials) and returns proposed text.
                Create with `create_adk_reflection_fn()` from
                `gepa_adk.engine.adk_reflection`.

        Raises:
            ValueError: If adk_reflection_fn is None.

        Examples:
            ```python
            from gepa_adk.engine import create_adk_reflection_fn

            reflection_fn = create_adk_reflection_fn(reflection_agent, executor)
            proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=reflection_fn)
            ```

        Note:
            Configuration validation happens immediately to fail fast rather
            than waiting until the first propose() call.
        """
        if adk_reflection_fn is None:
            raise ValueError(
                "adk_reflection_fn is required. Use create_adk_reflection_fn() "
                "from gepa_adk.engine.adk_reflection to create one."
            )

        self.adk_reflection_fn = adk_reflection_fn

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
                proposals for. Example: ["instruction"]

        Returns:
            ProposalResult: Dictionary mapping component names to proposed
                component text, or None if the reflective dataset is empty
                or has no entries for the requested components.

        Raises:
            EvolutionError: If ADK reflection returns invalid response.

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

        Note:
            Output validation ensures that empty or None LLM responses raise
            EvolutionError rather than breaking the evolution loop silently.
        """
        # Early return for empty dataset (no LLM calls)
        if not reflective_dataset:
            return None

        proposals = {}

        for component in components_to_update:
            # Skip if component not in reflective_dataset or has empty feedback
            if component not in reflective_dataset:
                continue

            trials = list(reflective_dataset[component])
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

            # Call ADK reflection function with component name for auto-selection
            # Check signature for backward compatibility
            try:
                sig = inspect.signature(self.adk_reflection_fn)
                param_count = len(sig.parameters)

                if param_count >= 3:
                    # New signature: supports component_name parameter
                    # Type checker can't see runtime signature inspection
                    proposed_component_text = await self.adk_reflection_fn(  # type: ignore[call-arg]
                        component_text, trials, component
                    )
                else:
                    # Old signature: only component_text and trials
                    proposed_component_text = await self.adk_reflection_fn(
                        component_text, trials
                    )
                    logger.debug(
                        "proposer.reflection_legacy_signature",
                        component=component,
                        param_count=param_count,
                    )

                # Validate response is non-empty string
                if not isinstance(proposed_component_text, str):
                    raise EvolutionError(
                        "Reflection agent must return a string, got "
                        f"{type(proposed_component_text).__name__}."
                    )

                if not proposed_component_text.strip():
                    raise EvolutionError(
                        "Reflection agent returned empty string. "
                        "Expected non-empty string with proposed component text."
                    )

                proposals[component] = proposed_component_text.strip()
            except EvolutionError:
                # Re-raise EvolutionError as-is
                raise
            except Exception as e:
                # Wrap other exceptions in EvolutionError
                raise EvolutionError(
                    f"Reflection agent raised exception: {type(e).__name__}: {str(e)}"
                ) from e

        # Return None if no valid proposals generated
        if not proposals:
            return None

        return proposals

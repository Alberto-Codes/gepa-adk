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
    create a reflection function from an ADK LlmAgent. The optional
    ``max_trials`` and ``max_trial_chars`` caps bound the trials handed to
    the reflection function; module-level helpers select and truncate them.
    An empty reflection response is retried once; a second empty response
    raises `EmptyProposalError`.
"""

__all__ = [
    "AsyncReflectiveMutationProposer",
    "ReflectionFn",
    "ReflectiveDataset",
    "ProposalResult",
]

import copy
import math
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


def _is_failing(trial: Mapping[str, Any]) -> bool:
    """Return whether a trial counts as failing for the trial cap.

    Args:
        trial: One trial record.

    Returns:
        True when the trial's ``feedback.score`` is below 1.0, or when the
        trial has no feedback mapping or no numeric score.
    """
    feedback = trial.get("feedback")
    if not isinstance(feedback, Mapping):
        return True
    score = feedback.get("score")
    if not isinstance(score, int | float):
        return True
    return score < 1.0


def _select_trials(
    trials: list[dict[str, Any]], max_trials: int
) -> list[dict[str, Any]]:
    """Keep at most ``max_trials`` trials, failing first, then passing.

    Args:
        trials: Trial records in batch order.
        max_trials: Maximum number of trials to keep.

    Returns:
        The kept trials: failing trials first, then passing trials, each in
        batch order. Failing trials take ``ceil(max_trials / 2)`` slots and
        passing trials the rest; when either group runs short the other one
        fills the remaining slots. When ``trials`` fits within the cap it is
        returned unchanged.
    """
    if len(trials) <= max_trials:
        return trials
    failing = [t for t in trials if _is_failing(t)]
    passing = [t for t in trials if not _is_failing(t)]
    n_failing = min(len(failing), math.ceil(max_trials / 2))
    n_passing = min(len(passing), max_trials - n_failing)
    n_failing = min(len(failing), max_trials - n_passing)
    return failing[:n_failing] + passing[:n_passing]


def _truncate_value(value: Any, max_chars: int, stats: list[int]) -> Any:
    """Return ``value`` with every long string cut to ``max_chars``.

    Args:
        value: A string, dict, list or other value from a trial.
        max_chars: Maximum length of any string value.
        stats: Two-item counter ``[truncated_fields, dropped_chars]``,
            updated in place.

    Returns:
        The value with long strings replaced by a prefix plus a
        ``…[truncated, N chars omitted]`` marker. Dicts and lists are
        rebuilt; other values are returned as is.
    """
    if isinstance(value, str):
        if len(value) <= max_chars:
            return value
        omitted = len(value) - max_chars
        stats[0] += 1
        stats[1] += omitted
        return value[:max_chars] + f"…[truncated, {omitted} chars omitted]"
    if isinstance(value, dict):
        return {k: _truncate_value(v, max_chars, stats) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate_value(v, max_chars, stats) for v in value]
    return value


def _truncate_trials(
    trials: list[dict[str, Any]], max_chars: int
) -> tuple[list[dict[str, Any]], int, int]:
    """Cut every long string inside each trial, working on deep copies.

    Args:
        trials: Trial records to truncate. They are not mutated.
        max_chars: Maximum length of any string value, at any depth.

    Returns:
        A tuple of the truncated trial copies, the number of truncated
        string fields and the total number of omitted characters.
    """
    stats = [0, 0]
    truncated = [_truncate_value(copy.deepcopy(t), max_chars, stats) for t in trials]
    return truncated, stats[0], stats[1]


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
        max_trials (int | None): Maximum trials per component handed to the
            reflection function, or None for no limit.
        max_trial_chars (int | None): Maximum length of any string value in
            a trial handed to the reflection function, or None for no limit.

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
        *,
        max_trials: int | None = None,
        max_trial_chars: int | None = None,
    ) -> None:
        """Initialize the mutation proposer.

        Args:
            adk_reflection_fn: Async callable for ADK-based reflection.
                Takes (component_text, trials, component_name) and returns
                (proposed_text, reasoning) tuple. Create with
                `create_adk_reflection_fn()` from
                `gepa_adk.engine.adk_reflection`.
            max_trials: Maximum trials per component handed to the
                reflection function. Failing trials take up to half the
                slots (rounded up), passing trials the rest. None sends
                every trial.
            max_trial_chars: Maximum length of any string value inside a
                trial handed to the reflection function. Longer strings are
                cut and marked. None leaves strings intact.

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
        self.max_trials = max_trials
        self.max_trial_chars = max_trial_chars
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
            in ``self.last_reasoning`` (last non-None value wins). When
            ``max_trials`` or ``max_trial_chars`` is set, the trials are
            capped before the call and ``proposer.trials_capped`` is logged
            whenever a trial was dropped or a string truncated. An empty
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
            trials = self._cap_trials(component, trials)

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

    def _cap_trials(
        self, component: str, trials: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Apply the trial-count and string-length caps for one component.

        Args:
            component: Component name, used in the log event.
            trials: Trial records in batch order. They are not mutated.

        Returns:
            The trials to hand to the reflection function.
        """
        total = len(trials)
        if self.max_trials is not None:
            trials = _select_trials(trials, self.max_trials)
        truncated_fields = dropped_chars = 0
        if self.max_trial_chars is not None:
            trials, truncated_fields, dropped_chars = _truncate_trials(
                trials, self.max_trial_chars
            )
        dropped_trials = total - len(trials)
        if dropped_trials or truncated_fields:
            logger.info(
                "proposer.trials_capped",
                component=component,
                kept=len(trials),
                dropped_trials=dropped_trials,
                truncated_fields=truncated_fields,
                dropped_chars=dropped_chars,
            )
        return trials

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
            EvolutionError: Any error from ``_reflect_once`` propagates
                without a retry, including ``ReflectionTimeoutError``; only
                an empty response is retried.
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

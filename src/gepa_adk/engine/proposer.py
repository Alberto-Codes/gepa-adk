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
    DEFAULT_PROMPT_TEMPLATE (str): Default prompt template for text mutation
        with `{component_text}` and `{trials}` placeholders.
    AsyncReflectiveMutationProposer (class): Main proposer class that generates
        text mutations via LLM reflection.
    ReflectionFn (type alias): Async callable signature for reflection functions:
        `(component_text: str, trials: list[dict]) -> str`.
    ReflectiveDataset (type alias): Mapping of component names to trial sequences.
    ProposalResult (type alias): Dictionary of proposed mutations or None.

Examples:
    Basic proposer usage:

    ```python
    from gepa_adk.engine import AsyncReflectiveMutationProposer

    proposer = AsyncReflectiveMutationProposer()
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
    ADK-based reflection via `adk_reflection_fn` is the recommended approach.
    Direct LiteLLM calls are deprecated and will be removed in a future version.
    Use `create_adk_reflection_fn()` from `gepa_adk.engine.adk_reflection` to
    create an ADK reflection function.
"""

__all__ = [
    "DEFAULT_PROMPT_TEMPLATE",
    "AsyncReflectiveMutationProposer",
    "ReflectionFn",
    "ReflectiveDataset",
    "ProposalResult",
]

import warnings
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

import structlog
from litellm import acompletion

from gepa_adk.domain.exceptions import EvolutionError

logger = structlog.get_logger(__name__)

# Type aliases for cleaner signatures
ReflectiveDataset = Mapping[str, Sequence[Mapping[str, Any]]]
ProposalResult = dict[str, str] | None
ReflectionFn = Callable[[str, list[dict[str, Any]]], Awaitable[str]]
"""Async callable: (component_text: str, trials: list[dict]) -> str.

Takes current component text and trials, returns proposed component text.
"""

# Default prompt template for text mutation
DEFAULT_PROMPT_TEMPLATE = """You are an expert at improving text based on performance trials.

## Component Text to Improve
{component_text}

## Trials
Each trial represents a complete test of the component text above:
- feedback: The evaluation (score, feedback_text, and optional dimensions)
- trajectory: The execution path (input → output, with optional trace details)

{trials}

## Task
Analyze the trials to understand what works and what doesn't. Then propose an
improved version of the component text that will produce better-scoring outputs.

Return ONLY the improved component text, nothing else.
"""


class AsyncReflectiveMutationProposer:
    """Generates text mutations via LLM reflection.

    This proposer takes a candidate's current component texts and feedback
    data, then uses an LLM to generate improved versions. It handles empty
    datasets gracefully by returning None without making LLM calls.

    Terminology:
        - component: Evolvable unit with name + text (the "gear" being tuned)
        - component_text: The text content of a component
        - trial: One record {input, output, feedback, trajectory}
        - trials: Collection of trial records for reflection
        - proposed_component_text: The improved text for the same component

    Attributes:
        model (str): LiteLLM model identifier (deprecated - use adk_reflection_fn).
        prompt_template (str): Custom prompt template (deprecated).
        temperature (float): LLM sampling temperature (deprecated).
        max_tokens (int): Maximum tokens in LLM response (deprecated).
        adk_reflection_fn (ReflectionFn | None): ADK reflection function (recommended).

    Examples:
        Recommended usage with ADK reflection agent:

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

        Deprecated LiteLLM usage (will be removed in future version):

        ```python
        # DEPRECATED - avoid this pattern
        proposer = AsyncReflectiveMutationProposer(
            model="gemini/gemini-2.5-flash", temperature=0.7
        )
        ```

    Note:
        ADK-based reflection is recommended for consistent session management
        and unified execution. Direct LiteLLM calls are deprecated.
    """

    def __init__(
        self,
        model: str = "ollama_chat/gpt-oss:20b",
        prompt_template: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        adk_reflection_fn: ReflectionFn | None = None,
    ) -> None:
        """Initialize the mutation proposer.

        Args:
            model: LiteLLM model identifier for reflection calls.
                **Deprecated:** Use `adk_reflection_fn` instead.
                Examples: "ollama_chat/qwen3:14b" (local dev with Ollama),
                "gemini/gemini-2.5-flash" (production).
            prompt_template: Custom prompt template with {component_text}
                and {trials} placeholders. Uses default if None.
                **Deprecated:** Configure prompts via ADK agent instruction instead.
            temperature: LLM sampling temperature (0.0 = deterministic,
                2.0 = creative). **Deprecated:** Configure via ADK agent.
            max_tokens: Maximum tokens in LLM response.
                **Deprecated:** Configure via ADK agent.
            adk_reflection_fn: Async callable for ADK-based reflection.
                **Recommended:** This is the preferred approach for reflection.
                When provided, used instead of litellm.acompletion().
                Create with `create_adk_reflection_fn()` from
                `gepa_adk.engine.adk_reflection`.

        Raises:
            ValueError: If model is empty, temperature out of range, or
                max_tokens <= 0.

        Note:
            Configuration validation happens immediately to fail fast rather
            than waiting until the first propose() call.
        """
        if not model:
            raise ValueError("model must be non-empty")
        if not (0.0 <= temperature <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        self.model = model
        self.prompt_template = prompt_template or DEFAULT_PROMPT_TEMPLATE
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.adk_reflection_fn = adk_reflection_fn
        self._litellm_deprecation_warned = False

        # Validate prompt template placeholders at init time (fail-fast)
        if "{component_text}" not in self.prompt_template:
            logger.warning(
                "prompt_template missing {component_text} placeholder",
                template=self.prompt_template,
            )
        if "{trials}" not in self.prompt_template:
            logger.warning(
                "prompt_template missing {trials} placeholder",
                template=self.prompt_template,
            )

        # Log proposer initialization with configured model
        logger.info("proposer_initialized", reflection_model=self.model)

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
            litellm.AuthenticationError: If API key is invalid.
            litellm.RateLimitError: If rate limit exceeded.
            litellm.APIError: If API call fails.

        Warns:
            DeprecationWarning: When using direct LiteLLM reflection (no
                adk_reflection_fn provided). Use ADK-based reflection instead.

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
            Output validation ensures that empty or None LLM responses fall
            back to the original component text rather than breaking the
            evolution loop.
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

            if self.adk_reflection_fn is not None:
                logger.debug(
                    "proposer.reflection_path",
                    method="adk",
                    component=component,
                )
                # Call ADK reflection function
                try:
                    proposed_component_text = await self.adk_reflection_fn(
                        component_text, trials
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
            else:
                # Emit deprecation warning for LiteLLM fallback path (once per instance)
                if not self._litellm_deprecation_warned:
                    warnings.warn(
                        "Direct LiteLLM reflection is deprecated and will be removed in a "
                        "future version. Use reflection_agent parameter with an ADK LlmAgent "
                        "instead. See: https://github.com/Alberto-Codes/gepa-adk/issues/144",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    self._litellm_deprecation_warned = True
                logger.debug(
                    "proposer.reflection_path",
                    method="litellm",
                    component=component,
                    deprecated=True,
                )
                # LiteLLM path (deprecated)
                messages = self._build_messages(component_text, trials)

                # Call LiteLLM async API
                response = await acompletion(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                # Extract response content
                content = response.choices[0].message.content

                # Edge case: Handle empty/None LLM response
                if content is None or not content.strip():
                    # Fall back to original component text
                    proposals[component] = component_text
                else:
                    proposals[component] = content.strip()

        # Return None if no valid proposals generated
        if not proposals:
            return None

        return proposals

    def _build_messages(
        self, component_text: str, trials: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, str]]:
        """Build LLM message list from component text and trials.

        Args:
            component_text: The current component text to be improved.
            trials: Sequence of trial records for reflection.

        Returns:
            List of message dictionaries in LiteLLM format.

        Note:
            Standard message format follows OpenAI's chat completion API
            structure, which LiteLLM uses as its common interface.
        """
        formatted_trials = self._format_trials(trials)

        prompt = self.prompt_template.format(
            component_text=component_text,
            trials=formatted_trials,
        )

        return [{"role": "user", "content": prompt}]

    def _format_trials(self, trials: Sequence[Mapping[str, Any]]) -> str:
        """Format trial records as text.

        Args:
            trials: Sequence of trial records to format.

        Returns:
            Formatted trials text for inclusion in prompt.

        Note:
            Serialization preserves structure while keeping prompts readable,
            balancing information density with LLM comprehension.
        """
        if not trials:
            return ""

        lines = []
        for i, trial in enumerate(trials, 1):
            lines.append(f"Trial {i}:")
            for key, value in trial.items():
                lines.append(f"  {key}: {value}")
            lines.append("")  # Blank line between trials

        return "\n".join(lines).strip()

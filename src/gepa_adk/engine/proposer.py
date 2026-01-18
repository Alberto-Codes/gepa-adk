"""Async reflective mutation proposer for GEPA evolution.

This module provides the AsyncReflectiveMutationProposer class that generates
text mutations via LLM reflection. It takes a candidate's current text and a
reflective dataset containing feedback, then uses async LLM calls to propose
improved text.

Attributes:
    DEFAULT_PROMPT_TEMPLATE (str): Default prompt template for text mutation
        with `{input_text}` and `{input_feedback}` placeholders.
    AsyncReflectiveMutationProposer (class): Main proposer class that generates
        text mutations via LLM reflection.
    ReflectionFn (type alias): Async callable signature for reflection functions:
        `(input_text: str, input_feedback: list[dict]) -> str`.
    ReflectiveDataset (type alias): Mapping of component names to feedback sequences.
    ProposalResult (type alias): Dictionary of proposed mutations or None.

Examples:
    Basic proposer usage:

    ```python
    from gepa_adk.engine import AsyncReflectiveMutationProposer

    proposer = AsyncReflectiveMutationProposer()
    result = await proposer.propose(
        candidate={"input_text": "Be helpful"},
        reflective_dataset={"input_text": [feedback_items]},
        components_to_update=["input_text"],
    )
    ```

See Also:
    - [`gepa_adk.ports.proposer`][gepa_adk.ports.proposer]: Proposer protocol definition.
    - [`gepa_adk.engine.async_engine`][gepa_adk.engine.async_engine]: Evolution engine
      that uses proposers.
    - [`gepa_adk.engine.adk_reflection`][gepa_adk.engine.adk_reflection]: ADK-based
      reflection function factory.

Note:
    This proposer uses LiteLLM's async API for non-blocking LLM calls, enabling
    efficient concurrent mutation generation across multiple candidates.
"""

__all__ = [
    "DEFAULT_PROMPT_TEMPLATE",
    "AsyncReflectiveMutationProposer",
    "ReflectionFn",
    "ReflectiveDataset",
    "ProposalResult",
]

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
"""Async callable: (input_text: str, input_feedback: list[dict]) -> str.

Takes current text and evaluation feedback, returns proposed text.
"""

# Default prompt template for text mutation
DEFAULT_PROMPT_TEMPLATE = """You are an expert at improving AI agent \
text based on performance feedback.

## Input Text
{input_text}

## Input Feedback
{input_feedback}

## Task
Based on the feedback above, propose improved text that:
1. Addresses the issues identified in negative feedback
2. Preserves elements that worked well in positive feedback
3. Maintains clarity and specificity

Return ONLY the proposed text, with no additional commentary.
"""


class AsyncReflectiveMutationProposer:
    """Generates text mutations via LLM reflection.

    This proposer takes a candidate's current text components and feedback
    data, then uses an LLM to generate improved versions of the text. It
    handles empty datasets gracefully by returning None without making LLM calls.

    Attributes:
        model (str): LiteLLM model identifier for reflection calls.
        prompt_template (str): Custom prompt template (uses default if None).
        temperature (float): LLM sampling temperature for creative variation.
        max_tokens (int): Maximum tokens in LLM response.

    Examples:
        ```python
        proposer = AsyncReflectiveMutationProposer(
            model="gemini/gemini-2.5-flash", temperature=0.7
        )
        result = await proposer.propose(
            candidate={"input_text": "Be helpful"},
            reflective_dataset={"input_text": [feedback_items]},
            components_to_update=["input_text"],
        )
        ```

    Note:
        All LLM calls are async to avoid blocking the event loop, making this
        proposer suitable for high-throughput evolution scenarios.
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
                Examples: "ollama_chat/qwen3:14b" (local dev with Ollama),
                "gemini/gemini-2.5-flash" (production).
                Note: "ollama_chat/" prefix is the correct LiteLLM format for
                Ollama chat models in this codebase.
            prompt_template: Custom prompt template with {input_text}
                and {input_feedback} placeholders. Uses default if None.
            temperature: LLM sampling temperature (0.0 = deterministic,
                2.0 = creative).
            max_tokens: Maximum tokens in LLM response.
            adk_reflection_fn: Optional async callable for ADK-based reflection.
                When provided, used instead of litellm.acompletion().
                When None, falls back to LiteLLM (backwards compatible).
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

        # Validate prompt template placeholders at init time (fail-fast)
        if "{input_text}" not in self.prompt_template:
            logger.warning(
                "prompt_template missing {input_text} placeholder",
                template=self.prompt_template,
            )
        if "{input_feedback}" not in self.prompt_template:
            logger.warning(
                "prompt_template missing {input_feedback} placeholder",
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
        """Propose mutated text via LLM reflection.

        Args:
            candidate (dict[str, str]): Current candidate component texts.
                Example: {"input_text": "Be helpful and concise"}
            reflective_dataset (ReflectiveDataset): Feedback examples per
                component. Example: {"input_text": [{"input": "...",
                "feedback": "..."}]}
            components_to_update (list[str]): Component names to generate
                proposals for. Example: ["input_text"]

        Returns:
            ProposalResult: Dictionary mapping component names to proposed new
                text, or None if the reflective dataset is empty or has no
                entries for the requested components.

        Raises:
            EvolutionError: If ADK reflection returns invalid response.
            litellm.AuthenticationError: If API key is invalid.
            litellm.RateLimitError: If rate limit exceeded.
            litellm.APIError: If API call fails.

        Examples:
            ```python
            result = await proposer.propose(
                candidate={"input_text": "Be helpful"},
                reflective_dataset={
                    "input_text": [{"input": "test", "feedback": "needs detail"}]
                },
                components_to_update=["input_text"],
            )
            # result: {"input_text": "Be helpful and detailed"}
            ```

        Note:
            Output validation ensures that empty or None LLM responses fall
            back to the original candidate text rather than breaking the
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

            feedback_items = list(reflective_dataset[component])
            if not feedback_items:
                continue

            # Skip component not in candidate
            if component not in candidate:
                continue

            input_text = candidate[component]

            if self.adk_reflection_fn is not None:
                logger.debug(
                    "proposer.reflection_path",
                    method="adk",
                    component=component,
                )
                # Call ADK reflection function
                try:
                    proposed_text = await self.adk_reflection_fn(
                        input_text, feedback_items
                    )

                    # Validate response is non-empty string
                    if not isinstance(proposed_text, str):
                        raise EvolutionError(
                            "Reflection agent must return a string, got "
                            f"{type(proposed_text).__name__}."
                        )

                    if not proposed_text.strip():
                        raise EvolutionError(
                            "Reflection agent returned empty string. "
                            "Expected non-empty string with proposed text."
                        )

                    proposals[component] = proposed_text.strip()
                except EvolutionError:
                    # Re-raise EvolutionError as-is
                    raise
                except Exception as e:
                    # Wrap other exceptions in EvolutionError
                    raise EvolutionError(
                        f"Reflection agent raised exception: {type(e).__name__}: {str(e)}"
                    ) from e
            else:
                logger.debug(
                    "proposer.reflection_path",
                    method="litellm",
                    component=component,
                )
                # LiteLLM path
                messages = self._build_messages(input_text, feedback_items)

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
                    # Fall back to original text
                    proposals[component] = input_text
                else:
                    proposals[component] = content.strip()

        # Return None if no valid proposals generated
        if not proposals:
            return None

        return proposals

    def _build_messages(
        self, input_text: str, feedback_items: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, str]]:
        """Build LLM message list from inputs.

        Args:
            input_text: The current text to be improved.
            feedback_items: Sequence of feedback examples with inputs and feedback.

        Returns:
            List of message dictionaries in LiteLLM format.

        Note:
            Standard message format follows OpenAI's chat completion API
            structure, which LiteLLM uses as its common interface.
        """
        formatted_feedback = self._format_feedback(feedback_items)

        prompt = self.prompt_template.format(
            input_text=input_text,
            input_feedback=formatted_feedback,
        )

        return [{"role": "user", "content": prompt}]

    def _format_feedback(self, feedback: Sequence[Mapping[str, Any]]) -> str:
        """Format feedback examples as text.

        Args:
            feedback: Sequence of feedback examples to format.

        Returns:
            Formatted feedback text for inclusion in prompt.

        Note:
            Serialization preserves structure while keeping prompts readable,
            balancing information density with LLM comprehension.
        """
        if not feedback:
            return ""

        lines = []
        for i, item in enumerate(feedback, 1):
            lines.append(f"Example {i}:")
            for key, value in item.items():
                lines.append(f"  {key}: {value}")
            lines.append("")  # Blank line between examples

        return "\n".join(lines).strip()

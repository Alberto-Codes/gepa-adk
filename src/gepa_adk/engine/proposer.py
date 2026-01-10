"""Async reflective mutation proposer for GEPA evolution.

This module provides the AsyncReflectiveMutationProposer class that generates
instruction mutations via LLM reflection. It takes a candidate's current
instruction text and a reflective dataset containing feedback, then uses async
LLM calls to propose improved instruction text.

Typical usage example:

    ```python
    from gepa_adk.engine import AsyncReflectiveMutationProposer

    proposer = AsyncReflectiveMutationProposer()
    result = await proposer.propose(
        candidate={"instruction": "Be helpful"},
        reflective_dataset={"instruction": [feedback_items]},
        components_to_update=["instruction"],
    )
    ```

Note:
    This proposer uses LiteLLM's async API for non-blocking LLM calls, enabling
    efficient concurrent mutation generation across multiple candidates.
"""

from collections.abc import Mapping, Sequence
from typing import Any

import structlog
from litellm import acompletion

logger = structlog.get_logger(__name__)

# Type aliases for cleaner signatures
ReflectiveDataset = Mapping[str, Sequence[Mapping[str, Any]]]
ProposalResult = dict[str, str] | None

# Default prompt template for instruction mutation
DEFAULT_PROMPT_TEMPLATE = """You are an expert at improving AI agent \
instructions based on performance feedback.

## Current Instruction
{current_instruction}

## Performance Feedback
{feedback_examples}

## Task
Based on the feedback above, propose an improved instruction that:
1. Addresses the issues identified in negative feedback
2. Preserves elements that worked well in positive feedback
3. Maintains clarity and specificity

Return ONLY the improved instruction text, with no additional commentary.
"""


class AsyncReflectiveMutationProposer:
    """Generates instruction mutations via LLM reflection.

    This proposer takes a candidate's current instruction components and
    feedback data, then uses an LLM to generate improved versions of the
    instructions. It handles empty datasets gracefully by returning None
    without making LLM calls.

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
            candidate={"instruction": "Be helpful"},
            reflective_dataset={"instruction": [feedback_items]},
            components_to_update=["instruction"],
        )
        ```

    Note:
        All LLM calls are async to avoid blocking the event loop, making this
        proposer suitable for high-throughput evolution scenarios.
    """

    def __init__(
        self,
        model: str = "ollama/gpt-oss:20b",
        prompt_template: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        """Initialize the mutation proposer.

        Args:
            model: LiteLLM model identifier for reflection calls.
                Examples: "ollama/gpt-oss:20b" (local dev),
                "gemini/gemini-2.5-flash" (production)
            prompt_template: Custom prompt template with {current_instruction}
                and {feedback_examples} placeholders. Uses default if None.
            temperature: LLM sampling temperature (0.0 = deterministic,
                2.0 = creative).
            max_tokens: Maximum tokens in LLM response.

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

        # Validate prompt template placeholders at init time (fail-fast)
        if "{current_instruction}" not in self.prompt_template:
            logger.warning(
                "prompt_template missing {current_instruction} placeholder",
                template=self.prompt_template,
            )
        if "{feedback_examples}" not in self.prompt_template:
            logger.warning(
                "prompt_template missing {feedback_examples} placeholder",
                template=self.prompt_template,
            )

    async def propose(
        self,
        candidate: dict[str, str],
        reflective_dataset: ReflectiveDataset,
        components_to_update: list[str],
    ) -> ProposalResult:
        """Propose mutated instruction text via LLM reflection.

        Args:
            candidate (dict[str, str]): Current candidate component texts.
                Example: {"instruction": "Be helpful and concise"}
            reflective_dataset (ReflectiveDataset): Feedback examples per
                component. Example: {"instruction": [{"input": "...",
                "feedback": "..."}]}
            components_to_update (list[str]): Component names to generate
                proposals for. Example: ["instruction"]

        Returns:
            ProposalResult: Dictionary mapping component names to proposed new
                text, or None if the reflective dataset is empty or has no
                entries for the requested components.

        Raises:
            litellm.AuthenticationError: If API key is invalid.
            litellm.RateLimitError: If rate limit exceeded.
            litellm.APIError: If API call fails.
            Exception: Any other LiteLLM exception propagates unchanged.

        Examples:
            ```python
            result = await proposer.propose(
                candidate={"instruction": "Be helpful"},
                reflective_dataset={
                    "instruction": [{"input": "test", "feedback": "needs detail"}]
                },
                components_to_update=["instruction"],
            )
            # result: {"instruction": "Be helpful and detailed"}
            ```

        Note:
            Output validation ensures that empty or None LLM responses fall
            back to the original candidate text rather than breaking the
            evolution loop.
        """
        # US3: Early return for empty dataset (no LLM calls)
        if not reflective_dataset:
            return None

        proposals = {}

        # Iterate through components_to_update
        for component in components_to_update:
            # US3: Skip if component not in reflective_dataset or has empty feedback
            if component not in reflective_dataset:
                continue

            feedback = reflective_dataset[component]
            if not feedback:
                continue

            # Edge case: Skip component not in candidate
            if component not in candidate:
                continue

            current_text = candidate[component]

            # Build messages for LLM
            messages = self._build_messages(current_text, feedback)

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
                proposals[component] = current_text
            else:
                proposals[component] = content.strip()

        # US3: Return None if no valid proposals generated
        if not proposals:
            return None

        return proposals

    def _build_messages(
        self, current_text: str, feedback: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, str]]:
        """Build LLM message list from inputs.

        Args:
            current_text: The current instruction text to be improved.
            feedback: Sequence of feedback examples with inputs and feedback.

        Returns:
            List of message dictionaries in LiteLLM format.

        Note:
            Standard message format follows OpenAI's chat completion API
            structure, which LiteLLM uses as its common interface.
        """
        # Format feedback examples
        feedback_text = self._format_feedback(feedback)

        # Substitute placeholders in prompt template
        prompt = self.prompt_template.format(
            current_instruction=current_text,
            feedback_examples=feedback_text,
        )

        # Return message list in OpenAI/LiteLLM format
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

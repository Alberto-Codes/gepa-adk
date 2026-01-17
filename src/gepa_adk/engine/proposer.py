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
"""Async callable: (current_instruction: str, feedback: list[dict]) -> str.

Takes current instruction text and evaluation feedback, returns improved instruction.
"""

# Session state schema keys for ADK reflection
SESSION_STATE_KEYS = {
    "current_instruction": str,
    "execution_feedback": str,  # JSON-serialized list
}
"""Expected keys and types in ADK session state for reflection.

The reflection agent accesses these keys via {key} template syntax
in its instruction.
"""

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


def create_adk_reflection_fn(
    reflection_agent: Any,  # LlmAgent from google.adk.agents
    session_service: Any | None = None,  # BaseSessionService from google.adk.sessions
) -> ReflectionFn:
    """Create a reflection function from an ADK LlmAgent.

    This factory function creates an async callable that uses the Google ADK
    framework for reflection. The returned function can be passed to
    AsyncReflectiveMutationProposer as the adk_reflection_fn parameter.

    Args:
        reflection_agent: ADK LlmAgent configured with instruction template
            containing {current_instruction} and {execution_feedback} placeholders.
            The agent's instruction should include logic for improving instructions
            based on feedback.
        session_service: Optional session service for state management.
            Defaults to InMemorySessionService if None. Use custom services
            (e.g., DatabaseSessionService) for production deployments requiring
            session persistence.

    Returns:
        Async callable matching ReflectionFn signature that generates improved
        instructions via the ADK agent.

    Raises:
        TypeError: If reflection_agent is not an LlmAgent instance.

    Examples:
        Basic usage with default session service:

        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk.engine import create_adk_reflection_fn

        agent = LlmAgent(
            name="InstructionReflector",
            model="gemini-2.0-flash",
            instruction=\"\"\"Improve this instruction:
            {current_instruction}

            Based on feedback:
            {execution_feedback}

            Return improved instruction only.\"\"\"
        )

        reflection_fn = create_adk_reflection_fn(agent)
        improved = await reflection_fn("Be helpful", [{"score": 0.5}])
        ```

        With custom session service:

        ```python
        from google.adk.sessions import DatabaseSessionService

        db_service = DatabaseSessionService(db_url="sqlite:///sessions.db")
        reflection_fn = create_adk_reflection_fn(agent, session_service=db_service)
        ```

    Note:
        The reflection function creates a fresh ADK session for each invocation,
        ensuring complete isolation between reflection operations. Session state
        is initialized with current_instruction (str) and execution_feedback
        (JSON-serialized list).
    """
    import json
    from uuid import uuid4

    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai.types import Content, Part

    # Default to InMemorySessionService if not provided
    if session_service is None:
        session_service = InMemorySessionService()

    async def reflect(
        current_instruction: str,
        feedback: list[dict[str, Any]],
    ) -> str:
        """Reflect on instruction using ADK agent to generate improved version.

        Uses the configured ADK reflection agent to analyze the current instruction
        and feedback, then generates an improved instruction based on the evaluation
        results.

        Args:
            current_instruction: The instruction text to improve.
            feedback: List of feedback dictionaries from evaluation. Each dictionary
                should contain evaluation results and scores.

        Returns:
            Improved instruction text generated by the reflection agent.

        Examples:
            Basic reflection with feedback:

            ```python
            feedback = [
                {"output": "result1", "score": 0.8},
                {"output": "result2", "score": 0.6},
            ]
            improved = await reflect(
                current_instruction="Write a function", feedback=feedback
            )
            ```

        Note:
            Each invocation creates a unique session with fresh state to ensure
            isolation between reflection operations.
        """
        # Generate unique session ID for this reflection
        session_id = f"reflect_{uuid4()}"

        # Log reflection start
        logger.info(
            "reflection.start",
            session_id=session_id,
            instruction_length=len(current_instruction),
            feedback_count=len(feedback),
        )

        try:
            # Create session with initial state
            session_state = {
                "current_instruction": current_instruction,
                "execution_feedback": json.dumps(feedback),
            }
            await session_service.create_session(
                app_name="gepa_reflection",
                user_id="reflection",
                session_id=session_id,
                state=session_state,
            )

            # Debug: Log what we're putting in session state
            logger.debug(
                "reflection.session_state",
                session_id=session_id,
                current_instruction_preview=current_instruction[:100] + "..."
                if len(current_instruction) > 100
                else current_instruction,
                execution_feedback_preview=json.dumps(feedback)[:200] + "..."
                if len(json.dumps(feedback)) > 200
                else json.dumps(feedback),
                state_keys=list(session_state.keys()),
            )

            # Create runner for this reflection
            runner = Runner(
                agent=reflection_agent,
                app_name="gepa_reflection",
                session_service=session_service,
            )

            # Execute reflection via Runner.run_async
            # Include instruction and feedback directly in user message since template
            # interpolation may not work reliably with LiteLlm models
            # Format feedback to match DEFAULT_PROMPT_TEMPLATE structure
            feedback_lines = []
            for i, item in enumerate(feedback, 1):
                if isinstance(item, dict):
                    lines = [f"Example {i}:"]
                    for key, value in item.items():
                        # Truncate long values for readability
                        if isinstance(value, str) and len(value) > 200:
                            value = value[:200] + "..."
                        lines.append(f"  {key}: {value}")
                    feedback_lines.extend(lines)
                    feedback_lines.append("")  # Blank line between examples

            feedback_text = "\n".join(feedback_lines).strip()

            # Match DEFAULT_PROMPT_TEMPLATE structure
            user_message_text = f"""## Current Instruction
{current_instruction}

## Performance Feedback
{feedback_text if feedback_text else "No feedback available"}

## Task
Based on the feedback above, propose an improved instruction that:
1. Addresses the issues identified in negative feedback
2. Preserves elements that worked well in positive feedback
3. Maintains clarity and specificity

Return ONLY the improved instruction text, with no additional commentary."""

            # Execute the agent - output_key will save final response to session state
            # Collect final event for fallback extraction
            final_event = None
            session_state: dict[str, Any] = {}
            async for event in runner.run_async(
                user_id="reflection",
                session_id=session_id,
                new_message=Content(
                    role="user",
                    parts=[Part(text=user_message_text)],
                ),
            ):
                if event.is_final_response():
                    final_event = event

                # Capture session state from event (matches multi_agent.py pattern)
                if hasattr(event, "session") and event.session:
                    if hasattr(event.session, "state"):
                        session_state = dict(event.session.state)  # type: ignore

            # Check if agent has output_key - this is the cleanest way to get structured output
            output_key = getattr(reflection_agent, "output_key", None)
            logger.debug(
                "reflection.checking_output_key",
                session_id=session_id,
                has_output_key=output_key is not None,
                output_key=output_key,
                session_state_keys=list(session_state.keys()) if session_state else [],
                has_output_schema=hasattr(reflection_agent, "output_schema")
                and reflection_agent.output_schema is not None,
            )
            if output_key and output_key in session_state:
                output_value = session_state[output_key]

                # If output_schema is set, output_value is already parsed JSON (dict)
                if (
                    hasattr(reflection_agent, "output_schema")
                    and reflection_agent.output_schema
                ):
                    if isinstance(output_value, dict) and "instruction" in output_value:
                        instruction_text = output_value["instruction"]
                        logger.debug(
                            "reflection.from_output_key",
                            session_id=session_id,
                            output_key=output_key,
                            extracted_length=len(instruction_text),
                        )
                        return str(instruction_text).strip()
                    elif isinstance(output_value, str):
                        # Sometimes output_key stores as string, parse it
                        try:
                            parsed = json.loads(output_value)
                            if isinstance(parsed, dict) and "instruction" in parsed:
                                instruction_text = parsed["instruction"]
                                logger.debug(
                                    "reflection.from_output_key_parsed",
                                    session_id=session_id,
                                    output_key=output_key,
                                    extracted_length=len(instruction_text),
                                )
                                return str(instruction_text).strip()
                        except (json.JSONDecodeError, TypeError):
                            pass
                else:
                    # No output_schema, output_value is just the text
                    logger.debug(
                        "reflection.from_output_key_text",
                        session_id=session_id,
                        output_key=output_key,
                        output_length=len(str(output_value)),
                    )
                    return str(output_value).strip()
            else:
                # Log why we're not using output_key
                if not output_key:
                    logger.debug(
                        "reflection.no_output_key",
                        session_id=session_id,
                        reason="agent_has_no_output_key",
                    )
                elif output_key not in session_state:
                    logger.debug(
                        "reflection.no_output_key",
                        session_id=session_id,
                        reason="output_key_not_in_session_state",
                        output_key=output_key,
                        available_keys=list(session_state.keys()),
                    )

            # Fallback: Extract from final event (for agents without output_key)
            # This is the old method - kept for backwards compatibility
            response_text = ""
            if final_event:
                has_response_content = (
                    final_event.actions
                    and hasattr(final_event.actions, "response_content")
                    and final_event.actions.response_content
                )
                if has_response_content:
                    parts_text = []
                    for part in final_event.actions.response_content:  # type: ignore[union-attr]
                        if hasattr(part, "text") and part.text:
                            parts_text.append(part.text)
                    if parts_text:
                        response_text = "".join(parts_text)
                elif final_event.content and final_event.content.parts:
                    parts_text = []
                    for part in final_event.content.parts:
                        if hasattr(part, "text") and part.text:
                            parts_text.append(part.text)
                    if parts_text:
                        response_text = "".join(parts_text)

            # Log reflection complete
            logger.info(
                "reflection.complete",
                session_id=session_id,
                response_length=len(response_text),
            )

            # Handle empty response - fallback to empty string
            if not response_text:
                logger.warning(
                    "reflection.empty_response",
                    session_id=session_id,
                )
                return ""

            # Post-process: Extract just the instruction text
            # (fallback for agents without output_schema)
            # The agent might include reasoning or commentary, so we try to extract
            # just the instruction part. Common patterns:
            # 1. Agent returns just the instruction (ideal case)
            # 2. Agent includes "Improved instruction:" or similar prefix
            # 3. Agent includes reasoning before/after the instruction
            cleaned_text = response_text.strip()

            # If response is short (<200 chars), likely just the instruction
            if len(cleaned_text) < 200:
                return cleaned_text

            # Try to extract instruction if it's wrapped in common patterns
            import re

            # Pattern 1: Look for "IMPROVED INSTRUCTION:" marker (explicit format)
            # Pattern 2: Look for "Improved instruction:" or similar markers
            # (capture everything after)
            # Pattern 3: Look for code blocks (likely contains instruction)
            # Pattern 4: Look for quoted instruction text
            instruction_patterns = [
                r"IMPROVED INSTRUCTION:\s*(.+?)(?:\n\n|\n(?:Here|This|The|Note|Note:|Explanation|Reasoning|Analysis|Summary)|$)",
                r"(?:improved instruction|new instruction|revised instruction|updated instruction)[:\-]?\s*\n?(.+?)(?:\n\n|\n(?:Here|This|The|Note|Note:|Explanation|Reasoning|Analysis|Summary)|$)",
                r"```(?:text|instruction)?\n?(.+?)\n?```",
                r'["\'](.+?)["\']',  # Quoted instruction
            ]

            for pattern in instruction_patterns:
                match = re.search(pattern, cleaned_text, re.IGNORECASE | re.DOTALL)
                if match:
                    extracted = match.group(1).strip()
                    # Must be substantial (at least 30 chars) and not just a fragment
                    if len(extracted) >= 30 and not extracted.endswith(
                        (".", ":", ";", ",")
                    ):
                        logger.debug(
                            "reflection.extracted_instruction",
                            session_id=session_id,
                            original_length=len(cleaned_text),
                            extracted_length=len(extracted),
                            pattern_used=pattern[:50],
                        )
                        return extracted

            # Fallback: If response is long, try to find the longest paragraph
            # that doesn't contain common reasoning words
            if len(cleaned_text) > 500:
                paragraphs = cleaned_text.split("\n\n")
                reasoning_words = [
                    "current",
                    "feedback",
                    "shows",
                    "scores",
                    "however",
                    "therefore",
                    "analysis",
                    "summary",
                ]

                # Find the longest paragraph that doesn't start with reasoning words
                best_paragraph = None
                best_length = 0

                for para in paragraphs:
                    para_clean = para.strip()
                    # Skip if starts with reasoning words or is too short
                    if len(para_clean) < 30:
                        continue
                    first_words = para_clean.lower().split()[:3]
                    if any(word in first_words for word in reasoning_words):
                        continue
                    if len(para_clean) > best_length:
                        best_length = len(para_clean)
                        best_paragraph = para_clean

                if best_paragraph:
                    logger.debug(
                        "reflection.extracted_instruction",
                        session_id=session_id,
                        original_length=len(cleaned_text),
                        extracted_length=len(best_paragraph),
                        method="longest_paragraph",
                    )
                    return best_paragraph

                logger.warning(
                    "reflection.long_response",
                    session_id=session_id,
                    response_length=len(cleaned_text),
                    preview=cleaned_text[:200],
                )

            # Last resort: return first 500 chars (might be the instruction at the start)
            if len(cleaned_text) > 500:
                first_part = cleaned_text[:500].strip()
                # Try to end at a sentence boundary
                last_period = first_part.rfind(".")
                if last_period > 100:
                    return first_part[: last_period + 1]
                return first_part

            return cleaned_text

        except Exception as e:
            # Log error and propagate
            logger.error(
                "reflection.error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    return reflect


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
        model: str = "ollama_chat/gpt-oss:20b",
        prompt_template: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        adk_reflection_fn: ReflectionFn | None = None,
    ) -> None:
        """Initialize the mutation proposer.

        Args:
            model: LiteLLM model identifier for reflection calls.
                Examples: "ollama_chat/gpt-oss:20b" (local dev),
                "gemini/gemini-2.5-flash" (production)
            prompt_template: Custom prompt template with {current_instruction}
                and {feedback_examples} placeholders. Uses default if None.
            temperature: LLM sampling temperature (0.0 = deterministic,
                2.0 = creative).
            max_tokens: Maximum tokens in LLM response.
            adk_reflection_fn: Optional async callable for ADK-based reflection.
                When provided, used instead of litellm.acompletion().
                When None, falls back to LiteLLM (backwards compatible).

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

            # US3: Use ADK reflection if available, otherwise LiteLLM
            if self.adk_reflection_fn is not None:
                # Call ADK reflection function
                try:
                    new_text = await self.adk_reflection_fn(current_text, feedback)

                    # Validate response is non-empty string
                    if not isinstance(new_text, str):
                        raise EvolutionError(
                            "Reflection agent must return a string, got "
                            f"{type(new_text).__name__}."
                        )

                    if not new_text.strip():
                        raise EvolutionError(
                            "Reflection agent returned empty string. "
                            "Expected non-empty string with improved instruction."
                        )

                    proposals[component] = new_text.strip()

                    # Log proposed instruction text
                    logger.debug(
                        "proposal.generated",
                        component=component,
                        original_length=len(current_text),
                        proposed_length=len(new_text.strip()),
                        proposed_preview=new_text.strip()[:200] + "..."
                        if len(new_text.strip()) > 200
                        else new_text.strip(),
                    )
                except EvolutionError:
                    # Re-raise EvolutionError as-is
                    raise
                except Exception as e:
                    # Wrap other exceptions in EvolutionError
                    raise EvolutionError(
                        f"Reflection agent raised exception: {type(e).__name__}: {str(e)}"
                    ) from e
            else:
                # Fallback to LiteLLM path (backwards compatible)
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
                    logger.debug(
                        "proposal.empty_fallback",
                        component=component,
                    )
                else:
                    proposals[component] = content.strip()
                    # Log proposed instruction text
                    logger.debug(
                        "proposal.generated",
                        component=component,
                        original_length=len(current_text),
                        proposed_length=len(content.strip()),
                        proposed_preview=content.strip()[:200] + "..."
                        if len(content.strip()) > 200
                        else content.strip(),
                    )

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

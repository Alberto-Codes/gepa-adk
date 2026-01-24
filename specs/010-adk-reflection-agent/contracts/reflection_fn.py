"""Contract definitions for ADK reflection function.

This module defines the type contracts and protocol for the ADK reflection
function used by AsyncReflectiveMutationProposer.

Note:
    These contracts are used for documentation and type checking. Runtime
    validation is performed in the factory function and proposer.
"""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

# Type alias for the reflection function signature
ReflectionFn = Callable[[str, list[dict[str, Any]]], Awaitable[str]]
"""Async callable that takes (input_text, input_feedback) and returns proposed_text.

Args:
    input_text: The text currently being evolved.
    input_feedback: List of feedback dictionaries from evaluation results.

Returns:
    Proposed text as a string.

Example:
    ```python
    async def my_reflection_fn(
        input_text: str,
        input_feedback: list[dict[str, Any]],
    ) -> str:
        # Process and return proposed text
        return "proposed text"
    ```
"""


@runtime_checkable
class ReflectionFnProtocol(Protocol):
    """Protocol for ADK reflection function.

    This protocol defines the structural interface for reflection functions.
    Used for runtime type checking with isinstance().

    Example:
        ```python
        def is_valid_reflection_fn(fn: Any) -> bool:
            return isinstance(fn, ReflectionFnProtocol)
        ```
    """

    async def __call__(
        self,
        input_text: str,
        input_feedback: list[dict[str, Any]],
    ) -> str:
        """Execute reflection to generate proposed text.

        Args:
            input_text: Current text to improve.
            input_feedback: List of feedback dictionaries from evaluation.

        Returns:
            Proposed text.
        """
        ...


# Session state schema keys
SESSION_STATE_KEYS = {
    "input_text": str,
    "input_feedback": str,  # JSON-serialized list
}
"""Expected keys and types in ADK session state for reflection.

The reflection agent accesses these keys via {key} template syntax
in its instruction.
"""


# Factory function contract
class CreateAdkReflectionFnContract:
    """Contract documentation for create_adk_reflection_fn factory.

    Factory Signature:
        ```python
        def create_adk_reflection_fn(
            reflection_agent: LlmAgent,
            session_service: BaseSessionService | None = None,
        ) -> ReflectionFn:
        ```

    Parameters:
        reflection_agent: ADK LlmAgent configured with instruction template
            containing {component_text} and {trials} placeholders.
        session_service: Optional session service for state management.
            Defaults to InMemorySessionService if None.

    Returns:
        Async callable matching ReflectionFn signature.

    Raises:
        TypeError: If reflection_agent is not an LlmAgent instance.

    Example:
        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

        agent = LlmAgent(
            name="Reflector",
            model="gemini-2.5-flash",
            instruction=\"\"\"Improve this text:
            {component_text}

            Based on trials:
            {trials}\"\"\"
        )

        reflection_fn = create_adk_reflection_fn(agent)
        proposed = await reflection_fn("Be helpful", [{"score": 0.5}])
        ```
    """

    pass


# Proposer extension contract
class AsyncReflectiveMutationProposerContract:
    """Contract documentation for extended AsyncReflectiveMutationProposer.

    Extended __init__ Signature:
        ```python
        def __init__(
            self,
            model: str = "ollama_chat/gpt-oss:20b",
            prompt_template: str | None = None,
            temperature: float = 0.7,
            max_tokens: int = 2048,
            adk_reflection_fn: ReflectionFn | None = None,  # NEW
        ) -> None:
        ```

    New Parameter:
        adk_reflection_fn: Optional async callable for ADK-based reflection.
            When provided, used instead of litellm.acompletion().
            When None, falls back to LiteLLM (backwards compatible).

    Behavior:
        - If adk_reflection_fn is provided:
            - Calls adk_reflection_fn(input_text, input_feedback)
            - Returns proposed text from ADK agent
        - If adk_reflection_fn is None:
            - Uses existing litellm.acompletion() path
            - No behavior change from current implementation
    """

    pass

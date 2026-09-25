r"""ADK-based reflection function factory.

This module provides the factory function for creating reflection functions
that use Google ADK agents. The returned function can be passed to
AsyncReflectiveMutationProposer as the adk_reflection_fn parameter.

Terminology:
    - **component_text**: The current text content of a component being evolved
    - **trial**: One performance record {feedback, trajectory}
    - **feedback**: Critic evaluation {score, feedback_text, feedback_*} (stochastic)
    - **trajectory**: Execution record {input, output, trace} (deterministic)
    - **trials**: Collection of trial records for reflection
    - **proposed_component_text**: The improved text for the same component

Attributes:
    create_adk_reflection_fn (function): Factory that creates a ReflectionFn
        using an ADK LlmAgent for reflection. The returned function produces
        ``(proposed_text, reasoning)`` tuples. An optional
        ``timeout_seconds`` reaches the executor, and a timed-out reflection
        raises ``ReflectionTimeoutError``. A proposal whose last model
        response reports a length stop, or that opens one of
        ``reasoning_tags`` without closing it, raises
        ``IncompleteProposalError``.
    is_length_stop (function): Whether a finish reason (ADK enum, its name
        in any case, or litellm's ``length``) marks output cut off at the
        token limit.
    ADKReflectionFn (class): Call signature of the function that
        ``create_adk_reflection_fn`` returns; it accepts ``component_name``
        by keyword and is assignable to ``ReflectionFn``.

Examples:
    Create a reflection function with custom agent:

    ```python
    from google.adk.agents import LlmAgent
    from google.adk.models.lite_llm import LiteLlm
    from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
    from gepa_adk.adapters.execution.agent_executor import AgentExecutor

    agent = LlmAgent(
        name="reflector",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="Improve: {component_text}\nTrials: {trials}",
    )
    executor = AgentExecutor()
    reflection_fn = create_adk_reflection_fn(agent, executor=executor)
    ```

See Also:
    - [`gepa_adk.engine.proposer`][gepa_adk.engine.proposer]: Proposer that uses
      reflection functions.
"""

__all__ = [
    "ADKReflectionFn",
    "create_adk_reflection_fn",
    "is_length_stop",
]

import json
from collections.abc import Sequence
from typing import Any, Protocol

import structlog

from gepa_adk.domain.exceptions import IncompleteProposalError, ReflectionTimeoutError
from gepa_adk.ports.agent_executor import AgentExecutorProtocol, ExecutionStatus
from gepa_adk.utils.events import extract_reasoning_from_events

logger = structlog.get_logger(__name__)

_LENGTH_STOP_NAMES = frozenset({"MAX_TOKENS", "LENGTH"})
_DEFAULT_REASONING_TAGS: tuple[str, ...] = ("think", "thinking", "reasoning")


def is_length_stop(finish_reason: Any) -> bool:
    """Report whether a finish reason marks output cut off at the token limit.

    Args:
        finish_reason: A ``google.genai.types.FinishReason`` member, its name
            as a string in any case, litellm's ``"length"``, or ``None``.

    Returns:
        True when the reason is ``MAX_TOKENS`` or ``LENGTH`` (case-insensitive);
        False for ``None``, an empty value or any other reason.

    Examples:
        ```python
        from google.genai import types

        is_length_stop(types.FinishReason.MAX_TOKENS)  # True
        is_length_stop("length")  # True
        is_length_stop("STOP")  # False
        is_length_stop(None)  # False
        ```
    """
    if finish_reason is None or finish_reason == "":
        return False
    name = getattr(finish_reason, "name", None)
    text = name if isinstance(name, str) else str(finish_reason)
    return text.upper() in _LENGTH_STOP_NAMES


def _last_finish_reason(events: Sequence[Any] | None) -> Any:
    """Return the finish reason of the last event that carries one.

    Args:
        events: Captured ADK events, or ``None``.

    Returns:
        The ``finish_reason`` of the last event whose ``finish_reason`` is not
        ``None``, or ``None`` when there are no events or none carries one.
    """
    for event in reversed(events or []):
        finish_reason = getattr(event, "finish_reason", None)
        if finish_reason is not None:
            return finish_reason
    return None


def _unterminated_tag(text: str, tags: Sequence[str]) -> str | None:
    """Return the reasoning tag the text opens with but never closes.

    Args:
        text: Proposed component text.
        tags: Reasoning tag names to check, without angle brackets.

    Returns:
        The first tag in ``tags`` that opens the stripped text (``<tag>`` or
        ``<tag `` with attributes, case-insensitive) while no ``</tag>``
        occurs anywhere in it; ``None`` otherwise. A tag in the middle of the
        text is not checked.
    """
    lowered = text.strip().lower()
    for tag in tags:
        name = tag.lower()
        opens = lowered.startswith(f"<{name}>") or lowered.startswith(f"<{name} ")
        if opens and f"</{name}>" not in lowered:
            return tag
    return None


def _incomplete_reason(
    raw_text: str, captured: Sequence[Any] | None, tags: Sequence[str]
) -> str | None:
    """Return why a proposal is incomplete, or None when it is complete.

    Args:
        raw_text: Proposed component text.
        captured: Captured ADK events of the reflection run.
        tags: Reasoning tag names to check for an unterminated opening.

    Returns:
        The finish reason name (upper-cased) for a length stop on the last
        event carrying a finish reason, ``"unterminated_<tag>"`` for an
        unclosed opening reasoning tag, or ``None``.
    """
    finish = _last_finish_reason(captured)
    if is_length_stop(finish):
        name = getattr(finish, "name", None)
        return name if isinstance(name, str) else str(finish).upper()
    tag = _unterminated_tag(raw_text, tags)
    if tag is not None:
        return f"unterminated_{tag}"
    return None


class ADKReflectionFn(Protocol):
    """Call signature of the reflection function built from an ADK agent.

    It matches ``ReflectionFn`` positionally, so the proposer accepts it, and
    also names its third parameter so callers may pass ``component_name`` by
    keyword or omit it.

    Examples:
        ```python
        reflect: ADKReflectionFn = create_adk_reflection_fn(agent, executor=executor)
        proposed, reasoning = await reflect(
            "Be helpful", [], component_name="instruction"
        )
        ```
    """

    async def __call__(
        self,
        component_text: str,
        trials: list[dict[str, Any]],
        component_name: str = "",
    ) -> tuple[str, str | None]:
        """Propose improved text for one component.

        Args:
            component_text: The current component text to improve.
            trials: Trial records from evaluation.
            component_name: Name of the component being evolved.

        Returns:
            Tuple of (proposed_component_text, reasoning).
        """
        ...


def create_adk_reflection_fn(
    reflection_agent: Any,  # LlmAgent from google.adk.agents
    executor: AgentExecutorProtocol,
    output_key: str = "proposed_component_text",
    timeout_seconds: int | None = None,
    reasoning_tags: Sequence[str] = _DEFAULT_REASONING_TAGS,
) -> ADKReflectionFn:
    """Create a reflection function from an ADK LlmAgent.

    This factory function creates an async callable that uses the Google ADK
    framework for reflection. The returned function can be passed to
    AsyncReflectiveMutationProposer as the adk_reflection_fn parameter.

    The caller is responsible for selecting the appropriate reflection agent.
    See ``gepa_adk.api.evolve()`` for the standard wiring pattern.

    Args:
        reflection_agent: ADK LlmAgent configured with instruction containing
            `{component_text}` and `{trials}` placeholders. The agent's
            instruction should include logic for improving text based on
            trial results.
        executor: AgentExecutorProtocol implementation for unified agent
            execution. Handles session management and execution, enabling
            feature parity across all agent types.
        output_key: Key in session state where ADK stores the agent's output.
            Defaults to "proposed_component_text". When set, the agent's output_key
            is configured to this value, and output is retrieved from session
            state after execution. Falls back to event-based extraction if
            the output_key is not found in session state.
        timeout_seconds: Seconds the reflection agent may run per call. Passed
            to ``executor.execute_agent`` as ``timeout_seconds`` only when not
            ``None``; ``None`` (default) keeps the executor's own default.
        reasoning_tags: Reasoning tag names (without angle brackets) that
            mark an incomplete proposal when the stripped text opens with one
            of them and never closes it. Matched case-insensitively. Defaults
            to ``("think", "thinking", "reasoning")``.

    Returns:
        Async callable matching ReflectionFn signature that generates proposed
        component text via the ADK agent. Typed as ``ADKReflectionFn`` so its
        ``component_name`` parameter may also be passed by keyword.

    Raises:
        RuntimeError: If ADK agent execution fails (propagated from executor).
        ReflectionTimeoutError: From the returned callable, when the executor
            reports ``ExecutionStatus.TIMEOUT``.
        IncompleteProposalError: From the returned callable, when the last
            captured event with a finish reason reports a length stop, or the
            proposal opens one of ``reasoning_tags`` without closing it.

    Examples:
        Basic usage with executor:

        ```python
        from google.adk.agents import LlmAgent
        from google.adk.models.lite_llm import LiteLlm
        from gepa_adk.adapters.execution.agent_executor import AgentExecutor
        from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

        agent = LlmAgent(
            name="InstructionReflector",
            model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
            instruction=\"\"\"Improve this component text:
            {component_text}

            Based on these trials:
            {trials}

            Return proposed component text only.\"\"\"
        )

        executor = AgentExecutor()
        reflection_fn = create_adk_reflection_fn(agent, executor=executor)
        trials = [{"input": "Hi", "output": "Hey", "feedback": {"score": 0.5}}]
        proposed = await reflection_fn("Be helpful", trials, "instruction")
        ```

    See Also:
        - [`gepa_adk.engine.proposer`][gepa_adk.engine.proposer]: Module containing
          ReflectionFn type alias and AsyncReflectiveMutationProposer class.
        - [`gepa_adk.api.evolve`][gepa_adk.api.evolve]: Standard wiring pattern
          for constructing the reflection chain.

    Notes:
        Opens a fresh ADK session for each invocation via AgentExecutor, ensuring
        complete isolation between reflection operations. State is initialized with
        component_text (str) and trials (JSON-serialized list of trial records).
        A timed-out execution logs ``reflection.timeout`` and raises
        ``ReflectionTimeoutError``; ``reflection.empty_response`` is logged only
        for a completed run that produced no text. An incomplete proposal logs
        ``reflection.incomplete`` at warning and raises
        ``IncompleteProposalError``; the length check runs before the
        empty-response path, so a length stop with no text is incomplete.
    """
    from uuid import uuid4

    timeout_source = "config" if timeout_seconds is not None else "executor_default"
    timeout_kwargs: dict[str, Any] = (
        {"timeout_seconds": timeout_seconds} if timeout_seconds is not None else {}
    )

    # Configure output_key on agent if not already set
    # This enables ADK's automatic output storage to session.state
    if output_key and (
        not hasattr(reflection_agent, "output_key") or not reflection_agent.output_key
    ):
        reflection_agent.output_key = output_key
        logger.debug(
            "reflection.output_key.configured",
            output_key=output_key,
            agent_name=getattr(reflection_agent, "name", "unknown"),
        )

    async def reflect(
        component_text: str,
        trials: list[dict[str, Any]],
        component_name: str = "",
    ) -> tuple[str, str | None]:
        """Reflect on component text using ADK agent to generate proposed version.

        Uses the configured ADK reflection agent to analyze the current component
        text and trials, then generates proposed component text based on the
        performance results.

        Args:
            component_text: The current component text to improve.
            trials: List of trial records from evaluation. Each trial contains
                input, output, feedback, and optional trajectory.
            component_name: Component name passed by the proposer. Logged
                for observability but not used for agent selection (caller
                pre-selects the agent). Defaults to empty string, which the
                logs and ``ReflectionTimeoutError`` report as ``"unknown"``.

        Returns:
            Tuple of (proposed_component_text, reasoning). The proposed text
            is empty string if the agent produces no output. Reasoning is
            extracted from thought-tagged parts of captured events, or
            None if no thinking content is available.

        Raises:
            RuntimeError: If ADK agent execution fails. The exception is logged
                and re-raised for upstream handling.
            ReflectionTimeoutError: If the executor reports a timeout. It is
                logged as ``reflection.timeout`` and not retried here.
            IncompleteProposalError: If the last model response reports a
                length stop or the text opens a reasoning tag it never
                closes. It is logged as ``reflection.incomplete``.

        Notes:
            Opens a unique session with fresh state for each invocation via
            AgentExecutor, ensuring isolation between reflection operations.
            The configured timeout, if any, is passed to the executor, and the
            start log records it with its source. Completeness is checked
            before the empty-response handling.
        """
        # Generate unique session ID for this reflection
        session_id = f"reflect_{uuid4()}"

        # Log reflection start
        logger.info(
            "reflection.start",
            session_id=session_id,
            component_text_length=len(component_text),
            trial_count=len(trials),
            component_name=component_name or "unknown",
            timeout_seconds=timeout_seconds,
            timeout_source=timeout_source,
        )

        # Prepare session state for template substitution
        session_state: dict[str, Any] = {
            "component_text": component_text,
            "trials": json.dumps(trials),
        }

        # Simple trigger message - data is in session state via template placeholders
        user_message = "Please improve the component text based on the trial results."

        try:
            result = await executor.execute_agent(
                agent=reflection_agent,
                input_text=user_message,
                session_state=session_state,
                **timeout_kwargs,
            )

            if result.status == ExecutionStatus.TIMEOUT:
                component = component_name or "unknown"
                logger.warning(
                    "reflection.timeout",
                    session_id=result.session_id,
                    component=component,
                    timeout_seconds=timeout_seconds,
                    timeout_source=timeout_source,
                )
                raise ReflectionTimeoutError(component, timeout_seconds)

            if result.status == ExecutionStatus.FAILED:
                logger.error(
                    "reflection.error",
                    session_id=result.session_id,
                    error=result.error_message,
                )
                raise RuntimeError(result.error_message or "Executor returned FAILED")

            proposed_component_text = result.extracted_value or ""
            captured = getattr(result, "captured_events", None)

            incomplete = _incomplete_reason(
                proposed_component_text, captured, reasoning_tags
            )
            if incomplete is not None:
                component = component_name or "unknown"
                logger.warning(
                    "reflection.incomplete",
                    session_id=result.session_id,
                    component=component,
                    finish_reason=incomplete,
                    response_length=len(proposed_component_text),
                )
                raise IncompleteProposalError(
                    component,
                    finish_reason=incomplete,
                    raw_text=proposed_component_text,
                )

            # Extract reasoning from captured events
            reasoning = extract_reasoning_from_events(captured)
            if reasoning:
                logger.debug(
                    "reflection.reasoning_captured",
                    reasoning_length=len(reasoning),
                )

            # Log reflection complete
            logger.info(
                "reflection.complete",
                session_id=result.session_id,
                response_length=len(proposed_component_text),
            )

            # Handle empty response
            if not proposed_component_text:
                logger.warning(
                    "reflection.empty_response",
                    session_id=result.session_id,
                )
                return ("", reasoning)

            return (proposed_component_text, reasoning)

        except (ReflectionTimeoutError, IncompleteProposalError):
            raise
        except Exception as e:
            logger.error(
                "reflection.error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    return reflect

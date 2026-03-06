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
        ``(proposed_text, reasoning)`` tuples.

Examples:
    Create a reflection function with custom agent:

    ```python
    from google.adk.agents import LlmAgent
    from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
    from gepa_adk.adapters.execution.agent_executor import AgentExecutor

    agent = LlmAgent(
        name="reflector",
        model="gemini-2.5-flash",
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
    "create_adk_reflection_fn",
]

import json
from typing import Any

import structlog

from gepa_adk.engine.proposer import ReflectionFn
from gepa_adk.ports.agent_executor import AgentExecutorProtocol, ExecutionStatus
from gepa_adk.utils.events import extract_reasoning_from_events

logger = structlog.get_logger(__name__)


def create_adk_reflection_fn(
    reflection_agent: Any,  # LlmAgent from google.adk.agents
    executor: AgentExecutorProtocol,
    output_key: str = "proposed_component_text",
) -> ReflectionFn:
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

    Returns:
        Async callable matching ReflectionFn signature that generates proposed
        component text via the ADK agent.

    Raises:
        RuntimeError: If ADK agent execution fails (propagated from executor).

    Examples:
        Basic usage with executor:

        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk.adapters.execution.agent_executor import AgentExecutor
        from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

        agent = LlmAgent(
            name="InstructionReflector",
            model="gemini-2.5-flash",
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

    Note:
        Opens a fresh ADK session for each invocation via AgentExecutor, ensuring
        complete isolation between reflection operations. State is initialized with
        component_text (str) and trials (JSON-serialized list of trial records).
    """
    from uuid import uuid4

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
                pre-selects the agent). Defaults to empty string.

        Returns:
            Tuple of (proposed_component_text, reasoning). The proposed text
            is empty string if the agent produces no output. Reasoning is
            extracted from thought-tagged parts of captured events, or
            None if no thinking content is available.

        Raises:
            RuntimeError: If ADK agent execution fails. The exception is logged
                and re-raised for upstream handling.

        Note:
            Opens a unique session with fresh state for each invocation via
            AgentExecutor, ensuring isolation between reflection operations.
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
            )

            if result.status == ExecutionStatus.FAILED:
                logger.error(
                    "reflection.error",
                    session_id=result.session_id,
                    error=result.error_message,
                )
                raise RuntimeError(result.error_message or "Executor returned FAILED")

            proposed_component_text = result.extracted_value or ""

            # Extract reasoning from captured events
            captured = getattr(result, "captured_events", None)
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

        except Exception as e:
            logger.error(
                "reflection.error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    return reflect

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
    REFLECTION_INSTRUCTION (str): Default instruction template with
        `{component_text}` and `{trials}` placeholders for ADK template
        substitution.
    SESSION_STATE_KEYS (dict[str, type]): Expected keys and types in ADK
        session state for reflection agent access.
    create_adk_reflection_fn (function): Factory that creates a ReflectionFn
        using an ADK LlmAgent for reflection.

Examples:
    Create a reflection function with custom agent:

    ```python
    from google.adk.agents import LlmAgent
    from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

    agent = LlmAgent(
        name="reflector",
        model="gemini-2.5-flash",
        instruction="Improve: {component_text}\nTrials: {trials}",
    )
    reflection_fn = create_adk_reflection_fn(agent)
    ```

See Also:
    - [`gepa_adk.engine.proposer`][gepa_adk.engine.proposer]: Proposer that uses
      reflection functions.
"""

__all__ = [
    "REFLECTION_INSTRUCTION",
    "SESSION_STATE_KEYS",
    "create_adk_reflection_fn",
]

import json
from typing import Any

import structlog

from gepa_adk.engine.proposer import ReflectionFn
from gepa_adk.ports.agent_executor import AgentExecutorProtocol, ExecutionStatus

logger = structlog.get_logger(__name__)

# Session state schema keys for ADK reflection
SESSION_STATE_KEYS = {
    "component_text": str,
    "trials": str,  # JSON-serialized list of trial records
}
"""Expected keys and types in ADK session state for reflection.

The reflection agent accesses these keys via `{key}` template syntax
in its instruction. ADK's `inject_session_state()` automatically
substitutes placeholders with session state values.

Keys:
    component_text: The text content being evolved (str).
    trials: JSON-serialized list of trial records (str). Each trial
        contains {input, output, feedback, trajectory}.
"""

# Default reflection instruction with ADK template placeholders
REFLECTION_INSTRUCTION = """## Component Text to Improve
{component_text}

## Trials
{trials}

Propose an improved version of the component text based on the trials above.
Return ONLY the improved component text, nothing else."""
"""Default instruction template for reflection agents.

Uses ADK's native template substitution syntax (`{key}`) to inject
session state values. ADK automatically replaces these placeholders
with values from `session.state[key]` during instruction processing.

The template contains two placeholders:

- `{component_text}`: The current text being evolved (str)
- `{trials}`: JSON-serialized list of trial records (str)

The instruction is processed by ADK's `inject_session_state()` function
before being sent to the LLM.

Examples:
    Use the default instruction with a custom agent:

    ```python
    from google.adk.agents import LlmAgent
    from gepa_adk.engine.adk_reflection import REFLECTION_INSTRUCTION

    agent = LlmAgent(
        name="reflector",
        model="gemini-2.5-flash",
        instruction=REFLECTION_INSTRUCTION,
    )
    ```

Note:
    This replaces the previous workaround of embedding data in user
    messages via Python f-strings.
"""


def create_adk_reflection_fn(
    reflection_agent: Any | None,  # LlmAgent from google.adk.agents
    executor: AgentExecutorProtocol,
    session_service: Any | None = None,  # BaseSessionService from google.adk.sessions
    output_key: str = "proposed_component_text",
    output_field: str | None = None,
    component_name: str | None = None,
    model: str | None = None,
) -> ReflectionFn:
    """Create a reflection function from an ADK LlmAgent.

    This factory function creates an async callable that uses the Google ADK
    framework for reflection. The returned function can be passed to
    AsyncReflectiveMutationProposer as the adk_reflection_fn parameter.

    Supports automatic agent selection based on component name when
    reflection_agent is None. Use this for component-aware reflection
    where different component types (e.g., output_schema vs instruction)
    require different validation tools and instructions.

    Args:
        reflection_agent: ADK LlmAgent configured with instruction containing
            `{component_text}` and `{trials}` placeholders. The agent's
            instruction should include logic for improving text based on
            trial results. If None, automatic agent selection is used based
            on component_name (requires model parameter).
        executor: AgentExecutorProtocol implementation for unified agent
            execution. Handles session management and execution, enabling
            feature parity across all agent types.
        session_service: Optional session service for state management.
            Defaults to InMemorySessionService if None. Use custom services
            (e.g., DatabaseSessionService) for production deployments requiring
            session persistence.
        output_key: Key in session state where ADK stores the agent's output.
            Defaults to "proposed_component_text". When set, the agent's output_key
            is configured to this value, and output is retrieved from session
            state after execution. Falls back to event-based extraction if
            the output_key is not found in session state.
        output_field: Optional field name to extract from structured output.
            When the reflection agent has an output_schema (Pydantic model),
            the output is stored as a dict in session state. This parameter
            specifies which field to extract from that dict. If None (default),
            the entire output is returned as a string.
        component_name: Optional component name for automatic agent selection.
            When reflection_agent is None, this is used to select the appropriate
            reflection agent from the component registry. Examples: "output_schema",
            "instruction". If None and reflection_agent is None, raises ValueError.
        model: Model name/identifier for automatic agent selection.
            Required when reflection_agent is None. Examples: "gemini-2.0-flash",
            "gemini-2.5-flash". Ignored when reflection_agent is provided.

    Returns:
        Async callable matching ReflectionFn signature that generates proposed
        component text via the ADK agent.

    Raises:
        Exception: If ADK agent execution fails (propagated from ADK Runner).

    Examples:
        Basic usage with executor:

        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk.adapters.agent_executor import AgentExecutor
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
        proposed = await reflection_fn("Be helpful", trials)
        ```

        With output_schema for structured output (e.g., schema evolution):

        ```python
        from pydantic import BaseModel, Field


        class SchemaProposal(BaseModel):
            class_definition: str = Field(description="The Pydantic class definition")
            reasoning: str = Field(description="Why this change was made")


        agent = LlmAgent(
            name="schema_reflector",
            model="gemini-2.5-flash",
            instruction="Improve the schema based on feedback...",
            output_schema=SchemaProposal,
        )

        # Extract only the class_definition field from structured output
        executor = AgentExecutor()
        reflection_fn = create_adk_reflection_fn(
            agent,
            executor=executor,
            output_field="class_definition",
        )
        ```

    See Also:
        - [`gepa_adk.engine.proposer`][gepa_adk.engine.proposer]: Module containing
          ReflectionFn type alias and AsyncReflectiveMutationProposer class.

    Note:
        Opens a fresh ADK session for each invocation via AgentExecutor, ensuring
        complete isolation between reflection operations. State is initialized with
        component_text (str) and trials (JSON-serialized list of trial records).
    """
    from uuid import uuid4

    from google.adk.sessions import InMemorySessionService

    # Store configuration for potential runtime auto-selection
    # If reflection_agent is None, auto-selection happens at call time using component_name
    _use_auto_selection = reflection_agent is None
    _auto_selection_model = model

    if _use_auto_selection and not model:
        raise ValueError(
            "model parameter is required when reflection_agent is None. "
            "Provide a model name (e.g., 'gemini-2.0-flash') to enable "
            "component-aware auto-selection of reflection agents."
        )

    # If component_name provided at creation AND agent is None, do creation-time selection
    if component_name and reflection_agent is None:
        from gepa_adk.engine.reflection_agents import get_reflection_agent

        assert model is not None  # Guaranteed by earlier validation
        reflection_agent = get_reflection_agent(component_name, model)
        _use_auto_selection = False  # Agent now selected, no need for runtime selection
        logger.info(
            "reflection.agent.auto_selected_at_creation",
            component_name=component_name,
            model=model,
            agent_name=getattr(reflection_agent, "name", "unknown"),
        )

    # Default to InMemorySessionService if not provided
    if session_service is None:
        session_service = InMemorySessionService()

    # Configure output_key on agent if not already set
    # This enables ADK's automatic output storage to session.state
    # Skip if using runtime auto-selection (reflection_agent will be None)
    if (
        reflection_agent is not None
        and output_key
        and (
            not hasattr(reflection_agent, "output_key")
            or not reflection_agent.output_key
        )
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
        component_name: str | None = None,
    ) -> str:
        """Reflect on component text using ADK agent to generate proposed version.

        Uses the configured ADK reflection agent to analyze the current component
        text and trials, then generates proposed component text based on the
        performance results.

        When reflection_agent was not provided at creation time (None), the
        component_name parameter is used to auto-select the appropriate reflection
        agent from the component registry.

        Args:
            component_text: The current component text to improve.
            trials: List of trial records from evaluation. Each trial contains
                input, output, feedback, and optional trajectory.
            component_name: Optional component name for runtime auto-selection.
                Used when reflection_agent was None at creation time. Examples:
                "output_schema", "instruction". If None and auto-selection is
                needed, uses the default text reflection agent.

        Returns:
            Proposed component text generated by the reflection agent. Returns
            empty string if the agent produces no output.

        Raises:
            Exception: If ADK agent execution fails. The exception is logged
                and re-raised for upstream handling.

        Examples:
            Call with component_name for auto-selection:

            ```python
            executor = AgentExecutor()
            reflection_fn = create_adk_reflection_fn(
                reflection_agent=None,
                executor=executor,
                model="gemini-2.0-flash",
            )
            trials = [
                {"input": "Hi", "output": "Hello", "feedback": {"score": 0.8}},
            ]
            # Auto-selects schema agent for output_schema component
            proposed = await reflection_fn("class Schema...", trials, "output_schema")
            ```

        Note:
            Opens a unique session with fresh state for each invocation via
            AgentExecutor, ensuring isolation between reflection operations.
        """
        # Runtime auto-selection if needed
        nonlocal reflection_agent
        agent_to_use = reflection_agent

        if _use_auto_selection:
            if not component_name:
                # No component_name provided - use default text agent
                from gepa_adk.engine.reflection_agents import (
                    create_text_reflection_agent,
                )

                agent_to_use = create_text_reflection_agent(_auto_selection_model)
                logger.debug(
                    "reflection.agent.runtime_default",
                    model=_auto_selection_model,
                )
            else:
                # Component_name provided - auto-select appropriate agent
                from gepa_adk.engine.reflection_agents import get_reflection_agent

                agent_to_use = get_reflection_agent(
                    component_name, _auto_selection_model
                )
                logger.info(
                    "reflection.agent.auto_selected_at_runtime",
                    component_name=component_name,
                    model=_auto_selection_model,
                    agent_name=getattr(agent_to_use, "name", "unknown"),
                )

            # Configure output_key on runtime-selected agent
            if output_key and (
                not hasattr(agent_to_use, "output_key") or not agent_to_use.output_key
            ):
                agent_to_use.output_key = output_key

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
                agent=agent_to_use,
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
                return ""

            return proposed_component_text

        except Exception as e:
            logger.error(
                "reflection.error",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    return reflect

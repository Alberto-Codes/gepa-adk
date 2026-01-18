r"""ADK-based reflection function factory.

This module provides the factory function for creating reflection functions
that use Google ADK agents. The returned function can be passed to
AsyncReflectiveMutationProposer as the adk_reflection_fn parameter.

Terminology:
    - **component_text**: The current text content of a component being evolved
    - **trial**: One performance record {input, output, feedback, trajectory}
    - **trials**: Collection of trial records for reflection
    - **proposed_component_text**: The improved text for the same component

Attributes:
    SESSION_STATE_KEYS (dict): Expected keys and types in ADK session state
        for reflection agent access.
    create_adk_reflection_fn (function): Factory that creates a ReflectionFn
        using an ADK LlmAgent for reflection.

Examples:
    ```python
    from google.adk.agents import LlmAgent
    from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

    agent = LlmAgent(
        name="reflector",
        model="gemini-2.0-flash",
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

logger = structlog.get_logger(__name__)

# Session state schema keys for ADK reflection
SESSION_STATE_KEYS = {
    "component_text": str,
    "trials": str,  # JSON-serialized list of trial records
}
"""Expected keys and types in ADK session state for reflection.

The reflection agent accesses these keys via {key} template syntax
in its prompt template:
- component_text: The text being evolved
- trials: JSON-serialized list of {input, output, feedback, trajectory} records
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

Placeholders:
    - {component_text}: The current text being evolved (string)
    - {trials}: JSON-serialized list of trial records (string)

The instruction is processed by ADK's `inject_session_state()` function
before being sent to the LLM. This replaces the previous workaround of
embedding data in user messages via Python f-strings.

Example:
    When session state contains:
    - component_text: "Be helpful"
    - trials: '[{"score": 0.5}]'

    The instruction becomes:
    "## Component Text to Improve
    Be helpful

    ## Trials
    [{"score": 0.5}]

    Propose an improved version..."
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
        reflection_agent: ADK LlmAgent configured with prompt template
            containing {component_text} and {trials} placeholders.
            The agent's prompt should include logic for improving text
            based on trial results.
        session_service: Optional session service for state management.
            Defaults to InMemorySessionService if None. Use custom services
            (e.g., DatabaseSessionService) for production deployments requiring
            session persistence.

    Returns:
        Async callable matching ReflectionFn signature that generates proposed
        component text via the ADK agent.

    Examples:
        Basic usage with default session service:

        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

        agent = LlmAgent(
            name="InstructionReflector",
            model="gemini-2.0-flash",
            instruction=\"\"\"Improve this component text:
            {component_text}

            Based on these trials:
            {trials}

            Return proposed component text only.\"\"\"
        )

        reflection_fn = create_adk_reflection_fn(agent)
        trials = [{"input": "Hi", "output": "Hey", "feedback": {"score": 0.5}}]
        proposed = await reflection_fn("Be helpful", trials)
        ```

        With custom session service:

        ```python
        from google.adk.sessions import DatabaseSessionService

        db_service = DatabaseSessionService(db_url="sqlite:///sessions.db")
        reflection_fn = create_adk_reflection_fn(agent, session_service=db_service)
        ```

    Note:
        Session isolation is maintained by creating a fresh ADK session for each
        invocation, ensuring complete isolation between reflection operations.
        State is initialized with component_text (str) and trials
        (JSON-serialized list of trial records).
    """
    from uuid import uuid4

    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai.types import Content, Part

    from gepa_adk.utils.events import extract_final_output

    # Default to InMemorySessionService if not provided
    if session_service is None:
        session_service = InMemorySessionService()

    async def reflect(
        component_text: str,
        trials: list[dict[str, Any]],
    ) -> str:
        """Reflect on component text using ADK agent to generate proposed version.

        Uses the configured ADK reflection agent to analyze the current component
        text and trials, then generates proposed component text based on the
        performance results.

        Args:
            component_text: The current component text to improve.
            trials: List of trial records from evaluation. Each trial contains
                input, output, feedback, and optional trajectory.

        Returns:
            Proposed component text generated by the reflection agent.

        Examples:
            Basic reflection with trials:

            ```python
            trials = [
                {"input": "Hello", "output": "Hi!", "feedback": {"score": 0.8}},
                {"input": "Goodbye", "output": "Bye", "feedback": {"score": 0.6}},
            ]
            proposed = await reflect(component_text="Be helpful", trials=trials)
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
            component_text_length=len(component_text),
            trial_count=len(trials),
        )

        try:
            # Create session with initial state
            session_state: dict[str, Any] = {
                "component_text": component_text,
                "trials": json.dumps(trials),
            }

            await session_service.create_session(
                app_name="gepa_reflection",
                user_id="reflection",
                session_id=session_id,
                state=session_state,
            )

            # Create runner for this reflection
            runner = Runner(
                agent=reflection_agent,
                app_name="gepa_reflection",
                session_service=session_service,
            )

            # Log template substitution setup
            logger.debug(
                "reflection.template_state",
                session_id=session_id,
                state_keys=list(session_state.keys()),
                component_text_length=len(component_text),
                trials_length=len(session_state["trials"]),
            )

            # Simple trigger message - data is in session state via template placeholders
            # ADK's inject_session_state() will substitute {component_text} and {trials}
            # in the agent's instruction from session.state values
            user_message = "Please improve the component text based on the trial results."

            # Execute reflection via Runner.run_async
            events = []
            async for event in runner.run_async(
                user_id="reflection",
                session_id=session_id,
                new_message=Content(
                    role="user",
                    parts=[Part(text=user_message)],
                ),
            ):
                events.append(event)

            proposed_component_text = extract_final_output(events)

            # Log reflection complete
            logger.info(
                "reflection.complete",
                session_id=session_id,
                response_length=len(proposed_component_text),
            )

            # Handle empty response - fallback to empty string
            if not proposed_component_text:
                logger.warning(
                    "reflection.empty_response",
                    session_id=session_id,
                )
                return ""

            return proposed_component_text

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

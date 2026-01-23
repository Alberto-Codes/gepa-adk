"""AgentExecutor adapter for unified agent execution.

This module implements the AgentExecutorProtocol, providing a unified
execution path for all ADK agent types (generator, critic, reflection)
with consistent session management, event capture, and result handling.

Attributes:
    AgentExecutor (class): Implementation of AgentExecutorProtocol.

Examples:
    Basic usage:

    ```python
    from gepa_adk.adapters.agent_executor import AgentExecutor
    from gepa_adk.ports.agent_executor import ExecutionStatus

    executor = AgentExecutor()
    result = await executor.execute_agent(
        agent=my_agent,
        input_text="Hello, world!",
    )
    if result.status == ExecutionStatus.SUCCESS:
        print(f"Output: {result.extracted_value}")
    ```

    With instruction override (for evolution):

    ```python
    result = await executor.execute_agent(
        agent=my_agent,
        input_text="Hello!",
        instruction_override="You are a formal assistant.",
    )
    # Original agent.instruction unchanged
    ```

See Also:
    - [`gepa_adk.ports.agent_executor`][gepa_adk.ports.agent_executor]:
        Protocol and type definitions.

Note:
    This adapter follows hexagonal architecture principles, implementing
    the AgentExecutorProtocol from the ports layer.
"""

import asyncio
import time
from typing import Any
from uuid import uuid4

import structlog
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService, Session
from google.genai import types

from gepa_adk.domain.exceptions import EvolutionError
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus
from gepa_adk.utils.events import extract_final_output, extract_output_from_state

logger = structlog.get_logger(__name__)


class SessionNotFoundError(EvolutionError):
    """Raised when a requested session does not exist.

    Attributes:
        session_id (str): The session ID that was not found.

    Examples:
        Handling session not found:

        ```python
        from gepa_adk.adapters.agent_executor import SessionNotFoundError

        try:
            result = await executor.execute_agent(
                agent=agent,
                input_text="Hello",
                existing_session_id="invalid_session",
            )
        except SessionNotFoundError as e:
            print(f"Session not found: {e.session_id}")
        ```

    Note:
        This exception is raised when existing_session_id is provided but
        the session does not exist in the session service.
    """

    def __init__(self, session_id: str) -> None:
        """Initialize SessionNotFoundError.

        Args:
            session_id: The session ID that was not found.
        """
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class AgentExecutor:
    """Unified agent execution adapter.

    Provides a single execution path for all ADK agent types (generator, critic,
    reflection) with consistent session management, event capture, and result
    handling.

    Attributes:
        _session_service (BaseSessionService): ADK session service for state management.
        _app_name (str): Application name for ADK runner.

    Examples:
        Basic usage:

        ```python
        executor = AgentExecutor()
        result = await executor.execute_agent(
            agent=my_agent,
            input_text="Hello, world!",
        )
        if result.status == ExecutionStatus.SUCCESS:
            print(f"Output: {result.extracted_value}")
        ```

        With custom session service:

        ```python
        from google.adk.sessions import InMemorySessionService

        session_service = InMemorySessionService()
        executor = AgentExecutor(session_service=session_service)
        ```

    Note:
        This class implements AgentExecutorProtocol for dependency injection
        and testing. All ADK-specific logic is encapsulated here.
    """

    def __init__(
        self,
        session_service: BaseSessionService | None = None,
        app_name: str = "gepa_executor",
    ) -> None:
        """Initialize AgentExecutor.

        Args:
            session_service: ADK session service for state management.
                If None, creates an InMemorySessionService.
            app_name: Application name for ADK runner. Defaults to "gepa_executor".

        Examples:
            Default initialization:

            ```python
            executor = AgentExecutor()
            ```

            With custom app name:

            ```python
            executor = AgentExecutor(app_name="my_app")
            ```

        Note:
            The session service is used for all agent executions. Creating
            a shared executor allows session state to be shared between
            agent executions when desired.
        """
        self._session_service = session_service or InMemorySessionService()
        self._app_name = app_name
        self._logger = logger.bind(component="AgentExecutor", app_name=app_name)

    async def _create_session(
        self,
        user_id: str,
        session_state: dict[str, Any] | None = None,
    ) -> Session:
        """Create a new session with optional initial state.

        Args:
            user_id: User identifier for the session.
            session_state: Initial state to inject into the session.

        Returns:
            Created ADK Session object.

        Note:
            Session state is used for template variable substitution in
            agent instructions (e.g., {component_text} and {trials}).
        """
        session_id = f"exec_{uuid4()}"

        self._logger.debug(
            "session.creating",
            session_id=session_id,
            user_id=user_id,
            has_initial_state=session_state is not None,
        )

        session = await self._session_service.create_session(
            app_name=self._app_name,
            user_id=user_id,
            session_id=session_id,
            state=session_state,
        )

        self._logger.debug(
            "session.created",
            session_id=session.id,
        )

        return session

    async def _get_session(self, session_id: str, user_id: str) -> Session:
        """Retrieve an existing session by ID.

        Args:
            session_id: The session ID to retrieve.
            user_id: User identifier for the session.

        Returns:
            Existing ADK Session object.

        Raises:
            SessionNotFoundError: If the session does not exist.

        Note:
            This method is used when existing_session_id is provided to
            enable session sharing between agents.
        """
        session = await self._session_service.get_session(
            app_name=self._app_name,
            user_id=user_id,
            session_id=session_id,
        )

        if session is None:
            raise SessionNotFoundError(session_id)

        self._logger.debug(
            "session.retrieved",
            session_id=session_id,
        )

        return session

    async def _get_or_create_session(
        self,
        session_id: str,
        user_id: str,
        session_state: dict[str, Any] | None = None,
    ) -> Session:
        """Get an existing session or create a new one with the specified ID.

        Implements "get or create" semantics for session management. If the
        session exists, returns it. If not, creates a new session with the
        specified ID and optional initial state.

        Args:
            session_id: The session ID to retrieve or create.
            user_id: User identifier for the session.
            session_state: Initial state to inject if creating a new session.
                Ignored if session already exists.

        Returns:
            ADK Session object (existing or newly created).

        Note:
            Only applies initial state when creating new sessions. Existing
            sessions retain their current state regardless of session_state
            parameter.
        """
        # Try to get existing session first
        session = await self._session_service.get_session(
            app_name=self._app_name,
            user_id=user_id,
            session_id=session_id,
        )

        if session is not None:
            self._logger.debug(
                "session.retrieved",
                session_id=session_id,
            )
            return session

        # Session doesn't exist, create it with the specified ID
        self._logger.debug(
            "session.creating_with_id",
            session_id=session_id,
            user_id=user_id,
            has_initial_state=session_state is not None,
        )

        session = await self._session_service.create_session(
            app_name=self._app_name,
            user_id=user_id,
            session_id=session_id,
            state=session_state,
        )

        self._logger.debug(
            "session.created",
            session_id=session.id,
        )

        return session

    def _apply_overrides(
        self,
        agent: Any,
        instruction_override: str | None,
        output_schema_override: Any | None,
    ) -> Any:
        """Apply instruction and schema overrides to create modified agent copy.

        Args:
            agent: Original ADK LlmAgent.
            instruction_override: If provided, replaces agent instruction.
            output_schema_override: If provided, replaces output schema.

        Returns:
            Modified agent copy (or original if no overrides).

        Note:
            Creates a shallow copy of the agent with overridden attributes.
            The original agent is never modified.
        """
        if instruction_override is None and output_schema_override is None:
            return agent

        # Import LlmAgent here to avoid circular imports
        from google.adk.agents import LlmAgent

        # Create a copy with overrides
        # LlmAgent doesn't have a simple copy mechanism, so we recreate it
        # with the same parameters but modified instruction/schema
        # Extract agent attributes with proper defaults
        agent_tools = getattr(agent, "tools", None)
        modified_agent = LlmAgent(
            name=agent.name,
            model=agent.model,
            instruction=instruction_override or agent.instruction,
            output_schema=output_schema_override
            or getattr(agent, "output_schema", None),
            output_key=getattr(agent, "output_key", None),
            tools=agent_tools if agent_tools else [],
            before_model_callback=getattr(agent, "before_model_callback", None),
            after_model_callback=getattr(agent, "after_model_callback", None),
        )

        self._logger.debug(
            "agent.overrides_applied",
            instruction_override=instruction_override is not None,
            schema_override=output_schema_override is not None,
        )

        return modified_agent

    async def _execute_runner(
        self,
        runner: Runner,
        session: Session,
        user_id: str,
        input_text: str,
    ) -> list[Any]:
        """Execute the ADK Runner and capture events.

        Args:
            runner: ADK Runner instance.
            session: ADK Session for execution.
            user_id: User identifier.
            input_text: User message to send.

        Returns:
            List of captured ADK events.

        Note:
            This method handles the core Runner.run_async() loop,
            capturing all events for later output extraction.
        """
        content = types.Content(
            role="user",
            parts=[types.Part(text=input_text)],
        )

        events: list[Any] = []

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            events.append(event)

        return events

    async def _execute_with_timeout(
        self,
        runner: Runner,
        session: Session,
        user_id: str,
        input_text: str,
        timeout_seconds: int,
    ) -> tuple[list[Any], bool]:
        """Execute runner with timeout handling.

        Args:
            runner: ADK Runner instance.
            session: ADK Session for execution.
            user_id: User identifier.
            input_text: User message to send.
            timeout_seconds: Maximum execution time.

        Returns:
            Tuple of (captured_events, timed_out).

        Note:
            On timeout, returns partial events captured before timeout.
            Uses asyncio.timeout for cancellation.
        """
        events: list[Any] = []
        timed_out = False

        try:
            async with asyncio.timeout(timeout_seconds):
                events = await self._execute_runner(
                    runner, session, user_id, input_text
                )
        except TimeoutError:
            timed_out = True
            self._logger.warning(
                "execution.timeout",
                session_id=session.id,
                timeout_seconds=timeout_seconds,
                events_captured=len(events),
            )

        return events, timed_out

    async def _extract_output(
        self,
        session: Session,
        events: list[Any],
        agent: Any,
    ) -> str | None:
        """Extract output from session state with event fallback.

        Args:
            session: ADK Session after execution.
            events: Captured events from execution.
            agent: Agent that was executed (for output_key).

        Returns:
            Extracted output string, or None if no output found.

        Note:
            Tries state-based extraction first (using output_key),
            then falls back to event-based extraction.
        """
        # Try state-based extraction first (if agent has output_key)
        output_key = getattr(agent, "output_key", None)
        if output_key:
            # Refresh session state
            refreshed_session = await self._session_service.get_session(
                app_name=self._app_name,
                user_id=session.user_id,
                session_id=session.id,
            )
            if refreshed_session and refreshed_session.state:
                state_output = extract_output_from_state(
                    refreshed_session.state, output_key
                )
                if state_output:
                    self._logger.debug(
                        "output.extracted_from_state",
                        output_key=output_key,
                    )
                    return state_output

        # Fallback to event-based extraction
        event_output = extract_final_output(events)
        if event_output:
            self._logger.debug("output.extracted_from_events")
            return event_output

        return None

    async def execute_agent(
        self,
        agent: Any,
        input_text: str,
        *,
        instruction_override: str | None = None,
        output_schema_override: Any | None = None,
        session_state: dict[str, Any] | None = None,
        existing_session_id: str | None = None,
        timeout_seconds: int = 300,
    ) -> ExecutionResult:
        """Execute an agent and return structured result.

        Runs the specified agent with the given input, optionally applying
        instruction or schema overrides for evolution scenarios. Manages
        session lifecycle and captures execution events.

        Args:
            agent: ADK LlmAgent to execute. The agent's tools, output_key,
                and other ADK features are preserved during execution.
            input_text: User message to send to the agent.
            instruction_override: If provided, replaces the agent's instruction
                for this execution only. Original agent is not modified.
            output_schema_override: If provided, replaces the agent's output
                schema for this execution only (type[BaseModel]). Used for schema evolution.
            session_state: Initial state to inject into the session. Used for
                template variable substitution (e.g., {component_text}).
            existing_session_id: If provided, reuses an existing session instead
                of creating a new one. Useful for critic accessing generator state.
            timeout_seconds: Maximum execution time in seconds. Defaults to 300.
                Execution terminates with TIMEOUT status if exceeded.

        Returns:
            ExecutionResult with status, output, and debugging information.

        Raises:
            SessionNotFoundError: If existing_session_id is provided but session
                does not exist.

        Examples:
            Basic execution:

            ```python
            result = await executor.execute_agent(
                agent=greeter,
                input_text="Hello!",
            )
            print(result.extracted_value)
            ```

            With session state for reflection:

            ```python
            result = await executor.execute_agent(
                agent=reflector,
                input_text="Improve the instruction",
                session_state={
                    "component_text": "Be helpful.",
                    "trials": '[{"score": 0.5}]',
                },
            )
            ```

        Note:
            The agent parameter is typed as Any to avoid coupling to ADK types
            in the ports layer. Implementations should validate that the agent
            is a valid LlmAgent.
        """
        start_time = time.perf_counter()
        user_id = "exec_user"

        self._logger.info(
            "execution.start",
            agent_name=getattr(agent, "name", "unknown"),
            input_length=len(input_text),
            has_instruction_override=instruction_override is not None,
            has_schema_override=output_schema_override is not None,
            has_session_state=session_state is not None,
            existing_session_id=existing_session_id,
            timeout_seconds=timeout_seconds,
        )

        # Get or create session
        session: Session
        if existing_session_id:
            session = await self._get_or_create_session(
                existing_session_id, user_id, session_state
            )
        else:
            session = await self._create_session(user_id, session_state)

        # Apply overrides if provided
        effective_agent = self._apply_overrides(
            agent, instruction_override, output_schema_override
        )

        # Create runner
        runner = Runner(
            agent=effective_agent,
            app_name=self._app_name,
            session_service=self._session_service,
        )

        # Execute with timeout and capture events
        events: list[Any] = []
        timed_out = False
        error_message: str | None = None

        try:
            events, timed_out = await self._execute_with_timeout(
                runner, session, user_id, input_text, timeout_seconds
            )
        except Exception as e:
            error_message = str(e)
            self._logger.error(
                "execution.error",
                session_id=session.id,
                error=error_message,
            )

        # Calculate execution time
        execution_time = time.perf_counter() - start_time

        # Determine status
        if error_message:
            status = ExecutionStatus.FAILED
        elif timed_out:
            status = ExecutionStatus.TIMEOUT
            error_message = f"Execution timed out after {timeout_seconds}s"
        else:
            status = ExecutionStatus.SUCCESS

        # Extract output (even on timeout, we try to get partial results)
        extracted_value: str | None = None
        if status == ExecutionStatus.SUCCESS or (timed_out and events):
            extracted_value = await self._extract_output(session, events, agent)

        self._logger.info(
            "execution.complete",
            session_id=session.id,
            status=status.value,
            execution_time_seconds=execution_time,
            events_captured=len(events),
            has_output=extracted_value is not None,
        )

        return ExecutionResult(
            status=status,
            session_id=session.id,
            extracted_value=extracted_value,
            error_message=error_message,
            execution_time_seconds=execution_time,
            captured_events=events,
        )


__all__ = ["AgentExecutor", "SessionNotFoundError"]

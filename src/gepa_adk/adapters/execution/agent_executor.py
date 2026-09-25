"""AgentExecutor adapter for unified agent execution.

This module implements the AgentExecutorProtocol, providing a unified
execution path for all ADK agent types (generator, critic, reflection)
with consistent session management, event capture, and result handling.
A transient session-service error (sqlite's ``database is locked``) is
retried under the executor's ``RetryPolicy`` in a fresh session.

Attributes:
    AgentExecutor (class): Implementation of AgentExecutorProtocol.
    is_transient_session_error (function): Classifies an exception as a
        transient session-service error worth retrying.

Examples:
    Basic usage:

    ```python
    from gepa_adk.adapters.execution.agent_executor import AgentExecutor
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

    With a custom retry policy for a loaded sqlite store:

    ```python
    from gepa_adk.ports.agent_executor import RetryPolicy

    executor = AgentExecutor(
        session_service=sqlite_service,
        retry_policy=RetryPolicy(max_attempts=5, backoff_seconds=1.0),
    )
    ```

See Also:
    - [`gepa_adk.ports.agent_executor`][gepa_adk.ports.agent_executor]:
        Protocol and type definitions.

Notes:
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
from gepa_adk.ports.agent_executor import (
    ExecutionResult,
    ExecutionStatus,
    RetryPolicy,
)
from gepa_adk.utils.events import extract_final_output, extract_output_from_state

logger = structlog.get_logger(__name__)

_TRANSIENT_MARKER = "database is locked"
_MAX_CHAIN_LINKS = 10


def is_transient_session_error(exc: BaseException) -> bool:
    """Return whether an exception is a transient session-service error.

    Walks the exception, then its ``__cause__`` and ``__context__`` chain,
    and reports True when any link's message contains ``database is
    locked`` (case-insensitive). The walk is cycle-safe and stops after
    ten links.

    Args:
        exc: The exception raised by the session service or the run.

    Returns:
        True when the error is sqlite's lock error, directly or wrapped;
        False otherwise.

    Examples:
        ```python
        import sqlite3

        from gepa_adk.adapters.execution.agent_executor import (
            is_transient_session_error,
        )

        assert is_transient_session_error(
            sqlite3.OperationalError("database is locked")
        )
        assert not is_transient_session_error(RuntimeError("boom"))
        ```

    Notes:
        Timeouts and provider errors are not transient under this rule;
        the executor does not retry them.
    """
    seen: set[int] = set()
    pending: list[BaseException] = [exc]
    while pending and len(seen) < _MAX_CHAIN_LINKS:
        link = pending.pop(0)
        if id(link) in seen:
            continue
        seen.add(id(link))
        if _TRANSIENT_MARKER in str(link).lower():
            return True
        pending.extend(
            nxt for nxt in (link.__cause__, link.__context__) if nxt is not None
        )
    return False


class SessionNotFoundError(EvolutionError):
    """Raised when a requested session does not exist.

    Attributes:
        session_id (str): The session ID that was not found.

    Examples:
        Handling session not found with strict existence checking:

        ```python
        from gepa_adk.adapters.execution.agent_executor import SessionNotFoundError

        try:
            session = await executor._get_session(
                session_id="invalid_session",
                user_id="user_123",
            )
        except SessionNotFoundError as e:
            print(f"Session not found: {e.session_id}")
        ```

    Notes:
        Arises only from strict existence-checking paths like _get_session().
        The execute_agent() method uses get-or-create semantics and will not
        raise this exception.
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
        retry_policy (RetryPolicy): Policy for retrying a transient
            session-service error such as ``database is locked``.
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

    Notes:
        Adapter implements AgentExecutorProtocol for dependency injection
        and testing. All ADK-specific logic is encapsulated here.
    """

    def __init__(
        self,
        session_service: BaseSessionService | None = None,
        app_name: str = "gepa_executor",
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        """Initialize AgentExecutor.

        Args:
            session_service: ADK session service for state management.
                If None, creates an InMemorySessionService.
            app_name: Application name for ADK runner. Defaults to "gepa_executor".
            retry_policy: Policy for retrying a transient session-service
                error. If None, uses ``RetryPolicy()`` (three attempts,
                0.5 s backoff, doubling).

        Examples:
            Default initialization:

            ```python
            executor = AgentExecutor()
            ```

            With custom app name:

            ```python
            executor = AgentExecutor(app_name="my_app")
            ```

            With a custom retry policy:

            ```python
            executor = AgentExecutor(
                session_service=sqlite_service,
                retry_policy=RetryPolicy(max_attempts=5),
            )
            ```

        Notes:
            Creates a shared executor that uses the session service for all
            agent executions, allowing session state to be shared between
            executions when desired.
        """
        self._session_service = session_service or InMemorySessionService()
        self._app_name = app_name
        self.retry_policy = retry_policy or RetryPolicy()
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

        Notes:
            Optional session state enables template variable substitution in
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

        Notes:
            Only performs strict existence checks for sessions that must
            already exist. Callers use this to fail fast instead of creating
            a new session. For get-or-create semantics, use _get_or_create_session.
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

        Notes:
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

        Notes:
            Original agent is preserved by creating a shallow copy with
            overridden attributes. The original agent is never modified.
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

    def _build_content(
        self,
        input_text: str,
        input_content: types.Content | None = None,
    ) -> types.Content:
        """Build Content for agent execution.

        Assembles the Content object to send to the agent. If input_content
        is provided, uses it directly. Otherwise, wraps input_text in a
        Content with a single text Part.

        Args:
            input_text: Text input for the agent.
            input_content: Pre-assembled multimodal Content. Takes precedence
                over input_text when provided.

        Returns:
            Content object for agent execution.

        Notes:
            Serves as the central point for Content assembly, supporting
            both text-only (backward compatible) and multimodal inputs.
        """
        if input_content is not None:
            return input_content

        return types.Content(
            role="user",
            parts=[types.Part(text=input_text)],
        )

    async def _execute_runner(
        self,
        runner: Runner,
        session: Session,
        user_id: str,
        input_text: str,
        input_content: types.Content | None = None,
    ) -> list[Any]:
        """Execute the ADK Runner and capture events.

        Args:
            runner: ADK Runner instance.
            session: ADK Session for execution.
            user_id: User identifier.
            input_text: User message to send (used if input_content is None).
            input_content: Pre-assembled multimodal Content. Takes precedence
                over input_text when provided.

        Returns:
            List of captured ADK events.

        Notes:
            Orchestrates the core Runner.run_async() loop, capturing all
            events for later output extraction.
        """
        content = self._build_content(input_text, input_content)

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
        input_content: types.Content | None = None,
    ) -> tuple[list[Any], bool]:
        """Execute runner with timeout handling.

        Args:
            runner: ADK Runner instance.
            session: ADK Session for execution.
            user_id: User identifier.
            input_text: User message to send (used if input_content is None).
            timeout_seconds: Maximum execution time.
            input_content: Pre-assembled multimodal Content. Takes precedence
                over input_text when provided.

        Returns:
            Tuple of (captured_events, timed_out).

        Notes:
            On timeout, returns partial events captured before timeout.
            Uses asyncio.timeout for cancellation.
        """
        events: list[Any] = []
        timed_out = False

        try:
            async with asyncio.timeout(timeout_seconds):
                events = await self._execute_runner(
                    runner, session, user_id, input_text, input_content
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

        Notes:
            Output extraction prioritizes state-based approach (using
            output_key), then falls back to event-based extraction.
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

    async def _open_session(
        self,
        user_id: str,
        session_state: dict[str, Any] | None,
        existing_session_id: str | None,
    ) -> Session:
        """Open the session for one execution attempt.

        Args:
            user_id: User identifier for the session.
            session_state: Initial state to inject into the session.
            existing_session_id: Session ID for get-or-create semantics, or
                None to create a fresh session.

        Returns:
            The ADK Session to run the attempt in.

        Notes:
            Called once per attempt, so a retried attempt without an
            ``existing_session_id`` runs in a fresh session.
        """
        if existing_session_id:
            return await self._get_or_create_session(
                existing_session_id, user_id, session_state
            )
        return await self._create_session(user_id, session_state)

    async def _retry_after(
        self,
        error: Exception,
        attempt: int,
        backoff: float,
        session: Session | None,
    ) -> bool:
        """Log and sleep before a retry when the error warrants one.

        Args:
            error: The exception the attempt raised.
            attempt: The 1-based number of the attempt that failed.
            backoff: Seconds to sleep before the next attempt.
            session: The attempt's session, or None if creation failed.

        Returns:
            True when the error is transient and attempts remain, after
            logging ``execution.retry`` and sleeping; False otherwise.

        Notes:
            Sleeps through ``asyncio.sleep`` so tests can patch it.
        """
        max_attempts = self.retry_policy.max_attempts
        if attempt >= max_attempts or not is_transient_session_error(error):
            return False
        self._logger.warning(
            "execution.retry",
            attempt=attempt,
            max_attempts=max_attempts,
            backoff_seconds=backoff,
            error=str(error),
            session_id=session.id if session else None,
        )
        await asyncio.sleep(backoff)
        return True

    async def _run_with_retry(
        self,
        runner: Runner,
        user_id: str,
        input_text: str,
        input_content: types.Content | None,
        session_state: dict[str, Any] | None,
        existing_session_id: str | None,
        timeout_seconds: int,
    ) -> tuple[Session | None, list[Any], bool, str | None, int]:
        """Open a session and run the agent, retrying transient errors.

        Args:
            runner: ADK Runner for the (possibly overridden) agent.
            user_id: User identifier.
            input_text: User message to send.
            input_content: Pre-assembled multimodal Content, if any.
            session_state: Initial state to inject into each session.
            existing_session_id: Session ID for get-or-create semantics.
            timeout_seconds: Maximum execution time per attempt.

        Returns:
            Tuple of (session, events, timed_out, error_message, attempts).
            ``session`` is None only when every session creation failed.

        Raises:
            Exception: A non-transient error from session creation is
                re-raised unchanged.
            AssertionError: If the loop ends without an attempt, which
                ``RetryPolicy`` validation rules out.

        Notes:
            A transient error is retried under ``self.retry_policy`` with a
            growing backoff. A non-transient run error, a timeout, and a
            transient error on the last attempt end the loop and are
            reported through the returned tuple.
        """
        backoff = float(self.retry_policy.backoff_seconds)
        session: Session | None = None
        attempt = 0
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            session = None
            try:
                session = await self._open_session(
                    user_id, session_state, existing_session_id
                )
                events, timed_out = await self._execute_with_timeout(
                    runner, session, user_id, input_text, timeout_seconds, input_content
                )
                return session, events, timed_out, None, attempt
            except Exception as e:
                if await self._retry_after(e, attempt, backoff, session):
                    backoff *= self.retry_policy.backoff_multiplier
                    continue
                if session is None and not is_transient_session_error(e):
                    raise
                self._logger.error(
                    "execution.error",
                    session_id=session.id if session else None,
                    error=str(e),
                    attempts=attempt,
                )
                return session, [], False, str(e), attempt
        # RetryPolicy validation guarantees at least one attempt above
        raise AssertionError("_run_with_retry ended without an attempt")

    async def execute_agent(
        self,
        agent: Any,
        input_text: str,
        *,
        input_content: types.Content | None = None,
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
            input_text: User message to send to the agent. Used when
                input_content is None for backward compatibility.
            input_content: Pre-assembled multimodal Content for the agent.
                When provided, takes precedence over input_text. Use this
                for multimodal inputs containing video or other media.
            instruction_override: If provided, replaces the agent's instruction
                for this execution only. Original agent is not modified.
            output_schema_override: If provided, replaces the agent's output
                schema for this execution only (type[BaseModel]). Used for schema evolution.
            session_state: Initial state to inject into the session. Used for
                template variable substitution (e.g., {component_text}).
            existing_session_id: If provided, uses get-or-create semantics to
                retrieve or create a session with this ID. Enables session sharing
                between agents (e.g., critic accessing generator state).
            timeout_seconds: Maximum execution time in seconds. Defaults to 300.
                Execution terminates with TIMEOUT status if exceeded.

        Returns:
            ExecutionResult with status, output, and debugging information.

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

            With multimodal content:

            ```python
            from google.genai.types import Content, Part

            content = Content(
                role="user",
                parts=[Part(text="Describe this video"), video_part],
            )
            result = await executor.execute_agent(
                agent=analyzer,
                input_text="",  # Can be empty when content provided
                input_content=content,
            )
            ```

        Notes:
            Optional typing (Any) is used for agent parameter to avoid
            coupling to ADK types in the ports layer. Implementations
            should validate that the agent is a valid LlmAgent.

            A transient session-service error (``database is locked``) in
            session creation or the run is retried under
            ``self.retry_policy``, each attempt in a fresh session unless
            ``existing_session_id`` is given. The session of a failed
            attempt stays in the store. Timeouts and other errors are not
            retried. When every session creation fails on a lock, the
            result is FAILED with an empty ``session_id``.
        """
        start_time = time.perf_counter()
        user_id = "exec_user"
        is_multimodal = input_content is not None

        self._logger.info(
            "execution.start",
            agent_name=getattr(agent, "name", "unknown"),
            input_length=len(input_text),
            is_multimodal=is_multimodal,
            has_instruction_override=instruction_override is not None,
            has_schema_override=output_schema_override is not None,
            has_session_state=session_state is not None,
            existing_session_id=existing_session_id,
            timeout_seconds=timeout_seconds,
        )

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

        # Open a session and execute with timeout, retrying transient errors
        (
            session,
            events,
            timed_out,
            error_message,
            attempts,
        ) = await self._run_with_retry(
            runner,
            user_id,
            input_text,
            input_content,
            session_state,
            existing_session_id,
            timeout_seconds,
        )
        session_id = session.id if session else ""

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
        if session and (status == ExecutionStatus.SUCCESS or (timed_out and events)):
            extracted_value = await self._extract_output(session, events, agent)

        self._logger.info(
            "execution.complete",
            session_id=session_id,
            status=status.value,
            attempts=attempts,
            execution_time_seconds=execution_time,
            events_captured=len(events),
            has_output=extracted_value is not None,
        )

        return ExecutionResult(
            status=status,
            session_id=session_id,
            extracted_value=extracted_value,
            error_message=error_message,
            execution_time_seconds=execution_time,
            captured_events=events,
        )


__all__ = ["AgentExecutor", "SessionNotFoundError", "is_transient_session_error"]

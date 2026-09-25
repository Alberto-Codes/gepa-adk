"""Acceptance tests for retrying a transient session-service error.

``AgentExecutor.execute_agent`` retries the run when the session service
raises a transient ``database is locked`` error, under a ``RetryPolicy``
the caller can set on the executor. The row is then scored from the
successful attempt instead of counting as a failed evaluation. Any other
error, and a run that exhausts the policy, still returns
``ExecutionStatus.FAILED`` as before. The ``evolve()`` family documents
that ``SqliteSessionService`` has no busy timeout or WAL of its own.

Examples:
    Run these tests on their own:

    ```bash
    uv run pytest tests/unit/adapters/test_agent_executor_retry.py -q
    ```

See Also:
    - [`gepa_adk.adapters.execution.agent_executor`][gepa_adk.adapters.execution.agent_executor]:
      The executor that retries transient session errors.
    - [`gepa_adk.ports.agent_executor`][gepa_adk.ports.agent_executor]:
      The ``RetryPolicy`` value object.

Notes:
    The agent is a ``BaseAgent`` fake that yields one event, so the real
    ADK ``Runner`` and ``InMemorySessionService`` run without an LLM. The
    lock is injected by a session-service subclass.
"""

from __future__ import annotations

import dataclasses
import sqlite3
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.sessions import InMemorySessionService
from google.genai import types
from structlog.testing import capture_logs

from gepa_adk.adapters.execution.agent_executor import (
    AgentExecutor,
    is_transient_session_error,
)
from gepa_adk.ports.agent_executor import ExecutionStatus, RetryPolicy

pytestmark = pytest.mark.unit

_LOCKED = "database is locked"


class Echo(BaseAgent):
    """Agent that yields one text event and counts its runs.

    Attributes:
        runs (int): Number of times the agent body ran.
    """

    runs: int = 0

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Yield a single "hello" event.

        Args:
            ctx: The invocation context.

        Yields:
            One model event with the text "hello".
        """
        self.runs += 1
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(role="model", parts=[types.Part(text="hello")]),
        )


class LockingService(InMemorySessionService):
    """Session service whose appends raise a scripted error a few times.

    Attributes:
        failures (list[BaseException]): Errors raised by the next appends,
            consumed in order; an empty list means every append succeeds.
        appends (int): Number of ``append_event`` calls made so far.
    """

    def __init__(self, failures: list[BaseException]) -> None:
        """Store the scripted failures.

        Args:
            failures: Errors raised by the next appends, in order.
        """
        super().__init__()
        self.failures = list(failures)
        self.appends = 0

    async def append_event(self, session: Any, event: Any) -> Any:
        """Raise the next scripted error or append the event.

        Args:
            session: Session to append to.
            event: Event to append.

        Returns:
            The appended event.

        Raises:
            BaseException: The next scripted failure, when one remains.
        """
        self.appends += 1
        if self.failures:
            raise self.failures.pop(0)
        return await super().append_event(session, event)


class LockedCreateService(InMemorySessionService):
    """Session service whose first ``create_session`` is locked.

    Attributes:
        creates (int): Number of ``create_session`` calls made so far.
    """

    def __init__(self) -> None:
        """Start the counter at zero."""
        super().__init__()
        self.creates = 0

    async def create_session(self, **kwargs: Any) -> Any:
        """Raise a lock on the first call, then create the session.

        Args:
            **kwargs: Passed through to the in-memory service.

        Returns:
            The created session.

        Raises:
            sqlite3.OperationalError: On the first call only.
        """
        self.creates += 1
        if self.creates == 1:
            raise sqlite3.OperationalError(_LOCKED)
        return await super().create_session(**kwargs)


def _locked(times: int) -> list[BaseException]:
    return [sqlite3.OperationalError(_LOCKED) for _ in range(times)]


def _fast(max_attempts: int = 3) -> RetryPolicy:
    return RetryPolicy(max_attempts=max_attempts, backoff_seconds=0.0)


async def _execute(service: Any, policy: RetryPolicy | None) -> tuple[Any, Echo, list]:
    agent = Echo(name="echo")
    executor = AgentExecutor(session_service=service, retry_policy=policy)
    with capture_logs() as logs:
        result = await executor.execute_agent(
            agent=agent, input_text="hi", timeout_seconds=5
        )
    return result, agent, logs


def _events(logs: list, name: str) -> list[dict[str, Any]]:
    return [e for e in logs if e["event"] == name]


class TestTransientLockIsRetried:
    """A locked session write is retried and the row is scored."""

    @pytest.mark.asyncio
    async def test_one_lock_is_retried_and_the_run_succeeds(self) -> None:
        """The second attempt succeeds and the output is extracted."""
        service = LockingService(_locked(1))

        result, agent, logs = await _execute(service, _fast())

        assert result.status == ExecutionStatus.SUCCESS
        assert result.extracted_value == "hello"
        assert result.error_message is None
        assert agent.runs == 1
        assert service.appends == 3
        retries = _events(logs, "execution.retry")
        assert len(retries) == 1
        assert retries[0]["attempt"] == 1
        assert retries[0]["max_attempts"] == 3
        assert _LOCKED in retries[0]["error"]
        assert _events(logs, "execution.error") == []

    @pytest.mark.asyncio
    async def test_persistent_lock_fails_after_max_attempts(self) -> None:
        """Every attempt is locked, so the run fails after three tries."""
        service = LockingService(_locked(10))

        result, agent, logs = await _execute(service, _fast(3))

        assert result.status == ExecutionStatus.FAILED
        assert result.error_message is not None
        assert _LOCKED in result.error_message
        assert result.extracted_value is None
        assert agent.runs == 0
        assert service.appends == 3
        assert len(_events(logs, "execution.retry")) == 2
        errors = _events(logs, "execution.error")
        assert len(errors) == 1
        assert errors[0]["attempts"] == 3

    @pytest.mark.asyncio
    async def test_non_transient_error_is_not_retried(self) -> None:
        """Any other error fails the run on the first attempt as before."""
        service = LockingService([RuntimeError("boom")])

        result, agent, logs = await _execute(service, _fast())

        assert result.status == ExecutionStatus.FAILED
        assert result.error_message == "boom"
        assert service.appends == 1
        assert _events(logs, "execution.retry") == []
        assert len(_events(logs, "execution.error")) == 1

    @pytest.mark.asyncio
    async def test_single_attempt_policy_disables_the_retry(self) -> None:
        """max_attempts=1 keeps the pre-2.5.1 behaviour."""
        service = LockingService(_locked(1))

        result, _, logs = await _execute(service, _fast(1))

        assert result.status == ExecutionStatus.FAILED
        assert service.appends == 1
        assert _events(logs, "execution.retry") == []

    @pytest.mark.asyncio
    async def test_backoff_grows_by_the_multiplier(self) -> None:
        """Two locks sleep 0.5 s then 1.0 s before the third attempt succeeds."""
        service = LockingService(_locked(2))
        policy = RetryPolicy(
            max_attempts=3, backoff_seconds=0.5, backoff_multiplier=2.0
        )

        with patch(
            "gepa_adk.adapters.execution.agent_executor.asyncio.sleep",
            new=AsyncMock(),
        ) as sleep:
            result, _, _ = await _execute(service, policy)

        assert result.status == ExecutionStatus.SUCCESS
        assert [c.args[0] for c in sleep.await_args_list] == [0.5, 1.0]

    @pytest.mark.asyncio
    async def test_locked_session_creation_is_retried(self) -> None:
        """A lock while creating the session is retried like a locked write."""
        service = LockedCreateService()

        result, agent, logs = await _execute(service, _fast())

        assert result.status == ExecutionStatus.SUCCESS
        assert result.extracted_value == "hello"
        assert service.creates == 2
        assert agent.runs == 1
        assert len(_events(logs, "execution.retry")) == 1

    @pytest.mark.asyncio
    async def test_default_policy_retries_a_lock(self) -> None:
        """With no policy given, the executor's default still retries."""
        service = LockingService(_locked(1))

        with patch(
            "gepa_adk.adapters.execution.agent_executor.asyncio.sleep",
            new=AsyncMock(),
        ) as sleep:
            result, _, _ = await _execute(service, None)

        assert result.status == ExecutionStatus.SUCCESS
        assert sleep.await_count == 1
        assert sleep.await_args_list[0].args[0] == RetryPolicy().backoff_seconds


class TestRetryPolicy:
    """RetryPolicy is a validated, frozen value object."""

    def test_defaults(self) -> None:
        """Three attempts, half a second, doubling."""
        policy = RetryPolicy()

        assert policy.max_attempts == 3
        assert policy.backoff_seconds == 0.5
        assert policy.backoff_multiplier == 2.0

    def test_executor_exposes_its_policy(self) -> None:
        """The executor stores the given policy and defaults to RetryPolicy()."""
        custom = RetryPolicy(max_attempts=5, backoff_seconds=0.1)

        assert AgentExecutor().retry_policy == RetryPolicy()
        assert AgentExecutor(retry_policy=custom).retry_policy is custom

    @pytest.mark.parametrize("bad", [0, -1, True, "3", 2.5])
    def test_rejects_bad_max_attempts(self, bad: Any) -> None:
        """max_attempts must be an int of at least 1."""
        with pytest.raises(ValueError, match="max_attempts"):
            RetryPolicy(max_attempts=bad)

    @pytest.mark.parametrize("bad", [-0.1, -1, True, "1"])
    def test_rejects_bad_backoff(self, bad: Any) -> None:
        """backoff_seconds must be a non-negative number."""
        with pytest.raises(ValueError, match="backoff_seconds"):
            RetryPolicy(backoff_seconds=bad)

    @pytest.mark.parametrize("bad", [0.5, 0, -1, True, "2"])
    def test_rejects_bad_multiplier(self, bad: Any) -> None:
        """backoff_multiplier must be a number of at least 1."""
        with pytest.raises(ValueError, match="backoff_multiplier"):
            RetryPolicy(backoff_multiplier=bad)

    def test_is_frozen(self) -> None:
        """A policy cannot be mutated after construction."""
        policy = RetryPolicy()

        with pytest.raises(dataclasses.FrozenInstanceError):
            policy.max_attempts = 9  # type: ignore[misc]


class TestTransientClassification:
    """Only a "database is locked" anywhere in the cause chain is transient."""

    def test_locked_operational_error(self) -> None:
        """The sqlite lock error itself is transient."""
        assert is_transient_session_error(sqlite3.OperationalError(_LOCKED)) is True

    def test_locked_error_wrapped_as_cause(self) -> None:
        """A wrapper whose __cause__ is the lock is transient too."""
        wrapper = RuntimeError("session write failed")
        wrapper.__cause__ = sqlite3.OperationalError(_LOCKED)

        assert is_transient_session_error(wrapper) is True

    def test_sqlalchemy_style_message(self) -> None:
        """A driver wrapper that embeds the sqlite message is transient."""
        error = RuntimeError(f"(sqlite3.OperationalError) {_LOCKED}\n[SQL: INSERT]")

        assert is_transient_session_error(error) is True

    @pytest.mark.parametrize(
        "exc",
        [
            sqlite3.OperationalError("no such table: sessions"),
            RuntimeError("boom"),
            ValueError(_LOCKED.upper().replace(" ", "_")),
            TimeoutError(),
        ],
        ids=lambda e: f"{type(e).__name__}:{e}"[:40],
    )
    def test_other_errors_are_not_transient(self, exc: BaseException) -> None:
        """Schema, programming and timeout errors are not retried."""
        assert is_transient_session_error(exc) is False


class TestDocstrings:
    """The evolve() family warns about SqliteSessionService."""

    @pytest.mark.parametrize("name", ["evolve", "evolve_group", "evolve_workflow"])
    def test_session_service_docs_name_the_sqlite_limits(self, name: str) -> None:
        """Each docstring says the service has no busy timeout or WAL of its own."""
        import gepa_adk.api as api

        doc = getattr(api, name).__doc__ or ""

        assert "busy timeout" in doc
        assert "WAL" in doc
        assert "RetryPolicy" in doc

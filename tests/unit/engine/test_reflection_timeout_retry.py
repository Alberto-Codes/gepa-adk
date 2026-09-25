"""Unit tests for how a reflection timeout travels through the proposer.

A ``ReflectionTimeoutError`` raised by the reflection function propagates
out of ``AsyncReflectiveMutationProposer.propose`` after exactly one call:
the proposer's empty-response retry does not apply to a timeout. The ADK
reflection function logs ``reflection.timeout`` for a timed-out run and
``reflection.empty_response`` only for a completed run with no text.

Examples:
    Run these tests on their own:

    ```bash
    uv run pytest tests/unit/engine/test_reflection_timeout_retry.py -q
    ```

See Also:
    - [`gepa_adk.engine.proposer`][gepa_adk.engine.proposer]: The proposer
      whose retry is exercised here.
    - [`gepa_adk.engine.adk_reflection`][gepa_adk.engine.adk_reflection]: The
      reflection function whose log lines are checked here.
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
from structlog.testing import capture_logs

from gepa_adk.domain.exceptions import ReflectionTimeoutError
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

pytestmark = pytest.mark.unit

_TRIALS = {"instruction": [{"input": "q", "output": "a", "feedback": {"score": 0.0}}]}


class _TimingOutReflection:
    """Reflection function that always raises ReflectionTimeoutError.

    Attributes:
        calls (int): Number of reflection calls made so far.
    """

    def __init__(self) -> None:
        """Start the call counter at zero."""
        self.calls = 0

    async def __call__(
        self, component_text: str, trials: list[dict[str, Any]], component: str
    ) -> tuple[str, str | None]:
        """Count the call and raise a timeout.

        Args:
            component_text: Current text (unused).
            trials: Trial records (unused).
            component: Component name carried by the error.

        Raises:
            ReflectionTimeoutError: On every call.
        """
        self.calls += 1
        raise ReflectionTimeoutError(component, timeout_seconds=12)


class _ScriptedExecutor:
    """Executor stub that returns one scripted result.

    Attributes:
        result (ExecutionResult): Result returned by every call.
    """

    def __init__(self, result: ExecutionResult) -> None:
        """Store the scripted result.

        Args:
            result: Result returned by every call.
        """
        self.result = result

    async def execute_agent(self, **kwargs: Any) -> ExecutionResult:
        """Return the scripted result.

        Args:
            **kwargs: The executor call's keyword arguments (ignored).

        Returns:
            The scripted result.
        """
        return self.result


def _reflector() -> LlmAgent:
    """Build a reflection agent with the template placeholders.

    Returns:
        An LlmAgent whose instruction names both placeholders.
    """
    return LlmAgent(
        name="reflector",
        model="gemini-3.8-flash",
        instruction="{component_text}\n{trials}",
    )


class TestProposerDoesNotRetryATimeout:
    """A timed-out reflection is not retried by the proposer."""

    @pytest.mark.asyncio
    async def test_timeout_propagates_after_one_call(self) -> None:
        """The first ReflectionTimeoutError propagates with no second attempt."""
        fn = _TimingOutReflection()
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=fn)

        with (
            capture_logs() as logs,
            pytest.raises(ReflectionTimeoutError) as exc_info,
        ):
            await proposer.propose(
                candidate={"instruction": "seed"},
                reflective_dataset=_TRIALS,
                components_to_update=["instruction"],
            )

        assert fn.calls == 1
        assert exc_info.value.component == "instruction"
        assert exc_info.value.timeout_seconds == 12
        assert [e for e in logs if e["event"] == "proposer.empty_retry"] == []


class TestTimeoutAndEmptyLogDifferently:
    """The timeout and the empty response produce different log lines."""

    @pytest.mark.asyncio
    async def test_timeout_logs_reflection_timeout_only(self) -> None:
        """A TIMEOUT status logs reflection.timeout and not empty_response."""
        executor = _ScriptedExecutor(
            ExecutionResult(
                status=ExecutionStatus.TIMEOUT, session_id="s", extracted_value=""
            )
        )
        reflect = create_adk_reflection_fn(_reflector(), executor=executor)

        with capture_logs() as logs, pytest.raises(ReflectionTimeoutError):
            await reflect("old", [], component_name="instruction")

        events = [e["event"] for e in logs]
        assert "reflection.empty_response" not in events
        timeouts = [e for e in logs if e["event"] == "reflection.timeout"]
        assert len(timeouts) == 1
        assert timeouts[0]["component"] == "instruction"
        assert timeouts[0]["timeout_seconds"] is None
        assert timeouts[0]["timeout_source"] == "executor_default"
        starts = [e for e in logs if e["event"] == "reflection.start"]
        assert starts[0]["timeout_source"] == "executor_default"

    @pytest.mark.asyncio
    async def test_empty_success_logs_empty_response_only(self) -> None:
        """A SUCCESS with no text logs empty_response and returns empty text."""
        executor = _ScriptedExecutor(
            ExecutionResult(
                status=ExecutionStatus.SUCCESS, session_id="s", extracted_value=""
            )
        )
        reflect = create_adk_reflection_fn(
            _reflector(), executor=executor, timeout_seconds=30
        )

        with capture_logs() as logs:
            proposed, _, _ = await reflect("old", [], component_name="instruction")

        assert proposed == ""
        events = [e["event"] for e in logs]
        assert "reflection.timeout" not in events
        assert events.count("reflection.empty_response") == 1
        starts = [e for e in logs if e["event"] == "reflection.start"]
        assert starts[0]["timeout_seconds"] == 30
        assert starts[0]["timeout_source"] == "config"

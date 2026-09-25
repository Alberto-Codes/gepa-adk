"""Acceptance tests for surviving a provider error from the reflection agent.

A reflection call that raises a retryable provider error (HTTP 429, 503,
a connection reset) is retried once after a short backoff. When the retry
fails too, the proposer raises ``ReflectionError`` with ``retryable=True``
and the engine records that iteration with ``skip_reason="reflection_error"``,
counts it toward stagnation, calls ``on_iteration``, re-checks the stop
conditions and continues with its accepted candidates and history intact.
A non-retryable error is not retried and still aborts the run; when the
abort happens after the baseline was scored, the raised ``EvolutionError``
carries the partial ``EvolutionResult`` in ``partial_result``; a reused
engine never attaches an earlier run's state.

Examples:
    Run these tests on their own:

    ```bash
    uv run pytest tests/unit/engine/test_reflection_error.py -q
    ```

See Also:
    - [`gepa_adk.engine.proposer`][gepa_adk.engine.proposer]: The proposer
      that classifies and retries reflection errors.
    - [`gepa_adk.engine.async_engine`][gepa_adk.engine.async_engine]: The
      engine that records a failed reflection as a skipped iteration.

Notes:
    The adapters and reflection functions are fakes, so no agent or LLM
    runs. The backoff is set to zero or patched so the tests stay fast.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from structlog.testing import capture_logs

from gepa_adk.domain.exceptions import EvolutionError, ReflectionError
from gepa_adk.domain.models import Candidate, EvolutionConfig, EvolutionResult
from gepa_adk.domain.types import StopReason
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.engine.proposer import (
    AsyncReflectiveMutationProposer,
    is_retryable_reflection_error,
)
from gepa_adk.ports.adapter import EvaluationBatch

pytestmark = pytest.mark.unit

_TRIALS = {"instruction": [{"input": "q", "output": "a", "feedback": {"score": 0.0}}]}

_RATE_LIMITED = (
    "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': "
    "'Resource has been exhausted (e.g. check quota).', 'status': "
    "'RESOURCE_EXHAUSTED'}}"
)
_UNAVAILABLE = "503 UNAVAILABLE. The service is currently unavailable."


class FailingAdapter:
    """Fake adapter whose proposals are scripted to fail or succeed.

    Attributes:
        script (list[str]): Per-iteration script: ``"retryable"`` raises a
            retryable ``ReflectionError``, ``"fatal"`` raises a
            non-retryable one; any other text is the proposal.
        calls (list[int]): Row counts of each ``evaluate()`` call.
    """

    def __init__(self, script: list[str]) -> None:
        """Store the script.

        Args:
            script: Per-iteration entries, consumed in order.
        """
        self.script = list(script)
        self.calls: list[int] = []

    async def evaluate(
        self,
        batch: list[dict[str, str]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Any, Any]:
        """Score 1.0 for the instruction "better" and 0.5 otherwise.

        Args:
            batch: Rows to evaluate.
            candidate: Candidate components.
            capture_traces: Whether traces were requested.

        Returns:
            A batch with one score per row.
        """
        self.calls.append(len(batch))
        score = 1.0 if candidate["instruction"] == "better" else 0.5
        return EvaluationBatch(
            outputs=[""] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[Any, Any],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Return an empty reflective dataset.

        Args:
            candidate: Ignored.
            eval_batch: Ignored.
            components_to_update: Ignored.

        Returns:
            An empty mapping.
        """
        return {}

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Raise the scripted error or return the scripted proposal.

        Args:
            candidate: Ignored.
            reflective_dataset: Ignored.
            components_to_update: Ignored.

        Returns:
            The next scripted proposal.

        Raises:
            ReflectionError: When the script entry is ``"retryable"`` or
                ``"fatal"``.
        """
        entry = self.script.pop(0)
        if entry == "retryable":
            raise ReflectionError(
                "instruction",
                cause=RuntimeError(_RATE_LIMITED),
                retryable=True,
                attempts=2,
            )
        if entry == "fatal":
            raise ReflectionError(
                "instruction",
                cause=ValueError("instruction template is missing {trials}"),
                retryable=False,
                attempts=1,
            )
        return {"instruction": entry}


class BaselineFailingAdapter(FailingAdapter):
    """Adapter whose very first evaluation raises an EvolutionError."""

    async def evaluate(
        self,
        batch: list[dict[str, str]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Any, Any]:
        """Raise before any score exists.

        Args:
            batch: Ignored.
            candidate: Ignored.
            capture_traces: Ignored.

        Raises:
            EvolutionError: Always.
        """
        raise EvolutionError("baseline evaluation failed")


def _engine(
    adapter: FailingAdapter, iterations: int, *, patience: int = 5, **config: Any
) -> AsyncGEPAEngine:
    return AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=iterations,
            patience=patience,
            min_improvement_threshold=0.0,
            **config,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=[{"input": "q1"}, {"input": "qü"}],
    )


async def _run(script: list[str], *, patience: int = 5) -> tuple[FailingAdapter, Any]:
    adapter = FailingAdapter(script)
    return adapter, await _engine(adapter, len(script), patience=patience).run()


class TestEngineRecordsReflectionError:
    """A retryable reflection error is a skipped iteration, not a dead run."""

    @pytest.mark.asyncio
    async def test_retryable_error_is_recorded_and_the_run_continues(self) -> None:
        """The failed iteration is skipped and the next proposal is still evaluated."""
        adapter, result = await _run(["retryable", "better"])

        first, second = result.iteration_history
        assert first.accepted is False
        assert first.skip_reason == "reflection_error"
        assert first.score == 0.0
        assert first.evolved_component == "instruction"
        assert second.accepted is True
        assert second.skip_reason is None
        assert result.total_iterations == 2
        assert adapter.calls == [2, 2]
        assert result.evolved_components["instruction"] == "better"

    @pytest.mark.asyncio
    async def test_errors_count_toward_patience(self) -> None:
        """Consecutive errors exhaust patience and end the run with the seed."""
        adapter, result = await _run(
            ["retryable", "retryable", "retryable"], patience=2
        )

        assert result.total_iterations == 2
        assert [r.skip_reason for r in result.iteration_history] == [
            "reflection_error",
            "reflection_error",
        ]
        assert adapter.calls == [2]
        assert result.evolved_components["instruction"] == "seed"

    @pytest.mark.asyncio
    async def test_skipped_record_reaches_on_iteration(self) -> None:
        """on_iteration sees the skipped record with no candidate id."""
        seen: list[tuple[str | None, str | None]] = []

        def on_iteration(record: Any, candidate_id: str | None) -> None:
            """Record the skip reason and candidate id of each iteration.

            Args:
                record: The appended iteration record.
                candidate_id: Id of the evaluated candidate, or None.
            """
            seen.append((record.skip_reason, candidate_id))

        adapter = FailingAdapter(["retryable", "better"])
        result = await _engine(adapter, 2, on_iteration=on_iteration).run()

        assert len(seen) == 2
        assert seen[0] == ("reflection_error", None)
        assert seen[1][0] is None
        assert isinstance(seen[1][1], str)
        assert result.total_iterations == 2

    @pytest.mark.asyncio
    async def test_skip_is_logged_with_the_cause(self) -> None:
        """The skip log names the reason, the component and the cause."""
        with capture_logs() as logs:
            await _run(["retryable", "better"])

        skips = [
            e
            for e in logs
            if e["event"] == "evolution.proposal_skipped"
            and e.get("reason") == "reflection_error"
        ]
        assert len(skips) == 1
        assert skips[0]["component"] == "instruction"
        assert skips[0]["error_type"] == "RuntimeError"
        assert "429" in skips[0]["error"]
        assert skips[0]["attempts"] == 2


class TestNonRetryableErrorAborts:
    """A non-retryable error aborts and exposes the partial result."""

    @pytest.mark.asyncio
    async def test_abort_after_iterations_carries_the_partial_result(self) -> None:
        """The raised error holds the scored iterations and the best candidate."""
        adapter = FailingAdapter(["better", "fatal"])

        with pytest.raises(ReflectionError) as excinfo:
            await _engine(adapter, 2).run()

        error = excinfo.value
        assert error.retryable is False
        assert isinstance(error.cause, ValueError)
        partial = error.partial_result
        assert isinstance(partial, EvolutionResult)
        assert partial.stop_reason == StopReason.ERROR
        assert partial.total_iterations == 1
        assert len(partial.iteration_history) == 1
        assert partial.iteration_history[0].accepted is True
        assert partial.evolved_components["instruction"] == "better"
        assert partial.final_score == 2.0
        assert adapter.calls == [2, 2]

    @pytest.mark.asyncio
    async def test_abort_before_the_baseline_has_no_partial_result(self) -> None:
        """An error before any score leaves partial_result as None."""
        adapter = BaselineFailingAdapter(["better"])

        with pytest.raises(EvolutionError, match="baseline") as excinfo:
            await _engine(adapter, 1).run()

        assert excinfo.value.partial_result is None

    @pytest.mark.asyncio
    async def test_reused_engine_does_not_attach_an_earlier_runs_state(self) -> None:
        """A second run whose baseline fails carries no stale partial result."""
        adapter = FailingAdapter(["better"])
        engine = _engine(adapter, 1)
        first = await engine.run()
        assert first.total_iterations == 1

        engine.adapter = BaselineFailingAdapter([])
        with pytest.raises(EvolutionError, match="baseline") as excinfo:
            await engine.run()

        assert excinfo.value.partial_result is None


class _ErrorScript:
    """Reflection function that raises or returns scripted entries.

    Attributes:
        script (list[BaseException | str]): Entries consumed in order; an
            exception is raised, a string is returned as the proposal.
        calls (int): Number of reflection calls made so far.
    """

    def __init__(self, script: list[BaseException | str]) -> None:
        """Store the script.

        Args:
            script: Entries consumed in order.
        """
        self.script = list(script)
        self.calls = 0

    async def __call__(
        self, component_text: str, trials: list[dict[str, Any]], component: str
    ) -> tuple[str, str | None]:
        """Raise or return the next scripted entry.

        Args:
            component_text: Current text (unused).
            trials: Trial records (unused).
            component: Component name (unused).

        Returns:
            The scripted text and ``None`` reasoning.

        Raises:
            BaseException: The scripted exception, when the entry is one.
        """
        self.calls += 1
        entry = self.script.pop(0)
        if isinstance(entry, BaseException):
            raise entry
        return entry, None


async def _propose(fn: _ErrorScript, **kwargs: Any) -> dict[str, str] | None:
    proposer = AsyncReflectiveMutationProposer(
        adk_reflection_fn=fn, retry_backoff_seconds=kwargs.pop("backoff", 0.0)
    )
    return await proposer.propose(
        candidate={"instruction": "seed"},
        reflective_dataset=_TRIALS,
        components_to_update=["instruction"],
    )


class TestProposerRetriesProviderErrors:
    """The proposer retries a retryable error once and wraps the rest."""

    @pytest.mark.asyncio
    async def test_retryable_error_then_text_uses_the_retry(self) -> None:
        """One 429 is retried and the second answer is used."""
        fn = _ErrorScript([RuntimeError(_RATE_LIMITED), "Better"])

        with capture_logs() as logs:
            result = await _propose(fn)

        assert result == {"instruction": "Better"}
        assert fn.calls == 2
        retries = [e for e in logs if e["event"] == "proposer.error_retry"]
        assert len(retries) == 1
        assert retries[0]["component"] == "instruction"
        assert retries[0]["error_type"] == "RuntimeError"

    @pytest.mark.asyncio
    async def test_retryable_error_twice_raises_reflection_error(self) -> None:
        """Two provider errors raise ReflectionError after exactly two calls."""
        second = RuntimeError(_UNAVAILABLE)
        fn = _ErrorScript([RuntimeError(_RATE_LIMITED), second])

        with pytest.raises(ReflectionError) as excinfo:
            await _propose(fn)

        error = excinfo.value
        assert fn.calls == 2
        assert isinstance(error, EvolutionError)
        assert error.component == "instruction"
        assert error.retryable is True
        assert error.attempts == 2
        assert error.cause is second
        assert error.__cause__ is second
        assert "RuntimeError" in str(error)
        assert "503" in str(error)

    @pytest.mark.asyncio
    async def test_non_retryable_error_is_not_retried(self) -> None:
        """A programming error is wrapped after one call with retryable=False."""
        fn = _ErrorScript([ValueError("template missing {trials}")])

        with pytest.raises(ReflectionError) as excinfo:
            await _propose(fn)

        assert fn.calls == 1
        assert excinfo.value.retryable is False
        assert excinfo.value.attempts == 1
        assert "ValueError" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_backoff_is_awaited_before_the_retry(self) -> None:
        """The configured backoff is slept once, between the two attempts."""
        fn = _ErrorScript([RuntimeError(_RATE_LIMITED), "Better"])

        with patch("gepa_adk.engine.proposer.asyncio.sleep", new=AsyncMock()) as sleep:
            await _propose(fn, backoff=0.25)

        sleep.assert_awaited_once_with(0.25)

    def test_default_backoff_is_short_and_positive(self) -> None:
        """The default backoff is a short positive number of seconds."""
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=_ErrorScript([]))

        assert 0 < proposer.retry_backoff_seconds <= 10


class _Coded(Exception):
    """Exception carrying a provider status code.

    Attributes:
        code (int): HTTP-style status code.
    """

    def __init__(self, code: int) -> None:
        """Store the code.

        Args:
            code: HTTP-style status code.
        """
        super().__init__(f"provider error {code}")
        self.code = code


class TestRetryableClassification:
    """Retryable means a quota, availability or connection failure."""

    @pytest.mark.parametrize(
        "exc",
        [
            RuntimeError(_RATE_LIMITED),
            RuntimeError(_UNAVAILABLE),
            RuntimeError("502 Bad Gateway"),
            RuntimeError("504 DEADLINE_EXCEEDED. Deadline expired"),
            RuntimeError("500 INTERNAL. An internal error has occurred."),
            ConnectionResetError(104, "Connection reset by peer"),
            ConnectionError("Server disconnected"),
            RuntimeError("Connection reset by peer"),
            RuntimeError("Rate-limited by the provider, retry later"),
            RuntimeError("rate limited"),
            RuntimeError("RateLimitError: too many requests"),
            RuntimeError("Too Many Requests"),
            TimeoutError("read timed out"),
            _Coded(429),
            _Coded(503),
        ],
        ids=lambda e: f"{type(e).__name__}:{e}"[:48],
    )
    def test_retryable(self, exc: BaseException) -> None:
        """Quota, availability and connection failures are retryable."""
        assert is_retryable_reflection_error(exc) is True

    @pytest.mark.parametrize(
        "exc",
        [
            ValueError("instruction template missing placeholder"),
            RuntimeError("400 INVALID_ARGUMENT. Bad request"),
            RuntimeError("401 UNAUTHENTICATED. Missing credentials"),
            RuntimeError("404 NOT_FOUND. Model not found"),
            RuntimeError("Executor returned FAILED"),
            _Coded(400),
            KeyError("trials"),
        ],
        ids=lambda e: f"{type(e).__name__}:{e}"[:48],
    )
    def test_not_retryable(self, exc: BaseException) -> None:
        """Client, auth and programming errors are not retryable."""
        assert is_retryable_reflection_error(exc) is False


_LITELLM_CONNECTION_ERROR = (
    "litellm.InternalServerError: InternalServerError: OpenAIException - "
    "Connection error."
)
_OPENAI_BAD_REQUEST = (
    "litellm.BadRequestError: BadRequestError: OpenAIException - "
    "Error code: 400 - {'error': {'message': 'Invalid model', "
    "'type': 'invalid_request_error'}}"
)
_OPENAI_UNAUTHENTICATED = (
    "litellm.AuthenticationError: AuthenticationError: OpenAIException - "
    "Error code: 401 - Incorrect API key provided"
)


class InternalServerError(Exception):
    """Stand-in for the LiteLLM and OpenAI SDK exception of that name."""


class APIConnectionError(Exception):
    """Stand-in for the OpenAI SDK exception of that name."""


class TestConnectionErrorsAreRetryable:
    """A dropped provider connection is retryable however it is spelled.

    GitHub issue 450: LiteLLM raises ``InternalServerError`` with the text
    ``OpenAIException - Connection error.`` when the local server goes
    away; ADK wraps it and the executor surfaces a ``RuntimeError`` whose
    message is that text, with no ``status_code`` attribute.
    """

    @pytest.mark.parametrize(
        "exc",
        [
            RuntimeError(_LITELLM_CONNECTION_ERROR),
            RuntimeError("Connection error."),
            RuntimeError("connection refused"),
            RuntimeError("Cannot connect to host localhost:11434 ssl:default"),
            RuntimeError("APIConnectionError: socket closed"),
            InternalServerError("upstream failed"),
            APIConnectionError("socket closed"),
        ],
        ids=lambda e: f"{type(e).__name__}:{e}"[:48],
    )
    def test_retryable(self, exc: BaseException) -> None:
        """Connection-error text and the SDK type names are retryable."""
        assert is_retryable_reflection_error(exc) is True

    @pytest.mark.parametrize(
        "exc",
        [
            RuntimeError(_OPENAI_BAD_REQUEST),
            RuntimeError(_OPENAI_UNAUTHENTICATED),
            RuntimeError("Executor returned FAILED"),
            ValueError("connection string is malformed"),
        ],
        ids=lambda e: f"{type(e).__name__}:{e}"[:48],
    )
    def test_not_retryable(self, exc: BaseException) -> None:
        """A 4xx OpenAI error and unrelated text stay fatal."""
        assert is_retryable_reflection_error(exc) is False

    @pytest.mark.asyncio
    async def test_proposer_retries_the_litellm_connection_error(self) -> None:
        """The full path: the proposer retries the wrapped text and uses the retry."""
        fn = _ErrorScript([RuntimeError(_LITELLM_CONNECTION_ERROR), "Better"])
        with capture_logs() as logs:
            result = await _propose(fn)
        assert result == {"instruction": "Better"}
        assert fn.calls == 2
        retries = [e for e in logs if e["event"] == "proposer.error_retry"]
        assert len(retries) == 1

    @pytest.mark.asyncio
    async def test_proposer_does_not_retry_the_openai_bad_request(self) -> None:
        """A 400 from the provider is wrapped after one call with retryable=False."""
        fn = _ErrorScript([RuntimeError(_OPENAI_BAD_REQUEST)])
        with pytest.raises(ReflectionError) as excinfo:
            await _propose(fn)
        assert fn.calls == 1
        assert excinfo.value.retryable is False

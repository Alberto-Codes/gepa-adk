"""Acceptance tests for the configurable reflection timeout.

``EvolutionConfig.reflection_timeout_seconds`` reaches the executor call
that runs the reflection agent. A reflection that times out raises
``ReflectionTimeoutError`` instead of returning an empty proposal, and the
engine records that iteration with ``skip_reason="reflection_timeout"``,
counts it toward stagnation, re-checks the stop conditions and continues
with its accepted candidates intact. Both ``evolve()`` and ``evolve_group()``
hand the configured timeout to the reflection function.

Examples:
    Run these tests on their own:

    ```bash
    uv run pytest tests/unit/engine/test_reflection_timeout.py -q
    ```

See Also:
    - [`gepa_adk.engine.adk_reflection`][gepa_adk.engine.adk_reflection]: The
      reflection function that forwards the timeout and raises on expiry.
    - [`gepa_adk.engine.async_engine`][gepa_adk.engine.async_engine]: The
      engine that records a timed-out reflection as a skipped iteration.

Notes:
    The executor and the adapter are fakes, so no agent or LLM runs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.domain.exceptions import ConfigurationError, EvolutionError
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.ports.adapter import EvaluationBatch
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

pytestmark = pytest.mark.unit


class RecordingExecutor:
    """Executor stub that records its kwargs and returns a scripted result.

    Attributes:
        result (ExecutionResult): Result returned by every call.
        kwargs (list[dict[str, Any]]): Keyword arguments of each call.
    """

    def __init__(self, result: ExecutionResult) -> None:
        """Store the scripted result.

        Args:
            result: Result returned by every call.
        """
        self.result = result
        self.kwargs: list[dict[str, Any]] = []

    async def execute_agent(self, **kwargs: Any) -> ExecutionResult:
        """Record the call and return the scripted result.

        Args:
            **kwargs: The executor call's keyword arguments.

        Returns:
            The scripted result.
        """
        self.kwargs.append(dict(kwargs))
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


class TestTimeoutReachesTheExecutor:
    """The configured timeout is passed to the executor call."""

    @pytest.mark.asyncio
    async def test_timeout_seconds_is_forwarded(self) -> None:
        """A configured timeout is passed as timeout_seconds."""
        executor = RecordingExecutor(
            ExecutionResult(
                status=ExecutionStatus.SUCCESS, session_id="s", extracted_value="new"
            )
        )
        reflect = create_adk_reflection_fn(
            _reflector(), executor=executor, timeout_seconds=45
        )

        proposed, _ = await reflect("old", [], component_name="instruction")

        assert proposed == "new"
        assert len(executor.kwargs) == 1
        assert executor.kwargs[0]["timeout_seconds"] == 45

    @pytest.mark.asyncio
    async def test_no_timeout_leaves_the_executor_default(self) -> None:
        """Without a configured timeout the executor's own default applies."""
        executor = RecordingExecutor(
            ExecutionResult(
                status=ExecutionStatus.SUCCESS, session_id="s", extracted_value="new"
            )
        )
        reflect = create_adk_reflection_fn(_reflector(), executor=executor)

        await reflect("old", [], component_name="instruction")

        assert "timeout_seconds" not in executor.kwargs[0]

    @pytest.mark.asyncio
    async def test_timed_out_execution_raises_a_distinct_error(self) -> None:
        """A TIMEOUT status raises ReflectionTimeoutError, not an empty proposal."""
        from gepa_adk.domain.exceptions import ReflectionTimeoutError

        executor = RecordingExecutor(
            ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                session_id="s",
                extracted_value="",
                error_message="Execution timed out after 7 seconds",
            )
        )
        reflect = create_adk_reflection_fn(
            _reflector(), executor=executor, timeout_seconds=7
        )

        with pytest.raises(ReflectionTimeoutError) as excinfo:
            await reflect("old", [], component_name="instruction")

        assert isinstance(excinfo.value, EvolutionError)
        assert excinfo.value.component == "instruction"
        assert excinfo.value.timeout_seconds == 7
        assert "7" in str(excinfo.value)


class TestConfigValidation:
    """reflection_timeout_seconds must be None or a positive int."""

    @pytest.mark.parametrize("bad", [0, -1, 2.5, True, "30"])
    def test_rejects_non_positive_or_non_int(self, bad: Any) -> None:
        """Zero, negatives, floats, bools and strings are configuration errors."""
        with pytest.raises(ConfigurationError, match="reflection_timeout_seconds"):
            EvolutionConfig(reflection_timeout_seconds=bad)

    def test_default_is_none(self) -> None:
        """No timeout override by default."""
        assert EvolutionConfig().reflection_timeout_seconds is None


class TestApiWiring:
    """evolve() hands the configured timeout to the reflection function."""

    @pytest.mark.asyncio
    async def test_evolve_passes_timeout_to_create_adk_reflection_fn(self) -> None:
        """The config value is passed as timeout_seconds."""
        from gepa_adk import evolve
        from gepa_adk.domain.models import EvolutionResult
        from tests.conftest import MockScorer

        agent = LlmAgent(name="a", model="gemini-3.8-flash", instruction="i")
        engine = MagicMock()
        engine.run = AsyncMock(
            return_value=EvolutionResult(
                original_score=0.0,
                final_score=0.0,
                evolved_components={"instruction": "i"},
                iteration_history=[],
                total_iterations=0,
            )
        )
        with (
            patch("gepa_adk.api.AsyncGEPAEngine", return_value=engine),
            patch("gepa_adk.api.ADKAdapter"),
            patch("gepa_adk.api.create_adk_reflection_fn") as create_fn,
        ):
            await evolve(
                agent,
                [{"input": "x", "expected": "y"}],
                scorer=MockScorer(score_value=0.5),
                reflection_agent=_reflector(),
                config=EvolutionConfig(reflection_timeout_seconds=90),
            )

        assert create_fn.call_args.kwargs["timeout_seconds"] == 90

    @pytest.mark.asyncio
    async def test_evolve_group_passes_timeout_to_create_adk_reflection_fn(
        self,
    ) -> None:
        """evolve_group() passes the config value as timeout_seconds too."""
        from gepa_adk.api import evolve_group

        agents = {
            "generator": LlmAgent(
                name="generator", model="gemini-3.8-flash", instruction="g"
            ),
            "reviewer": LlmAgent(
                name="reviewer", model="gemini-3.8-flash", instruction="r"
            ),
        }
        critic = LlmAgent(name="critic", model="gemini-3.8-flash", instruction="c")
        engine = MagicMock()
        engine.run = AsyncMock(
            return_value=MagicMock(
                evolved_components={
                    "generator.instruction": "g",
                    "reviewer.instruction": "r",
                },
                original_score=0.5,
                final_score=0.8,
                iteration_history=[],
                total_iterations=1,
            )
        )
        with (
            patch("gepa_adk.api.AgentExecutor"),
            patch("gepa_adk.api.CriticScorer"),
            patch("gepa_adk.api.MultiAgentAdapter"),
            patch("gepa_adk.api.AsyncGEPAEngine", return_value=engine),
            patch("gepa_adk.api.create_adk_reflection_fn") as create_fn,
        ):
            await evolve_group(
                agents=agents,
                primary="reviewer",
                trainset=[{"input": "x"}],
                critic=critic,
                reflection_agent=_reflector(),
                config=EvolutionConfig(reflection_timeout_seconds=75),
            )

        assert create_fn.call_args.kwargs["timeout_seconds"] == 75


class TimingOutAdapter:
    """Fake adapter whose proposals are scripted to time out or succeed.

    Attributes:
        script (list[str]): Per-iteration script: ``"timeout"`` raises
            ``ReflectionTimeoutError``; any other text is the proposal.
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
        """Raise a timeout or return the scripted proposal.

        Args:
            candidate: Ignored.
            reflective_dataset: Ignored.
            components_to_update: Ignored.

        Returns:
            The next scripted proposal.

        Raises:
            ReflectionTimeoutError: When the script entry is ``"timeout"``.
        """
        from gepa_adk.domain.exceptions import ReflectionTimeoutError

        entry = self.script.pop(0)
        if entry == "timeout":
            raise ReflectionTimeoutError("instruction", timeout_seconds=300)
        return {"instruction": entry}


async def _run(script: list[str], *, patience: int = 5) -> tuple[TimingOutAdapter, Any]:
    adapter = TimingOutAdapter(script)
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=len(script), patience=patience, min_improvement_threshold=0.0
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=[{"input": "q1"}, {"input": "qü"}],
    )
    return adapter, await engine.run()


class TestEngineRecordsTimeout:
    """A timed-out reflection is a skipped iteration, not a dead run."""

    @pytest.mark.asyncio
    async def test_timeout_is_recorded_and_the_run_continues(self) -> None:
        """The timeout iteration is skipped and the next proposal is still evaluated."""
        adapter, result = await _run(["timeout", "better"])

        first, second = result.iteration_history
        assert first.accepted is False
        assert first.skip_reason == "reflection_timeout"
        assert first.score == 0.0
        assert first.evolved_component == "instruction"
        assert second.accepted is True
        assert second.skip_reason is None
        assert result.total_iterations == 2
        assert adapter.calls == [2, 2]
        assert result.evolved_components["instruction"] == "better"

    @pytest.mark.asyncio
    async def test_timeouts_count_toward_patience(self) -> None:
        """Consecutive timeouts exhaust patience and end the run with the seed."""
        adapter, result = await _run(["timeout", "timeout", "timeout"], patience=2)

        assert result.total_iterations == 2
        assert [r.skip_reason for r in result.iteration_history] == [
            "reflection_timeout",
            "reflection_timeout",
        ]
        assert adapter.calls == [2]
        assert result.evolved_components["instruction"] == "seed"

"""Acceptance tests for issue 393: report evaluations that raised.

``EvaluationBatch.failed_indices`` names the rows whose agent run raised or
returned a failed execution. The engine sums those per iteration into
``IterationRecord.failed_evaluations``, keeps the baseline count on
``EvolutionResult.baseline_failed_evaluations`` and the run total on
``EvolutionResult.total_failed_evaluations``. Scores are unchanged; this is
reporting only. The result schema version moves to 2 and version 1 dicts
still load.

Notes:
    The engine tests use ``ConfigurableMockAdapter`` with a scripted
    ``custom_evaluate``; the adapter test drives a real ``ADKAdapter`` with an
    executor that fails on two of five rows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters import ADKAdapter
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import (
    CURRENT_SCHEMA_VERSION,
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    IterationRecord,
    MultiAgentEvolutionResult,
)
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus
from tests.conftest import MockScorer
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).parents[2] / "fixtures"


class _FailingScript:
    """``custom_evaluate`` that returns scripted failed indices per call.

    Attributes:
        script (list[list[int]]): Failed row indices for each evaluate call,
            in order; the last entry repeats.
        calls (int): Number of evaluate calls made so far.
    """

    def __init__(self, script: list[list[int]]) -> None:
        """Store the script and start the call counter at zero.

        Args:
            script: Failed indices per call.
        """
        self.script = script
        self.calls = 0

    async def __call__(
        self, batch: list[Any], candidate: dict[str, str], capture_traces: bool
    ) -> EvaluationBatch[Any, Any]:
        """Return a batch scoring 0.5 everywhere except the failed rows.

        Args:
            batch: Rows to evaluate.
            candidate: Component texts (unused).
            capture_traces: Whether traces are wanted.

        Returns:
            A batch whose failed rows score 0.0 and are named in
            ``failed_indices``.
        """
        failed = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        n = len(batch)
        return EvaluationBatch(
            outputs=[""] * n,
            scores=[0.0 if i in failed else 0.5 for i in range(n)],
            trajectories=[{"trace": i} for i in range(n)] if capture_traces else None,
            failed_indices=list(failed),
        )


async def _propose_improved(
    candidate: dict[str, str], reflective_dataset: Any, components: list[str]
) -> dict[str, str]:
    """Return a proposal that differs from the parent.

    Args:
        candidate: Parent component texts.
        reflective_dataset: Unused.
        components: Unused.

    Returns:
        The parent's instruction with a trailing "!".
    """
    return {"instruction": candidate["instruction"] + "!"}


async def _run(
    script: list[list[int]] | None,
    *,
    max_iterations: int,
    valset: list[dict[str, str]] | None = None,
) -> EvolutionResult:
    trainset = [{"input": f"q{i}"} for i in range(5)]
    adapter = create_mock_adapter(
        default_score=0.5,
        custom_propose=_propose_improved,
        custom_evaluate=_FailingScript(script) if script is not None else None,
    )
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=max_iterations, patience=0, min_improvement_threshold=0.0
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset,
        valset=valset,
    )
    return await engine.run()


class TestEngineReportsFailedEvaluations:
    """Per-iteration, baseline and total counts on the result."""

    @pytest.mark.asyncio
    async def test_two_of_five_rows_fail_in_iteration_one(self) -> None:
        """Baseline 0, iteration 1 has 2 failed rows, iteration 2 has 1; total 3."""
        result = await _run([[], [1, 3], [0]], max_iterations=2)

        assert [r.failed_evaluations for r in result.iteration_history] == [2, 1]
        assert result.baseline_failed_evaluations == 0
        assert result.total_failed_evaluations == 3
        assert result.total_failed_evaluations == (
            result.baseline_failed_evaluations
            + sum(r.failed_evaluations for r in result.iteration_history)
        )

    @pytest.mark.asyncio
    async def test_baseline_failures_are_counted(self) -> None:
        """Failures during the baseline evaluation land on the baseline field."""
        result = await _run([[0, 1, 2], []], max_iterations=1)

        assert result.baseline_failed_evaluations == 3
        assert result.iteration_history[0].failed_evaluations == 0
        assert result.total_failed_evaluations == 3

    @pytest.mark.asyncio
    async def test_distinct_valset_counts_both_evaluations(self) -> None:
        """With a separate valset each candidate costs two evaluations; both count."""
        valset = [{"input": f"v{i}"} for i in range(5)]
        result = await _run([[0]], max_iterations=1, valset=valset)

        assert result.baseline_failed_evaluations == 2
        assert result.iteration_history[0].failed_evaluations == 2
        assert result.total_failed_evaluations == 4

    @pytest.mark.asyncio
    async def test_no_failures_reports_zero_everywhere(self) -> None:
        """An adapter that never sets failed_indices reports 0 at every level."""
        result = await _run(None, max_iterations=2)

        assert result.baseline_failed_evaluations == 0
        assert result.total_failed_evaluations == 0
        assert all(r.failed_evaluations == 0 for r in result.iteration_history)

    @pytest.mark.asyncio
    async def test_scores_are_unchanged_by_counting(self) -> None:
        """Failed rows still score 0.0 and the iteration score is the batch sum."""
        result = await _run([[], [1, 3]], max_iterations=1)

        assert result.original_score == pytest.approx(2.5)
        assert result.iteration_history[0].score == pytest.approx(1.5)


class TestADKAdapterNamesFailedRows:
    """``ADKAdapter.evaluate()`` fills ``failed_indices`` for rows that fail."""

    @pytest.mark.asyncio
    async def test_failed_status_rows_are_listed(self) -> None:
        """Rows 1 and 3 of 5 return FAILED; their indices are reported in order."""
        proposer = AsyncMock()
        adapter = ADKAdapter(
            agent=LlmAgent(name="a", model="gemini-3.8-flash", instruction="Answer."),
            scorer=MockScorer(score_value=0.8),
            executor=MagicMock(),
            proposer=proposer,
        )

        async def execute_agent(**kwargs: Any) -> ExecutionResult:
            text = kwargs["input_text"]
            if text in {"q1", "q3"}:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    extracted_value="",
                    session_id="s",
                    error_message="boom",
                )
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value=f"answer to {text}",
                session_id="s",
            )

        adapter._executor.execute_agent = AsyncMock(side_effect=execute_agent)
        batch = [{"input": f"q{i}"} for i in range(5)]

        result = await adapter.evaluate(batch, {"instruction": "Answer."})

        assert result.failed_indices == [1, 3]
        assert [s == 0.0 for s in result.scores] == [False, True, False, True, False]

    @pytest.mark.asyncio
    async def test_no_failures_gives_empty_list(self) -> None:
        """Every row succeeding reports an empty failed_indices list."""
        adapter = ADKAdapter(
            agent=LlmAgent(name="a", model="gemini-3.8-flash", instruction="Answer."),
            scorer=MockScorer(score_value=0.8),
            executor=MagicMock(),
            proposer=AsyncMock(),
        )
        adapter._executor.execute_agent = AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS, extracted_value="ok", session_id="s"
            )
        )

        result = await adapter.evaluate([{"input": "q0"}], {"instruction": "Answer."})

        assert result.failed_indices == []


class TestSchemaVersionTwo:
    """The schema version is 2 and version 1 results still load."""

    def test_current_schema_version_is_two(self) -> None:
        """The constant moved from 1 to 2."""
        assert CURRENT_SCHEMA_VERSION == 2

    def test_v1_evolution_result_loads_with_zero_counts(self) -> None:
        """The checked-in v1 fixture migrates to version 2 with zero failures."""
        data = json.loads((_FIXTURES / "evolution_result_v1.json").read_text())
        assert data["schema_version"] == 1

        result = EvolutionResult.from_dict(data)

        assert result.schema_version == 2
        assert result.baseline_failed_evaluations == 0
        assert result.total_failed_evaluations == 0
        assert all(r.failed_evaluations == 0 for r in result.iteration_history)
        assert all(r.skip_reason is None for r in result.iteration_history)
        assert result.final_score == data["final_score"]

    def test_v1_multiagent_result_loads(self) -> None:
        """The checked-in v1 multi-agent fixture migrates to version 2."""
        data = json.loads((_FIXTURES / "multiagent_result_v1.json").read_text())

        result = MultiAgentEvolutionResult.from_dict(data)

        assert result.schema_version == 2
        assert result.baseline_failed_evaluations == 0
        assert result.total_failed_evaluations == 0

    def test_round_trip_keeps_counts(self) -> None:
        """to_dict carries the counts and from_dict restores them."""
        result = EvolutionResult(
            original_score=0.5,
            final_score=0.7,
            evolved_components={"instruction": "x"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.7,
                    component_text="x",
                    evolved_component="instruction",
                    accepted=True,
                    failed_evaluations=2,
                )
            ],
            total_iterations=1,
            baseline_failed_evaluations=1,
            total_failed_evaluations=3,
        )

        data = result.to_dict()
        restored = EvolutionResult.from_dict(json.loads(json.dumps(data)))

        assert data["schema_version"] == 2
        assert data["baseline_failed_evaluations"] == 1
        assert data["total_failed_evaluations"] == 3
        assert data["iteration_history"][0]["failed_evaluations"] == 2
        assert restored == result

    def test_newer_version_is_rejected(self) -> None:
        """A version 3 dict is refused so a downgrade cannot misread it."""
        data = json.loads((_FIXTURES / "evolution_result_v1.json").read_text())
        data["schema_version"] = 3

        with pytest.raises(ConfigurationError, match="schema_version"):
            EvolutionResult.from_dict(data)

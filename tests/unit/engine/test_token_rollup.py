"""Acceptance tests for the run-level token rollup.

The engine adds up the token usage the executor observed on each evaluated
row and reports it per iteration on ``IterationRecord.token_usage`` and for
the whole run on ``EvolutionResult.token_usage``. A counter stays unknown
where no row provided it, and a row without usage is counted as unknown
rather than as zero. The result schema moves to version 3 with a migration
that loads older results with unknown usage.

Examples:
    Run these tests:

    ```bash
    uv run pytest tests/unit/engine/test_token_rollup.py -q
    ```

See Also:
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: ``TokenRollup``,
      ``IterationRecord`` and the schema version 3 migration.
    - [`gepa_adk.engine.async_engine`][gepa_adk.engine.async_engine]: The
      engine that folds each evaluated batch into the rollups.

Notes:
    The adapter is a fake that returns real ``ADKTrajectory`` objects with
    scripted ``TokenUsage``, so no agent or LLM runs.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from gepa_adk.domain.models import (
    CURRENT_SCHEMA_VERSION,
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    IterationRecord,
)
from gepa_adk.domain.trajectory import ADKTrajectory, MultiAgentTrajectory, TokenUsage
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch

pytestmark = pytest.mark.unit

_SCORES = {"seed": 0.5, "worse": 0.0, "better": 1.0}


def _trajectory(usage: TokenUsage | None) -> ADKTrajectory:
    """Build a trajectory carrying the given usage.

    Args:
        usage: Token usage, or None for an unobserved row.

    Returns:
        An ADKTrajectory with no tool calls.
    """
    return ADKTrajectory(
        tool_calls=(),
        state_deltas=(),
        token_usage=usage,
        final_output="o",
        error=None,
    )


class UsageAdapter:
    """Fake adapter whose rows report scripted token usage.

    Attributes:
        proposals (list[str]): Instruction texts to propose, in order.
        per_row (int): Tokens per evaluated row: ``per_row`` input and
            ``2 * per_row`` output. Every third row (index 2, 5, ...) reports
            no usage.
        calls (list[tuple[int, str, bool]]): Row count, instruction and
            ``capture_traces`` of each ``evaluate()`` call.
    """

    def __init__(self, proposals: list[str], per_row: int = 10) -> None:
        """Store the script and the per-row token figure.

        Args:
            proposals: Instruction texts to propose, one per iteration.
            per_row: Input tokens per row; output is twice that.
        """
        self.proposals = list(proposals)
        self.per_row = per_row
        self.calls: list[tuple[int, str, bool]] = []

    async def evaluate(
        self,
        batch: list[dict[str, str]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Any, Any]:
        """Score by instruction and attach usage to every third row but one.

        Args:
            batch: Rows to evaluate.
            candidate: Candidate components.
            capture_traces: Whether traces were requested.

        Returns:
            A batch with trajectories when traces were requested.
        """
        instruction = candidate["instruction"]
        self.calls.append((len(batch), instruction, capture_traces))
        trajectories = None
        if capture_traces:
            trajectories = [
                _trajectory(
                    None
                    if i % 3 == 2
                    else TokenUsage(
                        input_tokens=self.per_row,
                        output_tokens=2 * self.per_row,
                        total_tokens=3 * self.per_row,
                    )
                )
                for i in range(len(batch))
            ]
        return EvaluationBatch(
            outputs=[instruction] * len(batch),
            scores=[_SCORES[instruction]] * len(batch),
            trajectories=trajectories,
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
        """Return the next scripted proposal.

        Args:
            candidate: Ignored.
            reflective_dataset: Ignored.
            components_to_update: Ignored.

        Returns:
            The next instruction text.
        """
        return {"instruction": self.proposals.pop(0)}


def _rows(n: int) -> list[dict[str, str]]:
    """Build n rows.

    Args:
        n: Number of rows.

    Returns:
        Rows with distinct inputs.
    """
    return [{"input": f"q{i}"} for i in range(n)]


async def _run(
    proposals: list[str],
    *,
    trainset_size: int = 3,
    valset: list[dict[str, str]] | None = None,
    minibatch: int | None = None,
) -> tuple[UsageAdapter, EvolutionResult]:
    """Run the engine over the fake adapter with scripted proposals.

    Args:
        proposals: Instruction texts to propose, one per iteration.
        trainset_size: Number of trainset rows.
        valset: Separate valset rows, or None to score on the trainset.
        minibatch: Reflection minibatch size, or None for none.

    Returns:
        The adapter, for its recorded calls, and the run's result.
    """
    adapter = UsageAdapter(proposals)
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=len(proposals),
            patience=10,
            min_improvement_threshold=0.0,
            reflection_minibatch_size=minibatch,
            seed=5,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=_rows(trainset_size),
        valset=valset,
    )
    return adapter, await engine.run()


class TestTokenRollupModel:
    """TokenRollup sums what was observed and keeps the rest unknown."""

    def test_from_batch_sums_known_rows_and_counts_unknown(self) -> None:
        """Two rows with usage and one without give partial sums and one unknown."""
        from gepa_adk.domain.models import TokenRollup

        batch = EvaluationBatch(
            outputs=["a", "b", "c"],
            scores=[1.0, 1.0, 1.0],
            trajectories=[
                _trajectory(TokenUsage(3, 5, 8)),
                _trajectory(TokenUsage(4, 7, 11)),
                _trajectory(None),
            ],
        )
        rollup = TokenRollup.from_batch(batch)

        assert rollup.input_tokens == 7
        assert rollup.output_tokens == 12
        assert rollup.total_tokens == 19
        assert rollup.rows_counted == 2
        assert rollup.rows_unknown == 1

    def test_from_batch_without_traces_is_unknown(self) -> None:
        """A batch with no trajectories has every counter unknown."""
        from gepa_adk.domain.models import TokenRollup

        batch = EvaluationBatch(outputs=["a", "b"], scores=[1.0, 1.0])
        rollup = TokenRollup.from_batch(batch)

        assert rollup.input_tokens is None
        assert rollup.output_tokens is None
        assert rollup.total_tokens is None
        assert rollup.rows_counted == 0
        assert rollup.rows_unknown == 2

    def test_empty_batch_is_zero_not_unknown(self) -> None:
        """Nothing evaluated means zero tokens, which is known."""
        from gepa_adk.domain.models import TokenRollup

        rollup = TokenRollup.from_batch(EvaluationBatch(outputs=[], scores=[]))

        assert (rollup.input_tokens, rollup.output_tokens, rollup.total_tokens) == (
            0,
            0,
            0,
        )
        assert rollup.rows_counted == 0
        assert rollup.rows_unknown == 0

    def test_from_batch_reads_multi_agent_totals(self) -> None:
        """A MultiAgentTrajectory contributes its total_token_usage."""
        from gepa_adk.domain.models import TokenRollup

        inner = _trajectory(TokenUsage(1, 1, 2))
        trajectory = MultiAgentTrajectory(
            agent_trajectories={"a": inner, "b": inner},
            pipeline_output="p",
            total_token_usage=TokenUsage(2, 2, 4),
            error=None,
        )
        rollup = TokenRollup.from_batch(
            EvaluationBatch(outputs=["p"], scores=[1.0], trajectories=[trajectory])
        )

        assert (rollup.input_tokens, rollup.output_tokens, rollup.total_tokens) == (
            2,
            2,
            4,
        )
        assert rollup.rows_counted == 1

    def test_combine_adds_counters_and_propagates_unknown(self) -> None:
        """Combining sums counted rows; an all-unknown side leaves sums partial."""
        from gepa_adk.domain.models import TokenRollup

        known = TokenRollup(
            input_tokens=7,
            output_tokens=12,
            total_tokens=19,
            rows_counted=2,
            rows_unknown=1,
        )
        unknown = TokenRollup(
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            rows_counted=0,
            rows_unknown=3,
        )
        combined = known.combine(unknown)

        assert (
            combined.input_tokens,
            combined.output_tokens,
            combined.total_tokens,
        ) == (
            7,
            12,
            19,
        )
        assert combined.rows_counted == 2
        assert combined.rows_unknown == 4
        assert unknown.combine(unknown).total_tokens is None

    def test_to_dict_writes_unknown_and_round_trips(self) -> None:
        """Unknown counters serialise as the string "unknown" and load back as None."""
        from gepa_adk.domain.models import TokenRollup

        rollup = TokenRollup(
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            rows_counted=0,
            rows_unknown=2,
        )
        data = json.loads(json.dumps(rollup.to_dict()))

        assert data == {
            "input_tokens": "unknown",
            "output_tokens": "unknown",
            "total_tokens": "unknown",
            "rows_counted": 0,
            "rows_unknown": 2,
        }
        assert TokenRollup.from_dict(data) == rollup
        known = TokenRollup(
            input_tokens=1,
            output_tokens=2,
            total_tokens=3,
            rows_counted=1,
            rows_unknown=0,
        )
        assert TokenRollup.from_dict(json.loads(json.dumps(known.to_dict()))) == known


class TestEngineRollup:
    """The engine reports per-iteration and run-level usage."""

    @pytest.mark.asyncio
    async def test_iterations_and_run_total(self) -> None:
        """Each iteration's rows and the baseline add up to the run total."""
        adapter, result = await _run(["worse", "better"], trainset_size=3)

        # Every full pass: rows 0 and 1 report 10/20/30 each, row 2 is unknown.
        assert [n for n, _, _ in adapter.calls] == [3, 3, 3]
        first, second = result.iteration_history
        for record in (first, second):
            assert record.token_usage is not None
            assert record.token_usage.input_tokens == 20
            assert record.token_usage.output_tokens == 40
            assert record.token_usage.total_tokens == 60
            assert record.token_usage.rows_counted == 2
            assert record.token_usage.rows_unknown == 1
        assert result.token_usage is not None
        # Baseline plus two iterations.
        assert result.token_usage.input_tokens == 60
        assert result.token_usage.output_tokens == 120
        assert result.token_usage.total_tokens == 180
        assert result.token_usage.rows_counted == 6
        assert result.token_usage.rows_unknown == 3

    @pytest.mark.asyncio
    async def test_skipped_iteration_reports_zero(self) -> None:
        """A duplicate proposal evaluates nothing, so its usage is zero and known."""
        _, result = await _run(["worse", "worse"], trainset_size=3)

        second = result.iteration_history[1]
        assert second.skip_reason == "duplicate"
        assert second.token_usage is not None
        assert second.token_usage.total_tokens == 0
        assert second.token_usage.rows_counted == 0
        assert second.token_usage.rows_unknown == 0
        assert result.token_usage is not None
        assert result.token_usage.total_tokens == 120

    @pytest.mark.asyncio
    async def test_separate_valset_rows_are_unknown(self) -> None:
        """The valset pass captures no traces, so its rows count as unknown."""
        _, result = await _run(["better"], trainset_size=3, valset=_rows(2))

        record = result.iteration_history[0]
        assert record.token_usage is not None
        assert record.token_usage.total_tokens == 60
        assert record.token_usage.rows_counted == 2
        assert record.token_usage.rows_unknown == 3
        assert result.token_usage is not None
        assert result.token_usage.rows_unknown == 6

    @pytest.mark.asyncio
    async def test_minibatch_rejection_counts_its_rows(self) -> None:
        """A minibatch-rejected proposal reports the sampled rows only."""
        adapter, result = await _run(["worse"], trainset_size=6, minibatch=2)

        assert [n for n, _, _ in adapter.calls] == [6, 2]
        record = result.iteration_history[0]
        assert record.skip_reason == "minibatch_rejected"
        assert record.token_usage is not None
        assert record.token_usage.rows_counted + record.token_usage.rows_unknown == 2


class TestSchemaVersion3:
    """The result schema is version 3 with a migration for older dicts."""

    def test_current_version_is_3(self) -> None:
        """The constant moved to 3."""
        assert CURRENT_SCHEMA_VERSION == 3

    @pytest.mark.asyncio
    async def test_result_round_trips_with_usage(self) -> None:
        """to_dict carries token_usage on the result and each record."""
        _, result = await _run(["better"], trainset_size=3)

        data = json.loads(json.dumps(result.to_dict()))
        assert data["schema_version"] == 3
        assert data["token_usage"]["input_tokens"] == 40
        assert data["iteration_history"][0]["token_usage"]["rows_unknown"] == 1
        restored = EvolutionResult.from_dict(data)
        assert restored == result

    def test_v2_dict_loads_with_unknown_usage(self) -> None:
        """A version 2 result has no usage keys and loads with None usage."""
        record = IterationRecord(
            iteration_number=1,
            score=1.0,
            component_text="t",
            evolved_component="instruction",
            accepted=True,
        )
        v2 = {
            "schema_version": 2,
            "stop_reason": "completed",
            "original_score": 0.5,
            "final_score": 1.0,
            "evolved_components": {"instruction": "t"},
            "iteration_history": [
                {k: v for k, v in record.to_dict().items() if k != "token_usage"}
            ],
            "total_iterations": 1,
            "valset_score": None,
            "trainset_score": None,
            "objective_scores": None,
            "original_components": None,
            "baseline_failed_evaluations": 0,
            "total_failed_evaluations": 0,
        }
        result = EvolutionResult.from_dict(v2)

        assert result.schema_version == CURRENT_SCHEMA_VERSION
        assert result.token_usage is None
        assert result.iteration_history[0].token_usage is None

    def test_record_to_dict_writes_unknown_for_missing_usage(self) -> None:
        """A record without usage still serialises the key, as None."""
        record = IterationRecord(
            iteration_number=1,
            score=1.0,
            component_text="t",
            evolved_component="instruction",
            accepted=True,
        )
        data = record.to_dict()

        assert "token_usage" in data
        assert data["token_usage"] is None
        assert IterationRecord.from_dict(data) == record

"""Acceptance tests for the reflection minibatch.

``EvolutionConfig.reflection_minibatch_size`` bounds the trainset rows each
iteration runs before a proposal earns its full evaluation. The engine draws
a fresh seeded sample each iteration from the rows the parent has scores
for, evaluates the proposal on those rows, and compares it with the parent's
cached scores on the same rows. A proposal that does not beat the parent
there is recorded with ``skip_reason="minibatch_rejected"`` and nothing else
is evaluated. A proposal that does is evaluated on the full trainset when
the valset is the trainset, so defaulted-valset reuse stays correct; with a
separate valset it is scored on the valset straight away and its sample
becomes the batch it has scores for, also when a Pareto candidate selector
picks it as the next parent. A row-scored adapter proves the gate
reads the parent's scores at the sampled indices.

Examples:
    Run this module:

    ```bash
    uv run pytest tests/unit/engine/test_reflection_minibatch.py -q
    ```

See Also:
    - [`gepa_adk.engine.async_engine`][gepa_adk.engine.async_engine]: The
      engine whose minibatch gate these tests drive.
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: ``EvolutionConfig``
      and ``IterationRecord``.

Notes:
    The adapter is a fake that scores every row by the candidate's
    instruction text and records each ``evaluate()`` call, so no agent or
    LLM runs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from gepa_adk.adapters.selection.candidate_selector import ParetoCandidateSelector
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch

pytestmark = pytest.mark.unit

_SCORES = {"seed": 0.5, "worse": 0.0, "same": 0.5, "better": 1.0}


class ScriptedAdapter:
    """Fake adapter that scores by instruction text and scripts proposals.

    Attributes:
        proposals (list[str]): Instruction texts to propose, in order.
        calls (list[tuple[list[str], str, bool]]): One entry per
            ``evaluate()`` call: the row inputs, the instruction and
            ``capture_traces``.
    """

    def __init__(self, proposals: list[str]) -> None:
        """Store the scripted proposals.

        Args:
            proposals: Instruction texts to propose, one per iteration.
        """
        self.proposals = list(proposals)
        self.calls: list[tuple[list[str], str, bool]] = []

    async def evaluate(
        self,
        batch: list[dict[str, str]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Any, Any]:
        """Score every row by the candidate's instruction text.

        Args:
            batch: Rows to evaluate.
            candidate: Candidate components.
            capture_traces: Whether traces were requested.

        Returns:
            A batch with one score per row and dummy traces when requested.
        """
        instruction = candidate["instruction"]
        self.calls.append(
            ([row["input"] for row in batch], instruction, capture_traces)
        )
        score = _SCORES[instruction]
        return EvaluationBatch(
            outputs=[instruction] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{"row": row["input"]} for row in batch]
            if capture_traces
            else None,
            inputs=[row["input"] for row in batch],
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
            The next instruction text from the script.
        """
        return {"instruction": self.proposals.pop(0)}


class DatasetSizeAdapter(ScriptedAdapter):
    """Scripted adapter that records the size of each reflective dataset batch.

    Attributes:
        dataset_sizes (list[int]): Rows in the batch handed to
            ``make_reflective_dataset``, one per call.
    """

    def __init__(self, proposals: list[str]) -> None:
        """Store the proposals and start with no recorded sizes.

        Args:
            proposals: Instruction texts to propose, one per iteration.
        """
        super().__init__(proposals)
        self.dataset_sizes: list[int] = []

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[Any, Any],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Record the batch size and return an empty dataset.

        Args:
            candidate: Ignored.
            eval_batch: The parent's batch; its row count is recorded.
            components_to_update: Ignored.

        Returns:
            An empty mapping.
        """
        self.dataset_sizes.append(len(eval_batch.scores))
        return {}


def _trainset(n: int = 6) -> list[dict[str, str]]:
    """Build a trainset with distinct inputs, one non-ASCII.

    Args:
        n: Number of rows.

    Returns:
        Rows whose inputs are ``"q0"`` to ``"q{n-1}"`` with a ``"qü"`` first.
    """
    return [{"input": "qü", "expected": "a"}] + [
        {"input": f"q{i}", "expected": "a"} for i in range(1, n)
    ]


async def _run(
    proposals: list[str],
    *,
    minibatch: int | None,
    trainset: list[dict[str, str]] | None = None,
    valset: list[dict[str, str]] | None = None,
    seed: int | None = 7,
    patience: int = 5,
    max_iterations: int | None = None,
) -> tuple[ScriptedAdapter, Any]:
    adapter = ScriptedAdapter(proposals)
    config = EvolutionConfig(
        max_iterations=max_iterations or len(proposals),
        patience=patience,
        min_improvement_threshold=0.0,
        reflection_minibatch_size=minibatch,
        seed=seed,
    )
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=config,
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=trainset if trainset is not None else _trainset(),
        valset=valset,
    )
    result = await engine.run()
    return adapter, result


class TestConfigValidation:
    """reflection_minibatch_size must be None or a positive int."""

    @pytest.mark.parametrize("bad", [0, -1, 2.5, True, "3"])
    def test_rejects_non_positive_or_non_int(self, bad: Any) -> None:
        """Zero, negatives, floats, bools and strings are configuration errors."""
        with pytest.raises(ConfigurationError, match="reflection_minibatch_size"):
            EvolutionConfig(reflection_minibatch_size=bad)

    def test_default_is_none(self) -> None:
        """No minibatch by default."""
        assert EvolutionConfig().reflection_minibatch_size is None


class TestMinibatchGate:
    """A proposal earns its full evaluation only by beating the parent on the sample."""

    @pytest.mark.asyncio
    async def test_losing_proposal_costs_only_the_minibatch(self) -> None:
        """A proposal worse on the sample is recorded as rejected and not evaluated further."""
        adapter, result = await _run(["worse"], minibatch=2)

        # Baseline: full trainset with traces. Iteration 1: two rows, nothing else.
        assert [len(inputs) for inputs, _, _ in adapter.calls] == [6, 2]
        assert adapter.calls[1][1] == "worse"
        assert adapter.calls[1][2] is True
        sampled = adapter.calls[1][0]
        assert len(set(sampled)) == 2
        assert set(sampled) <= {row["input"] for row in _trainset()}

        record = result.iteration_history[0]
        assert record.accepted is False
        assert record.skip_reason == "minibatch_rejected"
        assert record.score == 0.0
        assert record.failed_evaluations == 0
        assert result.final_score == 3.0
        assert result.evolved_components["instruction"] == "seed"

    @pytest.mark.asyncio
    async def test_tie_on_the_minibatch_is_rejected(self) -> None:
        """Equal scores on the sample do not earn a full evaluation."""
        adapter, result = await _run(["same"], minibatch=3)

        assert [len(inputs) for inputs, _, _ in adapter.calls] == [6, 3]
        assert result.iteration_history[0].skip_reason == "minibatch_rejected"
        assert result.iteration_history[0].score == 1.5

    @pytest.mark.asyncio
    async def test_winning_proposal_gets_full_trainset_and_reuses_it_for_scoring(
        self,
    ) -> None:
        """A proposal better on the sample is evaluated once on the full trainset."""
        adapter, result = await _run(["worse", "better"], minibatch=2)

        assert [len(inputs) for inputs, _, _ in adapter.calls] == [6, 2, 2, 6]
        assert adapter.calls[3][1] == "better"
        assert adapter.calls[3][2] is True
        assert [inp for inp, _, _ in adapter.calls][3] == [
            r["input"] for r in _trainset()
        ]

        first, second = result.iteration_history
        assert first.skip_reason == "minibatch_rejected"
        assert second.accepted is True
        assert second.skip_reason is None
        assert second.score == 6.0
        assert result.final_score == 6.0
        assert result.trainset_score == 1.0
        assert result.evolved_components["instruction"] == "better"

    @pytest.mark.asyncio
    async def test_separate_valset_skips_the_full_trainset_pass_after_the_gate(
        self,
    ) -> None:
        """With a distinct valset the winner goes straight from the gate to the valset."""
        valset = [{"input": f"v{i}", "expected": "a"} for i in range(3)]
        adapter, result = await _run(["worse", "better"], minibatch=2, valset=valset)

        sizes = [len(inputs) for inputs, _, _ in adapter.calls]
        assert sizes == [6, 3, 2, 2, 3]
        assert adapter.calls[3][1] == "better"
        assert adapter.calls[3][2] is True
        assert adapter.calls[4][0] == ["v0", "v1", "v2"]
        assert adapter.calls[4][2] is False
        first, second = result.iteration_history
        assert first.skip_reason == "minibatch_rejected"
        assert second.accepted is True
        assert second.skip_reason is None
        assert result.final_score == 3.0
        assert result.valset_score == 1.0
        assert result.evolved_components["instruction"] == "better"

    @pytest.mark.asyncio
    async def test_next_gate_compares_on_the_rows_the_parent_has(self) -> None:
        """After a skipped full pass the parent has scores for its sample only."""
        valset = [{"input": f"v{i}", "expected": "a"} for i in range(3)]
        adapter, result = await _run(["better", "same"], minibatch=2, valset=valset)

        sizes = [len(inputs) for inputs, _, _ in adapter.calls]
        assert sizes == [6, 3, 2, 3, 2]
        assert adapter.calls[4][1] == "same"
        assert adapter.calls[4][0] == adapter.calls[2][0]
        first, second = result.iteration_history
        assert first.accepted is True
        assert second.skip_reason == "minibatch_rejected"
        assert result.evolved_components["instruction"] == "better"

    @pytest.mark.asyncio
    async def test_reflective_dataset_reads_from_the_parents_batch(self) -> None:
        """The dataset for the next proposal comes from whatever batch the parent has."""
        valset = [{"input": f"v{i}", "expected": "a"} for i in range(3)]
        adapter = DatasetSizeAdapter(["better", "same"])
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=EvolutionConfig(
                max_iterations=2,
                patience=5,
                min_improvement_threshold=0.0,
                reflection_minibatch_size=2,
                seed=7,
            ),
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=_trainset(),
            valset=valset,
        )
        await engine.run()

        assert adapter.dataset_sizes == [6, 2]

    @pytest.mark.asyncio
    async def test_same_seed_draws_the_same_rows(self) -> None:
        """The sample is seeded, so two runs with one seed draw identical rows."""
        first, _ = await _run(["worse", "worse", "worse"], minibatch=2, seed=11)
        second, _ = await _run(["worse", "worse", "worse"], minibatch=2, seed=11)

        draws_first = [inputs for inputs, _, _ in first.calls[1:]]
        draws_second = [inputs for inputs, _, _ in second.calls[1:]]
        assert draws_first == draws_second
        assert len(draws_first) == 3
        # Fresh each iteration: over three draws of two from six, not all identical.
        assert len({tuple(sorted(d)) for d in draws_first}) > 1

    @pytest.mark.asyncio
    async def test_rejections_count_toward_patience(self) -> None:
        """Minibatch rejections advance stagnation and stop the run."""
        adapter, result = await _run(
            ["worse", "worse", "worse"], minibatch=2, patience=2, max_iterations=3
        )

        assert result.total_iterations == 2
        assert [r.skip_reason for r in result.iteration_history] == [
            "minibatch_rejected",
            "minibatch_rejected",
        ]
        assert [len(inputs) for inputs, _, _ in adapter.calls] == [6, 2, 2]


class TestMinibatchWithParetoSelector:
    """A Pareto-selected parent keeps the rows its minibatch batch covers."""

    @pytest.mark.asyncio
    async def test_selected_parent_gates_on_its_sampled_rows(self) -> None:
        """The second gate reuses the accepted parent's minibatch rows."""
        valset = [{"input": f"v{i}", "expected": "a"} for i in range(3)]
        adapter = ScriptedAdapter(["better", "same"])
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=EvolutionConfig(
                max_iterations=2,
                patience=5,
                min_improvement_threshold=0.0,
                reflection_minibatch_size=2,
                seed=7,
            ),
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=_trainset(),
            valset=valset,
            candidate_selector=ParetoCandidateSelector(),
        )
        result = await engine.run()

        sizes = [len(inputs) for inputs, _, _ in adapter.calls]
        assert sizes == [6, 3, 2, 3, 2]
        assert adapter.calls[4][1] == "same"
        assert adapter.calls[4][0] == adapter.calls[2][0]
        first, second = result.iteration_history
        assert first.accepted is True
        assert second.skip_reason == "minibatch_rejected"


class RowScoredAdapter(ScriptedAdapter):
    """Fake adapter whose score depends on the row as well as the instruction.

    Attributes:
        table (dict[str, dict[str, float]]): Score per instruction per row input.
    """

    table: dict[str, dict[str, float]] = {
        "seed": {"a": 0.9, "b": 0.1},
        "flat": {"a": 0.5, "b": 0.5},
    }

    async def evaluate(
        self,
        batch: list[dict[str, str]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Any, Any]:
        """Score each row from the table.

        Args:
            batch: Rows to evaluate.
            candidate: Candidate components.
            capture_traces: Whether traces were requested.

        Returns:
            A batch with the table's score for each row.
        """
        instruction = candidate["instruction"]
        inputs = [row["input"] for row in batch]
        self.calls.append((inputs, instruction, capture_traces))
        return EvaluationBatch(
            outputs=[instruction] * len(batch),
            scores=[self.table[instruction][i] for i in inputs],
            trajectories=[{"row": i} for i in inputs] if capture_traces else None,
            inputs=inputs,
        )


class TestGateComparesTheSampledRows:
    """The parent's scores are read at the sampled indices, not anywhere else."""

    @staticmethod
    async def _run_rows(seed: int, *, selector: bool) -> RowScoredAdapter:
        from gepa_adk.adapters.selection.candidate_selector import (
            ParetoCandidateSelector,
        )

        adapter = RowScoredAdapter(["flat"])
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=EvolutionConfig(
                max_iterations=1,
                patience=5,
                min_improvement_threshold=0.0,
                reflection_minibatch_size=1,
                seed=seed,
            ),
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=[{"input": "a"}, {"input": "b"}],
            candidate_selector=ParetoCandidateSelector() if selector else None,
        )
        await engine.run()
        return adapter

    @pytest.mark.asyncio
    @pytest.mark.parametrize("selector", [False, True])
    async def test_drawing_the_parents_weak_row_passes(self, selector: bool) -> None:
        """Seed 5 draws row b, where the parent scores 0.1: the flat 0.5 passes."""
        adapter = await self._run_rows(5, selector=selector)

        assert adapter.calls[1][0] == ["b"]
        assert [len(inputs) for inputs, _, _ in adapter.calls] == [2, 1, 2]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("selector", [False, True])
    async def test_drawing_the_parents_strong_row_rejects(self, selector: bool) -> None:
        """Seed 1 draws row a, where the parent scores 0.9: the flat 0.5 is rejected."""
        adapter = await self._run_rows(1, selector=selector)

        assert adapter.calls[1][0] == ["a"]
        assert [len(inputs) for inputs, _, _ in adapter.calls] == [2, 1]


class TestMinibatchDisabled:
    """None, or a size covering the trainset, keeps today's behaviour."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("minibatch", [None, 6, 60])
    async def test_full_trainset_each_iteration(self, minibatch: int | None) -> None:
        """Each proposal is evaluated once on the full trainset, as on 2.4.0."""
        adapter, result = await _run(["worse", "better"], minibatch=minibatch)

        assert [len(inputs) for inputs, _, _ in adapter.calls] == [6, 6, 6]
        assert [r.skip_reason for r in result.iteration_history] == [None, None]
        assert [r.accepted for r in result.iteration_history] == [False, True]
        assert result.final_score == 6.0

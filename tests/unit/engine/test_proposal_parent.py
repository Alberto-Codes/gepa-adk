"""Acceptance tests for recording the parent a proposal was mutated from.

The candidate the reflector rewrote is the proposal's parent. The engine
draws the parent once, in ``_propose_mutation``, and passes that draw to
``ParetoState.add_candidate`` instead of asking the selector a second
time. The proposal's ``parent_id`` is the parent's ``Candidate.id`` and
its ``generation`` is the parent's plus one from the moment it is
proposed. Every ``IterationRecord`` names its ``candidate_id`` and
``parent_ids``, and the result schema moves to version 4 with a migration
that fills the two new fields with ``None``.

Examples:
    Run these tests on their own:

    ```bash
    uv run pytest tests/unit/engine/test_proposal_parent.py -q
    ```

See Also:
    - [`gepa_adk.engine.async_engine`][gepa_adk.engine.async_engine]: The
      engine that records the genealogy.
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: ``IterationRecord``
      and the schema migration.

Notes:
    The adapter is a fake whose rows score differently per proposal so
    the Pareto front holds several leaders and a seeded selector draws
    among them. The selector is wrapped to record each draw.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from gepa_adk.adapters.selection.candidate_selector import ParetoCandidateSelector
from gepa_adk.domain.exceptions import EmptyProposalError
from gepa_adk.domain.models import (
    CURRENT_SCHEMA_VERSION,
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    IterationRecord,
)
from gepa_adk.domain.state import ParetoState
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch

pytestmark = pytest.mark.unit

# Row scores per proposal text: each proposal leads a different row so the
# Pareto front keeps several candidates for the selector to draw from.
_ROWS: dict[str, list[float]] = {
    "seed": [0.5, 0.5, 0.5],
    "p1": [0.9, 0.2, 0.5],
    "p2": [0.2, 0.9, 0.5],
    "p3": [0.5, 0.5, 0.95],
    "p4": [0.6, 0.6, 0.6],
    "p5": [0.95, 0.1, 0.1],
    "p6": [0.1, 0.95, 0.1],
}


class RowScoringAdapter:
    """Fake adapter with a fixed per-row score table and scripted proposals.

    Attributes:
        script (list[str]): Proposals returned in order; ``""`` makes the
            proposal empty.
        parents (list[str]): The instruction text of each candidate the
            reflector was asked to rewrite, in order.
    """

    def __init__(self, script: list[str]) -> None:
        """Store the script.

        Args:
            script: Proposal texts, consumed in order.
        """
        self.script = list(script)
        self.parents: list[str] = []

    async def evaluate(
        self,
        batch: list[dict[str, str]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Any, Any]:
        """Score each row from the table for the candidate's instruction.

        Args:
            batch: Rows to evaluate.
            candidate: Candidate components.
            capture_traces: Whether traces were requested.

        Returns:
            A batch with the table's score per row.
        """
        scores = _ROWS[candidate["instruction"]][: len(batch)]
        return EvaluationBatch(
            outputs=[""] * len(batch),
            scores=scores,
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
        """Record the parent text and return the next scripted proposal.

        Args:
            candidate: The candidate being rewritten.
            reflective_dataset: Ignored.
            components_to_update: Ignored.

        Returns:
            The next scripted proposal.
        """
        self.parents.append(candidate["instruction"])
        return {"instruction": self.script.pop(0)}


class RecordingSelector:
    """Selector wrapper that records every draw it hands the engine.

    Attributes:
        draws (list[int]): Candidate indices returned, in order.
    """

    def __init__(self, inner: ParetoCandidateSelector) -> None:
        """Wrap a selector.

        Args:
            inner: The selector that makes the draws.
        """
        self._inner = inner
        self.draws: list[int] = []

    async def select_candidate(self, state: ParetoState) -> int:
        """Draw from the inner selector and record the index.

        Args:
            state: The Pareto state to draw from.

        Returns:
            The drawn candidate index.
        """
        idx = await self._inner.select_candidate(state)
        self.draws.append(idx)
        return idx


_BATCH = [{"input": "q1"}, {"input": "q2"}, {"input": "q3"}]
_SEED = Candidate(components={"instruction": "seed"})


def _engine(
    adapter: RowScoringAdapter, iterations: int, selector: Any = None
) -> AsyncGEPAEngine:
    return AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=iterations, patience=10, min_improvement_threshold=0.0
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=_BATCH,
        candidate_selector=selector,
    )


class TestParetoParentIsTheMutatedCandidate:
    """With a stochastic selector, the recorded parent is the single draw."""

    @pytest.mark.asyncio
    async def test_one_draw_per_iteration_and_it_is_the_recorded_parent(
        self,
    ) -> None:
        """Each record's parent is the candidate the reflector rewrote."""
        script = ["p1", "p2", "p3", "p4", "p5", "p6"]
        adapter = RowScoringAdapter(script)
        selector = RecordingSelector(ParetoCandidateSelector(rng=random.Random(7)))
        engine = _engine(adapter, len(script), selector)

        result = await engine.run()

        state = engine._pareto_state
        assert state is not None
        assert result.total_iterations == 6
        assert len(selector.draws) == 6
        assert len(state.candidates) == 7
        for i, record in enumerate(result.iteration_history):
            proposal_idx = i + 1
            parent_idx = selector.draws[i]
            parent = state.candidates[parent_idx]
            proposal = state.candidates[proposal_idx]
            assert record.skip_reason is None
            assert record.candidate_id == proposal.id
            assert record.parent_ids == [parent.id]
            assert state.parent_indices[proposal_idx] == [parent_idx]
            assert proposal.parent_id == parent.id
            assert proposal.generation == parent.generation + 1
            assert adapter.parents[i] == parent.components["instruction"]
        # The seeded draws spread over the front, so the edges are not trivial
        assert len(set(selector.draws)) >= 2


class TestBestCandidateParentWithoutSelector:
    """Without a selector, the parent is the current best candidate."""

    @pytest.mark.asyncio
    async def test_parent_ids_follow_the_accepted_lineage(self) -> None:
        """p1 descends from the seed and p4 from p1 by id, not by generation."""
        adapter = RowScoringAdapter(["p1", "p4"])
        result = await _engine(adapter, 2).run()

        first, second = result.iteration_history
        assert first.accepted is True
        assert first.candidate_id == Candidate(components={"instruction": "p1"}).id
        assert first.parent_ids == [_SEED.id]
        assert second.accepted is True
        assert second.candidate_id == Candidate(components={"instruction": "p4"}).id
        assert second.parent_ids == [first.candidate_id]

    @pytest.mark.asyncio
    async def test_accepted_candidate_keeps_its_parent_id_and_generation(
        self,
    ) -> None:
        """Acceptance no longer rewrites the lineage with a gen-N label."""
        adapter = RowScoringAdapter(["p1", "p4"])
        engine = _engine(adapter, 2)

        await engine.run()

        assert engine._state is not None
        best = engine._state.best_candidate
        assert best.components["instruction"] == "p4"
        assert best.generation == 2
        assert best.parent_id == Candidate(components={"instruction": "p1"}).id
        assert not str(best.parent_id).startswith("gen-")


class TestSkippedRecords:
    """Skipped iterations name what they can."""

    @pytest.mark.asyncio
    async def test_duplicate_skip_names_the_candidate_and_parent(self) -> None:
        """A duplicate proposal still records its id and its parent."""
        adapter = RowScoringAdapter(["p1", "p1"])
        result = await _engine(adapter, 2).run()

        first, second = result.iteration_history
        assert second.skip_reason == "duplicate"
        assert second.candidate_id == first.candidate_id
        assert second.parent_ids == [first.candidate_id]

    @pytest.mark.asyncio
    async def test_empty_skip_has_no_candidate(self) -> None:
        """An empty proposal has no candidate id and no parent ids."""
        from tests.fixtures.adapters import create_mock_adapter

        async def empty(
            candidate: dict[str, str],
            reflective_dataset: Any,
            components_to_update: list[str],
        ) -> dict[str, str]:
            """Raise the error the proposer raises after two empty reflections.

            Args:
                candidate: Ignored.
                reflective_dataset: Ignored.
                components_to_update: Ignored.

            Raises:
                EmptyProposalError: Always.
            """
            raise EmptyProposalError("instruction")

        adapter = create_mock_adapter(custom_propose=empty)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=EvolutionConfig(max_iterations=1, patience=5),
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=_BATCH,
        )

        result = await engine.run()

        record = result.iteration_history[0]
        assert record.skip_reason == "empty_proposal"
        assert record.candidate_id is None
        assert record.parent_ids is None


class TestSchemaVersionFour:
    """IterationRecord carries the two new fields and migrates from v3."""

    def test_current_schema_version_is_four(self) -> None:
        """The result schema is bumped for the new record fields."""
        assert CURRENT_SCHEMA_VERSION == 4

    def test_record_round_trips_the_new_fields(self) -> None:
        """to_dict and from_dict carry candidate_id and parent_ids."""
        record = IterationRecord(
            iteration_number=1,
            score=1.0,
            component_text="p1",
            evolved_component="instruction",
            accepted=True,
            candidate_id="abc123",
            parent_ids=["seed01"],
        )

        data = record.to_dict()

        assert data["candidate_id"] == "abc123"
        assert data["parent_ids"] == ["seed01"]
        assert len(data) == 12
        assert IterationRecord.from_dict(data) == record

    def test_record_defaults_to_none(self) -> None:
        """Both fields default to None on construction and on load."""
        record = IterationRecord(
            iteration_number=1,
            score=0.0,
            component_text="",
            evolved_component="instruction",
            accepted=False,
        )
        loaded = IterationRecord.from_dict(
            {
                k: v
                for k, v in record.to_dict().items()
                if k not in ("candidate_id", "parent_ids")
            }
        )

        assert record.candidate_id is None
        assert record.parent_ids is None
        assert loaded.candidate_id is None
        assert loaded.parent_ids is None

    def test_v3_result_migrates_with_none_fills(self) -> None:
        """A version 3 dict loads as version 4 with None in the new fields."""
        result = EvolutionResult(
            original_score=0.5,
            final_score=1.0,
            evolved_components={"instruction": "p1"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=1.0,
                    component_text="p1",
                    evolved_component="instruction",
                    accepted=True,
                    candidate_id="abc123",
                    parent_ids=["seed01"],
                )
            ],
            total_iterations=1,
        )
        data = result.to_dict()
        data["schema_version"] = 3
        data["iteration_history"] = [
            {k: v for k, v in r.items() if k not in ("candidate_id", "parent_ids")}
            for r in data["iteration_history"]
        ]

        loaded = EvolutionResult.from_dict(data)

        assert loaded.schema_version == 4
        assert loaded.iteration_history[0].candidate_id is None
        assert loaded.iteration_history[0].parent_ids is None
        assert loaded.final_score == 1.0

    def test_v4_result_round_trips(self) -> None:
        """A current result keeps the genealogy through to_dict/from_dict."""
        record = IterationRecord(
            iteration_number=1,
            score=1.0,
            component_text="p1",
            evolved_component="instruction",
            accepted=True,
            candidate_id="abc123",
            parent_ids=["seed01"],
        )
        result = EvolutionResult(
            original_score=0.5,
            final_score=1.0,
            evolved_components={"instruction": "p1"},
            iteration_history=[record],
            total_iterations=1,
        )

        loaded = EvolutionResult.from_dict(result.to_dict())

        assert loaded.schema_version == 4
        assert loaded.iteration_history[0].candidate_id == "abc123"
        assert loaded.iteration_history[0].parent_ids == ["seed01"]

"""Acceptance tests for issue 380: skip a proposal already scored.

Before evaluating a proposal the engine compares its ``Candidate.id`` with
every candidate it has scored in the run (the baseline, each evaluated
proposal and each evaluated merge). A match skips the evaluation, reuses
that candidate's acceptance score, counts the iteration toward stagnation
and records it with ``skip_reason="duplicate"``. A merge candidate equal to
a scored one is skipped without evaluation or a record of its own, and the
iteration that scheduled it keeps its record.

Notes:
    The tests drive ``ConfigurableMockAdapter`` from
    ``tests/fixtures/adapters.py`` with a ``custom_propose`` that repeats
    itself, and count ``adapter.evaluate_calls``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from structlog.testing import capture_logs

from gepa_adk.adapters.selection.candidate_selector import ParetoCandidateSelector
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.domain.types import ProposalResult
from gepa_adk.engine import AsyncGEPAEngine
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.unit


def _constant(text: str):
    async def propose(
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components: list[str],
    ) -> dict[str, str]:
        return {"instruction": text}

    return propose


async def _run(text: str, *, scores: list[float], max_iterations: int, patience: int):
    adapter = create_mock_adapter(scores=scores, custom_propose=_constant(text))
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=max_iterations,
            patience=patience,
            min_improvement_threshold=0.0,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=[{"input": "q1"}, {"input": "q2"}],
    )
    with capture_logs() as logs:
        result = await engine.run()
    return adapter, result, [e for e in logs if e["event"] == "proposal.duplicate"]


class TestDuplicateProposalIsNotReEvaluated:
    """One evaluation per distinct candidate; repeats reuse the score."""

    @pytest.mark.asyncio
    async def test_same_text_every_iteration_is_evaluated_once(self) -> None:
        """Four iterations of one proposal cost one evaluation after the baseline."""
        adapter, result, dupes = await _run(
            "same", scores=[0.5, 0.7], max_iterations=4, patience=0
        )

        assert len(adapter.evaluate_calls) == 2
        assert result.total_iterations == 4
        assert result.evolved_components == {"instruction": "same"}
        history = result.iteration_history
        assert [r.accepted for r in history] == [True, False, False, False]
        assert [r.skip_reason for r in history] == [
            None,
            "duplicate",
            "duplicate",
            "duplicate",
        ]
        assert all(r.score == pytest.approx(1.4) for r in history)
        assert all(r.component_text == "same" for r in history)
        assert [d["iteration"] for d in dupes] == [2, 3, 4]
        same_id = Candidate(components={"instruction": "same"}).id
        assert all(d["candidate_id"] == same_id for d in dupes)
        assert all(d["score"] == pytest.approx(1.4) for d in dupes)

    @pytest.mark.asyncio
    async def test_duplicates_count_toward_patience(self) -> None:
        """Two duplicate iterations exhaust patience=2 after the accepted one."""
        adapter, result, dupes = await _run(
            "same", scores=[0.5, 0.7], max_iterations=10, patience=2
        )

        assert result.total_iterations == 3
        assert len(adapter.evaluate_calls) == 2
        assert len(dupes) == 2

    @pytest.mark.asyncio
    async def test_proposal_equal_to_the_seed_is_a_duplicate_of_the_baseline(
        self,
    ) -> None:
        """A reflector that hands back the seed text triggers no evaluation."""
        adapter, result, dupes = await _run(
            "seed", scores=[0.5], max_iterations=2, patience=0
        )

        assert len(adapter.evaluate_calls) == 1
        assert result.evolved_components == {"instruction": "seed"}
        assert [r.skip_reason for r in result.iteration_history] == [
            "duplicate",
            "duplicate",
        ]
        assert all(r.score == pytest.approx(1.0) for r in result.iteration_history)
        assert len(dupes) == 2

    @pytest.mark.asyncio
    async def test_distinct_proposals_are_still_evaluated(self) -> None:
        """A proposal that differs from everything scored is evaluated as before."""

        async def improving(
            candidate: dict[str, str],
            reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
            components: list[str],
        ) -> dict[str, str]:
            return {"instruction": candidate["instruction"] + "!"}

        adapter = create_mock_adapter(scores=[0.5, 0.6, 0.7], custom_propose=improving)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=EvolutionConfig(
                max_iterations=2, patience=0, min_improvement_threshold=0.0
            ),
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=[{"input": "q1"}, {"input": "q2"}],
        )
        with capture_logs() as logs:
            result = await engine.run()

        assert len(adapter.evaluate_calls) == 3
        assert all(r.skip_reason is None for r in result.iteration_history)
        assert not [e for e in logs if e["event"] == "proposal.duplicate"]


class _SeedMergeProposer:
    """Merge proposer stub that always proposes the seed candidate.

    Attributes:
        calls (int): Number of ``propose`` calls received.
    """

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.calls = 0

    async def propose(self, state: Any) -> ProposalResult:
        """Return the already scored seed as the merge result.

        Args:
            state: The engine's ParetoState (unused).

        Returns:
            A merge ProposalResult whose candidate equals the seed.
        """
        self.calls += 1
        return ProposalResult(
            candidate=Candidate(components={"instruction": "seed"}),
            parent_indices=[0, 1],
            tag="merge",
            metadata={"ancestor_idx": 0},
        )


class TestDuplicateMergeCandidateIsSkipped:
    """A merge equal to a scored candidate is not evaluated or recorded."""

    @pytest.mark.asyncio
    async def test_merge_equal_to_the_seed_is_skipped_without_a_record(
        self,
    ) -> None:
        """The accepted proposal schedules a merge that repeats the seed."""
        adapter = create_mock_adapter(
            scores=[0.5, 0.7], custom_propose=_constant("same")
        )
        merge_proposer = _SeedMergeProposer()
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=EvolutionConfig(
                max_iterations=1,
                patience=0,
                min_improvement_threshold=0.0,
                use_merge=True,
                max_merge_invocations=5,
            ),
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=[{"input": "q1"}, {"input": "q2"}],
            candidate_selector=ParetoCandidateSelector(),
            merge_proposer=merge_proposer,
        )
        with capture_logs() as logs:
            result = await engine.run()

        assert merge_proposer.calls == 1
        assert [c[1] for c in adapter.evaluate_calls] == [
            {"instruction": "seed"},
            {"instruction": "same"},
        ]
        skipped = [e for e in logs if e["event"] == "merge.proposal_skipped"]
        assert len(skipped) == 1
        assert skipped[0]["reason"] == "duplicate"
        assert skipped[0]["candidate_id"] == (
            Candidate(components={"instruction": "seed"}).id
        )
        assert len(result.iteration_history) == 1
        record = result.iteration_history[0]
        assert record.iteration_number == 1
        assert record.component_text == "same"
        assert record.accepted is True
        assert record.skip_reason is None

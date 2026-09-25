"""Acceptance tests for issue 390: a stable short id on Candidate.

``Candidate.id`` is a short hash of the candidate's components, so two
candidates with the same components share an id and any change to a
component changes it. The engine puts ``candidate_id`` on its evaluation,
acceptance, reuse and Pareto log events so a run's log can be read per
candidate.

Notes:
    The engine tests run ``ConfigurableMockAdapter`` from
    ``tests/fixtures/adapters.py`` under ``structlog.testing.capture_logs``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

import pytest
from structlog.testing import capture_logs

from gepa_adk.adapters.selection.candidate_selector import ParetoCandidateSelector
from gepa_adk.domain.models import Candidate, EvolutionConfig, EvolutionResult
from gepa_adk.engine import AsyncGEPAEngine
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.unit

_HEX12 = re.compile(r"^[0-9a-f]{12}$")


async def _propose_improved(
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components: list[str],
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


class TestCandidateId:
    """The id is a 12-hex-character hash of the components."""

    def test_id_is_twelve_hex_chars(self) -> None:
        """A candidate's id matches the short hash format."""
        assert _HEX12.match(Candidate(components={"instruction": "seed"}).id)

    def test_same_components_share_an_id(self) -> None:
        """Two candidates with equal components have equal ids."""
        a = Candidate(components={"instruction": "seed", "schema": "{}"})
        b = Candidate(components={"schema": "{}", "instruction": "seed"}, generation=3)
        assert a.id == b.id

    def test_changed_component_changes_the_id(self) -> None:
        """Any component change changes the id."""
        a = Candidate(components={"instruction": "seed"})
        b = Candidate(components={"instruction": "seed!"})
        c = Candidate(components={"instruction": "seed", "extra": "x"})
        assert len({a.id, b.id, c.id}) == 3

    def test_id_is_stable_across_processes(self) -> None:
        """The hash is deterministic, not salted per process."""
        # sha256 of the canonical JSON '{"instruction": "seed"}' truncated to 12
        import hashlib
        import json

        expected = hashlib.sha256(
            json.dumps({"instruction": "seed"}, sort_keys=True).encode()
        ).hexdigest()[:12]
        assert Candidate(components={"instruction": "seed"}).id == expected

    def test_non_ascii_text_hashes_the_raw_characters(self) -> None:
        """The hash is over ensure_ascii=False JSON, so accents are not escaped."""
        import hashlib
        import json

        components = {"instruction": "héllo wörld"}
        expected = hashlib.sha256(
            json.dumps(components, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:12]
        assert Candidate(components=components).id == expected

    def test_result_schema_is_unchanged(self) -> None:
        """EvolutionResult.to_dict() carries no candidate id and no new key."""
        result = EvolutionResult(
            original_score=0.5,
            final_score=0.5,
            evolved_components={"instruction": "seed"},
            iteration_history=[],
            total_iterations=0,
        )
        assert "candidate_id" not in result.to_dict()
        assert "id" not in result.to_dict()


async def _run(*, pareto: bool) -> list[MutableMapping[str, Any]]:
    adapter = create_mock_adapter(
        scores=[0.5, 0.7, 0.6], custom_propose=_propose_improved
    )
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=2, patience=0, min_improvement_threshold=0.0
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=[{"input": "q1"}, {"input": "q2"}],
        candidate_selector=ParetoCandidateSelector() if pareto else None,
    )
    with capture_logs() as logs:
        await engine.run()
    return logs


def _ids(logs: list[MutableMapping[str, Any]], event: str) -> list[str]:
    return [e["candidate_id"] for e in logs if e["event"] == event]


class TestEngineLogsCarryCandidateId:
    """Evaluation, acceptance, reuse and Pareto events name the candidate."""

    @pytest.mark.asyncio
    async def test_evaluation_events_have_distinct_ids_per_candidate(self) -> None:
        """Baseline, proposal 1 and proposal 2 are evaluated under three ids."""
        logs = await _run(pareto=False)

        ids = _ids(logs, "evaluation.completed")
        assert len(ids) == 3
        assert len(set(ids)) == 3
        assert all(_HEX12.match(i) for i in ids)
        seed, p1, p2 = ids
        assert seed == Candidate(components={"instruction": "seed"}).id
        assert p1 == Candidate(components={"instruction": "seed!"}).id
        assert p2 == Candidate(components={"instruction": "seed!!"}).id

    @pytest.mark.asyncio
    async def test_acceptance_events_carry_the_proposal_id(self) -> None:
        """Iteration 1 (0.7) is accepted, iteration 2 (0.6) rejected, each with its id."""
        logs = await _run(pareto=False)

        accepted = [e for e in logs if e["event"] == "proposal.accepted"]
        rejected = [e for e in logs if e["event"] == "proposal.rejected"]
        assert [e["iteration"] for e in accepted] == [1]
        assert [e["iteration"] for e in rejected] == [2]
        assert (
            accepted[0]["candidate_id"]
            == Candidate(components={"instruction": "seed!"}).id
        )
        assert (
            rejected[0]["candidate_id"]
            == Candidate(components={"instruction": "seed!!"}).id
        )
        assert accepted[0]["score"] == pytest.approx(1.4)
        assert rejected[0]["score"] == pytest.approx(1.2)

    @pytest.mark.asyncio
    async def test_reuse_events_carry_the_candidate_id(self) -> None:
        """Each reuse of the trainset batch names the candidate it belongs to."""
        logs = await _run(pareto=False)

        reuse_ids = _ids(logs, "evaluation.reuse_trainset_batch")
        assert reuse_ids == _ids(logs, "evaluation.completed")

    @pytest.mark.asyncio
    async def test_pareto_events_carry_the_candidate_id(self) -> None:
        """pareto_frontier.candidate_added names the candidate for each proposal."""
        logs = await _run(pareto=True)

        added = [e for e in logs if e["event"] == "pareto_frontier.candidate_added"]
        assert [e["iteration"] for e in added] == [1, 2]
        assert [e["candidate_id"] for e in added] == [
            Candidate(components={"instruction": "seed!"}).id,
            Candidate(components={"instruction": "seed!!"}).id,
        ]

    @pytest.mark.asyncio
    async def test_separate_valset_logs_two_evaluations_per_candidate(self) -> None:
        """A distinct valset costs a reflection and a scoring evaluation each."""
        adapter = create_mock_adapter(
            scores=[0.5, 0.5, 0.7, 0.7], custom_propose=_propose_improved
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=EvolutionConfig(
                max_iterations=1, patience=0, min_improvement_threshold=0.0
            ),
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=[{"input": "q1"}, {"input": "q2"}],
            valset=[{"input": "v1"}],
        )
        with capture_logs() as logs:
            await engine.run()

        completed = [e for e in logs if e["event"] == "evaluation.completed"]
        assert len(completed) == len(adapter.evaluate_calls) == 4
        assert [e["phase"] for e in completed] == ["reflection", "scoring"] * 2
        assert [e["n"] for e in completed] == [2, 1, 2, 1]
        seed = Candidate(components={"instruction": "seed"}).id
        p1 = Candidate(components={"instruction": "seed!"}).id
        assert [e["candidate_id"] for e in completed] == [seed, seed, p1, p1]
        assert not [e for e in logs if e["event"] == "evaluation.reuse_trainset_batch"]

"""Acceptance tests for the engine's per-candidate reflection batch cache.

Every candidate added to the Pareto state gets its reflection batch cached
in ``_candidate_eval_batches`` (and its trainset rows in
``_candidate_eval_rows``) right away, including a merged candidate. A
selector that returns an index with no cached batch breaks its contract,
so ``_propose_mutation`` raises ``ConfigurationError`` instead of quietly
evaluating the parent on the full trainset.

Examples:
    Run these tests on their own:

    ```bash
    uv run pytest tests/unit/engine/test_candidate_eval_cache.py -q
    ```

See Also:
    - [`gepa_adk.engine.async_engine`][gepa_adk.engine.async_engine]: The
      engine that keeps the cache.

Notes:
    The adapter comes from ``create_mock_adapter`` with a custom evaluate
    that scores each row from a per-text table, so a batch cached for the
    wrong candidate has the wrong scores and outputs.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from gepa_adk.adapters.selection.candidate_selector import ParetoCandidateSelector
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.domain.state import ParetoState
from gepa_adk.domain.types import FrontierType, ProposalResult
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch
from tests.fixtures.adapters import ConfigurableMockAdapter, create_mock_adapter

pytestmark = pytest.mark.unit

# Row scores per instruction text. Acceptance sums rows: seed 1.5, p1 1.7,
# m1 1.95 (merge accepted), p2 2.05, m2 0.3 (merge rejected), p3 2.4.
_ROWS: dict[str, list[float]] = {
    "seed": [0.5, 0.5, 0.5],
    "p1": [0.9, 0.2, 0.6],
    "m1": [0.3, 0.95, 0.7],
    "p2": [0.95, 0.3, 0.8],
    "m2": [0.1, 0.1, 0.1],
    "p3": [0.6, 0.9, 0.9],
}

_BATCH = [{"input": "q1"}, {"input": "q2"}, {"input": "q3"}]


class ScriptedMergeProposer:
    """Merge proposer stub returning scripted merged texts.

    Attributes:
        script (list[str | None]): Merged instruction per call; None means
            no merge is possible.
        calls (int): Number of ``propose`` calls.
    """

    def __init__(self, script: list[str | None]) -> None:
        """Store the script.

        Args:
            script: Merged instruction texts, consumed in order.
        """
        self.script = list(script)
        self.calls = 0

    async def propose(
        self,
        state: ParetoState,
        eval_batch: EvaluationBatch | None = None,
    ) -> ProposalResult | None:
        """Return the next scripted merge of the first two candidates.

        Args:
            state: The Pareto state to merge from.
            eval_batch: Ignored.

        Returns:
            A merge proposal with parents 0 and 1, or None when scripted.
        """
        self.calls += 1
        text = self.script.pop(0)
        if text is None:
            return None
        return ProposalResult(
            candidate=Candidate(components={"instruction": text}),
            parent_indices=[0, 1],
            tag="merge",
        )


class FixedSelector:
    """Selector that always returns the same index.

    Attributes:
        index (int): The index returned on every draw.
        draws (int): Number of draws made.
    """

    def __init__(self, index: int) -> None:
        """Store the index.

        Args:
            index: The index to return.
        """
        self.index = index
        self.draws = 0

    async def select_candidate(self, state: ParetoState) -> int:
        """Return the fixed index.

        Args:
            state: Ignored.

        Returns:
            The fixed index.
        """
        self.draws += 1
        return self.index


class RecordingSelector:
    """Selector wrapper that records each draw and the cache at draw time.

    Attributes:
        cache (dict[int, Any]): The engine's batch cache, set after the
            engine is built.
        draws (list[int]): Indices returned, in order.
        uncached (list[list[int]]): Per draw, the candidate indices with no
            cached batch at the moment of the draw.
    """

    def __init__(self, inner: ParetoCandidateSelector) -> None:
        """Wrap a selector.

        Args:
            inner: The selector that makes the draws.
        """
        self._inner = inner
        self.cache: dict[int, Any] = {}
        self.draws: list[int] = []
        self.uncached: list[list[int]] = []

    async def select_candidate(self, state: ParetoState) -> int:
        """Record the uncached candidates, then draw from the inner selector.

        Args:
            state: The Pareto state to draw from.

        Returns:
            The drawn candidate index.
        """
        self.uncached.append(
            [i for i in range(len(state.candidates)) if i not in self.cache]
        )
        idx = await self._inner.select_candidate(state)
        self.draws.append(idx)
        return idx


def _adapter(
    proposals: list[str],
) -> tuple[ConfigurableMockAdapter, list[tuple[list[Any], str]]]:
    """Build a row-scoring mock adapter with scripted proposals.

    Args:
        proposals: Proposal texts returned in order.

    Returns:
        The adapter and the list recording each evaluate call's rows and
        instruction text.
    """
    calls: list[tuple[list[Any], str]] = []
    script = list(proposals)

    async def evaluate(
        batch: list[Any], candidate: dict[str, str], capture_traces: bool
    ) -> EvaluationBatch[Any, Any]:
        text = candidate["instruction"]
        calls.append((list(batch), text))
        scores = _ROWS[text][: len(batch)]
        return EvaluationBatch(
            outputs=[f"{text}:{row['input']}" for row in batch],
            scores=scores,
            trajectories=[{"text": text}] * len(batch) if capture_traces else None,
            objective_scores=[{"acc": s, "len": 1.0 - s} for s in scores],
        )

    async def propose(
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        return {"instruction": script.pop(0)}

    adapter = create_mock_adapter(custom_evaluate=evaluate, custom_propose=propose)
    return adapter, calls


def _engine(
    adapter: ConfigurableMockAdapter,
    selector: Any,
    merge_proposer: ScriptedMergeProposer | None,
    iterations: int,
    frontier_type: FrontierType = FrontierType.INSTANCE,
) -> AsyncGEPAEngine:
    """Build an engine with a selector and an optional merge proposer.

    Args:
        adapter: The mock adapter.
        selector: The candidate selector.
        merge_proposer: The merge proposer stub, or None to disable merges.
        iterations: Maximum iterations.
        frontier_type: The Pareto frontier type.

    Returns:
        The engine.
    """
    return AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=iterations,
            patience=10,
            min_improvement_threshold=0.0,
            use_merge=merge_proposer is not None,
            frontier_type=frontier_type,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=_BATCH,
        candidate_selector=selector,
        merge_proposer=merge_proposer,
    )


def _index_of(state: ParetoState, text: str) -> int:
    """Return the Pareto index of the candidate with this instruction.

    Args:
        state: The Pareto state.
        text: The instruction text.

    Returns:
        The candidate's index.
    """
    texts = [c.components["instruction"] for c in state.candidates]
    assert texts.count(text) == 1
    return texts.index(text)


class TestMergedCandidateIsCached:
    """A merged candidate's reflection batch is cached with full rows."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("frontier_type", list(FrontierType))
    async def test_merged_candidate_batch_and_rows_are_cached(
        self, frontier_type: FrontierType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Accepted and rejected merges both cache their own batch."""
        adapter, _ = _adapter(["p1", "p2", "p3"])
        merger = ScriptedMergeProposer(["m1", "m2", None])
        engine = _engine(adapter, FixedSelector(0), merger, 3, frontier_type)
        accepted: list[str] = []
        accept = engine._accept_proposal

        def record_accept(candidate: Candidate, *args: Any, **kwargs: Any) -> None:
            accepted.append(candidate.components["instruction"])
            accept(candidate, *args, **kwargs)

        monkeypatch.setattr(engine, "_accept_proposal", record_accept)

        result = await engine.run()

        state = engine._pareto_state
        assert state is not None
        assert merger.calls == 3
        assert engine._merge_invocations == 2
        assert engine._merges_due == 0
        assert result.total_iterations == 3
        assert [c.components["instruction"] for c in state.candidates] == [
            "seed",
            "p1",
            "m1",
            "p2",
            "m2",
            "p3",
        ]
        for text in ("m1", "m2"):
            merged_idx = _index_of(state, text)
            cached = engine._candidate_eval_batches[merged_idx]
            assert cached.scores == _ROWS[text]
            assert cached.outputs == [f"{text}:q1", f"{text}:q2", f"{text}:q3"]
            assert cached.trajectories == [{"text": text}] * 3
            assert engine._candidate_eval_rows[merged_idx] is None
            assert state.parent_indices[merged_idx] == [0, 1]
        # m1 was accepted before p2 beat it; m2 was rejected
        assert accepted == ["p1", "m1", "p2", "p3"]
        assert engine._state is not None
        assert engine._state.best_candidate.components["instruction"] == "p3"


class TestUncachedSelectionRaises:
    """A selector index with no cached batch is a configuration error."""

    @pytest.mark.asyncio
    async def test_negative_index_raises_without_full_trainset_evaluation(
        self,
    ) -> None:
        """Selecting -1 raises and evaluates nothing after the baseline."""
        adapter, calls = _adapter(["p1"])
        selector = FixedSelector(-1)
        engine = _engine(adapter, selector, None, 1)

        with pytest.raises(ConfigurationError, match="-1") as excinfo:
            await engine.run()

        assert selector.draws == 1
        assert excinfo.value.value == -1
        # Only the baseline evaluated the trainset
        assert calls == [(_BATCH, "seed")]


class TestEveryDrawIsCached:
    """Every index a selector can draw already has a cached batch."""

    @pytest.mark.asyncio
    async def test_every_candidate_is_cached_at_each_draw(self) -> None:
        """No candidate is ever uncached when the selector draws."""
        adapter, _ = _adapter(["p1", "p2", "p3"])
        merger = ScriptedMergeProposer(["m1", "m2", None])
        selector = RecordingSelector(ParetoCandidateSelector(rng=random.Random(7)))
        engine = _engine(adapter, selector, merger, 3)
        selector.cache = engine._candidate_eval_batches

        await engine.run()

        state = engine._pareto_state
        assert state is not None
        assert len(selector.draws) == 3
        # Candidates at each draw: seed; seed, p1, m1; then p2 and m2 added
        assert [len(u) for u in selector.uncached] == [0, 0, 0]
        assert selector.uncached == [[], [], []]
        assert all(idx in engine._candidate_eval_batches for idx in selector.draws)
        assert sorted(engine._candidate_eval_batches) == list(
            range(len(state.candidates))
        )

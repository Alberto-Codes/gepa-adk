"""Tests for seed-based determinism (Story 2.7).

Attributes:
    pytestmark: All tests in this module are unit tests.
"""

from __future__ import annotations

import random
from unittest.mock import patch

import pytest

from gepa_adk.adapters.selection.candidate_selector import ParetoCandidateSelector
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.domain.state import ParetoState
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from tests.fixtures.adapters import MockAdapter

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Task 5.2: EvolutionConfig seed field
# ---------------------------------------------------------------------------


class TestEvolutionConfigSeed:
    """Tests for the seed field on EvolutionConfig."""

    def test_seed_default_is_none(self) -> None:
        """Default seed is None (backward compatible)."""
        assert EvolutionConfig().seed is None

    def test_seed_accepts_integer(self) -> None:
        """Seed accepts an integer value."""
        assert EvolutionConfig(seed=42).seed == 42

    def test_seed_accepts_zero(self) -> None:
        """Seed=0 is a valid seed (distinct from None)."""
        config = EvolutionConfig(seed=0)
        assert config.seed == 0
        assert config.seed is not None

    def test_seed_zero_creates_rng_in_engine(self) -> None:
        """Seed=0 triggers RNG creation in engine (not treated as falsy None)."""
        rng = random.Random(0)
        engine = AsyncGEPAEngine(
            adapter=MockAdapter(),
            config=EvolutionConfig(seed=0),
            initial_candidate=Candidate(components={"instruction": "test"}),
            batch=[{"input": "hello"}],
            rng=rng,
        )
        assert engine._rng is not None
        assert engine._rng is rng


# ---------------------------------------------------------------------------
# Task 5.3: RNG wiring through engine constructor
# ---------------------------------------------------------------------------


class TestSeedRngWiring:
    """Tests for RNG propagation through the engine constructor."""

    def test_engine_stores_rng_when_provided(self) -> None:
        """Engine stores the provided RNG instance."""
        rng = random.Random(42)
        engine = AsyncGEPAEngine(
            adapter=MockAdapter(),
            config=EvolutionConfig(seed=42),
            initial_candidate=Candidate(components={"instruction": "test"}),
            batch=[{"input": "hello"}],
            rng=rng,
        )
        assert engine._rng is rng

    def test_engine_rng_is_none_when_not_provided(self) -> None:
        """Engine RNG is None when no seed/rng provided."""
        engine = AsyncGEPAEngine(
            adapter=MockAdapter(),
            config=EvolutionConfig(),
            initial_candidate=Candidate(components={"instruction": "test"}),
            batch=[{"input": "hello"}],
        )
        assert engine._rng is None

    def test_merge_proposer_auto_created_with_seed(self) -> None:
        """MergeProposer is auto-created when use_merge=True and seed provided."""
        rng = random.Random(42)
        engine = AsyncGEPAEngine(
            adapter=MockAdapter(),
            config=EvolutionConfig(use_merge=True, seed=42),
            initial_candidate=Candidate(components={"instruction": "test"}),
            batch=[{"input": "hello"}],
            rng=rng,
        )
        assert engine._merge_proposer is not None
        assert engine._merge_proposer.rng is rng

    def test_merge_proposer_auto_created_without_seed(self) -> None:
        """MergeProposer is auto-created when use_merge=True, even without seed."""
        engine = AsyncGEPAEngine(
            adapter=MockAdapter(),
            config=EvolutionConfig(use_merge=True),
            initial_candidate=Candidate(components={"instruction": "test"}),
            batch=[{"input": "hello"}],
        )
        assert engine._merge_proposer is not None
        assert isinstance(engine._merge_proposer.rng, random.Random)

    def test_merge_proposer_not_created_when_use_merge_false(self) -> None:
        """No MergeProposer when use_merge=False (default)."""
        engine = AsyncGEPAEngine(
            adapter=MockAdapter(),
            config=EvolutionConfig(),
            initial_candidate=Candidate(components={"instruction": "test"}),
            batch=[{"input": "hello"}],
        )
        assert engine._merge_proposer is None

    def test_user_provided_merge_proposer_preserved(self) -> None:
        """User-provided merge proposer is not overridden."""
        from gepa_adk.engine.merge_proposer import MergeProposer

        user_rng = random.Random(99)
        user_proposer = MergeProposer(rng=user_rng)
        engine = AsyncGEPAEngine(
            adapter=MockAdapter(),
            config=EvolutionConfig(use_merge=True, seed=42),
            initial_candidate=Candidate(components={"instruction": "test"}),
            batch=[{"input": "hello"}],
            merge_proposer=user_proposer,
            rng=random.Random(42),
        )
        assert engine._merge_proposer is user_proposer
        assert engine._merge_proposer.rng is user_rng


# ---------------------------------------------------------------------------
# Task 5.4: Deterministic decisions
# ---------------------------------------------------------------------------


class TestDeterministicDecisions:
    """Tests for deterministic behavior with seeded RNG."""

    @staticmethod
    def _build_pareto_state() -> ParetoState:
        """Build a ParetoState with multiple candidates for selection tests."""
        state = ParetoState()
        c0 = Candidate(components={"instruction": "a"}, generation=0)
        c1 = Candidate(components={"instruction": "b"}, generation=1)
        c2 = Candidate(components={"instruction": "c"}, generation=2)
        state.add_candidate(c0, [0.5, 0.6, 0.7])
        state.add_candidate(c1, [0.6, 0.5, 0.8])
        state.add_candidate(c2, [0.7, 0.8, 0.5])
        return state

    @pytest.mark.asyncio
    async def test_same_seed_produces_identical_candidate_selections(self) -> None:
        """Two selectors with same seed produce identical selection sequences."""
        state = self._build_pareto_state()

        selector1 = ParetoCandidateSelector(rng=random.Random(42))
        selector2 = ParetoCandidateSelector(rng=random.Random(42))

        selections1 = [await selector1.select_candidate(state) for _ in range(20)]
        selections2 = [await selector2.select_candidate(state) for _ in range(20)]

        assert selections1 == selections2

    @pytest.mark.asyncio
    async def test_different_seeds_produce_different_selections(self) -> None:
        """Two selectors with different seeds diverge in selections."""
        state = self._build_pareto_state()

        selector1 = ParetoCandidateSelector(rng=random.Random(42))
        selector2 = ParetoCandidateSelector(rng=random.Random(99))

        selections1 = [await selector1.select_candidate(state) for _ in range(20)]
        selections2 = [await selector2.select_candidate(state) for _ in range(20)]

        assert selections1 != selections2

    @pytest.mark.asyncio
    async def test_engine_run_determinism_with_mock_adapter(self) -> None:
        """Same seed produces identical evolutionary trajectories (AC7)."""
        # Use increasing scores so evolution accepts changes
        scores = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

        async def _run_with_seed(seed: int) -> list[float]:
            adapter = MockAdapter(scores=list(scores))
            config = EvolutionConfig(
                max_iterations=3,
                patience=0,
                seed=seed,
            )
            rng = random.Random(seed)
            engine = AsyncGEPAEngine(
                adapter=adapter,
                config=config,
                initial_candidate=Candidate(components={"instruction": "Be helpful"}),
                batch=[{"input": "hello"}],
                rng=rng,
            )
            result = await engine.run()
            return [r.score for r in result.iteration_history]

        run1 = await _run_with_seed(42)
        run2 = await _run_with_seed(42)

        assert run1 == run2
        assert len(run1) > 0


# ---------------------------------------------------------------------------
# Task 5.5: API seed wiring
# ---------------------------------------------------------------------------


class TestApiSeedWiring:
    """Tests for RNG wiring through the API layer."""

    def test_create_candidate_selector_receives_rng(self) -> None:
        """create_candidate_selector passes seeded RNG to the selector."""
        from gepa_adk.adapters.selection.candidate_selector import (
            create_candidate_selector,
        )

        rng = random.Random(42)
        selector = create_candidate_selector("pareto", rng=rng)
        assert isinstance(selector, ParetoCandidateSelector)
        assert selector._rng is rng

    def test_create_candidate_selector_no_rng_when_no_seed(self) -> None:
        """create_candidate_selector with rng=None uses default Random."""
        from gepa_adk.adapters.selection.candidate_selector import (
            create_candidate_selector,
        )

        selector = create_candidate_selector("pareto", rng=None)
        assert isinstance(selector, ParetoCandidateSelector)
        assert isinstance(selector._rng, random.Random)

    @pytest.mark.asyncio
    async def test_evolve_passes_seeded_rng_to_engine(self) -> None:
        """evolve() creates RNG from seed and passes it to engine constructor."""
        from unittest.mock import AsyncMock, MagicMock

        from gepa_adk.api import evolve

        mock_engine = AsyncMock()
        mock_engine.run.side_effect = RuntimeError("stop_after_engine_init")

        with (
            patch("gepa_adk.api._pre_flight_validate_evolve"),
            patch("gepa_adk.api.CriticScorer"),
            patch("gepa_adk.api.ADKAdapter"),
            patch("gepa_adk.api.create_adk_reflection_fn"),
            patch("gepa_adk.api.AsyncReflectiveMutationProposer"),
            patch("gepa_adk.api.AsyncGEPAEngine") as MockEngine,
        ):
            MockEngine.return_value = mock_engine
            mock_agent = MagicMock()
            mock_agent.name = "test"
            mock_agent.instruction = "test"

            with pytest.raises(RuntimeError, match="stop_after_engine_init"):
                await evolve(
                    mock_agent,
                    [{"input": "x"}],
                    critic=MagicMock(),
                    config=EvolutionConfig(seed=42),
                )

            rng = MockEngine.call_args.kwargs["rng"]
            assert isinstance(rng, random.Random)

    @pytest.mark.asyncio
    async def test_evolve_group_passes_seeded_rng_to_engine(self) -> None:
        """evolve_group() creates RNG from seed and passes it to engine."""
        from unittest.mock import AsyncMock, MagicMock

        from gepa_adk.api import evolve_group

        mock_engine = AsyncMock()
        mock_engine.run.side_effect = RuntimeError("stop_after_engine_init")

        mock_handler = MagicMock()
        mock_handler.serialize.return_value = "serialized"

        with (
            patch("gepa_adk.api._pre_flight_validate_group"),
            patch("gepa_adk.api.CriticScorer"),
            patch("gepa_adk.api.MultiAgentAdapter"),
            patch("gepa_adk.api.create_adk_reflection_fn"),
            patch("gepa_adk.api.AsyncReflectiveMutationProposer"),
            patch("gepa_adk.api.get_handler", return_value=mock_handler),
            patch("gepa_adk.api.AsyncGEPAEngine") as MockEngine,
        ):
            MockEngine.return_value = mock_engine
            mock_agent = MagicMock()
            mock_agent.name = "agent_a"
            mock_agent.instruction = "test"

            with pytest.raises(RuntimeError, match="stop_after_engine_init"):
                await evolve_group(
                    agents={"agent_a": mock_agent},
                    primary="agent_a",
                    trainset=[{"input": "x"}],
                    critic=MagicMock(),
                    config=EvolutionConfig(seed=42),
                )

            rng = MockEngine.call_args.kwargs["rng"]
            assert isinstance(rng, random.Random)

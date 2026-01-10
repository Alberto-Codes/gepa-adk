"""Unit tests for AsyncGEPAEngine."""

from typing import Any

import pytest

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine


class TestConstructor:
    """Test AsyncGEPAEngine constructor validation."""

    def test_valid_construction(
        self,
        mock_adapter: Any,
        sample_config: EvolutionConfig,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test that valid inputs create engine successfully."""
        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=sample_config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )
        assert engine.adapter is mock_adapter
        assert engine.config is sample_config
        assert engine._initial_candidate is sample_candidate
        assert engine._batch is sample_batch
        assert engine._state is None

    def test_empty_batch_raises_value_error(
        self,
        mock_adapter: Any,
        sample_config: EvolutionConfig,
        sample_candidate: Candidate,
    ) -> None:
        """Test that empty batch raises ValueError."""
        with pytest.raises(
            ValueError, match="batch must contain at least one data instance"
        ):
            AsyncGEPAEngine(
                adapter=mock_adapter,
                config=sample_config,
                initial_candidate=sample_candidate,
                batch=[],
            )

    def test_missing_instruction_raises_value_error(
        self,
        mock_adapter: Any,
        sample_config: EvolutionConfig,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test that candidate without instruction raises ValueError."""
        candidate = Candidate(components={}, generation=0)
        with pytest.raises(
            ValueError, match="initial_candidate must have 'instruction' component"
        ):
            AsyncGEPAEngine(
                adapter=mock_adapter,
                config=sample_config,
                initial_candidate=candidate,
                batch=sample_batch,
            )

    def test_invalid_config_raises_configuration_error(
        self,
        mock_adapter: Any,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test that invalid config raises ConfigurationError.

        Note: ConfigurationError is raised by EvolutionConfig's __post_init__
        validation, not by AsyncGEPAEngine constructor.
        """
        with pytest.raises(ConfigurationError):
            invalid_config = EvolutionConfig(max_iterations=-1)
            AsyncGEPAEngine(
                adapter=mock_adapter,
                config=invalid_config,
                initial_candidate=sample_candidate,
                batch=sample_batch,
            )


class TestUserStory1:
    """Test User Story 1: Run Evolution Loop (MVP)."""

    @pytest.mark.asyncio
    async def test_baseline_evaluation_max_iterations_zero(
        self,
        mock_adapter: Any,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test baseline evaluation when max_iterations=0 (SC-006)."""
        from tests.unit.engine.conftest import MockAdapter

        adapter = MockAdapter(scores=[0.75])
        config = EvolutionConfig(max_iterations=0)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        assert result.original_score == 0.75
        assert result.final_score == 0.75
        assert result.total_iterations == 0
        assert len(result.iteration_history) == 0
        assert result.evolved_instruction == sample_candidate.components["instruction"]

    @pytest.mark.asyncio
    async def test_basic_loop_execution(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test basic loop execution with max_iterations=5 (SC-002)."""
        from tests.unit.engine.conftest import MockAdapter

        # Scores: baseline 0.5, then 0.6, 0.7, 0.8, 0.9, 1.0
        adapter = MockAdapter(scores=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        config = EvolutionConfig(max_iterations=5)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        assert result.total_iterations == 5
        assert len(result.iteration_history) == 5
        assert result.original_score == 0.5
        # All proposals should be accepted (improving scores)
        assert all(record.accepted for record in result.iteration_history)

    @pytest.mark.asyncio
    async def test_iteration_history_completeness(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test iteration history completeness (SC-004)."""
        from tests.unit.engine.conftest import MockAdapter

        adapter = MockAdapter(scores=[0.5, 0.6, 0.7])
        config = EvolutionConfig(max_iterations=2)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        assert len(result.iteration_history) == 2
        assert result.iteration_history[0].iteration_number == 1
        assert result.iteration_history[1].iteration_number == 2
        assert all(record.score > 0 for record in result.iteration_history)
        assert all(record.instruction for record in result.iteration_history)
        assert all(
            isinstance(record.accepted, bool) for record in result.iteration_history
        )

    @pytest.mark.asyncio
    async def test_adapter_exception_propagation(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test that adapter exceptions propagate (fail-fast behavior)."""
        from tests.unit.engine.conftest import MockAdapter

        class FailingAdapter(MockAdapter):
            async def evaluate(self, batch, candidate, capture_traces=False):
                raise RuntimeError("Adapter failure")

        adapter = FailingAdapter()
        config = EvolutionConfig(max_iterations=5)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        with pytest.raises(RuntimeError, match="Adapter failure"):
            await engine.run()

    @pytest.mark.asyncio
    async def test_mean_score_aggregation(
        self,
        sample_candidate: Candidate,
    ) -> None:
        """Test mean score aggregation in _evaluate_candidate()."""
        from tests.unit.engine.conftest import MockAdapter

        # Create adapter that returns different scores per example
        class MultiScoreAdapter(MockAdapter):
            async def evaluate(self, batch, candidate, capture_traces=False):
                from gepa_adk.ports.adapter import EvaluationBatch

                # Return different scores for each example
                scores = [0.6, 0.8, 1.0]  # Mean = 0.8
                return EvaluationBatch(
                    outputs=[None] * len(batch),
                    scores=scores[: len(batch)],
                    trajectories=None,
                )

        adapter = MultiScoreAdapter()
        batch = [{"x": 1}, {"x": 2}, {"x": 3}]
        config = EvolutionConfig(max_iterations=0)  # Just baseline
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=batch,
        )

        result = await engine.run()

        # Mean of [0.6, 0.8, 1.0] = 0.8
        assert result.original_score == pytest.approx(0.8)
        assert result.final_score == pytest.approx(0.8)


class TestUserStory3:
    """Test User Story 3: Accept Improved Candidates."""

    @pytest.mark.asyncio
    async def test_accept_proposal_above_threshold(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test accepting proposal above threshold (SC-005)."""
        from tests.unit.engine.conftest import MockAdapter

        # Baseline: 0.5, Proposal: 0.6, Threshold: 0.05
        # 0.6 > 0.5 + 0.05 = 0.55, so should accept
        adapter = MockAdapter(scores=[0.5, 0.6])
        config = EvolutionConfig(
            max_iterations=1,
            min_improvement_threshold=0.05,
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        assert result.iteration_history[0].accepted is True
        assert result.final_score == 0.6

    @pytest.mark.asyncio
    async def test_reject_proposal_below_threshold(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test rejecting proposal below threshold."""
        from tests.unit.engine.conftest import MockAdapter

        # Baseline: 0.5, Proposal: 0.54, Threshold: 0.05
        # 0.54 > 0.5 + 0.05 = 0.55 is False, so should reject
        adapter = MockAdapter(scores=[0.5, 0.54])
        config = EvolutionConfig(
            max_iterations=1,
            min_improvement_threshold=0.05,
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        assert result.iteration_history[0].accepted is False
        assert result.final_score == 0.5  # Best score unchanged

    @pytest.mark.asyncio
    async def test_threshold_zero_accepts_any_improvement(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test threshold=0.0 accepts any improvement."""
        from tests.unit.engine.conftest import MockAdapter

        # Baseline: 0.5, Proposal: 0.501, Threshold: 0.0
        # 0.501 > 0.5 + 0.0 = 0.5, so should accept
        adapter = MockAdapter(scores=[0.5, 0.501])
        config = EvolutionConfig(
            max_iterations=1,
            min_improvement_threshold=0.0,
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        assert result.iteration_history[0].accepted is True
        assert result.final_score == 0.501

    @pytest.mark.asyncio
    async def test_candidate_lineage_tracking(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test candidate lineage tracking (generation, parent_id) (FR-012)."""
        from tests.unit.engine.conftest import MockAdapter

        # Scores: 0.5 (baseline), 0.6 (accept), 0.7 (accept)
        adapter = MockAdapter(scores=[0.5, 0.6, 0.7])
        config = EvolutionConfig(
            max_iterations=2,
            min_improvement_threshold=0.05,
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        # Check that final candidate has updated generation
        # Generation should be 2 (initial=0, accepted 2 proposals)
        assert result.evolved_instruction.startswith("Improved: Improved:")
        # The exact lineage structure is internal, but we verify
        # that proposals were accepted and instruction evolved
        assert len([r for r in result.iteration_history if r.accepted]) == 2


class TestUserStory2:
    """Test User Story 2: Early Stopping on Convergence."""

    @pytest.mark.asyncio
    async def test_early_stopping_when_patience_exhausted(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test early stopping when patience exhausted (SC-003)."""
        from tests.unit.engine.conftest import MockAdapter

        # Scores: 0.5 (baseline), then 0.5, 0.5, 0.5 (stagnant, all rejected)
        # Patience=3, so should stop after 3 rejections
        adapter = MockAdapter(scores=[0.5, 0.5, 0.5, 0.5, 0.5])
        config = EvolutionConfig(
            max_iterations=10,
            patience=3,
            min_improvement_threshold=0.01,
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        # Should stop early due to patience (3 rejections)
        assert result.total_iterations < 10
        assert result.total_iterations == 3  # 3 iterations without improvement
        assert result.final_score == 0.5  # No improvement

    @pytest.mark.asyncio
    async def test_patience_zero_disables_early_stop(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test patience=0 disables early stop (FR-007)."""
        from tests.unit.engine.conftest import MockAdapter

        # Scores: 0.5 (baseline), then all 0.5 (stagnant)
        # Patience=0 means no early stopping, should run to max_iterations
        adapter = MockAdapter(scores=[0.5] * 10)
        config = EvolutionConfig(
            max_iterations=5,
            patience=0,  # Disabled
            min_improvement_threshold=0.01,
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        # Should run to max_iterations despite no improvement
        assert result.total_iterations == 5
        assert result.final_score == 0.5

    @pytest.mark.asyncio
    async def test_patience_reset_on_improvement(
        self,
        sample_candidate: Candidate,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test patience reset on improvement."""
        from tests.unit.engine.conftest import MockAdapter

        # Scores: 0.5 (baseline), 0.5 (reject), 0.5 (reject), 0.6 (accept, reset),
        # 0.5 (reject), 0.5 (reject), 0.5 (reject)
        # Patience=3, should continue after acceptance
        adapter = MockAdapter(scores=[0.5, 0.5, 0.5, 0.6, 0.5, 0.5, 0.5, 0.5])
        config = EvolutionConfig(
            max_iterations=10,
            patience=3,
            min_improvement_threshold=0.05,
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=sample_candidate,
            batch=sample_batch,
        )

        result = await engine.run()

        # Should run more iterations because patience was reset after acceptance
        assert result.total_iterations >= 4  # At least through the acceptance
        # Should have at least one accepted iteration
        assert any(r.accepted for r in result.iteration_history)

"""Unit tests for domain models.

Tests for EvolutionConfig, EvolutionResult, Candidate, and IterationRecord.
Following TDD approach - tests written before implementation.
"""

import pytest

from gepa_adk.domain.exceptions import ConfigurationError


# =============================================================================
# User Story 1: EvolutionConfig Tests (T010-T012)
# =============================================================================


class TestEvolutionConfigDefaults:
    """Tests for EvolutionConfig default values (T010)."""

    def test_default_max_iterations(self) -> None:
        """EvolutionConfig has default max_iterations of 50."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.max_iterations == 50

    def test_default_max_concurrent_evals(self) -> None:
        """EvolutionConfig has default max_concurrent_evals of 5."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.max_concurrent_evals == 5

    def test_default_min_improvement_threshold(self) -> None:
        """EvolutionConfig has default min_improvement_threshold of 0.01."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.min_improvement_threshold == 0.01

    def test_default_patience(self) -> None:
        """EvolutionConfig has default patience of 5."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.patience == 5

    def test_default_reflection_model(self) -> None:
        """EvolutionConfig has default reflection_model of 'gemini-2.0-flash'."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.reflection_model == "gemini-2.0-flash"

    def test_all_defaults_together(self) -> None:
        """EvolutionConfig with all defaults creates valid instance."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.max_iterations == 50
        assert config.max_concurrent_evals == 5
        assert config.min_improvement_threshold == 0.01
        assert config.patience == 5
        assert config.reflection_model == "gemini-2.0-flash"


class TestEvolutionConfigCustomValues:
    """Tests for EvolutionConfig custom value preservation (T011)."""

    def test_custom_max_iterations(self) -> None:
        """EvolutionConfig preserves custom max_iterations."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(max_iterations=100)
        assert config.max_iterations == 100

    def test_custom_max_concurrent_evals(self) -> None:
        """EvolutionConfig preserves custom max_concurrent_evals."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(max_concurrent_evals=10)
        assert config.max_concurrent_evals == 10

    def test_custom_min_improvement_threshold(self) -> None:
        """EvolutionConfig preserves custom min_improvement_threshold."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(min_improvement_threshold=0.05)
        assert config.min_improvement_threshold == 0.05

    def test_custom_patience(self) -> None:
        """EvolutionConfig preserves custom patience."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(patience=10)
        assert config.patience == 10

    def test_custom_reflection_model(self) -> None:
        """EvolutionConfig preserves custom reflection_model."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(reflection_model="gpt-4o")
        assert config.reflection_model == "gpt-4o"

    def test_all_custom_values(self) -> None:
        """EvolutionConfig preserves all custom values together."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(
            max_iterations=200,
            max_concurrent_evals=20,
            min_improvement_threshold=0.001,
            patience=15,
            reflection_model="claude-3-opus",
        )
        assert config.max_iterations == 200
        assert config.max_concurrent_evals == 20
        assert config.min_improvement_threshold == 0.001
        assert config.patience == 15
        assert config.reflection_model == "claude-3-opus"

    def test_zero_max_iterations_allowed(self) -> None:
        """EvolutionConfig allows max_iterations=0 (just evaluate baseline)."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(max_iterations=0)
        assert config.max_iterations == 0

    def test_zero_patience_allowed(self) -> None:
        """EvolutionConfig allows patience=0 (never stop early)."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(patience=0)
        assert config.patience == 0

    def test_zero_min_improvement_threshold_allowed(self) -> None:
        """EvolutionConfig allows min_improvement_threshold=0.0."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(min_improvement_threshold=0.0)
        assert config.min_improvement_threshold == 0.0


class TestEvolutionConfigValidation:
    """Tests for EvolutionConfig validation (T012)."""

    def test_negative_max_iterations_raises_error(self) -> None:
        """EvolutionConfig raises ConfigurationError for negative max_iterations."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(max_iterations=-1)
        assert exc_info.value.field == "max_iterations"
        assert exc_info.value.value == -1

    def test_zero_max_concurrent_evals_raises_error(self) -> None:
        """EvolutionConfig raises ConfigurationError for zero max_concurrent_evals."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(max_concurrent_evals=0)
        assert exc_info.value.field == "max_concurrent_evals"
        assert exc_info.value.value == 0

    def test_negative_max_concurrent_evals_raises_error(self) -> None:
        """EvolutionConfig raises ConfigurationError for negative max_concurrent_evals."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(max_concurrent_evals=-5)
        assert exc_info.value.field == "max_concurrent_evals"

    def test_empty_reflection_model_raises_error(self) -> None:
        """EvolutionConfig raises ConfigurationError for empty reflection_model."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(reflection_model="")
        assert exc_info.value.field == "reflection_model"

    def test_negative_patience_raises_error(self) -> None:
        """EvolutionConfig raises ConfigurationError for negative patience."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(patience=-1)
        assert exc_info.value.field == "patience"

    def test_negative_min_improvement_threshold_raises_error(self) -> None:
        """EvolutionConfig raises ConfigurationError for negative threshold."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(min_improvement_threshold=-0.01)
        assert exc_info.value.field == "min_improvement_threshold"


class TestEvolutionConfigStructure:
    """Tests for EvolutionConfig dataclass structure."""

    def test_uses_slots(self) -> None:
        """EvolutionConfig uses slots for memory efficiency."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert hasattr(config, "__slots__")

    def test_is_mutable(self) -> None:
        """EvolutionConfig is mutable (not frozen)."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        config.max_iterations = 100
        assert config.max_iterations == 100


# =============================================================================
# User Story 4: IterationRecord Tests (T031-T032)
# Note: Implementing US4 first because US2 depends on IterationRecord
# =============================================================================


class TestIterationRecordFieldAccess:
    """Tests for IterationRecord field access (T031)."""

    def test_iteration_number_access(self) -> None:
        """IterationRecord stores iteration_number correctly."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.75,
            instruction="Test instruction",
            accepted=True,
        )
        assert record.iteration_number == 1

    def test_score_access(self) -> None:
        """IterationRecord stores score correctly."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            instruction="Test instruction",
            accepted=True,
        )
        assert record.score == 0.85

    def test_instruction_access(self) -> None:
        """IterationRecord stores instruction correctly."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.75,
            instruction="You are a helpful assistant",
            accepted=True,
        )
        assert record.instruction == "You are a helpful assistant"

    def test_accepted_access(self) -> None:
        """IterationRecord stores accepted flag correctly."""
        from gepa_adk.domain.models import IterationRecord

        record_accepted = IterationRecord(
            iteration_number=1,
            score=0.75,
            instruction="Test",
            accepted=True,
        )
        record_rejected = IterationRecord(
            iteration_number=2,
            score=0.70,
            instruction="Test",
            accepted=False,
        )
        assert record_accepted.accepted is True
        assert record_rejected.accepted is False

    def test_all_fields_together(self) -> None:
        """IterationRecord stores all fields correctly."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=5,
            score=0.92,
            instruction="Expert analyst instruction",
            accepted=True,
        )
        assert record.iteration_number == 5
        assert record.score == 0.92
        assert record.instruction == "Expert analyst instruction"
        assert record.accepted is True


class TestIterationRecordImmutability:
    """Tests for IterationRecord immutability (T032)."""

    def test_iteration_number_is_immutable(self) -> None:
        """IterationRecord iteration_number cannot be modified."""
        from dataclasses import FrozenInstanceError

        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.75,
            instruction="Test",
            accepted=True,
        )
        with pytest.raises(FrozenInstanceError):
            record.iteration_number = 2

    def test_score_is_immutable(self) -> None:
        """IterationRecord score cannot be modified."""
        from dataclasses import FrozenInstanceError

        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.75,
            instruction="Test",
            accepted=True,
        )
        with pytest.raises(FrozenInstanceError):
            record.score = 0.90

    def test_instruction_is_immutable(self) -> None:
        """IterationRecord instruction cannot be modified."""
        from dataclasses import FrozenInstanceError

        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.75,
            instruction="Test",
            accepted=True,
        )
        with pytest.raises(FrozenInstanceError):
            record.instruction = "Modified"

    def test_accepted_is_immutable(self) -> None:
        """IterationRecord accepted flag cannot be modified."""
        from dataclasses import FrozenInstanceError

        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.75,
            instruction="Test",
            accepted=True,
        )
        with pytest.raises(FrozenInstanceError):
            record.accepted = False

    def test_uses_slots(self) -> None:
        """IterationRecord uses slots for memory efficiency."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.75,
            instruction="Test",
            accepted=True,
        )
        assert hasattr(record, "__slots__")


# =============================================================================
# User Story 2: EvolutionResult Tests (T017-T019)
# =============================================================================


class TestEvolutionResultFieldAccess:
    """Tests for EvolutionResult field access (T017)."""

    def test_original_score_access(self) -> None:
        """EvolutionResult stores original_score correctly."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test instruction",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.original_score == 0.60

    def test_final_score_access(self) -> None:
        """EvolutionResult stores final_score correctly."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test instruction",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.final_score == 0.85

    def test_evolved_instruction_access(self) -> None:
        """EvolutionResult stores evolved_instruction correctly."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="You are an expert analyst",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.evolved_instruction == "You are an expert analyst"

    def test_iteration_history_access(self) -> None:
        """EvolutionResult stores iteration_history correctly."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        records = [
            IterationRecord(
                iteration_number=1,
                score=0.70,
                instruction="First",
                accepted=True,
            ),
            IterationRecord(
                iteration_number=2,
                score=0.85,
                instruction="Second",
                accepted=True,
            ),
        ]
        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Second",
            iteration_history=records,
            total_iterations=2,
        )
        assert len(result.iteration_history) == 2
        assert result.iteration_history[0].score == 0.70
        assert result.iteration_history[1].score == 0.85

    def test_total_iterations_access(self) -> None:
        """EvolutionResult stores total_iterations correctly."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=5,
        )
        assert result.total_iterations == 5


class TestEvolutionResultComputedProperties:
    """Tests for EvolutionResult computed properties (T018)."""

    def test_improvement_positive(self) -> None:
        """EvolutionResult.improvement returns positive difference."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.improvement == pytest.approx(0.25, rel=1e-9)

    def test_improvement_negative(self) -> None:
        """EvolutionResult.improvement returns negative difference when degraded."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.85,
            final_score=0.60,
            evolved_instruction="Test",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.60,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.improvement == pytest.approx(-0.25, rel=1e-9)

    def test_improvement_zero(self) -> None:
        """EvolutionResult.improvement returns zero when no change."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.75,
            final_score=0.75,
            evolved_instruction="Test",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.75,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.improvement == 0.0

    def test_improved_true(self) -> None:
        """EvolutionResult.improved returns True when score increased."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.improved is True

    def test_improved_false_when_degraded(self) -> None:
        """EvolutionResult.improved returns False when score decreased."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.85,
            final_score=0.60,
            evolved_instruction="Test",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.60,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.improved is False

    def test_improved_false_when_unchanged(self) -> None:
        """EvolutionResult.improved returns False when score unchanged."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.75,
            final_score=0.75,
            evolved_instruction="Test",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.75,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.improved is False


class TestEvolutionResultImmutability:
    """Tests for EvolutionResult immutability (T019)."""

    def test_original_score_is_immutable(self) -> None:
        """EvolutionResult original_score cannot be modified."""
        from dataclasses import FrozenInstanceError

        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        with pytest.raises(FrozenInstanceError):
            result.original_score = 0.50

    def test_final_score_is_immutable(self) -> None:
        """EvolutionResult final_score cannot be modified."""
        from dataclasses import FrozenInstanceError

        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        with pytest.raises(FrozenInstanceError):
            result.final_score = 0.90

    def test_evolved_instruction_is_immutable(self) -> None:
        """EvolutionResult evolved_instruction cannot be modified."""
        from dataclasses import FrozenInstanceError

        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        with pytest.raises(FrozenInstanceError):
            result.evolved_instruction = "Modified"

    def test_uses_slots(self) -> None:
        """EvolutionResult uses slots for memory efficiency."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    instruction="Test",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert hasattr(result, "__slots__")


# =============================================================================
# User Story 3: Candidate Tests (T024-T026)
# =============================================================================


class TestCandidateComponentAccess:
    """Tests for Candidate component access (T024)."""

    def test_components_access(self) -> None:
        """Candidate stores components correctly."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={"instruction": "You are a helpful assistant"})
        assert candidate.components["instruction"] == "You are a helpful assistant"

    def test_components_modification(self) -> None:
        """Candidate components can be modified."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={"instruction": "Original"})
        candidate.components["instruction"] = "Modified"
        assert candidate.components["instruction"] == "Modified"

    def test_components_add_new_key(self) -> None:
        """Candidate components can have new keys added."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={"instruction": "Test"})
        candidate.components["output_schema"] = '{"type": "object"}'
        assert "output_schema" in candidate.components
        assert candidate.components["output_schema"] == '{"type": "object"}'

    def test_components_list_keys(self) -> None:
        """Candidate components keys can be listed."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(
            components={
                "instruction": "Test",
                "output_schema": "{}",
            }
        )
        keys = list(candidate.components.keys())
        assert "instruction" in keys
        assert "output_schema" in keys


class TestCandidateLineageFields:
    """Tests for Candidate lineage fields (T025)."""

    def test_generation_default(self) -> None:
        """Candidate has default generation of 0."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={})
        assert candidate.generation == 0

    def test_generation_custom(self) -> None:
        """Candidate preserves custom generation."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={}, generation=5)
        assert candidate.generation == 5

    def test_parent_id_default(self) -> None:
        """Candidate has default parent_id of None."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={})
        assert candidate.parent_id is None

    def test_parent_id_custom(self) -> None:
        """Candidate preserves custom parent_id."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={}, parent_id="parent-uuid-12345")
        assert candidate.parent_id == "parent-uuid-12345"

    def test_metadata_default(self) -> None:
        """Candidate has default empty metadata dict."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={})
        assert candidate.metadata == {}
        assert isinstance(candidate.metadata, dict)

    def test_metadata_custom(self) -> None:
        """Candidate preserves custom metadata."""
        from gepa_adk.domain.models import Candidate

        metadata = {"mutation_type": "reflective", "score": 0.85}
        candidate = Candidate(components={}, metadata=metadata)
        assert candidate.metadata["mutation_type"] == "reflective"
        assert candidate.metadata["score"] == 0.85

    def test_lineage_full_example(self) -> None:
        """Candidate tracks full lineage correctly."""
        from gepa_adk.domain.models import Candidate

        child = Candidate(
            components={"instruction": "Expert analyst"},
            generation=3,
            parent_id="gen2-uuid",
            metadata={"mutation_type": "reflective"},
        )
        assert child.generation == 3
        assert child.parent_id == "gen2-uuid"
        assert child.metadata["mutation_type"] == "reflective"


class TestCandidateMutableDefaults:
    """Tests for Candidate mutable defaults (T026)."""

    def test_components_default_factory(self) -> None:
        """Candidate components uses default_factory (empty dict)."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate()
        assert candidate.components == {}
        assert isinstance(candidate.components, dict)

    def test_components_not_shared_between_instances(self) -> None:
        """Candidate components dict is not shared between instances."""
        from gepa_adk.domain.models import Candidate

        candidate1 = Candidate()
        candidate2 = Candidate()
        candidate1.components["instruction"] = "Test"
        assert "instruction" not in candidate2.components

    def test_metadata_default_factory(self) -> None:
        """Candidate metadata uses default_factory (empty dict)."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate()
        assert candidate.metadata == {}
        assert isinstance(candidate.metadata, dict)

    def test_metadata_not_shared_between_instances(self) -> None:
        """Candidate metadata dict is not shared between instances."""
        from gepa_adk.domain.models import Candidate

        candidate1 = Candidate()
        candidate2 = Candidate()
        candidate1.metadata["key"] = "value"
        assert "key" not in candidate2.metadata

    def test_uses_slots(self) -> None:
        """Candidate uses slots for memory efficiency."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate()
        assert hasattr(candidate, "__slots__")

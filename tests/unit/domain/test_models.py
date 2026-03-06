"""Unit tests for domain models.

Tests for EvolutionConfig, EvolutionResult, Candidate, IterationRecord,
and MultiAgentEvolutionResult.
Following TDD approach - tests written before implementation.
"""

import pytest

from gepa_adk.domain.exceptions import ConfigurationError

pytestmark = pytest.mark.unit

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
        """EvolutionConfig has default reflection_model of 'ollama_chat/gpt-oss:20b'."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.reflection_model == "ollama_chat/gpt-oss:20b"

    def test_all_defaults_together(self) -> None:
        """EvolutionConfig with all defaults creates valid instance."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.max_iterations == 50
        assert config.max_concurrent_evals == 5
        assert config.min_improvement_threshold == 0.01
        assert config.patience == 5
        assert config.reflection_model == "ollama_chat/gpt-oss:20b"


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
            component_text="Test instruction",
            evolved_component="instruction",
            accepted=True,
        )
        assert record.iteration_number == 1

    def test_score_access(self) -> None:
        """IterationRecord stores score correctly."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Test instruction",
            evolved_component="instruction",
            accepted=True,
        )
        assert record.score == 0.85

    def test_instruction_access(self) -> None:
        """IterationRecord stores instruction correctly."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.75,
            component_text="You are a helpful assistant",
            evolved_component="instruction",
            accepted=True,
        )
        assert record.component_text == "You are a helpful assistant"

    def test_accepted_access(self) -> None:
        """IterationRecord stores accepted flag correctly."""
        from gepa_adk.domain.models import IterationRecord

        record_accepted = IterationRecord(
            iteration_number=1,
            score=0.75,
            component_text="Test",
            evolved_component="instruction",
            accepted=True,
        )
        record_rejected = IterationRecord(
            iteration_number=2,
            score=0.70,
            component_text="Test",
            evolved_component="instruction",
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
            component_text="Expert analyst instruction",
            evolved_component="instruction",
            accepted=True,
        )
        assert record.iteration_number == 5
        assert record.score == 0.92
        assert record.component_text == "Expert analyst instruction"
        assert record.accepted is True


class TestIterationRecordImmutability:
    """Tests for IterationRecord immutability (T032)."""

    def test_iteration_number_is_immutable(self, make_iteration_record) -> None:
        """IterationRecord iteration_number cannot be modified."""
        from dataclasses import FrozenInstanceError

        record = make_iteration_record()
        with pytest.raises(FrozenInstanceError):
            record.iteration_number = 2  # ty: ignore[invalid-assignment]

    def test_score_is_immutable(self, make_iteration_record) -> None:
        """IterationRecord score cannot be modified."""
        from dataclasses import FrozenInstanceError

        record = make_iteration_record()
        with pytest.raises(FrozenInstanceError):
            record.score = 0.90  # ty: ignore[invalid-assignment]

    def test_instruction_is_immutable(self, make_iteration_record) -> None:
        """IterationRecord instruction cannot be modified."""
        from dataclasses import FrozenInstanceError

        record = make_iteration_record()
        with pytest.raises(FrozenInstanceError):
            record.component_text = "Modified"  # ty: ignore[invalid-assignment]

    def test_accepted_is_immutable(self, make_iteration_record) -> None:
        """IterationRecord accepted flag cannot be modified."""
        from dataclasses import FrozenInstanceError

        record = make_iteration_record()
        with pytest.raises(FrozenInstanceError):
            record.accepted = False  # ty: ignore[invalid-assignment]

    def test_uses_slots(self, make_iteration_record) -> None:
        """IterationRecord uses slots for memory efficiency."""
        record = make_iteration_record()
        assert hasattr(record, "__slots__")


# =============================================================================
# User Story 2: EvolutionResult Tests (T017-T019)
# =============================================================================


class TestEvolutionResultFieldAccess:
    """Tests for EvolutionResult field access (T017)."""

    def test_original_score_access(self, make_evolution_result) -> None:
        """EvolutionResult stores original_score correctly."""
        result = make_evolution_result(original_score=0.60)
        assert result.original_score == 0.60
        assert result.schema_version == 1

    def test_final_score_access(self) -> None:
        """EvolutionResult stores final_score correctly."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_components={"instruction": "Test instruction"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    component_text="Test",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.final_score == 0.85

    def test_evolved_components_access(self) -> None:
        """EvolutionResult stores evolved_components correctly."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_components={"instruction": "You are an expert analyst"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    component_text="Test",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.evolved_components["instruction"] == "You are an expert analyst"

    def test_iteration_history_access(self) -> None:
        """EvolutionResult stores iteration_history correctly."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        records = [
            IterationRecord(
                iteration_number=1,
                score=0.70,
                component_text="First",
                evolved_component="instruction",
                accepted=True,
            ),
            IterationRecord(
                iteration_number=2,
                score=0.85,
                component_text="Second",
                evolved_component="instruction",
                accepted=True,
            ),
        ]
        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_components={"instruction": "Second"},
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
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    component_text="Test",
                    evolved_component="instruction",
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
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    component_text="Test",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.improvement == pytest.approx(0.25, rel=1e-9)
        assert result.schema_version == 1

    def test_improvement_negative(self) -> None:
        """EvolutionResult.improvement returns negative difference when degraded."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.85,
            final_score=0.60,
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.60,
                    component_text="Test",
                    evolved_component="instruction",
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
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.75,
                    component_text="Test",
                    evolved_component="instruction",
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
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    component_text="Test",
                    evolved_component="instruction",
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
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.60,
                    component_text="Test",
                    evolved_component="instruction",
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
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.75,
                    component_text="Test",
                    evolved_component="instruction",
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
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    component_text="Test",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        with pytest.raises(FrozenInstanceError):
            result.original_score = 0.50  # ty: ignore[invalid-assignment]

    def test_final_score_is_immutable(self) -> None:
        """EvolutionResult final_score cannot be modified."""
        from dataclasses import FrozenInstanceError

        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    component_text="Test",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        with pytest.raises(FrozenInstanceError):
            result.final_score = 0.90  # ty: ignore[invalid-assignment]

    def test_evolved_components_is_immutable(self) -> None:
        """EvolutionResult evolved_components cannot be reassigned."""
        from dataclasses import FrozenInstanceError

        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    component_text="Test",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        with pytest.raises(FrozenInstanceError):
            result.evolved_components = {}  # ty: ignore[invalid-assignment]

    def test_uses_slots(self) -> None:
        """EvolutionResult uses slots for memory efficiency."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    component_text="Test",
                    evolved_component="instruction",
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


# =============================================================================
# User Story 3: MultiAgentEvolutionResult Tests (T018)
# =============================================================================


class TestMultiAgentEvolutionResultComputedProperties:
    """Tests for MultiAgentEvolutionResult computed properties (T018)."""

    def test_improvement_positive(self) -> None:
        """MultiAgentEvolutionResult.improvement returns positive difference."""
        from gepa_adk.domain.models import (
            IterationRecord,
            MultiAgentEvolutionResult,
        )

        result = MultiAgentEvolutionResult(
            evolved_components={
                "generator": "Generate code",
                "critic": "Review code",
            },
            original_score=0.60,
            final_score=0.85,
            primary_agent="generator",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.85,
                    component_text="generator_instruction",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        assert result.improvement == pytest.approx(0.25, rel=1e-9)
        assert result.schema_version == 1

    def test_improvement_negative(self) -> None:
        """MultiAgentEvolutionResult.improvement returns negative when degraded."""
        from gepa_adk.domain.models import (
            MultiAgentEvolutionResult,
        )

        result = MultiAgentEvolutionResult(
            evolved_components={"generator": "Generate code"},
            original_score=0.80,
            final_score=0.60,
            primary_agent="generator",
            iteration_history=[],
            total_iterations=0,
        )
        assert result.improvement == pytest.approx(-0.20, rel=1e-9)

    def test_improvement_zero(self) -> None:
        """MultiAgentEvolutionResult.improvement returns zero when unchanged."""
        from gepa_adk.domain.models import (
            MultiAgentEvolutionResult,
        )

        result = MultiAgentEvolutionResult(
            evolved_components={"generator": "Generate code"},
            original_score=0.75,
            final_score=0.75,
            primary_agent="generator",
            iteration_history=[],
            total_iterations=0,
        )
        assert result.improvement == pytest.approx(0.0, rel=1e-9)

    def test_improved_true(self) -> None:
        """MultiAgentEvolutionResult.improved returns True when final > original."""
        from gepa_adk.domain.models import (
            MultiAgentEvolutionResult,
        )

        result = MultiAgentEvolutionResult(
            evolved_components={"generator": "Generate code"},
            original_score=0.60,
            final_score=0.85,
            primary_agent="generator",
            iteration_history=[],
            total_iterations=0,
        )
        assert result.improved is True

    def test_improved_false_when_degraded(self) -> None:
        """MultiAgentEvolutionResult.improved returns False when degraded."""
        from gepa_adk.domain.models import (
            MultiAgentEvolutionResult,
        )

        result = MultiAgentEvolutionResult(
            evolved_components={"generator": "Generate code"},
            original_score=0.80,
            final_score=0.60,
            primary_agent="generator",
            iteration_history=[],
            total_iterations=0,
        )
        assert result.improved is False

    def test_improved_false_when_equal(self) -> None:
        """MultiAgentEvolutionResult.improved returns False when scores equal."""
        from gepa_adk.domain.models import (
            MultiAgentEvolutionResult,
        )

        result = MultiAgentEvolutionResult(
            evolved_components={"generator": "Generate code"},
            original_score=0.75,
            final_score=0.75,
            primary_agent="generator",
            iteration_history=[],
            total_iterations=0,
        )
        assert result.improved is False

    def test_agent_names_sorted(self) -> None:
        """MultiAgentEvolutionResult.agent_names returns sorted list."""
        from gepa_adk.domain.models import (
            MultiAgentEvolutionResult,
        )

        result = MultiAgentEvolutionResult(
            evolved_components={
                "critic": "Review code",
                "generator": "Generate code",
                "validator": "Validate code",
            },
            original_score=0.60,
            final_score=0.85,
            primary_agent="generator",
            iteration_history=[],
            total_iterations=0,
        )
        assert result.agent_names == ["critic", "generator", "validator"]

    def test_agent_names_single_agent(self) -> None:
        """MultiAgentEvolutionResult.agent_names works with single agent."""
        from gepa_adk.domain.models import (
            MultiAgentEvolutionResult,
        )

        result = MultiAgentEvolutionResult(
            evolved_components={"generator": "Generate code"},
            original_score=0.60,
            final_score=0.85,
            primary_agent="generator",
            iteration_history=[],
            total_iterations=0,
        )
        assert result.agent_names == ["generator"]

    def test_agent_names_empty(self) -> None:
        """MultiAgentEvolutionResult.agent_names returns empty list when no agents."""
        from gepa_adk.domain.models import (
            MultiAgentEvolutionResult,
        )

        result = MultiAgentEvolutionResult(
            evolved_components={},
            original_score=0.60,
            final_score=0.85,
            primary_agent="generator",
            iteration_history=[],
            total_iterations=0,
        )
        assert result.agent_names == []


class TestStopReasonEnum:
    """Tests for StopReason enum values and str subclass."""

    def test_all_six_values_exist(self) -> None:
        """StopReason has exactly 6 members."""
        from gepa_adk.domain.types import StopReason

        assert len(StopReason) == 6

    def test_string_values(self) -> None:
        """StopReason values are the expected lowercase strings."""
        from gepa_adk.domain.types import StopReason

        expected = {
            "COMPLETED": "completed",
            "MAX_ITERATIONS": "max_iterations",
            "STOPPER_TRIGGERED": "stopper_triggered",
            "KEYBOARD_INTERRUPT": "keyboard_interrupt",
            "TIMEOUT": "timeout",
            "CANCELLED": "cancelled",
        }
        for name, value in expected.items():
            assert StopReason[name].value == value

    def test_str_subclass(self) -> None:
        """StopReason is a str subclass, enabling JSON serialization."""
        from gepa_adk.domain.types import StopReason

        for member in StopReason:
            assert isinstance(member, str)

    def test_enum_membership_by_value(self) -> None:
        """StopReason can be constructed from string value."""
        from gepa_adk.domain.types import StopReason

        assert StopReason("completed") == StopReason.COMPLETED
        assert StopReason("max_iterations") == StopReason.MAX_ITERATIONS
        assert StopReason("stopper_triggered") == StopReason.STOPPER_TRIGGERED


class TestEvolutionResultStopReason:
    """Tests for stop_reason and schema_version on result types."""

    def test_default_stop_reason_is_completed(self) -> None:
        """EvolutionResult defaults stop_reason to COMPLETED."""
        from gepa_adk.domain.models import EvolutionResult
        from gepa_adk.domain.types import StopReason

        result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Test"},
            iteration_history=[],
            total_iterations=3,
        )
        assert result.stop_reason == StopReason.COMPLETED

    def test_explicit_stop_reason(self) -> None:
        """EvolutionResult accepts explicit stop_reason."""
        from gepa_adk.domain.models import EvolutionResult
        from gepa_adk.domain.types import StopReason

        result = EvolutionResult(
            stop_reason=StopReason.MAX_ITERATIONS,
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Test"},
            iteration_history=[],
            total_iterations=3,
        )
        assert result.stop_reason == StopReason.MAX_ITERATIONS

    def test_stop_reason_accessible_on_frozen(self) -> None:
        """stop_reason is accessible on a frozen dataclass instance."""
        from gepa_adk.domain.models import EvolutionResult
        from gepa_adk.domain.types import StopReason

        result = EvolutionResult(
            stop_reason=StopReason.STOPPER_TRIGGERED,
            original_score=0.5,
            final_score=0.6,
            evolved_components={},
            iteration_history=[],
            total_iterations=1,
        )
        assert result.stop_reason is StopReason.STOPPER_TRIGGERED

    def test_multi_agent_default_stop_reason(self) -> None:
        """MultiAgentEvolutionResult defaults stop_reason to COMPLETED."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult
        from gepa_adk.domain.types import StopReason

        result = MultiAgentEvolutionResult(
            evolved_components={"agent.instruction": "Test"},
            original_score=0.5,
            final_score=0.8,
            primary_agent="agent",
            iteration_history=[],
            total_iterations=3,
        )
        assert result.stop_reason == StopReason.COMPLETED
        assert result.schema_version == 1

    def test_multi_agent_explicit_stop_reason(self) -> None:
        """MultiAgentEvolutionResult accepts explicit stop_reason."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult
        from gepa_adk.domain.types import StopReason

        result = MultiAgentEvolutionResult(
            stop_reason=StopReason.STOPPER_TRIGGERED,
            evolved_components={"agent.instruction": "Test"},
            original_score=0.5,
            final_score=0.8,
            primary_agent="agent",
            iteration_history=[],
            total_iterations=3,
        )
        assert result.stop_reason == StopReason.STOPPER_TRIGGERED


# =============================================================================
# Serialization Tests (Story 2.2)
# =============================================================================


class TestIterationRecordSerialization:
    """Tests for IterationRecord to_dict/from_dict serialization."""

    def test_to_dict_all_fields(self) -> None:
        """to_dict produces dict with all 7 fields."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
            objective_scores=[{"clarity": 0.9}],
        )
        d = record.to_dict()
        assert set(d.keys()) == {
            "iteration_number",
            "score",
            "component_text",
            "evolved_component",
            "accepted",
            "objective_scores",
            "reflection_reasoning",
        }
        assert d["iteration_number"] == 1
        assert d["score"] == 0.85
        assert d["component_text"] == "Be helpful"
        assert d["evolved_component"] == "instruction"
        assert d["accepted"] is True

    def test_to_dict_with_objective_scores(self) -> None:
        """Non-None objective_scores are serialized correctly."""
        from gepa_adk.domain.models import IterationRecord

        scores = [{"clarity": 0.9, "relevance": 0.8}]
        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
            objective_scores=scores,
        )
        d = record.to_dict()
        assert d["objective_scores"] == scores

    def test_to_dict_without_objective_scores(self) -> None:
        """None objective_scores produces None in dict."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
        )
        d = record.to_dict()
        assert d["objective_scores"] is None

    def test_from_dict_round_trip(self) -> None:
        """from_dict(record.to_dict()) matches original."""
        from gepa_adk.domain.models import IterationRecord

        original = IterationRecord(
            iteration_number=3,
            score=0.72,
            component_text="Test text",
            evolved_component="instruction",
            accepted=False,
            objective_scores=[{"a": 1.0}],
        )
        restored = IterationRecord.from_dict(original.to_dict())
        assert restored.iteration_number == original.iteration_number
        assert restored.score == original.score
        assert restored.component_text == original.component_text
        assert restored.evolved_component == original.evolved_component
        assert restored.accepted == original.accepted
        assert restored.objective_scores == original.objective_scores

    def test_from_dict_ignores_unknown_keys(self) -> None:
        """Extra keys in dict are silently ignored."""
        from gepa_adk.domain.models import IterationRecord

        data = {
            "iteration_number": 1,
            "score": 0.5,
            "component_text": "Test",
            "evolved_component": "instruction",
            "accepted": True,
            "objective_scores": None,
            "future_field": "should be ignored",
            "another_unknown": 42,
        }
        record = IterationRecord.from_dict(data)
        assert record.iteration_number == 1
        assert record.score == 0.5


class TestIterationRecordReflectionReasoning:
    """Tests for IterationRecord.reflection_reasoning field."""

    def test_reflection_reasoning_defaults_to_none(self) -> None:
        """reflection_reasoning defaults to None for backward compatibility."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
        )
        assert record.reflection_reasoning is None

    def test_reflection_reasoning_stores_string(self) -> None:
        """reflection_reasoning stores the provided reasoning string."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
            reflection_reasoning="The instruction lacks specificity",
        )
        assert record.reflection_reasoning == "The instruction lacks specificity"

    def test_to_dict_includes_reflection_reasoning(self) -> None:
        """to_dict includes reflection_reasoning in output."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
            reflection_reasoning="Added constraints for clarity",
        )
        d = record.to_dict()
        assert d["reflection_reasoning"] == "Added constraints for clarity"

    def test_to_dict_includes_none_reasoning(self) -> None:
        """to_dict includes None when reasoning is not set."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
        )
        d = record.to_dict()
        assert d["reflection_reasoning"] is None

    def test_from_dict_round_trip_preserves_reasoning(self) -> None:
        """from_dict(to_dict()) preserves reflection_reasoning."""
        from gepa_adk.domain.models import IterationRecord

        original = IterationRecord(
            iteration_number=2,
            score=0.90,
            component_text="Be concise",
            evolved_component="instruction",
            accepted=True,
            reflection_reasoning="Shortened the instruction for clarity",
        )
        restored = IterationRecord.from_dict(original.to_dict())
        assert restored.reflection_reasoning == original.reflection_reasoning

    def test_from_dict_missing_key_defaults_to_none(self) -> None:
        """from_dict with missing reflection_reasoning key defaults to None."""
        from gepa_adk.domain.models import IterationRecord

        data = {
            "iteration_number": 1,
            "score": 0.5,
            "component_text": "Test",
            "evolved_component": "instruction",
            "accepted": True,
            "objective_scores": None,
        }
        record = IterationRecord.from_dict(data)
        assert record.reflection_reasoning is None


class TestEvolutionResultReflectionReasoning:
    """Tests for EvolutionResult.reflection_reasoning property."""

    def test_reflection_reasoning_returns_last_iteration_reasoning(self) -> None:
        """reflection_reasoning returns the last iteration's reasoning."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Be helpful"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="v1",
                    evolved_component="instruction",
                    accepted=True,
                    reflection_reasoning="First reasoning",
                ),
                IterationRecord(
                    iteration_number=2,
                    score=0.8,
                    component_text="v2",
                    evolved_component="instruction",
                    accepted=True,
                    reflection_reasoning="Second reasoning",
                ),
            ],
            total_iterations=2,
        )
        assert result.reflection_reasoning == "Second reasoning"

    def test_reflection_reasoning_returns_none_for_empty_history(self) -> None:
        """reflection_reasoning returns None when iteration_history is empty."""
        from gepa_adk.domain.models import EvolutionResult

        result = EvolutionResult(
            original_score=0.5,
            final_score=0.5,
            evolved_components={"instruction": "Be helpful"},
            iteration_history=[],
            total_iterations=0,
        )
        assert result.reflection_reasoning is None

    def test_to_dict_from_dict_round_trip_preserves_reasoning(self) -> None:
        """Serialization round-trip preserves reasoning in iteration records."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        original = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Be helpful"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.8,
                    component_text="v1",
                    evolved_component="instruction",
                    accepted=True,
                    reflection_reasoning="The instruction was too vague",
                ),
            ],
            total_iterations=1,
        )
        restored = EvolutionResult.from_dict(original.to_dict())
        assert (
            restored.iteration_history[0].reflection_reasoning
            == "The instruction was too vague"
        )
        assert restored.reflection_reasoning == "The instruction was too vague"


class TestEvolutionResultSerialization:
    """Tests for EvolutionResult to_dict/from_dict serialization."""

    def test_to_dict_all_fields(self) -> None:
        """to_dict produces dict with all 10 fields, stop_reason as string."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord
        from gepa_adk.domain.types import StopReason

        result = EvolutionResult(
            stop_reason=StopReason.MAX_ITERATIONS,
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.8,
                    component_text="Test",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
            valset_score=0.75,
            trainset_score=0.70,
            objective_scores=[{"x": 1.0}],
        )
        d = result.to_dict()
        assert set(d.keys()) == {
            "schema_version",
            "stop_reason",
            "original_score",
            "final_score",
            "evolved_components",
            "iteration_history",
            "total_iterations",
            "valset_score",
            "trainset_score",
            "objective_scores",
            "original_components",
        }
        assert d["stop_reason"] == "max_iterations"
        assert d["schema_version"] == 1

    def test_to_dict_iteration_history_nested(self) -> None:
        """Iteration records are serialized as dicts, not objects."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.8,
                    component_text="Test",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        d = result.to_dict()
        assert isinstance(d["iteration_history"], list)
        assert isinstance(d["iteration_history"][0], dict)
        assert d["iteration_history"][0]["iteration_number"] == 1

    def test_from_dict_round_trip_complete(self) -> None:
        """Full result with all fields round-trips correctly."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord
        from gepa_adk.domain.types import StopReason

        original = EvolutionResult(
            stop_reason=StopReason.STOPPER_TRIGGERED,
            original_score=0.45,
            final_score=0.82,
            evolved_components={"instruction": "Be helpful"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="Be helpful",
                    evolved_component="instruction",
                    accepted=True,
                    objective_scores=[{"clarity": 0.9}],
                ),
            ],
            total_iterations=1,
            valset_score=0.80,
            trainset_score=0.75,
            objective_scores=[{"clarity": 0.9}],
        )
        restored = EvolutionResult.from_dict(original.to_dict())
        assert restored.schema_version == original.schema_version
        assert restored.stop_reason == original.stop_reason
        assert restored.original_score == original.original_score
        assert restored.final_score == original.final_score
        assert restored.evolved_components == original.evolved_components
        assert restored.total_iterations == original.total_iterations
        assert restored.valset_score == original.valset_score
        assert restored.trainset_score == original.trainset_score
        assert restored.objective_scores == original.objective_scores
        assert len(restored.iteration_history) == 1
        assert restored.iteration_history[0].score == 0.6

    def test_from_dict_round_trip_minimal(self) -> None:
        """Result with all optional fields as None round-trips."""
        from gepa_adk.domain.models import EvolutionResult

        original = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Test"},
            iteration_history=[],
            total_iterations=0,
        )
        restored = EvolutionResult.from_dict(original.to_dict())
        assert restored.valset_score is None
        assert restored.trainset_score is None
        assert restored.objective_scores is None
        assert restored.iteration_history == []

    def test_from_dict_every_stop_reason(self) -> None:
        """Round-trip works for each of the 6 StopReason values."""
        from gepa_adk.domain.models import EvolutionResult
        from gepa_adk.domain.types import StopReason

        for reason in StopReason:
            original = EvolutionResult(
                stop_reason=reason,
                original_score=0.5,
                final_score=0.8,
                evolved_components={"instruction": "Test"},
                iteration_history=[],
                total_iterations=0,
            )
            restored = EvolutionResult.from_dict(original.to_dict())
            assert restored.stop_reason == reason

    def test_from_dict_default_stop_reason(self) -> None:
        """Missing stop_reason key defaults to COMPLETED."""
        from gepa_adk.domain.models import EvolutionResult
        from gepa_adk.domain.types import StopReason

        data = {
            "schema_version": 1,
            "original_score": 0.5,
            "final_score": 0.8,
            "evolved_components": {"instruction": "Test"},
            "iteration_history": [],
            "total_iterations": 0,
        }
        result = EvolutionResult.from_dict(data)
        assert result.stop_reason == StopReason.COMPLETED

    def test_from_dict_default_schema_version(self) -> None:
        """Missing schema_version key defaults to 1."""
        from gepa_adk.domain.models import EvolutionResult

        data = {
            "original_score": 0.5,
            "final_score": 0.8,
            "evolved_components": {"instruction": "Test"},
            "iteration_history": [],
            "total_iterations": 0,
        }
        result = EvolutionResult.from_dict(data)
        assert result.schema_version == 1

    def test_from_dict_future_schema_version_raises(self) -> None:
        """schema_version 999 raises ConfigurationError."""
        from gepa_adk.domain.models import EvolutionResult

        data = {
            "schema_version": 999,
            "original_score": 0.5,
            "final_score": 0.8,
            "evolved_components": {"instruction": "Test"},
            "iteration_history": [],
            "total_iterations": 0,
        }
        with pytest.raises(ConfigurationError, match="schema_version"):
            EvolutionResult.from_dict(data)

    def test_from_dict_configurationerror_fields(self) -> None:
        """ConfigurationError has field, value, constraint attributes."""
        from gepa_adk.domain.models import EvolutionResult

        data = {"schema_version": 999}
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionResult.from_dict(data)
        err = exc_info.value
        assert err.field == "schema_version"
        assert err.value == 999
        assert err.constraint == "<= 1"

    def test_from_dict_invalid_stop_reason_raises(self) -> None:
        """Invalid stop_reason raises ConfigurationError, not ValueError."""
        from gepa_adk.domain.models import EvolutionResult

        data = {
            "schema_version": 1,
            "stop_reason": "bogus",
            "original_score": 0.5,
            "final_score": 0.8,
            "evolved_components": {"instruction": "Test"},
            "iteration_history": [],
            "total_iterations": 0,
        }
        with pytest.raises(ConfigurationError, match="stop_reason"):
            EvolutionResult.from_dict(data)

    def test_from_dict_missing_required_field_raises(self) -> None:
        """Dict missing original_score raises KeyError."""
        from gepa_adk.domain.models import EvolutionResult

        data = {
            "schema_version": 1,
            "final_score": 0.8,
            "evolved_components": {"instruction": "Test"},
            "iteration_history": [],
            "total_iterations": 0,
        }
        with pytest.raises(KeyError):
            EvolutionResult.from_dict(data)

    def test_from_dict_empty_dict_raises(self) -> None:
        """from_dict({}) raises KeyError for missing required fields."""
        from gepa_adk.domain.models import EvolutionResult

        with pytest.raises(KeyError):
            EvolutionResult.from_dict({})

    def test_to_dict_json_serializable(self) -> None:
        """json.dumps(result.to_dict()) succeeds without custom encoder."""
        import json

        from gepa_adk.domain.models import EvolutionResult, IterationRecord
        from gepa_adk.domain.types import StopReason

        result = EvolutionResult(
            stop_reason=StopReason.MAX_ITERATIONS,
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Test"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.8,
                    component_text="Test",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
            valset_score=0.75,
        )
        json_str = json.dumps(result.to_dict())
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["stop_reason"] == "max_iterations"


class TestMultiAgentEvolutionResultSerialization:
    """Tests for MultiAgentEvolutionResult to_dict/from_dict serialization."""

    def test_to_dict_all_fields(self) -> None:
        """to_dict produces dict with all 8 fields, primary_agent included."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult
        from gepa_adk.domain.types import StopReason

        result = MultiAgentEvolutionResult(
            stop_reason=StopReason.STOPPER_TRIGGERED,
            evolved_components={
                "generator": "Generate code",
                "critic": "Review code",
            },
            original_score=0.5,
            final_score=0.8,
            primary_agent="generator",
            iteration_history=[],
            total_iterations=0,
        )
        d = result.to_dict()
        assert set(d.keys()) == {
            "schema_version",
            "stop_reason",
            "evolved_components",
            "original_score",
            "final_score",
            "primary_agent",
            "iteration_history",
            "total_iterations",
            "original_components",
        }
        assert d["primary_agent"] == "generator"
        assert d["stop_reason"] == "stopper_triggered"

    def test_from_dict_round_trip(self) -> None:
        """Complete round-trip preserves all fields."""
        from gepa_adk.domain.models import (
            IterationRecord,
            MultiAgentEvolutionResult,
        )
        from gepa_adk.domain.types import StopReason

        original = MultiAgentEvolutionResult(
            stop_reason=StopReason.STOPPER_TRIGGERED,
            evolved_components={
                "generator": "Generate code",
                "critic": "Review code",
            },
            original_score=0.5,
            final_score=0.8,
            primary_agent="generator",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.8,
                    component_text="Generate code",
                    evolved_component="generator",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )
        restored = MultiAgentEvolutionResult.from_dict(original.to_dict())
        assert restored.schema_version == original.schema_version
        assert restored.stop_reason == original.stop_reason
        assert restored.evolved_components == original.evolved_components
        assert restored.original_score == original.original_score
        assert restored.final_score == original.final_score
        assert restored.primary_agent == original.primary_agent
        assert restored.total_iterations == original.total_iterations
        assert len(restored.iteration_history) == 1

    def test_from_dict_future_schema_version_raises(self) -> None:
        """schema_version 999 raises ConfigurationError."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult

        data = {
            "schema_version": 999,
            "evolved_components": {"generator": "Test"},
            "original_score": 0.5,
            "final_score": 0.8,
            "primary_agent": "generator",
            "iteration_history": [],
            "total_iterations": 0,
        }
        with pytest.raises(ConfigurationError, match="schema_version"):
            MultiAgentEvolutionResult.from_dict(data)

    def test_from_dict_invalid_stop_reason_raises(self) -> None:
        """Invalid stop_reason raises ConfigurationError, not ValueError."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult

        data = {
            "schema_version": 1,
            "stop_reason": "bogus",
            "evolved_components": {"generator": "Test"},
            "original_score": 0.5,
            "final_score": 0.8,
            "primary_agent": "generator",
            "iteration_history": [],
            "total_iterations": 0,
        }
        with pytest.raises(ConfigurationError, match="stop_reason"):
            MultiAgentEvolutionResult.from_dict(data)

    def test_from_dict_missing_required_field_raises(self) -> None:
        """Dict missing original_score raises KeyError."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult

        data = {
            "schema_version": 1,
            "evolved_components": {"generator": "Test"},
            "final_score": 0.8,
            "primary_agent": "generator",
            "iteration_history": [],
            "total_iterations": 0,
        }
        with pytest.raises(KeyError):
            MultiAgentEvolutionResult.from_dict(data)

    def test_from_dict_empty_dict_raises(self) -> None:
        """from_dict({}) raises KeyError for missing required fields."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult

        with pytest.raises(KeyError):
            MultiAgentEvolutionResult.from_dict({})


class TestSerializationFixtures:
    """Tests for loading JSON fixture files."""

    def test_load_evolution_result_v1_fixture(self) -> None:
        """Load evolution_result_v1.json, from_dict(), verify fields."""
        import json
        from pathlib import Path

        from gepa_adk.domain.models import EvolutionResult
        from gepa_adk.domain.types import StopReason

        fixture_path = (
            Path(__file__).parents[2] / "fixtures" / "evolution_result_v1.json"
        )
        with open(fixture_path) as f:
            data = json.load(f)

        result = EvolutionResult.from_dict(data)
        assert result.schema_version == 1
        assert result.stop_reason == StopReason.MAX_ITERATIONS
        assert result.original_score == 0.45
        assert result.final_score == 0.82
        assert result.evolved_components == {"instruction": "Be helpful and concise"}
        assert len(result.iteration_history) == 3
        assert result.total_iterations == 3
        assert result.valset_score == 0.80
        assert result.trainset_score == 0.75
        assert result.objective_scores is not None
        assert len(result.objective_scores) == 2

    def test_load_multiagent_result_v1_fixture(self) -> None:
        """Load multiagent_result_v1.json, from_dict(), verify fields."""
        import json
        from pathlib import Path

        from gepa_adk.domain.models import MultiAgentEvolutionResult
        from gepa_adk.domain.types import StopReason

        fixture_path = (
            Path(__file__).parents[2] / "fixtures" / "multiagent_result_v1.json"
        )
        with open(fixture_path) as f:
            data = json.load(f)

        result = MultiAgentEvolutionResult.from_dict(data)
        assert result.schema_version == 1
        assert result.stop_reason == StopReason.STOPPER_TRIGGERED
        assert result.original_score == 0.50
        assert result.final_score == 0.78
        assert result.primary_agent == "generator"
        assert len(result.evolved_components) == 2
        assert len(result.iteration_history) == 2
        assert result.total_iterations == 2

    def test_fixture_schema_version(self) -> None:
        """Loaded fixtures have schema_version == 1."""
        import json
        from pathlib import Path

        from gepa_adk.domain.models import EvolutionResult, MultiAgentEvolutionResult

        fixtures_dir = Path(__file__).parents[2] / "fixtures"

        with open(fixtures_dir / "evolution_result_v1.json") as f:
            er = EvolutionResult.from_dict(json.load(f))
        assert er.schema_version == 1

        with open(fixtures_dir / "multiagent_result_v1.json") as f:
            mr = MultiAgentEvolutionResult.from_dict(json.load(f))
        assert mr.schema_version == 1


# =============================================================================
# Original Components Field Tests (Story 2.3)
# =============================================================================


class TestEvolutionResultOriginalComponents:
    """Tests for EvolutionResult.original_components field and serialization."""

    def test_to_dict_includes_original_components(self) -> None:
        """Non-None originals appear in serialized dict."""
        from gepa_adk.domain.models import EvolutionResult

        result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Evolved"},
            iteration_history=[],
            total_iterations=1,
            original_components={"instruction": "Original"},
        )
        d = result.to_dict()
        assert d["original_components"] == {"instruction": "Original"}

    def test_to_dict_original_components_none(self) -> None:
        """None originals serialize as None."""
        from gepa_adk.domain.models import EvolutionResult

        result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Evolved"},
            iteration_history=[],
            total_iterations=1,
        )
        d = result.to_dict()
        assert d["original_components"] is None

    def test_from_dict_round_trip_with_original_components(self) -> None:
        """Round-trip preserves original_components."""
        from gepa_adk.domain.models import EvolutionResult

        originals = {"instruction": "Be helpful", "output_schema": "{}"}
        result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Evolved"},
            iteration_history=[],
            total_iterations=1,
            original_components=originals,
        )
        restored = EvolutionResult.from_dict(result.to_dict())
        assert restored.original_components == originals

    def test_from_dict_without_original_components_key(self) -> None:
        """Old dict without key deserializes to None (backward compat)."""
        from gepa_adk.domain.models import EvolutionResult

        data = {
            "schema_version": 1,
            "stop_reason": "completed",
            "original_score": 0.5,
            "final_score": 0.8,
            "evolved_components": {"instruction": "Test"},
            "iteration_history": [],
            "total_iterations": 0,
        }
        result = EvolutionResult.from_dict(data)
        assert result.original_components is None


class TestMultiAgentOriginalComponents:
    """Tests for MultiAgentEvolutionResult.original_components field."""

    def test_to_dict_includes_original_components(self) -> None:
        """Non-None originals appear in serialized dict."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult

        result = MultiAgentEvolutionResult(
            evolved_components={"gen": "Evolved"},
            original_score=0.5,
            final_score=0.8,
            primary_agent="gen",
            iteration_history=[],
            total_iterations=1,
            original_components={"gen": "Original"},
        )
        d = result.to_dict()
        assert d["original_components"] == {"gen": "Original"}

    def test_to_dict_original_components_none(self) -> None:
        """None originals serialize as None."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult

        result = MultiAgentEvolutionResult(
            evolved_components={"gen": "Evolved"},
            original_score=0.5,
            final_score=0.8,
            primary_agent="gen",
            iteration_history=[],
            total_iterations=1,
        )
        d = result.to_dict()
        assert d["original_components"] is None

    def test_from_dict_round_trip_with_original_components(self) -> None:
        """Round-trip preserves original_components."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult

        originals = {"gen": "Original gen", "critic": "Original critic"}
        result = MultiAgentEvolutionResult(
            evolved_components={"gen": "Evolved"},
            original_score=0.5,
            final_score=0.8,
            primary_agent="gen",
            iteration_history=[],
            total_iterations=1,
            original_components=originals,
        )
        restored = MultiAgentEvolutionResult.from_dict(result.to_dict())
        assert restored.original_components == originals

    def test_from_dict_without_original_components_key(self) -> None:
        """Old dict without key deserializes to None (backward compat)."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult

        data = {
            "schema_version": 1,
            "stop_reason": "completed",
            "evolved_components": {"gen": "Test"},
            "original_score": 0.5,
            "final_score": 0.8,
            "primary_agent": "gen",
            "iteration_history": [],
            "total_iterations": 0,
        }
        result = MultiAgentEvolutionResult.from_dict(data)
        assert result.original_components is None

    def test_v1_fixture_loads_without_original_components(self) -> None:
        """V1 fixture file has no original_components key, loads as None."""
        import json
        from pathlib import Path

        from gepa_adk.domain.models import MultiAgentEvolutionResult

        fixture_path = (
            Path(__file__).parents[2] / "fixtures" / "multiagent_result_v1.json"
        )
        with open(fixture_path) as f:
            data = json.load(f)

        result = MultiAgentEvolutionResult.from_dict(data)
        assert result.original_components is None


# =============================================================================
# Display Method Tests (Story 2.3)
# =============================================================================


class TestEvolutionResultRepr:
    """Tests for EvolutionResult.__repr__() narrative format."""

    def _make_result(
        self,
        original_score: float = 0.60,
        final_score: float = 0.85,
        total_iterations: int = 10,
        evolved_components: dict[str, str] | None = None,
        iteration_history: list | None = None,
    ):
        from gepa_adk.domain.models import EvolutionResult, IterationRecord
        from gepa_adk.domain.types import StopReason

        if evolved_components is None:
            evolved_components = {"instruction": "Be helpful"}
        if iteration_history is None:
            iteration_history = [
                IterationRecord(
                    iteration_number=i + 1,
                    score=0.7 + i * 0.01,
                    component_text="text",
                    evolved_component="instruction",
                    accepted=i % 2 == 0,
                )
                for i in range(total_iterations)
            ]
        return EvolutionResult(
            stop_reason=StopReason.COMPLETED,
            original_score=original_score,
            final_score=final_score,
            evolved_components=evolved_components,
            iteration_history=iteration_history,
            total_iterations=total_iterations,
        )

    def test_repr_contains_improvement_percentage(self) -> None:
        """Repr includes improvement percentage."""
        import re

        r = repr(self._make_result())
        assert re.search(r"[+-]?\d+\.\d+%", r)

    def test_repr_contains_scores(self) -> None:
        """Repr includes original and final score values."""
        r = repr(self._make_result(original_score=0.60, final_score=0.85))
        assert "0.60" in r
        assert "0.85" in r

    def test_repr_contains_iterations_and_stop_reason(self) -> None:
        """Repr includes iterations count and stop reason."""
        import re

        r = repr(self._make_result())
        assert re.search(r"iterations: \d+", r)
        assert re.search(r"stop_reason: \w+", r)

    def test_repr_contains_component_names(self) -> None:
        """Repr includes evolved component key names."""
        r = repr(self._make_result(evolved_components={"instruction": "x"}))
        assert "instruction" in r

    def test_repr_every_line_greppable(self) -> None:
        """No empty interior lines in repr output."""
        r = repr(self._make_result())
        lines = r.split("\n")
        for line in lines:
            assert line.strip() != "", f"Empty line found: {lines!r}"

    def test_repr_no_box_drawing(self) -> None:
        """No Unicode box-drawing characters (U+2500-U+257F)."""
        r = repr(self._make_result())
        for ch in r:
            assert not (0x2500 <= ord(ch) <= 0x257F), f"Box char found: {ch!r}"

    def test_repr_uses_two_space_indent(self) -> None:
        """Indented lines start with exactly two spaces."""
        r = repr(self._make_result())
        lines = r.split("\n")
        for line in lines[1:]:  # skip first line
            assert line.startswith("  "), f"Expected 2-space indent: {line!r}"

    def test_repr_positive_improvement(self) -> None:
        """Positive improvement shows + sign."""
        r = repr(self._make_result(original_score=0.50, final_score=0.80))
        assert "+" in r

    def test_repr_negative_improvement(self) -> None:
        """Negative improvement shows - sign."""
        r = repr(self._make_result(original_score=0.80, final_score=0.50))
        assert "-" in r

    def test_repr_zero_improvement(self) -> None:
        """Zero improvement shows 0.0%."""
        r = repr(self._make_result(original_score=0.50, final_score=0.50))
        assert "0.0%" in r

    def test_repr_empty_history(self) -> None:
        """Empty iteration_history omits acceptance_rate line."""
        r = repr(self._make_result(total_iterations=0, iteration_history=[]))
        assert "acceptance_rate" not in r

    def test_repr_multiple_components(self) -> None:
        """Multiple component names shown."""
        r = repr(
            self._make_result(
                evolved_components={"instruction": "x", "output_schema": "y"},
            )
        )
        assert "instruction" in r
        assert "output_schema" in r

    def test_repr_unicode_component_values(self) -> None:
        """Unicode in component text does not break repr."""
        r = repr(
            self._make_result(
                evolved_components={"instruction": "\u2764 \u4f60\u597d emoji"},
            )
        )
        assert "instruction" in r

    def test_repr_zero_base_score_shows_raw_delta(self) -> None:
        """Zero original_score shows raw delta instead of absurd percentage."""
        r = repr(self._make_result(original_score=0.0, final_score=0.85))
        # Must NOT contain astronomical percentage
        assert "000000" not in r
        # Should show raw improvement delta
        assert "+0.8500" in r
        assert "improvement" in r


class TestMultiAgentEvolutionResultRepr:
    """Tests for MultiAgentEvolutionResult.__repr__() narrative format."""

    def _make_result(self):
        from gepa_adk.domain.models import (
            IterationRecord,
            MultiAgentEvolutionResult,
        )
        from gepa_adk.domain.types import StopReason

        return MultiAgentEvolutionResult(
            stop_reason=StopReason.COMPLETED,
            evolved_components={
                "generator": "Generate code",
                "critic": "Review code",
            },
            original_score=0.60,
            final_score=0.85,
            primary_agent="generator",
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.7,
                    component_text="text",
                    evolved_component="generator",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

    def test_repr_contains_improvement_percentage(self) -> None:
        """Repr includes improvement percentage."""
        import re

        r = repr(self._make_result())
        assert re.search(r"[+-]?\d+\.\d+%", r)

    def test_repr_contains_primary_agent(self) -> None:
        """Repr shows primary agent name."""
        r = repr(self._make_result())
        assert "primary_agent: generator" in r

    def test_repr_contains_agent_names(self) -> None:
        """Repr shows agent names."""
        r = repr(self._make_result())
        assert "critic" in r
        assert "generator" in r

    def test_repr_uses_two_space_indent(self) -> None:
        """Indented lines start with exactly two spaces."""
        r = repr(self._make_result())
        lines = r.split("\n")
        for line in lines[1:]:
            assert line.startswith("  "), f"Expected 2-space indent: {line!r}"

    def test_repr_zero_base_score_shows_raw_delta(self) -> None:
        """Zero original_score shows raw delta instead of absurd percentage."""
        from gepa_adk.domain.models import MultiAgentEvolutionResult

        result = MultiAgentEvolutionResult(
            evolved_components={"gen": "code"},
            original_score=0.0,
            final_score=0.85,
            primary_agent="gen",
            iteration_history=[],
            total_iterations=0,
        )
        r = repr(result)
        assert "000000" not in r
        assert "+0.8500" in r
        assert "improvement" in r


class TestEvolutionResultShowDiff:
    """Tests for EvolutionResult.show_diff() unified diff output."""

    def _make_result(
        self,
        evolved: dict[str, str],
        originals: dict[str, str] | None = None,
    ):
        from gepa_adk.domain.models import EvolutionResult

        return EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components=evolved,
            iteration_history=[],
            total_iterations=0,
            original_components=originals,
        )

    def test_show_diff_contains_diff_markers(self) -> None:
        """Diff output contains ---, +++, @@ markers."""
        result = self._make_result(
            evolved={"instruction": "line1\nline2 changed"},
            originals={"instruction": "line1\nline2"},
        )
        diff = result.show_diff()
        assert "---" in diff
        assert "+++" in diff
        assert "@@" in diff

    def test_show_diff_shows_changed_component(self) -> None:
        """Changed text appears in diff output."""
        result = self._make_result(
            evolved={"instruction": "Be helpful and concise"},
            originals={"instruction": "Be helpful"},
        )
        diff = result.show_diff()
        assert "instruction" in diff

    def test_show_diff_identical_returns_no_changes(self) -> None:
        """Identical components return no-changes message."""
        result = self._make_result(
            evolved={"instruction": "Same text"},
            originals={"instruction": "Same text"},
        )
        assert result.show_diff() == "No changes detected."

    def test_show_diff_multiple_components(self) -> None:
        """Diffs for each changed component."""
        result = self._make_result(
            evolved={"instruction": "Changed A", "schema": "Changed B"},
            originals={"instruction": "Original A", "schema": "Original B"},
        )
        diff = result.show_diff()
        assert "instruction" in diff
        assert "schema" in diff

    def test_show_diff_missing_original_key(self) -> None:
        """New component with no original shows as additions."""
        result = self._make_result(
            evolved={"instruction": "Evolved", "new_comp": "Brand new"},
            originals={"instruction": "Original"},
        )
        diff = result.show_diff()
        assert "+Brand new" in diff

    def test_show_diff_multiline_values(self) -> None:
        """Multi-line component text diffs correctly."""
        result = self._make_result(
            evolved={"instruction": "line1\nline2\nline3 changed"},
            originals={"instruction": "line1\nline2\nline3"},
        )
        diff = result.show_diff()
        assert "@@" in diff

    def test_show_diff_zero_arg_with_stored_originals(self) -> None:
        """Zero-arg call uses self.original_components."""
        result = self._make_result(
            evolved={"instruction": "Evolved"},
            originals={"instruction": "Original"},
        )
        diff = result.show_diff()
        assert "instruction" in diff
        assert "---" in diff

    def test_show_diff_param_overrides_stored(self) -> None:
        """Explicit param takes priority over stored originals."""
        result = self._make_result(
            evolved={"instruction": "Evolved"},
            originals={"instruction": "Stored Original"},
        )
        diff = result.show_diff(original_components={"instruction": "Param Original"})
        assert "Param Original" in diff

    def test_show_diff_no_originals_raises_valueerror(self) -> None:
        """Both param and field None raises ValueError."""
        import pytest

        result = self._make_result(evolved={"instruction": "Test"})
        with pytest.raises(ValueError, match="No original components"):
            result.show_diff()

    def test_show_diff_component_with_diff_markers_in_text(self) -> None:
        """Component text containing --- / +++ / @@ chars handled."""
        result = self._make_result(
            evolved={"instruction": "---changed+++\n@@section"},
            originals={"instruction": "---original+++\n@@section"},
        )
        diff = result.show_diff()
        assert "instruction" in diff

    def test_show_diff_empty_string_components(self) -> None:
        """Empty string component value handled."""
        result = self._make_result(
            evolved={"instruction": "Now has content"},
            originals={"instruction": ""},
        )
        diff = result.show_diff()
        assert "+Now has content" in diff

    def test_show_diff_empty_dict_param_not_falsy_fallthrough(self) -> None:
        """Empty dict param is used as-is, not falling through to stored originals."""
        result = self._make_result(
            evolved={"instruction": "Evolved"},
            originals={"instruction": "Stored Original"},
        )
        # Empty dict means no originals to diff — new component shows as additions
        diff = result.show_diff(original_components={})
        assert "+Evolved" in diff
        # Must NOT contain stored original (would indicate falsy fallthrough)
        assert "Stored Original" not in diff


class TestMultiAgentEvolutionResultShowDiff:
    """Tests for MultiAgentEvolutionResult.show_diff()."""

    def _make_result(
        self,
        evolved: dict[str, str],
        originals: dict[str, str] | None = None,
    ):
        from gepa_adk.domain.models import MultiAgentEvolutionResult

        return MultiAgentEvolutionResult(
            evolved_components=evolved,
            original_score=0.5,
            final_score=0.8,
            primary_agent="gen",
            iteration_history=[],
            total_iterations=0,
            original_components=originals,
        )

    def test_show_diff_contains_diff_markers(self) -> None:
        """Diff output contains diff markers."""
        result = self._make_result(
            evolved={"gen": "Changed"},
            originals={"gen": "Original"},
        )
        diff = result.show_diff()
        assert "---" in diff
        assert "+++" in diff

    def test_show_diff_identical_returns_no_changes(self) -> None:
        """Identical components return no-changes message."""
        result = self._make_result(
            evolved={"gen": "Same"},
            originals={"gen": "Same"},
        )
        assert result.show_diff() == "No changes detected."

    def test_show_diff_zero_arg_with_stored_originals(self) -> None:
        """Zero-arg call uses self.original_components."""
        result = self._make_result(
            evolved={"gen": "Evolved"},
            originals={"gen": "Original"},
        )
        diff = result.show_diff()
        assert "gen" in diff

    def test_show_diff_no_originals_raises_valueerror(self) -> None:
        """Both param and field None raises ValueError."""
        import pytest

        result = self._make_result(evolved={"gen": "Test"})
        with pytest.raises(ValueError, match="No original components"):
            result.show_diff()

    def test_show_diff_empty_dict_param_not_falsy_fallthrough(self) -> None:
        """Empty dict param is used as-is, not falling through to stored originals."""
        result = self._make_result(
            evolved={"gen": "Evolved"},
            originals={"gen": "Stored Original"},
        )
        diff = result.show_diff(original_components={})
        assert "+Evolved" in diff
        assert "Stored Original" not in diff


class TestEvolutionResultReprHtml:
    """Tests for EvolutionResult._repr_html_() Jupyter rendering."""

    def _make_result(
        self,
        evolved_components: dict[str, str] | None = None,
    ):
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        if evolved_components is None:
            evolved_components = {"instruction": "Be helpful"}
        return EvolutionResult(
            original_score=0.50,
            final_score=0.85,
            evolved_components=evolved_components,
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.7,
                    component_text="text",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

    def test_repr_html_returns_string(self) -> None:
        """_repr_html_ returns a string."""
        assert isinstance(self._make_result()._repr_html_(), str)

    def test_repr_html_contains_table_tags(self) -> None:
        """HTML contains <table> elements."""
        import re

        html = self._make_result()._repr_html_()
        assert re.search(r"<table", html)
        assert re.search(r"</table>", html)

    def test_repr_html_contains_improvement(self) -> None:
        """HTML includes improvement percentage."""
        import re

        html = self._make_result()._repr_html_()
        assert re.search(r"[+-]?\d+\.\d+%", html)

    def test_repr_html_contains_scores(self) -> None:
        """HTML includes original and final scores."""
        html = self._make_result()._repr_html_()
        assert "0.5000" in html
        assert "0.8500" in html

    def test_repr_html_escapes_values(self) -> None:
        """XSS payload in component text is escaped."""
        html = self._make_result(
            evolved_components={"instruction": "<script>alert('xss')</script>"}
        )._repr_html_()
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_repr_html_contains_component_names(self) -> None:
        """Component keys appear in HTML."""
        html = self._make_result()._repr_html_()
        assert "instruction" in html

    def test_repr_html_contains_details_summary(self) -> None:
        """HTML includes <details> and <summary> tags."""
        html = self._make_result()._repr_html_()
        assert "<details>" in html
        assert "<summary>" in html


class TestMultiAgentEvolutionResultReprHtml:
    """Tests for MultiAgentEvolutionResult._repr_html_()."""

    def _make_result(self):
        from gepa_adk.domain.models import MultiAgentEvolutionResult

        return MultiAgentEvolutionResult(
            evolved_components={"gen": "Generate", "critic": "Review"},
            original_score=0.50,
            final_score=0.85,
            primary_agent="gen",
            iteration_history=[],
            total_iterations=0,
        )

    def test_repr_html_returns_string(self) -> None:
        """_repr_html_ returns a string."""
        assert isinstance(self._make_result()._repr_html_(), str)

    def test_repr_html_contains_table_tags(self) -> None:
        """HTML contains <table> elements."""
        import re

        html = self._make_result()._repr_html_()
        assert re.search(r"<table", html)
        assert re.search(r"</table>", html)

    def test_repr_html_contains_primary_agent(self) -> None:
        """HTML includes primary agent name."""
        html = self._make_result()._repr_html_()
        assert "gen" in html

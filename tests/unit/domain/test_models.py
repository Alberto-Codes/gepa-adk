"""Unit tests for domain models."""

import pytest

from gepa_adk.domain.exceptions import ConfigurationError


class TestEvolutionConfig:
    """Tests for EvolutionConfig dataclass."""

    def test_evolution_config_default_max_iterations(self):
        """Test EvolutionConfig defaults max_iterations to 50."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.max_iterations == 50

    def test_evolution_config_default_max_concurrent_evals(self):
        """Test EvolutionConfig defaults max_concurrent_evals to 5."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.max_concurrent_evals == 5

    def test_evolution_config_default_min_improvement_threshold(self):
        """Test EvolutionConfig defaults min_improvement_threshold to 0.01."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.min_improvement_threshold == 0.01

    def test_evolution_config_default_patience(self):
        """Test EvolutionConfig defaults patience to 5."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.patience == 5

    def test_evolution_config_default_reflection_model(self):
        """Test EvolutionConfig defaults reflection_model to gemini-2.0-flash."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig()
        assert config.reflection_model == "gemini-2.0-flash"

    def test_evolution_config_custom_values(self):
        """Test EvolutionConfig preserves custom values."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(
            max_iterations=100,
            max_concurrent_evals=10,
            min_improvement_threshold=0.05,
            patience=10,
            reflection_model="gemini-1.5-pro",
        )

        assert config.max_iterations == 100
        assert config.max_concurrent_evals == 10
        assert config.min_improvement_threshold == 0.05
        assert config.patience == 10
        assert config.reflection_model == "gemini-1.5-pro"

    def test_evolution_config_negative_max_iterations_raises_error(self):
        """Test EvolutionConfig raises ConfigurationError for negative max_iterations."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(max_iterations=-1)

        error = exc_info.value
        assert error.field == "max_iterations"
        assert error.value == -1
        assert ">= 0" in str(error)

    def test_evolution_config_zero_max_concurrent_evals_raises_error(self):
        """Test EvolutionConfig raises ConfigurationError for zero max_concurrent_evals."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(max_concurrent_evals=0)

        error = exc_info.value
        assert error.field == "max_concurrent_evals"
        assert error.value == 0
        assert ">= 1" in str(error)

    def test_evolution_config_negative_max_concurrent_evals_raises_error(self):
        """Test EvolutionConfig raises ConfigurationError for negative max_concurrent_evals."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(max_concurrent_evals=-1)

        error = exc_info.value
        assert error.field == "max_concurrent_evals"

    def test_evolution_config_negative_min_improvement_threshold_raises_error(self):
        """Test EvolutionConfig raises ConfigurationError for negative threshold."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(min_improvement_threshold=-0.01)

        error = exc_info.value
        assert error.field == "min_improvement_threshold"

    def test_evolution_config_negative_patience_raises_error(self):
        """Test EvolutionConfig raises ConfigurationError for negative patience."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(patience=-1)

        error = exc_info.value
        assert error.field == "patience"

    def test_evolution_config_empty_reflection_model_raises_error(self):
        """Test EvolutionConfig raises ConfigurationError for empty reflection_model."""
        from gepa_adk.domain.models import EvolutionConfig

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(reflection_model="")

        error = exc_info.value
        assert error.field == "reflection_model"

    def test_evolution_config_zero_max_iterations_is_valid(self):
        """Test EvolutionConfig allows zero max_iterations (no evolution, baseline only)."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(max_iterations=0)
        assert config.max_iterations == 0

    def test_evolution_config_zero_patience_is_valid(self):
        """Test EvolutionConfig allows zero patience (never stop early)."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(patience=0)
        assert config.patience == 0

    def test_evolution_config_zero_min_improvement_threshold_is_valid(self):
        """Test EvolutionConfig allows zero min_improvement_threshold."""
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(min_improvement_threshold=0.0)
        assert config.min_improvement_threshold == 0.0


class TestIterationRecord:
    """Tests for IterationRecord dataclass."""

    def test_iteration_record_field_access(self):
        """Test IterationRecord stores all required fields."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.75,
            instruction="You are a helpful assistant.",
            accepted=True,
        )

        assert record.iteration_number == 1
        assert record.score == 0.75
        assert record.instruction == "You are a helpful assistant."
        assert record.accepted is True

    def test_iteration_record_with_different_values(self):
        """Test IterationRecord with various field values."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=5,
            score=0.92,
            instruction="You are an expert analyst.",
            accepted=False,
        )

        assert record.iteration_number == 5
        assert record.score == 0.92
        assert record.instruction == "You are an expert analyst."
        assert record.accepted is False

    def test_iteration_record_is_immutable(self):
        """Test IterationRecord is frozen (immutable)."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.75,
            instruction="Test",
            accepted=True,
        )

        # Attempting to modify should raise an error
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            record.score = 0.8

    def test_iteration_record_supports_zero_score(self):
        """Test IterationRecord accepts zero score."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.0,
            instruction="Test",
            accepted=False,
        )

        assert record.score == 0.0

    def test_iteration_record_supports_scores_above_one(self):
        """Test IterationRecord accepts scores > 1.0 (not enforced)."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=1.5,
            instruction="Test",
            accepted=True,
        )

        assert record.score == 1.5

    def test_iteration_record_empty_instruction_allowed(self):
        """Test IterationRecord allows empty instruction string."""
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.5,
            instruction="",
            accepted=False,
        )

        assert record.instruction == ""


class TestEvolutionResult:
    """Tests for EvolutionResult dataclass."""

    def test_evolution_result_field_access(self):
        """Test EvolutionResult stores all required fields."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        record1 = IterationRecord(
            iteration_number=1, score=0.60, instruction="v1", accepted=True
        )
        record2 = IterationRecord(
            iteration_number=2, score=0.75, instruction="v2", accepted=True
        )

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.75,
            evolved_instruction="You are an expert.",
            iteration_history=[record1, record2],
            total_iterations=2,
        )

        assert result.original_score == 0.60
        assert result.final_score == 0.75
        assert result.evolved_instruction == "You are an expert."
        assert len(result.iteration_history) == 2
        assert result.total_iterations == 2

    def test_evolution_result_computed_improvement_positive(self):
        """Test EvolutionResult.improvement property with positive improvement."""
        from gepa_adk.domain.models import EvolutionResult

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test",
            iteration_history=[],
            total_iterations=0,
        )

        assert result.improvement == 0.25  # 0.85 - 0.60

    def test_evolution_result_computed_improvement_negative(self):
        """Test EvolutionResult.improvement property with negative improvement."""
        from gepa_adk.domain.models import EvolutionResult

        result = EvolutionResult(
            original_score=0.80,
            final_score=0.70,
            evolved_instruction="Test",
            iteration_history=[],
            total_iterations=0,
        )

        assert result.improvement == pytest.approx(-0.10)  # 0.70 - 0.80

    def test_evolution_result_computed_improvement_zero(self):
        """Test EvolutionResult.improvement property with no improvement."""
        from gepa_adk.domain.models import EvolutionResult

        result = EvolutionResult(
            original_score=0.75,
            final_score=0.75,
            evolved_instruction="Test",
            iteration_history=[],
            total_iterations=0,
        )

        assert result.improvement == 0.0

    def test_evolution_result_computed_improved_true(self):
        """Test EvolutionResult.improved property returns True when final > original."""
        from gepa_adk.domain.models import EvolutionResult

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test",
            iteration_history=[],
            total_iterations=0,
        )

        assert result.improved is True

    def test_evolution_result_computed_improved_false_when_worse(self):
        """Test EvolutionResult.improved property returns False when final < original."""
        from gepa_adk.domain.models import EvolutionResult

        result = EvolutionResult(
            original_score=0.80,
            final_score=0.70,
            evolved_instruction="Test",
            iteration_history=[],
            total_iterations=0,
        )

        assert result.improved is False

    def test_evolution_result_computed_improved_false_when_equal(self):
        """Test EvolutionResult.improved property returns False when no change."""
        from gepa_adk.domain.models import EvolutionResult

        result = EvolutionResult(
            original_score=0.75,
            final_score=0.75,
            evolved_instruction="Test",
            iteration_history=[],
            total_iterations=0,
        )

        assert result.improved is False

    def test_evolution_result_is_immutable(self):
        """Test EvolutionResult is frozen (immutable)."""
        from gepa_adk.domain.models import EvolutionResult

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Test",
            iteration_history=[],
            total_iterations=0,
        )

        # Attempting to modify should raise an error
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            result.final_score = 0.9

    def test_evolution_result_empty_iteration_history_allowed(self):
        """Test EvolutionResult allows empty iteration_history."""
        from gepa_adk.domain.models import EvolutionResult

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.60,
            evolved_instruction="Test",
            iteration_history=[],
            total_iterations=0,
        )

        assert result.iteration_history == []
        assert result.total_iterations == 0

    def test_evolution_result_with_multiple_iterations(self):
        """Test EvolutionResult with multiple iteration records."""
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        records = [
            IterationRecord(
                iteration_number=1, score=0.60, instruction="v1", accepted=True
            ),
            IterationRecord(
                iteration_number=2, score=0.72, instruction="v2", accepted=True
            ),
            IterationRecord(
                iteration_number=3, score=0.85, instruction="v3", accepted=True
            ),
        ]

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="v3",
            iteration_history=records,
            total_iterations=3,
        )

        assert len(result.iteration_history) == 3
        assert result.iteration_history[0].score == 0.60
        assert result.iteration_history[2].score == 0.85


class TestCandidate:
    """Tests for Candidate dataclass."""

    def test_candidate_component_access(self):
        """Test Candidate allows component get/set operations."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(
            components={"instruction": "You are a helpful assistant."}
        )

        assert candidate.components["instruction"] == "You are a helpful assistant."

    def test_candidate_component_modification(self):
        """Test Candidate allows modifying components."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={"instruction": "Original"})
        candidate.components["instruction"] = "Modified"

        assert candidate.components["instruction"] == "Modified"

    def test_candidate_multiple_components(self):
        """Test Candidate can store multiple components."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(
            components={
                "instruction": "You are an expert.",
                "output_schema": '{"type": "object"}',
            }
        )

        assert candidate.components["instruction"] == "You are an expert."
        assert candidate.components["output_schema"] == '{"type": "object"}'
        assert len(candidate.components) == 2

    def test_candidate_add_component(self):
        """Test Candidate allows adding new components."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={"instruction": "Test"})
        candidate.components["output_schema"] = "Schema"

        assert "output_schema" in candidate.components
        assert candidate.components["output_schema"] == "Schema"

    def test_candidate_list_component_keys(self):
        """Test Candidate can list all component keys."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(
            components={
                "instruction": "Test",
                "output_schema": "Schema",
                "examples": "Examples",
            }
        )

        keys = list(candidate.components.keys())
        assert "instruction" in keys
        assert "output_schema" in keys
        assert "examples" in keys
        assert len(keys) == 3

    def test_candidate_default_generation(self):
        """Test Candidate defaults generation to 0."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={"instruction": "Test"})

        assert candidate.generation == 0

    def test_candidate_custom_generation(self):
        """Test Candidate allows custom generation value."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={"instruction": "Test"}, generation=5)

        assert candidate.generation == 5

    def test_candidate_default_parent_id(self):
        """Test Candidate defaults parent_id to None."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={"instruction": "Test"})

        assert candidate.parent_id is None

    def test_candidate_with_parent_id(self):
        """Test Candidate stores parent_id for lineage tracking."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(
            components={"instruction": "Test"}, parent_id="parent-uuid-123"
        )

        assert candidate.parent_id == "parent-uuid-123"

    def test_candidate_default_metadata(self):
        """Test Candidate defaults metadata to empty dict."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={"instruction": "Test"})

        assert candidate.metadata == {}

    def test_candidate_with_metadata(self):
        """Test Candidate stores custom metadata."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(
            components={"instruction": "Test"},
            metadata={"mutation_type": "reflective", "score": 0.85},
        )

        assert candidate.metadata["mutation_type"] == "reflective"
        assert candidate.metadata["score"] == 0.85

    def test_candidate_empty_components_allowed(self):
        """Test Candidate allows empty components dict."""
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(components={})

        assert candidate.components == {}
        assert len(candidate.components) == 0

    def test_candidate_mutable_defaults_are_independent(self):
        """Test Candidate instances have independent mutable defaults."""
        from gepa_adk.domain.models import Candidate

        # Create two candidates without explicit components/metadata
        candidate1 = Candidate()
        candidate2 = Candidate()

        # Modify candidate1's components
        candidate1.components["instruction"] = "Test1"

        # candidate2 should not be affected
        assert "instruction" not in candidate2.components

        # Modify candidate1's metadata
        candidate1.metadata["key"] = "value1"

        # candidate2 should not be affected
        assert "key" not in candidate2.metadata

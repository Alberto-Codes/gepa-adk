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

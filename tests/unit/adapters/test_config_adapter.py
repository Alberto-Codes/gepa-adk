"""Unit tests for config_adapter module.

This module tests the serialize, deserialize, and validate functions
for GenerateContentConfig YAML serialization.
"""

from __future__ import annotations

import pytest
import yaml

from gepa_adk.adapters.config_adapter import (
    EVOLVABLE_PARAMS,
    deserialize_generate_config,
    serialize_generate_config,
    validate_generate_config,
)
from gepa_adk.domain.exceptions import ConfigValidationError


class TestSerializeGenerateConfig:
    """Unit tests for serialize_generate_config function."""

    def test_serialize_returns_yaml_string(self) -> None:
        """Serialize should return a YAML string."""
        from google.genai.types import GenerateContentConfig

        config = GenerateContentConfig(temperature=0.7)
        result = serialize_generate_config(config)
        assert isinstance(result, str)
        assert "temperature" in result

    def test_serialize_includes_descriptions(self) -> None:
        """Serialize should include YAML comments with descriptions."""
        from google.genai.types import GenerateContentConfig

        config = GenerateContentConfig(temperature=0.7)
        result = serialize_generate_config(config)
        # Should have comment describing temperature
        assert "# temperature:" in result

    def test_serialize_roundtrip(self) -> None:
        """Serialize output should be parseable by yaml.safe_load."""
        from google.genai.types import GenerateContentConfig

        config = GenerateContentConfig(temperature=0.7, top_p=0.9)
        yaml_str = serialize_generate_config(config)
        parsed = yaml.safe_load(yaml_str)
        assert parsed["temperature"] == 0.7
        assert parsed["top_p"] == 0.9

    def test_serialize_excludes_non_evolvable(self) -> None:
        """Serialize should exclude non-evolvable parameters."""
        from google.genai.types import GenerateContentConfig

        # system_instruction is not evolvable
        config = GenerateContentConfig(
            temperature=0.7,
            system_instruction="ignored",
        )
        result = serialize_generate_config(config)
        assert "system_instruction" not in result
        assert "temperature" in result

    def test_serialize_none_returns_empty(self) -> None:
        """serialize(None) should return empty string."""
        result = serialize_generate_config(None)
        assert result == ""

    def test_serialize_all_params(self) -> None:
        """Serialize should include all evolvable params when set."""
        from google.genai.types import GenerateContentConfig

        config = GenerateContentConfig(
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            max_output_tokens=1024,
            presence_penalty=0.5,
            frequency_penalty=0.5,
        )
        result = serialize_generate_config(config)

        # All params should be present
        for param in EVOLVABLE_PARAMS:
            assert param in result


class TestDeserializeGenerateConfig:
    """Unit tests for deserialize_generate_config function."""

    def test_deserialize_parses_yaml(self) -> None:
        """Deserialize should parse YAML and create config."""
        result = deserialize_generate_config("temperature: 0.5")
        assert result.temperature == 0.5

    def test_deserialize_merges_with_existing(self) -> None:
        """Deserialize should merge with existing config."""
        from google.genai.types import GenerateContentConfig

        existing = GenerateContentConfig(temperature=0.7, top_p=0.9)
        result = deserialize_generate_config("temperature: 0.5", existing)
        assert result.temperature == 0.5
        assert result.top_p == 0.9  # Preserved from existing

    def test_deserialize_empty_returns_default(self) -> None:
        """Deserialize with empty string should return default config."""
        result = deserialize_generate_config("")
        assert result is not None

    def test_deserialize_invalid_yaml_raises(self) -> None:
        """Deserialize with invalid YAML should raise ConfigValidationError."""
        with pytest.raises(ConfigValidationError):
            deserialize_generate_config("{{{{invalid")

    def test_deserialize_non_dict_raises(self) -> None:
        """Deserialize with non-dict YAML should raise ConfigValidationError."""
        with pytest.raises(ConfigValidationError, match="Expected YAML dict"):
            deserialize_generate_config("just a string")

    def test_deserialize_with_none_existing(self) -> None:
        """Deserialize with None existing should create new config."""
        result = deserialize_generate_config("temperature: 0.5", None)
        assert result.temperature == 0.5

    def test_deserialize_empty_with_existing_returns_existing(self) -> None:
        """Deserialize empty with existing should return existing."""
        from google.genai.types import GenerateContentConfig

        existing = GenerateContentConfig(temperature=0.7)
        result = deserialize_generate_config("", existing)
        assert result is existing


class TestValidateGenerateConfig:
    """Unit tests for validate_generate_config function."""

    def test_validate_empty_dict(self) -> None:
        """Validate with empty dict should return no errors."""
        errors = validate_generate_config({})
        assert errors == []

    def test_validate_valid_config(self) -> None:
        """Validate with valid config should return no errors."""
        errors = validate_generate_config(
            {
                "temperature": 0.7,
                "top_p": 0.9,
            }
        )
        assert errors == []

    def test_validate_temperature_out_of_range(self) -> None:
        """Validate should reject temperature > 2.0."""
        errors = validate_generate_config({"temperature": 3.0})
        assert len(errors) == 1
        assert "temperature" in errors[0]

    def test_validate_temperature_negative(self) -> None:
        """Validate should reject temperature < 0.0."""
        errors = validate_generate_config({"temperature": -0.5})
        assert len(errors) == 1
        assert "temperature" in errors[0]

    def test_validate_negative_top_k(self) -> None:
        """Validate should reject top_k <= 0."""
        errors = validate_generate_config({"top_k": -1})
        assert len(errors) == 1
        assert "top_k" in errors[0]

    def test_validate_zero_top_k(self) -> None:
        """Validate should reject top_k == 0."""
        errors = validate_generate_config({"top_k": 0})
        assert len(errors) == 1
        assert "top_k" in errors[0]

    def test_validate_multiple_errors(self) -> None:
        """Validate should return multiple errors for multiple violations."""
        errors = validate_generate_config(
            {
                "temperature": 999,
                "top_p": -1,
            }
        )
        assert len(errors) == 2

    def test_validate_unknown_param_no_error(self) -> None:
        """Validate should not error on unknown params (just warn)."""
        errors = validate_generate_config({"unknown_param": 42})
        assert errors == []  # Warning logged, no error

    def test_validate_temperature_boundary_valid(self) -> None:
        """Validate should accept temperature at boundaries (0.0 and 2.0)."""
        errors_zero = validate_generate_config({"temperature": 0.0})
        errors_two = validate_generate_config({"temperature": 2.0})
        assert errors_zero == []
        assert errors_two == []

    def test_validate_top_p_boundary_valid(self) -> None:
        """Validate should accept top_p at boundaries (0.0 and 1.0)."""
        errors_zero = validate_generate_config({"top_p": 0.0})
        errors_one = validate_generate_config({"top_p": 1.0})
        assert errors_zero == []
        assert errors_one == []

    def test_validate_top_p_out_of_range(self) -> None:
        """Validate should reject top_p outside [0.0, 1.0]."""
        errors_low = validate_generate_config({"top_p": -0.1})
        errors_high = validate_generate_config({"top_p": 1.1})
        assert len(errors_low) == 1
        assert len(errors_high) == 1

    def test_validate_presence_penalty_range(self) -> None:
        """Validate should accept presence_penalty in [-2.0, 2.0]."""
        errors_valid = validate_generate_config({"presence_penalty": 0.5})
        errors_low = validate_generate_config({"presence_penalty": -2.0})
        errors_high = validate_generate_config({"presence_penalty": 2.0})
        assert errors_valid == []
        assert errors_low == []
        assert errors_high == []

        # Outside range
        errors_too_low = validate_generate_config({"presence_penalty": -3.0})
        errors_too_high = validate_generate_config({"presence_penalty": 3.0})
        assert len(errors_too_low) == 1
        assert len(errors_too_high) == 1

    def test_validate_frequency_penalty_range(self) -> None:
        """Validate should accept frequency_penalty in [-2.0, 2.0]."""
        errors_valid = validate_generate_config({"frequency_penalty": 0.5})
        assert errors_valid == []

        # Outside range
        errors_too_low = validate_generate_config({"frequency_penalty": -3.0})
        errors_too_high = validate_generate_config({"frequency_penalty": 3.0})
        assert len(errors_too_low) == 1
        assert len(errors_too_high) == 1

    def test_validate_max_output_tokens_must_be_positive(self) -> None:
        """Validate should reject max_output_tokens <= 0."""
        errors_zero = validate_generate_config({"max_output_tokens": 0})
        errors_negative = validate_generate_config({"max_output_tokens": -100})
        assert len(errors_zero) == 1
        assert len(errors_negative) == 1

        # Valid
        errors_valid = validate_generate_config({"max_output_tokens": 1024})
        assert errors_valid == []

    def test_validate_top_k_must_be_positive(self) -> None:
        """Validate should reject top_k <= 0."""
        errors_zero = validate_generate_config({"top_k": 0})
        errors_negative = validate_generate_config({"top_k": -10})
        assert len(errors_zero) == 1
        assert len(errors_negative) == 1

        # Valid
        errors_valid = validate_generate_config({"top_k": 40})
        assert errors_valid == []

    def test_validate_non_numeric_value(self) -> None:
        """Validate should reject non-numeric values."""
        errors = validate_generate_config({"temperature": "hot"})
        assert len(errors) == 1
        assert "number" in errors[0]


class TestConfigValidationError:
    """Unit tests for ConfigValidationError exception."""

    def test_config_validation_error_is_evolution_error(self) -> None:
        """ConfigValidationError should be subclass of EvolutionError."""
        from gepa_adk.domain.exceptions import EvolutionError

        error = ConfigValidationError("test")
        assert isinstance(error, EvolutionError)

    def test_config_validation_error_stores_errors(self) -> None:
        """ConfigValidationError should store errors list."""
        error = ConfigValidationError("failed", errors=["error1", "error2"])
        assert error.errors == ["error1", "error2"]

    def test_config_validation_error_str(self) -> None:
        """ConfigValidationError str should include errors."""
        error = ConfigValidationError("Config invalid", errors=["error1"])
        assert "error1" in str(error)

    def test_config_validation_error_empty_errors(self) -> None:
        """ConfigValidationError should handle empty errors list."""
        error = ConfigValidationError("test")
        assert error.errors == []

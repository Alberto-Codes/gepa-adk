"""Unit tests for domain type aliases and configuration types.

Tests verify that type aliases are properly defined and exported, and that
configuration dataclasses have correct defaults and immutability.
Type aliases don't have runtime behavior, but we test their existence
and documentation.
"""

import pytest

from gepa_adk.domain.types import ComponentName, ModelName, Score, TrajectoryConfig

pytestmark = pytest.mark.unit


class TestScore:
    """Tests for the Score type alias."""

    def test_score_is_float_alias(self) -> None:
        """Score type alias accepts float values."""
        score: Score = 0.85
        assert isinstance(score, float)

    def test_score_accepts_integer_coercion(self) -> None:
        """Score accepts integer values (coerced to float context)."""
        score: Score = 1
        assert score == 1.0

    def test_score_typical_range(self) -> None:
        """Score typically represents values in [0.0, 1.0]."""
        low: Score = 0.0
        high: Score = 1.0
        mid: Score = 0.5
        assert low <= mid <= high


class TestComponentName:
    """Tests for the ComponentName type alias."""

    def test_component_name_is_string_alias(self) -> None:
        """ComponentName type alias accepts string values."""
        name: ComponentName = "instruction"
        assert isinstance(name, str)

    def test_component_name_common_values(self) -> None:
        """ComponentName accepts common GEPA component names."""
        instruction: ComponentName = "instruction"
        output_schema: ComponentName = "output_schema"
        assert instruction == "instruction"
        assert output_schema == "output_schema"


class TestModelName:
    """Tests for the ModelName type alias."""

    def test_model_name_is_string_alias(self) -> None:
        """ModelName type alias accepts string values."""
        model: ModelName = "gemini-2.0-flash"
        assert isinstance(model, str)

    def test_model_name_common_values(self) -> None:
        """ModelName accepts common model identifier formats."""
        gemini: ModelName = "gemini-2.0-flash"
        gpt: ModelName = "gpt-4o"
        assert "gemini" in gemini
        assert "gpt" in gpt


class TestTypeAliasExports:
    """Tests for module-level exports."""

    def test_all_types_exported(self) -> None:
        """All type aliases are in __all__."""
        from gepa_adk.domain import types

        assert "Score" in types.__all__
        assert "ComponentName" in types.__all__
        assert "ModelName" in types.__all__
        assert "TrajectoryConfig" in types.__all__


class TestTrajectoryConfig:
    """Tests for the TrajectoryConfig dataclass."""

    def test_default_configuration(self) -> None:
        """TrajectoryConfig has sensible defaults for secure extraction."""
        config = TrajectoryConfig()

        assert config.include_tool_calls is True
        assert config.include_state_deltas is True
        assert config.include_token_usage is True
        assert config.redact_sensitive is True
        assert config.sensitive_keys == ("password", "api_key", "token")
        assert config.max_string_length == 10000

    def test_custom_configuration(self) -> None:
        """TrajectoryConfig accepts custom values for all fields."""
        config = TrajectoryConfig(
            include_tool_calls=False,
            include_state_deltas=False,
            include_token_usage=False,
            redact_sensitive=False,
            sensitive_keys=("custom_key",),
            max_string_length=5000,
        )

        assert config.include_tool_calls is False
        assert config.include_state_deltas is False
        assert config.include_token_usage is False
        assert config.redact_sensitive is False
        assert config.sensitive_keys == ("custom_key",)
        assert config.max_string_length == 5000

    def test_truncation_disabled_with_none(self) -> None:
        """TrajectoryConfig allows None to disable truncation."""
        config = TrajectoryConfig(max_string_length=None)

        assert config.max_string_length is None

    def test_config_is_frozen(self) -> None:
        """TrajectoryConfig is immutable (frozen dataclass)."""
        config = TrajectoryConfig()

        with pytest.raises(AttributeError, match="cannot assign to field"):
            config.include_tool_calls = False  # type: ignore[misc]

    def test_sensitive_keys_is_tuple(self) -> None:
        """TrajectoryConfig.sensitive_keys is tuple (immutable)."""
        config = TrajectoryConfig()

        assert isinstance(config.sensitive_keys, tuple)
        assert config.sensitive_keys == ("password", "api_key", "token")

    def test_custom_sensitive_keys(self) -> None:
        """TrajectoryConfig accepts custom sensitive key lists."""
        config = TrajectoryConfig(
            sensitive_keys=("password", "api_key", "token", "ssn", "credit_card"),
        )

        assert len(config.sensitive_keys) == 5
        assert "ssn" in config.sensitive_keys
        assert "credit_card" in config.sensitive_keys

"""Unit tests for domain type aliases and configuration types.

Tests verify that type aliases are properly defined and exported, and that
configuration dataclasses have correct defaults and immutability.
Type aliases don't have runtime behavior, but we test their existence
and documentation.
"""

import pytest

from gepa_adk.domain.types import (
    ComponentName,
    ComponentSpec,
    ModelName,
    QualifiedComponentName,
    Score,
    TrajectoryConfig,
)

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
        model: ModelName = "gemini-2.5-flash"
        assert isinstance(model, str)

    def test_model_name_common_values(self) -> None:
        """ModelName accepts common model identifier formats."""
        gemini: ModelName = "gemini-2.5-flash"
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
        assert "QualifiedComponentName" in types.__all__
        assert "ModelName" in types.__all__
        assert "TrajectoryConfig" in types.__all__
        assert "ComponentSpec" in types.__all__


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


class TestQualifiedComponentName:
    """Tests for the QualifiedComponentName NewType."""

    def test_construction_via_newtype(self) -> None:
        """QualifiedComponentName can be constructed via NewType wrapper."""
        name: QualifiedComponentName = QualifiedComponentName("generator.instruction")
        assert name == "generator.instruction"

    def test_runtime_behavior_as_str(self) -> None:
        """QualifiedComponentName behaves as str at runtime."""
        name: QualifiedComponentName = QualifiedComponentName("critic.output_schema")
        assert isinstance(name, str)
        assert name.startswith("critic")
        assert "." in name

    def test_string_operations(self) -> None:
        """QualifiedComponentName supports string operations."""
        name: QualifiedComponentName = QualifiedComponentName("agent.component")
        assert name.split(".") == ["agent", "component"]
        assert len(name) == 15


class TestComponentSpec:
    """Tests for the ComponentSpec dataclass."""

    def test_construction_with_valid_names(self) -> None:
        """ComponentSpec constructs with valid agent and component names."""
        spec = ComponentSpec(agent="generator", component="instruction")
        assert spec.agent == "generator"
        assert spec.component == "instruction"

    def test_qualified_property_returns_qualified_name(self) -> None:
        """ComponentSpec.qualified returns QualifiedComponentName."""
        spec = ComponentSpec(agent="generator", component="instruction")
        qualified = spec.qualified
        assert qualified == "generator.instruction"
        # At runtime it's a str (NewType is erased)
        assert isinstance(qualified, str)

    def test_qualified_with_underscore_component(self) -> None:
        """ComponentSpec.qualified handles components with underscores."""
        spec = ComponentSpec(agent="critic", component="output_schema")
        assert spec.qualified == "critic.output_schema"

        spec2 = ComponentSpec(agent="refiner", component="generate_content_config")
        assert spec2.qualified == "refiner.generate_content_config"

    def test_parse_valid_qualified_name(self) -> None:
        """ComponentSpec.parse parses valid qualified names."""
        spec = ComponentSpec.parse("critic.output_schema")
        assert spec.agent == "critic"
        assert spec.component == "output_schema"

    def test_parse_with_multiple_dots(self) -> None:
        """ComponentSpec.parse handles names with multiple dots."""
        # Only first dot is used as separator
        spec = ComponentSpec.parse("agent.component.with.dots")
        assert spec.agent == "agent"
        assert spec.component == "component.with.dots"

    def test_parse_missing_dot_raises_valueerror(self) -> None:
        """ComponentSpec.parse raises ValueError for names without dot."""
        with pytest.raises(ValueError, match="expected format 'agent.component'"):
            ComponentSpec.parse("nodot")

    def test_parse_empty_agent_raises_valueerror(self) -> None:
        """ComponentSpec.parse raises ValueError for empty agent."""
        with pytest.raises(
            ValueError, match="both agent and component must be non-empty"
        ):
            ComponentSpec.parse(".component")

    def test_parse_empty_component_raises_valueerror(self) -> None:
        """ComponentSpec.parse raises ValueError for empty component."""
        with pytest.raises(
            ValueError, match="both agent and component must be non-empty"
        ):
            ComponentSpec.parse("agent.")

    def test_str_representation(self) -> None:
        """ComponentSpec.__str__ returns qualified name."""
        spec = ComponentSpec(agent="generator", component="instruction")
        assert str(spec) == "generator.instruction"

    def test_immutability_frozen(self) -> None:
        """ComponentSpec is immutable (frozen dataclass)."""
        spec = ComponentSpec(agent="generator", component="instruction")
        with pytest.raises(AttributeError, match="cannot assign to field"):
            spec.agent = "other"  # type: ignore[misc]

    def test_equality(self) -> None:
        """ComponentSpec instances with same values are equal."""
        spec1 = ComponentSpec(agent="gen", component="inst")
        spec2 = ComponentSpec(agent="gen", component="inst")
        spec3 = ComponentSpec(agent="gen", component="other")
        assert spec1 == spec2
        assert spec1 != spec3

    def test_roundtrip_parse_qualified(self) -> None:
        """ComponentSpec can roundtrip through parse and qualified."""
        original = ComponentSpec(agent="generator", component="output_schema")
        qualified = original.qualified
        parsed = ComponentSpec.parse(qualified)
        assert parsed == original

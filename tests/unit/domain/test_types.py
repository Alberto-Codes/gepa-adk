"""Unit tests for domain type aliases.

Tests verify that type aliases are properly defined and exported.
Type aliases don't have runtime behavior, but we test their existence
and documentation.
"""

import pytest

from gepa_adk.domain.types import ComponentName, ModelName, Score


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
class TestTypeAliasExports:
    """Tests for module-level exports."""

    def test_all_types_exported(self) -> None:
        """All type aliases are in __all__."""
        from gepa_adk.domain import types

        assert "Score" in types.__all__
        assert "ComponentName" in types.__all__
        assert "ModelName" in types.__all__

"""Unit tests for domain type aliases."""

import pytest

from gepa_adk.domain.types import ComponentName, ModelName, Score


def test_score_type_alias():
    """Test Score type alias accepts float values."""
    score: Score = 0.85
    assert isinstance(score, float)
    assert score == 0.85


def test_component_name_type_alias():
    """Test ComponentName type alias accepts string values."""
    name: ComponentName = "instruction"
    assert isinstance(name, str)
    assert name == "instruction"


def test_model_name_type_alias():
    """Test ModelName type alias accepts string values."""
    model: ModelName = "gemini-2.0-flash"
    assert isinstance(model, str)
    assert model == "gemini-2.0-flash"


def test_type_aliases_are_runtime_compatible():
    """Test that type aliases work at runtime."""
    # Type aliases should not affect runtime behavior
    score: Score = 1.0
    component: ComponentName = "output_schema"
    model: ModelName = "gpt-4o"

    # Can assign to each other (they're all their base types)
    assert isinstance(score, float)
    assert isinstance(component, str)
    assert isinstance(model, str)

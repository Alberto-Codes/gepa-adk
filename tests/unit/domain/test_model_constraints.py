"""Unit tests for ModelConstraints dataclass.

These tests verify the ModelConstraints dataclass behavior including
construction, attribute access, immutability, and hashability.
"""

from __future__ import annotations

import pytest


class TestModelConstraintsBasics:
    """Unit tests for ModelConstraints basic functionality."""

    def test_create_empty_constraints(self) -> None:
        """Empty constraints should be valid."""
        from gepa_adk.domain.types import ModelConstraints

        constraints = ModelConstraints()
        assert constraints.allowed_models == ()

    def test_create_with_single_model(self) -> None:
        """Constraints with single model should work."""
        from gepa_adk.domain.types import ModelConstraints

        constraints = ModelConstraints(allowed_models=("gemini-2.0-flash",))
        assert constraints.allowed_models == ("gemini-2.0-flash",)

    def test_create_with_multiple_models(self) -> None:
        """Constraints with multiple models should work."""
        from gepa_adk.domain.types import ModelConstraints

        constraints = ModelConstraints(
            allowed_models=("gemini-2.0-flash", "gpt-4o", "claude-3-sonnet")
        )
        assert len(constraints.allowed_models) == 3
        assert "gemini-2.0-flash" in constraints.allowed_models
        assert "gpt-4o" in constraints.allowed_models
        assert "claude-3-sonnet" in constraints.allowed_models

    def test_equality(self) -> None:
        """Two ModelConstraints with same values should be equal."""
        from gepa_adk.domain.types import ModelConstraints

        c1 = ModelConstraints(allowed_models=("a", "b"))
        c2 = ModelConstraints(allowed_models=("a", "b"))
        assert c1 == c2

    def test_inequality(self) -> None:
        """Two ModelConstraints with different values should not be equal."""
        from gepa_adk.domain.types import ModelConstraints

        c1 = ModelConstraints(allowed_models=("a",))
        c2 = ModelConstraints(allowed_models=("b",))
        assert c1 != c2

    def test_order_matters_for_equality(self) -> None:
        """ModelConstraints with different order should not be equal."""
        from gepa_adk.domain.types import ModelConstraints

        c1 = ModelConstraints(allowed_models=("a", "b"))
        c2 = ModelConstraints(allowed_models=("b", "a"))
        assert c1 != c2


class TestModelConstraintsImmutability:
    """Tests for frozen dataclass immutability."""

    def test_cannot_modify_allowed_models(self) -> None:
        """allowed_models should be immutable (frozen dataclass)."""
        from gepa_adk.domain.types import ModelConstraints

        constraints = ModelConstraints(allowed_models=("model-a",))

        with pytest.raises(AttributeError):
            constraints.allowed_models = ("model-b",)  # type: ignore[misc]


class TestModelConstraintsTypeHints:
    """Tests for type hint correctness."""

    def test_allowed_models_is_tuple(self) -> None:
        """allowed_models should be a tuple, not a list."""
        from gepa_adk.domain.types import ModelConstraints

        constraints = ModelConstraints(allowed_models=("a", "b"))
        assert isinstance(constraints.allowed_models, tuple)


class TestModelConstraintsHashability:
    """Tests for hashability (tuple-only fields make it hashable)."""

    def test_is_hashable(self) -> None:
        """ModelConstraints should be hashable (tuple field only)."""
        from gepa_adk.domain.types import ModelConstraints

        constraints = ModelConstraints(allowed_models=("model-a", "model-b"))

        # Should not raise - can be used as dict key or in set
        hash_value = hash(constraints)
        assert isinstance(hash_value, int)

    def test_can_use_in_set(self) -> None:
        """ModelConstraints can be added to a set."""
        from gepa_adk.domain.types import ModelConstraints

        c1 = ModelConstraints(allowed_models=("a",))
        c2 = ModelConstraints(allowed_models=("b",))
        c3 = ModelConstraints(allowed_models=("a",))  # Same as c1

        constraint_set = {c1, c2, c3}
        assert len(constraint_set) == 2  # c1 and c3 are equal

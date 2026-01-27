"""Unit tests for model validation tools.

Tests the factory function that creates validation tools for model selection.
"""

from gepa_adk.utils.model_tools import create_validate_model_choice


class TestCreateValidateModelChoice:
    """Tests for create_validate_model_choice factory."""

    def test_creates_callable(self):
        """Factory returns a callable validation function."""
        validate_fn = create_validate_model_choice(
            allowed_models=("model-a", "model-b")
        )

        assert callable(validate_fn)

    def test_valid_model_returns_success(self):
        """Valid model returns valid=True response."""
        validate_fn = create_validate_model_choice(
            allowed_models=("gpt-4o", "claude-3-sonnet")
        )

        result = validate_fn("gpt-4o")

        assert result["valid"] is True
        assert result["model_name"] == "gpt-4o"

    def test_invalid_model_returns_failure(self):
        """Invalid model returns valid=False with error and allowed list."""
        validate_fn = create_validate_model_choice(
            allowed_models=("gpt-4o", "claude-3-sonnet")
        )

        result = validate_fn("invalid-model")

        assert result["valid"] is False
        assert "invalid-model" in result["error"]
        assert "allowed_models" in result
        assert "gpt-4o" in result["allowed_models"]
        assert "claude-3-sonnet" in result["allowed_models"]

    def test_strips_whitespace(self):
        """Validation strips whitespace from model name."""
        validate_fn = create_validate_model_choice(
            allowed_models=("gpt-4o",)
        )

        result = validate_fn("  gpt-4o  ")

        assert result["valid"] is True
        assert result["model_name"] == "gpt-4o"

    def test_case_sensitive(self):
        """Validation is case-sensitive."""
        validate_fn = create_validate_model_choice(
            allowed_models=("GPT-4o",)
        )

        result = validate_fn("gpt-4o")

        assert result["valid"] is False

    def test_empty_allowed_models_rejects_all(self):
        """Empty allowed_models tuple rejects all models."""
        validate_fn = create_validate_model_choice(allowed_models=())

        result = validate_fn("any-model")

        assert result["valid"] is False

    def test_function_has_docstring(self):
        """Returned function has docstring for LLM tooling."""
        validate_fn = create_validate_model_choice(
            allowed_models=("model-a",)
        )

        assert validate_fn.__doc__ is not None
        assert "validate" in validate_fn.__doc__.lower()

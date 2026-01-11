"""Unit tests for domain exceptions.

Tests verify exception hierarchy, message formatting, and context fields.
"""

import pytest

from gepa_adk.domain.exceptions import (
    AdapterError,
    ConfigurationError,
    EvaluationError,
    EvolutionError,
)


@pytest.mark.unit
class TestEvolutionError:
    """Tests for the base EvolutionError exception."""

    def test_evolution_error_is_exception(self) -> None:
        """EvolutionError inherits from Exception."""
        assert issubclass(EvolutionError, Exception)

    def test_evolution_error_with_message(self) -> None:
        """EvolutionError stores message correctly."""
        error = EvolutionError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_evolution_error_can_be_raised(self) -> None:
        """EvolutionError can be raised and caught."""
        with pytest.raises(EvolutionError) as exc_info:
            raise EvolutionError("Test error")
        assert "Test error" in str(exc_info.value)

    def test_evolution_error_can_catch_subclasses(self) -> None:
        """EvolutionError catch block catches ConfigurationError."""
        with pytest.raises(EvolutionError):
            raise ConfigurationError("Config error")


@pytest.mark.unit
class TestConfigurationError:
    """Tests for the ConfigurationError exception."""

    def test_configuration_error_inherits_evolution_error(self) -> None:
        """ConfigurationError is a subclass of EvolutionError."""
        assert issubclass(ConfigurationError, EvolutionError)

    def test_configuration_error_basic_message(self) -> None:
        """ConfigurationError with just a message."""
        error = ConfigurationError("Invalid value")
        assert "Invalid value" in str(error)

    def test_configuration_error_with_field(self) -> None:
        """ConfigurationError formats field in string representation."""
        error = ConfigurationError("Invalid value", field="max_iterations")
        assert "Invalid value" in str(error)
        assert "field='max_iterations'" in str(error)

    def test_configuration_error_with_field_and_value(self) -> None:
        """ConfigurationError formats field and value in string representation."""
        error = ConfigurationError(
            "max_iterations must be non-negative",
            field="max_iterations",
            value=-1,
        )
        result = str(error)
        assert "max_iterations must be non-negative" in result
        assert "field='max_iterations'" in result
        assert "value=-1" in result

    def test_configuration_error_with_all_context(self) -> None:
        """ConfigurationError stores all context fields."""
        error = ConfigurationError(
            "Validation failed",
            field="patience",
            value=-5,
            constraint="must be >= 0",
        )
        assert error.field == "patience"
        assert error.value == -5
        assert error.constraint == "must be >= 0"

    def test_configuration_error_context_is_keyword_only(self) -> None:
        """Context parameters are keyword-only."""
        # This should work - all keyword args
        error = ConfigurationError("msg", field="f", value=1)
        assert error.field == "f"

        # Positional args after message should fail at type check level
        # (not runtime since Python allows it, but type checker catches it)

    def test_configuration_error_can_be_raised_and_caught(self) -> None:
        """ConfigurationError can be raised and caught specifically."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Bad config", field="test")
        assert exc_info.value.field == "test"

    def test_configuration_error_with_none_values(self) -> None:
        """ConfigurationError handles None context values."""
        error = ConfigurationError("Error", field=None, value=None)
        # None values should not appear in string representation
        result = str(error)
        assert result == "Error"
        assert "field" not in result


@pytest.mark.unit
class TestEvaluationError:
    """Tests for the EvaluationError exception."""

    def test_evaluation_error_inherits_evolution_error(self) -> None:
        """EvaluationError is a subclass of EvolutionError."""
        assert issubclass(EvaluationError, EvolutionError)

    def test_evaluation_error_basic_message(self) -> None:
        """EvaluationError with just a message."""
        error = EvaluationError("Agent execution failed")
        assert "Agent execution failed" in str(error)

    def test_evaluation_error_with_cause(self) -> None:
        """EvaluationError stores and displays cause."""
        original = RuntimeError("Connection lost")
        error = EvaluationError("Agent execution failed", cause=original)
        assert error.cause is original
        assert "caused by: Connection lost" in str(error)

    def test_evaluation_error_with_context(self) -> None:
        """EvaluationError stores and displays context kwargs."""
        error = EvaluationError(
            "Agent execution failed",
            agent_name="my_agent",
            input_text="test input",
        )
        result = str(error)
        assert "agent_name='my_agent'" in result
        assert "input_text='test input'" in result

    def test_evaluation_error_with_cause_and_context(self) -> None:
        """EvaluationError formats both cause and context."""
        original = ValueError("Invalid response")
        error = EvaluationError(
            "Scoring failed",
            cause=original,
            agent_name="critic",
        )
        result = str(error)
        assert "Scoring failed" in result
        assert "agent_name='critic'" in result
        assert "caused by: Invalid response" in result

    def test_evaluation_error_context_is_keyword_only(self) -> None:
        """Context parameters are keyword-only after message."""
        error = EvaluationError("msg", cause=None, agent_name="test")
        assert error.context == {"agent_name": "test"}

    def test_evaluation_error_can_be_caught_as_evolution_error(self) -> None:
        """EvaluationError can be caught with EvolutionError handler."""
        with pytest.raises(EvolutionError):
            raise EvaluationError("Test")


@pytest.mark.unit
class TestAdapterError:
    """Tests for the AdapterError exception."""

    def test_adapter_error_inherits_evaluation_error(self) -> None:
        """AdapterError is a subclass of EvaluationError."""
        assert issubclass(AdapterError, EvaluationError)

    def test_adapter_error_inherits_evolution_error(self) -> None:
        """AdapterError is also a subclass of EvolutionError."""
        assert issubclass(AdapterError, EvolutionError)

    def test_adapter_error_basic_message(self) -> None:
        """AdapterError with just a message."""
        error = AdapterError("Session service unavailable")
        assert "Session service unavailable" in str(error)

    def test_adapter_error_with_context(self) -> None:
        """AdapterError stores and displays context kwargs."""
        error = AdapterError(
            "Session service unavailable",
            adapter="ADKAdapter",
            operation="evaluate",
        )
        result = str(error)
        assert "adapter='ADKAdapter'" in result
        assert "operation='evaluate'" in result

    def test_adapter_error_can_be_caught_as_evaluation_error(self) -> None:
        """AdapterError can be caught with EvaluationError handler."""
        with pytest.raises(EvaluationError):
            raise AdapterError("Test")

    def test_adapter_error_can_be_caught_as_evolution_error(self) -> None:
        """AdapterError can be caught with EvolutionError handler."""
        with pytest.raises(EvolutionError):
            raise AdapterError("Test")


@pytest.mark.unit
class TestExceptionExports:
    """Tests for module-level exports."""

    def test_all_exceptions_exported(self) -> None:
        """All exceptions are in __all__."""
        from gepa_adk.domain import exceptions

        assert "EvolutionError" in exceptions.__all__
        assert "ConfigurationError" in exceptions.__all__
        assert "EvaluationError" in exceptions.__all__
        assert "AdapterError" in exceptions.__all__

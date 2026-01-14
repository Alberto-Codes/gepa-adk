"""Unit tests for domain exceptions.

Tests verify exception hierarchy, message formatting, and context fields.
"""

import pytest

from gepa_adk.domain.exceptions import (
    AdapterError,
    ConfigurationError,
    EvaluationError,
    EvolutionError,
    MissingScoreFieldError,
    OutputParseError,
    SchemaValidationError,
    ScoringError,
)

pytestmark = pytest.mark.unit


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


class TestScoringError:
    """Tests for the ScoringError exception."""

    def test_scoring_error_inherits_evolution_error(self) -> None:
        """ScoringError is a subclass of EvolutionError."""
        assert issubclass(ScoringError, EvolutionError)

    def test_scoring_error_basic_message(self) -> None:
        """ScoringError with just a message."""
        error = ScoringError("Scoring failed")
        assert "Scoring failed" in str(error)

    def test_scoring_error_with_cause(self) -> None:
        """ScoringError stores and displays cause."""
        original = ValueError("Invalid score")
        error = ScoringError("Scoring failed", cause=original)
        assert error.cause is original
        assert "caused by: Invalid score" in str(error)


class TestOutputParseError:
    """Tests for the OutputParseError exception."""

    def test_output_parse_error_inherits_scoring_error(self) -> None:
        """OutputParseError is a subclass of ScoringError."""
        assert issubclass(OutputParseError, ScoringError)

    def test_output_parse_error_basic(self) -> None:
        """OutputParseError with required attributes."""
        error = OutputParseError(
            "Failed to parse JSON",
            raw_output="not json",
            parse_error="Expecting value",
        )
        assert error.raw_output == "not json"
        assert error.parse_error == "Expecting value"

    def test_output_parse_error_string_format(self) -> None:
        """OutputParseError formats attributes in string representation."""
        error = OutputParseError(
            "Failed to parse JSON",
            raw_output="invalid json here",
            parse_error="Expecting value: line 1 column 1",
        )
        result = str(error)
        assert "Failed to parse JSON" in result
        assert "parse_error=" in result
        assert "raw_output=" in result

    def test_output_parse_error_truncates_long_output(self) -> None:
        """OutputParseError truncates raw_output over 100 chars."""
        long_output = "x" * 150
        error = OutputParseError(
            "Parse failed",
            raw_output=long_output,
            parse_error="error",
        )
        result = str(error)
        assert "..." in result
        assert len(long_output) > 100  # Confirm output was long

    def test_output_parse_error_with_cause(self) -> None:
        """OutputParseError stores cause for exception chaining."""
        import json

        try:
            json.loads("not json")
        except json.JSONDecodeError as e:
            error = OutputParseError(
                "JSON parse failed",
                raw_output="not json",
                parse_error=str(e),
                cause=e,
            )
            assert error.cause is e

    def test_output_parse_error_can_be_caught_as_scoring_error(self) -> None:
        """OutputParseError can be caught with ScoringError handler."""
        with pytest.raises(ScoringError):
            raise OutputParseError(
                "Parse failed",
                raw_output="bad",
                parse_error="error",
            )


class TestSchemaValidationError:
    """Tests for the SchemaValidationError exception."""

    def test_schema_validation_error_inherits_scoring_error(self) -> None:
        """SchemaValidationError is a subclass of ScoringError."""
        assert issubclass(SchemaValidationError, ScoringError)

    def test_schema_validation_error_basic(self) -> None:
        """SchemaValidationError with required attributes."""
        error = SchemaValidationError(
            "Schema validation failed",
            raw_output='{"wrong": "fields"}',
            validation_error="Field required: score",
        )
        assert error.raw_output == '{"wrong": "fields"}'
        assert error.validation_error == "Field required: score"

    def test_schema_validation_error_string_format(self) -> None:
        """SchemaValidationError formats attributes in string representation."""
        error = SchemaValidationError(
            "Output does not match schema",
            raw_output='{"result": "value"}',
            validation_error="1 validation error for MySchema",
        )
        result = str(error)
        assert "Output does not match schema" in result
        assert "validation_error=" in result
        assert "raw_output=" in result

    def test_schema_validation_error_with_cause(self) -> None:
        """SchemaValidationError stores cause for exception chaining."""
        original = ValueError("Validation failed")
        error = SchemaValidationError(
            "Schema mismatch",
            raw_output="{}",
            validation_error="missing fields",
            cause=original,
        )
        assert error.cause is original
        assert "caused by: Validation failed" in str(error)

    def test_schema_validation_error_can_be_caught_as_scoring_error(self) -> None:
        """SchemaValidationError can be caught with ScoringError handler."""
        with pytest.raises(ScoringError):
            raise SchemaValidationError(
                "Validation failed",
                raw_output="{}",
                validation_error="error",
            )


class TestMissingScoreFieldError:
    """Tests for the MissingScoreFieldError exception."""

    def test_missing_score_field_error_inherits_scoring_error(self) -> None:
        """MissingScoreFieldError is a subclass of ScoringError."""
        assert issubclass(MissingScoreFieldError, ScoringError)

    def test_missing_score_field_error_basic(self) -> None:
        """MissingScoreFieldError with required attributes."""
        error = MissingScoreFieldError(
            "Score field is null",
            parsed_output={"result": "value", "feedback": "good"},
        )
        assert error.parsed_output == {"result": "value", "feedback": "good"}
        assert error.available_fields == ["result", "feedback"]

    def test_missing_score_field_error_string_format(self) -> None:
        """MissingScoreFieldError formats available_fields in string representation."""
        error = MissingScoreFieldError(
            "Missing score",
            parsed_output={"field1": 1, "field2": 2},
        )
        result = str(error)
        assert "Missing score" in result
        assert "available_fields=" in result

    def test_missing_score_field_error_can_be_caught_as_scoring_error(self) -> None:
        """MissingScoreFieldError can be caught with ScoringError handler."""
        with pytest.raises(ScoringError):
            raise MissingScoreFieldError(
                "No score",
                parsed_output={},
            )


class TestExceptionExports:
    """Tests for module-level exports."""

    def test_all_exceptions_exported(self) -> None:
        """All exceptions are in __all__."""
        from gepa_adk.domain import exceptions

        assert "EvolutionError" in exceptions.__all__
        assert "ConfigurationError" in exceptions.__all__
        assert "EvaluationError" in exceptions.__all__
        assert "AdapterError" in exceptions.__all__
        assert "ScoringError" in exceptions.__all__
        assert "OutputParseError" in exceptions.__all__
        assert "SchemaValidationError" in exceptions.__all__
        assert "MissingScoreFieldError" in exceptions.__all__

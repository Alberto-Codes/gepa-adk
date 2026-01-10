"""Unit tests for domain exceptions."""

import pytest

from gepa_adk.domain.exceptions import ConfigurationError, EvolutionError


def test_evolution_error_is_base_exception():
    """Test EvolutionError is the base exception."""
    error = EvolutionError("Test error")
    assert isinstance(error, Exception)
    assert str(error) == "Test error"


def test_configuration_error_inherits_from_evolution_error():
    """Test ConfigurationError inherits from EvolutionError."""
    error = ConfigurationError("Config failed")
    assert isinstance(error, EvolutionError)
    assert isinstance(error, Exception)


def test_configuration_error_with_field_context():
    """Test ConfigurationError stores field, value, and constraint."""
    error = ConfigurationError(
        message="max_iterations must be >= 0",
        field="max_iterations",
        value=-1,
        constraint=">= 0",
    )

    assert str(error) == "max_iterations must be >= 0"
    assert error.field == "max_iterations"
    assert error.value == -1
    assert error.constraint == ">= 0"


def test_configuration_error_with_partial_context():
    """Test ConfigurationError with only some context fields."""
    error = ConfigurationError(
        message="Invalid configuration",
        field="some_field",
    )

    assert str(error) == "Invalid configuration"
    assert error.field == "some_field"
    assert error.value is None
    assert error.constraint is None


def test_configuration_error_without_context():
    """Test ConfigurationError with just a message."""
    error = ConfigurationError("General configuration error")

    assert str(error) == "General configuration error"
    assert error.field is None
    assert error.value is None
    assert error.constraint is None


def test_configuration_error_can_be_caught_as_evolution_error():
    """Test ConfigurationError can be caught as EvolutionError."""
    with pytest.raises(EvolutionError):
        raise ConfigurationError("Test")


def test_configuration_error_can_be_caught_specifically():
    """Test ConfigurationError can be caught specifically."""
    with pytest.raises(ConfigurationError):
        raise ConfigurationError("Test")

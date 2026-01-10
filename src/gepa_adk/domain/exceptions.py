"""Exception hierarchy for domain layer.

Note: This module defines exceptions for validation and configuration errors.
"""


class EvolutionError(Exception):
    """Base exception for all gepa-adk errors.

    Note: All domain-level exceptions inherit from this base.
    """

    pass


class ConfigurationError(EvolutionError):
    """Raised when configuration validation fails.

    Attributes:
        field: The configuration field that failed validation.
        value: The invalid value provided.
        constraint: The constraint that was violated.

    Note: This exception is raised during configuration validation.
    """

    def __init__(
        self, message: str, field: str | None = None, value=None, constraint: str | None = None
    ):
        """Initialize the ConfigurationError.

        Args:
            message: Human-readable error message.
            field: The configuration field that failed validation.
            value: The invalid value provided.
            constraint: The constraint that was violated.

        Note: The field, value, and constraint are stored for debugging.
        """
        super().__init__(message)
        self.field = field
        self.value = value
        self.constraint = constraint

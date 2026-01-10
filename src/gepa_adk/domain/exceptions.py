"""Exception hierarchy for gepa-adk.

This module defines the exception hierarchy following ADR-009 guidelines.
All gepa-adk specific exceptions inherit from EvolutionError.

Attributes:
    EvolutionError (class): Base exception for all gepa-adk errors.
    ConfigurationError (class): Raised when configuration validation fails.

Examples:
    Handling configuration errors:

    ```python
    from gepa_adk.domain.exceptions import ConfigurationError

    try:
        raise ConfigurationError(
            "Invalid value", field="max_iterations", value=-1, constraint=">= 0"
        )
    except ConfigurationError as e:
        print(f"Field: {e.field}, Value: {e.value}")
    # Output: Field: max_iterations, Value: -1
    ```

Note:
    The exception hierarchy provides structured error handling with
    contextual information for debugging and error recovery.
"""


class EvolutionError(Exception):
    """Base exception for all gepa-adk errors.

    All custom exceptions in gepa-adk should inherit from this class
    to allow for unified exception handling.

    Examples:
        Catching evolution errors:

        ```python
        from gepa_adk.domain.exceptions import EvolutionError

        try:
            raise EvolutionError("Evolution failed unexpectedly")
        except EvolutionError as e:
            print(f"Caught: {e}")
        # Output: Caught: Evolution failed unexpectedly
        ```

    Note:
        Always use this base class or its subclasses for domain errors.
        Standard Python exceptions should still be raised for programming
        errors (e.g., TypeError, ValueError for developer mistakes).
    """


class ConfigurationError(EvolutionError):
    """Raised when configuration validation fails.

    This exception is raised during EvolutionConfig initialization
    when a parameter violates its validation constraints.

    Attributes:
        field: The name of the configuration field that failed validation.
        value: The invalid value that was provided.
        constraint: Description of the validation constraint that was violated.

    Examples:
        Creating a configuration error with context:

        ```python
        from gepa_adk.domain.exceptions import ConfigurationError

        error = ConfigurationError(
            "max_iterations must be non-negative",
            field="max_iterations",
            value=-5,
            constraint=">= 0",
        )
        print(error.field, error.value, error.constraint)
        # Output: max_iterations -5 >= 0
        ```

    Note:
        Configuration errors indicate user-provided invalid settings,
        not programming errors. They should be caught and reported
        with clear guidance on valid values.
    """

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        value: object = None,
        constraint: str | None = None,
    ) -> None:
        """Initialize ConfigurationError with context.

        Args:
            message: Human-readable error description.
            field: Name of the invalid configuration field.
            value: The invalid value provided.
            constraint: Description of the validation constraint.

        Note:
            Context fields are keyword-only to ensure explicit labeling
            and prevent positional argument mistakes.
        """
        super().__init__(message)
        self.field = field
        self.value = value
        self.constraint = constraint

    def __str__(self) -> str:
        """Return string representation with context.

        Returns:
            Formatted error message including field and value context.
        """
        base = super().__str__()
        context_parts = []
        if self.field is not None:
            context_parts.append(f"field={self.field!r}")
        if self.value is not None:
            context_parts.append(f"value={self.value!r}")
        if context_parts:
            return f"{base} [{', '.join(context_parts)}]"
        return base


__all__ = ["EvolutionError", "ConfigurationError"]

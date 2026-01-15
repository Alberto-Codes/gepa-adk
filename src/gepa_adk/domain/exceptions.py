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

from typing import Any


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
        field (str | None): The name of the configuration field that failed
            validation.
        value (object): The invalid value that was provided.
        constraint (str | None): Description of the validation constraint that
            was violated.

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
        Arises from user-provided invalid settings, not programming errors.
        Should be caught and reported with clear guidance on valid values.
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
            Context fields use keyword-only syntax to ensure explicit labeling
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


class NoCandidateAvailableError(EvolutionError):
    """Raised when no candidates are available for selection.

    Attributes:
        cause (Exception | None): Original exception that caused this error.
        context (dict[str, object]): Extra context (candidate_idx, frontier_type).

    Examples:
        ```python
        raise NoCandidateAvailableError(
            "No candidates available",
            frontier_type="instance",
        )
        ```
    """

    def __init__(
        self,
        message: str,
        *,
        cause: Exception | None = None,
        **context: object,
    ) -> None:
        """Initialize NoCandidateAvailableError with context.

        Args:
            message: Human-readable error description.
            cause: Original exception that caused this error.
            **context: Additional context such as candidate_idx or frontier_type.
        """
        super().__init__(message)
        self.cause = cause
        self.context = context

    def __str__(self) -> str:
        """Return string with context and cause details."""
        base = super().__str__()
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            base = f"{base} [{ctx_str}]"
        if self.cause:
            base = f"{base} (caused by: {self.cause})"
        return base


class EvaluationError(EvolutionError):
    """Raised when batch evaluation fails.

    This exception indicates failures during agent evaluation,
    such as agent execution errors, timeout, or malformed output.

    Attributes:
        cause (Exception | None): Original exception that caused this error.
        context (dict): Additional context for debugging.

    Examples:
        Wrapping an ADK error:

        ```python
        from gepa_adk.domain.exceptions import EvaluationError

        try:
            result = await runner.run_async(...)
        except ADKError as e:
            raise EvaluationError(
                "Agent execution failed",
                cause=e,
                agent_name="my_agent",
            ) from e
        ```

    Note:
        Always preserves the original cause for debugging while providing
        a consistent interface for error handling.
    """

    def __init__(
        self,
        message: str,
        *,
        cause: Exception | None = None,
        **context: object,
    ) -> None:
        """Initialize EvaluationError with cause and context.

        Args:
            message: Human-readable error description.
            cause: Original exception that caused this error.
            **context: Additional context for debugging (agent_name, etc.).

        Note:
            Context is passed via keyword arguments. Positional arguments
            after message are not allowed.
        """
        super().__init__(message)
        self.cause = cause
        self.context = context

    def __str__(self) -> str:
        """Return string with cause chain if present.

        Returns:
            Formatted message with context and cause information.
        """
        base = super().__str__()
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            base = f"{base} [{ctx_str}]"
        if self.cause:
            base = f"{base} (caused by: {self.cause})"
        return base


class AdapterError(EvaluationError):
    """Raised when an adapter operation fails.

    This exception is used by adapter implementations (e.g., ADKAdapter)
    for adapter-specific failures such as session errors or configuration
    issues.

    Examples:
        Raising an adapter error:

        ```python
        from gepa_adk.domain.exceptions import AdapterError

        if not self._session_service:
            raise AdapterError(
                "Session service unavailable",
                adapter="ADKAdapter",
                operation="evaluate",
            )
        ```

    Note:
        AdapterError is a subclass of EvaluationError, so callers can
        catch either for different granularity of error handling.
    """


class ScoringError(EvolutionError):
    """Base exception for all scoring-related errors.

    All scoring exceptions inherit from this class to allow for unified
    exception handling in scoring operations.

    Attributes:
        cause (Exception | None): Original exception that caused this error.

    Examples:
        Catching scoring errors:

        ```python
        from gepa_adk.domain.exceptions import ScoringError

        try:
            score, metadata = await scorer.async_score(...)
        except ScoringError as e:
            print(f"Scoring failed: {e}")
        ```

    Note:
        All scoring exceptions inherit from this base class.
        ScoringError extends EvolutionError, following ADR-009 exception
        hierarchy guidelines.
    """

    def __init__(
        self,
        message: str,
        *,
        cause: Exception | None = None,
    ) -> None:
        """Initialize ScoringError with message and optional cause.

        Args:
            message: Human-readable error description.
            cause: Original exception that caused this error.
        """
        super().__init__(message)
        self.cause = cause

    def __str__(self) -> str:
        """Return string with cause chain if present.

        Returns:
            Formatted message with cause information.
        """
        base = super().__str__()
        if self.cause:
            base = f"{base} (caused by: {self.cause})"
        return base


class CriticOutputParseError(ScoringError):
    """Raised when critic agent output cannot be parsed as valid JSON.

    This exception indicates that the critic agent returned output that
    could not be parsed as JSON or did not conform to the expected schema.

    Attributes:
        raw_output (str): The unparseable output from critic.
        parse_error (str): Description of parsing failure.

    Examples:
        Handling parse errors:

        ```python
        from gepa_adk.domain.exceptions import CriticOutputParseError

        try:
            score, metadata = await scorer.async_score(...)
        except CriticOutputParseError as e:
            print(f"Invalid JSON: {e.raw_output}")
            print(f"Error: {e.parse_error}")
        ```

    Note:
        Arises when critic agent output cannot be parsed as valid JSON.
        Typically occurs when LLM output doesn't follow structured format
        despite output_schema being set.
    """

    def __init__(
        self,
        message: str,
        *,
        raw_output: str,
        parse_error: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize CriticOutputParseError with context.

        Args:
            message: Human-readable error description.
            raw_output: The unparseable output string from critic.
            parse_error: Description of the parsing failure.
            cause: Original exception that caused this error.
        """
        super().__init__(message, cause=cause)
        self.raw_output = raw_output
        self.parse_error = parse_error

    def __str__(self) -> str:
        """Return string with parse error details.

        Returns:
            Formatted message including parse error and raw output preview.
        """
        base = super().__str__()
        output_preview = (
            self.raw_output[:100] + "..."
            if len(self.raw_output) > 100
            else self.raw_output
        )
        return (
            f"{base} [parse_error={self.parse_error!r}, raw_output={output_preview!r}]"
        )


class OutputParseError(ScoringError):
    """Raised when agent output cannot be parsed as valid JSON.

    This exception indicates that the agent returned output that
    could not be parsed as JSON.

    Attributes:
        raw_output (str): The unparseable output from agent.
        parse_error (str): Description of parsing failure.

    Examples:
        Handling parse errors:

        ```python
        from gepa_adk.domain.exceptions import OutputParseError

        try:
            score, metadata = scorer.score(input_text, output)
        except OutputParseError as e:
            print(f"Invalid JSON: {e.raw_output[:50]}")
            print(f"Error: {e.parse_error}")
        ```

    Note:
        Arises when agent output cannot be parsed as valid JSON.
        Typically occurs when LLM output doesn't follow structured format.
    """

    def __init__(
        self,
        message: str,
        *,
        raw_output: str,
        parse_error: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize OutputParseError with context.

        Args:
            message: Human-readable error description.
            raw_output: The unparseable output string from agent.
            parse_error: Description of the parsing failure.
            cause: Original exception that caused this error.
        """
        super().__init__(message, cause=cause)
        self.raw_output = raw_output
        self.parse_error = parse_error

    def __str__(self) -> str:
        """Return string with parse error details.

        Returns:
            Formatted message including parse error and raw output preview.
        """
        base = super().__str__()
        output_preview = (
            self.raw_output[:100] + "..."
            if len(self.raw_output) > 100
            else self.raw_output
        )
        return (
            f"{base} [parse_error={self.parse_error!r}, raw_output={output_preview!r}]"
        )


class SchemaValidationError(ScoringError):
    """Raised when output fails Pydantic schema validation.

    This exception indicates that the agent output was valid JSON but
    did not conform to the expected Pydantic schema.

    Attributes:
        raw_output (str): The output that failed validation.
        validation_error (str): Description of validation failure.

    Examples:
        Handling schema validation errors:

        ```python
        from gepa_adk.domain.exceptions import SchemaValidationError

        try:
            score, metadata = scorer.score(input_text, output)
        except SchemaValidationError as e:
            print(f"Schema mismatch: {e.validation_error}")
        ```

    Note:
        Arises when output is valid JSON but doesn't match the schema.
        Typically occurs when field types are wrong or required fields
        have invalid values.
    """

    def __init__(
        self,
        message: str,
        *,
        raw_output: str,
        validation_error: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize SchemaValidationError with context.

        Args:
            message: Human-readable error description.
            raw_output: The output string that failed validation.
            validation_error: Description of the validation failure.
            cause: Original exception that caused this error.
        """
        super().__init__(message, cause=cause)
        self.raw_output = raw_output
        self.validation_error = validation_error

    def __str__(self) -> str:
        """Return string with validation error details.

        Returns:
            Formatted message including validation error details.
        """
        base = super().__str__()
        output_preview = (
            self.raw_output[:100] + "..."
            if len(self.raw_output) > 100
            else self.raw_output
        )
        return f"{base} [validation_error={self.validation_error!r}, raw_output={output_preview!r}]"


class MissingScoreFieldError(ScoringError):
    """Raised when score field is missing or null in parsed output.

    This exception indicates that the output was successfully parsed
    and validated, but the required `score` field is missing or null.

    Attributes:
        parsed_output (dict[str, Any]): The parsed output without valid score.
        available_fields (list[str]): Fields that were present.

    Examples:
        Handling missing score field:

        ```python
        from gepa_adk.domain.exceptions import MissingScoreFieldError

        try:
            score, metadata = await scorer.async_score(...)
        except MissingScoreFieldError as e:
            print(f"Missing score. Available fields: {e.available_fields}")
        ```

    Note:
        Applies when parsed output lacks a valid score value.
        The parsed_output may contain other valid fields that will be
        preserved in metadata if score is found.
    """

    def __init__(
        self,
        message: str,
        *,
        parsed_output: dict[str, Any],
        cause: Exception | None = None,
    ) -> None:
        """Initialize MissingScoreFieldError with parsed output.

        Args:
            message: Human-readable error description.
            parsed_output: The parsed dict without valid score field.
            cause: Original exception that caused this error.
        """
        super().__init__(message, cause=cause)
        self.parsed_output = parsed_output
        self.available_fields = list(parsed_output.keys())

    def __str__(self) -> str:
        """Return string with available fields.

        Returns:
            Formatted message including list of available fields.
        """
        base = super().__str__()
        return f"{base} [available_fields={self.available_fields}]"


class MultiAgentValidationError(EvolutionError):
    """Raised when multi-agent configuration validation fails.

    This exception is raised during MultiAgentAdapter initialization
    when a parameter violates its validation constraints.

    Attributes:
        field (str): The name of the configuration field that failed
            validation.
        value (object): The invalid value that was provided.
        constraint (str): Description of the validation constraint that
            was violated.

    Examples:
        Creating a multi-agent validation error:

        ```python
        from gepa_adk.domain.exceptions import MultiAgentValidationError

        error = MultiAgentValidationError(
            "agents list cannot be empty",
            field="agents",
            value=[],
            constraint="len >= 1",
        )
        print(error.field, error.value)  # agents []
        ```

    Note:
        Arises from user-provided invalid multi-agent settings, not
        programming errors. Should be caught and reported with clear
        guidance on valid values.
    """

    def __init__(
        self,
        message: str,
        *,
        field: str,
        value: object,
        constraint: str,
    ) -> None:
        """Initialize MultiAgentValidationError with context.

        Args:
            message: Human-readable error description.
            field: Name of the invalid configuration field.
            value: The invalid value provided.
            constraint: Description of the validation constraint.

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling
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
        return (
            f"{base} [field={self.field!r}, value={self.value!r}, "
            f"constraint={self.constraint!r}]"
        )


class WorkflowEvolutionError(EvolutionError):
    """Raised when workflow evolution fails.

    This exception is raised during workflow evolution when the workflow
    structure is invalid or no evolvable agents are found.

    Attributes:
        workflow_name (str | None): Name of the workflow that failed.
        cause (Exception | None): Original exception that caused this error.

    Examples:
        Handling workflow evolution errors:

        ```python
        from gepa_adk.domain.exceptions import WorkflowEvolutionError

        try:
            result = await evolve_workflow(workflow=empty_workflow, trainset=trainset)
        except WorkflowEvolutionError as e:
            print(f"Workflow '{e.workflow_name}' failed: {e}")
        ```

    Note:
        Arises when workflow contains no LlmAgents or evolution fails
        during execution. Follows ADR-009 exception hierarchy.
    """

    def __init__(
        self,
        message: str,
        *,
        workflow_name: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize WorkflowEvolutionError with context.

        Args:
            message: Human-readable error description.
            workflow_name: Name of the workflow that failed.
            cause: Original exception that caused this error.

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling
            and prevent positional argument mistakes.
        """
        super().__init__(message)
        self.workflow_name = workflow_name
        self.cause = cause

    def __str__(self) -> str:
        """Return string with cause chain if present.

        Returns:
            Formatted message with workflow name and cause information.

        Note:
            Outputs formatted error message including workflow context when
            available. Preserves cause chain for debugging nested exceptions.
        """
        base = super().__str__()
        if self.workflow_name:
            base = f"{base} [workflow_name={self.workflow_name!r}]"
        if self.cause:
            base = f"{base} (caused by: {self.cause})"
        return base


class InvalidScoreListError(EvolutionError):
    """Raised when score list is empty or contains non-finite values.

    This exception is raised during acceptance score aggregation when the
    evaluation batch scores are empty or contain NaN/inf values that would
    invalidate acceptance decisions.

    Attributes:
        scores (list[float]): The invalid score list that caused the error.
        reason (str): Description of why the scores are invalid ("empty" or
            "non-finite").

    Examples:
        Handling invalid score lists:

        ```python
        from gepa_adk.domain.exceptions import InvalidScoreListError

        try:
            acceptance_score = aggregate_scores(scores)
        except InvalidScoreListError as e:
            print(f"Invalid scores: {e.reason}, scores: {e.scores}")
        ```

    Note:
        Arises when evaluation batch scores cannot be aggregated for acceptance.
        Empty batches or non-finite values would corrupt evolution decisions.
    """

    def __init__(
        self,
        message: str,
        *,
        scores: list[float],
        reason: str,
    ) -> None:
        """Initialize InvalidScoreListError with context.

        Args:
            message: Human-readable error description.
            scores: The invalid score list.
            reason: Why the scores are invalid ("empty" or "non-finite").

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling.
        """
        super().__init__(message)
        self.scores = scores
        self.reason = reason

    def __str__(self) -> str:
        """Return string with score list and reason.

        Returns:
            Formatted message including reason and score list preview.
        """
        base = super().__str__()
        score_preview = (
            str(self.scores[:5]) + "..." if len(self.scores) > 5 else str(self.scores)
        )
        return f"{base} [reason={self.reason!r}, scores={score_preview}]"


__all__ = [
    "EvolutionError",
    "ConfigurationError",
    "NoCandidateAvailableError",
    "EvaluationError",
    "AdapterError",
    "ScoringError",
    "CriticOutputParseError",
    "OutputParseError",
    "SchemaValidationError",
    "MissingScoreFieldError",
    "MultiAgentValidationError",
    "WorkflowEvolutionError",
    "InvalidScoreListError",
]

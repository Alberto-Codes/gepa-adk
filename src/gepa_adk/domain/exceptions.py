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

See Also:
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: Domain models that
        raise these exceptions during validation.
    - [`gepa_adk.ports.adapter`][gepa_adk.ports.adapter]: Adapter protocol whose
        implementations raise EvaluationError and AdapterError.
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

        Note:
            Outputs formatted error message with field and value context
            when available, preserving base message structure.
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

    Note:
        Arises when candidate selector cannot find any valid candidates
        from the Pareto frontier, typically due to empty frontier or
        filtering constraints.
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

        Other Parameters:
            **context: Arbitrary key-value pairs stored as exception attributes
                for debugging context.

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling
            and prevent positional argument mistakes.
        """
        super().__init__(message)
        self.cause = cause
        self.context = context

    def __str__(self) -> str:
        """Return string with context and cause details.

        Returns:
            Formatted error message including context and cause information.

        Note:
            Outputs formatted error message with context dict and cause chain
            when available, preserving base message structure.
        """
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

        Other Parameters:
            **context: Arbitrary key-value pairs stored as exception attributes
                for debugging context.

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

        Note:
            Outputs formatted error message with context dict and cause chain
            when available, preserving base message structure.
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


class RestoreError(AdapterError):
    """Raised when agent restoration fails after evaluation.

    This exception is raised when one or more agent components fail to
    restore to their original state after candidate evaluation. Uses
    best-effort restoration: all components are attempted even if some fail,
    then errors are aggregated into this exception.

    Attributes:
        errors (list[tuple[str, Exception]]): List of (qualified_name, exception)
            pairs for each failed restoration.

    Examples:
        Handling partial restore failures:

        ```python
        from gepa_adk.domain.exceptions import RestoreError

        try:
            adapter._restore_agents(originals)
        except RestoreError as e:
            for qualified_name, error in e.errors:
                print(f"Failed to restore {qualified_name}: {error}")
        ```

        Aggregating restoration failures:

        ```python
        errors = []
        for name, original in originals.items():
            try:
                handler.restore(agent, original)
            except Exception as exc:
                errors.append((name, exc))
        if errors:
            raise RestoreError(
                f"Failed to restore {len(errors)} components",
                errors=errors,
            )
        ```

    Note:
        As a subclass of AdapterError, this exception indicates that the
        agent state may be corrupted and manual intervention may be required
        to reset agents to a known state.
    """

    def __init__(
        self,
        message: str,
        *,
        errors: list[tuple[str, Exception]],
        cause: Exception | None = None,
    ) -> None:
        """Initialize RestoreError with aggregated failures.

        Args:
            message: Human-readable error summary.
            errors: List of (qualified_name, exception) pairs for each failed
                restoration. Must be non-empty when raising this exception.
            cause: Optional underlying cause exception.

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling
            and prevent positional argument mistakes.
        """
        super().__init__(message, cause=cause)
        self.errors = errors

    def __str__(self) -> str:
        """Return string with failed component names.

        Returns:
            Formatted message including list of failed qualified names.

        Note:
            Outputs formatted error message with list of failed qualified
            names, preserving base message structure.
        """
        base = super().__str__()
        failed_names = [name for name, _ in self.errors]
        return f"{base} [failed_components={failed_names}]"


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

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling
            and prevent positional argument mistakes.
        """
        super().__init__(message)
        self.cause = cause

    def __str__(self) -> str:
        """Return string with cause chain if present.

        Returns:
            Formatted message with cause information.

        Note:
            Outputs formatted error message with cause chain when available,
            preserving base message structure.
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

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling
            and prevent positional argument mistakes.
        """
        super().__init__(message, cause=cause)
        self.raw_output = raw_output
        self.parse_error = parse_error

    def __str__(self) -> str:
        """Return string with parse error details.

        Returns:
            Formatted message including parse error and raw output preview.

        Note:
            Outputs formatted error message with parse error and raw output
            preview (truncated to 100 chars), preserving base message structure.
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

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling
            and prevent positional argument mistakes.
        """
        super().__init__(message, cause=cause)
        self.raw_output = raw_output
        self.parse_error = parse_error

    def __str__(self) -> str:
        """Return string with parse error details.

        Returns:
            Formatted message including parse error and raw output preview.

        Note:
            Outputs formatted error message with parse error and raw output
            preview (truncated to 100 chars), preserving base message structure.
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
    did not conform to the expected Pydantic schema. Also used for
    schema text validation during output schema evolution.

    Attributes:
        raw_output (str): The output that failed validation.
        validation_error (str): Description of validation failure.
        line_number (int | None): Line number where error occurred (for syntax errors).
        validation_stage (str | None): Stage where validation failed
            ("syntax", "structure", or "execution").

    Examples:
        Handling schema validation errors:

        ```python
        from gepa_adk.domain.exceptions import SchemaValidationError

        try:
            score, metadata = scorer.score(input_text, output)
        except SchemaValidationError as e:
            print(f"Schema mismatch: {e.validation_error}")
            if e.line_number:
                print(f"Error at line {e.line_number}")
        ```

    Note:
        Arises when output is valid JSON but doesn't match the schema.
        Typically occurs when field types are wrong or required fields
        have invalid values. For schema evolution, also raised when
        proposed schema text is syntactically invalid or structurally
        incorrect (e.g., missing BaseModel inheritance).
    """

    def __init__(
        self,
        message: str,
        *,
        raw_output: str,
        validation_error: str,
        cause: Exception | None = None,
        line_number: int | None = None,
        validation_stage: str | None = None,
    ) -> None:
        """Initialize SchemaValidationError with context.

        Args:
            message: Human-readable error description.
            raw_output: The output string that failed validation.
            validation_error: Description of the validation failure.
            cause: Original exception that caused this error.
            line_number: Line number where error occurred (for syntax errors).
            validation_stage: Stage where validation failed. One of:
                - "syntax": Python syntax error
                - "structure": Missing BaseModel, has imports/functions
                - "execution": Error during exec()

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling
            and prevent positional argument mistakes.
        """
        super().__init__(message, cause=cause)
        self.raw_output = raw_output
        self.validation_error = validation_error
        self.line_number = line_number
        self.validation_stage = validation_stage

    def __str__(self) -> str:
        """Return string with validation error details.

        Returns:
            Formatted message including validation error details.

        Note:
            Outputs formatted error message with validation error and raw output
            preview (truncated to 100 chars), preserving base message structure.
        """
        base = super().__str__()
        output_preview = (
            self.raw_output[:100] + "..."
            if len(self.raw_output) > 100
            else self.raw_output
        )
        parts = [f"validation_error={self.validation_error!r}"]
        if self.line_number is not None:
            parts.append(f"line={self.line_number}")
        if self.validation_stage is not None:
            parts.append(f"stage={self.validation_stage!r}")
        parts.append(f"raw_output={output_preview!r}")
        return f"{base} [{', '.join(parts)}]"


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

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling
            and prevent positional argument mistakes.
        """
        super().__init__(message, cause=cause)
        self.parsed_output = parsed_output
        self.available_fields = list(parsed_output.keys())

    def __str__(self) -> str:
        """Return string with available fields.

        Returns:
            Formatted message including list of available fields.

        Note:
            Outputs formatted error message with list of available fields
            from parsed output, preserving base message structure.
        """
        base = super().__str__()
        return f"{base} [available_fields={self.available_fields}]"


class VideoValidationError(ConfigurationError):
    """Raised when video file validation fails.

    This exception is raised during video file processing when a video
    file does not exist, exceeds size limits, or has an invalid MIME type.

    Attributes:
        video_path (str): The path to the video file that failed validation.
        field (str): The configuration field name (default "video").
        constraint (str): Description of the validation constraint that was violated.

    Examples:
        Raising a video validation error:

        ```python
        from gepa_adk.domain.exceptions import VideoValidationError

        raise VideoValidationError(
            "Video file not found",
            video_path="/path/to/missing.mp4",
            constraint="file must exist",
        )
        ```

        Handling video validation errors:

        ```python
        from gepa_adk.domain.exceptions import VideoValidationError

        try:
            await video_service.prepare_video_parts(["/bad/path.mp4"])
        except VideoValidationError as e:
            print(f"Invalid video: {e.video_path}")
            print(f"Constraint violated: {e.constraint}")
        ```

    Note:
        Arises from video file validation failures during multimodal input
        processing. File existence, size limits (2GB), and MIME type
        (video/*) are validated before loading video content.
    """

    def __init__(
        self,
        message: str,
        *,
        video_path: str,
        field: str = "video",
        constraint: str,
    ) -> None:
        """Initialize VideoValidationError with video file context.

        Args:
            message: Human-readable error description.
            video_path: The path to the video file that failed validation.
            field: Name of the configuration field (default "video").
            constraint: Description of the validation constraint violated.

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling
            and prevent positional argument mistakes.
        """
        super().__init__(message, field=field, value=video_path, constraint=constraint)
        self.video_path = video_path

    def __str__(self) -> str:
        """Return string representation with video path context.

        Returns:
            Formatted error message including video_path and constraint.

        Note:
            Outputs formatted error message with video_path for easy
            identification of the problematic file in error logs.
        """
        base = Exception.__str__(self)
        return (
            f"{base} [video_path={self.video_path!r}, constraint={self.constraint!r}]"
        )


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

        Note:
            Outputs formatted error message with field, value, and constraint
            context when available, preserving base message structure.
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


class ConfigValidationError(EvolutionError):
    """Raised when config validation fails.

    This exception is raised during generate_content_config evolution
    when a proposed config contains invalid parameter values or malformed YAML.

    Attributes:
        message (str): Human-readable error message.
        errors (list[str]): List of individual validation errors.

    Examples:
        Creating a config validation error:

        ```python
        from gepa_adk.domain.exceptions import ConfigValidationError

        error = ConfigValidationError(
            "Config validation failed",
            errors=["temperature must be 0.0-2.0, got 3.0"],
        )
        print(error.errors)  # ["temperature must be 0.0-2.0, got 3.0"]
        ```

    Note:
        Arises when proposed config values violate parameter constraints
        or when YAML parsing fails. Should be caught and logged as a warning,
        with the original config preserved.
    """

    def __init__(
        self,
        message: str,
        *,
        errors: list[str] | None = None,
    ) -> None:
        """Initialize ConfigValidationError with context.

        Args:
            message: Human-readable error description.
            errors: List of individual validation errors.

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling
            and prevent positional argument mistakes.
        """
        super().__init__(message)
        self.errors = errors or []

    def __str__(self) -> str:
        """Return string representation with errors.

        Returns:
            Formatted error message including list of validation errors.

        Note:
            Outputs formatted error message with validation errors list
            when available, preserving base message structure.
        """
        base = super().__str__()
        if self.errors:
            return f"{base} [errors={self.errors}]"
        return base


class InvalidScoreListError(ScoringError):
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
        cause: Exception | None = None,
    ) -> None:
        """Initialize InvalidScoreListError with context.

        Args:
            message: Human-readable error description.
            scores: The invalid score list.
            reason: Why the scores are invalid ("empty" or "non-finite").
            cause: Original exception that caused this error.

        Note:
            Context fields use keyword-only syntax to ensure explicit labeling.
        """
        super().__init__(message, cause=cause)
        self.scores = scores
        self.reason = reason

    def __str__(self) -> str:
        """Return string with score list and reason.

        Returns:
            Formatted message including reason and score list preview.

        Note:
            Outputs formatted error message with reason and score list preview
            (first 5 scores), preserving base message structure.
        """
        base = super().__str__()
        score_preview = (
            str(self.scores[:5]) + "..." if len(self.scores) > 5 else str(self.scores)
        )
        return f"{base} [reason={self.reason!r}, scores={score_preview}]"


__all__ = [
    "EvolutionError",
    "ConfigurationError",
    "ConfigValidationError",
    "NoCandidateAvailableError",
    "EvaluationError",
    "AdapterError",
    "RestoreError",
    "ScoringError",
    "CriticOutputParseError",
    "OutputParseError",
    "SchemaValidationError",
    "MissingScoreFieldError",
    "MultiAgentValidationError",
    "VideoValidationError",
    "WorkflowEvolutionError",
    "InvalidScoreListError",
]

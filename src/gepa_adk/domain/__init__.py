"""Domain layer for gepa-adk evolution engine.

This module exports the core domain models for the GEPA-ADK evolution engine.

Attributes:
    EvolutionConfig (class): Configuration parameters for evolution runs.
    EvolutionResult (class): Outcome of a completed evolution run.
    Candidate (class): Instruction candidate being evolved.
    IterationRecord (class): Metrics for a single evolution iteration.
    TokenRollup (class): Token usage summed over evaluated rows.
    Score (type): Type alias for normalized scores.
    ComponentName (type): Type alias for component identifiers.
    ModelName (type): Type alias for model identifiers.
    TrajectoryConfig (class): Configuration for trajectory extraction.
    StopReason (enum): Why an evolution run terminated.
    OnIterationCallback (type): Callback invoked after each iteration.
    ProposalValidator (type): Check run on each proposed component text.
    DEFAULT_SENSITIVE_KEYS (tuple): Default keys for trajectory redaction.
    CURRENT_SCHEMA_VERSION (int): Current result schema version.
    EvolutionError (class): Base exception for all gepa-adk errors.
    ConfigurationError (class): Raised when configuration validation fails.
    EvaluationError (class): Raised when batch evaluation fails.
    AdapterError (class): Raised when adapter operations fail.
    EmptyProposalError (class): Raised when reflection stays empty after
        one retry.
    ReflectionTimeoutError (class): Raised when the reflection agent exceeds
        its timeout.
    IncompleteProposalError (class): Raised when the reflection output was
        cut off or opens a reasoning tag it never closes.
    ReflectionError (class): Raised when the reflection function raises;
        retryable errors are skipped, others abort the run.
    MultiAgentEvolutionResult (class): Outcome of a completed multi-agent evolution run.
    ParetoState (class): Tracks evolution state for Pareto-aware selection.
    ParetoFrontier (class): Tracks non-dominated candidates across multiple frontier
        dimensions.
    StopperState (class): Immutable snapshot of evolution state for stopper decisions.
    ADKTrajectory (class): Execution trace from ADK agent evaluation.
    MultiAgentTrajectory (class): Execution trace from multi-agent pipeline evaluation.
    ToolCallRecord (class): Record of a single tool call during agent execution.
    TokenUsage (class): Token usage statistics from LLM calls.
    COMPONENT_INSTRUCTION (str): Name of the instruction component.
    COMPONENT_OUTPUT_SCHEMA (str): Name of the output schema component.
    COMPONENT_GENERATE_CONFIG (str): Name of the generate_content_config component.
    DEFAULT_COMPONENT_NAME (str): Component evolved when none is named
        (``instruction``).
    FrontierType (Enum): Supported frontier tracking strategies for Pareto selection.
    MultiAgentCandidate (type): Mapping of qualified component names to their text.
    MergeAttempt (type): Merged candidate with its parent and ancestor indices, or None.
    AncestorLog (type): Parent and ancestor indices of an attempted merge.
    SchemaConstraints (class): Constraints for output schema evolution.
    ScoringError (class): Base exception for all scoring-related errors.
    CriticOutputParseError (class): Raised when critic agent output cannot be parsed as
        valid JSON.
    MissingScoreFieldError (class): Raised when score field is missing or null in parsed
        output.
    MultiAgentValidationError (class): Raised when multi-agent configuration validation
        fails.
    NoCandidateAvailableError (class): Raised when no candidates are available for
        selection.
    VideoValidationError (class): Raised when video file validation fails.

Examples:
    Basic usage with configuration and records:

    ```python
    from gepa_adk.domain import EvolutionConfig, IterationRecord

    config = EvolutionConfig(max_iterations=20)
    record = IterationRecord(
        iteration_number=1,
        score=0.85,
        component_text="Test",
        evolved_component="instruction",
        accepted=True,
    )
    ```

See Also:
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: Core dataclass implementations.
    - [`gepa_adk.domain.types`][gepa_adk.domain.types]: Type aliases for domain concepts.
    - [`gepa_adk.domain.exceptions`][gepa_adk.domain.exceptions]: Exception hierarchy.

Notes:
    This package contains pure domain logic with no external dependencies.
    All models follow hexagonal architecture principles (ADR-000).
"""

from gepa_adk.domain.exceptions import (
    AdapterError,
    ConfigurationError,
    CriticOutputParseError,
    EmptyProposalError,
    EvaluationError,
    EvolutionError,
    IncompleteProposalError,
    MissingScoreFieldError,
    MultiAgentValidationError,
    NoCandidateAvailableError,
    ReflectionError,
    ReflectionTimeoutError,
    ScoringError,
    VideoValidationError,
)
from gepa_adk.domain.models import (
    CURRENT_SCHEMA_VERSION,
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    IterationRecord,
    MultiAgentEvolutionResult,
    TokenRollup,
)
from gepa_adk.domain.state import ParetoFrontier, ParetoState
from gepa_adk.domain.stopper import StopperState
from gepa_adk.domain.trajectory import (
    ADKTrajectory,
    MultiAgentTrajectory,
    TokenUsage,
    ToolCallRecord,
)
from gepa_adk.domain.types import (
    COMPONENT_GENERATE_CONFIG,
    COMPONENT_INSTRUCTION,
    COMPONENT_OUTPUT_SCHEMA,
    DEFAULT_COMPONENT_NAME,
    DEFAULT_SENSITIVE_KEYS,
    AncestorLog,
    ComponentName,
    FrontierType,
    MergeAttempt,
    ModelName,
    MultiAgentCandidate,
    OnIterationCallback,
    ProposalValidator,
    SchemaConstraints,
    Score,
    StopReason,
    TrajectoryConfig,
)

__all__ = [  # noqa: RUF022  # grouped by layer under section comments
    # Models
    "CURRENT_SCHEMA_VERSION",
    "EvolutionConfig",
    "EvolutionResult",
    "Candidate",
    "IterationRecord",
    "TokenRollup",
    "MultiAgentEvolutionResult",
    "ParetoState",
    "ParetoFrontier",
    "StopperState",
    # Trajectory types
    "ADKTrajectory",
    "MultiAgentTrajectory",
    "ToolCallRecord",
    "TokenUsage",
    # Types
    "Score",
    "ComponentName",
    "COMPONENT_INSTRUCTION",
    "COMPONENT_OUTPUT_SCHEMA",
    "COMPONENT_GENERATE_CONFIG",
    "DEFAULT_COMPONENT_NAME",
    "DEFAULT_SENSITIVE_KEYS",
    "FrontierType",
    "StopReason",
    "OnIterationCallback",
    "ProposalValidator",
    "ModelName",
    "TrajectoryConfig",
    "MultiAgentCandidate",
    "MergeAttempt",
    "AncestorLog",
    "SchemaConstraints",
    # Exceptions
    "EvolutionError",
    "ConfigurationError",
    "EvaluationError",
    "AdapterError",
    "ScoringError",
    "CriticOutputParseError",
    "MissingScoreFieldError",
    "MultiAgentValidationError",
    "NoCandidateAvailableError",
    "EmptyProposalError",
    "ReflectionTimeoutError",
    "IncompleteProposalError",
    "ReflectionError",
    "VideoValidationError",
]

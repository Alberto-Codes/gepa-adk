"""Domain layer for gepa-adk evolution engine.

This module exports the core domain models for the GEPA-ADK evolution engine.

Attributes:
    EvolutionConfig (class): Configuration parameters for evolution runs.
    EvolutionResult (class): Outcome of a completed evolution run.
    Candidate (class): Instruction candidate being evolved.
    IterationRecord (class): Metrics for a single evolution iteration.
    Score (type): Type alias for normalized scores.
    ComponentName (type): Type alias for component identifiers.
    ModelName (type): Type alias for model identifiers.
    TrajectoryConfig (class): Configuration for trajectory extraction.
    StopReason (enum): Why an evolution run terminated.
    CURRENT_SCHEMA_VERSION (int): Current result schema version.
    EvolutionError (class): Base exception for all gepa-adk errors.
    ConfigurationError (class): Raised when configuration validation fails.
    EvaluationError (class): Raised when batch evaluation fails.
    AdapterError (class): Raised when adapter operations fail.

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

Note:
    This package contains pure domain logic with no external dependencies.
    All models follow hexagonal architecture principles (ADR-000).
"""

from gepa_adk.domain.exceptions import (
    AdapterError,
    ConfigurationError,
    CriticOutputParseError,
    EvaluationError,
    EvolutionError,
    MissingScoreFieldError,
    MultiAgentValidationError,
    NoCandidateAvailableError,
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
    AncestorLog,
    ComponentName,
    FrontierType,
    MergeAttempt,
    ModelName,
    MultiAgentCandidate,
    SchemaConstraints,
    Score,
    StopReason,
    TrajectoryConfig,
)

__all__ = [
    # Models
    "CURRENT_SCHEMA_VERSION",
    "EvolutionConfig",
    "EvolutionResult",
    "Candidate",
    "IterationRecord",
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
    "FrontierType",
    "StopReason",
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
    "VideoValidationError",
]

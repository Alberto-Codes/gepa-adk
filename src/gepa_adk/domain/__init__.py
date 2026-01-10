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
    EvolutionError (class): Base exception for all gepa-adk errors.
    ConfigurationError (class): Raised when configuration validation fails.

Examples:
    Basic usage with configuration and records:

    ```python
    from gepa_adk.domain import EvolutionConfig, IterationRecord

    config = EvolutionConfig(max_iterations=20)
    record = IterationRecord(
        iteration_number=1, score=0.85, instruction="Test", accepted=True
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

from gepa_adk.domain.exceptions import ConfigurationError, EvolutionError
from gepa_adk.domain.models import (
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    IterationRecord,
)
from gepa_adk.domain.types import ComponentName, ModelName, Score

__all__ = [
    # Models
    "EvolutionConfig",
    "EvolutionResult",
    "Candidate",
    "IterationRecord",
    # Types
    "Score",
    "ComponentName",
    "ModelName",
    # Exceptions
    "EvolutionError",
    "ConfigurationError",
]

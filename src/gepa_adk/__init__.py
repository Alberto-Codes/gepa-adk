"""GEPA-ADK: Async-first evolution engine for agentic development.

This package provides domain models and utilities for evolving agent
instructions using the GEPA (Generalized Evolutionary Prompt-programming
Architecture) approach.

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
    AsyncGEPAAdapter (protocol): Async adapter protocol for evaluation.
    EvaluationBatch (class): Evaluation results container for adapters.
    DataInst (type): Type variable for adapter input instances.
    Trajectory (type): Type variable for adapter traces.
    RolloutOutput (type): Type variable for adapter outputs.

Examples:
    Basic usage with configuration and candidates:

    ```python
    from gepa_adk import EvolutionConfig, Candidate

    config = EvolutionConfig(max_iterations=10, patience=3)
    candidate = Candidate(components={"instruction": "Be helpful"})
    ```

See Also:
    - [`gepa_adk.domain`][gepa_adk.domain]: Core domain layer with models and types.
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: Detailed model implementations.
    - [`gepa_adk.domain.exceptions`][gepa_adk.domain.exceptions]: Exception hierarchy.

Note:
    This is the main entry point for the gepa-adk package. Domain models
    are re-exported here for convenient top-level access.
"""

from gepa_adk.domain import (
    Candidate,
    ComponentName,
    ConfigurationError,
    EvolutionConfig,
    EvolutionError,
    EvolutionResult,
    IterationRecord,
    ModelName,
    Score,
)
from gepa_adk.ports import (
    AsyncGEPAAdapter,
    DataInst,
    EvaluationBatch,
    RolloutOutput,
    Trajectory,
)

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
    # Ports
    "AsyncGEPAAdapter",
    "EvaluationBatch",
    "DataInst",
    "Trajectory",
    "RolloutOutput",
]


def main() -> None:
    """Entry point for CLI invocation."""
    print("Hello from gepa-adk!")

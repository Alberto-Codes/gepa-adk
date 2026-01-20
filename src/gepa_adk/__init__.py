"""GEPA-ADK: Async-first evolution engine for agentic development.

This package provides domain models and utilities for evolving agent
instructions using the GEPA (Generalized Evolutionary Prompt-programming
Architecture) approach.

Attributes:
    __version__ (str): Package version from pyproject.toml.
    EvolutionConfig (class): Configuration parameters for evolution runs.
    EvolutionResult (class): Outcome of a completed evolution run.
    Candidate (class): Instruction candidate being evolved.
    IterationRecord (class): Metrics for a single evolution iteration.
    Score (type): Type alias for normalized scores.
    ComponentName (type): Type alias for component identifiers.
    ModelName (type): Type alias for model identifiers.
    TrajectoryConfig (class): Configuration for trajectory extraction.
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

    Configuring trajectory extraction:

    ```python
    from gepa_adk import TrajectoryConfig

    trajectory_config = TrajectoryConfig(
        redact_sensitive=True,
        max_string_length=5000,
    )
    ```

See Also:
    - [`gepa_adk.domain`][gepa_adk.domain]: Core domain layer with models and types.
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: Detailed model implementations.
    - [`gepa_adk.domain.exceptions`][gepa_adk.domain.exceptions]: Exception hierarchy.

Note:
    This is the main entry point for the gepa-adk package. Domain models
    are re-exported here for convenient top-level access.
"""

# Suppress Pydantic serializer warnings from ADK/LiteLLM dependencies
# These are upstream issues (GH #81) and don't affect functionality
import warnings

warnings.filterwarnings(
    "ignore",
    message=".*Pydantic.*serializer.*",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*Pydantic.*serialization.*",
    category=UserWarning,
)

# Version is read from installed package metadata
try:
    from importlib.metadata import version as _get_version

    __version__ = _get_version("gepa-adk")
except Exception:
    # Fallback for development environments where package isn't installed
    __version__ = "0.0.0.dev"

from gepa_adk.adapters.component_selector import (  # noqa: E402
    AllComponentSelector,
    RoundRobinComponentSelector,
    create_component_selector,
)
from gepa_adk.adapters.critic_scorer import (  # noqa: E402
    ADVANCED_CRITIC_INSTRUCTION,
    SIMPLE_CRITIC_INSTRUCTION,
    CriticOutput,
    SimpleCriticOutput,
    normalize_feedback,
)
from gepa_adk.api import (  # noqa: E402
    evolve,
    evolve_group,
    evolve_sync,
    evolve_workflow,
)
from gepa_adk.domain import (  # noqa: E402
    DEFAULT_COMPONENT_NAME,
    Candidate,
    ComponentName,
    ConfigurationError,
    EvolutionConfig,
    EvolutionError,
    EvolutionResult,
    FrontierType,
    IterationRecord,
    ModelName,
    MultiAgentEvolutionResult,
    Score,
    TrajectoryConfig,
)
from gepa_adk.engine import AsyncGEPAEngine, MergeProposer  # noqa: E402
from gepa_adk.ports import (  # noqa: E402
    AsyncGEPAAdapter,
    DataInst,
    EvaluationBatch,
    RolloutOutput,
    Trajectory,
)
from gepa_adk.ports.selector import ComponentSelectorProtocol  # noqa: E402

__all__ = [
    # Version
    "__version__",
    # Models
    "EvolutionConfig",
    "EvolutionResult",
    "MultiAgentEvolutionResult",
    "Candidate",
    "IterationRecord",
    # Types
    "Score",
    "ComponentName",
    "DEFAULT_COMPONENT_NAME",
    "ModelName",
    "FrontierType",
    "TrajectoryConfig",
    # Exceptions
    "EvolutionError",
    "ConfigurationError",
    # Engine
    "AsyncGEPAEngine",
    "MergeProposer",
    # Ports
    "AsyncGEPAAdapter",
    "EvaluationBatch",
    "DataInst",
    "Trajectory",
    "RolloutOutput",
    # Selectors
    "ComponentSelectorProtocol",
    "RoundRobinComponentSelector",
    "AllComponentSelector",
    "create_component_selector",
    # Critic schemas and helpers
    "SimpleCriticOutput",
    "CriticOutput",
    "SIMPLE_CRITIC_INSTRUCTION",
    "ADVANCED_CRITIC_INSTRUCTION",
    "normalize_feedback",
    # API
    "evolve",
    "evolve_sync",
    "evolve_group",
    "evolve_workflow",
]


def main() -> None:
    """Entry point for CLI invocation."""
    print("Hello from gepa-adk!")

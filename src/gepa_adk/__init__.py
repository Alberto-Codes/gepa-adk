"""GEPA-ADK: Async-first evolution engine for agentic development.

This package provides domain models and utilities for evolving agent
instructions using the GEPA (Generalized Evolutionary Prompt-programming
Architecture) approach.

Attributes:
    __version__ (str): Package version from pyproject.toml.
    EvolutionConfig (class): Configuration parameters for evolution runs.
    EvolutionResult (class): Outcome of a completed evolution run.
    MultiAgentEvolutionResult (class): Outcome of a multi-agent evolution run.
    Candidate (class): Instruction candidate being evolved.
    IterationRecord (class): Metrics for a single evolution iteration.
    Score (type): Type alias for normalized scores.
    ComponentName (type): Type alias for component identifiers.
    DEFAULT_COMPONENT_NAME (str): Default component name constant.
    ModelName (type): Type alias for model identifiers.
    StopReason (enum): Why an evolution run terminated.
    FrontierType (enum): Pareto frontier type selector.
    CURRENT_SCHEMA_VERSION (int): Current result schema version.
    TrajectoryConfig (class): Configuration for trajectory extraction.
    SchemaConstraints (class): Schema-level field constraints for evolution.
    EvolutionError (class): Base exception for all gepa-adk errors.
    ConfigurationError (class): Raised when configuration validation fails.
    VideoValidationError (class): Raised for invalid video input.
    AsyncGEPAEngine (class): Core async evolution engine.
    MergeProposer (class): Proposes merged candidates from the Pareto frontier.
    AsyncGEPAAdapter (protocol): Async adapter protocol for evaluation.
    EvaluationBatch (class): Evaluation results container for adapters.
    DataInst (type): Type variable for adapter input instances.
    Trajectory (type): Type variable for adapter traces.
    RolloutOutput (type): Type variable for adapter outputs.
    ComponentSelectorProtocol (protocol): Protocol for component selection.
    RoundRobinComponentSelector (class): Round-robin component selector.
    AllComponentSelector (class): Selector that returns all components.
    create_component_selector (function): Factory for component selectors.
    SimpleCriticOutput (class): Pydantic schema for simple critic output.
    CriticOutput (class): Pydantic schema for advanced critic output.
    SIMPLE_CRITIC_INSTRUCTION (str): Default simple critic instruction.
    ADVANCED_CRITIC_INSTRUCTION (str): Default advanced critic instruction.
    STRUCTURED_OUTPUT_CRITIC_INSTRUCTION (str): Preset instruction for structure evaluation.
    ACCURACY_CRITIC_INSTRUCTION (str): Preset instruction for factual accuracy evaluation.
    RELEVANCE_CRITIC_INSTRUCTION (str): Preset instruction for relevance evaluation.
    normalize_feedback (function): Normalize critic feedback to standard form.
    create_critic (function): Factory for pre-configured critic agents by preset name.
    critic_presets (dict): Maps preset name to human-readable description.
    evolve (function): Async single-agent evolution entry point.
    evolve_sync (function): Deprecated synchronous wrapper for evolve().
    evolve_group (function): Async multi-agent group evolution.
    evolve_workflow (function): Async workflow-level evolution.
    run_sync (function): Universal sync wrapper for any async evolution call.

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

from gepa_adk.adapters.scoring.critic_scorer import (  # noqa: E402
    ACCURACY_CRITIC_INSTRUCTION,
    ADVANCED_CRITIC_INSTRUCTION,
    RELEVANCE_CRITIC_INSTRUCTION,
    SIMPLE_CRITIC_INSTRUCTION,
    STRUCTURED_OUTPUT_CRITIC_INSTRUCTION,
    CriticOutput,
    SimpleCriticOutput,
    create_critic,
    critic_presets,
    normalize_feedback,
)
from gepa_adk.adapters.selection.component_selector import (  # noqa: E402
    AllComponentSelector,
    RoundRobinComponentSelector,
    create_component_selector,
)
from gepa_adk.api import (  # noqa: E402
    evolve,
    evolve_group,
    evolve_sync,
    evolve_workflow,
    run_sync,
)
from gepa_adk.domain import (  # noqa: E402
    CURRENT_SCHEMA_VERSION,
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
    SchemaConstraints,
    Score,
    StopReason,
    TrajectoryConfig,
    VideoValidationError,
)
from gepa_adk.engine import AsyncGEPAEngine, MergeProposer  # noqa: E402
from gepa_adk.ports import (  # noqa: E402
    AsyncGEPAAdapter,
    DataInst,
    EvaluationBatch,
    RolloutOutput,
    Trajectory,
)
from gepa_adk.ports.component_selector import ComponentSelectorProtocol  # noqa: E402

__all__ = [
    # Version
    "__version__",
    # Models
    "CURRENT_SCHEMA_VERSION",
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
    "StopReason",
    "TrajectoryConfig",
    "SchemaConstraints",
    # Exceptions
    "EvolutionError",
    "ConfigurationError",
    "VideoValidationError",
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
    "STRUCTURED_OUTPUT_CRITIC_INSTRUCTION",
    "ACCURACY_CRITIC_INSTRUCTION",
    "RELEVANCE_CRITIC_INSTRUCTION",
    "normalize_feedback",
    "create_critic",
    "critic_presets",
    # API
    "evolve",
    "evolve_sync",
    "evolve_group",
    "evolve_workflow",
    "run_sync",
]


def main() -> None:
    """Entry point for CLI invocation."""
    print("Hello from gepa-adk!")

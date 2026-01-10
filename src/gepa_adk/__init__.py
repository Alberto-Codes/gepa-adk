"""gepa-adk: Evolutionary optimization for Google ADK agents.

This package provides domain models and tools for evolving AI agent
instructions through genetic-pareto optimization.

Note: Main entry point for the gepa-adk package.
"""

# Export domain models for top-level access
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

__all__ = [
    "EvolutionConfig",
    "EvolutionResult",
    "IterationRecord",
    "Candidate",
    "EvolutionError",
    "ConfigurationError",
    "Score",
    "ComponentName",
    "ModelName",
]


def main() -> None:
    """Main entry point for CLI.

    Note: Placeholder for future CLI implementation.
    """
    print("Hello from gepa-adk!")

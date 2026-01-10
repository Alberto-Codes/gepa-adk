"""GEPA-ADK: Async-first evolution engine for agentic development.

This package provides domain models and utilities for evolving agent
instructions using the GEPA (Generalized Evolutionary Prompt-programming
Architecture) approach.

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


def main() -> None:
    """Entry point for CLI invocation."""
    print("Hello from gepa-adk!")

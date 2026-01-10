"""Domain layer for gepa-adk evolution engine.

This module exports core domain models, types, and exceptions.

Note: This module provides the public API for the domain layer.
"""

from gepa_adk.domain.exceptions import ConfigurationError, EvolutionError
from gepa_adk.domain.models import Candidate, EvolutionConfig, EvolutionResult, IterationRecord
from gepa_adk.domain.types import ComponentName, ModelName, Score

__all__ = [
    "EvolutionError",
    "ConfigurationError",
    "Score",
    "ComponentName",
    "ModelName",
    "EvolutionConfig",
    "IterationRecord",
    "EvolutionResult",
    "Candidate",
]

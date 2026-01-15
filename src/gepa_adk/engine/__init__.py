"""Async evolution engine for gepa-adk.

This module provides the AsyncGEPAEngine class that orchestrates the
core evolution loop for optimizing agent instructions using the GEPA
algorithm with async support.

Attributes:
    AsyncGEPAEngine (class): Main evolution engine class.

Examples:
    Basic usage:

    ```python
    from gepa_adk.engine import AsyncGEPAEngine
    from gepa_adk.domain.models import EvolutionConfig, Candidate

    engine = AsyncGEPAEngine(
        adapter=my_adapter,
        config=EvolutionConfig(max_iterations=50),
        initial_candidate=Candidate(components={"instruction": "Be helpful"}),
        batch=training_data,
    )
    result = await engine.run()
    ```

See Also:
    - [`gepa_adk.ports.adapter.AsyncGEPAAdapter`][gepa_adk.ports.adapter.AsyncGEPAAdapter]:
      Protocol for adapters.
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: Domain models used by the engine.
"""

from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.engine.genealogy import (
    detect_component_divergence,
    filter_ancestors_by_score,
    find_common_ancestor,
    get_ancestors,
    has_desirable_predictors,
)
from gepa_adk.engine.merge_proposer import MergeProposer
from gepa_adk.engine.proposer import (
    SESSION_STATE_KEYS,
    AsyncReflectiveMutationProposer,
    ReflectionFn,
    create_adk_reflection_fn,
)

__all__ = [
    "AsyncGEPAEngine",
    "AsyncReflectiveMutationProposer",
    "ReflectionFn",
    "SESSION_STATE_KEYS",
    "create_adk_reflection_fn",
    "get_ancestors",
    "find_common_ancestor",
    "filter_ancestors_by_score",
    "detect_component_divergence",
    "has_desirable_predictors",
    "MergeProposer",
]

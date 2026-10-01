"""Async evolution engine for gepa-adk.

This package provides the AsyncGEPAEngine class that orchestrates the
core evolution loop, along with mutation proposers, merge proposers,
genealogy utilities, and ADK reflection helpers.

Attributes:
    AsyncGEPAEngine (class): Main evolution engine class.
    AsyncReflectiveMutationProposer (class): Mutation proposer using LLM reflection.
    MergeProposer (class): Proposer for merging Pareto-optimal candidates.
    ReflectionFn (type): Type alias for reflection callables.
    create_adk_reflection_fn (function): Factory for ADK-based reflection functions.
    is_length_stop (function): Whether a finish reason marks output cut off
        at the token limit.
    REFLECTION_INSTRUCTION (str): Default reflection instruction template.
    SESSION_STATE_KEYS (dict): Session state keys the reflection agent reads.
    detect_component_divergence (function): Detect which components have diverged from
        ancestor to parent.
    filter_ancestors_by_score (function): Filter ancestors by minimum average score
        constraint.
    find_common_ancestor (function): Find the most recent common ancestor of two
        candidates.
    get_ancestors (function): Return all ancestor indices for a candidate.
    has_desirable_predictors (function): Check if merge has desirable complementary
        component changes.

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
    - [`AsyncGEPAAdapter`][gepa_adk.ports.adapter.AsyncGEPAAdapter]:
      Protocol for adapters.
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: Domain models used by the engine.
"""

from gepa_adk.domain.types import REFLECTION_INSTRUCTION, SESSION_STATE_KEYS
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn, is_length_stop
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
    AsyncReflectiveMutationProposer,
    ReflectionFn,
)

__all__ = [
    "REFLECTION_INSTRUCTION",
    "SESSION_STATE_KEYS",
    "AsyncGEPAEngine",
    "AsyncReflectiveMutationProposer",
    "MergeProposer",
    "ReflectionFn",
    "create_adk_reflection_fn",
    "detect_component_divergence",
    "filter_ancestors_by_score",
    "find_common_ancestor",
    "get_ancestors",
    "has_desirable_predictors",
    "is_length_stop",
]

"""Factory fixtures for domain model test objects.

Provides ``make_iteration_record``, ``make_evolution_result``, and
``make_multiagent_result`` factories that return valid instances with
sensible defaults. Accept ``**overrides`` for customization.

Attributes:
    pytestmark: Not set — conftest is auto-loaded by pytest.

Examples:
    Using factories in tests:

    ```python
    def test_score(make_iteration_record):
        record = make_iteration_record(score=0.99)
        assert record.score == 0.99


    def test_result(make_evolution_result):
        result = make_evolution_result(final_score=0.95)
        assert result.improved
    ```

See Also:
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: Source definitions.

Note:
    Fixtures are session-scoped factories — each call produces a fresh
    instance. Override any field via keyword arguments.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from gepa_adk.domain.models import (
    EvolutionResult,
    IterationRecord,
    MultiAgentEvolutionResult,
)


@pytest.fixture
def make_iteration_record() -> Callable[..., IterationRecord]:
    """Factory for IterationRecord with sensible defaults.

    Returns:
        Callable that creates IterationRecord instances.

    Examples:
        ```python
        def test_accepted(make_iteration_record):
            r = make_iteration_record(accepted=True)
            assert r.accepted
        ```

    Note:
        Defaults produce a valid accepted record at iteration 1.
    """

    def _factory(**overrides: Any) -> IterationRecord:
        defaults: dict[str, Any] = {
            "iteration_number": 1,
            "score": 0.85,
            "component_text": "Be helpful",
            "evolved_component": "instruction",
            "accepted": True,
        }
        defaults.update(overrides)
        return IterationRecord(**defaults)

    return _factory


@pytest.fixture
def make_evolution_result(
    make_iteration_record: Callable[..., IterationRecord],
) -> Callable[..., EvolutionResult]:
    """Factory for EvolutionResult with sensible defaults.

    Args:
        make_iteration_record: Iteration record factory fixture.

    Returns:
        Callable that creates EvolutionResult instances.

    Examples:
        ```python
        def test_improved(make_evolution_result):
            r = make_evolution_result(original_score=0.5, final_score=0.9)
            assert r.improved
        ```

    Note:
        Defaults produce a result that shows improvement (0.60 → 0.85).
        Includes one default iteration record.
    """

    def _factory(**overrides: Any) -> EvolutionResult:
        defaults: dict[str, Any] = {
            "original_score": 0.60,
            "final_score": 0.85,
            "evolved_components": {"instruction": "Be helpful"},
            "iteration_history": [make_iteration_record()],
            "total_iterations": 1,
        }
        defaults.update(overrides)
        return EvolutionResult(**defaults)

    return _factory


@pytest.fixture
def make_multiagent_result(
    make_iteration_record: Callable[..., IterationRecord],
) -> Callable[..., MultiAgentEvolutionResult]:
    """Factory for MultiAgentEvolutionResult with sensible defaults.

    Args:
        make_iteration_record: Iteration record factory fixture.

    Returns:
        Callable that creates MultiAgentEvolutionResult instances.

    Examples:
        ```python
        def test_agents(make_multiagent_result):
            r = make_multiagent_result(primary_agent="writer")
            assert r.primary_agent == "writer"
        ```

    Note:
        Defaults produce a result with generator/critic agents showing
        improvement (0.60 → 0.85).
    """

    def _factory(**overrides: Any) -> MultiAgentEvolutionResult:
        defaults: dict[str, Any] = {
            "evolved_components": {
                "generator": "Generate high-quality code",
                "critic": "Review code thoroughly",
            },
            "original_score": 0.60,
            "final_score": 0.85,
            "primary_agent": "generator",
            "iteration_history": [make_iteration_record()],
            "total_iterations": 1,
        }
        defaults.update(overrides)
        return MultiAgentEvolutionResult(**defaults)

    return _factory

"""Acceptance tests for the schema-validation skip path.

A proposal whose ``output_schema`` text fails validation is recorded in the
iteration history with ``skip_reason="schema_validation_failed"``, counts
toward stagnation, and the loop re-checks the stop conditions before it
continues, so a run whose every proposal is invalid ends by
``max_iterations`` or ``patience`` instead of looping until the reflector
happens to return a valid schema.

Notes:
    The adapter is the configurable mock from ``tests/fixtures/adapters.py``
    with a ``custom_propose`` that always returns invalid schema text, so
    no agent or LLM runs.

Examples:
    Run this module alone:

    ```bash
    uv run pytest tests/unit/engine/test_schema_validation_skip.py -q
    ```

See Also:
    [`tests.unit.engine.test_schema_validation_skip_stopper`][]: The custom
        ``stop_callbacks`` case.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig, IterationRecord
from gepa_adk.engine import AsyncGEPAEngine
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.unit

_VALID_SCHEMA = (
    "from pydantic import BaseModel\n\n\nclass Answer(BaseModel):\n    text: str\n"
)
_INVALID_SCHEMA = "class Answer(BaseModel:\n    text: str  # ünclosed paren\n"


async def _propose_invalid_schema(
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components: list[str],
) -> dict[str, str]:
    """Return an output_schema that cannot be validated.

    Args:
        candidate: Parent component texts (unused).
        reflective_dataset: Reflection examples (unused).
        components: Components to update (unused).

    Returns:
        A proposal whose ``output_schema`` is syntactically invalid.
    """
    return {"output_schema": _INVALID_SCHEMA}


async def _run(
    *, max_iterations: int, patience: int, on_iteration: Any = None
) -> tuple[Any, Any]:
    adapter = create_mock_adapter(
        default_score=0.5, custom_propose=_propose_invalid_schema
    )
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=max_iterations,
            patience=patience,
            min_improvement_threshold=0.0,
            on_iteration=on_iteration,
        ),
        initial_candidate=Candidate(
            components={"instruction": "seed", "output_schema": _VALID_SCHEMA}
        ),
        batch=[{"input": "q1"}, {"input": "qü"}],
    )
    result = await engine.run()
    return adapter, result


class TestSchemaValidationSkipEndsTheRun:
    """Invalid proposals cannot keep the loop alive past its stop conditions.

    Examples:
        ```bash
        uv run pytest tests/unit/engine/test_schema_validation_skip.py -q
        ```
    """

    @pytest.mark.asyncio
    async def test_ends_by_max_iterations(self) -> None:
        """Three invalid proposals end the run after three iterations with the seed."""
        adapter, result = await _run(max_iterations=3, patience=10)

        assert result.total_iterations == 3
        assert len(result.iteration_history) == 3
        assert [r.skip_reason for r in result.iteration_history] == [
            "schema_validation_failed"
        ] * 3
        assert all(r.accepted is False for r in result.iteration_history)
        assert all(r.score == 0.0 for r in result.iteration_history)
        assert all(
            r.evolved_component == "output_schema" for r in result.iteration_history
        )
        assert all(
            r.component_text == _INVALID_SCHEMA for r in result.iteration_history
        )
        assert all(r.failed_evaluations == 0 for r in result.iteration_history)
        # Only the baseline was evaluated.
        assert len(adapter.evaluate_calls) == 1
        assert result.evolved_components["output_schema"] == _VALID_SCHEMA
        assert result.evolved_components["instruction"] == "seed"

    @pytest.mark.asyncio
    async def test_ends_by_patience(self) -> None:
        """Invalid proposals count toward stagnation and exhaust patience."""
        adapter, result = await _run(max_iterations=10, patience=2)

        assert result.total_iterations == 2
        assert [r.skip_reason for r in result.iteration_history] == [
            "schema_validation_failed",
            "schema_validation_failed",
        ]
        assert len(adapter.evaluate_calls) == 1

    @pytest.mark.asyncio
    async def test_skipped_iteration_reaches_on_iteration(self) -> None:
        """The on_iteration callback sees each skipped record."""
        seen: list[IterationRecord] = []

        def record(iteration: IterationRecord, candidate_id: str | None) -> None:
            """Collect each record the engine reports.

            Args:
                iteration: The iteration record.
                candidate_id: Id of the candidate the record concerns (unused).
            """
            seen.append(iteration)

        _, result = await _run(max_iterations=2, patience=5, on_iteration=record)

        assert len(seen) == 2
        assert [r.skip_reason for r in seen] == ["schema_validation_failed"] * 2
        assert seen == result.iteration_history

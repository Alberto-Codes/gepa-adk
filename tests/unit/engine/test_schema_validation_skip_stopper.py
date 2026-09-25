"""Custom stoppers are consulted after a schema-validation skip.

A proposal whose ``output_schema`` text fails validation is recorded and
followed by the stop check, so a ``stop_callbacks`` stopper can end a run
whose every proposal is invalid.

Examples:
    Run this module alone:

    ```bash
    uv run pytest tests/unit/engine/test_schema_validation_skip_stopper.py -q
    ```

See Also:
    [`tests.unit.engine.test_schema_validation_skip`][]: The
        ``max_iterations``, ``patience`` and ``on_iteration`` cases.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig, IterationRecord
from gepa_adk.domain.stopper import StopperState
from gepa_adk.domain.types import StopReason
from gepa_adk.engine import AsyncGEPAEngine
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.unit

_VALID_SCHEMA = (
    "from pydantic import BaseModel\n\n\nclass Answer(BaseModel):\n    text: str\n"
)
_INVALID_SCHEMA = "class Answer(BaseModel:\n    text: str\n"


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


class _StopAfterFirstRecord:
    """Stopper that fires once the engine has recorded one iteration.

    Attributes:
        records (list[IterationRecord]): Records seen by ``on_iteration``.
        calls (int): Number of times the engine consulted the stopper.

    Examples:
        ```python
        stopper = _StopAfterFirstRecord()
        config = EvolutionConfig(
            on_iteration=stopper.on_iteration, stop_callbacks=[stopper]
        )
        ```
    """

    def __init__(self) -> None:
        """Start with no records seen and no calls made."""
        self.records: list[IterationRecord] = []
        self.calls = 0

    def on_iteration(self, record: IterationRecord, candidate_id: str | None) -> None:
        """Collect each record the engine reports.

        Args:
            record: The iteration record.
            candidate_id: Id of the candidate the record concerns (unused).
        """
        self.records.append(record)

    def __call__(self, state: StopperState) -> bool:
        """Stop once a record exists.

        Args:
            state: Evolution state snapshot (unused).

        Returns:
            True after the first record, else False.
        """
        self.calls += 1
        return len(self.records) >= 1


@pytest.mark.asyncio
async def test_custom_stopper_ends_run_after_one_skipped_iteration() -> None:
    """A stopper that fires after the first record ends the run at one skip."""
    stopper = _StopAfterFirstRecord()
    adapter = create_mock_adapter(
        default_score=0.5, custom_propose=_propose_invalid_schema
    )
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=50,
            patience=50,
            min_improvement_threshold=0.0,
            on_iteration=stopper.on_iteration,
            stop_callbacks=[stopper],
        ),
        initial_candidate=Candidate(
            components={"instruction": "seed", "output_schema": _VALID_SCHEMA}
        ),
        batch=[{"input": "q1"}],
    )

    result = await engine.run()

    assert result.stop_reason == StopReason.STOPPER_TRIGGERED
    assert result.total_iterations == 1
    assert [r.skip_reason for r in result.iteration_history] == [
        "schema_validation_failed"
    ]
    assert stopper.records == result.iteration_history
    # Called once before the loop and once after the skipped iteration.
    assert stopper.calls == 2
    assert len(adapter.evaluate_calls) == 1

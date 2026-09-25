"""Unit tests for ``on_iteration`` on a duplicate-proposal skip.

A proposal already scored this run is recorded with
``skip_reason="duplicate"``; the callback receives that record and the
duplicate proposal's id.

Examples:
    Run this module alone:

    ```bash
    uv run pytest tests/unit/engine/test_on_iteration_duplicate.py -q
    ```

See Also:
    - [`gepa_adk.domain.models.EvolutionConfig`][gepa_adk.domain.models.EvolutionConfig]:
      Defines the ``on_iteration`` field.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig, IterationRecord
from gepa_adk.engine import AsyncGEPAEngine
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.unit


async def _same(
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components: list[str],
) -> dict[str, str]:
    """Propose the same text every time.

    Args:
        candidate: Unused.
        reflective_dataset: Unused.
        components: Unused.

    Returns:
        The fixed proposal.
    """
    return {"instruction": "same"}


class TestOnIterationDuplicate:
    """A duplicate skip reaches the callback with the duplicate's id.

    Examples:
        ```bash
        uv run pytest tests/unit/engine/test_on_iteration_duplicate.py -q
        ```
    """

    @pytest.mark.asyncio
    async def test_duplicate_skip_is_reported_with_its_id(self) -> None:
        """Iteration 2 repeats iteration 1 and is reported as a duplicate."""
        seen: list[tuple[IterationRecord, str | None]] = []

        def on_iteration(record: IterationRecord, candidate_id: str | None) -> None:
            """Collect the record and id."""
            seen.append((record, candidate_id))

        adapter = create_mock_adapter(scores=[0.5, 0.7, 0.6, 0.8], custom_propose=_same)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=EvolutionConfig(
                max_iterations=2,
                patience=0,
                min_improvement_threshold=0.0,
                on_iteration=on_iteration,
            ),
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=[{"input": "q1"}, {"input": "q2"}],
        )

        result = await engine.run()

        same_id = Candidate(components={"instruction": "same"}).id
        assert len(seen) == 2
        assert [r for r, _ in seen] == result.iteration_history
        assert [(r.skip_reason, cid) for r, cid in seen] == [
            (None, same_id),
            ("duplicate", same_id),
        ]

"""Acceptance tests for issue 134, scoped to one callback.

``EvolutionConfig.on_iteration`` is called after each iteration with that
iteration's ``IterationRecord`` and the id of the candidate it concerns.
The callback may be sync or async. Skipped iterations (an empty proposal,
a duplicate) are reported too; an empty proposal carries ``None`` as the
candidate id because nothing was proposed.

Notes:
    The tests drive ``ConfigurableMockAdapter`` from
    ``tests/fixtures/adapters.py`` through ``custom_propose``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from gepa_adk.domain.exceptions import ConfigurationError, EmptyProposalError
from gepa_adk.domain.models import Candidate, EvolutionConfig, IterationRecord
from gepa_adk.engine import AsyncGEPAEngine
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.unit


async def _improving(
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components: list[str],
) -> dict[str, str]:
    """Return the parent's instruction with a trailing "!".

    Args:
        candidate: Parent component texts.
        reflective_dataset: Unused.
        components: Unused.

    Returns:
        A proposal that differs from the parent.
    """
    return {"instruction": candidate["instruction"] + "!"}


class _Script:
    """``custom_propose`` that raises ``EmptyProposalError`` on call 2.

    Attributes:
        calls (int): Number of propose calls so far.
    """

    def __init__(self) -> None:
        """Start the counter at zero."""
        self.calls = 0

    async def __call__(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components: list[str],
    ) -> dict[str, str]:
        """Return "p1", then raise, then "p3".

        Args:
            candidate: Unused.
            reflective_dataset: Unused.
            components: Unused.

        Returns:
            The scripted proposal.

        Raises:
            EmptyProposalError: On the second call.
        """
        self.calls += 1
        if self.calls == 2:
            raise EmptyProposalError("instruction")
        return {"instruction": f"p{self.calls}"}


async def _run(
    on_iteration: Any, *, propose: Any = _improving, max_iterations: int = 2
):
    adapter = create_mock_adapter(scores=[0.5, 0.7, 0.6, 0.8], custom_propose=propose)
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=max_iterations,
            patience=0,
            min_improvement_threshold=0.0,
            on_iteration=on_iteration,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=[{"input": "q1"}, {"input": "q2"}],
    )
    return await engine.run()


class TestOnIterationCallback:
    """The callback sees every iteration record and the candidate id."""

    @pytest.mark.asyncio
    async def test_sync_callback_receives_each_record_and_id(self) -> None:
        """Two iterations call a sync callback twice, in order, with the ids."""
        seen: list[tuple[IterationRecord, str | None]] = []

        def on_iteration(record: IterationRecord, candidate_id: str | None) -> None:
            """Collect the record and id."""
            seen.append((record, candidate_id))

        result = await _run(on_iteration)

        assert [r for r, _ in seen] == result.iteration_history
        assert [r.iteration_number for r, _ in seen] == [1, 2]
        assert [cid for _, cid in seen] == [
            Candidate(components={"instruction": "seed!"}).id,
            Candidate(components={"instruction": "seed!!"}).id,
        ]

    @pytest.mark.asyncio
    async def test_async_callback_is_awaited(self) -> None:
        """An async callback is awaited before the next iteration starts."""
        seen: list[int] = []

        async def on_iteration(
            record: IterationRecord, candidate_id: str | None
        ) -> None:
            """Collect the iteration number from an async callback."""
            seen.append(record.iteration_number)

        await _run(on_iteration)

        assert seen == [1, 2]

    @pytest.mark.asyncio
    async def test_skipped_iteration_is_reported_with_none_id(self) -> None:
        """An empty-proposal iteration reaches the callback with candidate_id None."""
        seen: list[tuple[int, str | None, str | None]] = []

        def on_iteration(record: IterationRecord, candidate_id: str | None) -> None:
            """Collect the number, skip reason and id."""
            seen.append((record.iteration_number, record.skip_reason, candidate_id))

        await _run(on_iteration, propose=_Script(), max_iterations=3)

        assert seen[0] == (1, None, Candidate(components={"instruction": "p1"}).id)
        assert seen[1] == (2, "empty_proposal", None)
        assert seen[2] == (3, None, Candidate(components={"instruction": "p3"}).id)

    @pytest.mark.asyncio
    async def test_callback_error_propagates(self) -> None:
        """An exception in the callback is not swallowed."""

        def on_iteration(record: IterationRecord, candidate_id: str | None) -> None:
            """Fail on purpose.

            Raises:
                RuntimeError: Always, to prove the engine does not swallow it.
            """
            raise RuntimeError("stop here")

        with pytest.raises(RuntimeError, match="stop here"):
            await _run(on_iteration)

    def test_non_callable_is_rejected(self) -> None:
        """A non-callable on_iteration is a configuration error."""
        with pytest.raises(ConfigurationError, match="on_iteration"):
            EvolutionConfig(on_iteration="not callable")  # type: ignore[arg-type]

    def test_default_is_none(self) -> None:
        """No callback by default."""
        assert EvolutionConfig().on_iteration is None

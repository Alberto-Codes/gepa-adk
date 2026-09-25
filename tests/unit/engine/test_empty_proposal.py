"""Acceptance tests for issue 392: an empty reflection response does not abort.

The proposer retries the reflection once. When the retry is also empty it
raises ``EmptyProposalError``. The engine treats that error as a failed
iteration: it records the iteration as not accepted with the
``empty_proposal`` marker, counts it toward stagnation and continues, so
``EvolutionResult`` stays complete.

Notes:
    The engine tests drive ``ConfigurableMockAdapter`` from
    ``tests/fixtures/adapters.py`` through ``custom_propose``; the proposer
    tests call ``AsyncReflectiveMutationProposer`` with a counting reflection
    function.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from structlog.testing import capture_logs

from gepa_adk.domain.exceptions import EmptyProposalError, EvolutionError
from gepa_adk.domain.models import Candidate, EvolutionConfig, IterationRecord
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.unit

_TRIALS = {"instruction": [{"input": "q", "output": "a", "feedback": {"score": 0.0}}]}


class _ProposeScript:
    """``custom_propose`` that follows a per-call script.

    Attributes:
        script (list[str | None]): One entry per call. A string is returned
            as the new instruction; ``None`` raises ``EmptyProposalError``.
        calls (int): Number of propose calls made so far.
    """

    def __init__(self, script: list[str | None]) -> None:
        """Store the script and start the call counter at zero.

        Args:
            script: Per-call outcomes, consumed in order and repeated at the
                end.
        """
        self.script = script
        self.calls = 0

    async def __call__(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components: list[str],
    ) -> dict[str, str]:
        """Return the scripted proposal or raise for an empty one.

        Args:
            candidate: Parent component texts (unused).
            reflective_dataset: Reflection examples (unused).
            components: Components to update (unused).

        Returns:
            The scripted instruction text.

        Raises:
            EmptyProposalError: When the script entry is ``None``.
        """
        entry = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        if entry is None:
            raise EmptyProposalError("instruction")
        return {"instruction": entry}


class _CountingReflection:
    """Reflection function that returns scripted texts and counts calls.

    Attributes:
        responses (list[str]): Texts returned in order; the last repeats.
        calls (int): Number of reflection calls made so far.
    """

    def __init__(self, responses: list[str]) -> None:
        """Store the responses and start the counter at zero.

        Args:
            responses: Scripted reflection outputs.
        """
        self.responses = responses
        self.calls = 0

    async def __call__(
        self, component_text: str, trials: list[dict[str, Any]], component: str
    ) -> tuple[str, str | None]:
        """Return the next scripted response.

        Args:
            component_text: Current text (unused).
            trials: Trial records (unused).
            component: Component name (unused).

        Returns:
            The scripted text and ``None`` reasoning.
        """
        text = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return text, None


async def _run(
    script: list[str | None], *, scores: list[float], max_iterations: int, patience: int
):
    adapter = create_mock_adapter(scores=scores, custom_propose=_ProposeScript(script))
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=max_iterations,
            patience=patience,
            min_improvement_threshold=0.0,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=[{"input": "q1"}, {"input": "q2"}],
    )
    with capture_logs() as logs:
        result = await engine.run()
    return adapter, result, logs


class TestEngineSurvivesEmptyProposal:
    """The run completes and reports the empty iteration."""

    @pytest.mark.asyncio
    async def test_empty_on_iteration_two_then_proposal_on_three(self) -> None:
        """Iteration 2 is recorded as skipped; iteration 3's proposal wins."""
        adapter, result, logs = await _run(
            ["p1", None, "p3"], scores=[0.5, 0.7, 0.9], max_iterations=3, patience=0
        )

        assert result.evolved_components["instruction"] == "p3"
        assert result.total_iterations == 3
        assert len(adapter.evaluate_calls) == 3  # baseline, p1, p3: nothing for 2
        assert [r.iteration_number for r in result.iteration_history] == [1, 2, 3]
        assert [r.accepted for r in result.iteration_history] == [True, False, True]
        skipped = result.iteration_history[1]
        assert skipped.skip_reason == "empty_proposal"
        assert skipped.evolved_component == "instruction"
        assert skipped.component_text == ""
        assert result.iteration_history[0].skip_reason is None
        assert result.iteration_history[2].skip_reason is None
        events = [
            e
            for e in logs
            if e["event"] == "evolution.proposal_skipped"
            and e.get("reason") == "empty_proposal"
        ]
        assert len(events) == 1
        assert events[0]["iteration"] == 2

    @pytest.mark.asyncio
    async def test_always_empty_ends_by_patience_with_seed(self) -> None:
        """Two empty iterations exhaust patience=2; the seed is the result."""
        adapter, result, _ = await _run(
            [None], scores=[0.5], max_iterations=10, patience=2
        )

        assert result.evolved_components == {"instruction": "seed"}
        assert result.total_iterations == 2
        assert len(adapter.evaluate_calls) == 1
        assert all(not r.accepted for r in result.iteration_history)
        assert all(r.skip_reason == "empty_proposal" for r in result.iteration_history)
        assert result.final_score == result.original_score

    @pytest.mark.asyncio
    async def test_always_empty_ends_by_max_iterations_not_error(self) -> None:
        """With patience disabled the run reaches max_iterations, not an error."""
        _, result, _ = await _run([None], scores=[0.5], max_iterations=3, patience=0)

        assert result.total_iterations == 3
        assert len(result.iteration_history) == 3
        assert result.evolved_components == {"instruction": "seed"}

    def test_skip_reason_round_trips_and_defaults_to_none(self) -> None:
        """to_dict carries skip_reason; old dicts without it load as None."""
        record = IterationRecord(
            iteration_number=2,
            score=0.0,
            component_text="",
            evolved_component="instruction",
            accepted=False,
            skip_reason="empty_proposal",
        )
        assert IterationRecord.from_dict(record.to_dict()).skip_reason == (
            "empty_proposal"
        )
        legacy = record.to_dict()
        del legacy["skip_reason"]
        assert IterationRecord.from_dict(legacy).skip_reason is None


class TestProposerRetriesOnce:
    """The proposer retries an empty reflection exactly once."""

    @pytest.mark.asyncio
    async def test_empty_then_text_returns_the_retry(self) -> None:
        """One empty response is retried and the second answer is used."""
        fn = _CountingReflection(["", "Better"])
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=fn)

        with capture_logs() as logs:
            result = await proposer.propose(
                candidate={"instruction": "seed"},
                reflective_dataset=_TRIALS,
                components_to_update=["instruction"],
            )

        assert result == {"instruction": "Better"}
        assert fn.calls == 2
        retries = [e for e in logs if e["event"] == "proposer.empty_retry"]
        assert len(retries) == 1
        assert retries[0]["component"] == "instruction"

    @pytest.mark.asyncio
    async def test_empty_twice_raises_empty_proposal_error(self) -> None:
        """Two empty responses raise EmptyProposalError after exactly two calls."""
        fn = _CountingReflection(["", "   "])
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=fn)

        with pytest.raises(EmptyProposalError, match="empty string") as exc_info:
            await proposer.propose(
                candidate={"instruction": "seed"},
                reflective_dataset=_TRIALS,
                components_to_update=["instruction"],
            )

        assert fn.calls == 2
        assert isinstance(exc_info.value, EvolutionError)
        assert exc_info.value.component == "instruction"

    @pytest.mark.asyncio
    async def test_non_empty_first_answer_is_not_retried(self) -> None:
        """A good first answer makes exactly one reflection call."""
        fn = _CountingReflection(["Good"])
        proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=fn)

        result = await proposer.propose(
            candidate={"instruction": "seed"},
            reflective_dataset=_TRIALS,
            components_to_update=["instruction"],
        )

        assert result == {"instruction": "Good"}
        assert fn.calls == 1

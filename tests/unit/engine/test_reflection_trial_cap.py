"""Acceptance tests for issue 394: cap the trials sent to the reflection prompt.

``EvolutionConfig.reflection_max_trials`` bounds how many trials each
component sends to the reflector, preferring a mix of failing and passing
rows. ``EvolutionConfig.reflection_max_trial_chars`` bounds every string
value inside a trial with a visible marker. ``AsyncReflectiveMutationProposer``
applies both caps and logs what it dropped; ``evolve()`` wires them from the
config.

Notes:
    The proposer tests use a recording reflection function so the exact
    trial list delivered to the reflector can be asserted.
"""

from __future__ import annotations

import re
from collections.abc import MutableMapping
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent
from structlog.testing import capture_logs

from gepa_adk import evolve, evolve_group
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import EvolutionConfig, EvolutionResult
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from tests.conftest import MockScorer

pytestmark = pytest.mark.unit

_MARKER = re.compile(r"…\[truncated, (\d+) chars omitted\]$")


class _Recorder:
    """Reflection function that records the trials it receives.

    Attributes:
        received (list[list[dict[str, Any]]]): One trial list per call.
    """

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.received: list[list[dict[str, Any]]] = []

    async def __call__(
        self, component_text: str, trials: list[dict[str, Any]], component: str
    ) -> tuple[str, str | None]:
        """Record the trials and return a fixed proposal.

        Args:
            component_text: Current text (unused).
            trials: The trial records handed to the reflector.
            component: Component name (unused).

        Returns:
            A fixed proposal and ``None`` reasoning.
        """
        self.received.append(trials)
        return "Improved", None


def _trial(i: int, *, score: float, text_len: int = 4) -> dict[str, Any]:
    return {
        "input": f"q{i}",
        "output": "o" * text_len,
        "feedback": {"score": score, "feedback_text": "ok"},
        "trajectory": {
            "input": f"q{i}",
            "output": "o" * text_len,
            "trace": "t" * text_len,
        },
    }


def _thirty_trials() -> list[dict[str, Any]]:
    """Return 30 trials: index divisible by 3 passes (1.0), the rest fail.

    Returns:
        Thirty trial records, ten passing and twenty failing, in index order.
    """
    return [_trial(i, score=1.0 if i % 3 == 0 else 0.0) for i in range(30)]


async def _propose(
    trials: list[dict[str, Any]],
    *,
    max_trials: int | None,
    max_trial_chars: int | None,
) -> tuple[_Recorder, list[MutableMapping[str, Any]]]:
    fn = _Recorder()
    proposer = AsyncReflectiveMutationProposer(
        adk_reflection_fn=fn, max_trials=max_trials, max_trial_chars=max_trial_chars
    )
    with capture_logs() as logs:
        result = await proposer.propose(
            candidate={"instruction": "seed"},
            reflective_dataset={"instruction": trials},
            components_to_update=["instruction"],
        )
    assert result == {"instruction": "Improved"}
    return fn, [e for e in logs if e["event"] == "proposer.trials_capped"]


class TestConfigFields:
    """Both fields default to None and reject values below 1."""

    def test_defaults_are_none(self) -> None:
        """A default config sets no cap."""
        config = EvolutionConfig()
        assert config.reflection_max_trials is None
        assert config.reflection_max_trial_chars is None

    @pytest.mark.parametrize(
        "field", ["reflection_max_trials", "reflection_max_trial_chars"]
    )
    @pytest.mark.parametrize("value", [0, -1])
    def test_values_below_one_raise(self, field: str, value: int) -> None:
        """Zero and negative caps are configuration errors."""
        with pytest.raises(ConfigurationError, match=field):
            EvolutionConfig(**{field: value})

    def test_one_is_accepted(self) -> None:
        """A cap of 1 is the smallest valid value."""
        config = EvolutionConfig(reflection_max_trials=1, reflection_max_trial_chars=1)
        assert config.reflection_max_trials == 1
        assert config.reflection_max_trial_chars == 1


class TestMaxTrials:
    """The proposer keeps at most N trials, failing first then passing."""

    @pytest.mark.asyncio
    async def test_six_of_thirty_keeps_three_failing_then_three_passing(self) -> None:
        """20 failing and 10 passing trials capped at 6 yields 3 + 3 in batch order."""
        trials = _thirty_trials()
        fn, capped = await _propose(trials, max_trials=6, max_trial_chars=None)

        assert len(fn.received) == 1
        delivered = fn.received[0]
        assert len(delivered) == 6
        assert [t["input"] for t in delivered] == ["q1", "q2", "q4", "q0", "q3", "q6"]
        assert [t["feedback"]["score"] for t in delivered] == [
            0.0,
            0.0,
            0.0,
            1.0,
            1.0,
            1.0,
        ]
        assert len(capped) == 1
        assert capped[0]["component"] == "instruction"
        assert capped[0]["kept"] == 6
        assert capped[0]["dropped_trials"] == 24
        assert capped[0]["truncated_fields"] == 0
        assert capped[0]["dropped_chars"] == 0

    @pytest.mark.asyncio
    async def test_fills_from_passing_when_failing_runs_short(self) -> None:
        """One failing trial and nine passing capped at 4 yields 1 + 3."""
        trials = [_trial(i, score=0.0 if i == 5 else 1.0) for i in range(10)]
        fn, capped = await _propose(trials, max_trials=4, max_trial_chars=None)

        assert [t["input"] for t in fn.received[0]] == ["q5", "q0", "q1", "q2"]
        assert capped[0]["kept"] == 4
        assert capped[0]["dropped_trials"] == 6

    @pytest.mark.asyncio
    async def test_odd_cap_rounds_the_failing_share_up(self) -> None:
        """A cap of 5 keeps ceil(5/2)=3 failing then 2 passing, not 2 and 3."""
        trials = _thirty_trials()
        fn, capped = await _propose(trials, max_trials=5, max_trial_chars=None)

        assert [t["input"] for t in fn.received[0]] == ["q1", "q2", "q4", "q0", "q3"]
        assert capped[0]["kept"] == 5
        assert capped[0]["dropped_trials"] == 25

    @pytest.mark.asyncio
    async def test_fills_from_failing_when_passing_runs_short(self) -> None:
        """Nine failing and one passing capped at 5 yields 4 failing + 1 passing."""
        trials = [_trial(i, score=1.0 if i == 7 else 0.0) for i in range(10)]
        fn, capped = await _propose(trials, max_trials=5, max_trial_chars=None)

        assert [t["input"] for t in fn.received[0]] == ["q0", "q1", "q2", "q3", "q7"]
        assert capped[0]["dropped_trials"] == 5

    @pytest.mark.asyncio
    async def test_cap_above_count_changes_nothing(self) -> None:
        """A cap larger than the trial count delivers every trial and logs nothing."""
        trials = _thirty_trials()
        fn, capped = await _propose(trials, max_trials=50, max_trial_chars=None)

        assert fn.received[0] == trials
        assert capped == []


class TestMaxTrialChars:
    """Every string value inside a trial is cut to the cap with a marker."""

    @pytest.mark.asyncio
    async def test_long_strings_are_cut_with_marker_and_short_ones_kept(self) -> None:
        """Output and nested trace at 200 chars are cut to 50; 'ok' stays intact."""
        trials = [_trial(i, score=0.0, text_len=200) for i in range(2)]
        fn, capped = await _propose(trials, max_trials=None, max_trial_chars=50)

        delivered = fn.received[0]
        assert len(delivered) == 2
        for trial in delivered:
            for value in (
                trial["output"],
                trial["trajectory"]["output"],
                trial["trajectory"]["trace"],
            ):
                match = _MARKER.search(value)
                assert match is not None, value
                assert int(match.group(1)) == 150
                assert value[:50] == "o" * 50 or value[:50] == "t" * 50
                assert len(value) == 50 + len(match.group(0))
            assert trial["feedback"]["feedback_text"] == "ok"
            assert trial["feedback"]["score"] == 0.0
        assert len(capped) == 1
        assert capped[0]["kept"] == 2
        assert capped[0]["dropped_trials"] == 0
        assert capped[0]["truncated_fields"] == 6
        assert capped[0]["dropped_chars"] == 900

    @pytest.mark.asyncio
    async def test_original_trials_are_not_mutated(self) -> None:
        """Truncation works on copies; the reflective dataset is unchanged."""
        trials = [_trial(0, score=0.0, text_len=200)]
        await _propose(trials, max_trials=None, max_trial_chars=50)

        assert trials[0]["output"] == "o" * 200
        assert trials[0]["trajectory"]["trace"] == "t" * 200


class TestNoCaps:
    """Both caps None deliver the trials unchanged and log nothing."""

    @pytest.mark.asyncio
    async def test_none_caps_pass_trials_through(self) -> None:
        """Thirty long trials arrive as-is with no capping event."""
        trials = [_trial(i, score=0.0, text_len=200) for i in range(30)]
        fn, capped = await _propose(trials, max_trials=None, max_trial_chars=None)

        assert fn.received[0] == trials
        assert capped == []


class TestEvolveWiring:
    """``evolve()`` hands both config fields to the proposer."""

    @pytest.mark.asyncio
    async def test_evolve_passes_caps_to_proposer(self) -> None:
        """The proposer is built with the config's two cap values."""
        agent = LlmAgent(name="a", model="gemini-3.8-flash", instruction="Answer.")
        result = EvolutionResult(
            original_score=0.5,
            final_score=0.5,
            evolved_components={"instruction": "Answer."},
            iteration_history=[],
            total_iterations=0,
        )
        engine = MagicMock()
        engine.run = AsyncMock(return_value=result)
        config = EvolutionConfig(
            reflection_max_trials=8, reflection_max_trial_chars=300
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine", return_value=engine),
            patch("gepa_adk.api.ADKAdapter", return_value=MagicMock()),
            patch("gepa_adk.api.CriticScorer"),
            patch("gepa_adk.api.AsyncReflectiveMutationProposer") as proposer_class,
        ):
            await evolve(agent, [{"input": "q"}], config=config, scorer=MockScorer())

        proposer_class.assert_called_once()
        assert proposer_class.call_args.kwargs["max_trials"] == 8
        assert proposer_class.call_args.kwargs["max_trial_chars"] == 300

    @pytest.mark.asyncio
    async def test_evolve_group_passes_caps_to_proposer(self) -> None:
        """The multi-agent entry point builds the proposer with the same caps."""
        generator = LlmAgent(
            name="generator", model="gemini-3.8-flash", instruction="Write."
        )
        critic = LlmAgent(name="critic", model="gemini-3.8-flash", instruction="Judge.")
        result = EvolutionResult(
            original_score=0.5,
            final_score=0.5,
            evolved_components={"generator.instruction": "Write."},
            iteration_history=[],
            total_iterations=0,
        )
        engine = MagicMock()
        engine.run = AsyncMock(return_value=result)
        config = EvolutionConfig(reflection_max_trials=3, reflection_max_trial_chars=99)

        with (
            patch("gepa_adk.api.AsyncGEPAEngine", return_value=engine),
            patch("gepa_adk.api.MultiAgentAdapter", return_value=MagicMock()),
            patch("gepa_adk.api.AsyncReflectiveMutationProposer") as proposer_class,
        ):
            await evolve_group(
                agents={"generator": generator, "critic": critic},
                primary="generator",
                trainset=[{"input": "q"}],
                config=config,
                scorer=MockScorer(),
            )

        proposer_class.assert_called_once()
        assert proposer_class.call_args.kwargs["max_trials"] == 3
        assert proposer_class.call_args.kwargs["max_trial_chars"] == 99

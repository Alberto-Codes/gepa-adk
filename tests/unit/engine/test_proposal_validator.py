"""Acceptance tests for ``EvolutionConfig.proposal_validator``.

A caller-supplied validator sees each proposed component text before the
engine validates or evaluates it. A non-None return is the reason the
proposal is rejected: the iteration is recorded with
``skip_reason="proposal_rejected"`` and that reason, costs no evaluation,
counts toward patience and reaches ``on_iteration`` like every other skip
(GitHub issue 452).

Notes:
    The mock adapter scripts the proposals, so the refusal text a local
    reflector produced ("I need the missing inputs ...") is replayed
    without an LLM. Version 5 of the result schema carries the reason on
    the record (the current version is 6); the migration test loads a
    version 4 dict.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from structlog.testing import capture_logs

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import (
    CURRENT_SCHEMA_VERSION,
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    IterationRecord,
)
from gepa_adk.engine import AsyncGEPAEngine
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.unit

_REFUSAL = (
    "I can improve it, but I need the missing inputs. Please provide: "
    "1. The current component text 2. The trial results"
)
_REASON = "asked for its inputs instead of answering"


def _scripted(texts: list[str]) -> Callable[..., Awaitable[dict[str, str]]]:
    """Return a propose function that replays ``texts`` in order.

    Args:
        texts: One instruction text per iteration.

    Returns:
        An async propose callable for ``create_mock_adapter``.
    """
    remaining = list(texts)

    async def propose(
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components: list[str],
    ) -> dict[str, str]:
        return {"instruction": remaining.pop(0)}

    return propose


def _refuse_requests_for_inputs(component: str, text: str) -> str | None:
    """Reject a proposal that asks for its inputs instead of answering.

    Args:
        component: The component name.
        text: The proposed text.

    Returns:
        The reason when the text is a request for inputs, else None.
    """
    return _REASON if "I need the missing inputs" in text else None


async def _run(
    texts: list[str],
    *,
    validator: Callable[[str, str], str | None] | None,
    patience: int = 5,
    max_iterations: int | None = None,
    on_iteration: Callable[..., Any] | None = None,
) -> tuple[Any, EvolutionResult, list[MutableMapping[str, Any]]]:
    """Run the engine over scripted proposals with the given validator.

    Args:
        texts: Proposal texts, one per iteration.
        validator: The ``proposal_validator`` to configure, or None.
        patience: Stagnation patience.
        max_iterations: Iteration cap; defaults to ``len(texts)``.
        on_iteration: Optional ``on_iteration`` callback.

    Returns:
        The adapter, the result and the captured log events.
    """
    adapter = create_mock_adapter(
        scores=[0.5, 0.7, 0.8, 0.9, 0.95], custom_propose=_scripted(texts)
    )
    kwargs: dict[str, Any] = {}
    if validator is not None:
        kwargs["proposal_validator"] = validator
    if on_iteration is not None:
        kwargs["on_iteration"] = on_iteration
    config = EvolutionConfig(
        max_iterations=max_iterations or len(texts),
        patience=patience,
        min_improvement_threshold=0.0,
        **kwargs,
    )
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=config,
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=[{"input": "q1"}, {"input": "q2"}],
    )
    with capture_logs() as logs:
        result = await engine.run()
    return adapter, result, logs


class TestConfigField:
    """``proposal_validator`` is optional and must be callable."""

    def test_default_is_none(self) -> None:
        """An unset validator is None."""
        assert EvolutionConfig().proposal_validator is None

    def test_non_callable_is_rejected(self) -> None:
        """A non-callable value raises ConfigurationError naming the field."""
        not_callable: Any = "reject everything"
        with pytest.raises(ConfigurationError) as excinfo:
            EvolutionConfig(proposal_validator=not_callable)
        assert excinfo.value.field == "proposal_validator"


class TestRejectedProposal:
    """A non-None reason skips the proposal without evaluating it."""

    @pytest.mark.asyncio
    async def test_rejection_is_recorded_and_not_evaluated(self) -> None:
        """The refusal is recorded with its reason and costs no evaluation."""
        adapter, result, logs = await _run(
            [_REFUSAL, "better"], validator=_refuse_requests_for_inputs
        )

        first, second = result.iteration_history
        assert first.skip_reason == "proposal_rejected"
        assert first.rejection_reason == _REASON
        assert first.accepted is False
        assert first.score == 0.0
        assert first.component_text == _REFUSAL
        assert first.evolved_component == "instruction"
        assert first.candidate_id is not None
        assert first.parent_ids == [Candidate(components={"instruction": "seed"}).id]
        assert second.skip_reason is None
        assert second.rejection_reason is None
        assert second.accepted is True
        assert result.evolved_components == {"instruction": "better"}
        assert len(adapter.evaluate_calls) == 2
        skips = [e for e in logs if e["event"] == "evolution.proposal_skipped"]
        assert len(skips) == 1
        assert skips[0]["reason"] == "proposal_rejected"
        assert skips[0]["rejection_reason"] == _REASON

    @pytest.mark.asyncio
    async def test_validator_receives_component_name_and_text(self) -> None:
        """The validator is called once per proposal with name and text."""
        calls: list[tuple[str, str]] = []

        def record(component: str, text: str) -> str | None:
            calls.append((component, text))
            return None

        await _run([_REFUSAL, "better"], validator=record)

        assert calls == [("instruction", _REFUSAL), ("instruction", "better")]

    @pytest.mark.asyncio
    async def test_rejections_count_toward_patience(self) -> None:
        """Rejections advance stagnation and stop the run."""
        adapter, result, _ = await _run(
            [_REFUSAL, _REFUSAL, _REFUSAL],
            validator=_refuse_requests_for_inputs,
            patience=2,
            max_iterations=3,
        )

        assert result.total_iterations == 2
        assert [r.skip_reason for r in result.iteration_history] == [
            "proposal_rejected",
            "proposal_rejected",
        ]
        assert len(adapter.evaluate_calls) == 1

    @pytest.mark.asyncio
    async def test_on_iteration_receives_the_rejected_record(self) -> None:
        """The rejected iteration reaches ``on_iteration`` with its id."""
        seen: list[tuple[IterationRecord, str | None]] = []

        def on_iteration(record: IterationRecord, candidate_id: str | None) -> None:
            seen.append((record, candidate_id))

        _, result, _ = await _run(
            [_REFUSAL], validator=_refuse_requests_for_inputs, on_iteration=on_iteration
        )

        assert len(seen) == 1
        record, candidate_id = seen[0]
        assert record.skip_reason == "proposal_rejected"
        assert record.rejection_reason == _REASON
        assert candidate_id == result.iteration_history[0].candidate_id
        assert candidate_id is not None

    @pytest.mark.asyncio
    async def test_a_raising_validator_aborts_the_run(self) -> None:
        """An exception from the validator propagates; nothing is recorded."""

        def broken(component: str, text: str) -> str | None:
            raise ValueError("validator failed")

        adapter = create_mock_adapter(
            scores=[0.5, 0.7], custom_propose=_scripted(["better"])
        )
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=EvolutionConfig(max_iterations=1, proposal_validator=broken),
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=[{"input": "q1"}, {"input": "q2"}],
        )

        with pytest.raises(ValueError, match="validator failed"):
            await engine.run()
        assert len(adapter.evaluate_calls) == 1


class TestAcceptedProposal:
    """None from the validator, or no validator, evaluates as before."""

    @pytest.mark.asyncio
    async def test_none_and_missing_validator_evaluate_alike(self) -> None:
        """A validator returning None changes nothing about the run."""
        adapter_with, with_validator, _ = await _run(
            ["better", "best"], validator=lambda component, text: None
        )
        adapter_without, without_validator, _ = await _run(
            ["better", "best"], validator=None
        )

        for result in (with_validator, without_validator):
            assert [r.skip_reason for r in result.iteration_history] == [None, None]
            assert [r.rejection_reason for r in result.iteration_history] == [
                None,
                None,
            ]
            assert result.evolved_components == {"instruction": "best"}
        assert len(adapter_with.evaluate_calls) == len(adapter_without.evaluate_calls)
        assert len(adapter_with.evaluate_calls) == 3


class TestRecordShape:
    """``rejection_reason`` is on the record and in schema version 5 and later."""

    def test_current_schema_version_is_six(self) -> None:
        """The rejection reason is a version 5 field; version 6 splits usage."""
        assert CURRENT_SCHEMA_VERSION == 6

    def test_record_round_trips_the_reason(self) -> None:
        """``to_dict`` writes the reason and ``from_dict`` reads it back."""
        record = IterationRecord(
            iteration_number=1,
            score=0.0,
            component_text=_REFUSAL,
            evolved_component="instruction",
            accepted=False,
            skip_reason="proposal_rejected",
            rejection_reason=_REASON,
        )
        data = record.to_dict()
        assert data["rejection_reason"] == _REASON
        assert IterationRecord.from_dict(data) == record
        assert IterationRecord.from_dict(data).rejection_reason == _REASON

    def test_record_without_the_key_reads_none(self) -> None:
        """A dict written before version 5 has no reason."""
        data = {
            "iteration_number": 1,
            "score": 0.5,
            "component_text": "x",
            "evolved_component": "instruction",
            "accepted": True,
        }
        assert IterationRecord.from_dict(data).rejection_reason is None

    def test_version_4_result_migrates_with_none_reason(self) -> None:
        """A version 4 result loads at version 6 with None on every record."""
        fixture = Path("tests/fixtures/evolution_result_v3.json")
        data = json.loads(fixture.read_text(encoding="utf-8"))
        data["schema_version"] = 4
        for record in data["iteration_history"]:
            record["candidate_id"] = "c1"
            record["parent_ids"] = ["c0"]
            record.setdefault("token_usage", None)
        assert data["iteration_history"]

        result = EvolutionResult.from_dict(data)

        assert result.schema_version == CURRENT_SCHEMA_VERSION == 6
        assert all(r.rejection_reason is None for r in result.iteration_history)
        assert result.to_dict()["schema_version"] == 6
        assert all(
            "rejection_reason" in r for r in result.to_dict()["iteration_history"]
        )

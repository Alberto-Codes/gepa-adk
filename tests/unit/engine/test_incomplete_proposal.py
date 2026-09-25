"""Acceptance tests for skipping a reflection cut off at the token limit.

When the last model response behind a reflection reports a length stop
(``finish_reason`` ``MAX_TOKENS``), or the proposal opens a reasoning tag
that is never closed, the reflection function raises
``IncompleteProposalError`` instead of returning the truncated text. The
engine records that iteration with ``skip_reason="incomplete_proposal"``,
keeps the raw text on the record, counts it toward stagnation, calls
``on_iteration`` and continues without evaluating anything. A complete
text with a normal stop is evaluated as before.

Examples:
    Run these tests on their own:

    ```bash
    uv run pytest tests/unit/engine/test_incomplete_proposal.py -q
    ```

See Also:
    - [`gepa_adk.engine.adk_reflection`][gepa_adk.engine.adk_reflection]: The
      reflection function that reads the finish reason.
    - [`gepa_adk.engine.async_engine`][gepa_adk.engine.async_engine]: The
      engine that records the skipped iteration.

Notes:
    The executor and the adapter are fakes, so no agent or LLM runs. The
    fake executor returns real ADK ``Event`` objects so the finish reason
    is read the way production events carry it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.genai import types
from structlog.testing import capture_logs

from gepa_adk.domain.exceptions import EvolutionError, IncompleteProposalError
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn, is_length_stop
from gepa_adk.ports.adapter import EvaluationBatch
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

pytestmark = pytest.mark.unit

_CUT = "Be concise and always"


def _event(text: str, finish: types.FinishReason | None) -> Event:
    return Event(
        author="reflector",
        finish_reason=finish,
        content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


class ScriptedExecutor:
    """Executor stub that returns one scripted result.

    Attributes:
        result (ExecutionResult): Result returned by every call.
        calls (int): Number of calls made so far.
    """

    def __init__(self, result: ExecutionResult) -> None:
        """Store the scripted result.

        Args:
            result: Result returned by every call.
        """
        self.result = result
        self.calls = 0

    async def execute_agent(self, **kwargs: Any) -> ExecutionResult:
        """Return the scripted result.

        Args:
            **kwargs: Ignored.

        Returns:
            The scripted result.
        """
        self.calls += 1
        return self.result


def _reflect(text: str, events: list[Event] | None, **kwargs: Any) -> Any:
    executor = ScriptedExecutor(
        ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            session_id="s",
            extracted_value=text,
            captured_events=events,
        )
    )
    agent = LlmAgent(
        name="reflector",
        model="gemini-3.8-flash",
        instruction="{component_text}\n{trials}",
    )
    return create_adk_reflection_fn(agent, executor=executor, **kwargs)


class TestLengthStopRaises:
    """A MAX_TOKENS finish on the last model response is incomplete."""

    @pytest.mark.asyncio
    async def test_max_tokens_raises_incomplete_proposal(self) -> None:
        """The cut-off text is not returned; the error carries the details."""
        reflect = _reflect(_CUT, [_event(_CUT, types.FinishReason.MAX_TOKENS)])

        with capture_logs() as logs, pytest.raises(IncompleteProposalError) as excinfo:
            await reflect("old", [], component_name="instruction")

        error = excinfo.value
        assert isinstance(error, EvolutionError)
        assert error.component == "instruction"
        assert error.finish_reason == "MAX_TOKENS"
        assert error.output_length == len(_CUT)
        assert error.raw_text == _CUT
        assert "MAX_TOKENS" in str(error)
        incomplete = [e for e in logs if e["event"] == "reflection.incomplete"]
        assert len(incomplete) == 1
        assert incomplete[0]["finish_reason"] == "MAX_TOKENS"
        assert incomplete[0]["response_length"] == len(_CUT)
        assert incomplete[0]["component"] == "instruction"

    @pytest.mark.asyncio
    async def test_normal_stop_returns_the_text(self) -> None:
        """The same text with a STOP finish is a complete proposal."""
        reflect = _reflect(_CUT, [_event(_CUT, types.FinishReason.STOP)])

        proposed, _, _ = await reflect("old", [], component_name="instruction")

        assert proposed == _CUT

    @pytest.mark.asyncio
    async def test_no_finish_reason_returns_the_text(self) -> None:
        """Events without a finish reason (fakes, tools) are complete."""
        reflect = _reflect(_CUT, [_event(_CUT, None)])

        proposed, _, _ = await reflect("old", [], component_name="instruction")

        assert proposed == _CUT

    @pytest.mark.asyncio
    async def test_no_events_returns_the_text(self) -> None:
        """A result without captured events is complete."""
        reflect = _reflect(_CUT, None)

        proposed, _, _ = await reflect("old", [], component_name="instruction")

        assert proposed == _CUT

    @pytest.mark.asyncio
    async def test_only_the_last_model_response_counts(self) -> None:
        """An earlier MAX_TOKENS event is ignored when the last stop is normal."""
        events = [
            _event("draft", types.FinishReason.MAX_TOKENS),
            _event(_CUT, types.FinishReason.STOP),
        ]
        reflect = _reflect(_CUT, events)

        proposed, _, _ = await reflect("old", [], component_name="instruction")

        assert proposed == _CUT

    @pytest.mark.asyncio
    async def test_last_event_length_stop_after_a_normal_one(self) -> None:
        """A MAX_TOKENS on the last event is incomplete even after a STOP."""
        events = [
            _event("draft", types.FinishReason.STOP),
            _event(_CUT, types.FinishReason.MAX_TOKENS),
        ]
        reflect = _reflect(_CUT, events)

        with pytest.raises(IncompleteProposalError):
            await reflect("old", [], component_name="instruction")

    @pytest.mark.asyncio
    async def test_empty_text_with_max_tokens_is_still_incomplete(self) -> None:
        """A length stop wins over the empty-response path."""
        reflect = _reflect("", [_event("", types.FinishReason.MAX_TOKENS)])

        with pytest.raises(IncompleteProposalError) as excinfo:
            await reflect("old", [], component_name="instruction")

        assert excinfo.value.output_length == 0


class TestUnterminatedReasoningTag:
    """A proposal that opens a reasoning tag and never closes it is incomplete."""

    @pytest.mark.asyncio
    async def test_open_think_tag_without_close_raises(self) -> None:
        """An opening <think> with no </think> is incomplete under a normal stop."""
        text = "<think>\nThe instruction should focus on"
        reflect = _reflect(text, [_event(text, types.FinishReason.STOP)])

        with pytest.raises(IncompleteProposalError) as excinfo:
            await reflect("old", [], component_name="instruction")

        assert excinfo.value.finish_reason == "unterminated_think"
        assert excinfo.value.raw_text == text

    @pytest.mark.asyncio
    async def test_closed_think_tag_is_complete(self) -> None:
        """A closed reasoning block is returned unchanged."""
        text = "<think>plan</think>\nBe concise."
        reflect = _reflect(text, [_event(text, types.FinishReason.STOP)])

        proposed, _, _ = await reflect("old", [], component_name="instruction")

        assert proposed == text

    @pytest.mark.asyncio
    async def test_tag_list_is_configurable(self) -> None:
        """Only the configured tags are checked."""
        text = "<scratch>\nworking"
        reflect = _reflect(
            text, [_event(text, types.FinishReason.STOP)], reasoning_tags=("scratch",)
        )
        with pytest.raises(IncompleteProposalError) as excinfo:
            await reflect("old", [], component_name="instruction")
        assert excinfo.value.finish_reason == "unterminated_scratch"

        think = "<think>\nworking"
        reflect = _reflect(
            think, [_event(think, types.FinishReason.STOP)], reasoning_tags=("scratch",)
        )
        proposed, _, _ = await reflect("old", [], component_name="instruction")
        assert proposed == think

    @pytest.mark.asyncio
    async def test_default_tags_cover_common_names(self) -> None:
        """think, thinking and reasoning are checked by default."""
        for tag in ("think", "thinking", "reasoning"):
            text = f"<{tag}>\nworking"
            reflect = _reflect(text, [_event(text, types.FinishReason.STOP)])
            with pytest.raises(IncompleteProposalError) as excinfo:
                await reflect("old", [], component_name="instruction")
            assert excinfo.value.finish_reason == f"unterminated_{tag}"

    @pytest.mark.asyncio
    async def test_tag_in_the_middle_of_the_text_is_not_checked(self) -> None:
        """Only a tag that opens the text marks an unterminated envelope."""
        text = "Be concise. Do not print <think> tags."
        reflect = _reflect(text, [_event(text, types.FinishReason.STOP)])

        proposed, _, _ = await reflect("old", [], component_name="instruction")

        assert proposed == text


class TestLengthStopClassifier:
    """is_length_stop recognises the enum, its name and litellm's word."""

    @pytest.mark.parametrize(
        "value",
        [types.FinishReason.MAX_TOKENS, "MAX_TOKENS", "max_tokens", "length"],
    )
    def test_length_stops(self, value: Any) -> None:
        """Every spelling of a length stop is recognised."""
        assert is_length_stop(value) is True

    @pytest.mark.parametrize(
        "value", [types.FinishReason.STOP, "STOP", "stop", None, "", "SAFETY"]
    )
    def test_other_stops(self, value: Any) -> None:
        """Normal, blocked and missing finish reasons are not length stops."""
        assert is_length_stop(value) is False


class IncompleteAdapter:
    """Fake adapter whose proposals are scripted to be cut off or complete.

    Attributes:
        script (list[str]): Per-iteration script: ``"incomplete"`` raises
            ``IncompleteProposalError``; any other text is the proposal.
        calls (list[int]): Row counts of each ``evaluate()`` call.
    """

    def __init__(self, script: list[str]) -> None:
        """Store the script.

        Args:
            script: Per-iteration entries, consumed in order.
        """
        self.script = list(script)
        self.calls: list[int] = []

    async def evaluate(
        self,
        batch: list[dict[str, str]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Any, Any]:
        """Score 1.0 for the instruction "better" and 0.5 otherwise.

        Args:
            batch: Rows to evaluate.
            candidate: Candidate components.
            capture_traces: Whether traces were requested.

        Returns:
            A batch with one score per row.
        """
        self.calls.append(len(batch))
        score = 1.0 if candidate["instruction"] == "better" else 0.5
        return EvaluationBatch(
            outputs=[""] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[Any, Any],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Return an empty reflective dataset.

        Args:
            candidate: Ignored.
            eval_batch: Ignored.
            components_to_update: Ignored.

        Returns:
            An empty mapping.
        """
        return {}

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Raise the scripted error or return the scripted proposal.

        Args:
            candidate: Ignored.
            reflective_dataset: Ignored.
            components_to_update: Ignored.

        Returns:
            The next scripted proposal.

        Raises:
            IncompleteProposalError: When the script entry is ``"incomplete"``.
        """
        entry = self.script.pop(0)
        if entry == "incomplete":
            raise IncompleteProposalError(
                "instruction", finish_reason="MAX_TOKENS", raw_text=_CUT
            )
        return {"instruction": entry}


async def _run(
    script: list[str], *, patience: int = 5, **config: Any
) -> tuple[IncompleteAdapter, Any]:
    adapter = IncompleteAdapter(script)
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=EvolutionConfig(
            max_iterations=len(script),
            patience=patience,
            min_improvement_threshold=0.0,
            **config,
        ),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=[{"input": "q1"}, {"input": "qü"}],
    )
    return adapter, await engine.run()


class TestEngineRecordsIncompleteProposal:
    """A cut-off reflection is a skipped iteration, not an evaluation."""

    @pytest.mark.asyncio
    async def test_incomplete_is_recorded_and_the_run_continues(self) -> None:
        """Nothing is evaluated for the cut-off text; the next proposal is."""
        adapter, result = await _run(["incomplete", "better"])

        first, second = result.iteration_history
        assert first.accepted is False
        assert first.skip_reason == "incomplete_proposal"
        assert first.score == 0.0
        assert first.component_text == _CUT
        assert first.evolved_component == "instruction"
        assert second.accepted is True
        assert second.skip_reason is None
        assert result.total_iterations == 2
        assert adapter.calls == [2, 2]
        assert result.evolved_components["instruction"] == "better"

    @pytest.mark.asyncio
    async def test_incompletes_count_toward_patience(self) -> None:
        """Consecutive cut-offs exhaust patience and end the run with the seed."""
        adapter, result = await _run(
            ["incomplete", "incomplete", "incomplete"], patience=2
        )

        assert result.total_iterations == 2
        assert [r.skip_reason for r in result.iteration_history] == [
            "incomplete_proposal",
            "incomplete_proposal",
        ]
        assert adapter.calls == [2]
        assert result.evolved_components["instruction"] == "seed"

    @pytest.mark.asyncio
    async def test_skipped_record_reaches_on_iteration(self) -> None:
        """on_iteration sees the skipped record with no candidate id."""
        seen: list[tuple[str | None, str | None]] = []

        def on_iteration(record: Any, candidate_id: str | None) -> None:
            """Record the skip reason and candidate id of each iteration.

            Args:
                record: The appended iteration record.
                candidate_id: Id of the evaluated candidate, or None.
            """
            seen.append((record.skip_reason, candidate_id))

        await _run(["incomplete", "better"], on_iteration=on_iteration)

        assert len(seen) == 2
        assert seen[0] == ("incomplete_proposal", None)
        assert seen[1][0] is None
        assert isinstance(seen[1][1], str)

    @pytest.mark.asyncio
    async def test_skip_is_logged_with_length_and_finish_reason(self) -> None:
        """The skip log carries the raw length and the finish reason."""
        with capture_logs() as logs:
            await _run(["incomplete", "better"])

        skips = [
            e
            for e in logs
            if e["event"] == "evolution.proposal_skipped"
            and e.get("reason") == "incomplete_proposal"
        ]
        assert len(skips) == 1
        assert skips[0]["component"] == "instruction"
        assert skips[0]["finish_reason"] == "MAX_TOKENS"
        assert skips[0]["response_length"] == len(_CUT)

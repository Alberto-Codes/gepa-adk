"""Acceptance tests for counting the reflection agent's token usage.

The reflection function reports the usage of each reflection call, the
proposer rolls the calls of one ``propose()`` into ``last_token_usage``,
and the engine folds that rollup into the iteration and run rollups under
a ``reflection`` split next to the ``evaluation`` split, so a run's cost
is complete (GitHub issue 428).

Notes:
    A fake executor answers every call with one usage-bearing event, so the
    expected splits are known without an LLM. A reflection executor that
    captures no events leaves the reflection split unknown, never zero.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from google.adk.agents import LlmAgent

from gepa_adk import evolve
from gepa_adk.domain.models import (
    CURRENT_SCHEMA_VERSION,
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    IterationRecord,
    TokenRollup,
    TokenUsage,
)
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus
from tests.conftest import MockScorer
from tests.fixtures.adapters import create_mock_adapter
from tests.unit.test_api_result_passthrough import (
    _INPUT_TOKENS,
    _OUTPUT_TOKENS,
    _TOTAL_TOKENS,
    UsageReportingExecutor,
)

pytestmark = pytest.mark.unit

_USAGE = TokenUsage(
    input_tokens=_INPUT_TOKENS,
    output_tokens=_OUTPUT_TOKENS,
    total_tokens=_TOTAL_TOKENS,
)
_ONE_CALL = TokenRollup(
    input_tokens=_INPUT_TOKENS,
    output_tokens=_OUTPUT_TOKENS,
    total_tokens=_TOTAL_TOKENS,
    rows_counted=1,
    rows_unknown=0,
)
_ONE_UNKNOWN_CALL = TokenRollup(
    input_tokens=None,
    output_tokens=None,
    total_tokens=None,
    rows_counted=0,
    rows_unknown=1,
)
_TRIALS = {"instruction": [{"input": "q", "output": "a", "feedback": {"score": 0.0}}]}


def _leaf(tokens: int, rows: int) -> TokenRollup:
    """Build a plain rollup with equal counters.

    Args:
        tokens: Value for each of the three counters.
        rows: Rows counted.

    Returns:
        A rollup without splits.
    """
    return TokenRollup(
        input_tokens=tokens,
        output_tokens=tokens,
        total_tokens=tokens,
        rows_counted=rows,
        rows_unknown=0,
    )


class TestTokenRollupSplits:
    """A rollup carries an evaluation and a reflection split."""

    def test_leaf_has_no_splits(self) -> None:
        """A rollup built from rows has no split."""
        leaf = _leaf(3, 1)
        assert leaf.evaluation is None
        assert leaf.reflection is None

    def test_split_sums_its_parts(self) -> None:
        """The top-level counters cover both splits."""
        rollup = TokenRollup.split(evaluation=_leaf(30, 3), reflection=_ONE_CALL)
        assert rollup.input_tokens == 30 + _INPUT_TOKENS
        assert rollup.output_tokens == 30 + _OUTPUT_TOKENS
        assert rollup.total_tokens == 30 + _TOTAL_TOKENS
        assert rollup.rows_counted == 4
        assert rollup.rows_unknown == 0
        assert rollup.evaluation == _leaf(30, 3)
        assert rollup.reflection == _ONE_CALL

    def test_split_with_unknown_reflection_keeps_the_evaluation_counters(
        self,
    ) -> None:
        """An unknown reflection call is counted in rows_unknown, not as zero."""
        rollup = TokenRollup.split(
            evaluation=_leaf(30, 3), reflection=_ONE_UNKNOWN_CALL
        )
        assert rollup.input_tokens == 30
        assert rollup.rows_counted == 3
        assert rollup.rows_unknown == 1
        assert rollup.reflection == _ONE_UNKNOWN_CALL

    def test_combine_adds_split_wise(self) -> None:
        """Combining two split rollups combines each split."""
        first = TokenRollup.split(evaluation=_leaf(30, 3), reflection=_ONE_CALL)
        second = TokenRollup.split(
            evaluation=_leaf(20, 2), reflection=_ONE_UNKNOWN_CALL
        )
        combined = first.combine(second)
        assert combined.evaluation == _leaf(50, 5)
        assert combined.reflection == TokenRollup(
            input_tokens=_INPUT_TOKENS,
            output_tokens=_OUTPUT_TOKENS,
            total_tokens=_TOTAL_TOKENS,
            rows_counted=1,
            rows_unknown=1,
        )
        assert combined.input_tokens == 50 + _INPUT_TOKENS
        assert combined.rows_counted == 6
        assert combined.rows_unknown == 1

    def test_combine_treats_a_leaf_as_evaluation(self) -> None:
        """A rollup without splits combined with a split one counts as evaluation."""
        combined = _leaf(30, 3).combine(
            TokenRollup.split(evaluation=_leaf(20, 2), reflection=_ONE_CALL)
        )
        assert combined.evaluation == _leaf(50, 5)
        assert combined.reflection == _ONE_CALL

    def test_to_dict_writes_both_splits_and_round_trips(self) -> None:
        """The dict carries ``evaluation`` and ``reflection`` and loads back."""
        rollup = TokenRollup.split(
            evaluation=_leaf(30, 3), reflection=_ONE_UNKNOWN_CALL
        )
        data = rollup.to_dict()
        assert data["evaluation"] == _leaf(30, 3).to_dict()
        assert data["reflection"]["input_tokens"] == "unknown"
        assert data["reflection"]["rows_unknown"] == 1
        assert TokenRollup.from_dict(data) == rollup
        leaf_data = _leaf(3, 1).to_dict()
        assert leaf_data["evaluation"] is None
        assert leaf_data["reflection"] is None
        assert TokenRollup.from_dict(leaf_data) == _leaf(3, 1)

    def test_dict_without_split_keys_loads_as_a_leaf(self) -> None:
        """A version 5 rollup dict has no split keys."""
        data = {
            "input_tokens": 3,
            "output_tokens": 3,
            "total_tokens": 3,
            "rows_counted": 1,
            "rows_unknown": 0,
        }
        assert TokenRollup.from_dict(data) == _leaf(3, 1)


class TestSchemaVersionSix:
    """A version 5 result loads with its usage as the evaluation split."""

    def test_current_schema_version_is_six(self) -> None:
        """The splits are a version 6 field."""
        assert CURRENT_SCHEMA_VERSION == 6

    def test_version_5_dict_migrates_usage_into_the_evaluation_split(self) -> None:
        """Old counters become the evaluation split; reflection is None."""
        old_usage = _leaf(30, 3).to_dict()
        record = IterationRecord(
            iteration_number=1,
            score=1.0,
            component_text="x",
            evolved_component="instruction",
            accepted=True,
        ).to_dict()
        record["token_usage"] = dict(old_usage)
        data = {
            "schema_version": 5,
            "original_score": 0.5,
            "final_score": 1.0,
            "evolved_components": {"instruction": "x"},
            "iteration_history": [record],
            "total_iterations": 1,
            "token_usage": dict(old_usage),
        }

        result = EvolutionResult.from_dict(data)

        assert result.schema_version == 6
        assert result.token_usage is not None
        assert result.token_usage.evaluation == _leaf(30, 3)
        assert result.token_usage.reflection is None
        assert result.token_usage.input_tokens == 30
        usage = result.iteration_history[0].token_usage
        assert usage is not None
        assert usage.evaluation == _leaf(30, 3)
        assert usage.reflection is None
        assert result.to_dict()["token_usage"]["reflection"] is None

    def test_version_5_none_usage_stays_none(self) -> None:
        """A result saved without usage still loads with None."""
        data = {
            "schema_version": 5,
            "original_score": 0.5,
            "final_score": 1.0,
            "evolved_components": {"instruction": "x"},
            "iteration_history": [],
            "total_iterations": 0,
            "token_usage": None,
        }
        assert EvolutionResult.from_dict(data).token_usage is None


class _UsageScript:
    """Reflection function that returns scripted (text, reasoning, usage) tuples.

    Attributes:
        script (list[BaseException | tuple[Any, ...]]): Entries consumed in
            order; an exception is raised, a tuple is returned as is.
        calls (int): Reflection calls made so far.
    """

    def __init__(self, script: list[BaseException | tuple[Any, ...]]) -> None:
        """Store the script.

        Args:
            script: Entries consumed in order.
        """
        self.script = list(script)
        self.calls = 0

    async def __call__(
        self, component_text: str, trials: list[dict[str, Any]], component: str
    ) -> Any:
        """Raise or return the next scripted entry.

        Args:
            component_text: Current text (unused).
            trials: Trial records (unused).
            component: Component name (unused).

        Returns:
            The scripted tuple.

        Raises:
            BaseException: The scripted exception, when the entry is one.
        """
        self.calls += 1
        entry = self.script.pop(0)
        if isinstance(entry, BaseException):
            raise entry
        return entry


async def _propose(fn: _UsageScript) -> AsyncReflectiveMutationProposer:
    """Run one ``propose()`` with the scripted reflection function.

    Args:
        fn: The scripted reflection function.

    Returns:
        The proposer, after the call.
    """
    proposer = AsyncReflectiveMutationProposer(
        adk_reflection_fn=fn, retry_backoff_seconds=0.0
    )
    await proposer.propose(
        candidate={"instruction": "seed"},
        reflective_dataset=_TRIALS,
        components_to_update=["instruction"],
    )
    return proposer


class TestProposerReportsReflectionUsage:
    """``last_token_usage`` rolls up the reflection calls of one propose()."""

    @pytest.mark.asyncio
    async def test_three_tuple_reports_the_calls_usage(self) -> None:
        """One call with usage gives one counted row."""
        proposer = await _propose(_UsageScript([("Better", None, _USAGE)]))
        assert proposer.last_token_usage == _ONE_CALL

    @pytest.mark.asyncio
    async def test_two_tuple_and_none_usage_are_unknown(self) -> None:
        """A function without usage, or with None, gives one unknown row."""
        legacy = await _propose(_UsageScript([("Better", None)]))
        assert legacy.last_token_usage == _ONE_UNKNOWN_CALL
        none = await _propose(_UsageScript([("Better", None, None)]))
        assert none.last_token_usage == _ONE_UNKNOWN_CALL

    @pytest.mark.asyncio
    async def test_a_raised_call_is_not_a_row_and_the_retry_is(self) -> None:
        """A retried provider error costs no counted row; the retry does."""
        fn = _UsageScript([RuntimeError("503 UNAVAILABLE"), ("Better", None, _USAGE)])
        proposer = await _propose(fn)
        assert fn.calls == 2
        assert proposer.last_token_usage == _ONE_CALL

    @pytest.mark.asyncio
    async def test_usage_resets_per_propose(self) -> None:
        """A second propose() starts from zero."""
        fn = _UsageScript([("Better", None, _USAGE), ("Best", None, None)])
        proposer = AsyncReflectiveMutationProposer(
            adk_reflection_fn=fn, retry_backoff_seconds=0.0
        )
        for _ in range(2):
            await proposer.propose(
                candidate={"instruction": "seed"},
                reflective_dataset=_TRIALS,
                components_to_update=["instruction"],
            )
        assert proposer.last_token_usage == _ONE_UNKNOWN_CALL


class _EventExecutor:
    """Executor stub whose result carries the given captured events.

    Attributes:
        events (list[Any] | None): Events to return on every call.
    """

    def __init__(self, events: list[Any] | None) -> None:
        """Store the events.

        Args:
            events: Events to return, or None to capture nothing.
        """
        self.events = events

    async def execute_agent(
        self, agent: Any, input_text: str, **kwargs: Any
    ) -> ExecutionResult:
        """Return a proposal with the stored events.

        Args:
            agent: Ignored.
            input_text: Ignored.
            **kwargs: Ignored.

        Returns:
            A successful result.
        """
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            session_id="stub",
            extracted_value="Better",
            captured_events=self.events,
        )


class TestReflectionFunctionReportsUsage:
    """``create_adk_reflection_fn`` returns the call's usage from its events."""

    @pytest.mark.asyncio
    async def test_usage_from_captured_events(self) -> None:
        """The usage on the captured events is the third element."""
        event = SimpleNamespace(
            usage_metadata=SimpleNamespace(
                prompt_token_count=_INPUT_TOKENS,
                candidates_token_count=_OUTPUT_TOKENS,
                total_token_count=_TOTAL_TOKENS,
            )
        )
        agent = LlmAgent(name="reflector", model="ollama_chat/gpt-oss:20b")
        reflect = create_adk_reflection_fn(agent, executor=_EventExecutor([event]))
        text, reasoning, usage = await reflect("seed", [], "instruction")
        assert text == "Better"
        assert reasoning is None
        assert usage == _USAGE

    @pytest.mark.asyncio
    async def test_no_events_means_no_usage(self) -> None:
        """An executor that captures no events reports None, not zero."""
        agent = LlmAgent(name="reflector", model="ollama_chat/gpt-oss:20b")
        reflect = create_adk_reflection_fn(agent, executor=_EventExecutor(None))
        _, _, usage = await reflect("seed", [], "instruction")
        assert usage is None


class NoReflectionEventsExecutor(UsageReportingExecutor):
    """Usage-reporting executor whose reflection calls capture no events."""

    async def execute_agent(
        self, agent: Any, input_text: str, **kwargs: Any
    ) -> ExecutionResult:
        """Drop the captured events on reflection calls.

        Args:
            agent: The agent to run.
            input_text: The user message.
            **kwargs: The executor keyword arguments.

        Returns:
            The parent's result, without events for a reflection call.
        """
        result = await super().execute_agent(agent, input_text, **kwargs)
        if "component_text" in (kwargs.get("session_state") or {}):
            return ExecutionResult(
                status=result.status,
                session_id=result.session_id,
                extracted_value=result.extracted_value,
                captured_events=None,
            )
        return result


def _agents() -> tuple[LlmAgent, LlmAgent]:
    """Build the evolving agent and the reflector.

    Returns:
        The two agents.
    """
    agent = LlmAgent(
        name="answerer",
        model="ollama_chat/gpt-oss:20b",
        instruction="Answer the question.",
    )
    reflector = LlmAgent(
        name="reflector",
        model="ollama_chat/gpt-oss:20b",
        instruction="Improve the component.",
    )
    return agent, reflector


_TRAINSET = [{"input": "row-a"}, {"input": "row-b"}, {"input": "row-c"}]


class TestRunRollupSplitsReflection:
    """The run and each iteration distinguish evaluation from reflection."""

    @pytest.mark.asyncio
    async def test_reflection_calls_are_counted_per_iteration_and_per_run(
        self,
    ) -> None:
        """Two iterations, two reflection calls, each on its record and in the run."""
        agent, reflector = _agents()
        executor = UsageReportingExecutor()

        result = await evolve(
            agent,
            _TRAINSET,
            scorer=MockScorer(1.0),
            reflection_agent=reflector,
            config=EvolutionConfig(max_iterations=2, patience=10, seed=7),
            executor=executor,
        )

        assert executor.reflection_calls == 2
        records = result.iteration_history
        assert len(records) == 2
        for record in records:
            assert record.token_usage is not None
            assert record.token_usage.reflection == _ONE_CALL
            assert record.token_usage.evaluation is not None
            assert record.token_usage.evaluation.rows_counted == len(_TRAINSET)
            assert record.token_usage.input_tokens == (
                record.token_usage.evaluation.input_tokens + _INPUT_TOKENS
            )
        assert result.token_usage is not None
        assert result.token_usage.reflection == TokenRollup(
            input_tokens=2 * _INPUT_TOKENS,
            output_tokens=2 * _OUTPUT_TOKENS,
            total_tokens=2 * _TOTAL_TOKENS,
            rows_counted=2,
            rows_unknown=0,
        )
        evaluation = result.token_usage.evaluation
        assert evaluation is not None
        assert evaluation.rows_counted == 3 * len(_TRAINSET)
        assert result.token_usage.input_tokens == (
            evaluation.input_tokens + 2 * _INPUT_TOKENS
        )
        assert result.token_usage.rows_counted == evaluation.rows_counted + 2

    @pytest.mark.asyncio
    async def test_reflection_without_events_is_unknown(self) -> None:
        """A reflection executor that captures no events leaves the split unknown."""
        agent, reflector = _agents()
        executor = NoReflectionEventsExecutor()

        result = await evolve(
            agent,
            _TRAINSET,
            scorer=MockScorer(1.0),
            reflection_agent=reflector,
            config=EvolutionConfig(max_iterations=2, patience=10, seed=7),
            executor=executor,
        )

        for record in result.iteration_history:
            assert record.token_usage is not None
            assert record.token_usage.reflection == _ONE_UNKNOWN_CALL
            assert record.token_usage.evaluation is not None
            assert record.token_usage.input_tokens == (
                record.token_usage.evaluation.input_tokens
            )
        assert result.token_usage is not None
        assert result.token_usage.reflection == TokenRollup(
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            rows_counted=0,
            rows_unknown=2,
        )
        assert result.token_usage.rows_unknown == 2
        assert result.token_usage.evaluation is not None
        assert result.token_usage.input_tokens == (
            result.token_usage.evaluation.input_tokens
        )

    @pytest.mark.asyncio
    async def test_adapter_without_a_proposer_leaves_reflection_none(self) -> None:
        """An adapter that proposes without the proposer reports no reflection split."""

        async def propose(candidate: Any, dataset: Any, components: Any) -> dict:
            return {"instruction": "better"}

        adapter = create_mock_adapter(scores=[0.5, 0.7], custom_propose=propose)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=EvolutionConfig(max_iterations=1, min_improvement_threshold=0.0),
            initial_candidate=Candidate(components={"instruction": "seed"}),
            batch=[{"input": "q1"}, {"input": "q2"}],
        )
        result = await engine.run()

        record = result.iteration_history[0]
        assert record.token_usage is not None
        assert record.token_usage.reflection is None
        assert result.token_usage is not None
        assert result.token_usage.reflection is None

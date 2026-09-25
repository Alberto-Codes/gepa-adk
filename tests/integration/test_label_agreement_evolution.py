"""Acceptance tests for label-agreement scoring of a schema agent.

A schema agent evaluated over rows that carry ``expected`` is scored by
agreement between a named output field and the label, through the
``scorer=`` keyword rather than a critic. The score must change when the
label changes.

Notes:
    The executor is a stub that returns fixed JSON, so no LLM runs. The
    adapter, scorer and evaluation path are real.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from google.adk.agents import LlmAgent
from pydantic import BaseModel

from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter
from gepa_adk.adapters.scoring import LabelAgreementScorer
from gepa_adk.ports import Scorer
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

pytestmark = pytest.mark.integration


class Decision(BaseModel):
    """Output schema with a label field and no self-reported score."""

    label: str
    confidence: float


class FixedJsonExecutor:
    """Executor stub that returns one fixed JSON document for every call.

    Attributes:
        payload (str): JSON text returned as ``extracted_value``.
        calls (int): Number of executions so far.
    """

    def __init__(self, payload: str) -> None:
        """Store the payload every execution returns.

        Args:
            payload: JSON text returned as ``extracted_value``.
        """
        self.payload = payload
        self.calls = 0

    async def execute_agent(
        self, agent: Any, input_text: str, **kwargs: Any
    ) -> ExecutionResult:
        """Return the fixed payload as a successful execution.

        Args:
            agent: Ignored.
            input_text: Ignored.
            **kwargs: Ignored.

        Returns:
            A successful ExecutionResult carrying the payload.
        """
        self.calls += 1
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            session_id="stub",
            extracted_value=self.payload,
        )


@pytest.fixture
def schema_agent() -> LlmAgent:
    """Agent with an output_schema and no critic.

    Returns:
        An LlmAgent whose output_schema is Decision.
    """
    return LlmAgent(
        name="decider",
        model="gemini-3.8-flash",
        instruction="Decide.",
        output_schema=Decision,
    )


def _adapter(agent: LlmAgent, payload: str) -> ADKAdapter:
    return ADKAdapter(
        agent=agent,
        scorer=LabelAgreementScorer(field="label"),
        executor=FixedJsonExecutor(payload),
        proposer=MagicMock(),
    )


class TestLabelAgreementScoring:
    """Scores follow agreement between the output field and ``expected``."""

    def test_label_agreement_scorer_satisfies_scorer_protocol(self) -> None:
        """The scorer is usable through the scorer= keyword."""
        assert isinstance(LabelAgreementScorer(field="label"), Scorer)

    @pytest.mark.asyncio
    async def test_score_changes_when_label_changes(
        self, schema_agent: LlmAgent
    ) -> None:
        """The same output scores 1.0 against a matching label and 0.0 otherwise."""
        adapter = _adapter(schema_agent, '{"label": "spam", "confidence": 0.9}')

        matching = await adapter.evaluate(
            [{"input": "Buy now!!!", "expected": "spam"}],
            {"instruction": "Decide."},
        )
        differing = await adapter.evaluate(
            [{"input": "Buy now!!!", "expected": "ham"}],
            {"instruction": "Decide."},
        )

        assert matching.scores == [1.0]
        assert differing.scores == [0.0]

    @pytest.mark.asyncio
    async def test_mixed_batch_scores_each_row_by_its_own_label(
        self, schema_agent: LlmAgent
    ) -> None:
        """A batch with one matching and one differing label scores [1.0, 0.0]."""
        adapter = _adapter(schema_agent, '{"label": "spam", "confidence": 0.9}')

        batch = await adapter.evaluate(
            [
                {"input": "Buy now!!!", "expected": "spam"},
                {"input": "Lunch at noon?", "expected": "ham"},
            ],
            {"instruction": "Decide."},
        )

        assert batch.scores == [1.0, 0.0]
        assert len(batch.scores) == 2

    @pytest.mark.asyncio
    async def test_row_without_expected_scores_zero_with_reason(
        self, schema_agent: LlmAgent
    ) -> None:
        """A row with no label cannot agree with anything and scores 0.0."""
        adapter = _adapter(schema_agent, '{"label": "spam", "confidence": 0.9}')

        batch = await adapter.evaluate(
            [{"input": "Buy now!!!"}], {"instruction": "Decide."}
        )

        assert batch.scores == [0.0]
        assert batch.metadata is not None
        assert batch.metadata[0]["reason"] == "missing_expected"


class TestLabelAgreementScorerDirect:
    """Direct calls cover the field, whole-output and error paths."""

    def test_field_match_is_exact_after_strip(self) -> None:
        """Whitespace around the label is ignored; case is not."""
        scorer = LabelAgreementScorer(field="label")
        score, meta = scorer.score("q", '{"label": " spam "}', "spam")
        assert score == 1.0
        assert meta["agreement"] is True
        assert meta["actual"] == "spam"
        score, _ = scorer.score("q", '{"label": "Spam"}', "spam")
        assert score == 0.0

    def test_whole_output_mode_compares_json_or_text(self) -> None:
        """Without a field, equal JSON documents agree regardless of spacing."""
        scorer = LabelAgreementScorer()
        score, _ = scorer.score("q", '{"a": 1, "b": 2}', '{"b":2,"a":1}')
        assert score == 1.0
        score, _ = scorer.score("q", "plain answer", "plain answer")
        assert score == 1.0
        score, _ = scorer.score("q", "plain answer", "other")
        assert score == 0.0

    def test_output_that_is_not_json_scores_zero(self) -> None:
        """A field scorer given non-JSON output reports the parse failure."""
        scorer = LabelAgreementScorer(field="label")
        score, meta = scorer.score("q", "not json", "spam")
        assert score == 0.0
        assert meta["reason"] == "output_not_json"

    def test_missing_field_scores_zero(self) -> None:
        """A field absent from the output reports field_missing."""
        scorer = LabelAgreementScorer(field="label")
        score, meta = scorer.score("q", '{"other": "spam"}', "spam")
        assert score == 0.0
        assert meta["reason"] == "field_missing"

    @pytest.mark.asyncio
    async def test_async_score_matches_score(self) -> None:
        """async_score returns the same result as score."""
        scorer = LabelAgreementScorer(field="label")
        assert await scorer.async_score("q", '{"label": "x"}', "x") == scorer.score(
            "q", '{"label": "x"}', "x"
        )

"""Acceptance tests for issue 387: warn when a schema agent self-grades labelled rows.

When ``evolve()`` selects ``SchemaBasedScorer`` (no ``critic=``, no
``scorer=``, agent has an ``output_schema``) and any trainset row carries
``expected``, it logs a warning that names ``LabelAgreementScorer`` and the
``scorer=`` keyword. Behaviour is unchanged.

Notes:
    The engine and adapter are patched so no LLM is built or called; the
    warning is read with ``structlog.testing.capture_logs``.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from structlog.testing import capture_logs

from gepa_adk import evolve
from gepa_adk.domain.models import EvolutionResult
from tests.conftest import MockScorer

pytestmark = pytest.mark.unit

_EVENT = "scorer.schema_based_over_labelled_trainset"


class Graded(BaseModel):
    """Self-scoring schema that selects SchemaBasedScorer."""

    score: float = Field(ge=0.0, le=1.0)
    answer: str


@pytest.fixture
def schema_agent() -> LlmAgent:
    """An agent with an output_schema.

    Returns:
        An LlmAgent whose output_schema carries a score field.
    """
    return LlmAgent(
        name="graded",
        model="gemini-3.8-flash",
        instruction="Answer.",
        output_schema=Graded,
    )


async def _evolve(
    agent: LlmAgent, trainset: list[dict[str, Any]], **kwargs: Any
) -> list[MutableMapping[str, Any]]:
    engine = MagicMock()
    engine.run = AsyncMock(
        return_value=EvolutionResult(
            original_score=0.5,
            final_score=0.5,
            evolved_components={"instruction": "Answer."},
            iteration_history=[],
            total_iterations=0,
        )
    )
    with (
        patch("gepa_adk.api.AsyncGEPAEngine", return_value=engine),
        patch("gepa_adk.api.ADKAdapter", return_value=MagicMock()),
        capture_logs() as logs,
    ):
        await evolve(agent, trainset, **kwargs)
    return [e for e in logs if e["event"] == _EVENT]


class TestSchemaScorerOverLabelledRowsWarns:
    """The warning fires exactly when self-grading meets labelled rows."""

    @pytest.mark.asyncio
    async def test_labelled_rows_and_no_scorer_warn(
        self, schema_agent: LlmAgent
    ) -> None:
        """Two of three rows carry expected: one warning naming the fix."""
        events = await _evolve(
            schema_agent,
            [
                {"input": "q1", "expected": "a1"},
                {"input": "q2"},
                {"input": "q3", "expected": "a3"},
            ],
        )

        assert len(events) == 1
        event = events[0]
        assert event["log_level"] == "warning"
        assert event["rows_with_expected"] == 2
        assert event["rows"] == 3
        assert "LabelAgreementScorer" in event["hint"]
        assert "scorer=" in event["hint"]

    @pytest.mark.asyncio
    async def test_unlabelled_rows_do_not_warn(self, schema_agent: LlmAgent) -> None:
        """No expected anywhere, no warning."""
        events = await _evolve(schema_agent, [{"input": "q1"}, {"input": "q2"}])

        assert events == []

    @pytest.mark.asyncio
    async def test_explicit_scorer_does_not_warn(self, schema_agent: LlmAgent) -> None:
        """A caller-supplied scorer over labelled rows is not self-grading."""
        events = await _evolve(
            schema_agent, [{"input": "q1", "expected": "a1"}], scorer=MockScorer()
        )

        assert events == []

    @pytest.mark.asyncio
    async def test_critic_does_not_warn(self, schema_agent: LlmAgent) -> None:
        """A critic over labelled rows is not self-grading either."""
        critic = LlmAgent(name="critic", model="gemini-3.8-flash", instruction="Judge.")
        with patch("gepa_adk.api.CriticScorer", return_value=MockScorer()):
            events = await _evolve(
                schema_agent, [{"input": "q1", "expected": "a1"}], critic=critic
            )

        assert events == []

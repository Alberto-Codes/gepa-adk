"""Acceptance tests for the ``scorer=`` keyword on the public entry points.

Covers `evolve()`, `evolve_group()` and `evolve_workflow()` accepting a
hand-written `Scorer` implementation, and the mutual exclusion between
``critic=`` and ``scorer=``.

Notes:
    The engine and adapters are patched so no LLM is constructed or called.
    The assertions check that the caller's scorer instance is the one wired
    into the adapter, and that neither `CriticScorer` nor
    `SchemaBasedScorer` is built when a scorer is given.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent, SequentialAgent
from pydantic import BaseModel, Field

from gepa_adk import evolve, evolve_group, evolve_workflow
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import EvolutionResult
from gepa_adk.ports import Scorer
from tests.conftest import MockScorer

pytestmark = pytest.mark.unit


@pytest.fixture
def plain_agent() -> LlmAgent:
    """Agent with no output_schema, so only a critic or scorer can score it.

    Returns:
        An LlmAgent with no output_schema.
    """
    return LlmAgent(
        name="plain_agent",
        model="gemini-3.8-flash",
        instruction="Answer the question.",
    )


@pytest.fixture
def critic() -> LlmAgent:
    """Critic agent used for the mutual-exclusion checks.

    Returns:
        A critic LlmAgent.
    """
    return LlmAgent(
        name="critic",
        model="gemini-3.8-flash",
        instruction="Score responses.",
    )


@pytest.fixture
def trainset() -> list[dict[str, Any]]:
    """Two labelled rows.

    Returns:
        Two rows with input and expected.
    """
    return [
        {"input": "What is 2+2?", "expected": "4"},
        {"input": "What is 3+3?", "expected": "6"},
    ]


@pytest.fixture
def evolution_result() -> EvolutionResult:
    """Result the patched engine returns.

    Returns:
        A minimal EvolutionResult.
    """
    return EvolutionResult(
        original_score=0.5,
        final_score=0.8,
        evolved_components={"instruction": "Improved instruction"},
        iteration_history=[],
        total_iterations=1,
    )


def _patched_engine(evolution_result: EvolutionResult) -> MagicMock:
    engine = MagicMock()
    engine.run = AsyncMock(return_value=evolution_result)
    return engine


class TestEvolveAcceptsScorer:
    """`evolve()` wires a caller-supplied Scorer straight into the adapter."""

    @pytest.mark.asyncio
    async def test_evolve_uses_the_given_scorer(
        self,
        plain_agent: LlmAgent,
        trainset: list[dict[str, Any]],
        evolution_result: EvolutionResult,
    ) -> None:
        """The adapter receives the caller's scorer and no built-in scorer is made."""
        scorer = MockScorer(score_value=0.7)
        assert isinstance(scorer, Scorer)

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as engine_class,
            patch("gepa_adk.api.ADKAdapter") as adapter_class,
            patch("gepa_adk.api.CriticScorer") as critic_scorer_class,
            patch("gepa_adk.api.SchemaBasedScorer") as schema_scorer_class,
        ):
            engine_class.return_value = _patched_engine(evolution_result)
            adapter_class.return_value = MagicMock()

            result = await evolve(plain_agent, trainset, scorer=scorer)

        assert isinstance(result, EvolutionResult)
        adapter_class.assert_called_once()
        assert adapter_class.call_args.kwargs["scorer"] is scorer
        critic_scorer_class.assert_not_called()
        schema_scorer_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_scorer_takes_precedence_over_output_schema(
        self,
        trainset: list[dict[str, Any]],
        evolution_result: EvolutionResult,
    ) -> None:
        """An explicit scorer wins over the agent's output_schema fallback."""

        class OutputSchema(BaseModel):
            """Self-scoring schema that would enable SchemaBasedScorer."""

            score: float = Field(ge=0.0, le=1.0)
            result: str

        schema_agent = LlmAgent(
            name="schema_agent",
            model="gemini-3.8-flash",
            instruction="Answer.",
            output_schema=OutputSchema,
        )
        scorer = MockScorer(score_value=0.7)

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as engine_class,
            patch("gepa_adk.api.ADKAdapter") as adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as schema_scorer_class,
        ):
            engine_class.return_value = _patched_engine(evolution_result)
            adapter_class.return_value = MagicMock()

            await evolve(schema_agent, trainset, scorer=scorer)

        assert adapter_class.call_args.kwargs["scorer"] is scorer
        schema_scorer_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_critic_and_scorer_together_raise(
        self,
        plain_agent: LlmAgent,
        critic: LlmAgent,
        trainset: list[dict[str, Any]],
    ) -> None:
        """Passing critic and scorer together is a ConfigurationError."""
        with pytest.raises(ConfigurationError, match="critic.*scorer|scorer.*critic"):
            await evolve(plain_agent, trainset, critic=critic, scorer=MockScorer())

    @pytest.mark.asyncio
    async def test_object_without_score_methods_raises(
        self,
        plain_agent: LlmAgent,
        trainset: list[dict[str, Any]],
    ) -> None:
        """An object that does not satisfy Scorer is a ConfigurationError."""
        with pytest.raises(ConfigurationError, match="scorer") as exc_info:
            await evolve(plain_agent, trainset, scorer=object())
        assert exc_info.value.field == "scorer"


class TestEvolveGroupAcceptsScorer:
    """`evolve_group()` passes a caller-supplied Scorer to MultiAgentAdapter."""

    @pytest.fixture
    def agents(self) -> dict[str, LlmAgent]:
        """Two agents where the primary has no output_schema.

        Returns:
            A generator and a refiner LlmAgent keyed by name.
        """
        return {
            "generator": LlmAgent(
                name="generator",
                model="gemini-3.8-flash",
                instruction="Generate content",
            ),
            "refiner": LlmAgent(
                name="refiner",
                model="gemini-3.8-flash",
                instruction="Refine content",
            ),
        }

    @pytest.mark.asyncio
    async def test_evolve_group_uses_the_given_scorer(
        self,
        agents: dict[str, LlmAgent],
        trainset: list[dict[str, Any]],
    ) -> None:
        """MultiAgentAdapter receives the caller's scorer and no CriticScorer is made."""
        scorer = MockScorer(score_value=0.7)

        with (
            patch("gepa_adk.api.MultiAgentAdapter") as adapter_class,
            patch("gepa_adk.api.AsyncGEPAEngine") as engine_class,
            patch("gepa_adk.api.CriticScorer") as critic_scorer_class,
            patch("gepa_adk.api.create_adk_reflection_fn"),
            patch("gepa_adk.api.AsyncReflectiveMutationProposer"),
        ):
            engine = MagicMock()
            engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"refiner.instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                )
            )
            engine_class.return_value = engine

            await evolve_group(
                agents=agents,
                primary="refiner",
                trainset=trainset,
                scorer=scorer,
            )

        adapter_class.assert_called_once()
        assert adapter_class.call_args.kwargs["scorer"] is scorer
        critic_scorer_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_evolve_group_critic_and_scorer_together_raise(
        self,
        agents: dict[str, LlmAgent],
        critic: LlmAgent,
        trainset: list[dict[str, Any]],
    ) -> None:
        """Passing critic and scorer together is a ConfigurationError."""
        with pytest.raises(ConfigurationError, match="critic.*scorer|scorer.*critic"):
            await evolve_group(
                agents=agents,
                primary="refiner",
                trainset=trainset,
                critic=critic,
                scorer=MockScorer(),
            )


class TestEvolveWorkflowAcceptsScorer:
    """`evolve_workflow()` forwards a caller-supplied Scorer to evolve_group()."""

    @pytest.fixture
    def workflow(self, plain_agent: LlmAgent) -> SequentialAgent:
        """Sequential workflow wrapping the plain agent.

        Returns:
            A SequentialAgent whose only sub-agent is the plain agent.
        """
        return SequentialAgent(name="workflow", sub_agents=[plain_agent])

    @pytest.mark.asyncio
    async def test_evolve_workflow_forwards_scorer(
        self,
        workflow: SequentialAgent,
        trainset: list[dict[str, Any]],
    ) -> None:
        """evolve_workflow() passes the scorer through to evolve_group()."""
        scorer = MockScorer(score_value=0.7)

        with patch("gepa_adk.api.evolve_group") as evolve_group_mock:
            evolve_group_mock.return_value = MagicMock(
                evolved_components={"plain_agent.instruction": "evolved"},
                original_score=0.5,
                final_score=0.8,
                primary_agent="plain_agent",
                iteration_history=[],
                total_iterations=1,
            )

            await evolve_workflow(workflow=workflow, trainset=trainset, scorer=scorer)

        evolve_group_mock.assert_called_once()
        assert evolve_group_mock.call_args.kwargs["scorer"] is scorer

    @pytest.mark.asyncio
    async def test_evolve_workflow_critic_and_scorer_together_raise(
        self,
        workflow: SequentialAgent,
        critic: LlmAgent,
        trainset: list[dict[str, Any]],
    ) -> None:
        """Passing critic and scorer together is a ConfigurationError."""
        with pytest.raises(ConfigurationError, match="critic.*scorer|scorer.*critic"):
            await evolve_workflow(
                workflow=workflow,
                trainset=trainset,
                critic=critic,
                scorer=MockScorer(),
            )

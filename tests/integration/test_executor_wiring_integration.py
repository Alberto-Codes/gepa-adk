"""Integration tests for executor wiring across evolution pipeline.

This module verifies that ``evolve_group()`` and ``evolve_workflow()`` create
a single ``AgentExecutor`` instance and thread it to every internal consumer
(CriticScorer, MultiAgentAdapter, reflection function). Unlike the unit tests
in ``test_api_session_service.py`` which check each consumer in isolation,
these tests assert shared-identity across ALL consumers in a single call.

These tests require zero external credentials and run in every CI pipeline.

Note:
    These tests complement the real-API tests in
    ``test_multi_agent_executor_integration.py`` (marked ``@pytest.mark.api``)
    by verifying the same wiring concern without network dependencies.

See Also:
    - ``tests/unit/test_api_session_service.py``: Per-consumer unit tests
    - ``tests/integration/test_multi_agent_executor_integration.py``: Real-API tests
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent, SequentialAgent
from pydantic import BaseModel, Field

pytestmark = pytest.mark.integration


class CriticOutput(BaseModel):
    """Simple critic output schema for testing."""

    score: float = Field(ge=0.0, le=1.0)
    feedback: str = ""


@pytest.fixture
def multi_agents() -> dict[str, LlmAgent]:
    """Create a two-agent pipeline for multi-agent evolution tests."""
    generator = LlmAgent(
        name="generator",
        model="gemini-2.5-flash",
        instruction="Answer the question simply and clearly.",
        output_key="draft_answer",
    )
    reviewer = LlmAgent(
        name="reviewer",
        model="gemini-2.5-flash",
        instruction="Review the draft answer: {draft_answer}. Provide final answer.",
    )
    return {"generator": generator, "reviewer": reviewer}


@pytest.fixture
def critic_agent() -> LlmAgent:
    """Create a critic agent with output schema."""
    return LlmAgent(
        name="critic",
        model="gemini-2.5-flash",
        instruction="Score the response",
        output_schema=CriticOutput,
    )


@pytest.fixture
def minimal_trainset() -> list[dict[str, Any]]:
    """Create a minimal training set."""
    return [{"input": "What is 2+2?"}]


@pytest.fixture
def workflow_agents() -> tuple[SequentialAgent, LlmAgent, LlmAgent]:
    """Create a two-step workflow for workflow evolution tests."""
    step1 = LlmAgent(
        name="step1",
        model="gemini-2.5-flash",
        instruction="Provide initial answer to the question.",
        output_key="initial_answer",
    )
    step2 = LlmAgent(
        name="step2",
        model="gemini-2.5-flash",
        instruction="Refine this answer: {initial_answer}",
    )
    workflow = SequentialAgent(
        name="TwoStepWorkflow",
        sub_agents=[step1, step2],
    )
    return workflow, step1, step2


def _mock_engine_result(agent_names: list[str]) -> MagicMock:
    """Create a mock engine.run() result with evolved components."""
    components = {f"{name}.instruction": f"Evolved {name}" for name in agent_names}
    result = MagicMock(
        evolved_components=components,
        original_score=0.5,
        final_score=0.8,
        iteration_history=[],
        total_iterations=1,
    )
    return result


class TestEvolveGroupExecutorWiring:
    """Verify evolve_group() threads a single executor to all consumers."""

    @pytest.mark.asyncio
    async def test_single_executor_shared_across_all_consumers(
        self,
        multi_agents: dict[str, LlmAgent],
        critic_agent: LlmAgent,
        minimal_trainset: list[dict[str, Any]],
    ) -> None:
        """A single AgentExecutor instance reaches CriticScorer, adapter, and reflection."""
        from gepa_adk.api import evolve_group

        with (
            patch("gepa_adk.api.AgentExecutor") as mock_executor_cls,
            patch("gepa_adk.api.CriticScorer") as mock_critic_scorer_cls,
            patch("gepa_adk.api.MultiAgentAdapter") as mock_adapter_cls,
            patch("gepa_adk.api.create_adk_reflection_fn") as mock_create_reflection_fn,
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_cls,
        ):
            mock_executor = MagicMock()
            mock_executor_cls.return_value = mock_executor

            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=_mock_engine_result(["generator", "reviewer"]),
            )
            mock_engine_cls.return_value = mock_engine

            await evolve_group(
                agents=multi_agents,
                primary="reviewer",
                trainset=minimal_trainset,
                critic=critic_agent,
            )

            # Single executor created
            mock_executor_cls.assert_called_once()

            # Same instance threaded to CriticScorer
            critic_kwargs = mock_critic_scorer_cls.call_args[1]
            assert critic_kwargs["executor"] is mock_executor

            # Same instance threaded to MultiAgentAdapter
            adapter_kwargs = mock_adapter_cls.call_args[1]
            assert adapter_kwargs["executor"] is mock_executor

            # Same instance threaded to reflection function
            reflection_kwargs = mock_create_reflection_fn.call_args[1]
            assert reflection_kwargs["executor"] is mock_executor

    @pytest.mark.asyncio
    async def test_evolution_completes_with_evolved_components(
        self,
        multi_agents: dict[str, LlmAgent],
        critic_agent: LlmAgent,
        minimal_trainset: list[dict[str, Any]],
    ) -> None:
        """evolve_group() returns result with evolved components for all agents."""
        from gepa_adk.api import evolve_group

        with (
            patch("gepa_adk.api.AgentExecutor"),
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_cls,
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=_mock_engine_result(["generator", "reviewer"]),
            )
            mock_engine_cls.return_value = mock_engine

            result = await evolve_group(
                agents=multi_agents,
                primary="reviewer",
                trainset=minimal_trainset,
                critic=critic_agent,
            )

            assert result is not None
            assert result.evolved_components is not None
            assert "generator.instruction" in result.evolved_components
            assert "reviewer.instruction" in result.evolved_components
            assert result.total_iterations >= 1

    @pytest.mark.asyncio
    async def test_no_critic_skips_critic_scorer(
        self,
        multi_agents: dict[str, LlmAgent],
        minimal_trainset: list[dict[str, Any]],
    ) -> None:
        """Without a critic, CriticScorer is not created but executor still wires."""
        from gepa_adk.api import evolve_group

        with (
            patch("gepa_adk.api.AgentExecutor") as mock_executor_cls,
            patch("gepa_adk.api.CriticScorer") as mock_critic_scorer_cls,
            patch("gepa_adk.api.MultiAgentAdapter") as mock_adapter_cls,
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_cls,
        ):
            mock_executor = MagicMock()
            mock_executor_cls.return_value = mock_executor

            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=_mock_engine_result(["generator", "reviewer"]),
            )
            mock_engine_cls.return_value = mock_engine

            await evolve_group(
                agents=multi_agents,
                primary="reviewer",
                trainset=minimal_trainset,
                # No critic parameter
            )

            # Executor still created
            mock_executor_cls.assert_called_once()

            # CriticScorer NOT created when no critic
            mock_critic_scorer_cls.assert_not_called()

            # Adapter still receives executor
            adapter_kwargs = mock_adapter_cls.call_args[1]
            assert adapter_kwargs["executor"] is mock_executor


class TestEvolveWorkflowExecutorWiring:
    """Verify evolve_workflow() delegates to evolve_group() with executor wiring."""

    @pytest.mark.asyncio
    async def test_workflow_delegates_to_evolve_group(
        self,
        workflow_agents: tuple[SequentialAgent, LlmAgent, LlmAgent],
        critic_agent: LlmAgent,
        minimal_trainset: list[dict[str, Any]],
    ) -> None:
        """evolve_workflow() delegates to evolve_group() which creates the executor."""
        from gepa_adk.api import evolve_workflow

        workflow, _step1, _step2 = workflow_agents

        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = MagicMock(
                evolved_components={
                    "step1.instruction": "Evolved step1",
                    "step2.instruction": "Evolved step2",
                },
                original_score=0.5,
                final_score=0.8,
                primary_agent="step2",
                iteration_history=[],
                total_iterations=1,
            )

            result = await evolve_workflow(
                workflow=workflow,
                trainset=minimal_trainset,
                critic=critic_agent,
            )

            # evolve_group() was called (delegation)
            mock_evolve_group.assert_called_once()

            # Result propagates from evolve_group
            assert result is not None
            assert "step1.instruction" in result.evolved_components
            assert "step2.instruction" in result.evolved_components

    @pytest.mark.asyncio
    async def test_workflow_round_robin_evolves_all_agents(
        self,
        workflow_agents: tuple[SequentialAgent, LlmAgent, LlmAgent],
        critic_agent: LlmAgent,
        minimal_trainset: list[dict[str, Any]],
    ) -> None:
        """round_robin=True passes all workflow agents to evolve_group()."""
        from gepa_adk.api import evolve_workflow

        workflow, _step1, _step2 = workflow_agents

        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = MagicMock(
                evolved_components={
                    "step1.instruction": "Evolved step1",
                    "step2.instruction": "Evolved step2",
                },
                original_score=0.5,
                final_score=0.8,
                primary_agent="step2",
                iteration_history=[],
                total_iterations=1,
            )

            await evolve_workflow(
                workflow=workflow,
                trainset=minimal_trainset,
                critic=critic_agent,
                round_robin=True,
            )

            # evolve_group receives all workflow agents
            call_kwargs = mock_evolve_group.call_args[1]
            agents_dict = call_kwargs["agents"]
            assert "step1" in agents_dict
            assert "step2" in agents_dict

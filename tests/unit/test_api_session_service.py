"""Unit tests for session_service parameter in evolve_group() and evolve_workflow().

Tests verify that:
1. Custom session_service is threaded through to internal components
2. Default InMemorySessionService is created when not provided
3. Session_service flows to AgentExecutor, CriticScorer, and reflection function

See Also:
    - Issue #226: Expose session_service parameter in public API
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.sessions import BaseSessionService, InMemorySessionService


@pytest.fixture
def test_agent() -> LlmAgent:
    """Create a test LlmAgent for evolution."""
    return LlmAgent(
        name="test_agent",
        model="gemini-2.5-flash",
        instruction="Test instruction",
    )


@pytest.fixture
def test_critic() -> LlmAgent:
    """Create a test critic agent."""
    from pydantic import BaseModel, Field

    class CriticOutput(BaseModel):
        score: float = Field(ge=0.0, le=1.0)
        feedback: str = ""

    return LlmAgent(
        name="critic",
        model="gemini-2.5-flash",
        instruction="Score the response",
        output_schema=CriticOutput,
    )


@pytest.fixture
def test_trainset() -> list[dict[str, Any]]:
    """Create a minimal training set."""
    return [{"input": "test input"}]


@pytest.fixture
def mock_session_service() -> MagicMock:
    """Create a mock session service."""
    mock = MagicMock(spec=BaseSessionService)
    mock.create_session = AsyncMock(return_value=MagicMock())
    mock.get_session = AsyncMock(return_value=MagicMock())
    return mock


@pytest.fixture
def test_workflow(test_agent: LlmAgent) -> SequentialAgent:
    """Create a test workflow with one LlmAgent."""
    return SequentialAgent(
        name="test_workflow",
        sub_agents=[test_agent],
    )


class TestEvolveGroupSessionService:
    """Tests for session_service parameter in evolve_group()."""

    @pytest.mark.asyncio
    async def test_session_service_passed_to_agent_executor(
        self,
        test_agent: LlmAgent,
        test_critic: LlmAgent,
        test_trainset: list[dict[str, Any]],
        mock_session_service: MagicMock,
    ) -> None:
        """Verify session_service is passed to AgentExecutor."""
        from gepa_adk.api import evolve_group

        with (
            patch("gepa_adk.api.AgentExecutor") as mock_executor_cls,
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_cls,
        ):
            # Setup mocks
            mock_executor = MagicMock()
            mock_executor_cls.return_value = mock_executor

            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"test_agent.instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                )
            )
            mock_engine_cls.return_value = mock_engine

            await evolve_group(
                agents={"test_agent": test_agent},
                primary="test_agent",
                trainset=test_trainset,
                critic=test_critic,
                session_service=mock_session_service,
            )

            # Verify AgentExecutor was created with our session_service
            mock_executor_cls.assert_called_once()
            call_kwargs = mock_executor_cls.call_args[1]
            assert call_kwargs["session_service"] is mock_session_service

    @pytest.mark.asyncio
    async def test_session_service_flows_to_critic_scorer_via_executor(
        self,
        test_agent: LlmAgent,
        test_critic: LlmAgent,
        test_trainset: list[dict[str, Any]],
        mock_session_service: MagicMock,
    ) -> None:
        """Verify CriticScorer receives session_service via the shared executor."""
        from gepa_adk.api import evolve_group

        with (
            patch("gepa_adk.api.AgentExecutor") as mock_executor_cls,
            patch("gepa_adk.api.CriticScorer") as mock_critic_scorer_cls,
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_cls,
        ):
            # Setup mocks
            mock_executor = MagicMock()
            mock_executor_cls.return_value = mock_executor

            mock_critic_scorer = MagicMock()
            mock_critic_scorer_cls.return_value = mock_critic_scorer

            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"test_agent.instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                )
            )
            mock_engine_cls.return_value = mock_engine

            await evolve_group(
                agents={"test_agent": test_agent},
                primary="test_agent",
                trainset=test_trainset,
                critic=test_critic,
                session_service=mock_session_service,
            )

            # Verify CriticScorer was created with the executor that has our session_service
            mock_critic_scorer_cls.assert_called_once()
            call_kwargs = mock_critic_scorer_cls.call_args[1]
            # The executor passed to CriticScorer should be the one we created
            assert call_kwargs["executor"] is mock_executor
            # And that executor was created with our session_service
            executor_call_kwargs = mock_executor_cls.call_args[1]
            assert executor_call_kwargs["session_service"] is mock_session_service

    @pytest.mark.asyncio
    async def test_session_service_passed_to_multi_agent_adapter(
        self,
        test_agent: LlmAgent,
        test_critic: LlmAgent,
        test_trainset: list[dict[str, Any]],
        mock_session_service: MagicMock,
    ) -> None:
        """Verify session_service is passed to MultiAgentAdapter."""
        from gepa_adk.api import evolve_group

        with (
            patch("gepa_adk.api.AgentExecutor"),
            patch("gepa_adk.api.MultiAgentAdapter") as mock_adapter_cls,
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_cls,
            patch("gepa_adk.api.create_adk_reflection_fn"),
        ):
            mock_adapter = MagicMock()
            mock_adapter_cls.return_value = mock_adapter

            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"test_agent.instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                )
            )
            mock_engine_cls.return_value = mock_engine

            await evolve_group(
                agents={"test_agent": test_agent},
                primary="test_agent",
                trainset=test_trainset,
                critic=test_critic,
                session_service=mock_session_service,
            )

            # Verify MultiAgentAdapter was created with our session_service
            mock_adapter_cls.assert_called_once()
            call_kwargs = mock_adapter_cls.call_args[1]
            assert call_kwargs["session_service"] is mock_session_service

    @pytest.mark.asyncio
    async def test_session_service_not_passed_to_reflection_fn(
        self,
        test_agent: LlmAgent,
        test_critic: LlmAgent,
        test_trainset: list[dict[str, Any]],
        mock_session_service: MagicMock,
    ) -> None:
        """Verify session_service is NOT passed to create_adk_reflection_fn.

        The session_service parameter was removed from create_adk_reflection_fn.
        Session management is handled by the executor instead.
        """
        from gepa_adk.api import evolve_group

        with (
            patch("gepa_adk.api.AgentExecutor"),
            patch("gepa_adk.api.MultiAgentAdapter"),
            patch("gepa_adk.api.create_adk_reflection_fn") as mock_create_reflection_fn,
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_cls,
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"test_agent.instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                )
            )
            mock_engine_cls.return_value = mock_engine

            await evolve_group(
                agents={"test_agent": test_agent},
                primary="test_agent",
                trainset=test_trainset,
                critic=test_critic,
                session_service=mock_session_service,
            )

            # Verify create_adk_reflection_fn was called but WITHOUT session_service
            mock_create_reflection_fn.assert_called_once()
            call_kwargs = mock_create_reflection_fn.call_args[1]
            assert "session_service" not in call_kwargs, (
                "session_service must not be passed to create_adk_reflection_fn"
            )

    @pytest.mark.asyncio
    async def test_default_inmemory_session_service_when_none(
        self,
        test_agent: LlmAgent,
        test_critic: LlmAgent,
        test_trainset: list[dict[str, Any]],
    ) -> None:
        """Verify InMemorySessionService is created when session_service is None."""
        from gepa_adk.api import evolve_group

        with (
            patch("gepa_adk.api.AgentExecutor") as mock_executor_cls,
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_cls,
        ):
            mock_executor = MagicMock()
            mock_executor_cls.return_value = mock_executor

            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"test_agent.instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                )
            )
            mock_engine_cls.return_value = mock_engine

            await evolve_group(
                agents={"test_agent": test_agent},
                primary="test_agent",
                trainset=test_trainset,
                critic=test_critic,
                # session_service not provided (defaults to None)
            )

            # Verify AgentExecutor was created with an InMemorySessionService
            mock_executor_cls.assert_called_once()
            call_kwargs = mock_executor_cls.call_args[1]
            assert isinstance(call_kwargs["session_service"], InMemorySessionService)


class TestEvolveWorkflowSessionService:
    """Tests for session_service parameter in evolve_workflow()."""

    @pytest.mark.asyncio
    async def test_session_service_passed_through_to_evolve_group(
        self,
        test_workflow: SequentialAgent,
        test_critic: LlmAgent,
        test_trainset: list[dict[str, Any]],
        mock_session_service: MagicMock,
    ) -> None:
        """Verify session_service is passed through to evolve_group."""
        from gepa_adk.api import evolve_workflow

        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = MagicMock(
                evolved_components={"test_agent.instruction": "evolved"},
                original_score=0.5,
                final_score=0.8,
                primary_agent="test_agent",
                iteration_history=[],
                total_iterations=1,
            )

            await evolve_workflow(
                workflow=test_workflow,
                trainset=test_trainset,
                critic=test_critic,
                session_service=mock_session_service,
            )

            # Verify evolve_group was called with our session_service
            mock_evolve_group.assert_called_once()
            call_kwargs = mock_evolve_group.call_args[1]
            assert call_kwargs["session_service"] is mock_session_service

    @pytest.mark.asyncio
    async def test_default_none_passed_when_not_provided(
        self,
        test_workflow: SequentialAgent,
        test_critic: LlmAgent,
        test_trainset: list[dict[str, Any]],
    ) -> None:
        """Verify None is passed to evolve_group when session_service not provided."""
        from gepa_adk.api import evolve_workflow

        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = MagicMock(
                evolved_components={"test_agent.instruction": "evolved"},
                original_score=0.5,
                final_score=0.8,
                primary_agent="test_agent",
                iteration_history=[],
                total_iterations=1,
            )

            await evolve_workflow(
                workflow=test_workflow,
                trainset=test_trainset,
                critic=test_critic,
                # session_service not provided
            )

            # Verify evolve_group was called with session_service=None
            mock_evolve_group.assert_called_once()
            call_kwargs = mock_evolve_group.call_args[1]
            assert call_kwargs["session_service"] is None

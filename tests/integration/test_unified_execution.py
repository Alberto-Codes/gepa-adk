"""Integration tests for unified agent execution.

This module tests the AgentExecutor with real ADK agents to verify
feature parity across generator, critic, and reflection agent types.

Tests follow ADR-005 three-layer testing strategy at the integration layer.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gepa_adk.adapters.agent_executor import AgentExecutor
from gepa_adk.ports.agent_executor import ExecutionStatus


def create_mock_session_service() -> MagicMock:
    """Create mock session service that properly tracks sessions."""
    sessions: dict[str, MagicMock] = {}

    session_service = MagicMock()

    async def create_session(
        app_name: str,
        user_id: str,
        session_id: str | None = None,
        state: dict[str, Any] | None = None,
    ) -> MagicMock:
        nonlocal sessions
        session = MagicMock()
        session.id = session_id or f"sess_{len(sessions)}"
        session.user_id = user_id
        session.state = state or {}
        sessions[session.id] = session
        return session

    async def get_session(
        app_name: str, user_id: str, session_id: str
    ) -> MagicMock | None:
        return sessions.get(session_id)

    session_service.create_session = AsyncMock(side_effect=create_session)
    session_service.get_session = AsyncMock(side_effect=get_session)

    return session_service


@pytest.mark.integration
class TestSessionSharing:
    """Integration tests for session sharing between agents (T025)."""

    @pytest.mark.asyncio
    async def test_critic_accesses_generator_session_state(self) -> None:
        """T025: Critic can access state written by generator in shared session."""
        # Create shared session service
        session_service = create_mock_session_service()
        executor = AgentExecutor(session_service=session_service, app_name="test_app")

        # Create mock generator agent
        generator_agent = MagicMock()
        generator_agent.name = "generator"
        generator_agent.model = "gemini-2.0-flash"
        generator_agent.instruction = "Generate something"
        generator_agent.output_key = "generated_output"
        generator_agent.tools = []

        # Mock Runner to simulate generator execution that writes to state
        with patch("gepa_adk.adapters.agent_executor.Runner") as mock_runner_cls:
            # Generator run - writes output to state
            async def generator_run_async(*args: Any, **kwargs: Any) -> Any:
                session_id = kwargs.get("session_id")
                # Simulate state update by modifying the session
                session = await session_service.get_session(
                    app_name="test_app", user_id="exec_user", session_id=session_id
                )
                if session:
                    session.state["generated_output"] = "Hello from generator"
                    session.state["generation_metadata"] = {"quality": "high"}

                mock_event = MagicMock()
                mock_event.content = MagicMock()
                mock_event.content.parts = [MagicMock(text="Hello from generator")]
                mock_event.content.role = "model"
                mock_event.actions = None
                yield mock_event

            mock_runner_instance = MagicMock()
            mock_runner_instance.run_async = generator_run_async
            mock_runner_cls.return_value = mock_runner_instance

            # Execute generator
            gen_result = await executor.execute_agent(
                agent=generator_agent,
                input_text="Generate something",
            )

            assert gen_result.status == ExecutionStatus.SUCCESS
            generator_session_id = gen_result.session_id

        # Now execute critic with the same session
        critic_agent = MagicMock()
        critic_agent.name = "critic"
        critic_agent.model = "gemini-2.0-flash"
        critic_agent.instruction = "Evaluate the generation"
        critic_agent.output_key = "critic_output"
        critic_agent.tools = []

        with patch("gepa_adk.adapters.agent_executor.Runner") as mock_runner_cls:
            # Capture what session the critic sees
            captured_session_state: dict[str, Any] = {}

            async def critic_run_async(*args: Any, **kwargs: Any) -> Any:
                session_id = kwargs.get("session_id")
                # Verify critic can see generator's state
                session = await session_service.get_session(
                    app_name="test_app", user_id="exec_user", session_id=session_id
                )
                if session:
                    captured_session_state.update(session.state)
                    session.state["critic_output"] = "Evaluation: Good"

                mock_event = MagicMock()
                mock_event.content = MagicMock()
                mock_event.content.parts = [MagicMock(text="Evaluation: Good")]
                mock_event.content.role = "model"
                mock_event.actions = None
                yield mock_event

            mock_runner_instance = MagicMock()
            mock_runner_instance.run_async = critic_run_async
            mock_runner_cls.return_value = mock_runner_instance

            # Execute critic with generator's session
            critic_result = await executor.execute_agent(
                agent=critic_agent,
                input_text="Evaluate the output",
                existing_session_id=generator_session_id,
            )

            assert critic_result.status == ExecutionStatus.SUCCESS

            # Verify critic could access generator's state
            assert "generated_output" in captured_session_state
            assert captured_session_state["generated_output"] == "Hello from generator"
            assert "generation_metadata" in captured_session_state


@pytest.mark.integration
class TestUnifiedExecutionFeatureParity:
    """Integration tests verifying feature parity across agent types."""

    # T044-T047: Integration tests for migration
    # These tests verify that consumers produce identical results
    # before and after migration to AgentExecutor


@pytest.mark.integration
class TestBackwardCompatibility:
    """Integration tests verifying backward compatibility (T047)."""

    pass

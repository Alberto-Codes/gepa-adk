"""Unit tests for App/Runner pattern support in evolution APIs.

Tests the feature #227: Support ADK App/Runner Pattern for Evolution.

These tests verify:
1. Service extraction from Runner instances
2. Precedence rules: runner > app > session_service > default
3. Warning logging when multiple config sources provided
4. Backward compatibility when no app/runner provided
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent
from google.adk.sessions import BaseSessionService, InMemorySessionService

from gepa_adk.api import _resolve_evolution_services


class TestResolveEvolutionServices:
    """Tests for _resolve_evolution_services() helper function."""

    def test_runner_takes_precedence_over_all(self) -> None:
        """Runner's services should be used when runner is provided."""
        # Arrange
        mock_runner = MagicMock()
        mock_session_service = MagicMock(spec=BaseSessionService)
        mock_artifact_service = MagicMock()
        mock_runner.session_service = mock_session_service
        mock_runner.artifact_service = mock_artifact_service

        mock_app = MagicMock()
        mock_app.name = "test_app"

        other_session_service = MagicMock(spec=BaseSessionService)

        # Act
        session, artifact = _resolve_evolution_services(
            runner=mock_runner,
            app=mock_app,  # Should be ignored
            session_service=other_session_service,  # Should be ignored
        )

        # Assert
        assert session is mock_session_service
        assert artifact is mock_artifact_service

    def test_app_uses_provided_session_service(self) -> None:
        """When app provided without runner, uses session_service param."""
        # Arrange
        mock_app = MagicMock()
        mock_app.name = "test_app"
        mock_session_service = MagicMock(spec=BaseSessionService)

        # Act
        session, artifact = _resolve_evolution_services(
            runner=None,
            app=mock_app,
            session_service=mock_session_service,
        )

        # Assert - App doesn't hold services, uses provided session_service
        assert session is mock_session_service
        assert artifact is None

    def test_app_creates_default_when_no_session_service(self) -> None:
        """When app provided without session_service, creates InMemory."""
        # Arrange
        mock_app = MagicMock()
        mock_app.name = "test_app"

        # Act
        session, artifact = _resolve_evolution_services(
            runner=None,
            app=mock_app,
            session_service=None,
        )

        # Assert
        assert isinstance(session, InMemorySessionService)
        assert artifact is None

    def test_session_service_used_when_no_runner_or_app(self) -> None:
        """Direct session_service param used when no runner/app."""
        # Arrange
        mock_session_service = MagicMock(spec=BaseSessionService)

        # Act
        session, artifact = _resolve_evolution_services(
            runner=None,
            app=None,
            session_service=mock_session_service,
        )

        # Assert
        assert session is mock_session_service
        assert artifact is None

    def test_default_inmemory_when_nothing_provided(self) -> None:
        """Creates InMemorySessionService when no args provided."""
        # Act
        session, artifact = _resolve_evolution_services(
            runner=None,
            app=None,
            session_service=None,
        )

        # Assert
        assert isinstance(session, InMemorySessionService)
        assert artifact is None


class TestEvolveAppRunnerParameters:
    """Tests for evolve() with app/runner parameters."""

    @pytest.fixture
    def mock_agent(self) -> LlmAgent:
        """Create a mock LlmAgent for testing."""
        return LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test instruction",
        )

    @pytest.fixture
    def mock_trainset(self) -> list[dict]:
        """Create a mock trainset for testing."""
        return [{"input": "test input"}]

    @pytest.mark.asyncio
    async def test_evolve_with_runner_uses_runner_session_service(
        self, mock_agent: LlmAgent, mock_trainset: list[dict]
    ) -> None:
        """evolve() with runner should use runner's session_service."""
        # Arrange
        mock_runner = MagicMock()
        mock_session_service = MagicMock(spec=BaseSessionService)
        mock_runner.session_service = mock_session_service
        mock_runner.artifact_service = None
        mock_runner.app_name = "test_app"

        with (
            patch("gepa_adk.api.AgentExecutor") as mock_executor_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.SchemaBasedScorer"),
        ):
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor

            mock_adapter = MagicMock()
            mock_adapter_class.return_value = mock_adapter

            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                    valset_score=0.8,
                    trainset_score=0.8,
                )
            )
            mock_engine_class.return_value = mock_engine

            # Need output_schema for SchemaBasedScorer
            mock_agent.output_schema = MagicMock()
            mock_agent.output_schema.model_fields = {"score": MagicMock()}

            # Act - import here to get patched version
            from gepa_adk.api import evolve

            await evolve(
                agent=mock_agent,
                trainset=mock_trainset,
                runner=mock_runner,
            )

            # Assert - AgentExecutor should be created with runner's session_service
            mock_executor_class.assert_called()
            call_kwargs = mock_executor_class.call_args
            assert call_kwargs.kwargs.get("session_service") is mock_session_service

    @pytest.mark.asyncio
    async def test_evolve_logs_warning_when_runner_and_app_provided(
        self, mock_agent: LlmAgent, mock_trainset: list[dict]
    ) -> None:
        """evolve() should log warning when both runner and app provided."""
        # Arrange
        mock_runner = MagicMock()
        mock_runner.session_service = MagicMock(spec=BaseSessionService)
        mock_runner.artifact_service = None
        mock_runner.app_name = "runner_app"

        mock_app = MagicMock()
        mock_app.name = "test_app"

        with (
            patch("gepa_adk.api.AgentExecutor"),
            patch("gepa_adk.api.ADKAdapter"),
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.SchemaBasedScorer"),
            patch("gepa_adk.api.logger") as mock_logger,
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                    valset_score=0.8,
                    trainset_score=0.8,
                )
            )
            mock_engine_class.return_value = mock_engine

            mock_agent.output_schema = MagicMock()
            mock_agent.output_schema.model_fields = {"score": MagicMock()}

            from gepa_adk.api import evolve

            # Act
            await evolve(
                agent=mock_agent,
                trainset=mock_trainset,
                runner=mock_runner,
                app=mock_app,
            )

            # Assert - warning should be logged
            mock_logger.warning.assert_called()
            warning_calls = [
                c
                for c in mock_logger.warning.call_args_list
                if "precedence" in str(c)
            ]
            assert len(warning_calls) > 0

    @pytest.mark.asyncio
    async def test_evolve_logs_warning_when_runner_and_executor_provided(
        self, mock_agent: LlmAgent, mock_trainset: list[dict]
    ) -> None:
        """evolve() should log warning when both runner and executor provided."""
        # Arrange
        mock_runner = MagicMock()
        mock_runner.session_service = MagicMock(spec=BaseSessionService)
        mock_runner.artifact_service = None
        mock_runner.app_name = "runner_app"

        mock_executor = MagicMock()

        with (
            patch("gepa_adk.api.AgentExecutor"),
            patch("gepa_adk.api.ADKAdapter"),
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.SchemaBasedScorer"),
            patch("gepa_adk.api.logger") as mock_logger,
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                    valset_score=0.8,
                    trainset_score=0.8,
                )
            )
            mock_engine_class.return_value = mock_engine

            mock_agent.output_schema = MagicMock()
            mock_agent.output_schema.model_fields = {"score": MagicMock()}

            from gepa_adk.api import evolve

            # Act
            await evolve(
                agent=mock_agent,
                trainset=mock_trainset,
                runner=mock_runner,
                executor=mock_executor,
            )

            # Assert - warning about runner over executor should be logged
            mock_logger.warning.assert_called()
            warning_calls = [
                c
                for c in mock_logger.warning.call_args_list
                if "executor" in str(c).lower()
            ]
            assert len(warning_calls) > 0


class TestEvolveGroupAppRunnerParameters:
    """Tests for evolve_group() with app/runner parameters."""

    @pytest.fixture
    def mock_agents(self) -> dict[str, LlmAgent]:
        """Create mock agents for testing."""
        return {
            "generator": LlmAgent(
                name="generator",
                model="gemini-2.5-flash",
                instruction="Generate content",
            ),
            "refiner": LlmAgent(
                name="refiner",
                model="gemini-2.5-flash",
                instruction="Refine content",
            ),
        }

    @pytest.fixture
    def mock_trainset(self) -> list[dict]:
        """Create a mock trainset for testing."""
        return [{"input": "test input"}]

    @pytest.mark.asyncio
    async def test_evolve_group_with_runner_extracts_services(
        self, mock_agents: dict[str, LlmAgent], mock_trainset: list[dict]
    ) -> None:
        """evolve_group() with runner should use runner's session_service."""
        # Arrange
        mock_runner = MagicMock()
        mock_session_service = MagicMock(spec=BaseSessionService)
        mock_runner.session_service = mock_session_service
        mock_runner.artifact_service = None
        mock_runner.app_name = "test_app"

        with (
            patch("gepa_adk.api.AgentExecutor") as mock_executor_class,
            patch("gepa_adk.api.MultiAgentAdapter"),
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.CriticScorer"),
            patch("gepa_adk.api.create_adk_reflection_fn"),
            patch("gepa_adk.api.AsyncReflectiveMutationProposer"),
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"generator.instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                )
            )
            mock_engine_class.return_value = mock_engine

            # Add output_schema to primary agent for scoring
            mock_agents["refiner"].output_schema = MagicMock()
            mock_agents["refiner"].output_schema.model_fields = {"score": MagicMock()}

            from gepa_adk.api import evolve_group

            # Act
            await evolve_group(
                agents=mock_agents,
                primary="refiner",
                trainset=mock_trainset,
                runner=mock_runner,
            )

            # Assert - AgentExecutor should be created with runner's session_service
            mock_executor_class.assert_called()
            call_kwargs = mock_executor_class.call_args
            assert call_kwargs.kwargs.get("session_service") is mock_session_service

    @pytest.mark.asyncio
    async def test_evolve_group_runner_precedence_over_session_service(
        self, mock_agents: dict[str, LlmAgent], mock_trainset: list[dict]
    ) -> None:
        """Runner takes precedence over direct session_service parameter."""
        # Arrange
        mock_runner = MagicMock()
        runner_session = MagicMock(spec=BaseSessionService)
        mock_runner.session_service = runner_session
        mock_runner.artifact_service = None
        mock_runner.app_name = "test_app"

        direct_session = MagicMock(spec=BaseSessionService)

        with (
            patch("gepa_adk.api.AgentExecutor") as mock_executor_class,
            patch("gepa_adk.api.MultiAgentAdapter"),
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.CriticScorer"),
            patch("gepa_adk.api.create_adk_reflection_fn"),
            patch("gepa_adk.api.AsyncReflectiveMutationProposer"),
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"generator.instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                )
            )
            mock_engine_class.return_value = mock_engine

            mock_agents["refiner"].output_schema = MagicMock()
            mock_agents["refiner"].output_schema.model_fields = {"score": MagicMock()}

            from gepa_adk.api import evolve_group

            # Act
            await evolve_group(
                agents=mock_agents,
                primary="refiner",
                trainset=mock_trainset,
                runner=mock_runner,
                session_service=direct_session,  # Should be overridden by runner
            )

            # Assert - runner's session_service should be used, not direct_session
            mock_executor_class.assert_called()
            call_kwargs = mock_executor_class.call_args
            used_session = call_kwargs.kwargs.get("session_service")
            assert used_session is runner_session
            assert used_session is not direct_session


class TestEvolveWorkflowAppRunnerPassthrough:
    """Tests for evolve_workflow() passing app/runner to evolve_group()."""

    @pytest.mark.asyncio
    async def test_evolve_workflow_passes_runner_to_evolve_group(self) -> None:
        """evolve_workflow() should pass runner through to evolve_group()."""
        # Arrange
        from google.adk.agents import SequentialAgent

        mock_llm_agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test",
        )
        mock_workflow = SequentialAgent(
            name="workflow",
            sub_agents=[mock_llm_agent],
        )

        mock_runner = MagicMock()
        mock_runner.session_service = MagicMock(spec=BaseSessionService)
        mock_runner.artifact_service = None
        mock_runner.app_name = "test_app"

        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = MagicMock(
                evolved_components={"test_agent.instruction": "evolved"},
                original_score=0.5,
                final_score=0.8,
                primary_agent="test_agent",
                iteration_history=[],
                total_iterations=1,
            )

            from gepa_adk.api import evolve_workflow

            # Act
            await evolve_workflow(
                workflow=mock_workflow,
                trainset=[{"input": "test"}],
                runner=mock_runner,
            )

            # Assert - evolve_group should be called with runner parameter
            mock_evolve_group.assert_called_once()
            call_kwargs = mock_evolve_group.call_args.kwargs
            assert call_kwargs.get("runner") is mock_runner

    @pytest.mark.asyncio
    async def test_evolve_workflow_passes_app_to_evolve_group(self) -> None:
        """evolve_workflow() should pass app through to evolve_group()."""
        from google.adk.agents import SequentialAgent

        mock_llm_agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test",
        )
        mock_workflow = SequentialAgent(
            name="workflow",
            sub_agents=[mock_llm_agent],
        )

        mock_app = MagicMock()
        mock_app.name = "test_app"

        with patch("gepa_adk.api.evolve_group") as mock_evolve_group:
            mock_evolve_group.return_value = MagicMock(
                evolved_components={"test_agent.instruction": "evolved"},
                original_score=0.5,
                final_score=0.8,
                primary_agent="test_agent",
                iteration_history=[],
                total_iterations=1,
            )

            from gepa_adk.api import evolve_workflow

            # Act
            await evolve_workflow(
                workflow=mock_workflow,
                trainset=[{"input": "test"}],
                app=mock_app,
            )

            # Assert - evolve_group should be called with app parameter
            mock_evolve_group.assert_called_once()
            call_kwargs = mock_evolve_group.call_args.kwargs
            assert call_kwargs.get("app") is mock_app


class TestBackwardCompatibility:
    """Tests for backward compatibility when no app/runner provided."""

    def test_resolve_services_default_behavior(self) -> None:
        """Without app/runner, should create InMemorySessionService."""
        # Act
        session, artifact = _resolve_evolution_services(
            runner=None,
            app=None,
            session_service=None,
        )

        # Assert
        assert isinstance(session, InMemorySessionService)
        assert artifact is None

    @pytest.mark.asyncio
    async def test_evolve_without_app_runner_uses_defaults(self) -> None:
        """evolve() without app/runner should use default session service."""
        mock_agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test",
        )

        with (
            patch("gepa_adk.api.AgentExecutor") as mock_executor_class,
            patch("gepa_adk.api.ADKAdapter"),
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.SchemaBasedScorer"),
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(
                return_value=MagicMock(
                    evolved_components={"instruction": "evolved"},
                    original_score=0.5,
                    final_score=0.8,
                    iteration_history=[],
                    total_iterations=1,
                    valset_score=0.8,
                    trainset_score=0.8,
                )
            )
            mock_engine_class.return_value = mock_engine

            mock_agent.output_schema = MagicMock()
            mock_agent.output_schema.model_fields = {"score": MagicMock()}

            from gepa_adk.api import evolve

            # Act
            await evolve(
                agent=mock_agent,
                trainset=[{"input": "test"}],
                # No app, runner, or executor
            )

            # Assert - AgentExecutor should be created with InMemorySessionService
            mock_executor_class.assert_called()
            call_kwargs = mock_executor_class.call_args
            session_arg = call_kwargs.kwargs.get("session_service")
            assert isinstance(session_arg, InMemorySessionService)

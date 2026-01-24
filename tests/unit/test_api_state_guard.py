"""Unit tests for StateGuard integration in public API.

Tests verify that StateGuard validation is correctly applied to evolved
instructions in evolve(), evolve_sync(), evolve_group(), and evolve_workflow().

Note:
    These tests use mocks to avoid requiring actual ADK agent execution
    or LLM API calls. StateGuard validation logic is tested separately
    in tests/unit/utils/test_state_guard.py.
"""

from __future__ import annotations

import re
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

import gepa_adk.api as api_module
from gepa_adk import evolve, evolve_group, evolve_workflow
from gepa_adk.domain.models import (
    EvolutionResult,
    IterationRecord,
    MultiAgentEvolutionResult,
)
from gepa_adk.utils import StateGuard

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_agent() -> LlmAgent:
    """Create a mock LlmAgent for testing."""
    return LlmAgent(
        name="test_agent",
        model="gemini-2.5-flash",
        instruction="You are a helpful assistant.",
    )


@pytest.fixture
def mock_agent_with_token() -> LlmAgent:
    """Create a mock LlmAgent with state token in instruction."""

    class OutputSchema(BaseModel):
        score: float = Field(ge=0.0, le=1.0)
        result: str

    return LlmAgent(
        name="test_agent",
        model="gemini-2.5-flash",
        instruction="Hello {user_id}, you are a helpful assistant.",
        output_schema=OutputSchema,
    )


@pytest.fixture
def sample_trainset() -> list[dict[str, str]]:
    """Create a sample training set."""
    return [
        {"input": "What is 2+2?", "expected": "4"},
        {"input": "What is 3+3?", "expected": "6"},
    ]


@pytest.fixture
def mock_evolution_result() -> EvolutionResult:
    """Create a mock EvolutionResult for testing."""
    return EvolutionResult(
        original_score=0.5,
        final_score=0.8,
        evolved_components={"instruction": "Improved instruction"},
        iteration_history=[
            IterationRecord(
                iteration_number=1,
                score=0.6,
                component_text="Test instruction",
                evolved_component="instruction",
                accepted=True,
            )
        ],
        total_iterations=1,
    )


@pytest.fixture
def state_guard() -> StateGuard:
    """Create a StateGuard instance for testing."""
    return StateGuard(required_tokens=["{user_id}"])


class TestEvolveStateGuardUserStory1:
    """Tests for User Story 1: Automatic Token Repair During Evolution."""

    @pytest.mark.asyncio
    async def test_evolve_state_guard_repairs_missing_token(
        self,
        mock_agent_with_token: LlmAgent,
        sample_trainset: list[dict[str, str]],
        state_guard: StateGuard,
    ) -> None:
        """Verify StateGuard repairs missing token in evolved instruction."""
        # Mock the evolution result with missing token
        mock_result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            # Missing {user_id}
            evolved_components={
                "instruction": "Hello there, you are a helpful assistant."
            },
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="Test instruction",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            result = await evolve(
                mock_agent_with_token,
                sample_trainset,
                state_guard=state_guard,
            )

            # Verify token was repaired
            assert "{user_id}" in result.evolved_components["instruction"]
            assert result.evolved_components["instruction"].endswith("\n\n{user_id}")

    @pytest.mark.asyncio
    async def test_evolve_no_state_guard_returns_unchanged(
        self,
        mock_agent_with_token: LlmAgent,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """Verify evolve() returns unchanged instruction when state_guard=None."""
        # Mock the evolution result with missing token
        mock_result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            # Missing {user_id}
            evolved_components={
                "instruction": "Hello there, you are a helpful assistant."
            },
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="Test instruction",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            result = await evolve(
                mock_agent_with_token,
                sample_trainset,
                state_guard=None,
            )

            # Verify instruction is unchanged (no token repair)
            assert (
                result.evolved_components["instruction"]
                == "Hello there, you are a helpful assistant."
            )
            assert "{user_id}" not in result.evolved_components["instruction"]

    @pytest.mark.asyncio
    async def test_evolve_state_guard_repair_disabled(
        self,
        mock_agent_with_token: LlmAgent,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """Verify StateGuard respects repair_missing=False."""
        state_guard_no_repair = StateGuard(
            required_tokens=["{user_id}"],
            repair_missing=False,
        )

        # Mock the evolution result with missing token
        mock_result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            # Missing {user_id}
            evolved_components={
                "instruction": "Hello there, you are a helpful assistant."
            },
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="Test instruction",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            result = await evolve(
                mock_agent_with_token,
                sample_trainset,
                state_guard=state_guard_no_repair,
            )

            # Verify token was NOT repaired (repair disabled)
            assert (
                result.evolved_components["instruction"]
                == "Hello there, you are a helpful assistant."
            )
            assert not result.evolved_components["instruction"].endswith(
                "\n\n{user_id}"
            )

    @pytest.mark.asyncio
    async def test_evolve_state_guard_not_mutated(
        self,
        mock_agent_with_token: LlmAgent,
        sample_trainset: list[dict[str, str]],
        state_guard: StateGuard,
    ) -> None:
        """Verify StateGuard instance is not mutated after validation."""
        original_required_tokens = state_guard.required_tokens.copy()
        original_repair_missing = state_guard.repair_missing
        original_escape_unauthorized = state_guard.escape_unauthorized
        original_instruction = mock_agent_with_token.instruction

        # Mock the evolution result
        mock_result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={
                "instruction": "Hello there, you are a helpful assistant."
            },
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="Test instruction",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            await evolve(
                mock_agent_with_token,
                sample_trainset,
                state_guard=state_guard,
            )

            # Verify StateGuard instance was not mutated
            assert state_guard.required_tokens == original_required_tokens
            assert state_guard.repair_missing == original_repair_missing
            assert state_guard.escape_unauthorized == original_escape_unauthorized
            assert mock_agent_with_token.instruction == original_instruction

    @pytest.mark.asyncio
    async def test_evolve_state_guard_unchanged_instruction(
        self,
        mock_agent_with_token: LlmAgent,
        sample_trainset: list[dict[str, str]],
        state_guard: StateGuard,
    ) -> None:
        """Verify identical evolved instruction produces no changes."""
        # Mock the evolution result with token preserved
        mock_result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            # Token preserved
            evolved_components={
                "instruction": "Hello {user_id}, you are a helpful assistant."
            },
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="Test instruction",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            result = await evolve(
                mock_agent_with_token,
                sample_trainset,
                state_guard=state_guard,
            )

            # Verify instruction is unchanged (token was already present)
            assert (
                result.evolved_components["instruction"]
                == "Hello {user_id}, you are a helpful assistant."
            )
            assert not result.evolved_components["instruction"].endswith(
                "\n\n{user_id}"
            )


class TestEvolveStateGuardUserStory2:
    """Tests for User Story 2: Unauthorized Token Escaping."""

    @pytest.mark.asyncio
    async def test_evolve_state_guard_escapes_unauthorized(
        self,
        mock_agent_with_token: LlmAgent,
        sample_trainset: list[dict[str, str]],
        state_guard: StateGuard,
    ) -> None:
        """Verify StateGuard escapes unauthorized tokens in evolved instruction."""
        # Mock the evolution result with unauthorized token
        # Unauthorized {malicious}
        mock_result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={
                "instruction": "Hello {user_id}, process with {malicious}"
            },
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="Test instruction",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            result = await evolve(
                mock_agent_with_token,
                sample_trainset,
                state_guard=state_guard,
            )

            # Verify unauthorized token was escaped
            assert "{user_id}" in result.evolved_components["instruction"]
            assert "{{malicious}}" in result.evolved_components["instruction"]
            assert (
                re.search(
                    r"(?<!\{)\{malicious\}(?!\})",
                    result.evolved_components["instruction"],
                )
                is None
            )

    @pytest.mark.asyncio
    async def test_evolve_state_guard_escape_disabled(
        self,
        mock_agent_with_token: LlmAgent,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """Verify StateGuard respects escape_unauthorized=False."""
        state_guard_no_escape = StateGuard(
            required_tokens=["{user_id}"],
            escape_unauthorized=False,
        )

        # Mock the evolution result with unauthorized token
        # Unauthorized {malicious}
        mock_result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={
                "instruction": "Hello {user_id}, process with {malicious}"
            },
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="Test instruction",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            result = await evolve(
                mock_agent_with_token,
                sample_trainset,
                state_guard=state_guard_no_escape,
            )

            # Verify unauthorized token was NOT escaped (escape disabled)
            assert "{user_id}" in result.evolved_components["instruction"]
            assert "{malicious}" in result.evolved_components["instruction"]
            assert "{{malicious}}" not in result.evolved_components["instruction"]

    @pytest.mark.asyncio
    async def test_evolve_state_guard_authorized_token_not_escaped(
        self,
        mock_agent_with_token: LlmAgent,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """Verify authorized tokens (in required_tokens) are NOT escaped."""
        state_guard_with_context = StateGuard(
            required_tokens=["{user_id}", "{context}"],
        )

        # Mock the evolution result with new authorized token
        mock_result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            # New authorized {context}
            evolved_components={"instruction": "Hello {user_id}, context: {context}"},
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="Test instruction",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            result = await evolve(
                mock_agent_with_token,
                sample_trainset,
                state_guard=state_guard_with_context,
            )

            # Verify authorized tokens are NOT escaped
            assert "{user_id}" in result.evolved_components["instruction"]
            assert "{context}" in result.evolved_components["instruction"]
            assert "{{context}}" not in result.evolved_components["instruction"]


class TestStateGuardLogging:
    """Tests for StateGuard logging behavior."""

    def test_apply_state_guard_validation_logs_applied(self) -> None:
        """Verify applied validation logs repaired and escaped tokens."""
        state_guard = StateGuard(required_tokens=["{user_id}"])
        original = "Hello {user_id}"
        evolved = "Hello"

        with patch("gepa_adk.api.logger") as mock_logger:
            validated = api_module._apply_state_guard_validation(
                state_guard,
                original,
                evolved,
                "test_agent",
            )

        assert validated.endswith("\n\n{user_id}")
        mock_logger.info.assert_called_once()
        event_name = mock_logger.info.call_args.args[0]
        payload = mock_logger.info.call_args.kwargs
        assert event_name == "evolve.state_guard.applied"
        assert payload["agent_name"] == "test_agent"
        assert payload["component_text_modified"] is True
        assert payload["repaired_tokens"] == ["{user_id}"]
        assert payload["escaped_tokens"] == []
        assert payload["repaired"] is True
        assert payload["escaped"] is False

    def test_apply_state_guard_validation_logs_no_changes(self) -> None:
        """Verify no-change validation logs debug event."""
        state_guard = StateGuard(required_tokens=["{user_id}"])
        original = "Hello {user_id}"
        evolved = "Hi {user_id}"

        with patch("gepa_adk.api.logger") as mock_logger:
            validated = api_module._apply_state_guard_validation(
                state_guard,
                original,
                evolved,
                "test_agent",
            )

        assert validated == evolved
        mock_logger.debug.assert_called_once()
        event_name = mock_logger.debug.call_args.args[0]
        payload = mock_logger.debug.call_args.kwargs
        assert event_name == "evolve.state_guard.no_changes"
        assert payload["agent_name"] == "test_agent"
        mock_logger.info.assert_not_called()


class TestEvolveGroupStateGuardUserStory3:
    """Tests for User Story 3: StateGuard in Multi-Agent Evolution."""

    @pytest.fixture
    def mock_agents_with_tokens(self) -> dict[str, LlmAgent]:
        """Create mock agents dict with state tokens in instructions."""

        class OutputSchema(BaseModel):
            score: float = Field(ge=0.0, le=1.0)
            result: str

        return {
            "agent_a": LlmAgent(
                name="agent_a",
                model="gemini-2.5-flash",
                instruction="Process {session_id}",
                output_schema=OutputSchema,
            ),
            "agent_b": LlmAgent(
                name="agent_b",
                model="gemini-2.5-flash",
                instruction="Review {session_id}",
                output_schema=OutputSchema,
            ),
        }

    @pytest.fixture
    def state_guard_session(self) -> StateGuard:
        """Create a StateGuard instance for session tokens."""
        return StateGuard(required_tokens=["{session_id}"])

    @pytest.mark.asyncio
    async def test_evolve_group_state_guard_each_agent(
        self,
        mock_agents_with_tokens: dict[str, LlmAgent],
        sample_trainset: list[dict[str, str]],
        state_guard_session: StateGuard,
    ) -> None:
        """Verify evolve_group applies StateGuard to each agent."""
        # Mock the evolution result - using qualified names per ADR-012
        mock_result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={
                "instruction": "Process"  # Primary agent missing token
            },
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="Test instruction",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.MultiAgentAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            result = await evolve_group(
                agents=mock_agents_with_tokens,
                primary="agent_a",
                trainset=sample_trainset,
                state_guard=state_guard_session,
            )

            # Verify StateGuard was applied to each agent
            assert isinstance(result, MultiAgentEvolutionResult)
            # Primary agent should have token repaired (using qualified name)
            assert "{session_id}" in result.evolved_components["agent_a.instruction"]
            # Other agents should also be validated (even if unchanged)
            assert "agent_b.instruction" in result.evolved_components

    @pytest.mark.asyncio
    async def test_evolve_group_state_guard_per_agent_original(
        self,
        mock_agents_with_tokens: dict[str, LlmAgent],
        sample_trainset: list[dict[str, str]],
        state_guard_session: StateGuard,
    ) -> None:
        """Verify evolve_group uses each agent's original instruction as reference."""
        # Mock the evolution result where agent_b loses its token
        mock_result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Review"},  # Primary agent missing token
            iteration_history=[
                IterationRecord(
                    iteration_number=1,
                    score=0.6,
                    component_text="Test instruction",
                    evolved_component="instruction",
                    accepted=True,
                )
            ],
            total_iterations=1,
        )

        with (
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.MultiAgentAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            # Setup mocks
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            result = await evolve_group(
                agents=mock_agents_with_tokens,
                primary="agent_b",  # Use agent_b as primary
                trainset=sample_trainset,
                state_guard=state_guard_session,
            )

            # Verify each agent's instruction is validated against its own original
            assert isinstance(result, MultiAgentEvolutionResult)
            # Primary agent (agent_b) should have token repaired (using qualified name)
            assert "{session_id}" in result.evolved_components["agent_b.instruction"]


class TestEvolveWorkflowStateGuardUserStory4:
    """Tests for User Story 4: StateGuard in Workflow Evolution."""

    @pytest.fixture
    def mock_workflow_agents(self) -> list[LlmAgent]:
        """Create mock agents for workflow testing."""

        class OutputSchema(BaseModel):
            score: float = Field(ge=0.0, le=1.0)
            result: str

        return [
            LlmAgent(
                name="internal_agent_1",
                model="gemini-2.5-flash",
                instruction="Process {session_id}",
                output_schema=OutputSchema,
            ),
            LlmAgent(
                name="internal_agent_2",
                model="gemini-2.5-flash",
                instruction="Review {session_id}",
                output_schema=OutputSchema,
            ),
        ]

    @pytest.fixture
    def state_guard_session(self) -> StateGuard:
        """Create a StateGuard instance for session tokens."""
        return StateGuard(required_tokens=["{session_id}"])

    @pytest.mark.asyncio
    async def test_evolve_workflow_state_guard(
        self,
        mock_workflow_agents: list[LlmAgent],
        sample_trainset: list[dict[str, str]],
        state_guard_session: StateGuard,
    ) -> None:
        """Verify evolve_workflow applies StateGuard to internal agents."""
        from google.adk.agents import BaseAgent, SequentialAgent

        # Create a workflow with the agents
        workflow = SequentialAgent(
            name="test_workflow",
            sub_agents=cast(list[BaseAgent], mock_workflow_agents),
        )

        with (
            patch("gepa_adk.api.find_llm_agents") as mock_find_agents,
            patch("gepa_adk.api.evolve_group") as mock_evolve_group,
        ):
            # Setup mocks
            mock_find_agents.return_value = mock_workflow_agents
            mock_evolve_group.return_value = MultiAgentEvolutionResult(
                evolved_components={
                    "internal_agent_1": "Process\n\n{session_id}",
                    "internal_agent_2": "Review {session_id}",
                },
                original_score=0.5,
                final_score=0.8,
                primary_agent="internal_agent_2",
                iteration_history=[],
                total_iterations=1,
            )

            result = await evolve_workflow(
                workflow=workflow,
                trainset=sample_trainset,
                state_guard=state_guard_session,
            )

            # Verify evolve_group was called with state_guard
            mock_evolve_group.assert_called_once()
            call_kwargs = mock_evolve_group.call_args.kwargs
            assert call_kwargs["state_guard"] == state_guard_session

            # Verify result contains validated instructions
            assert isinstance(result, MultiAgentEvolutionResult)
            assert "internal_agent_1" in result.evolved_components
            assert "internal_agent_2" in result.evolved_components

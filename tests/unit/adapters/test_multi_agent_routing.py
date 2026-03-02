"""Unit tests for multi-agent component routing functionality.

Tests verify component routing to correct agents based on qualified names
per ADR-012 (dot notation: agent.component format).
"""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent
from pytest_mock import MockerFixture

from gepa_adk.adapters import MultiAgentAdapter
from gepa_adk.domain.exceptions import RestoreError
from tests.conftest import MockScorer

pytestmark = pytest.mark.unit


@pytest.fixture
def test_agents() -> dict[str, LlmAgent]:
    """Create test ADK agents dict for testing."""
    return {
        "generator": LlmAgent(
            name="generator",
            model="gemini-2.5-flash",
            instruction="original instruction",
        ),
        "critic": LlmAgent(
            name="critic",
            model="gemini-2.5-flash",
            instruction="critic original",
        ),
    }


@pytest.fixture
def test_components() -> dict[str, list[str]]:
    """Create test components mapping for testing."""
    return {
        "generator": ["instruction"],
        "critic": ["instruction"],
    }


@pytest.fixture
def test_scorer() -> MockScorer:
    """Create a test scorer."""
    return MockScorer(score_value=0.85)


@pytest.fixture
def adapter(
    test_agents: dict[str, LlmAgent],
    test_components: dict[str, list[str]],
    test_scorer: MockScorer,
    mock_proposer,
) -> MultiAgentAdapter:
    """Create a MultiAgentAdapter instance for testing."""
    return MultiAgentAdapter(
        agents=test_agents,
        primary="generator",
        components=test_components,
        scorer=test_scorer,
        proposer=mock_proposer,
    )


class TestApplyCandidateRouting:
    """Tests for _apply_candidate routing behavior (T006)."""

    def test_apply_candidate_routes_to_correct_agent_single_component(
        self,
        adapter: MultiAgentAdapter,
    ) -> None:
        """Single component is routed to the correct agent."""
        # Arrange
        candidate = {"generator.instruction": "evolved instruction"}
        original_instruction = adapter.agents["generator"].instruction

        # Act - call actual method
        originals = adapter._apply_candidate(candidate)

        # Assert - verify state change
        assert adapter.agents["generator"].instruction == "evolved instruction"

        # Assert - verify original value tracked
        assert originals["generator.instruction"] == original_instruction

    def test_apply_candidate_routes_multiple_components_to_multiple_agents(
        self,
        adapter: MultiAgentAdapter,
    ) -> None:
        """Multiple components are routed to their respective agents."""
        # Arrange
        original_gen = adapter.agents["generator"].instruction
        original_critic = adapter.agents["critic"].instruction
        candidate = {
            "generator.instruction": "gen evolved",
            "critic.instruction": "critic evolved",
        }

        # Act - call actual method
        originals = adapter._apply_candidate(candidate)

        # Assert - each agent got the correct instruction
        assert adapter.agents["generator"].instruction == "gen evolved"
        assert adapter.agents["critic"].instruction == "critic evolved"

        # Assert - originals tracked correctly
        assert originals["generator.instruction"] == original_gen
        assert originals["critic.instruction"] == original_critic


class TestValidateComponents:
    """Tests for _validate_components behavior (T007-T010a).

    Note:
        Tests _validate_components via constructor since it's called in __init__.
    """

    def test_validate_components_passes_for_valid_configuration(
        self,
        test_agents: dict[str, LlmAgent],
        test_components: dict[str, list[str]],
        test_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """Valid configuration passes validation without errors."""
        # Act - create adapter (calls _validate_components in __init__)
        adapter = MultiAgentAdapter(
            agents=test_agents,
            primary="generator",
            components=test_components,
            scorer=test_scorer,
            proposer=mock_proposer,
        )

        # Assert - no exceptions raised means validation passed
        assert adapter is not None
        assert adapter.agents == test_agents
        assert adapter.components == test_components

    def test_validate_components_raises_for_unknown_agent_in_components(
        self,
        test_agents: dict[str, LlmAgent],
        test_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """ValueError raised when agent in components not in agents dict (T008)."""
        # Arrange
        invalid_components = {
            "generator": ["instruction"],
            "nonexistent": ["instruction"],  # Unknown agent
        }

        # Act & Assert
        with pytest.raises(ValueError, match="not found.*Available"):
            MultiAgentAdapter(
                agents=test_agents,
                primary="generator",
                components=invalid_components,
                scorer=test_scorer,
                proposer=mock_proposer,
            )

    def test_validate_components_raises_for_unknown_component_handler(
        self,
        test_agents: dict[str, LlmAgent],
        test_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """ValueError raised when component has no handler (T009)."""
        # Arrange
        invalid_components = {
            "generator": ["unknown_component"],  # No handler registered
            "critic": [],  # Include critic to pass agent validation
        }

        # Act & Assert
        with pytest.raises(ValueError, match="No handler.*Available"):
            MultiAgentAdapter(
                agents=test_agents,
                primary="generator",
                components=invalid_components,
                scorer=test_scorer,
                proposer=mock_proposer,
            )

    def test_validate_components_raises_for_agent_missing_from_components(
        self,
        test_agents: dict[str, LlmAgent],
        test_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """ValueError raised when agent in agents dict missing from components (T010)."""
        # Arrange
        incomplete_components = {
            "generator": ["instruction"],
            # "critic" is missing from components
        }

        # Act & Assert
        with pytest.raises(ValueError, match="missing from components"):
            MultiAgentAdapter(
                agents=test_agents,
                primary="generator",
                components=incomplete_components,
                scorer=test_scorer,
                proposer=mock_proposer,
            )

    def test_empty_component_list_excludes_agent_from_evolution(
        self,
        test_agents: dict[str, LlmAgent],
        test_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """Empty component list is valid and excludes agent from evolution (T010a)."""
        # Arrange
        components_with_empty = {
            "generator": ["instruction"],
            "critic": [],  # Empty list = excluded from evolution
        }

        # Act - create adapter (calls _validate_components in __init__)
        adapter = MultiAgentAdapter(
            agents=test_agents,
            primary="generator",
            components=components_with_empty,
            scorer=test_scorer,
            proposer=mock_proposer,
        )

        # Assert - validation passes with empty list
        assert adapter is not None
        assert adapter.components["critic"] == []


class TestRestoreAgents:
    """Tests for _restore_agents behavior (T018-T020)."""

    def test_restore_agents_successful_restoration(
        self,
        adapter: MultiAgentAdapter,
    ) -> None:
        """All agents are restored successfully (T018)."""
        # Arrange
        candidate = {
            "generator.instruction": "evolved",
            "critic.instruction": "evolved",
        }
        originals = adapter._apply_candidate(candidate)

        # Verify agents were modified
        assert adapter.agents["generator"].instruction == "evolved"
        assert adapter.agents["critic"].instruction == "evolved"

        # Act - call actual method
        adapter._restore_agents(originals)

        # Assert - no errors, all restored
        assert adapter.agents["generator"].instruction == "original instruction"
        assert adapter.agents["critic"].instruction == "critic original"

    def test_restore_agents_with_partial_failure_aggregation(
        self,
        adapter: MultiAgentAdapter,
        mocker: MockerFixture,
    ) -> None:
        """Partial failures are aggregated into RestoreError (T019)."""
        # Arrange
        candidate = {
            "generator.instruction": "evolved",
            "critic.instruction": "evolved",
        }
        originals = adapter._apply_candidate(candidate)

        # Mock handler.restore to fail for critic
        from gepa_adk.adapters.components.component_handlers import get_handler

        instruction_handler = get_handler("instruction")
        original_restore = instruction_handler.restore

        def failing_restore(agent, original):
            """Restore that fails for critic agent."""
            if agent.name == "critic":
                raise RuntimeError("restore failed")
            original_restore(agent, original)

        mocker.patch.object(
            instruction_handler,
            "restore",
            side_effect=failing_restore,
        )

        # Act & Assert - RestoreError raised with aggregated errors
        with pytest.raises(RestoreError) as exc_info:
            adapter._restore_agents(originals)

        # Assert - one error aggregated
        assert len(exc_info.value.errors) == 1
        assert exc_info.value.errors[0][0] == "critic.instruction"
        assert isinstance(exc_info.value.errors[0][1], RuntimeError)

    def test_restoration_after_evaluation_error(
        self,
        adapter: MultiAgentAdapter,
    ) -> None:
        """Agents are restored even after evaluation error (T020)."""
        # Arrange
        candidate = {"generator.instruction": "evolved"}
        originals = adapter._apply_candidate(candidate)

        # Verify agent was modified
        assert adapter.agents["generator"].instruction == "evolved"

        evaluation_failed = False

        # Act - simulate evaluate with failure and try/finally restore
        try:
            # Simulate evaluation failure
            raise RuntimeError("evaluation failed")
        except RuntimeError:
            evaluation_failed = True
        finally:
            # Restore should still happen
            adapter._restore_agents(originals)

        # Assert - evaluation failed but agent was restored
        assert evaluation_failed
        assert adapter.agents["generator"].instruction == "original instruction"


class TestOriginalsTracking:
    """Tests for originals tracking per agent (T024-T025)."""

    def test_originals_dict_structure_after_apply(
        self,
        adapter: MultiAgentAdapter,
    ) -> None:
        """Originals dict uses qualified names as keys (T024)."""
        # Arrange
        original_instruction = adapter.agents["generator"].instruction
        candidate = {"generator.instruction": "evolved"}

        # Act - call actual method
        originals = adapter._apply_candidate(candidate)

        # Assert - key is qualified name, value is original
        assert "generator.instruction" in originals
        assert originals["generator.instruction"] == original_instruction

    def test_originals_tracking_multiple_agents_and_components(
        self,
        test_agents: dict[str, LlmAgent],
        test_scorer: MockScorer,
        mock_proposer,
    ) -> None:
        """Originals tracked correctly for multiple agents and components (T025)."""
        # Arrange
        refiner = LlmAgent(
            name="refiner",
            model="gemini-2.5-flash",
            instruction="ref instruction",
        )
        agents_with_refiner = {
            "generator": test_agents["generator"],
            "refiner": refiner,
            "critic": test_agents["critic"],
        }
        components_with_refiner = {
            "generator": ["instruction"],
            "refiner": ["instruction"],
            "critic": ["instruction"],
        }

        adapter = MultiAgentAdapter(
            agents=agents_with_refiner,
            primary="generator",
            components=components_with_refiner,
            scorer=test_scorer,
            proposer=mock_proposer,
        )

        original_gen = adapter.agents["generator"].instruction
        original_ref = adapter.agents["refiner"].instruction
        original_critic = adapter.agents["critic"].instruction

        candidate = {
            "generator.instruction": "gen evolved",
            "refiner.instruction": "ref evolved",
            "critic.instruction": "critic evolved",
        }

        # Act - call actual method
        originals = adapter._apply_candidate(candidate)

        # Assert - all originals tracked with qualified names
        assert len(originals) == 3
        assert originals["generator.instruction"] == original_gen
        assert originals["refiner.instruction"] == original_ref
        assert originals["critic.instruction"] == original_critic

        # Assert - verify agents were modified
        assert adapter.agents["generator"].instruction == "gen evolved"
        assert adapter.agents["refiner"].instruction == "ref evolved"
        assert adapter.agents["critic"].instruction == "critic evolved"

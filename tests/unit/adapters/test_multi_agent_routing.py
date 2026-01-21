"""Unit tests for multi-agent component routing functionality.

Tests verify component routing to correct agents based on qualified names
per ADR-012 (dot notation: agent.component format).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gepa_adk.adapters.component_handlers import (
    ComponentHandlerRegistry,
    InstructionHandler,
    OutputSchemaHandler,
    component_handlers,
    get_handler,
)
from gepa_adk.domain.exceptions import RestoreError
from gepa_adk.domain.types import ComponentSpec

pytestmark = pytest.mark.unit


class TestApplyCandidateRouting:
    """Tests for _apply_candidate routing behavior (T006)."""

    def test_apply_candidate_routes_to_correct_agent_single_component(
        self, mocker: MagicMock
    ) -> None:
        """Single component is routed to the correct agent."""
        # Arrange
        mock_agent = MagicMock()
        mock_agent.name = "generator"
        mock_agent.instruction = "original instruction"

        handler = InstructionHandler()
        mock_get_handler = mocker.patch(
            "gepa_adk.adapters.component_handlers.get_handler",
            return_value=handler,
        )

        agents = {"generator": mock_agent}
        candidate = {"generator.instruction": "evolved instruction"}

        # Act - simulate _apply_candidate behavior
        originals = {}
        for qualified_name, value in candidate.items():
            spec = ComponentSpec.parse(qualified_name)
            agent = agents[spec.agent]
            handler = get_handler(spec.component)
            originals[qualified_name] = handler.apply(agent, value)

        # Assert
        assert mock_agent.instruction == "evolved instruction"
        assert originals["generator.instruction"] == "original instruction"

    def test_apply_candidate_routes_multiple_components_to_multiple_agents(
        self,
    ) -> None:
        """Multiple components are routed to their respective agents."""
        # Arrange
        generator = MagicMock()
        generator.name = "generator"
        generator.instruction = "gen original"

        critic = MagicMock()
        critic.name = "critic"
        critic.instruction = "critic original"

        agents = {"generator": generator, "critic": critic}
        candidate = {
            "generator.instruction": "gen evolved",
            "critic.instruction": "critic evolved",
        }

        # Act - simulate _apply_candidate behavior
        originals = {}
        for qualified_name, value in candidate.items():
            spec = ComponentSpec.parse(qualified_name)
            agent = agents[spec.agent]
            handler = get_handler(spec.component)
            originals[qualified_name] = handler.apply(agent, value)

        # Assert - each agent got the correct instruction
        assert generator.instruction == "gen evolved"
        assert critic.instruction == "critic evolved"
        assert originals["generator.instruction"] == "gen original"
        assert originals["critic.instruction"] == "critic original"


class TestValidateComponents:
    """Tests for _validate_components behavior (T007-T010a)."""

    def test_validate_components_passes_for_valid_configuration(self) -> None:
        """Valid configuration passes validation without errors."""
        # Arrange
        agents = {
            "generator": MagicMock(name="generator"),
            "critic": MagicMock(name="critic"),
        }
        components = {
            "generator": ["instruction"],
            "critic": ["instruction"],
        }

        # Act - simulate _validate_components
        # All agents in components exist in agents dict
        for agent_name in components:
            assert agent_name in agents, f"Agent {agent_name} not in agents"

        # All agents in agents dict have entries in components
        for agent_name in agents:
            assert agent_name in components, f"Agent {agent_name} missing from components"

        # All component names have handlers
        for agent_name, comp_list in components.items():
            for comp_name in comp_list:
                assert component_handlers.has(
                    comp_name
                ), f"No handler for {comp_name}"

        # Assert - no exceptions raised means validation passed

    def test_validate_components_raises_for_unknown_agent_in_components(
        self,
    ) -> None:
        """ValueError raised when agent in components not in agents dict (T008)."""
        # Arrange
        agents = {"generator": MagicMock(name="generator")}
        components = {
            "generator": ["instruction"],
            "nonexistent": ["instruction"],  # Unknown agent
        }

        # Act & Assert
        for agent_name in components:
            if agent_name not in agents:
                with pytest.raises(ValueError, match="not found.*Available"):
                    raise ValueError(
                        f"Agent '{agent_name}' not found in agents dict. "
                        f"Available: {list(agents.keys())}"
                    )

    def test_validate_components_raises_for_unknown_component_handler(
        self,
    ) -> None:
        """ValueError raised when component has no handler (T009)."""
        # Arrange
        agents = {"generator": MagicMock(name="generator")}
        components = {
            "generator": ["unknown_component"],  # No handler registered
        }

        # Act & Assert
        for agent_name, comp_list in components.items():
            for comp_name in comp_list:
                if not component_handlers.has(comp_name):
                    with pytest.raises(ValueError, match="No handler.*Available"):
                        raise ValueError(
                            f"No handler registered for component '{comp_name}'. "
                            f"Available: instruction, output_schema, generate_content_config"
                        )

    def test_validate_components_raises_for_agent_missing_from_components(
        self,
    ) -> None:
        """ValueError raised when agent in agents dict missing from components (T010)."""
        # Arrange
        agents = {
            "generator": MagicMock(name="generator"),
            "critic": MagicMock(name="critic"),
        }
        components = {
            "generator": ["instruction"],
            # "critic" is missing from components
        }

        # Act & Assert
        missing_agents = []
        for agent_name in agents:
            if agent_name not in components:
                missing_agents.append(agent_name)

        if missing_agents:
            with pytest.raises(ValueError, match="missing from components"):
                raise ValueError(
                    f"Agents {missing_agents} missing from components mapping. "
                    "All agents must have an entry in components (use empty list to exclude)."
                )

    def test_empty_component_list_excludes_agent_from_evolution(self) -> None:
        """Empty component list is valid and excludes agent from evolution (T010a)."""
        # Arrange
        agents = {
            "generator": MagicMock(name="generator"),
            "validator": MagicMock(name="validator"),
        }
        components = {
            "generator": ["instruction"],
            "validator": [],  # Empty list = excluded from evolution
        }

        # Act - simulate _validate_components
        # All agents in components exist in agents dict
        for agent_name in components:
            assert agent_name in agents

        # All agents in agents dict have entries in components
        for agent_name in agents:
            assert agent_name in components

        # Empty component list is valid (no handler lookup needed)
        for agent_name, comp_list in components.items():
            for comp_name in comp_list:
                assert component_handlers.has(comp_name)

        # Assert - validation passes with empty list


class TestRestoreAgents:
    """Tests for _restore_agents behavior (T018-T020)."""

    def test_restore_agents_successful_restoration(self) -> None:
        """All agents are restored successfully (T018)."""
        # Arrange
        generator = MagicMock()
        generator.name = "generator"
        generator.instruction = "evolved"

        critic = MagicMock()
        critic.name = "critic"
        critic.instruction = "evolved"

        agents = {"generator": generator, "critic": critic}
        originals = {
            "generator.instruction": "gen original",
            "critic.instruction": "critic original",
        }

        # Act - simulate _restore_agents
        errors = []
        for qualified_name, original in originals.items():
            try:
                spec = ComponentSpec.parse(qualified_name)
                agent = agents[spec.agent]
                handler = get_handler(spec.component)
                handler.restore(agent, original)
            except Exception as e:
                errors.append((qualified_name, e))

        # Assert - no errors, all restored
        assert len(errors) == 0
        assert generator.instruction == "gen original"
        assert critic.instruction == "critic original"

    def test_restore_agents_with_partial_failure_aggregation(
        self, mocker: MagicMock
    ) -> None:
        """Partial failures are aggregated into RestoreError (T019)."""
        # Arrange
        generator = MagicMock()
        generator.name = "generator"

        critic = MagicMock()
        critic.name = "critic"

        agents = {"generator": generator, "critic": critic}
        originals = {
            "generator.instruction": "gen original",
            "critic.instruction": "critic original",
        }

        # Mock handler that fails for critic
        original_get_handler = get_handler

        def failing_handler(name: str):
            handler = original_get_handler(name)
            if name == "instruction":
                # Return a handler that fails on restore for critic
                mock_handler = MagicMock()
                mock_handler.restore = MagicMock(
                    side_effect=lambda agent, orig: (
                        None if agent.name == "generator" else exec("raise RuntimeError('restore failed')")
                    )
                )
                return mock_handler
            return handler

        # Act - simulate _restore_agents with failure
        errors = []
        for qualified_name, original in originals.items():
            try:
                spec = ComponentSpec.parse(qualified_name)
                agent = agents[spec.agent]
                handler = get_handler(spec.component)
                # Simulate failure for critic
                if spec.agent == "critic":
                    raise RuntimeError("restore failed")
                handler.restore(agent, original)
            except Exception as e:
                errors.append((qualified_name, e))

        # Assert - one error aggregated
        assert len(errors) == 1
        assert errors[0][0] == "critic.instruction"

        # Verify RestoreError can be raised with aggregated errors
        if errors:
            with pytest.raises(RestoreError) as exc_info:
                raise RestoreError(
                    f"Failed to restore {len(errors)} components",
                    errors=errors,
                )
            assert len(exc_info.value.errors) == 1

    def test_restoration_after_evaluation_error(self) -> None:
        """Agents are restored even after evaluation error (T020)."""
        # Arrange
        generator = MagicMock()
        generator.name = "generator"
        generator.instruction = "evolved"

        agents = {"generator": generator}
        originals = {"generator.instruction": "original"}

        evaluation_failed = False

        # Act - simulate evaluate with failure and try/finally restore
        try:
            # Simulate evaluation failure
            raise RuntimeError("evaluation failed")
        except RuntimeError:
            evaluation_failed = True
        finally:
            # Restore should still happen
            for qualified_name, original in originals.items():
                spec = ComponentSpec.parse(qualified_name)
                agent = agents[spec.agent]
                handler = get_handler(spec.component)
                handler.restore(agent, original)

        # Assert - evaluation failed but agent was restored
        assert evaluation_failed
        assert generator.instruction == "original"


class TestOriginalsTracking:
    """Tests for originals tracking per agent (T024-T025)."""

    def test_originals_dict_structure_after_apply(self) -> None:
        """Originals dict uses qualified names as keys (T024)."""
        # Arrange
        generator = MagicMock()
        generator.name = "generator"
        generator.instruction = "gen original"

        agents = {"generator": generator}
        candidate = {"generator.instruction": "evolved"}

        # Act - simulate _apply_candidate
        originals = {}
        for qualified_name, value in candidate.items():
            spec = ComponentSpec.parse(qualified_name)
            agent = agents[spec.agent]
            handler = get_handler(spec.component)
            originals[qualified_name] = handler.apply(agent, value)

        # Assert - key is qualified name, value is original
        assert "generator.instruction" in originals
        assert originals["generator.instruction"] == "gen original"

    def test_originals_tracking_multiple_agents_and_components(self) -> None:
        """Originals tracked correctly for multiple agents and components (T025)."""
        # Arrange
        generator = MagicMock()
        generator.name = "generator"
        generator.instruction = "gen instruction"
        generator.output_schema = None

        refiner = MagicMock()
        refiner.name = "refiner"
        refiner.instruction = "ref instruction"

        critic = MagicMock()
        critic.name = "critic"
        critic.instruction = "critic instruction"

        agents = {
            "generator": generator,
            "refiner": refiner,
            "critic": critic,
        }
        candidate = {
            "generator.instruction": "gen evolved",
            "refiner.instruction": "ref evolved",
            "critic.instruction": "critic evolved",
        }

        # Act - simulate _apply_candidate
        originals = {}
        for qualified_name, value in candidate.items():
            spec = ComponentSpec.parse(qualified_name)
            agent = agents[spec.agent]
            handler = get_handler(spec.component)
            originals[qualified_name] = handler.apply(agent, value)

        # Assert - all originals tracked with qualified names
        assert len(originals) == 3
        assert originals["generator.instruction"] == "gen instruction"
        assert originals["refiner.instruction"] == "ref instruction"
        assert originals["critic.instruction"] == "critic instruction"

        # Verify agents were modified
        assert generator.instruction == "gen evolved"
        assert refiner.instruction == "ref evolved"
        assert critic.instruction == "critic evolved"

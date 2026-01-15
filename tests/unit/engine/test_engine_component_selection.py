"""Unit tests for engine component selection logic."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from gepa_adk.adapters.component_selector import (
    RoundRobinComponentSelector,
)
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from gepa_adk.ports.selector import ComponentSelectorProtocol

pytestmark = pytest.mark.unit


class TestComponentListBuilding:
    """Test _build_component_list helper."""

    def test_extracts_candidate_keys(
        self,
        mock_adapter: Any,
        sample_config: EvolutionConfig,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test extracting keys from candidate (T022)."""
        candidate = Candidate(
            components={"instruction": "base", "comp1": "v1", "comp2": "v2"},
            generation=0,
        )
        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=sample_config,
            initial_candidate=candidate,
            batch=sample_batch,
        )

        # Method doesn't exist yet, so we expect AttributeError if we run it now.
        # But we are writing the test first.
        components = engine._build_component_list(candidate)
        # "instruction" is excluded because other keys exist
        assert set(components) == {"comp1", "comp2"}

    def test_excludes_generic_instruction_alias(
        self,
        mock_adapter: Any,
        sample_config: EvolutionConfig,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test excluding 'instruction' when agent-specific keys exist (T023)."""
        candidate = Candidate(
            components={
                "instruction": "generic",
                "agent1_instruction": "v1",
                "agent2_instruction": "v2",
            },
            generation=0,
        )
        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=sample_config,
            initial_candidate=candidate,
            batch=sample_batch,
        )

        components = engine._build_component_list(candidate)
        # Should exclude "instruction" because other keys exist
        assert "instruction" not in components
        assert "agent1_instruction" in components
        assert "agent2_instruction" in components

    def test_keeps_instruction_if_only_key(
        self,
        mock_adapter: Any,
        sample_config: EvolutionConfig,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test keeping 'instruction' if it is the only key."""
        candidate = Candidate(components={"instruction": "generic"}, generation=0)
        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=sample_config,
            initial_candidate=candidate,
            batch=sample_batch,
        )

        components = engine._build_component_list(candidate)
        assert components == ["instruction"]


class TestEngineComponentSelection:
    """Test integration of selector into engine."""

    @pytest.mark.asyncio
    async def test_uses_selector_in_propose_mutation(
        self,
        mock_adapter: Any,
        sample_config: EvolutionConfig,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test that engine uses the injected selector (T024)."""
        # Mock selector
        mock_selector = MagicMock(spec=ComponentSelectorProtocol)
        mock_selector.select_components = AsyncMock(return_value=["agent1_instruction"])

        candidate = Candidate(
            components={
                "instruction": "base",
                "agent1_instruction": "v1",
                "agent2_instruction": "v2",
            },
            generation=0,
        )

        # This will fail until __init__ is updated
        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=sample_config,
            initial_candidate=candidate,
            batch=sample_batch,
            component_selector=mock_selector,
        )

        # Initialize state manually or mock it
        engine._state = MagicMock()
        engine._state.best_candidate = candidate
        engine._state.iteration = 1
        engine._state.last_eval_batch = MagicMock()  # Mock eval batch

        # Mock adapter methods
        mock_adapter.make_reflective_dataset = AsyncMock(return_value={})
        mock_adapter.propose_new_texts = AsyncMock(return_value={})
        engine.adapter = mock_adapter  # Ensure it's using the mock

        # Mock _build_component_list if not implemented yet, but we want to test integration
        # Assuming _build_component_list works or is mocked
        # Use object.__setattr__ to bypass type checking for method assignment
        object.__setattr__(
            engine,
            "_build_component_list",
            MagicMock(return_value=["agent1_instruction", "agent2_instruction"]),
        )

        await engine._propose_mutation()
        mock_selector.select_components.assert_called_once()
        call_args = mock_selector.select_components.call_args
        # args: components, iteration, candidate_idx
        # Components passed to selector should come from _build_component_list
        # Called with kwargs
        assert set(call_args.kwargs["components"]) == {
            "agent1_instruction",
            "agent2_instruction",
        }
        assert call_args.kwargs["iteration"] == 1

    @pytest.mark.asyncio
    async def test_defaults_to_round_robin(
        self,
        mock_adapter: Any,
        sample_config: EvolutionConfig,
        sample_batch: list[dict[str, str]],
    ) -> None:
        """Test engine defaults to round-robin if no selector provided (T025)."""
        candidate = Candidate(
            components={"instruction": "base", "A": "1", "B": "2"}, generation=0
        )
        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=sample_config,
            initial_candidate=candidate,
            batch=sample_batch,
            # No component_selector
        )

        # Check internal attribute
        # Note: private attribute might not exist yet
        assert isinstance(engine._component_selector, RoundRobinComponentSelector)

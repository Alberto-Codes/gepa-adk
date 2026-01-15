"""Unit tests for component selector adapters."""

import pytest

from gepa_adk.adapters.component_selector import (
    AllComponentSelector,
    RoundRobinComponentSelector,
    create_component_selector,
)

pytestmark = pytest.mark.unit


class TestRoundRobinComponentSelector:
    """Test suite for RoundRobinComponentSelector."""

    @pytest.mark.asyncio
    async def test_basic_cycling(self) -> None:
        """Test basic cycling through components (T007)."""
        selector = RoundRobinComponentSelector()
        components = ["A", "B", "C"]
        candidate_idx = 0

        # Iteration 1 -> "A"
        selected = await selector.select_components(components, 1, candidate_idx)
        assert selected == ["A"]

        # Iteration 2 -> "B"
        selected = await selector.select_components(components, 2, candidate_idx)
        assert selected == ["B"]

        # Iteration 3 -> "C"
        selected = await selector.select_components(components, 3, candidate_idx)
        assert selected == ["C"]

        # Iteration 4 -> "A" (wrap around)
        selected = await selector.select_components(components, 4, candidate_idx)
        assert selected == ["A"]

    @pytest.mark.asyncio
    async def test_single_component(self) -> None:
        """Test round-robin with single component (T008)."""
        selector = RoundRobinComponentSelector()
        components = ["A"]
        candidate_idx = 0

        assert await selector.select_components(components, 1, candidate_idx) == ["A"]
        assert await selector.select_components(components, 2, candidate_idx) == ["A"]

    @pytest.mark.asyncio
    async def test_per_candidate_state_tracking(self) -> None:
        """Test per-candidate-idx state tracking (T009)."""
        selector = RoundRobinComponentSelector()
        components = ["A", "B"]

        # Candidate 0: select A
        assert await selector.select_components(components, 1, candidate_idx=0) == ["A"]

        # Candidate 1: select A (independent state)
        assert await selector.select_components(components, 1, candidate_idx=1) == ["A"]

        # Candidate 0: select B
        assert await selector.select_components(components, 2, candidate_idx=0) == ["B"]

        # Candidate 1: select B
        assert await selector.select_components(components, 2, candidate_idx=1) == ["B"]

    @pytest.mark.asyncio
    async def test_modulo_wrap_around(self) -> None:
        """Test round-robin modulo wrap-around logic (T010)."""
        selector = RoundRobinComponentSelector()
        components = ["A", "B"]
        candidate_idx = 0

        # Should be A, B, A, B...
        # We manually advance internal state via calls
        await selector.select_components(components, 1, candidate_idx)  # A
        await selector.select_components(components, 2, candidate_idx)  # B

        # Wrap around
        assert await selector.select_components(components, 3, candidate_idx) == ["A"]

    @pytest.mark.asyncio
    async def test_zero_components_raises_value_error(self) -> None:
        """Test selector with zero components raises ValueError (T010a)."""
        selector = RoundRobinComponentSelector()
        with pytest.raises(ValueError, match="No components provided"):
            await selector.select_components([], 1, 0)


class TestAllComponentSelector:
    """Test suite for AllComponentSelector."""

    @pytest.mark.asyncio
    async def test_returns_all_components(self) -> None:
        """Test that all components are returned (T016)."""
        selector = AllComponentSelector()
        components = ["A", "B", "C"]

        selected = await selector.select_components(components, 1, 0)
        assert selected == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_stateless_behavior(self) -> None:
        """Test that result is consistent regardless of state (T017)."""
        selector = AllComponentSelector()
        components = ["A", "B"]

        # Iteration 1
        assert await selector.select_components(components, 1, 0) == ["A", "B"]
        # Iteration 2
        assert await selector.select_components(components, 2, 0) == ["A", "B"]
        # Different candidate
        assert await selector.select_components(components, 1, 1) == ["A", "B"]

    @pytest.mark.asyncio
    async def test_zero_components_raises_value_error(self) -> None:
        """Test selector with zero components raises ValueError."""
        selector = AllComponentSelector()
        with pytest.raises(ValueError, match="No components provided"):
            await selector.select_components([], 1, 0)


class TestComponentSelectorFactory:
    """Test suite for create_component_selector factory."""

    def test_creates_round_robin(self) -> None:
        """Test creating round-robin selector (T032)."""
        selector = create_component_selector("round_robin")
        assert isinstance(selector, RoundRobinComponentSelector)

    def test_creates_all(self) -> None:
        """Test creating all-components selector (T033)."""
        selector = create_component_selector("all")
        assert isinstance(selector, AllComponentSelector)

    def test_invalid_type_raises_error(self) -> None:
        """Test invalid type raises ValueError (T034)."""
        with pytest.raises(ValueError, match="Unknown component selector"):
            create_component_selector("invalid")

    def test_alias_variations(self) -> None:
        """Test alias variations (T035)."""
        assert isinstance(
            create_component_selector("roundrobin"), RoundRobinComponentSelector
        )
        assert isinstance(
            create_component_selector("all_components"), AllComponentSelector
        )

"""Unit tests for CompositeStopper.

Tests cover all acceptance criteria from issue #195:
- Any mode - one stopper fires → True
- Any mode - no stoppers fire → False
- All mode - all stoppers fire → True
- All mode - one stopper doesn't fire → False
- Empty stoppers rejected
- Invalid mode rejected
- Nested composites work
- Protocol compliance
"""

import pytest

from gepa_adk.adapters.stoppers import CompositeStopper
from gepa_adk.domain.stopper import StopperState
from gepa_adk.ports.stopper import StopperProtocol

pytestmark = pytest.mark.unit


@pytest.fixture
def default_state() -> StopperState:
    """Create a default stopper state for testing."""
    return StopperState(
        iteration=5,
        best_score=0.5,
        stagnation_counter=0,
        total_evaluations=25,
        candidates_count=1,
        elapsed_seconds=30.0,
    )


class AlwaysTrueStopper:
    """Test stopper that always returns True."""

    def __call__(self, state: StopperState) -> bool:
        """Return True regardless of state."""
        return True


class AlwaysFalseStopper:
    """Test stopper that always returns False."""

    def __call__(self, state: StopperState) -> bool:
        """Return False regardless of state."""
        return False


class TestCompositeStopperInitialization:
    """Tests for CompositeStopper initialization and validation."""

    def test_init_with_single_stopper_succeeds(self) -> None:
        """CompositeStopper accepts a single stopper."""
        stopper = CompositeStopper([AlwaysTrueStopper()])

        assert len(stopper.stoppers) == 1
        assert stopper.mode == "any"

    def test_init_with_multiple_stoppers_succeeds(self) -> None:
        """CompositeStopper accepts multiple stoppers."""
        stopper = CompositeStopper([AlwaysTrueStopper(), AlwaysFalseStopper()])

        assert len(stopper.stoppers) == 2

    def test_init_with_empty_list_raises_value_error(self) -> None:
        """CompositeStopper rejects empty stopper list."""
        with pytest.raises(ValueError) as excinfo:
            CompositeStopper([])

        assert "At least one stopper required" in str(excinfo.value)

    def test_init_with_invalid_mode_raises_value_error(self) -> None:
        """CompositeStopper rejects invalid mode."""
        with pytest.raises(ValueError) as excinfo:
            CompositeStopper([AlwaysTrueStopper()], mode="invalid")

        assert "mode must be 'any' or 'all'" in str(excinfo.value)

    def test_init_with_any_mode_succeeds(self) -> None:
        """CompositeStopper accepts 'any' mode."""
        stopper = CompositeStopper([AlwaysTrueStopper()], mode="any")

        assert stopper.mode == "any"

    def test_init_with_all_mode_succeeds(self) -> None:
        """CompositeStopper accepts 'all' mode."""
        stopper = CompositeStopper([AlwaysTrueStopper()], mode="all")

        assert stopper.mode == "all"

    def test_init_default_mode_is_any(self) -> None:
        """CompositeStopper defaults to 'any' mode."""
        stopper = CompositeStopper([AlwaysTrueStopper()])

        assert stopper.mode == "any"


class TestCompositeStopperAnyMode:
    """Tests for CompositeStopper with mode='any' (OR logic)."""

    def test_any_mode_returns_true_when_one_stopper_fires(
        self, default_state: StopperState
    ) -> None:
        """Any mode returns True when at least one stopper returns True."""
        stopper = CompositeStopper(
            [AlwaysFalseStopper(), AlwaysTrueStopper()],
            mode="any",
        )

        result = stopper(default_state)

        assert result is True

    def test_any_mode_returns_true_when_first_stopper_fires(
        self, default_state: StopperState
    ) -> None:
        """Any mode returns True when first stopper returns True."""
        stopper = CompositeStopper(
            [AlwaysTrueStopper(), AlwaysFalseStopper()],
            mode="any",
        )

        result = stopper(default_state)

        assert result is True

    def test_any_mode_returns_false_when_no_stoppers_fire(
        self, default_state: StopperState
    ) -> None:
        """Any mode returns False when no stoppers return True."""
        stopper = CompositeStopper(
            [AlwaysFalseStopper(), AlwaysFalseStopper()],
            mode="any",
        )

        result = stopper(default_state)

        assert result is False

    def test_any_mode_returns_true_when_all_stoppers_fire(
        self, default_state: StopperState
    ) -> None:
        """Any mode returns True when all stoppers return True."""
        stopper = CompositeStopper(
            [AlwaysTrueStopper(), AlwaysTrueStopper()],
            mode="any",
        )

        result = stopper(default_state)

        assert result is True


class TestCompositeStopperAllMode:
    """Tests for CompositeStopper with mode='all' (AND logic)."""

    def test_all_mode_returns_true_when_all_stoppers_fire(
        self, default_state: StopperState
    ) -> None:
        """All mode returns True when all stoppers return True."""
        stopper = CompositeStopper(
            [AlwaysTrueStopper(), AlwaysTrueStopper()],
            mode="all",
        )

        result = stopper(default_state)

        assert result is True

    def test_all_mode_returns_false_when_one_stopper_doesnt_fire(
        self, default_state: StopperState
    ) -> None:
        """All mode returns False when any stopper returns False."""
        stopper = CompositeStopper(
            [AlwaysTrueStopper(), AlwaysFalseStopper()],
            mode="all",
        )

        result = stopper(default_state)

        assert result is False

    def test_all_mode_returns_false_when_first_stopper_doesnt_fire(
        self, default_state: StopperState
    ) -> None:
        """All mode returns False when first stopper returns False."""
        stopper = CompositeStopper(
            [AlwaysFalseStopper(), AlwaysTrueStopper()],
            mode="all",
        )

        result = stopper(default_state)

        assert result is False

    def test_all_mode_returns_false_when_no_stoppers_fire(
        self, default_state: StopperState
    ) -> None:
        """All mode returns False when no stoppers return True."""
        stopper = CompositeStopper(
            [AlwaysFalseStopper(), AlwaysFalseStopper()],
            mode="all",
        )

        result = stopper(default_state)

        assert result is False


class TestCompositeStopperNestedComposites:
    """Tests for nested CompositeStopper behavior."""

    def test_nested_any_in_any_evaluates_correctly(
        self, default_state: StopperState
    ) -> None:
        """Nested 'any' inside 'any' evaluates OR logic correctly."""
        inner = CompositeStopper(
            [AlwaysFalseStopper(), AlwaysTrueStopper()],
            mode="any",
        )
        outer = CompositeStopper(
            [AlwaysFalseStopper(), inner],
            mode="any",
        )

        result = outer(default_state)

        assert result is True

    def test_nested_all_in_any_evaluates_correctly(
        self, default_state: StopperState
    ) -> None:
        """Nested 'all' inside 'any' evaluates complex logic correctly."""
        inner = CompositeStopper(
            [AlwaysTrueStopper(), AlwaysFalseStopper()],
            mode="all",
        )  # Returns False
        outer = CompositeStopper(
            [inner, AlwaysTrueStopper()],
            mode="any",
        )

        result = outer(default_state)

        assert result is True

    def test_nested_any_in_all_evaluates_correctly(
        self, default_state: StopperState
    ) -> None:
        """Nested 'any' inside 'all' evaluates complex logic correctly."""
        inner = CompositeStopper(
            [AlwaysFalseStopper(), AlwaysTrueStopper()],
            mode="any",
        )  # Returns True
        outer = CompositeStopper(
            [inner, AlwaysTrueStopper()],
            mode="all",
        )

        result = outer(default_state)

        assert result is True

    def test_nested_all_in_all_evaluates_correctly(
        self, default_state: StopperState
    ) -> None:
        """Nested 'all' inside 'all' evaluates AND logic correctly."""
        inner = CompositeStopper(
            [AlwaysTrueStopper(), AlwaysFalseStopper()],
            mode="all",
        )  # Returns False
        outer = CompositeStopper(
            [inner, AlwaysTrueStopper()],
            mode="all",
        )

        result = outer(default_state)

        assert result is False

    def test_deeply_nested_composite_evaluates_correctly(
        self, default_state: StopperState
    ) -> None:
        """Deeply nested composites evaluate correctly."""
        level1 = CompositeStopper(
            [AlwaysTrueStopper(), AlwaysTrueStopper()],
            mode="all",
        )  # True
        level2 = CompositeStopper(
            [level1, AlwaysFalseStopper()],
            mode="any",
        )  # True
        level3 = CompositeStopper(
            [level2, AlwaysTrueStopper()],
            mode="all",
        )  # True

        result = level3(default_state)

        assert result is True


class TestCompositeStopperProtocolCompliance:
    """Tests verifying CompositeStopper satisfies StopperProtocol."""

    def test_satisfies_stopper_protocol(self) -> None:
        """CompositeStopper instance satisfies StopperProtocol."""
        stopper = CompositeStopper([AlwaysTrueStopper()])

        assert isinstance(stopper, StopperProtocol)

    def test_call_returns_bool(self, default_state: StopperState) -> None:
        """CompositeStopper __call__ returns a boolean value."""
        stopper = CompositeStopper([AlwaysTrueStopper()])

        result = stopper(default_state)

        assert isinstance(result, bool)


class TestCompositeStopperRepr:
    """Tests for CompositeStopper string representation."""

    def test_repr_includes_stoppers_and_mode(self) -> None:
        """Repr includes stoppers list and mode."""
        stopper = CompositeStopper(
            [AlwaysTrueStopper(), AlwaysFalseStopper()],
            mode="any",
        )

        result = repr(stopper)

        assert "CompositeStopper" in result
        assert "mode='any'" in result

    def test_repr_with_all_mode(self) -> None:
        """Repr correctly shows 'all' mode."""
        stopper = CompositeStopper([AlwaysTrueStopper()], mode="all")

        result = repr(stopper)

        assert "mode='all'" in result


class TestCompositeStopperEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_stopper_any_mode_returns_stopper_result(
        self, default_state: StopperState
    ) -> None:
        """Single stopper in 'any' mode returns that stopper's result."""
        stopper_true = CompositeStopper([AlwaysTrueStopper()], mode="any")
        stopper_false = CompositeStopper([AlwaysFalseStopper()], mode="any")

        assert stopper_true(default_state) is True
        assert stopper_false(default_state) is False

    def test_single_stopper_all_mode_returns_stopper_result(
        self, default_state: StopperState
    ) -> None:
        """Single stopper in 'all' mode returns that stopper's result."""
        stopper_true = CompositeStopper([AlwaysTrueStopper()], mode="all")
        stopper_false = CompositeStopper([AlwaysFalseStopper()], mode="all")

        assert stopper_true(default_state) is True
        assert stopper_false(default_state) is False

    def test_many_stoppers_any_mode(self, default_state: StopperState) -> None:
        """Many stoppers in 'any' mode work correctly."""
        many_false = [AlwaysFalseStopper() for _ in range(10)]
        many_false.append(AlwaysTrueStopper())
        stopper = CompositeStopper(many_false, mode="any")

        result = stopper(default_state)

        assert result is True

    def test_many_stoppers_all_mode(self, default_state: StopperState) -> None:
        """Many stoppers in 'all' mode work correctly."""
        many_true = [AlwaysTrueStopper() for _ in range(10)]
        many_true.append(AlwaysFalseStopper())
        stopper = CompositeStopper(many_true, mode="all")

        result = stopper(default_state)

        assert result is False

    def test_stoppers_receive_state(self) -> None:
        """Child stoppers receive the state object."""
        received_states: list[StopperState] = []

        class StateCapturer:
            def __call__(self, state: StopperState) -> bool:
                received_states.append(state)
                return False

        state = StopperState(
            iteration=10,
            best_score=0.9,
            stagnation_counter=3,
            total_evaluations=100,
            candidates_count=5,
            elapsed_seconds=60.0,
        )
        stopper = CompositeStopper([StateCapturer(), StateCapturer()])

        stopper(state)

        assert len(received_states) == 2
        assert received_states[0] is state
        assert received_states[1] is state

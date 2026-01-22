"""Unit tests for StopperState domain model.

Tests cover the StopperState dataclass including:
- Field initialization and access
- Immutability (frozen dataclass)
- Slots usage for memory efficiency
"""

import pytest

from gepa_adk.domain.stopper import StopperState

pytestmark = pytest.mark.unit


class TestStopperStateCreation:
    """Tests for StopperState initialization."""

    def test_stopper_state_accepts_all_fields(self) -> None:
        """StopperState accepts all required fields."""
        state = StopperState(
            iteration=5,
            best_score=0.85,
            stagnation_counter=2,
            total_evaluations=50,
            candidates_count=3,
            elapsed_seconds=120.5,
        )

        assert state.iteration == 5
        assert state.best_score == 0.85
        assert state.stagnation_counter == 2
        assert state.total_evaluations == 50
        assert state.candidates_count == 3
        assert state.elapsed_seconds == 120.5

    def test_stopper_state_with_zero_values(self) -> None:
        """StopperState accepts zero values for all fields."""
        state = StopperState(
            iteration=0,
            best_score=0.0,
            stagnation_counter=0,
            total_evaluations=0,
            candidates_count=0,
            elapsed_seconds=0.0,
        )

        assert state.iteration == 0
        assert state.best_score == 0.0
        assert state.stagnation_counter == 0
        assert state.total_evaluations == 0
        assert state.candidates_count == 0
        assert state.elapsed_seconds == 0.0

    def test_stopper_state_with_boundary_score(self) -> None:
        """StopperState accepts boundary score values."""
        state_zero = StopperState(
            iteration=1,
            best_score=0.0,
            stagnation_counter=0,
            total_evaluations=1,
            candidates_count=1,
            elapsed_seconds=1.0,
        )
        assert state_zero.best_score == 0.0

        state_one = StopperState(
            iteration=1,
            best_score=1.0,
            stagnation_counter=0,
            total_evaluations=1,
            candidates_count=1,
            elapsed_seconds=1.0,
        )
        assert state_one.best_score == 1.0


class TestStopperStateImmutability:
    """Tests for StopperState immutability (frozen=True)."""

    def test_stopper_state_iteration_is_immutable(self) -> None:
        """Attempting to modify iteration raises FrozenInstanceError."""
        state = StopperState(
            iteration=5,
            best_score=0.85,
            stagnation_counter=2,
            total_evaluations=50,
            candidates_count=3,
            elapsed_seconds=120.5,
        )

        with pytest.raises(AttributeError):
            state.iteration = 10  # type: ignore[misc]

    def test_stopper_state_best_score_is_immutable(self) -> None:
        """Attempting to modify best_score raises FrozenInstanceError."""
        state = StopperState(
            iteration=5,
            best_score=0.85,
            stagnation_counter=2,
            total_evaluations=50,
            candidates_count=3,
            elapsed_seconds=120.5,
        )

        with pytest.raises(AttributeError):
            state.best_score = 0.95  # type: ignore[misc]

    def test_stopper_state_stagnation_counter_is_immutable(self) -> None:
        """Attempting to modify stagnation_counter raises FrozenInstanceError."""
        state = StopperState(
            iteration=5,
            best_score=0.85,
            stagnation_counter=2,
            total_evaluations=50,
            candidates_count=3,
            elapsed_seconds=120.5,
        )

        with pytest.raises(AttributeError):
            state.stagnation_counter = 5  # type: ignore[misc]

    def test_stopper_state_total_evaluations_is_immutable(self) -> None:
        """Attempting to modify total_evaluations raises FrozenInstanceError."""
        state = StopperState(
            iteration=5,
            best_score=0.85,
            stagnation_counter=2,
            total_evaluations=50,
            candidates_count=3,
            elapsed_seconds=120.5,
        )

        with pytest.raises(AttributeError):
            state.total_evaluations = 100  # type: ignore[misc]

    def test_stopper_state_candidates_count_is_immutable(self) -> None:
        """Attempting to modify candidates_count raises FrozenInstanceError."""
        state = StopperState(
            iteration=5,
            best_score=0.85,
            stagnation_counter=2,
            total_evaluations=50,
            candidates_count=3,
            elapsed_seconds=120.5,
        )

        with pytest.raises(AttributeError):
            state.candidates_count = 10  # type: ignore[misc]

    def test_stopper_state_elapsed_seconds_is_immutable(self) -> None:
        """Attempting to modify elapsed_seconds raises FrozenInstanceError."""
        state = StopperState(
            iteration=5,
            best_score=0.85,
            stagnation_counter=2,
            total_evaluations=50,
            candidates_count=3,
            elapsed_seconds=120.5,
        )

        with pytest.raises(AttributeError):
            state.elapsed_seconds = 200.0  # type: ignore[misc]


class TestStopperStateSlots:
    """Tests for StopperState slots=True optimization."""

    def test_stopper_state_has_slots(self) -> None:
        """StopperState uses __slots__ for memory efficiency."""
        assert hasattr(StopperState, "__slots__")

    def test_stopper_state_no_dict(self) -> None:
        """StopperState instances have no __dict__ due to slots."""
        state = StopperState(
            iteration=5,
            best_score=0.85,
            stagnation_counter=2,
            total_evaluations=50,
            candidates_count=3,
            elapsed_seconds=120.5,
        )

        assert not hasattr(state, "__dict__")

# Contract: ParetoState Domain Model

**Feature**: 022-pareto-frontier
**Date**: 2026-01-14
**Type**: Domain Model (dataclass)

## Overview

`ParetoState` is the core domain model for tracking evolution state with per-example score tracking, enabling Pareto-aware candidate selection.

---

## Class Definition

```python
from dataclasses import dataclass, field
from typing import Literal
from gepa_adk.domain.models import Candidate

FrontierType = Literal["instance", "objective", "hybrid", "cartesian"]

@dataclass
class ParetoFrontier:
    """Tracks non-dominated candidates across validation examples.

    Attributes:
        example_leaders: Maps example index to set of candidate indices
            that achieve the best score on that example.
        best_scores: Maps example index to the best score achieved.
    """

    example_leaders: dict[int, set[int]] = field(default_factory=dict)
    best_scores: dict[int, float] = field(default_factory=dict)

    def update(
        self,
        candidate_idx: int,
        scores: dict[int, float],
    ) -> None:
        """Update frontier with new candidate scores.

        Args:
            candidate_idx: Index of the new candidate.
            scores: Mapping of example_idx to score.
        """
        ...

    def get_non_dominated(self) -> set[int]:
        """Return all candidate indices in any leader set."""
        ...

    def get_selection_weights(self) -> dict[int, int]:
        """Return candidate_idx to frequency count mapping."""
        ...


@dataclass
class ParetoState:
    """Evolution state with Pareto frontier tracking.

    This replaces the simple _EngineState when Pareto-aware selection
    is enabled, tracking per-example scores for all candidates.

    Attributes:
        candidates: List of all candidates discovered.
        candidate_scores: Maps candidate_idx to {example_idx: score}.
        frontier: Current Pareto frontier.
        frontier_type: Strategy for frontier tracking.
        iteration: Current iteration number.
        best_average_idx: Index of highest-average-score candidate.
        stagnation_counter: Iterations since last improvement.
        original_score: Baseline score from first evaluation.
    """

    candidates: list[Candidate] = field(default_factory=list)
    candidate_scores: dict[int, dict[int, float]] = field(default_factory=dict)
    frontier: ParetoFrontier = field(default_factory=ParetoFrontier)
    frontier_type: FrontierType = "instance"
    iteration: int = 0
    best_average_idx: int = 0
    stagnation_counter: int = 0
    original_score: float = 0.0

    def add_candidate(
        self,
        candidate: Candidate,
        scores: list[float],
    ) -> int:
        """Add a new candidate with its per-example scores.

        Args:
            candidate: The candidate to add.
            scores: List of scores, one per example (index-aligned).

        Returns:
            Index of the newly added candidate.
        """
        ...

    def get_average_score(self, candidate_idx: int) -> float:
        """Calculate average score for a candidate.

        Args:
            candidate_idx: Index of candidate.

        Returns:
            Mean of all per-example scores.

        Raises:
            KeyError: If candidate_idx not found.
        """
        ...

    def update_best_average(self) -> None:
        """Recalculate and update best_average_idx."""
        ...
```

---

## Contract Guarantees

### Construction Invariants
| Invariant | Description |
|-----------|-------------|
| Empty initial state | Fresh state has empty candidates list |
| Frontier initialized | frontier is always a valid ParetoFrontier |
| Valid frontier_type | Must be one of "instance", "objective", "hybrid", "cartesian" |

### Method Contracts

#### `add_candidate(candidate, scores)`
| Condition | Type | Description |
|-----------|------|-------------|
| Pre | `len(scores) >= 1` | Must have at least one score |
| Pre | All scores finite | No NaN or infinity values |
| Post | Returns valid index | `0 <= result < len(self.candidates)` |
| Post | Frontier updated | `self.frontier.update()` called |
| Post | Best updated | `self.best_average_idx` may change |

#### `get_average_score(candidate_idx)`
| Condition | Type | Description |
|-----------|------|-------------|
| Pre | Valid index | `candidate_idx` in `self.candidate_scores` |
| Post | Finite result | Returns finite float |

---

## State Transitions

```
┌─────────────────┐
│  Initial State  │
│  candidates: [] │
│  frontier: {}   │
└────────┬────────┘
         │ add_candidate(c0, scores0)
         ▼
┌─────────────────────────┐
│     One Candidate       │
│  candidates: [c0]       │
│  frontier: {0: {0}}     │
│  best_average_idx: 0    │
└────────┬────────────────┘
         │ add_candidate(c1, scores1)
         ▼
┌──────────────────────────────┐
│      Multiple Candidates     │
│  candidates: [c0, c1]        │
│  frontier: updated           │
│  best_average_idx: 0 or 1    │
└──────────────────────────────┘
```

---

## Test Contract

```python
# tests/unit/test_pareto_state.py

import pytest
from gepa_adk.domain.state import ParetoState, ParetoFrontier
from gepa_adk.domain.models import Candidate

class TestParetoState:
    """Unit tests for ParetoState domain model."""

    def test_initial_state_is_empty(self):
        """Fresh state has no candidates."""
        state = ParetoState()
        assert len(state.candidates) == 0
        assert len(state.candidate_scores) == 0

    def test_add_candidate_returns_valid_index(self):
        """add_candidate returns correct index."""
        state = ParetoState()
        candidate = Candidate(components={"instruction": "test"})
        idx = state.add_candidate(candidate, scores=[0.5, 0.6, 0.7])
        assert idx == 0
        assert len(state.candidates) == 1

    def test_add_candidate_updates_frontier(self):
        """Frontier is updated after adding candidate."""
        state = ParetoState()
        candidate = Candidate(components={"instruction": "test"})
        state.add_candidate(candidate, scores=[0.8, 0.6])

        assert 0 in state.frontier.get_non_dominated()

    def test_add_multiple_candidates_tracks_specialization(self):
        """Different candidates can lead on different examples."""
        state = ParetoState()

        c0 = Candidate(components={"instruction": "general"})
        c1 = Candidate(components={"instruction": "specialist"})

        state.add_candidate(c0, scores=[0.7, 0.7])  # Generalist
        state.add_candidate(c1, scores=[0.9, 0.5])  # Specialist on example 0

        # c1 should lead example 0, c0 leads example 1
        assert 1 in state.frontier.example_leaders.get(0, set())
        assert 0 in state.frontier.example_leaders.get(1, set())

    def test_get_average_score_calculates_correctly(self):
        """Average score is computed from all examples."""
        state = ParetoState()
        candidate = Candidate(components={"instruction": "test"})
        state.add_candidate(candidate, scores=[0.4, 0.6, 0.8])

        avg = state.get_average_score(0)
        assert avg == pytest.approx(0.6)

    def test_best_average_idx_updates_on_better_candidate(self):
        """best_average_idx changes when better candidate added."""
        state = ParetoState()

        c0 = Candidate(components={"instruction": "ok"})
        c1 = Candidate(components={"instruction": "better"})

        state.add_candidate(c0, scores=[0.5, 0.5])
        assert state.best_average_idx == 0

        state.add_candidate(c1, scores=[0.9, 0.9])
        assert state.best_average_idx == 1


class TestParetoFrontier:
    """Unit tests for ParetoFrontier."""

    def test_empty_frontier(self):
        """Empty frontier has no non-dominated candidates."""
        frontier = ParetoFrontier()
        assert len(frontier.get_non_dominated()) == 0

    def test_single_candidate_is_non_dominated(self):
        """Single candidate is always non-dominated."""
        frontier = ParetoFrontier()
        frontier.update(0, {0: 0.8, 1: 0.6})

        assert frontier.get_non_dominated() == {0}

    def test_selection_weights_count_frequency(self):
        """Weights reflect how many examples a candidate leads."""
        frontier = ParetoFrontier()
        frontier.update(0, {0: 0.9, 1: 0.9, 2: 0.5})  # Leads 0, 1
        frontier.update(1, {0: 0.5, 1: 0.5, 2: 0.9})  # Leads 2

        weights = frontier.get_selection_weights()
        assert weights[0] == 2  # Leads 2 examples
        assert weights[1] == 1  # Leads 1 example
```

---

## Usage Examples

### Creating and Populating State
```python
from gepa_adk.domain.state import ParetoState
from gepa_adk.domain.models import Candidate

# Create state
state = ParetoState(frontier_type="instance")

# Add initial candidate
initial = Candidate(components={"instruction": "Be helpful"})
state.add_candidate(initial, scores=[0.7, 0.6, 0.8])

# Add evolved candidate
evolved = Candidate(
    components={"instruction": "Be helpful and concise"},
    generation=1,
)
state.add_candidate(evolved, scores=[0.9, 0.5, 0.7])

# Check frontier
non_dominated = state.frontier.get_non_dominated()
print(f"Non-dominated candidates: {non_dominated}")  # {0, 1}
```

### Integration with Engine
```python
# In AsyncGEPAEngine._initialize_baseline()
eval_batch = await self.adapter.evaluate(batch, candidate, capture_traces=True)
scores = eval_batch.scores  # Per-example scores

self._pareto_state = ParetoState(frontier_type=self.config.frontier_type)
self._pareto_state.add_candidate(self._initial_candidate, scores)
```

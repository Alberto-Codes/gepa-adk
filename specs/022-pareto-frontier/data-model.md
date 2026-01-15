# Data Model: Pareto Frontier Tracking and Candidate Selection

**Feature**: 022-pareto-frontier
**Date**: 2026-01-14

## Entity Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│   ParetoState   │────▶│  ParetoFrontier  │────▶│  CandidateScore   │
└─────────────────┘     └──────────────────┘     └───────────────────┘
        │                        │
        │                        ▼
        │               ┌──────────────────┐
        │               │   ExampleLeader  │
        │               └──────────────────┘
        │
        ▼
┌─────────────────┐
│    Candidate    │ (existing)
└─────────────────┘
```

---

## Domain Entities

### ParetoState

**Purpose**: Tracks evolution state with per-example score tracking for Pareto-aware candidate selection.

**Location**: `src/gepa_adk/domain/state.py` (new file)

| Field | Type | Description |
|-------|------|-------------|
| `candidates` | `list[Candidate]` | All candidates discovered during evolution |
| `candidate_scores` | `dict[int, dict[int, float]]` | Maps candidate_idx → {example_idx → score} |
| `frontier` | `ParetoFrontier` | Current Pareto frontier state |
| `frontier_type` | `FrontierType` | Strategy for frontier tracking |
| `iteration` | `int` | Current iteration number |
| `best_average_idx` | `int` | Index of candidate with highest average score |

**Validation Rules**:
- `candidates` must not be empty after initialization
- `candidate_scores` keys must be valid indices into `candidates`
- `frontier_type` must be a valid `FrontierType` enum value

**State Transitions**:
```
┌──────────┐    add_candidate()    ┌────────────────┐    update_frontier()    ┌────────────────┐
│  Empty   │ ─────────────────────▶│ Has Candidates │ ──────────────────────▶│ Frontier Ready │
└──────────┘                       └────────────────┘                        └────────────────┘
```

---

### ParetoFrontier

**Purpose**: Maintains the non-dominated candidate set, tracking which candidates lead on which examples.

**Location**: `src/gepa_adk/domain/state.py`

| Field | Type | Description |
|-------|------|-------------|
| `example_leaders` | `dict[int, set[int]]` | Maps example_idx → set of candidate indices that are best for that example |
| `best_scores` | `dict[int, float]` | Maps example_idx → best score achieved for that example |

**Validation Rules**:
- All candidate indices in `example_leaders` must be valid
- `best_scores` keys must match `example_leaders` keys

**Methods**:
| Method | Description |
|--------|-------------|
| `update(candidate_idx, scores)` | Update frontier with new candidate's per-example scores |
| `get_non_dominated()` | Return set of all candidate indices appearing in any example's leader set |
| `get_selection_weights()` | Return dict of candidate_idx → weight (frequency in leader sets) |

---

### CandidateScore (Value Object)

**Purpose**: Immutable record of a candidate's score on a specific example.

**Location**: `src/gepa_adk/domain/state.py`

| Field | Type | Description |
|-------|------|-------------|
| `candidate_idx` | `int` | Index of the candidate |
| `example_idx` | `int` | Index of the validation example |
| `score` | `float` | Score achieved (higher is better) |

**Validation Rules**:
- `score` must be a finite float (not NaN or infinity)

---

### FrontierType (Enum)

**Purpose**: Configures which dimensions are tracked for Pareto dominance.

**Location**: `src/gepa_adk/domain/types.py` (extend existing)

| Value | Description |
|-------|-------------|
| `INSTANCE` | Track best per validation example (default, initial scope) |
| `OBJECTIVE` | Track best per objective metric (deferred) |
| `HYBRID` | Both instance and objective (deferred) |
| `CARTESIAN` | Per (example, objective) pair (deferred) |

---

## Port Protocols

### CandidateSelectorProtocol

**Purpose**: Strategy interface for selecting which candidate to mutate next.

**Location**: `src/gepa_adk/ports/selector.py` (new file)

```python
@runtime_checkable
class CandidateSelectorProtocol(Protocol):
    """Async protocol for candidate selection strategies."""

    async def select_candidate(self, state: ParetoState) -> int:
        """Select a candidate index for mutation.

        Args:
            state: Current evolution state with frontier.

        Returns:
            Index of selected candidate.

        Raises:
            NoCandidateAvailableError: If state has no candidates.
        """
        ...
```

---

## Adapter Implementations

### ParetoCandidateSelector

**Purpose**: Samples from Pareto front with probability proportional to example leadership frequency.

**Location**: `src/gepa_adk/adapters/candidate_selector.py` (new file)

| Field | Type | Description |
|-------|------|-------------|
| `rng` | `random.Random` | Random number generator for reproducibility |

**Algorithm**:
1. Get non-dominated candidates from frontier
2. Calculate selection weights (frequency in leader sets)
3. Sample candidate proportional to weights

---

### CurrentBestCandidateSelector

**Purpose**: Always returns the candidate with highest average score (greedy baseline).

**Location**: `src/gepa_adk/adapters/candidate_selector.py`

| Field | Type | Description |
|-------|------|-------------|
| (none) | - | Stateless selector |

**Algorithm**:
1. Return `state.best_average_idx`

---

### EpsilonGreedyCandidateSelector

**Purpose**: Explores random candidates with probability ε, otherwise selects best.

**Location**: `src/gepa_adk/adapters/candidate_selector.py`

| Field | Type | Description |
|-------|------|-------------|
| `epsilon` | `float` | Exploration probability (0.0 to 1.0) |
| `rng` | `random.Random` | Random number generator |

**Algorithm**:
1. With probability ε: return random candidate index
2. Otherwise: return `state.best_average_idx`

---

## Relationships

```
Candidate 1:N CandidateScore     (one candidate has many per-example scores)
ParetoState 1:1 ParetoFrontier   (state owns one frontier)
ParetoFrontier N:M Candidate     (frontier tracks multiple candidates per example)
```

---

## Integration with Existing Models

### EvaluationBatch (existing, no changes)
Already contains `scores: list[Score]` for per-example scores. Index in list serves as example ID.

### AsyncGEPAEngine (modified)
- Add optional `candidate_selector: CandidateSelectorProtocol` parameter
- Replace `_EngineState` usage with `ParetoState` when selector provided
- Await selector in `_propose_mutation()` to choose parent

### EvolutionConfig (modified)
- Add optional `frontier_type: FrontierType = FrontierType.INSTANCE`
- Add optional `candidate_selector_type: str = "current_best"`

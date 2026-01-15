# Data Model: Frontier Types and Valset Evaluation Policies

**Feature**: 027-frontier-eval-policy
**Date**: 2026-01-15

## Entity Overview

```
┌─────────────────────┐     ┌──────────────────────┐
│   ParetoState       │────▶│    ParetoFrontier    │
│   (modified)        │     │    (extended)        │
└─────────────────────┘     └──────────────────────┘
         │                           │
         │                           ├──▶ Example Leaders (instance)
         │                           ├──▶ Objective Leaders (objective)
         │                           └──▶ Cartesian Leaders (cartesian)
         │
         ▼
┌─────────────────────┐
│  AsyncGEPAEngine    │
│  (modified)         │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐     ┌──────────────────────┐
│EvaluationPolicyProto│────▶│  FullEvaluationPolicy│
│  (new port)         │     │  SubsetEvalPolicy    │
└─────────────────────┘     └──────────────────────┘
```

---

## Domain Layer Modifications

### ParetoFrontier (Extended)

**Purpose**: Tracks non-dominated candidates across multiple frontier dimensions (instance, objective, cartesian).

**Location**: `src/gepa_adk/domain/state.py`

| Field | Type | Description |
|-------|------|-------------|
| `example_leaders` | `dict[int, set[int]]` | Instance-level: example_idx → leader candidate indices |
| `best_scores` | `dict[int, float]` | Instance-level: example_idx → best score |
| `objective_leaders` | `dict[str, set[int]]` | Objective-level: objective_name → leader candidate indices |
| `objective_best_scores` | `dict[str, float]` | Objective-level: objective_name → best score |
| `cartesian_leaders` | `dict[tuple[int, str], set[int]]` | Cartesian: (example_idx, objective) → leader candidate indices |
| `cartesian_best_scores` | `dict[tuple[int, str], float]` | Cartesian: (example_idx, objective) → best score |

**New Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `update_objective` | `(candidate_idx: int, objective_scores: dict[str, float], *, logger: FrontierLogger \| None = None) -> None` | Update objective-level frontier |
| `update_cartesian` | `(candidate_idx: int, scores: dict[int, float], objective_scores: dict[int, dict[str, float]], *, logger: FrontierLogger \| None = None) -> None` | Update cartesian frontier |
| `get_pareto_front_mapping` | `(frontier_type: FrontierType) -> dict[FrontierKey, set[int]]` | Return frontier mapping for specified type |

**Validation Rules**:
- All candidate indices must be non-negative
- Objective names must be non-empty strings
- Scores must be finite floats

---

### ParetoState (Modified)

**Purpose**: Tracks evolution state with multi-dimensional frontier support.

**Location**: `src/gepa_adk/domain/state.py`

**Modified Fields**:

| Field | Type | Change |
|-------|------|--------|
| `frontier_type` | `FrontierType` | Remove INSTANCE-only restriction |
| `candidate_objective_scores` | `dict[int, dict[str, float]]` | NEW: Per-candidate aggregated objective scores |

**Modified Methods**:

| Method | Change |
|--------|--------|
| `__post_init__` | Remove ConfigurationError for non-INSTANCE types |
| `add_candidate` | Accept optional `objective_scores` parameter; update appropriate frontier based on `frontier_type` |

**Validation Rules**:
- When `frontier_type` in (OBJECTIVE, HYBRID, CARTESIAN): `objective_scores` must be provided
- Raise `ConfigurationError` if objective scores missing for objective-based frontier types

---

### FrontierKey (Type Alias)

**Purpose**: Union type for frontier mapping keys across all frontier types.

**Location**: `src/gepa_adk/domain/types.py`

```python
FrontierKey: TypeAlias = int | str | tuple[str, int] | tuple[str, int, str]
"""Key type for frontier mappings:
- int: example_idx for INSTANCE
- str: objective_name for OBJECTIVE
- tuple[str, int]: ("val_id", example_idx) or ("objective", objective_name) for HYBRID
- tuple[str, int, str]: ("cartesian", example_idx, objective_name) for CARTESIAN
"""
```

---

## Port Layer Additions

### EvaluationPolicyProtocol

**Purpose**: Strategy interface for selecting which validation examples to evaluate.

**Location**: `src/gepa_adk/ports/selector.py`

```python
@runtime_checkable
class EvaluationPolicyProtocol(Protocol):
    """Protocol for valset evaluation strategies.

    Determines which validation examples to evaluate per iteration
    and how to identify the best candidate.
    """

    def get_eval_batch(
        self,
        valset_ids: Sequence[int],
        state: ParetoState,
        target_candidate_idx: int | None = None,
    ) -> list[int]:
        """Select validation example indices to evaluate.

        Args:
            valset_ids: All available validation example indices.
            state: Current evolution state.
            target_candidate_idx: Optional candidate being evaluated.

        Returns:
            List of example indices to evaluate this iteration.
        """
        ...

    def get_best_candidate(self, state: ParetoState) -> int:
        """Return index of best candidate based on evaluation results.

        Args:
            state: Current evolution state with scores.

        Returns:
            Index of best performing candidate.

        Raises:
            NoCandidateAvailableError: If no candidates exist.
        """
        ...

    def get_valset_score(self, candidate_idx: int, state: ParetoState) -> float:
        """Return aggregated valset score for a candidate.

        Args:
            candidate_idx: Candidate to score.
            state: Current evolution state.

        Returns:
            Aggregated score (typically average across evaluated examples).
        """
        ...
```

---

## Adapter Layer Additions

### FullEvaluationPolicy

**Purpose**: Evaluates all validation examples every iteration.

**Location**: `src/gepa_adk/adapters/evaluation_policy.py`

| Field | Type | Description |
|-------|------|-------------|
| (none) | - | Stateless policy |

**Methods**:

| Method | Implementation |
|--------|----------------|
| `get_eval_batch` | Return all `valset_ids` |
| `get_best_candidate` | Return index with highest average score |
| `get_valset_score` | Return mean of candidate's evaluated scores |

---

### SubsetEvaluationPolicy

**Purpose**: Evaluates a configurable subset of validation examples with round-robin coverage.

**Location**: `src/gepa_adk/adapters/evaluation_policy.py`

| Field | Type | Description |
|-------|------|-------------|
| `subset_size` | `int \| float` | If int: absolute count. If float (0.0-1.0): fraction of valset. |
| `_offset` | `int` | Internal: current position for round-robin |

**Methods**:

| Method | Implementation |
|--------|----------------|
| `get_eval_batch` | Return slice of `valset_ids` starting at `_offset`, wrapping around |
| `get_best_candidate` | Return index with highest average across evaluated examples |
| `get_valset_score` | Return mean of candidate's evaluated scores |

**Constructor**:
```python
def __init__(self, subset_size: int | float = 0.2):
    """
    Args:
        subset_size: If int, evaluate this many examples per iteration.
                     If float, evaluate this fraction of total valset.
                     Default: 0.2 (20% of valset per iteration).
    """
```

---

## Engine Modifications

### AsyncGEPAEngine

**Modified Constructor Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `evaluation_policy` | `EvaluationPolicyProtocol \| None` | `None` | Policy for selecting validation examples |

**Modified Methods**:

| Method | Change |
|--------|--------|
| `__init__` | Accept `evaluation_policy`, default to `FullEvaluationPolicy()` |
| `_evaluate_scoring` | Call `evaluation_policy.get_eval_batch()` to determine which examples to evaluate |

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CONFIGURATION                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ frontier_type: FrontierType = INSTANCE                                   │ │
│  │ evaluation_policy: EvaluationPolicyProtocol = FullEvaluationPolicy()    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EVALUATION FLOW                                      │
│  ┌────────────────────┐    ┌───────────────────┐    ┌────────────────────┐  │
│  │ evaluation_policy  │───▶│ get_eval_batch()  │───▶│ Selected IDs       │  │
│  │ .get_eval_batch()  │    │ valset_ids, state │    │ [0, 5, 10, ...]    │  │
│  └────────────────────┘    └───────────────────┘    └────────────────────┘  │
│                                                              │               │
│                                                              ▼               │
│                                                     ┌────────────────────┐  │
│                                                     │ adapter.evaluate() │  │
│                                                     │ (selected subset)  │  │
│                                                     └────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTIER UPDATE                                       │
│  ┌────────────────────┐                                                      │
│  │ ParetoState        │                                                      │
│  │ .add_candidate()   │                                                      │
│  └────────────────────┘                                                      │
│           │                                                                   │
│           ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ frontier_type determines which frontiers are updated:                   │ │
│  │                                                                          │ │
│  │ INSTANCE:  frontier.update(candidate_idx, scores)                       │ │
│  │ OBJECTIVE: frontier.update_objective(candidate_idx, objective_scores)   │ │
│  │ HYBRID:    Both of above                                                │ │
│  │ CARTESIAN: frontier.update_cartesian(candidate_idx, scores, obj_scores)│ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CANDIDATE SELECTION                                   │
│  ┌────────────────────┐    ┌───────────────────────────────────────────┐    │
│  │ CandidateSelector  │───▶│ state.frontier.get_pareto_front_mapping() │    │
│  │ .select_candidate()│    │ Returns mapping based on frontier_type    │    │
│  └────────────────────┘    └───────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Backward Compatibility

All additions maintain backward compatibility:

| Component | Default Behavior | Existing Code Impact |
|-----------|-----------------|---------------------|
| `ParetoState.frontier_type` | `FrontierType.INSTANCE` | No change required |
| `evaluation_policy` | `FullEvaluationPolicy()` | No change required |
| `objective_scores` | `None` (optional) | Only required for objective-based frontier types |
| New frontier fields | Empty dicts | No impact when frontier_type=INSTANCE |

---

## Validation Matrix

| frontier_type | objective_scores Required | Frontier Updated |
|---------------|--------------------------|------------------|
| INSTANCE | No | example_leaders, best_scores |
| OBJECTIVE | Yes | objective_leaders, objective_best_scores |
| HYBRID | Yes | All instance + objective fields |
| CARTESIAN | Yes | cartesian_leaders, cartesian_best_scores |

# Data Model: Objective Scores Passthrough

**Feature**: 026-objective-scores
**Date**: 2026-01-15

## Entity Overview

This feature adds optional `objective_scores` fields to existing domain models to enable multi-objective metric passthrough from adapter evaluations.

## Type Definitions

### ObjectiveScoresType (type alias)

```
list[dict[str, float]] | None
```

**Description**: Per-example mapping of objective metric names to their numeric scores.

**Structure**:
- Outer list: One entry per evaluated example (index-aligned with EvaluationBatch.scores)
- Inner dict: Maps objective name (str) to score value (float)
- None: When adapter does not provide objective scores

**Example**:
```python
# For 3 evaluated examples with 2 objectives each:
[
    {"accuracy": 0.95, "latency": 0.8},   # Example 0
    {"accuracy": 0.88, "latency": 0.92},  # Example 1
    {"accuracy": 0.91, "latency": 0.85},  # Example 2
]
```

## Modified Entities

### IterationRecord

**Current State** (domain/models.py:144-183):
```
Fields:
- iteration_number: int (required)
- score: float (required)
- instruction: str (required)
- accepted: bool (required)
```

**Proposed Addition**:
```
- objective_scores: list[dict[str, float]] | None = None (optional)
```

**Rationale**: Captures per-example objective breakdown for the iteration, enabling historical multi-objective analysis.

**Validation**: None (passthrough - adapter provides validated data)

**Relationships**:
- Created by: AsyncGEPAEngine._record_iteration()
- Stored in: EvolutionResult.iteration_history

---

### EvolutionResult

**Current State** (domain/models.py:185-257):
```
Fields:
- original_score: float (required)
- final_score: float (required)
- evolved_instruction: str (required)
- iteration_history: list[IterationRecord] (required)
- total_iterations: int (required)
- valset_score: float | None = None (optional)
- trainset_score: float | None = None (optional)
```

**Proposed Addition**:
```
- objective_scores: list[dict[str, float]] | None = None (optional)
```

**Rationale**: Exposes the best candidate's objective scores for final result analysis without requiring iteration history traversal.

**Validation**: None (passthrough from engine state)

**Relationships**:
- Created by: AsyncGEPAEngine._build_result()
- Sources: _EngineState.best_objective_scores

---

### _EngineState (internal)

**Current State** (engine/async_engine.py:41-82):
```
Fields:
- best_candidate: Candidate (required)
- best_score: float (required)
- original_score: float (required)
- iteration: int = 0
- stagnation_counter: int = 0
- iteration_history: list[IterationRecord] = []
- last_eval_batch: EvaluationBatch | None = None
- best_reflection_score: float = 0.0
- best_valset_mean: float | None = None
```

**Proposed Addition**:
```
- best_objective_scores: list[dict[str, float]] | None = None
```

**Rationale**: Tracks the objective scores from the current best candidate's evaluation for result building.

**Validation**: None (passthrough)

**Relationships**:
- Updated by: AsyncGEPAEngine._accept_proposal(), _initialize_baseline()
- Used by: AsyncGEPAEngine._build_result(), _record_iteration()

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ADAPTER LAYER                                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ EvaluationBatch                                                 │ │
│  │   objective_scores: list[dict[str, float]] | None              │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ENGINE LAYER                                  │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ _EngineState (internal)                                         │ │
│  │   best_objective_scores: list[dict[str, float]] | None         │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                  │                                   │
│           ┌──────────────────────┴──────────────────────┐           │
│           ▼                                              ▼           │
│  ┌─────────────────────┐                    ┌─────────────────────┐ │
│  │ _record_iteration() │                    │ _build_result()     │ │
│  └─────────────────────┘                    └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                │                                          │
                ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DOMAIN LAYER                                  │
│  ┌────────────────────────────┐    ┌────────────────────────────┐  │
│  │ IterationRecord            │    │ EvolutionResult            │  │
│  │   objective_scores: ...    │    │   objective_scores: ...    │  │
│  └────────────────────────────┘    └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Backward Compatibility

All additions are optional with `None` defaults:

| Entity | New Field | Default | Existing Code Impact |
|--------|-----------|---------|---------------------|
| IterationRecord | objective_scores | None | No change required |
| EvolutionResult | objective_scores | None | No change required |
| _EngineState | best_objective_scores | None | Internal only |

**Test**: Existing tests should pass without modification as they don't provide objective_scores.

## Migration

No migration required. New fields are optional additions that:
1. Default to `None` when not provided
2. Do not affect serialization (dataclasses handle optional fields)
3. Do not break existing API contracts

# Data Model: AsyncGEPAAdapter Protocol

**Feature**: 004-async-gepa-adapter
**Date**: 2026-01-10
**Source**: [spec.md](spec.md), [research.md](research.md)

## Entity Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                     AsyncGEPAAdapter Protocol                        │
│  (ports/adapter.py)                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Generic Parameters:                                                 │
│    - DataInst: Input data type                                       │
│    - Trajectory: Execution trace type                                │
│    - RolloutOutput: Evaluation result type                           │
├─────────────────────────────────────────────────────────────────────┤
│  async evaluate(batch, candidate, capture_traces)                    │
│      → EvaluationBatch[Trajectory, RolloutOutput]                    │
│                                                                      │
│  async make_reflective_dataset(candidate, eval_batch, components)    │
│      → Mapping[str, Sequence[Mapping[str, Any]]]                     │
│                                                                      │
│  async propose_new_texts(candidate, dataset, components)             │
│      → dict[str, str]                                                │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ returns
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EvaluationBatch Dataclass                       │
│  (ports/adapter.py)                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Generic Parameters:                                                 │
│    - Trajectory                                                      │
│    - RolloutOutput                                                   │
├─────────────────────────────────────────────────────────────────────┤
│  outputs: list[RolloutOutput]       # Per-example raw outputs       │
│  scores: list[float]                # Per-example numeric scores    │
│  trajectories: list[Trajectory]|None # Optional execution traces    │
│  objective_scores: list[dict]|None  # Optional multi-objective      │
└─────────────────────────────────────────────────────────────────────┘
```

## Entity Definitions

### EvaluationBatch

**Purpose**: Container for batch evaluation results returned by `evaluate()`.

**Location**: `src/gepa_adk/ports/adapter.py`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `outputs` | `list[RolloutOutput]` | Yes | Raw per-example outputs (opaque to engine) |
| `scores` | `list[float]` | Yes | Per-example scores, higher is better |
| `trajectories` | `list[Trajectory] \| None` | No | Per-example traces when `capture_traces=True` |
| `objective_scores` | `list[dict[str, float]] \| None` | No | Multi-objective scores per example |

**Invariants**:
- `len(outputs) == len(scores)` (always)
- If `trajectories` is not None: `len(trajectories) == len(scores)`
- If `objective_scores` is not None: `len(objective_scores) == len(scores)`

**Dataclass Configuration**:
```python
@dataclass(slots=True, frozen=True)
class EvaluationBatch(Generic[Trajectory, RolloutOutput]):
    ...
```

### AsyncGEPAAdapter Protocol

**Purpose**: Defines the contract for async GEPA adapters.

**Location**: `src/gepa_adk/ports/adapter.py`

**Generic Parameters**:
| Parameter | Description | Example |
|-----------|-------------|---------|
| `DataInst` | Type of input data instances | `dict[str, str]`, custom dataclass |
| `Trajectory` | Type of execution trace data | `list[Message]`, custom trace type |
| `RolloutOutput` | Type of evaluation output | `str`, custom result type |

**Methods**:

#### `evaluate`

```python
async def evaluate(
    self,
    batch: list[DataInst],
    candidate: dict[str, str],
    capture_traces: bool = False,
) -> EvaluationBatch[Trajectory, RolloutOutput]
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `batch` | `list[DataInst]` | Input data instances to evaluate |
| `candidate` | `dict[str, str]` | Component name → text mapping (from `Candidate.components`) |
| `capture_traces` | `bool` | Whether to capture execution traces |
| **Returns** | `EvaluationBatch` | Evaluation results with scores and optional traces |

#### `make_reflective_dataset`

```python
async def make_reflective_dataset(
    self,
    candidate: dict[str, str],
    eval_batch: EvaluationBatch[Trajectory, RolloutOutput],
    components_to_update: list[str],
) -> Mapping[str, Sequence[Mapping[str, Any]]]
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `candidate` | `dict[str, str]` | Current candidate components |
| `eval_batch` | `EvaluationBatch` | Results from `evaluate()` with traces |
| `components_to_update` | `list[str]` | Component names to generate datasets for |
| **Returns** | `Mapping[...]` | Component name → list of reflective examples |

**Reflective Dataset Schema** (recommended):
```python
{
    "component_name": [
        {
            "Inputs": {"key": "value"},       # Minimal input view
            "Generated Outputs": "...",       # Model outputs
            "Feedback": "..."                 # Performance feedback
        },
        # ... more examples
    ]
}
```

#### `propose_new_texts`

```python
async def propose_new_texts(
    self,
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components_to_update: list[str],
) -> dict[str, str]
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `candidate` | `dict[str, str]` | Current candidate components |
| `reflective_dataset` | `Mapping[...]` | Dataset from `make_reflective_dataset()` |
| `components_to_update` | `list[str]` | Component names to propose updates for |
| **Returns** | `dict[str, str]` | Component name → new proposed text |

## Type Aliases

Defined in `src/gepa_adk/ports/adapter.py`:

```python
from typing import TypeVar

DataInst = TypeVar("DataInst")
Trajectory = TypeVar("Trajectory")
RolloutOutput = TypeVar("RolloutOutput")
```

## Relationship to Domain Models

| Domain Model | Relationship | Usage |
|--------------|--------------|-------|
| `Candidate` | Consumed via `.components` | `candidate.components` passed to adapter methods |
| `EvolutionConfig` | Configuration | Adapters may reference config for settings |
| `Score` (type alias) | Semantic typing | Scores in `EvaluationBatch` are `Score` (float) |
| `ComponentName` | Semantic typing | Keys in candidate dict are `ComponentName` |

## Validation Rules

### EvaluationBatch

1. **Length Consistency**: All lists must have same length
2. **Score Validity**: Scores should be comparable floats (no NaN in normal operation)
3. **Trajectory Presence**: If `capture_traces=True` was passed, `trajectories` must not be None

### Protocol Implementation

1. **Method Presence**: All three async methods must be implemented
2. **Async Signature**: Methods must be coroutines (`async def`)
3. **Type Compatibility**: Static type checkers validate signatures

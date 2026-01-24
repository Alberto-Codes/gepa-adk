# Data Model: AsyncGEPAEngine

**Feature**: 006-async-gepa-engine
**Date**: 2026-01-10

## Overview

This document defines the data structures and relationships for the AsyncGEPAEngine feature. Most domain models already exist from PR #22; this feature adds the engine class and internal state.

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AsyncGEPAEngine                               │
│  (Orchestrator - holds references, manages state)                   │
├─────────────────────────────────────────────────────────────────────┤
│  adapter: AsyncGEPAAdapter    ←──────┐                              │
│  config: EvolutionConfig             │                              │
│  _batch: list[DataInst]              │   Protocol (injected)        │
│  _state: _EngineState        ←───────┼──────────────────────────┐   │
└─────────────────────────────────────────────────────────────────┼───┘
                                       │                          │
         ┌─────────────────────────────┘                          │
         │                                                         │
         ▼                                                         ▼
┌─────────────────────────┐                    ┌─────────────────────────┐
│   AsyncGEPAAdapter      │                    │     _EngineState        │
│   (Protocol - ports/)   │                    │   (Internal, mutable)   │
├─────────────────────────┤                    ├─────────────────────────┤
│ evaluate()              │                    │ iteration: int          │
│ make_reflective_dataset()│                   │ best_candidate: Candidate│
│ propose_new_texts()     │                    │ best_score: float       │
└─────────────────────────┘                    │ stagnation_counter: int │
         │                                     │ iteration_history: list │
         │                                     │ original_score: float   │
         ▼                                     └─────────────────────────┘
┌─────────────────────────┐                              │
│   EvaluationBatch       │                              │
│   (Frozen result)       │                              ▼
├─────────────────────────┤                    ┌─────────────────────────┐
│ outputs: list           │                    │     EvolutionResult     │
│ scores: list[Score]     │                    │   (Frozen, returned)    │
│ trajectories: list|None │                    ├─────────────────────────┤
│ objective_scores: ...   │                    │ original_score: float   │
└─────────────────────────┘                    │ final_score: float      │
                                               │ evolved_instruction: str│
                                               │ iteration_history: list │
                                               │ total_iterations: int   │
                                               └─────────────────────────┘
                                                         │
                                                         │ contains
                                                         ▼
                                               ┌─────────────────────────┐
                                               │    IterationRecord      │
                                               │   (Frozen, per-iter)    │
                                               ├─────────────────────────┤
                                               │ iteration_number: int   │
                                               │ score: float            │
                                               │ instruction: str        │
                                               │ accepted: bool          │
                                               └─────────────────────────┘
```

## Entities

### AsyncGEPAEngine (NEW)

**Location**: `src/gepa_adk/engine/async_engine.py`
**Purpose**: Orchestrates the evolution loop, coordinates adapter calls

| Field | Type | Description |
|-------|------|-------------|
| `adapter` | `AsyncGEPAAdapter` | Injected adapter for evaluation and proposals |
| `config` | `EvolutionConfig` | Evolution parameters |
| `_initial_candidate` | `Candidate` | Starting candidate for evolution |
| `_batch` | `list[DataInst]` | Evaluation data instances |
| `_state` | `_EngineState` | Internal mutable state |

**Methods**:
| Method | Signature | Description |
|--------|-----------|-------------|
| `run` | `async def run(self) -> EvolutionResult` | Execute evolution loop |

**Lifecycle**:
1. Constructed with adapter, config, initial candidate, batch
2. `run()` called to execute evolution
3. Returns frozen `EvolutionResult`
4. Instance can be discarded (no cleanup needed)

---

### _EngineState (NEW - Internal)

**Location**: `src/gepa_adk/engine/async_engine.py` (private class)
**Purpose**: Mutable state during evolution run

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `iteration` | `int` | `0` | Current iteration number (1-indexed in records) |
| `best_candidate` | `Candidate` | — | Best candidate found so far |
| `best_score` | `float` | — | Score of best candidate |
| `stagnation_counter` | `int` | `0` | Iterations since last improvement |
| `iteration_history` | `list[IterationRecord]` | `[]` | All iteration records |
| `original_score` | `float` | — | Baseline score (first evaluation) |

**Notes**:
- Not exposed publicly
- Created fresh for each `run()` call
- Converted to `EvolutionResult` at end of run

---

### EvolutionConfig (EXISTING)

**Location**: `src/gepa_adk/domain/models.py`
**Purpose**: Configuration parameters for evolution

| Field | Type | Default | Used By Engine |
|-------|------|---------|----------------|
| `max_iterations` | `int` | `50` | Stopping condition |
| `max_concurrent_evals` | `int` | `5` | Future: semaphore limit |
| `min_improvement_threshold` | `float` | `0.01` | Acceptance logic |
| `patience` | `int` | `5` | Early stopping |
| `reflection_model` | `str` | `"gemini-2.5-flash"` | Passed to adapter (not used by engine directly) |

---

### EvolutionResult (EXISTING)

**Location**: `src/gepa_adk/domain/models.py`
**Purpose**: Frozen outcome of evolution run

| Field | Type | Description |
|-------|------|-------------|
| `original_score` | `float` | Starting score (baseline) |
| `final_score` | `float` | Best score achieved |
| `evolved_instruction` | `str` | Best instruction text |
| `iteration_history` | `list[IterationRecord]` | Complete iteration log |
| `total_iterations` | `int` | Number of iterations run |

**Computed Properties**:
- `improvement` → `final_score - original_score`
- `improved` → `final_score > original_score`

---

### IterationRecord (EXISTING)

**Location**: `src/gepa_adk/domain/models.py`
**Purpose**: Immutable record of single iteration

| Field | Type | Description |
|-------|------|-------------|
| `iteration_number` | `int` | 1-indexed iteration number |
| `score` | `float` | Score achieved in this iteration |
| `instruction` | `str` | Instruction evaluated |
| `accepted` | `bool` | Whether proposal was accepted |

---

### Candidate (EXISTING)

**Location**: `src/gepa_adk/domain/models.py`
**Purpose**: Mutable instruction candidate

| Field | Type | Default | Engine Usage |
|-------|------|---------|--------------|
| `components` | `dict[str, str]` | `{}` | Holds instruction text |
| `generation` | `int` | `0` | Updated on acceptance |
| `parent_id` | `str | None` | `None` | Updated on acceptance |
| `metadata` | `dict[str, Any]` | `{}` | Future: tracking info |

**Key Component**:
- `components["instruction"]` - main prompt text for v1

---

### AsyncGEPAAdapter (EXISTING - Protocol)

**Location**: `src/gepa_adk/ports/adapter.py`
**Purpose**: Protocol for adapter implementations

| Method | Async | Purpose |
|--------|-------|---------|
| `evaluate` | ✅ | Score candidate on batch |
| `make_reflective_dataset` | ✅ | Build reflection data from traces |
| `propose_new_texts` | ✅ | Generate mutation proposals |

---

### EvaluationBatch (EXISTING)

**Location**: `src/gepa_adk/ports/adapter.py`
**Purpose**: Container for evaluation results

| Field | Type | Description |
|-------|------|-------------|
| `outputs` | `list[RolloutOutput]` | Per-example outputs |
| `scores` | `list[Score]` | Per-example scores |
| `trajectories` | `list | None` | Execution traces |
| `objective_scores` | `list | None` | Multi-objective (v2) |

## State Transitions

### Evolution Run State Machine

```
                         ┌──────────────┐
                         │  INITIALIZED │
                         │  (run called)│
                         └──────┬───────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   BASELINE EVALUATION │
                    │ (evaluate initial)    │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
         ┌─────────│      ITERATING        │◀────────┐
         │         │  (while not stopped)  │         │
         │         └───────────┬───────────┘         │
         │                     │                     │
         │  ┌──────────────────┼──────────────────┐  │
         │  │                  ▼                  │  │
         │  │    ┌─────────────────────────┐      │  │
         │  │    │   EVALUATE PROPOSAL     │      │  │
         │  │    └───────────┬─────────────┘      │  │
         │  │                │                    │  │
         │  │    ┌───────────┴───────────┐        │  │
         │  │    ▼                       ▼        │  │
         │  │ ┌────────┐           ┌──────────┐   │  │
         │  │ │ACCEPTED│           │ REJECTED │   │  │
         │  │ │(update │           │(increment│   │  │
         │  │ │ best)  │           │stagnation)   │  │
         │  │ └────┬───┘           └─────┬────┘   │  │
         │  │      │                     │        │  │
         │  │      └──────────┬──────────┘        │  │
         │  │                 │                   │  │
         │  │                 ▼                   │  │
         │  │    ┌─────────────────────────┐      │  │
         │  │    │    RECORD ITERATION     │      │  │
         │  │    └───────────┬─────────────┘      │  │
         │  │                │                    │  │
         │  └────────────────┼────────────────────┘  │
         │                   │                       │
         │                   └───────────────────────┘
         │
         │  (max_iterations OR patience exhausted)
         │
         ▼
┌───────────────────────┐
│      COMPLETED        │
│ (return EvolutionResult)
└───────────────────────┘
```

## Validation Rules

### Constructor Validation

| Validation | Error Type | Condition |
|------------|------------|-----------|
| Config valid | `ConfigurationError` | Handled by `EvolutionConfig.__post_init__` |
| Batch non-empty | `ValueError` | `len(batch) == 0` |
| Candidate has instruction | `ValueError` | `"instruction" not in candidate.components` |

### Runtime Invariants

| Invariant | Enforcement |
|-----------|-------------|
| `iteration >= 0` | Counter starts at 0, increments only |
| `best_score >= 0` | Scores from adapter (assumed normalized) |
| `stagnation_counter <= patience` | Reset on acceptance, checked in `_should_stop` |
| `len(iteration_history) == iteration` | Record created each iteration |

## Type Aliases (Reference)

From `src/gepa_adk/domain/types.py`:

| Alias | Type | Usage |
|-------|------|-------|
| `Score` | `float` | Normalized scores [0.0, 1.0] |
| `ComponentName` | `str` | e.g., "instruction" |
| `ModelName` | `str` | e.g., "gemini-2.5-flash" |

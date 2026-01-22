# Data Model: Wire stop_callbacks into AsyncGEPAEngine

**Feature**: 196-stopper-engine-integration
**Date**: 2026-01-22

## Overview

This feature does not introduce new domain entities. It integrates existing entities (StopperState, StopperProtocol) into AsyncGEPAEngine by adding internal state tracking.

## Existing Entities (No Changes)

### 1. StopperState

**Location**: `src/gepa_adk/domain/stopper.py`
**Type**: Frozen dataclass (immutable)

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | `int` | Current iteration number (0-indexed) |
| `best_score` | `float` | Best score achieved so far |
| `stagnation_counter` | `int` | Iterations without improvement |
| `total_evaluations` | `int` | Count of all evaluate() calls |
| `candidates_count` | `int` | Number of candidates in Pareto frontier |
| `elapsed_seconds` | `float` | Wall-clock time since evolution started |

**Invariants**:
- Immutable (frozen dataclass)
- All fields required at construction
- `iteration >= 0`
- `total_evaluations >= 0`
- `elapsed_seconds >= 0.0`

### 2. StopperProtocol

**Location**: `src/gepa_adk/ports/stopper.py`
**Type**: Runtime-checkable Protocol

```python
@runtime_checkable
class StopperProtocol(Protocol):
    def __call__(self, state: StopperState) -> bool:
        """Return True to signal evolution should stop."""
        ...
```

**Structural Subtyping**: Any callable with signature `(StopperState) -> bool` satisfies this protocol.

### 3. EvolutionConfig.stop_callbacks

**Location**: `src/gepa_adk/domain/models.py`
**Type**: `list[StopperProtocol]`
**Default**: `field(default_factory=list)` (empty list)

**Validation**: None (accepts any list of callables)

## New Internal State (Engine Attributes)

The following attributes are added to `AsyncGEPAEngine` to support StopperState construction:

### 1. _start_time

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `_start_time` | `float \| None` | `None` | Monotonic timestamp set at start of `run()` |

**Lifecycle**:
- Set to `time.monotonic()` at start of `run()` method
- Used to compute `elapsed_seconds` for StopperState
- Reset to `None` on engine reset (if applicable)

### 2. _total_evaluations

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `_total_evaluations` | `int` | `0` | Cumulative count of evaluations |

**Lifecycle**:
- Initialized to `0` in constructor
- Incremented by batch size after each `adapter.evaluate()` call
- Reset to `0` on engine reset (if applicable)

## State Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                     AsyncGEPAEngine                         │
├─────────────────────────────────────────────────────────────┤
│  _start_time: float | None                                  │
│  _total_evaluations: int                                    │
│  _state: _EngineState                                       │
│  _pareto_state: ParetoState | None                          │
│  config: EvolutionConfig ────────────┐                      │
└──────────────────────────────────────┼──────────────────────┘
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │   EvolutionConfig      │
                          ├────────────────────────┤
                          │ stop_callbacks: list   │──────┐
                          │ max_iterations: int    │      │
                          │ patience: int          │      │
                          └────────────────────────┘      │
                                                          │
                    ┌─────────────────────────────────────┘
                    │
                    ▼
          ┌──────────────────┐        ┌──────────────────┐
          │ StopperProtocol  │◄───────│   StopperState   │
          ├──────────────────┤        ├──────────────────┤
          │ __call__(state)  │        │ iteration        │
          │   -> bool        │        │ best_score       │
          └──────────────────┘        │ stagnation_count │
                    ▲                 │ total_evaluations│
                    │                 │ candidates_count │
                    │                 │ elapsed_seconds  │
        ┌───────────┼───────────┐     └──────────────────┘
        │           │           │
┌───────┴───┐ ┌─────┴─────┐ ┌───┴──────────┐
│ Timeout   │ │ Threshold │ │ Signal       │
│ Stopper   │ │ Stopper   │ │ Stopper      │
└───────────┘ └───────────┘ └──────────────┘
```

## StopperState Construction

The engine builds StopperState snapshots using this mapping:

| StopperState Field | Source |
|--------------------|--------|
| `iteration` | `self._state.iteration` |
| `best_score` | `self._state.best_score` |
| `stagnation_counter` | `self._state.stagnation_counter` |
| `total_evaluations` | `self._total_evaluations` |
| `candidates_count` | `len(self._pareto_state.candidates) if self._pareto_state else 0` |
| `elapsed_seconds` | `time.monotonic() - self._start_time` |

## Validation Rules

### At Runtime

1. **stop_callbacks type**: Each item must be callable with `(StopperState) -> bool` signature
2. **StopperState construction**: All fields must be computable at time of snapshot

### Error Handling

1. **Stopper raises exception**: Log error, continue evolution (graceful degradation)
2. **StopperState construction fails**: Should not happen if engine state is consistent (assert)

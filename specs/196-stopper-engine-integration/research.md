# Research: Wire stop_callbacks into AsyncGEPAEngine

**Feature**: 196-stopper-engine-integration
**Date**: 2026-01-22

## Overview

This research documents the findings from codebase exploration to understand how to integrate stop_callbacks into AsyncGEPAEngine.

## 1. Existing Stopper Infrastructure

### 1.1 StopperState (Domain Layer)

**Location**: `src/gepa_adk/domain/stopper.py`

**Decision**: Use existing StopperState dataclass unchanged.

**Rationale**: StopperState is already a well-designed immutable frozen dataclass with all required fields:
- `iteration: int` - Current iteration number (0-indexed)
- `best_score: float` - Best score achieved so far
- `stagnation_counter: int` - Iterations without improvement
- `total_evaluations: int` - Count of all evaluate() calls
- `candidates_count: int` - Number of candidates in frontier
- `elapsed_seconds: float` - Wall-clock time since evolution started

**Alternatives Considered**:
- Creating a new state class specific to engine → Rejected: Would duplicate domain model and violate DRY principle.

### 1.2 StopperProtocol (Ports Layer)

**Location**: `src/gepa_adk/ports/stopper.py`

**Decision**: Use existing StopperProtocol unchanged.

**Rationale**: Protocol is runtime-checkable and requires only `__call__(self, state: StopperState) -> bool`. Structural typing allows any callable with correct signature.

**Alternatives Considered**:
- Adding lifecycle methods to protocol → Rejected: SignalStopper's setup/cleanup are implementation details, not protocol requirements.

### 1.3 Stopper Implementations (Adapters Layer)

**Location**: `src/gepa_adk/adapters/stoppers/`

All implementations are complete and tested:
- **TimeoutStopper**: Checks `state.elapsed_seconds >= timeout_seconds`
- **ScoreThresholdStopper**: Checks `state.best_score >= threshold`
- **SignalStopper**: Returns `self._stop_requested` flag, has `setup()` and `cleanup()` methods
- **CompositeStopper**: Combines multiple stoppers with "any" or "all" logic

**Decision**: No changes needed to adapter implementations.

## 2. AsyncGEPAEngine Analysis

### 2.1 Current _EngineState

**Location**: `src/gepa_adk/engine/async_engine.py` (lines 48-93)

**Current Fields**:
```python
@dataclass
class _EngineState:
    iteration: int = 0
    stagnation_counter: int = 0
    best_score: float
    best_candidate: ...
    iteration_history: list[IterationRecord]
    # ... other fields
```

**Missing Fields for StopperState**:
- `_start_time: float | None` - Not tracked
- `_total_evaluations: int` - Not tracked
- `candidates_count` - Can derive from `self._pareto_state.candidates` if ParetoState exists

**Decision**: Add `_start_time` and `_total_evaluations` as instance attributes on AsyncGEPAEngine (not _EngineState).

**Rationale**: These are engine-level concerns, not per-iteration state. Keeping them as instance attributes simplifies reset logic and matches existing patterns like `self._state`.

### 2.2 Current _should_stop() Implementation

**Location**: `src/gepa_adk/engine/async_engine.py` (lines 579-601)

**Current Logic**:
1. Check `iteration >= max_iterations` → return True
2. Check `patience > 0` and `stagnation_counter >= patience` → return True
3. Return False

**Decision**: Extend _should_stop() to check stop_callbacks after built-in conditions.

**Rationale**: Built-in conditions should remain first for performance (most common case). Custom stoppers checked only if built-in conditions don't trigger.

### 2.3 Evolution Loop Entry Point

**Location**: `src/gepa_adk/engine/async_engine.py` - `run()` method

**Decision**: Add lifecycle management (setup/cleanup) in `run()` method with try/finally.

**Rationale**: Ensures cleanup() is called even on exceptions, matching spec requirement FR-007.

## 3. Implementation Approach

### 3.1 State Tracking

**Decision**: Track state in AsyncGEPAEngine instance attributes.

```python
class AsyncGEPAEngine:
    def __init__(self, ...):
        ...
        self._start_time: float | None = None
        self._total_evaluations: int = 0
```

**Rationale**:
- `_start_time` must persist across iterations
- `_total_evaluations` accumulates throughout evolution
- Instance attributes are simpler than modifying _EngineState

### 3.2 StopperState Builder

**Decision**: Add `_build_stopper_state()` method to engine.

```python
def _build_stopper_state(self) -> StopperState:
    elapsed = time.monotonic() - self._start_time if self._start_time else 0.0
    return StopperState(
        iteration=self._state.iteration,
        best_score=self._state.best_score,
        stagnation_counter=self._state.stagnation_counter,
        total_evaluations=self._total_evaluations,
        candidates_count=len(self._pareto_state.candidates) if self._pareto_state else 0,
        elapsed_seconds=elapsed,
    )
```

**Rationale**: Encapsulates snapshot creation, makes _should_stop() cleaner, enables reuse if needed.

### 3.3 Stopper Checking Order

**Decision**: Check built-in conditions first, then stop_callbacks.

**Rationale**:
- Built-in conditions are O(1) comparisons
- stop_callbacks may involve multiple stopper calls
- Early return on built-in conditions avoids unnecessary work

### 3.4 SignalStopper Lifecycle

**Decision**: Use duck typing to detect setup/cleanup methods.

```python
signal_stoppers = [s for s in self.config.stop_callbacks if hasattr(s, 'setup')]
for stopper in signal_stoppers:
    stopper.setup()
```

**Rationale**:
- No protocol change needed
- Supports any future stopper with lifecycle needs
- Uses Python's duck typing idiom

**Alternatives Considered**:
- Adding `LifecycleStopper` protocol → Rejected: Over-engineering for single use case
- Requiring all stoppers to have setup/cleanup → Rejected: Breaks existing simple stoppers

### 3.5 Logging Strategy

**Decision**: Log stopper trigger with structlog including stopper class name and iteration.

```python
logger.info(
    "stopper.triggered",
    stopper=type(stopper).__name__,
    iteration=self._state.iteration,
)
```

**Rationale**: Matches existing structured logging patterns in codebase (ADR-008).

## 4. Testing Strategy

### 4.1 Unit Tests (tests/unit/engine/)

**Decision**: Create `test_stopper_integration.py` with mock stoppers.

Test cases:
- Mock stopper invoked each iteration
- Mock stopper receives valid StopperState
- Stopper returning True stops evolution
- Multiple stoppers - first True wins
- Empty stop_callbacks has no effect

### 4.2 Integration Tests (tests/integration/)

**Decision**: Create `test_stopper_integration.py` with real stoppers.

Test cases:
- TimeoutStopper triggers after elapsed time
- ScoreThresholdStopper triggers at target score
- SignalStopper setup/cleanup lifecycle
- CompositeStopper with multiple conditions

### 4.3 Contract Tests

**Decision**: Existing protocol tests in `tests/contracts/test_stopper_protocol.py` are sufficient.

**Rationale**: Protocol compliance already tested. Integration tests verify engine correctly uses the protocol.

## 5. Risk Assessment

### 5.1 Performance Impact

**Risk**: Stopper checking adds overhead to evolution loop.
**Mitigation**:
- Build-in conditions checked first (fast path)
- StopperState construction is O(1)
- Stoppers expected to be sub-millisecond

### 5.2 Backward Compatibility

**Risk**: Changes could break existing code using AsyncGEPAEngine.
**Mitigation**:
- Default `stop_callbacks=[]` in EvolutionConfig (already exists)
- No API changes to public methods
- Empty list = same behavior as before

### 5.3 SignalStopper Cleanup on Exception

**Risk**: Cleanup not called if exception occurs.
**Mitigation**: Use try/finally pattern in run() method to guarantee cleanup.

## 6. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| StopperState | Complete | `src/gepa_adk/domain/stopper.py` |
| StopperProtocol | Complete | `src/gepa_adk/ports/stopper.py` |
| TimeoutStopper | Complete | `src/gepa_adk/adapters/stoppers/timeout.py` |
| ScoreThresholdStopper | Complete | `src/gepa_adk/adapters/stoppers/threshold.py` |
| SignalStopper | Complete | `src/gepa_adk/adapters/stoppers/signal.py` |
| CompositeStopper | Complete | `src/gepa_adk/adapters/stoppers/composite.py` |
| EvolutionConfig.stop_callbacks | Complete | `src/gepa_adk/domain/models.py` |

All dependencies are complete. This is the final integration step.

## 7. Summary

No NEEDS CLARIFICATION items remain. Implementation approach is clear:

1. Add `_start_time` and `_total_evaluations` to AsyncGEPAEngine
2. Add `_build_stopper_state()` method
3. Extend `_should_stop()` to check stop_callbacks
4. Add lifecycle management (setup/cleanup) in `run()` with try/finally
5. Log stopper triggers with structlog
6. Create unit and integration tests

Estimated scope: ~50 lines changes to async_engine.py + ~100 lines tests.

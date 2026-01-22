# Contract: Stopper Integration in AsyncGEPAEngine

**Feature**: 196-stopper-engine-integration
**Date**: 2026-01-22

## Overview

This contract defines the behavior of stopper callback integration in AsyncGEPAEngine. It specifies how the engine interacts with stoppers during the evolution loop.

## Contract: Stopper Invocation

### Preconditions

1. `EvolutionConfig.stop_callbacks` is a list (may be empty)
2. Each item in `stop_callbacks` is callable with signature `(StopperState) -> bool`
3. Engine has been initialized with valid config

### Postconditions

1. Each stopper in `stop_callbacks` is invoked once per iteration
2. Stoppers receive a valid `StopperState` snapshot
3. If any stopper returns `True`, evolution terminates
4. Stopper invocation order matches list order

### Invariants

1. Built-in conditions (max_iterations, patience) are checked before custom stoppers
2. Empty `stop_callbacks` list results in no stopper invocations
3. StopperState is immutable during stopper invocation

## Contract: StopperState Accuracy

### Preconditions

1. Engine `_start_time` is set before evolution loop
2. Engine `_total_evaluations` is incremented after each evaluation batch

### Postconditions

1. `elapsed_seconds` = current monotonic time - start time
2. `total_evaluations` = sum of all evaluation batch sizes
3. `iteration` = current iteration number (0-indexed)
4. `best_score` = highest score achieved so far
5. `stagnation_counter` = iterations since last improvement
6. `candidates_count` = number of candidates in Pareto frontier

### Accuracy Requirements

| Field | Accuracy |
|-------|----------|
| `elapsed_seconds` | Within 50ms of actual elapsed time |
| `total_evaluations` | Exact count |
| `iteration` | Exact |
| `best_score` | Exact |
| `stagnation_counter` | Exact |
| `candidates_count` | Exact |

## Contract: Lifecycle Management

### Preconditions

1. Stoppers with `setup()` method are identified via `hasattr()`
2. Stoppers with `cleanup()` method are identified via `hasattr()`

### Postconditions

1. `setup()` is called on all applicable stoppers before evolution loop starts
2. `cleanup()` is called on all applicable stoppers after evolution loop ends
3. `cleanup()` is called even if an exception occurs during evolution
4. `cleanup()` is called in reverse order of `setup()` calls

### Error Handling

1. If `setup()` raises an exception, propagate the exception (don't start evolution)
2. If `cleanup()` raises an exception, log the error and continue cleanup for remaining stoppers

## Contract: Logging

### Events

| Event | Trigger | Fields |
|-------|---------|--------|
| `stopper.triggered` | Stopper returns True | `stopper`: class name, `iteration`: current iteration |

### Format

```python
logger.info(
    "stopper.triggered",
    stopper=type(stopper).__name__,
    iteration=self._state.iteration,
)
```

## Test Cases

### Unit Tests

```gherkin
Scenario: Stopper invoked each iteration
  Given EvolutionConfig with stop_callbacks=[MockStopper()]
  And MockStopper tracks invocation count
  When evolution runs for 3 iterations
  Then MockStopper.__call__ invoked at least 3 times

Scenario: Stopper receives valid StopperState
  Given EvolutionConfig with stop_callbacks=[StateCapturer()]
  When evolution runs
  Then StateCapturer received StopperState with all fields populated

Scenario: Stopper returning True stops evolution
  Given EvolutionConfig with stop_callbacks=[AlwaysTrueStopper()]
  When evolution starts
  Then evolution terminates after 1 iteration

Scenario: Multiple stoppers - short circuit on first True
  Given stop_callbacks=[AlwaysFalseStopper(), AlwaysTrueStopper(), NotCalledStopper()]
  When _should_stop() is called
  Then first two stoppers called
  And third stopper NOT called

Scenario: Empty stop_callbacks has no effect
  Given EvolutionConfig with stop_callbacks=[]
  When evolution runs
  Then only built-in conditions checked
```

### Integration Tests

```gherkin
Scenario: TimeoutStopper triggers
  Given TimeoutStopper(0.5) in stop_callbacks
  When evolution runs for > 0.5 seconds
  Then evolution stops
  And elapsed_seconds >= 0.5

Scenario: SignalStopper lifecycle
  Given SignalStopper() in stop_callbacks
  When evolution runs
  Then setup() called before loop
  And cleanup() called after loop

Scenario: cleanup() called on exception
  Given SignalStopper() in stop_callbacks
  And evolution raises exception during loop
  When exception is caught
  Then cleanup() was still called
```

## Verification

Contract compliance is verified by:

1. **Unit tests**: `tests/unit/engine/test_stopper_integration.py`
2. **Integration tests**: `tests/integration/test_stopper_integration.py`
3. **Code review**: Verify _should_stop() checks built-in conditions first

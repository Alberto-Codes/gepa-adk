# Quickstart: Wire stop_callbacks into AsyncGEPAEngine

**Feature**: 196-stopper-engine-integration
**Date**: 2026-01-22

## Overview

This feature integrates custom stopper callbacks into the evolution engine. After implementation, users can configure custom stop conditions that are checked during evolution.

## Prerequisites

- All stopper implementations are complete:
  - `TimeoutStopper` - Stop after elapsed time
  - `ScoreThresholdStopper` - Stop when score reaches target
  - `SignalStopper` - Stop on Ctrl+C (SIGINT/SIGTERM)
  - `CompositeStopper` - Combine multiple stoppers

## Usage

### Basic Example

```python
from gepa_adk.adapters.stoppers import TimeoutStopper, ScoreThresholdStopper
from gepa_adk.domain.models import EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine

# Configure stoppers
config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=[
        TimeoutStopper(timeout_seconds=300.0),  # 5 minutes
        ScoreThresholdStopper(threshold=0.95),   # 95% score
    ],
)

# Create and run engine
engine = AsyncGEPAEngine(config=config, ...)
result = await engine.run()
```

### Using SignalStopper for Graceful Shutdown

```python
from gepa_adk.adapters.stoppers import SignalStopper

config = EvolutionConfig(
    max_iterations=1000,
    stop_callbacks=[
        SignalStopper(),  # Ctrl+C triggers graceful stop
    ],
)
```

### Combining Multiple Conditions

```python
from gepa_adk.adapters.stoppers import (
    CompositeStopper,
    TimeoutStopper,
    ScoreThresholdStopper,
)

# Stop when EITHER timeout OR score threshold is reached
composite = CompositeStopper(
    stoppers=[
        TimeoutStopper(600.0),
        ScoreThresholdStopper(0.99),
    ],
    mode="any",  # OR logic (default)
)

config = EvolutionConfig(
    max_iterations=1000,
    stop_callbacks=[composite],
)
```

### Custom Stopper

```python
from gepa_adk.domain.stopper import StopperState

class EvaluationLimitStopper:
    """Stop after a fixed number of evaluations."""

    def __init__(self, max_evaluations: int) -> None:
        self.max_evaluations = max_evaluations

    def __call__(self, state: StopperState) -> bool:
        return state.total_evaluations >= self.max_evaluations

config = EvolutionConfig(
    max_iterations=1000,
    stop_callbacks=[EvaluationLimitStopper(max_evaluations=500)],
)
```

## StopperState Fields

Stoppers receive a `StopperState` snapshot with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | `int` | Current iteration (0-indexed) |
| `best_score` | `float` | Best score achieved |
| `stagnation_counter` | `int` | Iterations without improvement |
| `total_evaluations` | `int` | Total evaluate() calls |
| `candidates_count` | `int` | Candidates in Pareto frontier |
| `elapsed_seconds` | `float` | Wall-clock time since start |

## Behavior Notes

1. **Order of checks**: Built-in conditions (max_iterations, patience) are checked before custom stoppers
2. **Short-circuit**: First stopper to return `True` stops evolution
3. **Empty list**: If `stop_callbacks=[]`, only built-in conditions apply
4. **Logging**: When a stopper triggers, a log event is emitted with the stopper class name

## Testing

Run the integration tests:

```bash
# Unit tests with mocks
uv run pytest tests/unit/engine/test_stopper_integration.py -v

# Integration tests with real stoppers
uv run pytest tests/integration/test_stopper_integration.py -v
```

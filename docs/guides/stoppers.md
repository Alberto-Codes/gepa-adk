# Stop Callbacks

This guide covers how to use stop callbacks (stoppers) to control when evolution terminates.

!!! tip "Beyond Basic Parameters"
    While `EvolutionConfig` provides `max_iterations` and `patience`
    for basic termination control, stop callbacks enable advanced use cases like API cost
    limits, external orchestration, score thresholds, and combining multiple conditions.

## When to Use Stop Callbacks

Use stop callbacks when you need:

- **API Cost Control** — Limit total model evaluations to stay within budget
- **Time-Based Limits** — Stop after a specific wall-clock duration
- **External Orchestration** — Allow CI/CD pipelines or job schedulers to signal termination
- **Graceful Shutdown** — Handle Ctrl+C and system signals properly
- **Complex Conditions** — Combine multiple stop conditions with AND/OR logic

## Available Stoppers

| Stopper | Purpose | Use Case |
|---------|---------|----------|
| `MaxEvaluationsStopper(n)` | Stop after n total evaluations | API cost control |
| `TimeoutStopper(seconds)` | Stop after elapsed time | Job time limits |
| `ScoreThresholdStopper(threshold)` | Stop when score is reached | Early success |
| `RegressionStopper(window)` | Stop when score declines over N iterations | Detecting degrading runs |
| `SignalStopper()` | Stop on Ctrl+C or SIGTERM | Graceful shutdown |
| `FileStopper(path)` | Stop when a file exists | External orchestration |
| `CompositeStopper([...], mode)` | Combine stoppers | Complex conditions |

## Basic Usage

### MaxEvaluationsStopper

Control API costs by limiting total evaluations:

```python
from gepa_adk import evolve, run_sync, EvolutionConfig
from gepa_adk.adapters.stoppers import MaxEvaluationsStopper

# Stop after 1000 total evaluations
config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=[MaxEvaluationsStopper(1000)],
)

result = run_sync(evolve(agent, trainset, config=config))
```

**Why use this?** Each evaluation typically corresponds to one model API call.
If you're using expensive models like GPT-4 or Gemini Pro, limiting evaluations
directly controls your costs.

### FileStopper

Allow external systems to signal termination by creating a file:

```python
from gepa_adk.adapters.stoppers import FileStopper

# Stop when /tmp/gepa_stop file appears
config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=[FileStopper("/tmp/gepa_stop")],
)

# From another process or script:
# touch /tmp/gepa_stop
```

**Options:**

```python
# Automatically remove the stop file after triggering
stopper = FileStopper("/tmp/gepa_stop", remove_on_stop=True)

# Manually remove the stop file
stopper = FileStopper("/tmp/gepa_stop")
stopper.remove_stop_file()  # Idempotent - safe to call even if file doesn't exist
```

**Use cases:**
- CI/CD pipelines that create a stop file when jobs need to terminate
- Kubernetes jobs using preStop hooks
- Monitoring systems that detect issues and signal shutdown

### TimeoutStopper

Stop after a specific duration:

```python
from gepa_adk.adapters.stoppers import TimeoutStopper

# Stop after 1 hour
config = EvolutionConfig(
    max_iterations=1000,
    stop_callbacks=[TimeoutStopper(3600)],  # 3600 seconds = 1 hour
)
```

### ScoreThresholdStopper

Stop early when a target score is achieved:

```python
from gepa_adk.adapters.stoppers import ScoreThresholdStopper

# Stop when score reaches 95%
config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=[ScoreThresholdStopper(0.95)],
)
```

### RegressionStopper

Stop when scores are consistently declining over a lookback window:

```python
from gepa_adk import RegressionStopper

# Stop if score drops compared to where it was 3 iterations ago (default)
config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=[RegressionStopper()],
)

# Tighter window — stop if score drops vs just 2 iterations ago
config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=[RegressionStopper(window=2)],
)
```

**Cold-start phase:** `RegressionStopper` requires `window + 1` calls before it can fire. With the default `window=3`, the first 3 iterations are always `False` — this is by design to avoid false positives on noisy early scores.

**Plateau is not regression:** Equal scores (`0.8, 0.8, 0.8, 0.8`) do not trigger a stop. Only a *strictly lower* score than `window` iterations ago triggers regression detection.

**Instance reuse:** Call `stopper.setup()` between runs (or let the engine do it automatically) to reset history. Without this, history from run N bleeds into run N+1.

**Composition ordering caveat:** When using `CompositeStopper(mode="all")`, list `RegressionStopper` **first**. Python's `all()` short-circuits on the first `False` result, so if a non-stateful stopper listed before `RegressionStopper` returns `False`, `RegressionStopper.__call__` is never invoked and its history never accumulates.

```python
from gepa_adk import RegressionStopper
from gepa_adk.adapters.stoppers import CompositeStopper, ScoreThresholdStopper

# ✅ Correct: RegressionStopper listed first in mode="all"
composite = CompositeStopper(
    [RegressionStopper(window=3), ScoreThresholdStopper(0.95)],
    mode="all",
)

# ✅ Safe with mode="any" — short-circuit only fires when stopping anyway
composite = CompositeStopper(
    [ScoreThresholdStopper(0.95), RegressionStopper(window=3)],
    mode="any",
)
```

### SignalStopper

Handle Ctrl+C and system signals gracefully:

```python
from gepa_adk.adapters.stoppers import SignalStopper

# Use as context manager for proper cleanup
async with SignalStopper() as signal_stopper:
    config = EvolutionConfig(
        max_iterations=100,
        stop_callbacks=[signal_stopper],
    )
    result = await evolve(agent, trainset, config=config)
```

## Combining Stoppers

Use `CompositeStopper` to combine multiple conditions:

### OR Logic (mode="any")

Stop when **any** condition is met:

```python
from gepa_adk.adapters.stoppers import (
    CompositeStopper,
    MaxEvaluationsStopper,
    TimeoutStopper,
    ScoreThresholdStopper,
)

# Stop when: budget exhausted OR timeout OR target reached
composite = CompositeStopper([
    MaxEvaluationsStopper(5000),     # Budget limit
    TimeoutStopper(3600),             # 1 hour timeout
    ScoreThresholdStopper(0.95),      # Target score
], mode="any")

config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=[composite],
)
```

### AND Logic (mode="all")

Stop only when **all** conditions are met:

```python
# Stop only when both score threshold AND minimum evaluations are met
composite = CompositeStopper([
    ScoreThresholdStopper(0.90),     # Must reach 90%
    MaxEvaluationsStopper(100),       # Must have at least 100 evaluations
], mode="all")
```

### Nested Composites

For complex logic, nest composites:

```python
# Stop when: (budget OR timeout) AND (score threshold reached)
time_or_budget = CompositeStopper([
    MaxEvaluationsStopper(5000),
    TimeoutStopper(3600),
], mode="any")

complex_stop = CompositeStopper([
    time_or_budget,
    ScoreThresholdStopper(0.90),
], mode="all")
```

## Common Patterns

### Development vs Production

```python
import os

if os.environ.get("ENV") == "production":
    stop_callbacks = [
        MaxEvaluationsStopper(10000),
        TimeoutStopper(7200),  # 2 hours
    ]
else:
    stop_callbacks = [
        MaxEvaluationsStopper(100),  # Quick iterations in dev
    ]

config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=stop_callbacks,
)
```

### CI/CD Pipeline Integration

```python
from gepa_adk.adapters.stoppers import FileStopper, TimeoutStopper, CompositeStopper

# Allow pipeline to stop via file, with job timeout fallback
config = EvolutionConfig(
    max_iterations=1000,
    stop_callbacks=[
        CompositeStopper([
            FileStopper("/var/run/gepa/stop"),
            TimeoutStopper(1800),  # 30 min job limit
        ], mode="any"),
    ],
)
```

### Graceful Shutdown with Cleanup

```python
from gepa_adk.adapters.stoppers import SignalStopper, FileStopper, CompositeStopper

async def run_evolution():
    async with SignalStopper() as signal_stopper:
        file_stopper = FileStopper("/tmp/gepa_stop", remove_on_stop=True)

        config = EvolutionConfig(
            max_iterations=100,
            stop_callbacks=[
                CompositeStopper([signal_stopper, file_stopper], mode="any"),
            ],
        )

        return await evolve(agent, trainset, config=config)
```

## Creating Custom Stoppers

Stoppers implement a simple protocol — any callable with the right signature works:

```python
from gepa_adk.domain.stopper import StopperState

class MyCustomStopper:
    """Stop when a custom condition is met."""

    def __init__(self, threshold: int) -> None:
        self.threshold = threshold

    def __call__(self, state: StopperState) -> bool:
        """Return True to stop evolution."""
        return state.candidates_count > self.threshold

# Use it
config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=[MyCustomStopper(10)],
)
```

**Available state fields:**

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | `int` | Current iteration (0-indexed) |
| `best_score` | `float` | Best score achieved |
| `stagnation_counter` | `int` | Iterations without improvement |
| `total_evaluations` | `int` | Total evaluate() calls |
| `candidates_count` | `int` | Candidates in frontier |
| `elapsed_seconds` | `float` | Wall-clock time elapsed |

## API Reference

- [`MaxEvaluationsStopper`][gepa_adk.adapters.stoppers.MaxEvaluationsStopper] — Evaluation limit
- [`FileStopper`][gepa_adk.adapters.stoppers.FileStopper] — File-based stop signal
- [`TimeoutStopper`][gepa_adk.adapters.stoppers.TimeoutStopper] — Time-based limit
- [`ScoreThresholdStopper`][gepa_adk.adapters.stoppers.ScoreThresholdStopper] — Score threshold
- [`RegressionStopper`][gepa_adk.adapters.stoppers.RegressionStopper] — Score regression detection
- [`SignalStopper`][gepa_adk.adapters.stoppers.SignalStopper] — Signal handling
- [`CompositeStopper`][gepa_adk.adapters.stoppers.CompositeStopper] — Combine stoppers
- [`StopperState`][gepa_adk.domain.stopper.StopperState] — State passed to stoppers
- [`StopperProtocol`][gepa_adk.ports.stopper.StopperProtocol] — Protocol interface

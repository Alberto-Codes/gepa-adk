# Quickstart: Optional Stoppers

**Branch**: `197-optional-stoppers` | **Date**: 2026-01-22

## Overview

This guide shows how to use `MaxEvaluationsStopper` and `FileStopper` to control evolution termination based on API budget or external signals.

## Installation

These stoppers are included in the core `gepa-adk` package. No additional installation required.

```bash
uv add gepa-adk  # Includes all stoppers
```

## Quick Examples

### Control API Costs with MaxEvaluationsStopper

Limit evolution to a fixed number of model evaluations:

```python
from gepa_adk.adapters.stoppers import MaxEvaluationsStopper
from gepa_adk.domain.models import EvolutionConfig

# Stop after 1000 total evaluations (across all iterations)
config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=[
        MaxEvaluationsStopper(1000),  # Hard limit on API calls
    ],
)
```

### External Orchestration with FileStopper

Allow external systems to signal graceful termination:

```python
from gepa_adk.adapters.stoppers import FileStopper
from gepa_adk.domain.models import EvolutionConfig

# Stop when /tmp/gepa_stop file appears
config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=[
        FileStopper("/tmp/gepa_stop"),
    ],
)

# To stop evolution from external process:
# touch /tmp/gepa_stop
```

### Auto-Cleanup with remove_on_stop

Automatically remove the stop file after triggering:

```python
from gepa_adk.adapters.stoppers import FileStopper

# File is removed after triggering stop
stopper = FileStopper("/tmp/gepa_stop", remove_on_stop=True)
```

### Combining Multiple Stop Conditions

Use `CompositeStopper` to combine conditions:

```python
from gepa_adk.adapters.stoppers import (
    CompositeStopper,
    MaxEvaluationsStopper,
    FileStopper,
    TimeoutStopper,
    ScoreThresholdStopper,
)
from gepa_adk.domain.models import EvolutionConfig

# Stop on ANY condition (OR logic)
config = EvolutionConfig(
    stop_callbacks=[
        CompositeStopper([
            MaxEvaluationsStopper(5000),       # Budget limit
            FileStopper("/tmp/gepa_stop"),     # External signal
            TimeoutStopper(3600),              # 1 hour timeout
            ScoreThresholdStopper(0.95),       # Success threshold
        ], mode="any"),  # Stop when ANY condition is met
    ],
)
```

## Use Cases

### CI/CD Pipeline Integration

```python
# In your CI/CD pipeline job
config = EvolutionConfig(
    stop_callbacks=[
        FileStopper("/var/run/gepa/stop"),
        TimeoutStopper(1800),  # 30-minute job limit
    ],
)

# Pipeline can create stop file to terminate:
# kubectl exec pod -- touch /var/run/gepa/stop
```

### Budget-Constrained Experiments

```python
# Limit expensive API calls during experimentation
config = EvolutionConfig(
    stop_callbacks=[
        MaxEvaluationsStopper(100),   # Only 100 API calls
    ],
)
```

### Manual Cleanup

```python
# Explicitly remove stop file before starting
stopper = FileStopper("/tmp/gepa_stop")
stopper.remove_stop_file()  # Ensure clean state

# Or remove after evolution completes
stopper.remove_stop_file()
```

## Common Patterns

### Pattern 1: Development vs Production

```python
import os

if os.environ.get("ENV") == "production":
    stop_callbacks = [
        MaxEvaluationsStopper(10000),
        FileStopper("/var/run/gepa/stop"),
    ]
else:
    stop_callbacks = [
        MaxEvaluationsStopper(100),  # Quick iteration in dev
    ]
```

### Pattern 2: Graceful Shutdown

```python
from gepa_adk.adapters.stoppers import SignalStopper, FileStopper, CompositeStopper

# Support both Ctrl+C and file-based shutdown
graceful_stop = CompositeStopper([
    SignalStopper(),                    # Ctrl+C / SIGTERM
    FileStopper("/tmp/gepa_stop"),      # External file signal
], mode="any")
```

## Troubleshooting

### MaxEvaluationsStopper not stopping

- Check that `total_evaluations` in logs matches your expectation
- The stopper checks `>=`, so it stops when the limit is reached or exceeded
- If batch size is large, the count may exceed the limit between checks

### FileStopper not detecting file

- Verify the file path is correct and accessible
- Check file permissions (readable by the process)
- Use absolute paths for reliability
- The file just needs to exist; contents don't matter

### Combining with CompositeStopper

- Default mode is `"any"` (OR logic)
- Use `mode="all"` for AND logic (all conditions must be true)
- Nested composites are supported for complex logic

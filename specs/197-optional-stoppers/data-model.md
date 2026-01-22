# Data Model: Optional Stoppers

**Branch**: `197-optional-stoppers` | **Date**: 2026-01-22

## Overview

This feature adds two new stopper adapter classes. No new domain entities are required as both stoppers consume the existing `StopperState` dataclass.

## Existing Entities (No Changes)

### StopperState (domain/stopper.py)

```python
@dataclass(frozen=True, slots=True)
class StopperState:
    """Immutable snapshot of evolution state for stopper decisions."""

    iteration: int              # Current iteration number (0-indexed)
    best_score: float           # Best score achieved so far
    stagnation_counter: int     # Iterations without improvement
    total_evaluations: int      # Cumulative count of evaluate() calls
    candidates_count: int       # Number of candidates in frontier
    elapsed_seconds: float      # Wall-clock time since evolution started
```

**Usage by New Stoppers**:
- `MaxEvaluationsStopper` uses: `total_evaluations`
- `FileStopper` uses: None (checks external file system state)

### StopperProtocol (ports/stopper.py)

```python
@runtime_checkable
class StopperProtocol(Protocol):
    """Protocol for stop condition objects."""

    def __call__(self, state: StopperState) -> bool:
        """Check if evolution should stop."""
        ...
```

## New Adapter Classes

### MaxEvaluationsStopper

```
+-----------------------------------+
|     MaxEvaluationsStopper         |
+-----------------------------------+
| - max_evaluations: int            |
+-----------------------------------+
| + __init__(max_evaluations: int)  |
| + __call__(state: StopperState)   |
|   -> bool                         |
+-----------------------------------+
```

**Attributes**:
| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `max_evaluations` | `int` | `> 0` | Maximum number of evaluations before stopping |

**Validation Rules**:
- `max_evaluations` must be a positive integer
- Raises `ValueError` if `max_evaluations <= 0`

**Stop Condition**:
```
STOP when state.total_evaluations >= max_evaluations
```

### FileStopper

```
+-------------------------------------------+
|              FileStopper                  |
+-------------------------------------------+
| - stop_file_path: Path                    |
| - remove_on_stop: bool                    |
+-------------------------------------------+
| + __init__(stop_file_path: str | Path,    |
|            remove_on_stop: bool = False)  |
| + __call__(state: StopperState) -> bool   |
| + remove_stop_file() -> None              |
+-------------------------------------------+
```

**Attributes**:
| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `stop_file_path` | `Path` | (required) | Path to the stop signal file |
| `remove_on_stop` | `bool` | `False` | If True, remove file when triggering stop |

**Validation Rules**:
- `stop_file_path` is converted to `Path` if string provided
- No validation that path exists or is valid (non-existent paths simply don't trigger)

**Stop Condition**:
```
STOP when stop_file_path.exists() is True
IF remove_on_stop AND stopping:
    stop_file_path.unlink(missing_ok=True)
```

**Auxiliary Methods**:
- `remove_stop_file()`: Manually remove the stop file (idempotent)

## State Transitions

Neither stopper maintains internal state. Both are pure functions of their input:

```
MaxEvaluationsStopper:
    Input: StopperState.total_evaluations
    Output: bool (stop if >= threshold)

FileStopper:
    Input: File system state (stop_file_path existence)
    Output: bool (stop if file exists)
    Side Effect: Optional file removal
```

## Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                         Engine Layer                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              AsyncGEPAEngine._should_stop()              │   │
│  │                                                          │   │
│  │  1. Build StopperState from engine state                 │   │
│  │  2. For each stopper: if stopper(state): return True     │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │ calls
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Ports Layer                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   StopperProtocol                        │   │
│  │           __call__(state: StopperState) -> bool          │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │ implements
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Adapters Layer                            │
│  ┌────────────────────┐  ┌────────────────────┐                 │
│  │MaxEvaluationsStopper│  │    FileStopper     │                 │
│  │                    │  │                    │                 │
│  │ Uses:              │  │ Uses:              │                 │
│  │ state.total_evals  │  │ file system        │                 │
│  └────────────────────┘  └────────────────────┘                 │
│                                                                 │
│  Existing:                                                      │
│  ┌──────────────┐ ┌───────────────────┐ ┌───────────────┐       │
│  │TimeoutStopper│ │ScoreThresholdStop.│ │ SignalStopper │       │
│  └──────────────┘ └───────────────────┘ └───────────────┘       │
│                          │                                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               CompositeStopper                           │   │
│  │  Combines multiple stoppers with AND/OR logic            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Type Definitions

```python
# Type alias for stopper-compatible callables
StopperCallable = Callable[[StopperState], bool]

# Union type for FileStopper path input
PathLike = str | Path
```

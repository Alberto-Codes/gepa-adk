# API Contract: Optional Stoppers

**Branch**: `197-optional-stoppers` | **Date**: 2026-01-22

## Overview

This document defines the API contracts for `MaxEvaluationsStopper` and `FileStopper`. Both implement the existing `StopperProtocol` and are internal Python APIs (no REST/GraphQL).

## Protocol Compliance

Both stoppers MUST implement the `StopperProtocol`:

```python
@runtime_checkable
class StopperProtocol(Protocol):
    def __call__(self, state: StopperState) -> bool: ...
```

## MaxEvaluationsStopper API

### Constructor

```python
MaxEvaluationsStopper(max_evaluations: int) -> MaxEvaluationsStopper
```

**Parameters**:
| Name | Type | Required | Constraints | Description |
|------|------|----------|-------------|-------------|
| `max_evaluations` | `int` | Yes | `> 0` | Maximum number of evaluations |

**Returns**: `MaxEvaluationsStopper` instance

**Raises**:
| Exception | Condition |
|-----------|-----------|
| `ValueError` | `max_evaluations <= 0` |

**Example**:
```python
# Valid usage
stopper = MaxEvaluationsStopper(1000)

# Invalid usage - raises ValueError
stopper = MaxEvaluationsStopper(0)   # ValueError: max_evaluations must be positive
stopper = MaxEvaluationsStopper(-1)  # ValueError: max_evaluations must be positive
```

### __call__

```python
MaxEvaluationsStopper.__call__(state: StopperState) -> bool
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `state` | `StopperState` | Yes | Current evolution state snapshot |

**Returns**: `bool`
- `True` if `state.total_evaluations >= max_evaluations`
- `False` otherwise

**Example**:
```python
stopper = MaxEvaluationsStopper(100)

state_50 = StopperState(total_evaluations=50, ...)
assert stopper(state_50) is False

state_100 = StopperState(total_evaluations=100, ...)
assert stopper(state_100) is True

state_150 = StopperState(total_evaluations=150, ...)
assert stopper(state_150) is True
```

---

## FileStopper API

### Constructor

```python
FileStopper(
    stop_file_path: str | Path,
    remove_on_stop: bool = False
) -> FileStopper
```

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `stop_file_path` | `str \| Path` | Yes | - | Path to stop signal file |
| `remove_on_stop` | `bool` | No | `False` | Auto-remove file on stop |

**Returns**: `FileStopper` instance

**Example**:
```python
# String path
stopper = FileStopper("/tmp/gepa_stop")

# Path object
stopper = FileStopper(Path("/tmp/gepa_stop"))

# With auto-removal
stopper = FileStopper("/tmp/gepa_stop", remove_on_stop=True)
```

### __call__

```python
FileStopper.__call__(state: StopperState) -> bool
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `state` | `StopperState` | Yes | Current evolution state snapshot |

**Returns**: `bool`
- `True` if stop file exists (and removes it if `remove_on_stop=True`)
- `False` otherwise

**Side Effects**:
- If `remove_on_stop=True` AND file exists: file is deleted

**Example**:
```python
stopper = FileStopper("/tmp/gepa_stop")

# File doesn't exist
assert stopper(state) is False

# Create file
Path("/tmp/gepa_stop").touch()
assert stopper(state) is True

# With remove_on_stop
stopper_rm = FileStopper("/tmp/gepa_stop", remove_on_stop=True)
Path("/tmp/gepa_stop").touch()
assert stopper_rm(state) is True
assert not Path("/tmp/gepa_stop").exists()  # File removed
```

### remove_stop_file

```python
FileStopper.remove_stop_file() -> None
```

**Parameters**: None

**Returns**: `None`

**Side Effects**: Removes stop file if it exists (idempotent)

**Example**:
```python
stopper = FileStopper("/tmp/gepa_stop")
Path("/tmp/gepa_stop").touch()

stopper.remove_stop_file()
assert not Path("/tmp/gepa_stop").exists()

# Safe to call again - no error
stopper.remove_stop_file()
```

---

## Integration with CompositeStopper

Both stoppers work with `CompositeStopper` for combining conditions:

```python
from gepa_adk.adapters.stoppers import (
    CompositeStopper,
    MaxEvaluationsStopper,
    FileStopper,
    TimeoutStopper,
)

# Stop on ANY condition (OR logic - default)
combined = CompositeStopper([
    MaxEvaluationsStopper(1000),
    FileStopper("/tmp/gepa_stop"),
    TimeoutStopper(3600),
], mode="any")

# Stop only when ALL conditions met (AND logic)
combined = CompositeStopper([
    MaxEvaluationsStopper(100),
    FileStopper("/tmp/gepa_stop"),
], mode="all")
```

---

## EvolutionConfig Integration

```python
from gepa_adk.domain.models import EvolutionConfig
from gepa_adk.adapters.stoppers import MaxEvaluationsStopper, FileStopper

config = EvolutionConfig(
    max_iterations=100,
    stop_callbacks=[
        MaxEvaluationsStopper(5000),
        FileStopper("/var/run/gepa/stop"),
    ],
)
```

---

## Error Handling Contract

| Stopper | Error Condition | Exception | Recovery |
|---------|-----------------|-----------|----------|
| `MaxEvaluationsStopper` | `max_evaluations <= 0` | `ValueError` | Fix input value |
| `FileStopper` | Race condition on delete | None | `missing_ok=True` handles gracefully |
| `FileStopper` | Invalid path | None | File simply never exists, no stop triggered |
| `FileStopper` | Permission denied | `PermissionError` | Fix file permissions |

---

## Thread Safety

- `MaxEvaluationsStopper`: Thread-safe (stateless after construction)
- `FileStopper`: Thread-safe for `__call__`; `remove_stop_file` has race condition potential but is idempotent

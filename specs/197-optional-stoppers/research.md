# Research: Optional Stoppers (MaxEvaluations and File-based)

**Branch**: `197-optional-stoppers` | **Date**: 2026-01-22

## Research Summary

This feature has minimal unknowns due to the well-established stopper infrastructure. Research focused on:
1. Existing stopper patterns in the codebase
2. Best practices for file-based signaling
3. Race condition handling

## Research Findings

### 1. Stopper Protocol Compliance

**Decision**: Implement both stoppers as synchronous callables conforming to `StopperProtocol`

**Rationale**:
- The existing `StopperProtocol` defines `__call__(state: StopperState) -> bool`
- All existing stoppers (TimeoutStopper, ScoreThresholdStopper, SignalStopper, CompositeStopper) follow this pattern
- Synchronous design is intentional - stoppers should be fast, pure functions of state

**Alternatives Considered**:
- Async stopper protocol: Rejected - adds complexity for no benefit; file existence check is fast I/O
- Inheritance from base class: Rejected - protocol-based interfaces are the constitution standard

### 2. MaxEvaluationsStopper Implementation Pattern

**Decision**: Use `total_evaluations` field from `StopperState` with simple comparison

**Rationale**:
- `StopperState` already tracks `total_evaluations: int` (cumulative count of evaluate() calls)
- Pattern matches `TimeoutStopper` (compare field against threshold)
- Validation: reject zero or negative values at construction time (like `TimeoutStopper`)

**Alternatives Considered**:
- Track evaluations internally: Rejected - state already provides this; duplicating would violate single source of truth
- Allow zero evaluations: Rejected - meaningless configuration that would stop immediately

### 3. FileStopper Implementation Pattern

**Decision**: Use `pathlib.Path.exists()` for file detection with optional cleanup

**Rationale**:
- `pathlib` is stdlib (no new dependencies)
- `Path.exists()` is cross-platform (Windows, macOS, Linux)
- Optional `remove_on_stop` parameter for automatic cleanup
- Manual `remove_stop_file()` method for explicit cleanup

**Alternatives Considered**:
- `os.path.exists()`: Rejected - `pathlib` is more Pythonic and already used in codebase
- Watching file with inotify/fswatch: Rejected - adds external dependencies, polling is sufficient for stopper checks
- Read file content as signal: Rejected - mere existence is simpler and sufficient

### 4. Race Condition Handling

**Decision**: Handle race conditions gracefully with `missing_ok=True`

**Rationale**:
- File may be removed between existence check and unlink attempt
- `Path.unlink(missing_ok=True)` handles this atomically
- No need for file locking - eventual consistency is acceptable for stop signals

**Alternatives Considered**:
- File locking: Rejected - adds complexity; race condition between check and delete is benign
- Try/except FileNotFoundError: Rejected - `missing_ok=True` is cleaner

### 5. FileStopper Lifecycle Methods

**Decision**: No `setup()` or `cleanup()` methods required

**Rationale**:
- Unlike `SignalStopper`, `FileStopper` has no system resources to manage
- File existence check is stateless per call
- Manual cleanup via `remove_stop_file()` is sufficient for explicit use cases
- Engine integration handles stoppers without lifecycle methods correctly

**Alternatives Considered**:
- Auto-remove stop file on engine start (setup): Rejected - user may intentionally have the file from previous run
- Create sentinel file on cleanup: Rejected - changes semantics from "stop when file exists" to "stop when file removed"

### 6. Input Validation Patterns

**Decision**: Validate inputs at construction time

**Rationale**:
- `MaxEvaluationsStopper`: Raise `ValueError` for `max_evaluations <= 0`
- `FileStopper`: Accept any path (valid or not) - invalid paths simply never trigger stop
- Matches existing stopper patterns (e.g., `TimeoutStopper` validates `timeout_seconds > 0`)

**Alternatives Considered**:
- Validate file path exists on construction: Rejected - stop file may not exist yet; that's the point
- Validate parent directory exists: Rejected - adds complexity; non-existent path just means no stop

### 7. Testing Strategy

**Decision**: Three-layer testing per ADR-005

**Rationale**:
- Contract tests: Verify both stoppers implement `StopperProtocol`
- Unit tests: Test all acceptance scenarios with mocked `StopperState`
- Integration tests: Not required - these stoppers have no external I/O beyond file system

**Test Files**:
- `tests/contracts/test_stopper_protocol.py` - Add parametrized tests for new stoppers
- `tests/unit/adapters/stoppers/test_evaluations.py` - MaxEvaluationsStopper scenarios
- `tests/unit/adapters/stoppers/test_file.py` - FileStopper scenarios with `tmp_path` fixture

## Dependencies Verified

| Dependency | Status | Notes |
|------------|--------|-------|
| `StopperState.total_evaluations` | ✅ Available | Field exists in domain/stopper.py |
| `StopperProtocol` | ✅ Available | Protocol exists in ports/stopper.py |
| `CompositeStopper` | ✅ Available | For combining stoppers in adapters/stoppers/composite.py |
| `pathlib.Path` | ✅ stdlib | No new dependencies |
| `structlog` | ✅ Available | Already in project for logging |

## Conclusion

No unknowns remain. Implementation can proceed with:
- `MaxEvaluationsStopper`: Compare `state.total_evaluations >= self.max_evaluations`
- `FileStopper`: Check `self.stop_file_path.exists()` with optional `remove_on_stop`

Both implementations are straightforward following established patterns.

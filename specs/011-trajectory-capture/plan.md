# Implementation Plan: Trajectory Capture from ADK Sessions

**Feature Branch**: `011-trajectory-capture`  
**Created**: 2026-01-10  
**Spec**: [spec.md](spec.md)  
**Parent Issue**: GitHub Issue #11

## Research Summary

### ADK Architecture Analysis

Based on analysis of the installed Google ADK package (v1.22.0):

**Event Structure** (`google.adk.events.event.Event`):
- Inherits from `LlmResponse` which contains `usage_metadata: Optional[types.GenerateContentResponseUsageMetadata]`
- Has `actions: EventActions` containing `state_delta: dict[str, object]`
- Has methods: `get_function_calls()` → `list[types.FunctionCall]`, `get_function_responses()` → `list[types.FunctionResponse]`

**Token Usage** (`google.genai.types.GenerateContentResponseUsageMetadata`):
- `prompt_token_count: int`
- `candidates_token_count: int`
- `total_token_count: int` (sum of prompt + candidates + tool_use + thoughts)

**State Deltas** (`google.adk.events.event_actions.EventActions`):
- `state_delta: dict[str, object]` - Direct dict, not before/after values

### Existing Codebase

**Already Implemented** (`src/gepa_adk/domain/trajectory.py`):
- `ToolCallRecord(name, arguments, result, timestamp)`
- `TokenUsage(input_tokens, output_tokens, total_tokens)`
- `ADKTrajectory(tool_calls, state_deltas, token_usage, final_output, error)`

**Already Implemented** (`src/gepa_adk/adapters/adk_adapter.py`):
- `_extract_tool_calls(events)` - extracts from `Event.actions.function_calls`
- `_extract_state_deltas(events)` - extracts from `Event.state_delta` (note: different than `Event.actions.state_delta`)
- `_extract_token_usage(events)` - extracts from `Event.usage_metadata`
- `_build_trajectory()` - assembles all components

### Gap Analysis

| Required by Issue #11 | Current State | Action |
|----------------------|---------------|--------|
| `TrajectoryConfig` dataclass | Not exists | Create in `domain/types.py` |
| `extract_trajectory(response, config)` | Partial (in ADKAdapter) | Extract to `utils/events.py` |
| Configurable extraction flags | Hardcoded in ADKAdapter | Add config-based filtering |
| Sensitive data redaction | Not exists | Implement `_redact_sensitive()` |
| Recursive redaction | Not exists | Implement deep traversal |

## Architecture Decision

**Option A**: Add config + extraction to existing trajectory.py ✗
- Couples domain models with extraction logic
- Violates single responsibility

**Option B**: Create new `utils/events.py` module ✓
- Keeps domain models pure
- Extraction utilities are infrastructure-level concern
- Matches Issue #11 specification exactly

**Decision**: Option B - Create `utils/events.py` with `TrajectoryConfig` and `extract_trajectory`

## Implementation Tasks

### Task 1: Create TrajectoryConfig in domain/types.py (P1)
**Status**: not-started  
**Estimated**: 15 min

Add `TrajectoryConfig` dataclass to existing types module:
```python
@dataclass(frozen=True, slots=True)
class TrajectoryConfig:
    include_tool_calls: bool = True
    include_state_deltas: bool = True
    include_token_usage: bool = True
    redact_sensitive: bool = True
    sensitive_keys: tuple[str, ...] = ("password", "api_key", "token")
```

**Files**:
- Modify: `src/gepa_adk/domain/types.py`
- Modify: `src/gepa_adk/domain/__init__.py` (export)

**Tests**:
- `tests/unit/domain/test_types.py` - config defaults, immutability

---

### Task 2: Create utils module with events.py (P1)
**Status**: not-started  
**Estimated**: 30 min

Create extraction utilities module:

```python
# src/gepa_adk/utils/__init__.py
# src/gepa_adk/utils/events.py

def extract_trajectory(
    events: list[Event],
    config: TrajectoryConfig,
    final_output: str = "",
    error: str | None = None,
) -> ADKTrajectory:
    """Extract trajectory data from ADK events based on config."""
```

**Files**:
- Create: `src/gepa_adk/utils/__init__.py`
- Create: `src/gepa_adk/utils/events.py`

**Tests**:
- Create: `tests/unit/utils/__init__.py`
- Create: `tests/unit/utils/test_events.py`

---

### Task 3: Implement redaction function (P2)
**Status**: not-started  
**Estimated**: 30 min

Create recursive redaction utility:

```python
def _redact_sensitive(
    data: Any,
    sensitive_keys: tuple[str, ...],
    marker: str = "[REDACTED]",
) -> Any:
    """Recursively redact sensitive keys from data structures."""
```

**Implementation Details**:
- Handle `dict`, `list`, `tuple` recursively
- Exact key matching (case-sensitive)
- Return new data structure, don't mutate

**Files**:
- Modify: `src/gepa_adk/utils/events.py`

**Tests**:
- Add to: `tests/unit/utils/test_events.py`
- Cases: nested dicts, lists with dicts, mixed structures, no sensitive data

---

### Task 4: Implement extract_trajectory function (P1)
**Status**: not-started  
**Estimated**: 45 min

Full extraction function with configurable behavior:

```python
def extract_trajectory(
    events: list[Event],
    config: TrajectoryConfig | None = None,
    final_output: str = "",
    error: str | None = None,
) -> ADKTrajectory:
    """Extract trajectory from ADK Event stream based on config."""
    config = config or TrajectoryConfig()
    
    tool_calls = _extract_tool_calls(events) if config.include_tool_calls else ()
    state_deltas = _extract_state_deltas(events) if config.include_state_deltas else ()
    token_usage = _extract_token_usage(events) if config.include_token_usage else None
    
    # Build trajectory
    trajectory_data = {...}
    
    # Apply redaction if enabled
    if config.redact_sensitive:
        trajectory_data = _redact_sensitive(trajectory_data, config.sensitive_keys)
    
    return ADKTrajectory(**trajectory_data)
```

**Files**:
- Modify: `src/gepa_adk/utils/events.py`

**Tests**:
- Add to: `tests/unit/utils/test_events.py`
- Cases: all flags true/false combinations, empty events, missing data

---

### Task 5: Refactor ADKAdapter to use extract_trajectory (P2)
**Status**: not-started  
**Estimated**: 30 min

Update ADKAdapter to delegate trajectory building:

```python
# In ADKAdapter._build_trajectory
from gepa_adk.utils.events import extract_trajectory

def _build_trajectory(self, events, final_output, error=None):
    return extract_trajectory(
        events=events,
        config=self._trajectory_config,  # New attribute
        final_output=final_output,
        error=error,
    )
```

**Files**:
- Modify: `src/gepa_adk/adapters/adk_adapter.py`

**Tests**:
- Modify: `tests/unit/adapters/test_adk_adapter.py` - verify delegation

---

### Task 6: Add TrajectoryConfig to ADKAdapter (P2)
**Status**: not-started  
**Estimated**: 20 min

Add trajectory config to adapter initialization:

```python
def __init__(
    self,
    agent: LlmAgent,
    scorer: Scorer,
    session_service: BaseSessionService | None = None,
    app_name: str = "gepa_adk_eval",
    trajectory_config: TrajectoryConfig | None = None,  # New
) -> None:
    ...
    self._trajectory_config = trajectory_config or TrajectoryConfig()
```

**Files**:
- Modify: `src/gepa_adk/adapters/adk_adapter.py`

**Tests**:
- Modify: `tests/unit/adapters/test_adk_adapter.py`

---

### Task 7: Update exports and documentation (P3)
**Status**: not-started  
**Estimated**: 15 min

Update package exports:

**Files**:
- Modify: `src/gepa_adk/__init__.py` - export TrajectoryConfig, extract_trajectory
- Modify: `src/gepa_adk/domain/__init__.py` - export TrajectoryConfig

---

### Task 8: Integration tests (P2)
**Status**: not-started  
**Estimated**: 30 min

Create integration tests with realistic ADK events:

**Files**:
- Create: `tests/integration/test_trajectory_capture.py`

**Test Cases**:
- Extract from real ADK Event objects
- Redaction with actual sensitive data
- Full flow through ADKAdapter

---

## Dependency Graph

```
Task 1 (TrajectoryConfig)
    ↓
Task 2 (utils/events.py skeleton)
    ↓
Task 3 (redaction) ←─────┐
    ↓                    │
Task 4 (extract_trajectory) ←─ depends on 1, 2, 3
    ↓
Task 5 (refactor ADKAdapter) ←─ depends on 4
    ↓
Task 6 (config in ADKAdapter) ←─ depends on 1, 5
    ↓
Task 7 (exports) ←─ depends on 1, 2, 4, 6
    ↓
Task 8 (integration tests) ←─ depends on all
```

## Test Strategy

### Unit Tests (TDD)

1. **test_types.py** - TrajectoryConfig
   - Test default values
   - Test immutability (frozen)
   - Test custom sensitive_keys

2. **test_events.py** - Extraction utilities
   - Test redaction with various data structures
   - Test extract_trajectory with each config flag
   - Test graceful handling of missing data

### Integration Tests

1. **test_trajectory_capture.py**
   - Full ADKAdapter flow with trajectory config
   - Real ADK Event mock objects
   - End-to-end redaction verification

## Success Validation

- [ ] All existing tests pass (`uv run pytest`)
- [ ] New unit tests cover TrajectoryConfig and extract_trajectory
- [ ] Redaction works recursively at any depth
- [ ] ADKAdapter accepts TrajectoryConfig
- [ ] No sensitive data in extracted trajectories when redaction enabled
- [ ] Graceful handling of missing/null event data

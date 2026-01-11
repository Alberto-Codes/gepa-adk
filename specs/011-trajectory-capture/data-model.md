# Data Model: Trajectory Capture from ADK Sessions

**Feature**: 011-trajectory-capture  
**Date**: 2026-01-10  
**Status**: Complete

## Entity Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        TrajectoryConfig                          │
│  (NEW - domain/types.py)                                        │
├─────────────────────────────────────────────────────────────────┤
│  include_tool_calls: bool = True                                │
│  include_state_deltas: bool = True                              │
│  include_token_usage: bool = True                               │
│  redact_sensitive: bool = True                                  │
│  sensitive_keys: tuple[str, ...] = ("password", "api_key", "token") │
│  max_string_length: int | None = 10000                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ configures
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      extract_trajectory()                        │
│  (NEW - utils/events.py)                                        │
├─────────────────────────────────────────────────────────────────┤
│  Input: events: list[Event], final_output: str, config: TrajectoryConfig │
│  Output: ADKTrajectory                                          │
│  Behavior: Extract + redaction + truncation                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ produces
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ADKTrajectory                             │
│  (EXISTING - domain/trajectory.py)                              │
├─────────────────────────────────────────────────────────────────┤
│  tool_calls: tuple[ToolCallRecord, ...]                         │
│  state_deltas: tuple[dict[str, Any], ...]                       │
│  token_usage: TokenUsage | None                                 │
│  final_output: str                                              │
│  error: str | None                                              │
└─────────────────────────────────────────────────────────────────┘
```

## New Entities

### TrajectoryConfig

**Location**: `src/gepa_adk/domain/types.py`  
**Type**: `@dataclass(frozen=True, slots=True)`

```python
@dataclass(frozen=True, slots=True)
class TrajectoryConfig:
    """Configuration for trajectory extraction behavior.
    
    Controls which components are extracted from ADK event streams,
    whether sensitive data should be redacted, and whether large
    values should be truncated.
    
    Attributes:
        include_tool_calls: Extract tool/function call records.
        include_state_deltas: Extract session state changes.
        include_token_usage: Extract LLM token consumption metrics.
        redact_sensitive: Apply sensitive data redaction.
        sensitive_keys: Field names to redact (exact match).
        max_string_length: Truncate strings longer than this. None disables.
    """
    include_tool_calls: bool = True
    include_state_deltas: bool = True
    include_token_usage: bool = True
    redact_sensitive: bool = True
    sensitive_keys: tuple[str, ...] = ("password", "api_key", "token")
    max_string_length: int | None = 10000
```

**Validation Rules**:
- All fields have sensible defaults (no required args)
- `sensitive_keys` must be tuple (immutable) not list
- `max_string_length` of None disables truncation
- Frozen ensures config can't be modified after creation

**Relationships**:
- Used by `extract_trajectory()` function
- Optionally stored by `ADKAdapter` for default config

---

## Existing Entities (Reference)

### ADKTrajectory

**Location**: `src/gepa_adk/domain/trajectory.py`  
**No changes required**

```python
@dataclass(frozen=True, slots=True)
class ADKTrajectory:
    tool_calls: tuple[ToolCallRecord, ...]
    state_deltas: tuple[dict[str, Any], ...]
    token_usage: TokenUsage | None
    final_output: str
    error: str | None
```

### ToolCallRecord

**Location**: `src/gepa_adk/domain/trajectory.py`  
**No changes required**

```python
@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    name: str
    arguments: dict[str, Any]
    result: Any
    timestamp: float
```

### TokenUsage

**Location**: `src/gepa_adk/domain/trajectory.py`  
**No changes required**

```python
@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
```

---

## Field Mappings

### ADK Event → ToolCallRecord

| ADK Source | Target Field |
|------------|--------------|
| `FunctionCall.name` | `name` |
| `FunctionCall.args` | `arguments` |
| `FunctionResponse.response` | `result` |
| `Event.timestamp` | `timestamp` |

### ADK Event → TokenUsage

| ADK Source | Target Field |
|------------|--------------|
| `usage_metadata.prompt_token_count` | `input_tokens` |
| `usage_metadata.candidates_token_count` | `output_tokens` |
| `usage_metadata.total_token_count` | `total_tokens` |

### ADK Event → State Delta

| ADK Source | Target |
|------------|--------|
| `event.actions.state_delta` | `dict[str, Any]` appended to `state_deltas` tuple |

---

## State Transitions

TrajectoryConfig is immutable (frozen dataclass). No state transitions.

ADKTrajectory is immutable. Created once by `extract_trajectory()`, never modified.

---

## Constraints

1. **Immutability**: All domain models use `frozen=True`
2. **No External Imports**: `TrajectoryConfig` in domain/ cannot import from google.adk
3. **Tuple Collections**: Use `tuple[...]` not `list[...]` for immutable sequences
4. **Default Security**: `redact_sensitive=True` by default (secure by default)

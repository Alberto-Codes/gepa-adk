# Data Model: ADK Session State Management

**Feature**: 122-adk-session-state
**Date**: 2026-01-18

## Overview

This feature enhances the existing data flow between reflection agent components by leveraging ADK's native session state management. No new domain models are introduced; instead, existing patterns are extended to use ADK's built-in state storage.

## Entities

### Session State (ADK-Managed)

The session state is managed by ADK's `Session` model and persisted via `BaseSessionService`.

```
┌─────────────────────────────────────────────────────────────┐
│ Session (google.adk.sessions.Session)                       │
├─────────────────────────────────────────────────────────────┤
│ id: str                    # Unique session identifier      │
│ app_name: str              # Application name               │
│ user_id: str               # User identifier                │
│ state: dict[str, Any]      # Session state storage          │
│ events: list[Event]        # Event history                  │
│ last_update_time: float    # Last modification timestamp    │
└─────────────────────────────────────────────────────────────┘
```

### Session State Keys (Reflection Context)

| Key | Type | Description | Source |
|-----|------|-------------|--------|
| `component_text` | `str` | Current component text being evolved | Injected at session creation |
| `trials` | `str` | JSON-serialized list of trial records | Injected at session creation |
| `proposed_instruction` | `str` | Agent's proposed improvement (output) | Stored by ADK via output_key |

### Trial Record Structure (Existing)

No changes to the trial record structure. Already used in `adk_reflection.py`:

```python
trial: dict[str, Any] = {
    "input": str,           # Input to the system
    "output": str,          # Output from the system
    "feedback": {           # Critic evaluation
        "score": float,
        "feedback_text": str,
        "feedback_guidance": str | None,
        "feedback_dimensions": dict | None,
    },
    "trajectory": dict | None,  # Execution trace (optional)
}
```

## State Flow

```
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ Input Injection      │     │ Agent Execution      │     │ Output Retrieval     │
│                      │     │                      │     │                      │
│ session.state = {    │     │ instruction uses:    │     │ return               │
│   component_text,    │ ──► │   {component_text}   │ ──► │   session.state[     │
│   trials (JSON)      │     │   {trials}           │     │     output_key       │
│ }                    │     │                      │     │   ]                  │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
```

## Relationships

### ReflectionFn ↔ Session State

```
ReflectionFn(component_text, trials) -> proposed_component_text
                    │                              ▲
                    ▼                              │
           ┌───────────────┐              ┌───────────────┐
           │ Session.state │  ──────────► │ Session.state │
           │ (input)       │   Agent      │ (output)      │
           │               │   Exec       │               │
           │ component_text│              │ proposed_     │
           │ trials        │              │ instruction   │
           └───────────────┘              └───────────────┘
```

### Multi-Agent Workflow State Flow (Future)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Critic      │     │ Session     │     │ Reflection  │
│ Agent       │     │ State       │     │ Agent       │
│             │     │             │     │             │
│ output_key: │ ──► │ critic_     │ ──► │ instruction:│
│ "critic_    │     │ feedback    │     │ {critic_    │
│  feedback"  │     │             │     │  feedback}  │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Validation Rules

### Session State Validation

| Rule | Enforcement |
|------|-------------|
| `component_text` must be non-empty string | Validated before session creation |
| `trials` must be valid JSON | JSON serialization at injection |
| `output_key` must be valid identifier | ADK validates via `_is_valid_state_name()` |

### Output Validation

| Rule | Enforcement |
|------|-------------|
| Output must be non-empty string | Validated in `AsyncReflectiveMutationProposer` |
| Output must not be `None` | Fallback to event-based extraction |

## State Transitions

### Reflection Operation Lifecycle

```
┌─────────────┐
│   INIT      │  Session created with initial state
└──────┬──────┘
       │ create_session(state={component_text, trials})
       ▼
┌─────────────┐
│  RUNNING    │  Agent executing, state accessible via templates
└──────┬──────┘
       │ Agent produces final response
       ▼
┌─────────────┐
│  COMPLETE   │  output_key written to state_delta
└──────┬──────┘
       │ state_delta merged into session.state
       ▼
┌─────────────┐
│ RETRIEVED   │  Output extracted from session.state[output_key]
└─────────────┘
```

## Backward Compatibility

### Existing Interface (Unchanged)

```python
ReflectionFn = Callable[[str, list[dict[str, Any]]], Awaitable[str]]
```

The function signature remains identical:
- Input: `(component_text: str, trials: list[dict])`
- Output: `str` (proposed component text)

### Internal Changes (Transparent to Callers)

| Before | After |
|--------|-------|
| Data passed via session state | Data passed via session state (unchanged) |
| Output extracted from events | Output extracted from session.state (new) |
| No output_key | output_key configured on agent |

## Schema Definitions

### Session State Schema

```python
SESSION_STATE_KEYS = {
    "component_text": str,
    "trials": str,  # JSON-serialized
}

# Extended with output_key
SESSION_STATE_KEYS_WITH_OUTPUT = {
    **SESSION_STATE_KEYS,
    "proposed_instruction": str,  # Default output_key value
}
```

### Type Aliases (Existing)

```python
# From engine/proposer.py - unchanged
ReflectionFn = Callable[[str, list[dict[str, Any]]], Awaitable[str]]
ReflectiveDataset = Mapping[str, Sequence[Mapping[str, Any]]]
ProposalResult = dict[str, str] | None
```

## Shared Utility

### extract_output_from_state

A shared utility in `utils/events.py` for extracting output from session state:

```python
def extract_output_from_state(
    session_state: dict[str, Any],
    output_key: str | None,
) -> str | None:
    """Extract output from session state using output_key.

    Returns None if extraction fails (caller should fallback).
    """
```

**Location**: `src/gepa_adk/utils/events.py`

**Used By**:
- `engine/adk_reflection.py` - Reflection agent output retrieval
- `adapters/multi_agent.py` - Multi-agent pipeline output retrieval

**Rationale**: Shared utility in `utils/` follows hexagonal architecture (accessible from both engine/ and adapters/ without violating layer boundaries).

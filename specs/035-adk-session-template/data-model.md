# Data Model: ADK Session State Template Substitution

**Branch**: `035-adk-session-template` | **Date**: 2026-01-18

## Overview

This feature does not introduce new data models. It modifies how existing data flows through the reflection agent by using ADK's native template substitution instead of manual message construction.

## Existing Entities (No Changes)

### Session State

The session state structure remains unchanged:

```python
session_state: dict[str, Any] = {
    "component_text": str,  # The component text to improve
    "trials": str,          # JSON-serialized trial results
}
```

**Notes:**
- `component_text`: Plain string containing the agent instruction/prompt to improve
- `trials`: Must be pre-serialized to JSON string (ADK uses `str()` conversion)

### Template Placeholders

Templates are string patterns in agent instructions, not persisted data:

| Placeholder | Maps To | Type |
|-------------|---------|------|
| `{component_text}` | `session.state["component_text"]` | str |
| `{trials}` | `session.state["trials"]` | str (JSON) |

## Data Flow

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        BEFORE (Current)                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  component_text ──┐                                                  │
│                   ├──► f-string interpolation ──► user_message       │
│  trials ──────────┘                                                  │
│                                                                      │
│  LlmAgent.instruction = "static instruction"                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         AFTER (Proposed)                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  component_text ──┐                                                  │
│                   ├──► session_state dict ──► ADK inject_session_state│
│  trials ──────────┘                                                  │
│                                                                      │
│  LlmAgent.instruction = "{component_text}\n{trials}\n..."            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Validation Rules

| Field | Rule | Enforced By |
|-------|------|-------------|
| `component_text` | Non-empty string | Existing validation in `create_adk_reflection_fn` |
| `trials` | Valid JSON string | Pre-serialization via `json.dumps()` |
| Template keys | Valid Python identifiers | ADK's `_is_valid_state_name()` |

## State Transitions

N/A - No state machine involved. Session state is immutable during agent execution.

## Migration Notes

No data migration required. This is a code-level change in how data is passed to the LLM, not a change in data structure or storage.

# Data Model: Shared ADK Event Output Extraction Utility

**Feature Branch**: `033-event-output-extraction`
**Created**: 2026-01-17

## Overview

This feature does not introduce new persistent data models. It operates on in-memory ADK event objects passed from the google-adk library.

## External Types (ADK Library)

The utility function processes objects from the google-adk library. These types are documented here for reference but are NOT defined by this project.

### ADK Event (google.adk.events.Event)

The event object emitted by ADK agents during execution.

| Attribute | Type | Description |
|-----------|------|-------------|
| `is_final_response()` | method → bool | Returns True if this is the final response event |
| `actions` | EventActions | None | Container for response actions |
| `content` | EventContent | None | Container for content parts |

### EventActions (google.adk.events.EventActions)

| Attribute | Type | Description |
|-----------|------|-------------|
| `response_content` | list[Part] | None | List of response content parts (preferred source) |

### EventContent (google.adk.events.Content)

| Attribute | Type | Description |
|-----------|------|-------------|
| `parts` | list[Part] | None | List of content parts (fallback source) |

### Part (google.genai.types.Part)

| Attribute | Type | Description |
|-----------|------|-------------|
| `text` | str | None | Text content of the part |
| `thought` | bool | None | True if this is reasoning/thinking content (should be filtered) |

## Internal Types

### Function Return Type

The `extract_final_output` function returns:

| Type | Description |
|------|-------------|
| `str` | Extracted output text, or empty string if no valid output found |

## State Transitions

N/A - This is a stateless utility function. No state transitions occur.

## Data Flow

```
ADK Events (list[Any])
        │
        ▼
┌───────────────────────────────┐
│    extract_final_output()     │
│                               │
│  1. Iterate events            │
│  2. Check is_final_response() │
│  3. Try response_content      │
│  4. Fallback to content.parts │
│  5. Filter part.thought=True  │
│  6. Return text (or concat)   │
└───────────────────────────────┘
        │
        ▼
    str (output text)
```

## Validation Rules

| Rule | Description | Enforcement |
|------|-------------|-------------|
| V-001 | Parts with `thought=True` MUST be excluded | Checked via `getattr(part, "thought", False)` |
| V-002 | Empty/None text parts MUST be skipped | Checked via `hasattr(part, "text") and part.text` |
| V-003 | Missing attributes MUST not raise exceptions | Defensive `getattr`/`hasattr` checks throughout |

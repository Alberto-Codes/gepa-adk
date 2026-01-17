# Contract: extract_final_output Function

**Feature Branch**: `033-event-output-extraction`
**Created**: 2026-01-17

## Function Signature

```python
def extract_final_output(events: list[Any], *, prefer_concatenated: bool = False) -> str
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `events` | `list[Any]` | Yes | - | List of ADK event objects to process |
| `prefer_concatenated` | `bool` | No | `False` | If True, concatenate all non-thought text parts from all events |

## Return Value

| Type | Description |
|------|-------------|
| `str` | Extracted output text. Returns empty string `""` if no valid output found. |

## Behavior Contract

### Response Source Priority

1. **Primary**: `event.actions.response_content` (if available and non-empty)
2. **Fallback**: `event.content.parts` (if response_content unavailable)

### Event Filtering

- Only events where `event.is_final_response()` returns `True` are processed
- Non-final events are skipped

### Part Filtering (Bug Fix)

- Parts where `getattr(part, "thought", False)` is `True` MUST be excluded
- Parts where `part.text` is `None` or empty string MUST be skipped
- Only parts with valid non-thought text content are included

### Extraction Modes

#### Mode 1: Default (`prefer_concatenated=False`)

- Iterate through events to find first final response
- Return first non-thought text part from that event
- Stop after first valid text is found

#### Mode 2: Concatenated (`prefer_concatenated=True`)

- Iterate through ALL events
- Collect all non-thought text parts from all final response events
- Concatenate all collected texts (no separator)
- Return concatenated result

## Pre-conditions

- `events` parameter is a list (may be empty)
- Event objects have duck-typed interface compatible with ADK events

## Post-conditions

- Return value is always a string (never None)
- No exceptions raised for missing attributes (graceful degradation)
- Original events list is not modified

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Empty events list | Return `""` |
| No final response events | Return `""` |
| All parts have `thought=True` | Return `""` |
| Event missing `actions` attribute | Gracefully skip to fallback |
| Event missing `content` attribute | Skip event, continue to next |
| Part missing `text` attribute | Skip part, continue to next |

## Test Cases

### TC-001: Extract from response_content

**Given**: Event with `actions.response_content` containing `[Part(text="Hello")]`
**When**: `extract_final_output(events)` is called
**Then**: Returns `"Hello"`

### TC-002: Fallback to content.parts

**Given**: Event with `actions=None` and `content.parts` containing `[Part(text="World")]`
**When**: `extract_final_output(events)` is called
**Then**: Returns `"World"`

### TC-003: Filter thought parts

**Given**: Event with parts `[Part(text="Thinking...", thought=True), Part(text="Answer")]`
**When**: `extract_final_output(events)` is called
**Then**: Returns `"Answer"`

### TC-004: All thought parts

**Given**: Event with parts `[Part(text="Thinking...", thought=True)]`
**When**: `extract_final_output(events)` is called
**Then**: Returns `""`

### TC-005: Empty events list

**Given**: Empty list `[]`
**When**: `extract_final_output(events)` is called
**Then**: Returns `""`

### TC-006: Concatenated mode

**Given**: Multiple events each with `Part(text="chunk1")`, `Part(text="chunk2")`
**When**: `extract_final_output(events, prefer_concatenated=True)` is called
**Then**: Returns `"chunk1chunk2"`

### TC-007: Skip non-final events

**Given**: Event where `is_final_response()` returns `False`
**When**: `extract_final_output(events)` is called
**Then**: Returns `""` (skips non-final event)

### TC-008: Multiple events, default mode

**Given**: Multiple final events with text parts
**When**: `extract_final_output(events)` is called (default mode)
**Then**: Returns text from first final event only

### TC-009: Graceful handling of missing attributes

**Given**: Event object without `actions` or `content` attributes
**When**: `extract_final_output(events)` is called
**Then**: Returns `""` without raising exception

### TC-010: Part without thought attribute

**Given**: Event with `Part(text="Text")` (no `thought` attribute)
**When**: `extract_final_output(events)` is called
**Then**: Returns `"Text"` (treats missing thought as False)

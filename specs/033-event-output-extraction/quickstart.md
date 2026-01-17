# Quickstart: Shared ADK Event Output Extraction Utility

**Feature Branch**: `033-event-output-extraction`
**Created**: 2026-01-17

## Overview

This feature adds a shared utility function `extract_final_output` to centralize ADK event output extraction logic. It fixes a critical bug where models emitting reasoning content (`part.thought=True`) were causing parse failures.

## Usage

### Basic Usage

```python
from gepa_adk.utils.events import extract_final_output

# Extract output from ADK events (default: first text part from final event)
events = await runner.run(user_id="user", session_id="session", content=input_text)
output = extract_final_output(events)
```

### Streaming/Concatenation Mode

```python
from gepa_adk.utils.events import extract_final_output

# For streaming scenarios where JSON may be split across parts
events = await runner.run(user_id="user", session_id="session", content=input_text)
output = extract_final_output(events, prefer_concatenated=True)
```

## For Adapter Maintainers

### Before (Duplicated Code)

Each adapter had its own extraction logic:

```python
# In adk_adapter.py, multi_agent.py, critic_scorer.py
if event.is_final_response():
    if event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, "text") and part.text:
                final_output = part.text
                break
```

### After (Shared Utility)

```python
from gepa_adk.utils.events import extract_final_output

# Simple one-liner replacement
final_output = extract_final_output(events)
```

## Key Behaviors

1. **Response Source Priority**: Tries `event.actions.response_content` first, falls back to `event.content.parts`
2. **Thought Filtering**: Automatically filters out reasoning content (`part.thought=True`)
3. **Graceful Degradation**: Returns empty string for missing/malformed events (no exceptions)

## Related Files

- **Utility**: `src/gepa_adk/utils/events.py`
- **Contract**: `specs/033-event-output-extraction/contracts/extract_final_output.md`
- **Tests**: `tests/unit/utils/test_events.py`

# Data Model: ADK Reflection Agents

**Date**: 2026-01-17
**Branch**: `034-adk-ollama-reflection`
**Status**: Implemented

## Overview

This document describes the data structures used for ADK reflection agents.

## Core Data Structures

### ReflectionFn Protocol

The reflection function protocol that ADK reflection agents implement:

```python
ReflectionFn = Callable[[str, list[dict[str, Any]]], Awaitable[str]]

# Parameters:
#   component_text: str - The current text to improve
#   trials: list[dict] - Performance records with feedback and trajectory
# Returns:
#   str - The proposed improved text
```

### Trial Structure

Each trial represents one evaluation of the component with structured feedback:

```python
trial = {
    "feedback": {
        "score": 0.75,                        # Required: 0.0-1.0
        "feedback_text": "Good but formal",   # Required: critic feedback
        "feedback_guidance": "Use formal",    # Optional: actionable guidance
        "feedback_dimensions": {...},         # Optional: multi-dimensional scores
    },
    "trajectory": {
        "input": "I am His Majesty",          # Required: input text
        "output": "Hello, Your Majesty!",     # Required: agent output
        "trace": {                            # Optional: execution metadata
            "tool_calls": 0,
            "tokens": 150,
            "error": None,
        },
    },
}
```

### Session State

When `create_adk_reflection_fn()` creates a session, it sets:

```python
session_state = {
    "component_text": str,  # The text being evolved
    "trials": str,          # JSON-serialized list of trial records
}
```

**Note:** Data is passed in the user message, not via session state templating. The session state is maintained for potential future use.

## User Message Format

The reflection function sends data directly in the user message:

```python
user_message = f"""## Component Text to Improve
{component_text}

## Trials
{json.dumps(trials, indent=2)}

Propose an improved version of the component text based on the trials above.
Return ONLY the improved component text, nothing else."""
```

## Response Extraction

The `extract_final_output()` utility extracts text from ADK events:

```python
from gepa_adk.utils.events import extract_final_output

proposed_text = extract_final_output(events)
```

This utility:
- Filters `part.thought=True` content
- Handles empty responses gracefully
- Works with any ADK agent output format

## Terminology Reference

| Term | Description |
|------|-------------|
| `component_text` | Current text content being evolved |
| `trial` | Single performance record with feedback and trajectory |
| `trials` | Collection of trial records |
| `feedback` | Critic evaluation (score, text, guidance, dimensions) |
| `trajectory` | Execution journey (input, output, trace) |
| `trace` | Optional execution metadata (tool_calls, tokens, error) |

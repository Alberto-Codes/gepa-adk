# Quickstart: ADK Session State Template Substitution

**Branch**: `035-adk-session-template` | **Date**: 2026-01-18

## Overview

This guide shows how to use ADK's template substitution syntax (`{key}`) in reflection agent instructions to automatically inject session state values.

## Basic Usage

### 1. Define Agent with Template Placeholders

```python
from google.adk.agents import LlmAgent

# Use {key} placeholders that reference session state keys
reflection_agent = LlmAgent(
    name="Reflector",
    model="gemini-2.0-flash",
    instruction="""## Component Text to Improve
{component_text}

## Trial Results
{trials}

Analyze the trial results and propose an improved version of the component text.
Return ONLY the improved component text, nothing else.""",
)
```

### 2. Create Reflection Function

```python
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

# Factory handles session state setup automatically
reflection_fn = create_adk_reflection_fn(reflection_agent)
```

### 3. Call Reflection

```python
# Data passed to session state, then injected into instruction
improved_text = await reflection_fn(
    component_text="You are a helpful assistant.",
    trials=[
        {"feedback": "Too generic", "score": 0.5},
        {"feedback": "Needs more specificity", "score": 0.6},
    ],
)
```

## Template Syntax Reference

### Required Placeholders

```python
{key}  # Raises KeyError if key not in session state
```

**Example:**
```python
instruction = "Improve this: {component_text}"
# If session.state["component_text"] doesn't exist → KeyError
```

### Optional Placeholders

```python
{key?}  # Returns empty string if key not in session state
```

**Example:**
```python
instruction = "Context: {context?}\nImprove: {component_text}"
# If session.state["context"] doesn't exist → replaced with ""
```

### Supported Key Types

| Key Format | Example | Description |
|------------|---------|-------------|
| Simple | `{component_text}` | Standard session state lookup |
| Optional | `{component_text?}` | Empty string if missing |
| App-scoped | `{app:shared_config}` | Application-level state |
| User-scoped | `{user:preferences}` | User-level state |
| Temp-scoped | `{temp:scratch}` | Temporary session state |

## Type Handling

ADK converts all values to strings using `str()`. For complex types, pre-serialize:

```python
import json

# Good: Pre-serialize complex types
session_state = {
    "component_text": "You are a helpful assistant.",
    "trials": json.dumps(trials, indent=2),  # JSON string
}

# Bad: ADK will use repr() which may not be readable
session_state = {
    "trials": trials,  # dict → "{'feedback': 'Too generic', ...}"
}
```

## Migration from Manual Message Construction

### Before (Current Workaround)

```python
# Data embedded in user message via f-string
user_message = f"""## Component Text to Improve
{component_text}

## Trials
{json.dumps(trials, indent=2)}

Propose an improved version..."""

async for event in runner.run_async(
    user_id="reflection",
    session_id=session_id,
    new_message=Content(role="user", parts=[Part(text=user_message)]),
):
    events.append(event)
```

### After (Using Templates)

```python
# Data in session state, template in instruction
session_state = {
    "component_text": component_text,
    "trials": json.dumps(trials, indent=2),
}

# Agent instruction has placeholders
# instruction = "## Component Text to Improve\n{component_text}\n..."

# Simple trigger message
async for event in runner.run_async(
    user_id="reflection",
    session_id=session_id,
    new_message=Content(role="user", parts=[Part(text="Improve the component.")]),
):
    events.append(event)
```

## Error Handling

### Missing Required Key

```python
# Instruction uses {component_text} but state doesn't have it
session_state = {"trials": "..."}  # Missing component_text

# Result: KeyError("Context variable not found: `component_text`.")
```

### Invalid Key Name

```python
# Invalid Python identifier - placeholder left unchanged
instruction = "{my-invalid-key}"  # Hyphens not allowed
# Result: Literal "{my-invalid-key}" in instruction
```

### Empty Values

```python
# None values become empty strings
session_state = {"component_text": None}
# Result: Placeholder replaced with ""
```

## Testing Template Substitution

```python
import pytest
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService

@pytest.mark.asyncio
async def test_template_substitution():
    """Verify template placeholders are replaced with session state."""
    agent = LlmAgent(
        name="test",
        model="gemini-2.0-flash",
        instruction="Input: {test_value}",
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="test",
        user_id="test",
        session_id="test-session",
        state={"test_value": "hello world"},
    )

    # Run agent and verify instruction was processed correctly
    # (Implementation details depend on your test harness)
```

## Troubleshooting

### Placeholder Not Replaced

1. **Check key name**: Must be valid Python identifier (letters, numbers, underscores)
2. **Check session state**: Verify key exists in `session.state`
3. **Check spelling**: Key names are case-sensitive

### KeyError on Run

1. **Use optional syntax**: Change `{key}` to `{key?}` if value may be missing
2. **Check state initialization**: Ensure `create_session()` includes all required keys

### Unexpected String Format

1. **Pre-serialize complex types**: Use `json.dumps()` for dicts/lists
2. **Check value type**: `None` becomes `""`, not `"None"`

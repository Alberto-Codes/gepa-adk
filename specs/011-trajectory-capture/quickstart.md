# Quickstart: Trajectory Capture from ADK Sessions

**Feature**: 011-trajectory-capture  
**Date**: 2026-01-10

## Basic Usage

### Extract Trajectory with Default Config

```python
from gepa_adk.utils.events import extract_trajectory
from gepa_adk.domain.types import TrajectoryConfig

# Events collected from ADK runner
events: list[Event] = [...]

# Extract with all defaults (tool calls, state, tokens, redaction ON)
trajectory = extract_trajectory(
    events=events,
    final_output="Agent response text",
)

# Access trajectory data
print(f"Tool calls: {len(trajectory.tool_calls)}")
print(f"State changes: {len(trajectory.state_deltas)}")
print(f"Tokens used: {trajectory.token_usage.total_tokens if trajectory.token_usage else 'N/A'}")
```

### Custom Configuration

```python
from gepa_adk.domain.types import TrajectoryConfig

# Only capture tool calls, no redaction
config = TrajectoryConfig(
    include_tool_calls=True,
    include_state_deltas=False,
    include_token_usage=False,
    redact_sensitive=False,
)

trajectory = extract_trajectory(events=events, config=config)
```

### Custom Sensitive Keys

```python
# Redact additional fields
config = TrajectoryConfig(
    sensitive_keys=("password", "api_key", "token", "ssn", "credit_card"),
)

trajectory = extract_trajectory(events=events, config=config)
# All matching fields in tool args/state will show "[REDACTED]"
```

### Truncate Large Values (DOM, Screenshots)

```python
# Truncate strings longer than 5000 chars (useful for browser tools)
config = TrajectoryConfig(
    max_string_length=5000,  # Default is 10000
)

trajectory = extract_trajectory(events=events, config=config)
# Large tool results like DOM snapshots will show:
# "<html>...[truncated 45000 chars]"
```

### Disable Truncation

```python
# Keep full values (use with caution for memory)
config = TrajectoryConfig(
    max_string_length=None,  # No truncation
)
```

### Combined: Redaction + Truncation

```python
# Secure AND compact trajectories
config = TrajectoryConfig(
    redact_sensitive=True,
    sensitive_keys=("password", "api_key", "token", "secret"),
    max_string_length=8000,  # Trim verbose outputs
)

# Order: redaction first, then truncation
# Sensitive values become "[REDACTED]" (never truncated)
# Large non-sensitive values are truncated
```

---

## Integration with ADKAdapter

### Configure Adapter with Trajectory Settings

```python
from google.adk.agents import LlmAgent
from gepa_adk.adapters import ADKAdapter
from gepa_adk.domain.types import TrajectoryConfig

agent = LlmAgent(name="helper", model="gemini-2.5-flash", instruction="Be helpful")
scorer = MyScorer()

# Adapter with custom trajectory config
config = TrajectoryConfig(
    include_token_usage=True,
    redact_sensitive=True,
    sensitive_keys=("password", "api_key", "token", "secret"),
    max_string_length=10000,  # Truncate DOM/screenshots
)

adapter = ADKAdapter(
    agent=agent,
    scorer=scorer,
    trajectory_config=config,  # Applied to all evaluations
)

# Evaluate with trace capture
batch = [{"input": "What is 2+2?", "expected": "4"}]
result = await adapter.evaluate(batch, {"instruction": "Be precise"}, capture_traces=True)

# Trajectories use the configured settings
for trajectory in result.trajectories:
    print(trajectory.tool_calls)  # Sensitive args redacted, large values truncated
```

---

## Common Patterns

### Inspect Tool Calls

```python
for tool_call in trajectory.tool_calls:
    print(f"Tool: {tool_call.name}")
    print(f"Args: {tool_call.arguments}")
    print(f"Result: {tool_call.result}")
    print(f"Time: {tool_call.timestamp}s")
```

### Check for Errors

```python
if trajectory.error:
    print(f"Execution failed: {trajectory.error}")
else:
    print(f"Success: {trajectory.final_output[:100]}...")
```

### Aggregate Token Usage

```python
total_tokens = 0
for trajectory in trajectories:
    if trajectory.token_usage:
        total_tokens += trajectory.token_usage.total_tokens

print(f"Total tokens across all evaluations: {total_tokens}")
```

---

## Configuration Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `include_tool_calls` | `bool` | `True` | Extract function/tool call records |
| `include_state_deltas` | `bool` | `True` | Extract session state changes |
| `include_token_usage` | `bool` | `True` | Extract LLM token metrics |
| `redact_sensitive` | `bool` | `True` | Apply redaction to sensitive fields |
| `sensitive_keys` | `tuple[str, ...]` | `("password", "api_key", "token")` | Field names to redact |
| `max_string_length` | `int \| None` | `10000` | Truncate strings longer than this; None disables |

---

## Security & Performance Notes

1. **Secure by Default**: Redaction is ON by default. Explicitly set `redact_sensitive=False` to disable.

2. **Exact Matching**: Only exact key names are redacted. `"password"` matches `{"password": "..."}` but NOT `{"password_hash": "..."}`.

3. **Recursive**: Both redaction and truncation apply at all nesting levels in dicts and lists.

4. **Immutable Output**: Trajectories are frozen dataclasses. Original ADK events are never modified.

5. **Order of Operations**: Redaction runs BEFORE truncation. Sensitive values become `[REDACTED]` and are never truncated.

6. **Truncation Marker**: Truncated values end with `...[truncated N chars]` to indicate data loss and original size.

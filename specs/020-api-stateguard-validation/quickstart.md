# Quickstart: API StateGuard Validation

**Feature**: 020-api-stateguard-validation  
**Date**: January 13, 2026

## Overview

StateGuard protects ADK state injection tokens during instruction evolution. When you provide a `state_guard` parameter to `evolve()`, any missing required tokens are automatically repaired and unauthorized new tokens are escaped.

## Basic Usage

### Single Agent Evolution with StateGuard

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve
from gepa_adk.utils import StateGuard

# Create an agent with state tokens in the instruction
agent = LlmAgent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="Hello {user_id}, your context is: {context}",
    output_schema=MyOutputSchema,
)

# Configure StateGuard to protect required tokens
guard = StateGuard(required_tokens=["{user_id}", "{context}"])

# Evolve with state protection
result = await evolve(
    agent=agent,
    trainset=training_data,
    state_guard=guard,  # Tokens are protected!
)

# The evolved instruction is guaranteed to contain {user_id} and {context}
print(result.evolved_instruction)
```

### Synchronous Usage

```python
from gepa_adk import evolve_sync

# Same as async, but synchronous
result = evolve_sync(
    agent=agent,
    trainset=training_data,
    state_guard=StateGuard(required_tokens=["{user_id}"]),
)
```

## Multi-Agent Evolution

```python
from gepa_adk import evolve_group

# Protect tokens across all agents in the group
result = await evolve_group(
    agents=[generator, reviewer, validator],
    primary="validator",
    trainset=training_data,
    state_guard=StateGuard(required_tokens=["{session_id}"]),
)

# Each agent's evolved instruction is validated
for name, instruction in result.evolved_instructions.items():
    print(f"{name}: {instruction}")  # All contain {session_id} if originally present
```

## Workflow Evolution

```python
from google.adk.agents import SequentialAgent
from gepa_adk import evolve_workflow

pipeline = SequentialAgent(
    name="Pipeline",
    sub_agents=[agent1, agent2, agent3],
)

result = await evolve_workflow(
    workflow=pipeline,
    trainset=training_data,
    state_guard=StateGuard(required_tokens=["{user_id}", "{context}"]),
)
```

## Configuration Options

### Disable Token Repair

```python
# Only escape unauthorized tokens, don't repair missing ones
guard = StateGuard(
    required_tokens=["{user_id}"],
    repair_missing=False,
    escape_unauthorized=True,
)
```

### Disable Token Escaping

```python
# Only repair missing tokens, don't escape unauthorized ones
guard = StateGuard(
    required_tokens=["{user_id}"],
    repair_missing=True,
    escape_unauthorized=False,
)
```

### No StateGuard (Default Behavior)

```python
# Without state_guard, no token validation is applied
result = await evolve(agent=agent, trainset=data)  # state_guard defaults to None
```

## Token Formats Supported

StateGuard recognizes these ADK token formats:

| Format | Example | Description |
|--------|---------|-------------|
| Simple | `{user_id}` | Standard state variable |
| Prefixed | `{app:settings}` | Namespaced state variable |
| Optional | `{name?}` | ADK optional token (returns empty if not found) |
| Combined | `{app:config?}` | Namespaced optional token |

## What Happens Under the Hood

1. **Before evolution**: Original instruction is captured from `agent.instruction`
2. **During evolution**: Instruction is mutated by the LLM reflection agent
3. **After evolution**: If `state_guard` is provided:
   - Compare evolved instruction tokens against original
   - Repair any missing required tokens (append at end)
   - Escape any unauthorized new tokens (double braces)
4. **Return**: `EvolutionResult` with validated `evolved_instruction`

## Troubleshooting

### Token Not Being Repaired

**Symptom**: A token is missing from evolved instruction but not repaired.

**Causes**:
1. Token not in `required_tokens` list
2. Token not present in original instruction
3. `repair_missing=False` was set

**Solution**: Ensure token is in both the original instruction AND the `required_tokens` list.

### Token Being Escaped Unexpectedly

**Symptom**: A token like `{new_token}` becomes `{{new_token}}`.

**Cause**: The token was introduced by the LLM and is not in the original instruction.

**Solution**: If the token should be allowed, add it to `required_tokens`.

### No Effect When StateGuard Provided

**Symptom**: StateGuard has no visible effect.

**Cause**: The LLM preserved all required tokens correctly.

**Solution**: This is expected behavior! StateGuard only acts when needed.

# API Contract: StateGuard Integration

**Feature**: 020-api-stateguard-validation  
**Date**: January 13, 2026  
**Type**: Internal API

## Overview

This contract defines the integration of StateGuard into the public API functions.

## Function Signatures

### evolve()

```python
async def evolve(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    valset: list[dict[str, Any]] | None = None,
    critic: LlmAgent | None = None,
    reflection_agent: LlmAgent | None = None,
    config: EvolutionConfig | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    state_guard: StateGuard | None = None,  # <-- Type annotation updated
) -> EvolutionResult:
    ...
```

### evolve_sync()

```python
def evolve_sync(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    valset: list[dict[str, Any]] | None = None,
    critic: LlmAgent | None = None,
    reflection_agent: LlmAgent | None = None,
    config: EvolutionConfig | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    state_guard: StateGuard | None = None,  # <-- Type annotation updated
) -> EvolutionResult:
    ...
```

### evolve_group()

```python
async def evolve_group(
    agents: list[LlmAgent],
    primary: str,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    share_session: bool = True,
    config: EvolutionConfig | None = None,
    state_guard: StateGuard | None = None,  # <-- NEW parameter
) -> MultiAgentEvolutionResult:
    ...
```

### evolve_workflow()

```python
async def evolve_workflow(
    workflow: SequentialAgent | LoopAgent | ParallelAgent,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    primary: str | None = None,
    max_depth: int = 5,
    config: EvolutionConfig | None = None,
    state_guard: StateGuard | None = None,  # <-- NEW parameter
) -> MultiAgentEvolutionResult:
    ...
```

## Behavior Specification

### When `state_guard=None` (Default)

- No validation is performed
- Evolved instruction is returned unchanged
- Backward compatible with existing code

### When `state_guard` is Provided

1. **Capture original instruction(s)** at function entry
2. **Run evolution** normally
3. **Apply StateGuard validation** to final evolved instruction(s):
   ```python
   validated = state_guard.validate(original, evolved)
   ```
4. **Return result** with validated instruction(s)

### Logging Contract

When StateGuard modifies an instruction:

```python
logger.info(
    "evolve.state_guard.applied",
    agent_name="<agent_name>",
    instruction_modified=True,
)
```

When StateGuard validation produces no changes:

```python
logger.debug(
    "evolve.state_guard.no_changes",
    agent_name="<agent_name>",
)
```

## Test Cases

### TC-001: StateGuard Repairs Missing Token

**Input**:
- Original instruction: `"Hello {user_id}, context: {context}"`
- Evolved instruction: `"Hello there, context: {context}"` (missing `{user_id}`)
- StateGuard: `StateGuard(required_tokens=["{user_id}", "{context}"])`

**Expected Output**:
- Validated instruction: `"Hello there, context: {context}\n\n{user_id}"`

### TC-002: StateGuard Escapes Unauthorized Token

**Input**:
- Original instruction: `"Process for {user_id}"`
- Evolved instruction: `"Process for {user_id} with {malicious}"`
- StateGuard: `StateGuard(required_tokens=["{user_id}"])`

**Expected Output**:
- Validated instruction: `"Process for {user_id} with {{malicious}}"`

### TC-003: StateGuard No-Op When Tokens Preserved

**Input**:
- Original instruction: `"Hello {user_id}"`
- Evolved instruction: `"Greetings {user_id}"`
- StateGuard: `StateGuard(required_tokens=["{user_id}"])`

**Expected Output**:
- Validated instruction: `"Greetings {user_id}"` (unchanged)

### TC-004: StateGuard Disabled (None)

**Input**:
- Original instruction: `"Hello {user_id}"`
- Evolved instruction: `"Hello"` (missing `{user_id}`)
- StateGuard: `None`

**Expected Output**:
- Returned instruction: `"Hello"` (no validation applied)

### TC-005: Multi-Agent StateGuard Validation

**Input**:
- Agent A original: `"Process {session_id}"`
- Agent A evolved: `"Process"` (missing token)
- Agent B original: `"Review {session_id}"`
- Agent B evolved: `"Review {session_id}"` (token preserved)
- StateGuard: `StateGuard(required_tokens=["{session_id}"])`

**Expected Output**:
- Agent A validated: `"Process\n\n{session_id}"`
- Agent B validated: `"Review {session_id}"` (unchanged)

### TC-006: repair_missing=False Disables Repair

**Input**:
- Original instruction: `"Hello {user_id}"`
- Evolved instruction: `"Hello"`
- StateGuard: `StateGuard(required_tokens=["{user_id}"], repair_missing=False)`

**Expected Output**:
- Validated instruction: `"Hello"` (repair disabled)

### TC-007: escape_unauthorized=False Disables Escape

**Input**:
- Original instruction: `"Process {user_id}"`
- Evolved instruction: `"Process {user_id} {new_token}"`
- StateGuard: `StateGuard(required_tokens=["{user_id}"], escape_unauthorized=False)`

**Expected Output**:
- Validated instruction: `"Process {user_id} {new_token}"` (escape disabled)

# API Contract Changes: Wire ADK Reflection Agent into evolve() API

**Feature Branch**: `021-adk-reflection-evolve`
**Date**: 2026-01-14

## Overview

This feature modifies the behavior of an existing parameter without changing the public API signature. No breaking changes.

## evolve() Function

### Current Signature (No Change)

```python
async def evolve(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    valset: list[dict[str, Any]] | None = None,
    critic: LlmAgent | None = None,
    reflection_agent: LlmAgent | None = None,  # <-- Now functional
    config: EvolutionConfig | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    state_guard: StateGuard | None = None,
) -> EvolutionResult
```

### Parameter Behavior Change

| Parameter | Before | After |
|-----------|--------|-------|
| `reflection_agent` | Ignored with warning | Used for ADK-based reflection |

### Behavior Matrix

| reflection_agent | critic | Reflection Method | Scoring Method |
|------------------|--------|-------------------|----------------|
| None | None | LiteLLM | Schema scoring |
| None | LlmAgent | LiteLLM | Critic agent |
| LlmAgent | None | ADK Runner | Schema scoring |
| LlmAgent | LlmAgent | ADK Runner | Critic agent |

### Error Conditions

| Condition | Error Type | Message |
|-----------|------------|---------|
| `reflection_agent` not LlmAgent | `TypeError` | "reflection_agent must be LlmAgent, got {type}" |
| reflection agent returns non-string | `EvolutionError` | "Reflection agent must return a string, got {type}." |
| reflection agent returns empty string | `EvolutionError` | "Reflection agent returned empty string. Expected non-empty string with improved instruction." |
| reflection agent raises exception | `EvolutionError` | "Reflection agent raised exception: {ErrorType}: {message}" |

## ADKAdapter.__init__() (Internal)

### New Signature

```python
def __init__(
    self,
    agent: LlmAgent,
    scorer: Scorer,
    max_concurrent_evals: int = 5,
    session_service: BaseSessionService | None = None,
    app_name: str = "gepa_adk_eval",
    trajectory_config: TrajectoryConfig | None = None,
    proposer: AsyncReflectiveMutationProposer | None = None,
    reflection_agent: LlmAgent | None = None,  # <-- NEW PARAMETER
) -> None
```

### Parameter Details

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `reflection_agent` | `LlmAgent \| None` | `None` | Optional ADK agent for reflection. If provided, creates `adk_reflection_fn` for proposer. |

### Precedence Rules

If both `proposer` and `reflection_agent` are provided:
- `proposer` takes precedence (user explicitly configured proposer)
- `reflection_agent` is ignored with warning log

## Logging Changes

### Removed

```python
# BEFORE (api.py:842-846)
logger.warning(
    "evolve.reflection_agent.not_implemented",
    agent_name=agent.name,
    message="reflection_agent not yet implemented, using default proposer",
)
```

### Added

```python
# NEW (api.py)
logger.debug(
    "evolve.reflection_agent.configured",
    agent_name=agent.name,
    reflection_agent_name=reflection_agent.name,
)
```

## Backward Compatibility

| Scenario | Compatible | Notes |
|----------|------------|-------|
| Calling `evolve()` without `reflection_agent` | Yes | Uses LiteLLM (unchanged) |
| Calling `evolve()` with `reflection_agent` | Yes | Now uses ADK (was ignored) |
| Existing code relying on warning log | No | Warning removed; code checking for this log will not find it |

## Example Usage

### With Custom Reflection Agent

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve

# Configure reflection agent with custom prompt
reflection_agent = LlmAgent(
    name="instructor",
    model="gemini-2.5-flash",
    instruction="""Improve this instruction based on feedback:

Current instruction: {current_instruction}

Feedback: {execution_feedback}

Return only the improved instruction text.""",
)

# Evolve with ADK reflection
result = await evolve(
    agent=my_agent,
    trainset=trainset,
    reflection_agent=reflection_agent,
)
```

### Default Behavior (Unchanged)

```python
# Still works with LiteLLM reflection
result = await evolve(agent=my_agent, trainset=trainset)
```

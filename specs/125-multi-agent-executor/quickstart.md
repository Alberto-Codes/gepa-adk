# Quickstart: Multi-Agent Unified Executor

**Feature**: 125-multi-agent-executor
**Date**: 2026-01-19

## Overview

This feature ensures all multi-agent evolution scenarios use the unified `AgentExecutor` for consistent session management and feature parity with single-agent evolution.

## Usage Examples

### Basic Multi-Agent Evolution (Existing API)

No changes needed for existing callers. The executor is created internally.

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve_group
from gepa_adk.adapters.critic_scorer import CriticOutput

# Define agents
generator = LlmAgent(
    name="generator",
    model="gemini-2.5-flash",
    instruction="Generate a response to the user's question.",
    output_key="generated_response",
)

validator = LlmAgent(
    name="validator",
    model="gemini-2.5-flash",
    instruction="Validate the response in {generated_response}.",
)

# Define critic for scoring
critic = LlmAgent(
    name="quality_critic",
    model="gemini-2.5-flash",
    instruction="Score the quality of the validation.",
    output_schema=CriticOutput,
)

# Training data
trainset = [
    {"input": "What is Python?", "expected": "A programming language"},
    {"input": "What is 2+2?", "expected": "4"},
]

# Evolve - executor is created automatically (FR-003)
result = await evolve_group(
    agents=[generator, validator],
    primary="validator",
    trainset=trainset,
    critic=critic,
)

print(f"Best score: {result.best_score}")
print(f"Generator instruction: {result.evolved_components['generator_instruction']}")
print(f"Validator instruction: {result.evolved_components['validator_instruction']}")
```

### With Custom MultiAgentAdapter (Advanced)

For advanced use cases, you can provide an executor directly.

```python
from gepa_adk.adapters.agent_executor import AgentExecutor
from gepa_adk.adapters.multi_agent import MultiAgentAdapter
from gepa_adk.adapters.critic_scorer import CriticScorer

# Create shared executor
executor = AgentExecutor()

# Create scorer with executor
scorer = CriticScorer(critic_agent=critic, executor=executor)

# Create adapter with executor (FR-001, FR-002)
adapter = MultiAgentAdapter(
    agents=[generator, validator],
    primary="validator",
    scorer=scorer,
    executor=executor,  # All agents use this executor
)

# Evaluate with unified execution
batch = [{"input": "What is Python?", "expected": "A programming language"}]
candidate = {
    "generator_instruction": "Generate a helpful response.",
    "validator_instruction": "Validate thoroughly.",
}

result = await adapter.evaluate(batch, candidate)
```

### Workflow Evolution (Automatic Support)

Workflow evolution inherits executor support automatically (FR-007).

```python
from google.adk.agents import LlmAgent, SequentialAgent
from gepa_adk import evolve_workflow

# Define workflow agents
step1 = LlmAgent(
    name="step1",
    model="gemini-2.5-flash",
    instruction="Process the input.",
    output_key="step1_output",
)

step2 = LlmAgent(
    name="step2",
    model="gemini-2.5-flash",
    instruction="Refine based on {step1_output}.",
)

# Create workflow
workflow = SequentialAgent(
    name="my_workflow",
    sub_agents=[step1, step2],
)

# Evolve - uses unified executor internally
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    critic=critic,
)
```

## Verification

### Check Executor Usage in Logs

All agent executions should show `uses_executor=True`:

```python
import structlog
structlog.configure(
    processors=[structlog.dev.ConsoleRenderer()],
)

# Run evolution
result = await evolve_group(...)

# Logs will show:
# adapter.evaluate.start uses_executor=True ...
# scorer.async_score.start uses_executor=True ...
# reflection.start uses_executor=True ...
```

### Test Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| `evolve_group()` with critic | Critic uses executor (FR-005) |
| `evolve_group()` with reflection_agent | Reflection uses executor (FR-006) |
| `evolve_workflow()` | Inherits executor from `evolve_group()` (FR-007) |
| `MultiAgentAdapter(executor=None)` | Falls back to legacy execution (FR-009) |
| Log inspection | All entries show `uses_executor=True` (FR-008) |

## Migration Guide

### For Existing Code

**No changes required.** All existing `evolve_group()` and `evolve_workflow()` calls continue to work. The executor is created internally.

### For Custom Adapters

If you're using `MultiAgentAdapter` directly, you can optionally pass an executor:

```python
# Before (still works)
adapter = MultiAgentAdapter(agents=agents, primary=primary, scorer=scorer)

# After (recommended for consistency)
executor = AgentExecutor()
adapter = MultiAgentAdapter(
    agents=agents,
    primary=primary,
    scorer=CriticScorer(critic_agent=critic, executor=executor),
    executor=executor,
)
```

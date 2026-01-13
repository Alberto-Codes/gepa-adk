# Quickstart: Public API (evolve, evolve_sync)

**Feature**: 018-public-api  
**Date**: 2026-01-12

## Installation

```bash
# The gepa-adk package (already installed if you're using the library)
uv add gepa-adk
```

## Basic Usage

### Async Context (Recommended)

```python
import asyncio
from google.adk.agents import LlmAgent
from gepa_adk import evolve

# Create your agent (must have output_schema for schema-based scoring)
from pydantic import BaseModel, Field

class OutputSchema(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    result: str

agent = LlmAgent(
    name="assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant.",
    output_schema=OutputSchema,  # Required for schema-based scoring
)

# Define training examples
trainset = [
    {"input": "What is 2+2?", "expected": "4"},
    {"input": "What is the capital of France?", "expected": "Paris"},
]

# Evolve the agent's instruction
async def main():
    result = await evolve(agent, trainset)
    
    print(f"Original score: {result.original_score:.2f}")
    print(f"Final score: {result.final_score:.2f}")
    print(f"Evolved instruction:\n{result.evolved_instruction}")

asyncio.run(main())
```

### Synchronous Context (Scripts & Notebooks)

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve_sync

# Create agent with output_schema (or provide a critic)
from pydantic import BaseModel, Field

class OutputSchema(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    result: str

agent = LlmAgent(
    name="assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant.",
    output_schema=OutputSchema,  # Required for schema-based scoring
)

trainset = [
    {"input": "Explain quantum computing", "expected": "A clear explanation..."},
]

# Works in scripts, Jupyter notebooks, and any sync context
result = evolve_sync(agent, trainset)

print(f"Improvement: {result.improvement:.2%}")
print(f"Evolved: {result.evolved_instruction}")
```

## Configuration Options

### Custom Evolution Settings

```python
from gepa_adk import evolve, EvolutionConfig

config = EvolutionConfig(
    max_iterations=100,      # More iterations for better results
    patience=10,             # Stop after 10 iterations without improvement
    min_improvement_threshold=0.02,  # Only accept 2%+ improvements
)

result = await evolve(agent, trainset, config=config)
```

### Using a Critic Agent for Scoring

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve
from pydantic import BaseModel

class CriticOutput(BaseModel):
    score: float
    feedback: str

critic = LlmAgent(
    name="critic",
    model="gemini-2.0-flash",
    instruction="Score the response quality from 0 to 1.",
    output_schema=CriticOutput,
)

result = await evolve(
    agent=agent,
    trainset=trainset,
    critic=critic,  # Use LLM-based scoring
)
```

### Validation Dataset

```python
trainset = [{"input": "...", "expected": "..."} for _ in range(80)]
valset = [{"input": "...", "expected": "..."} for _ in range(20)]

result = await evolve(
    agent=agent,
    trainset=trainset,
    valset=valset,  # Evaluate on held-out data
)
```

### Trajectory Capture

```python
from gepa_adk import evolve, TrajectoryConfig

trajectory_config = TrajectoryConfig(
    redact_sensitive=True,
    max_string_length=5000,
)

result = await evolve(
    agent=agent,
    trainset=trainset,
    trajectory_config=trajectory_config,
)
```

## Analyzing Results

```python
result = await evolve(agent, trainset)

# Basic metrics
print(f"Started at: {result.original_score:.2f}")
print(f"Ended at: {result.final_score:.2f}")
print(f"Improvement: {result.improvement:.2%}")
print(f"Did improve: {result.improved}")

# Iteration history
for record in result.iteration_history:
    status = "✓" if record.accepted else "✗"
    print(f"  {status} Iteration {record.iteration_number}: {record.score:.2f}")

# Apply the evolved instruction
agent.instruction = result.evolved_instruction
```

## API Reference

### `evolve()`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent` | `LlmAgent` | *required* | Agent to evolve |
| `trainset` | `list[dict]` | *required* | Training examples |
| `valset` | `list[dict] \| None` | `None` | Validation examples |
| `critic` | `LlmAgent \| None` | `None` | Scoring agent |
| `reflection_agent` | `LlmAgent \| None` | `None` | Proposal agent |
| `config` | `EvolutionConfig \| None` | `None` | Settings |
| `trajectory_config` | `TrajectoryConfig \| None` | `None` | Trace settings |
| `state_guard` | `StateGuard \| None` | `None` | Token preservation |

**Returns**: `EvolutionResult`

### `evolve_sync()`

Same parameters as `evolve()`, but runs synchronously.

## See Also

- [`evolve_group()`](../016-wire-adapters-proposer/quickstart.md) - Evolve multiple agents together
- [`evolve_workflow()`](../017-workflow-evolution/quickstart.md) - Evolve workflow agents

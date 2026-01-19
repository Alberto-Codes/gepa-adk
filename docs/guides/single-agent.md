# Single-Agent Evolution

This guide covers basic agent <evolution:evolution> patterns for optimizing a single LlmAgent.

!!! tip "Working Examples Available"
    For complete, runnable examples, see:

    - **[examples/basic_evolution.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/basic_evolution.py)** — Uses Ollama with critic scoring
    - **[Getting Started Guide](../getting-started.md)** — Step-by-step walkthrough

    The examples below use Gemini for illustration, but Ollama (`gpt-oss:20b`) is required for the evolution engine.

## When to Use This Pattern

Use single-agent evolution when:

- You have one agent that needs optimization
- The agent can self-assess its output quality (providing <trial:feedback>)
- You want straightforward instruction improvement

## Prerequisites

- Python 3.12+
- gepa-adk installed (`uv add gepa-adk`)
- GEMINI_API_KEY environment variable set

## Basic Evolution

### Step 1: Define Output Schema with Score

The agent needs a structured output with a `score` field for self-assessment:

```python
from pydantic import BaseModel, Field


class TaskOutput(BaseModel):
    """Structured output with self-assessment."""

    result: str
    reasoning: str
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Self-assessed quality score (0.0-1.0)",
    )
```

### Step 2: Create the Agent

```python
from google.adk.agents import LlmAgent

agent = LlmAgent(
    name="task-agent",
    model="gemini-2.0-flash",
    instruction="""You are a task assistant. When given a task:
1. Complete the task to the best of your ability
2. Explain your reasoning
3. Honestly assess the quality of your response (0.0-1.0)""",
    output_schema=TaskOutput,
)
```

### Step 3: Prepare Training Data

Create examples that represent your use case:

```python
trainset = [
    {"input": "Summarize: The quick brown fox jumps over the lazy dog."},
    {"input": "Summarize: Python is a programming language."},
    {"input": "Summarize: Machine learning uses data to find patterns."},
]
```

### Step 4: Run Evolution

```python
from gepa_adk import evolve_sync, EvolutionConfig

config = EvolutionConfig(
    max_iterations=20,
    patience=5,
)

result = evolve_sync(agent, trainset, config=config)
print(f"Improvement: {result.improvement:.2%}")
print(f"Evolved instruction:\n{result.evolved_instruction}")  # evolved_component_text
```

## Complete Working Example

```python
"""Single-agent evolution example."""

import os
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from gepa_adk import evolve_sync, EvolutionConfig


class SummaryOutput(BaseModel):
    summary: str
    key_points: list[str]
    score: float = Field(ge=0.0, le=1.0)


def main() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("Set GEMINI_API_KEY environment variable")

    agent = LlmAgent(
        name="summarizer",
        model="gemini-2.0-flash",
        instruction="Summarize the given text concisely.",
        output_schema=SummaryOutput,
    )

    trainset = [
        {"input": "The quick brown fox jumps over the lazy dog."},
        {"input": "Python is a high-level programming language."},
        {"input": "Machine learning finds patterns in data."},
        {"input": "The weather today is sunny with a chance of rain."},
        {"input": "Artificial intelligence is transforming industries."},
    ]

    config = EvolutionConfig(max_iterations=20, patience=5)
    result = evolve_sync(agent, trainset, config=config)

    print(f"Original score: {result.original_score:.3f}")
    print(f"Final score: {result.final_score:.3f}")
    print(f"Improvement: {result.improvement:.2%}")
    print(f"\nEvolved instruction:\n{result.evolved_instruction}")


if __name__ == "__main__":
    main()
```

## Common Patterns and Tips

### Using Validation Sets

Split your data for more robust optimization:

```python
trainset = examples[:8]  # 80% for training
valset = examples[8:]    # 20% for validation

result = evolve_sync(agent, trainset, valset=valset, config=config)
print(f"Training score: {result.trainset_score:.3f}")
print(f"Validation score: {result.valset_score:.3f}")
```

### Custom Evolution Configuration

Fine-tune evolution parameters:

```python
config = EvolutionConfig(
    max_iterations=50,     # More iterations for complex tasks
    patience=10,           # More patience for slower convergence
    fitness_threshold=0.95,  # Stop early if threshold reached
)
```

### Async Evolution

For better performance in async contexts:

```python
import asyncio
from gepa_adk import evolve

async def run_evolution():
    result = await evolve(agent, trainset, config=config)
    return result

result = asyncio.run(run_evolution())
```

## Output Schema Evolution

In addition to evolving instructions, gepa-adk can evolve the **output schema** itself.
This is useful when you want to optimize the structure of your agent's responses.

### Why Evolve Output Schemas?

- **Optimize field definitions** — Improve descriptions and constraints
- **Refine data structure** — Let evolution find better field organization
- **Co-evolve with instructions** — Optimize both together for best results

### Serialization and Deserialization

Output schemas are Pydantic BaseModel classes. To evolve them, gepa-adk serializes
the class to Python source code, evolves the text, then deserializes it back.

```python
from gepa_adk.utils.schema_utils import (
    serialize_pydantic_schema,
    deserialize_schema,
)

# Serialize a schema to text
schema_text = serialize_pydantic_schema(TaskOutput)

# After evolution, deserialize back to a usable class
EvolvedOutput = deserialize_schema(evolved_schema_text)

# Apply to agent
agent.output_schema = EvolvedOutput
```

### Evolving Output Schema

Specify `components=["output_schema"]` to evolve the schema:

```python
from gepa_adk import evolve_sync, EvolutionConfig

result = evolve_sync(
    agent,
    trainset,
    components=["output_schema"],  # Target schema for evolution
    config=EvolutionConfig(max_iterations=20, patience=5),
)

# Get evolved schema text
print(result.evolved_component_text)
```

### Evolving Both Instruction and Schema

You can evolve multiple components simultaneously:

```python
result = evolve_sync(
    agent,
    trainset,
    components=["instruction", "output_schema"],
    config=config,
)
```

### Schema Validation

Evolved schemas are validated before acceptance to ensure:

- **Valid Python syntax** — Must parse without errors
- **BaseModel inheritance** — Must be a Pydantic model
- **Security** — No import statements or function definitions allowed
- **Self-contained** — All types must be available in the execution namespace

Invalid schema proposals are automatically rejected, and evolution continues
with the previous best candidate.

### Using Evolved Schemas

After evolution completes:

```python
from gepa_adk.utils.schema_utils import deserialize_schema

# Deserialize the evolved schema
EvolvedSchema = deserialize_schema(result.evolved_component_text)

# Create a new agent with the evolved schema
evolved_agent = LlmAgent(
    name="evolved-agent",
    model="gemini-2.0-flash",
    instruction=agent.instruction,
    output_schema=EvolvedSchema,
)
```

## Related Guides

- [Critic Agents](critic-agents.md) — Use external critics for scoring
- [Multi-Agent](multi-agent.md) — Evolve multiple agents together
- [Workflows](workflows.md) — Optimize agent pipelines

## API Reference

- [`evolve()`][gepa_adk.evolve] — Async evolution function
- [`evolve_sync()`][gepa_adk.evolve_sync] — Synchronous wrapper
- [`EvolutionConfig`][gepa_adk.EvolutionConfig] — Configuration options
- [`EvolutionResult`][gepa_adk.EvolutionResult] — Evolution results
- [`serialize_pydantic_schema()`][gepa_adk.utils.serialize_pydantic_schema] — Schema serialization
- [`deserialize_schema()`][gepa_adk.utils.deserialize_schema] — Schema deserialization
- [`validate_schema_text()`][gepa_adk.utils.validate_schema_text] — Schema validation

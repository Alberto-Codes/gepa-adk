# Single-Agent Evolution

This guide covers basic agent evolution patterns for optimizing a single LlmAgent.

!!! tip "Working Examples"
    Complete runnable examples:

    - **[examples/basic_evolution.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/basic_evolution.py)** — Greeting agent with critic
    - **[examples/critic_agent.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/critic_agent.py)** — Story generation with critic

## When to Use This Pattern

Use single-agent evolution when:

- You have one agent that needs instruction optimization
- You can define clear scoring criteria via a critic agent
- You want straightforward instruction improvement

## Prerequisites

- Python 3.12+
- gepa-adk installed (`uv add gepa-adk`)
- Ollama running locally with a model (e.g., `llama3.2:latest`)
- `OLLAMA_API_BASE` environment variable set

```bash
export OLLAMA_API_BASE=http://localhost:11434
```

## Basic Evolution with Critic

The standard pattern uses a **critic agent** to score the evolved agent's outputs.

### Step 1: Create the Agent to Evolve

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

agent = LlmAgent(
    name="greeter",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Greet the user appropriately based on their introduction.",
)
```

### Step 2: Create a Critic Agent

The critic evaluates outputs and provides scores. Use `SimpleCriticOutput` for basic scoring:

```python
from gepa_adk import SimpleCriticOutput

critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Score for formal, Dickens-style greetings. 0.0-1.0.",
    output_schema=SimpleCriticOutput,
)
```

Or define a custom critic schema for richer feedback:

```python
from pydantic import BaseModel, Field

class CriticOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str

critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="""Evaluate greeting quality. Look for formal, elaborate,
Dickens-style greetings appropriate for the social context.
Score 0.0-1.0 where 1.0 is a perfect formal greeting.""",
    output_schema=CriticOutput,
)
```

### Step 3: Prepare Training Data

```python
trainset = [
    {"input": "I am His Majesty, the King."},
    {"input": "I am your mother."},
    {"input": "I am a close friend."},
]
```

### Step 4: Run Evolution

```python
from gepa_adk import evolve, run_sync, EvolutionConfig

config = EvolutionConfig(
    max_iterations=5,
    patience=2,
    reflection_model="ollama_chat/llama3.2:latest",
)

result = run_sync(evolve(agent, trainset, critic=critic, config=config))

print(f"Original score: {result.original_score:.3f}")
print(f"Final score: {result.final_score:.3f}")
print(f"Improvement: {result.improvement:.2%}")
print(f"Evolved instruction:\n{result.evolved_components['instruction']}")
```

## Complete Working Example

```python
"""Single-agent evolution with critic scoring."""

import asyncio
import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel, Field

from gepa_adk import evolve, EvolutionConfig


class CriticOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str


async def main() -> None:
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("Set OLLAMA_API_BASE environment variable")

    agent = LlmAgent(
        name="greeter",
        model=LiteLlm(model="ollama_chat/llama3.2:latest"),
        instruction="Greet the user appropriately.",
    )

    critic = LlmAgent(
        name="critic",
        model=LiteLlm(model="ollama_chat/llama3.2:latest"),
        instruction="""Evaluate greeting quality. Look for formal, Dickens-style
greetings appropriate for the social context. Score 0.0-1.0.""",
        output_schema=CriticOutput,
    )

    trainset = [
        {"input": "I am His Majesty, the King."},
        {"input": "I am your mother."},
        {"input": "I am a close friend."},
    ]

    config = EvolutionConfig(
        max_iterations=5,
        patience=2,
        reflection_model="ollama_chat/llama3.2:latest",
    )

    result = await evolve(agent, trainset, critic=critic, config=config)

    print(f"Original: {result.original_score:.3f}")
    print(f"Final: {result.final_score:.3f}")
    print(f"Improvement: {result.improvement:.2%}")
    print(f"\nEvolved instruction:\n{result.evolved_components['instruction']}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration Options

### EvolutionConfig Parameters

```python
from gepa_adk import EvolutionConfig

config = EvolutionConfig(
    max_iterations=20,          # Maximum evolution iterations
    patience=5,                 # Stop after N iterations without improvement
    reflection_model="ollama_chat/llama3.2:latest",  # Model for generating improvements
    min_improvement_threshold=0.01,  # Minimum score gain to accept
)
```

### Using Validation Sets

Split data for more robust optimization:

```python
# Given a larger dataset of examples
examples = [
    {"input": "I am the Mayor."},
    {"input": "I am your neighbor."},
    {"input": "I am a stranger."},
    {"input": "I am the postman."},
    {"input": "I am a visiting dignitary."},
    {"input": "I am your teacher."},
    {"input": "I am the shopkeeper."},
    {"input": "I am a lost traveler."},
    {"input": "I am your cousin."},
    {"input": "I am the village elder."},
]

trainset = examples[:8]   # 80% for training
valset = examples[8:]     # 20% for validation

result = run_sync(evolve(agent, trainset, valset=valset, critic=critic, config=config))
```

### Stop Callbacks

Add custom stopping conditions:

```python
from gepa_adk.adapters.stoppers import ScoreThresholdStopper

config = EvolutionConfig(
    max_iterations=50,
    patience=10,
    reflection_model="ollama_chat/llama3.2:latest",
    stop_callbacks=[ScoreThresholdStopper(0.95)],  # Stop at 95% score
)
```

See the [Stop Callbacks Guide](stoppers.md) for more options.

### Async vs Sync

Use `evolve()` for async contexts, `run_sync(evolve(...))` for scripts:

```python
# Async
result = await evolve(agent, trainset, critic=critic, config=config)

# Sync (wraps async internally)
result = run_sync(evolve(agent, trainset, critic=critic, config=config))
```

## Advanced: Output Schema Evolution

You can evolve the agent's **output schema** in addition to instructions.

### When to Use

- Optimize field definitions and descriptions
- Refine data structure for better outputs
- Co-evolve instruction and schema together

### Example

```python
from pydantic import BaseModel, Field

class TaskOutput(BaseModel):
    result: str
    confidence: float = Field(ge=0.0, le=1.0)

agent = LlmAgent(
    name="task-agent",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Complete the task.",
    output_schema=TaskOutput,
)

# Evolve just the output schema
result = run_sync(evolve(
    agent,
    trainset,
    critic=critic,
    components=["output_schema"],
    config=config,
))

print(result.evolved_components["output_schema"])
```

### Evolving Both

```python
result = run_sync(evolve(
    agent,
    trainset,
    critic=critic,
    components=["instruction", "output_schema"],
    config=config,
))
```

### Using Evolved Schemas

```python
from gepa_adk.utils.schema_utils import deserialize_schema

EvolvedSchema = deserialize_schema(result.evolved_components["output_schema"])

evolved_agent = LlmAgent(
    name="evolved-agent",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction=result.evolved_components["instruction"],
    output_schema=EvolvedSchema,
)
```

## Advanced: Generation Config Evolution

Evolve LLM parameters like temperature and top_p.

### Example

```python
from google.genai.types import GenerateContentConfig

agent = LlmAgent(
    name="creative-agent",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Write creatively.",
    generate_content_config=GenerateContentConfig(
        temperature=0.7,
        top_p=0.9,
    ),
)

result = run_sync(evolve(
    agent,
    trainset,
    critic=critic,
    components=["generate_content_config"],
    config=config,
))

print(result.evolved_components["generate_content_config"])
```

## Related Guides

- [Critic Agents](critic-agents.md) — Detailed critic patterns
- [Multi-Agent](multi-agent.md) — Evolve multiple agents together
- [Workflows](workflows.md) — Optimize agent pipelines

## API Reference

- [`evolve()`][gepa_adk.api.evolve] — Async evolution
- [`run_sync()`][gepa_adk.api.run_sync] — Sync wrapper for async evolution
- [`EvolutionConfig`][gepa_adk.domain.models.EvolutionConfig] — Configuration
- [`EvolutionResult`][gepa_adk.domain.models.EvolutionResult] — Results

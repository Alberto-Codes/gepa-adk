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
    model="gemini-2.5-flash",
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
print(f"Evolved instruction:\n{result.evolved_components["instruction"]}")
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
        model="gemini-2.5-flash",
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
    print(f"\nEvolved instruction:\n{result.evolved_components["instruction"]}")


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

!!! tip "Stop Callbacks"
    For advanced termination control (API cost limits, external orchestration, etc.),
    see the [Stop Callbacks Guide](stoppers.md).

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

### Using App/Runner for Infrastructure Integration

If you have an existing ADK application with configured services (session storage,
artifact storage), you can pass your `Runner` instance to evolution. The evolution
engine will use your runner's `session_service` for all operations:

```python
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

# SQLite for local development (persists to file)
session_service = DatabaseSessionService(db_url="sqlite+aiosqlite:///evolution.db")

# Or PostgreSQL for production
# session_service = DatabaseSessionService(db_url="postgresql+asyncpg://user:pass@host/db")

runner = Runner(
    app_name="my_app",
    agent=agent,
    session_service=session_service,
)

# Initialize tables before concurrent operations
await session_service.list_sessions(app_name="my_app")

# Evolution uses your runner's session_service
result = await evolve(
    agent,
    trainset,
    runner=runner,  # Services extracted from runner
)
```

This enables seamless integration with existing ADK infrastructure without
duplicating configuration. All agents during evolution (evolved agent, critic,
reflection agent) share the same session service.

!!! example "Full Example"
    See [`examples/app_runner_integration.py`](https://github.com/google/gepa-adk/blob/HEAD/examples/app_runner_integration.py)
    for a complete example with SQLite persistence.

!!! tip "Backward Compatible"
    The `app` and `runner` parameters are optional. Existing code continues
    to work unchanged, using the default `InMemorySessionService`.

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
print(result.evolved_components["output_schema"])
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

### Validated Schema Reflection

When evolving `output_schema` components, gepa-adk automatically uses a specialized
reflection agent equipped with a validation tool. This agent can self-validate
proposed schemas before returning them, reducing wasted evolution iterations.

**How It Works:**

1. Component-aware agent selection detects `output_schema` evolution
2. A schema reflection agent is created with the `validate_output_schema` tool
3. The agent validates proposals and self-corrects errors before returning
4. Only syntactically valid schemas reach the evolution engine

**Benefits:**

- **Fewer invalid proposals** — Validation tool catches syntax errors early
- **Faster convergence** — No wasted iterations on unparseable schemas
- **Self-correction** — Agent can fix simple errors without human intervention
- **Zero configuration** — Works automatically when evolving output_schema

**Example:**

```python
from gepa_adk import evolve_sync, EvolutionConfig
from gepa_adk.engine.reflection_agents import create_schema_reflection_agent

# Create a schema reflection agent with validation tool
schema_agent = create_schema_reflection_agent(model="gemini-2.5-flash")

# Use it for evolution - the agent will validate proposed schemas
result = evolve_sync(
    agent,
    trainset,
    reflection_agent=schema_agent,
    config=EvolutionConfig(max_iterations=20, patience=5),
)

# The reflection agent used validation tools during evolution
# All returned proposals are guaranteed to be syntactically valid
```

**Note:** The feature automatically selects appropriate reflection agents when
the proposer evolves different components (e.g., instruction vs output_schema).
To manually control which reflection agent is used, pass it via the
`reflection_agent` parameter as shown above.

**Technical Details:**

The validation agent uses the `validate_output_schema` tool from
`gepa_adk.utils.schema_tools`. This tool checks:

- Python syntax validity (AST parsing)
- BaseModel inheritance
- Field definitions and type hints
- Security constraints (no imports/exec)

You can use component-aware reflection manually if needed:

```python
from gepa_adk.engine.reflection_agents import get_reflection_agent

# Get schema reflection agent with validation tool
schema_agent = get_reflection_agent("output_schema", model="gemini-2.5-flash")

# Or get basic text reflection agent
text_agent = get_reflection_agent("instruction", model="gemini-2.5-flash")
```

### Using Evolved Schemas

After evolution completes:

```python
from gepa_adk.utils.schema_utils import deserialize_schema

# Deserialize the evolved schema
EvolvedSchema = deserialize_schema(result.evolved_components["output_schema"])

# Create a new agent with the evolved schema
evolved_agent = LlmAgent(
    name="evolved-agent",
    model="gemini-2.5-flash",
    instruction=agent.instruction,
    output_schema=EvolvedSchema,
)
```

## Generation Config Evolution

In addition to evolving instructions and output schemas, gepa-adk can evolve the
**LLM generation configuration** parameters like temperature, top_p, and sampling settings.

### Why Evolve Generation Config?

- **Optimize creativity vs. consistency** — Find the right temperature for your task
- **Tune sampling parameters** — Discover optimal top_p/top_k for your use case
- **Task-specific tuning** — Different tasks benefit from different parameter combinations
- **Data-driven optimization** — Let evolution find parameters that improve task scores

### Evolvable Parameters

The following parameters can be evolved:

| Parameter | Range | Description |
|-----------|-------|-------------|
| `temperature` | 0.0 - 2.0 | Controls randomness (0.0=deterministic, 2.0=creative) |
| `top_p` | 0.0 - 1.0 | Nucleus sampling threshold |
| `top_k` | > 0 | Top-k sampling (higher=more diverse) |
| `max_output_tokens` | > 0 | Maximum response length |
| `presence_penalty` | -2.0 - 2.0 | Penalizes repeated topics |
| `frequency_penalty` | -2.0 - 2.0 | Penalizes repeated tokens |

### Evolving Generation Config

Specify `components=["generate_content_config"]` to evolve the config:

```python
from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig
from gepa_adk import evolve_sync, EvolutionConfig

# Create agent with initial config
agent = LlmAgent(
    name="task-agent",
    model="gemini-2.5-flash",
    instruction="Complete the given task.",
    output_schema=TaskOutput,
    generate_content_config=GenerateContentConfig(
        temperature=0.7,
        top_p=0.9,
    ),
)

# Evolve the generation config
result = evolve_sync(
    agent,
    trainset,
    components=["generate_content_config"],
    config=EvolutionConfig(max_iterations=20, patience=5),
)

# View evolved config (YAML format)
print(result.evolved_components["generate_content_config"])
```

### Evolving Multiple Components

You can evolve generation config together with instruction and/or output schema:

```python
result = evolve_sync(
    agent,
    trainset,
    components=["instruction", "generate_content_config"],
    config=config,
)
```

### Config Validation

Proposed config changes are validated before acceptance:

- **Range constraints** — Parameters must be within valid ranges
- **Type checking** — Values must be numeric
- **Graceful rejection** — Invalid proposals are rejected, evolution continues

Invalid config proposals are automatically rejected with a warning log, and the
previous best candidate is retained.

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

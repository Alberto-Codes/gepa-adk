# Multi-Agent Evolution

This guide covers evolving multiple agents working together in a pipeline, allowing them to co-evolve and improve their coordination.

!!! tip "Working Example"
    Complete runnable example:

    - **[examples/multi_agent.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/multi_agent.py)** — Two-generator pipeline with secret scoring criteria

## When to Use Multi-Agent Evolution

Use `evolve_group()` when:

- Multiple agents collaborate in a pipeline
- Output from one agent feeds into another (via `output_key`)
- You want coordinated improvement across all agents
- Agents share session state during execution

## Prerequisites

- Python 3.12+
- gepa-adk installed (`uv add gepa-adk`)
- Ollama running locally
- `OLLAMA_API_BASE` environment variable set

## Basic Multi-Agent Pattern

### Step 1: Create Pipeline Agents

Each agent in the pipeline uses `output_key` to save output to session state, which downstream agents can access via template placeholders:

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

# Generator 1: Creates initial content
generator1 = LlmAgent(
    name="generator1",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Answer the user's question with a clear, informative response.",
    output_key="gen1_output",  # Saved to session.state["gen1_output"]
)

# Generator 2: Expands on Generator 1's output
generator2 = LlmAgent(
    name="generator2",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction=(
        "You received this initial response:\n"
        "{gen1_output}\n\n"  # Accesses Generator 1's output
        "Rewrite and expand this into a richer response."
    ),
    output_key="gen2_output",  # Final pipeline output
)

# Bundle as dict (required in v0.3+)
pipeline_agents = {
    "generator1": generator1,
    "generator2": generator2,
}
```

### Step 2: Create Critic and Reflection Agents

```python
from gepa_adk import CriticOutput

# Critic: Scores pipeline output (NOT evolved)
critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Score the writing quality. 0.0-1.0.",
    output_schema=CriticOutput,
)

# Reflection: Improves instructions based on feedback
reflection_agent = LlmAgent(
    name="reflector",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction=(
        "## Current Instruction\n"
        "{component_text}\n\n"
        "## Trial Results\n"
        "{trials}\n\n"
        "Write an improved instruction. Return ONLY the instruction text."
    ),
    output_key="proposed_component_text",
)
```

### Step 3: Run Evolution

```python
from gepa_adk import evolve_group, EvolutionConfig

trainset = [
    {"input": "What does it feel like to be truly exhausted?"},
    {"input": "Describe a moment when everything went wrong."},
]

config = EvolutionConfig(
    max_iterations=4,
    patience=2,
)

result = await evolve_group(
    agents=pipeline_agents,
    primary="generator2",  # Score final agent's output
    trainset=trainset,
    critic=critic,
    reflection_agent=reflection_agent,
    config=config,
)

# Access evolved instructions via qualified names
print(result.evolved_components["generator1.instruction"])
print(result.evolved_components["generator2.instruction"])
```

## Per-Agent Component Configuration

Control which components to evolve for each agent:

```python
components = {
    "generator1": ["instruction"],  # Evolve instruction only
    "generator2": ["instruction"],  # Evolve instruction only
    "validator": [],                # Exclude from evolution
}

result = await evolve_group(
    agents=pipeline_agents,
    primary="generator2",
    trainset=trainset,
    critic=critic,
    components=components,
)
```

### Available Components

- `"instruction"` - The agent's instruction text
- `"output_schema"` - The agent's Pydantic output schema
- `"generate_content_config"` - The agent's generation configuration

### Excluding Agents from Evolution

Use an empty list to exclude an agent while keeping it in the pipeline:

```python
components = {
    "generator": ["instruction"],
    "validator": [],  # Participates but isn't evolved
}
```

## Qualified Component Names

Evolved components use qualified names in `agent.component` format per ADR-012:

```python
# Access via qualified names
generator1_instruction = result.evolved_components["generator1.instruction"]
generator2_instruction = result.evolved_components["generator2.instruction"]

# Iterate over all evolved components
for qualified_name, value in result.evolved_components.items():
    agent_name, component = qualified_name.split(".")
    print(f"{agent_name}: {component}")
```

## Round-Robin Iteration Tracking

The engine uses round-robin to select which agent's instruction to improve each iteration:

```python
result = await evolve_group(
    agents=pipeline_agents,
    primary="generator2",
    trainset=trainset,
    critic=critic,
    config=EvolutionConfig(max_iterations=4),
)

# Inspect which component was evolved each iteration
for record in result.iteration_history:
    print(f"Iteration {record.iteration_number}:")
    print(f"  Evolved: {record.evolved_component}")
    print(f"  Score: {record.score:.3f}")
    print(f"  Accepted: {record.accepted}")
```

With two agents and 4 iterations:

```
Iteration 1: Evolved: generator1.instruction
Iteration 2: Evolved: generator2.instruction
Iteration 3: Evolved: generator1.instruction
Iteration 4: Evolved: generator2.instruction
```

## Reflection Agent Configuration

The reflection agent must use `{component_text}` and `{trials}` template placeholders. ADK substitutes these from session state:

```python
reflection_agent = LlmAgent(
    name="reflector",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction=(
        "## Current Instruction\n"
        "{component_text}\n\n"
        "## Trial Results\n"
        "{trials}\n\n"
        "Based on the trial results, write an improved instruction.\n"
        "Return ONLY the improved instruction text."
    ),
    output_key="proposed_component_text",
)
```

!!! tip "Clean Output"
    Add "Return ONLY the improved instruction" to prevent reasoning text in the output.

## Alternative: Use reflection_model

Instead of a custom reflection agent, use `reflection_model` in config:

```python
config = EvolutionConfig(
    max_iterations=4,
    patience=2,
    reflection_model="ollama_chat/llama3.2:latest",
)

result = await evolve_group(
    agents=pipeline_agents,
    primary="generator2",
    trainset=trainset,
    critic=critic,
    config=config,  # Uses built-in reflection with specified model
)
```

## Unified Executor (Advanced)

`evolve_group()` automatically creates a unified `AgentExecutor` for consistent session management:

- **Consistent session management** across all agents
- **Automatic timeout handling** for all agent types
- **Event capture** without manual session service management

```python
# Executor is created and managed automatically
result = await evolve_group(
    agents=pipeline_agents,
    primary="generator2",
    trainset=trainset,
    critic=critic,
    reflection_agent=reflection_agent,
)
# All agents use the same executor
```

### Manual Executor Usage

For advanced use cases with explicit executor:

```python
from google.adk.sessions import InMemorySessionService
from gepa_adk.adapters import AgentExecutor, MultiAgentAdapter

session_service = InMemorySessionService()
executor = AgentExecutor(session_service=session_service)

adapter = MultiAgentAdapter(
    agents=pipeline_agents,
    primary="generator2",
    components={"generator1": ["instruction"], "generator2": ["instruction"]},
    scorer=my_scorer,
    proposer=my_proposer,
    executor=executor,
)
```

## App/Runner Infrastructure Integration

For existing ADK applications with configured services:

```python
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

# SQLite for local development
session_service = DatabaseSessionService(db_url="sqlite+aiosqlite:///evolution.db")

runner = Runner(
    app_name="my_pipeline",
    agent=pipeline_agent,
    session_service=session_service,
)

# Initialize tables before concurrent operations
await session_service.list_sessions(app_name="my_pipeline")

# Evolution uses your runner's session_service
result = await evolve_group(
    agents=pipeline_agents,
    primary="generator2",
    trainset=trainset,
    runner=runner,
)
```

### Service Precedence

1. **`runner`** - If provided, runner's services are used
2. **`app`** - If provided (without runner), uses app's configuration
3. **`session_service`** - Direct parameter when no runner/app
4. **Default** - Creates `InMemorySessionService`

!!! tip "Backward Compatible"
    The `app` and `runner` parameters are optional. Existing code continues to work unchanged.

## Migration Guide (v0.2 → v0.3)

### Breaking Changes

**1. `agents` parameter changed from list to dict**

```python
# v0.2 (OLD)
agents = [generator1, generator2]
result = await evolve_group(agents=agents, ...)

# v0.3 (NEW)
agents = {"generator1": generator1, "generator2": generator2}
result = await evolve_group(agents=agents, ...)
```

**2. `evolved_components` uses qualified names**

```python
# v0.2 (OLD)
result.evolved_components["generator1"]

# v0.3 (NEW)
result.evolved_components["generator1.instruction"]
```

**3. New `components` parameter for per-agent control**

```python
# v0.3 - Per-agent component configuration
result = await evolve_group(
    agents=agents,
    components={
        "generator1": ["instruction"],
        "generator2": ["instruction"],
    },
)
```

## Related Guides

- [Single-Agent](single-agent.md) — Basic evolution patterns
- [Critic Agents](critic-agents.md) — Custom scoring with critic agents
- [Workflows](workflows.md) — Evolve workflow agents (Sequential, Loop, Parallel)

## API Reference

- [`evolve_group()`][gepa_adk.api.evolve_group] — Multi-agent evolution
- [`MultiAgentEvolutionResult`][gepa_adk.domain.MultiAgentEvolutionResult] — Result type
- [`EvolutionConfig`][gepa_adk.domain.EvolutionConfig] — Configuration options
- [`CriticOutput`][gepa_adk.adapters.critic_scorer.CriticOutput] — Critic schema

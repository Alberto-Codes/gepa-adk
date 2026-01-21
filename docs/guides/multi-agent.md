# Multi-Agent Evolution

Multi-agent <evolution:evolution> optimizes multiple agents working together in a pipeline, allowing them to co-evolve and improve their coordination.

## Quick Start

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve_group, EvolutionConfig

# Create agents as a dict mapping names to LlmAgent instances
agents = {
    "generator": LlmAgent(
        name="generator",
        model="gemini-2.0-flash",
        instruction="Generate a Python function.",
        output_key="generated_code",
    ),
    "reviewer": LlmAgent(
        name="reviewer",
        model="gemini-2.0-flash",
        instruction="Review the code: {generated_code}",
        output_schema=ReviewOutput,  # For scoring
    ),
}

# Evolve the pipeline
result = await evolve_group(
    agents=agents,
    primary="reviewer",  # Agent whose output is scored
    trainset=trainset,
)

# Access evolved instructions via qualified names
print(result.evolved_components["generator.instruction"])
print(result.evolved_components["reviewer.instruction"])
```

## Per-Agent Component Configuration

Starting in v0.3, you can configure which components to evolve for each agent:

```python
# Configure per-agent components
components = {
    "generator": ["instruction"],  # Evolve generator's instruction
    "reviewer": ["instruction"],   # Evolve reviewer's instruction
    "validator": [],               # Exclude validator from evolution
}

result = await evolve_group(
    agents=agents,
    primary="reviewer",
    trainset=trainset,
    components=components,  # Per-agent configuration
)
```

### Available Components

- `"instruction"` - The agent's instruction text
- `"output_schema"` - The agent's Pydantic output schema
- `"generate_content_config"` - The agent's generation configuration

### Excluding Agents from Evolution

Use an empty list to exclude an agent from evolution while keeping it in the pipeline:

```python
components = {
    "generator": ["instruction"],
    "reviewer": [],  # Reviewer participates but isn't evolved
}
```

## Qualified Component Names

Evolved components use qualified names in `agent.component` format per ADR-012:

```python
result = await evolve_group(
    agents={"generator": gen, "reviewer": rev},
    primary="reviewer",
    trainset=trainset,
)

# Access via qualified names
generator_instruction = result.evolved_components["generator.instruction"]
reviewer_instruction = result.evolved_components["reviewer.instruction"]

# Iterate over all evolved components
for qualified_name, value in result.evolved_components.items():
    agent_name, component = qualified_name.split(".")
    print(f"{agent_name}: {component} = {value[:50]}...")
```

## Migration Guide (v0.2 → v0.3)

### Breaking Changes

**1. `agents` parameter changed from list to dict**

```python
# v0.2 (OLD)
agents = [generator, reviewer]
result = await evolve_group(
    agents=agents,  # list[LlmAgent]
    primary="reviewer",
    trainset=trainset,
)

# v0.3 (NEW)
agents = {"generator": generator, "reviewer": reviewer}
result = await evolve_group(
    agents=agents,  # dict[str, LlmAgent]
    primary="reviewer",
    trainset=trainset,
)
```

**2. `evolved_components` uses qualified names**

```python
# v0.2 (OLD)
generator_instruction = result.evolved_components["generator"]
reviewer_instruction = result.evolved_components["reviewer"]

# v0.3 (NEW)
generator_instruction = result.evolved_components["generator.instruction"]
reviewer_instruction = result.evolved_components["reviewer.instruction"]
```

**3. New `components` parameter**

```python
# v0.2 - All agents evolved the same components
result = await evolve_group(agents=agents, ...)

# v0.3 - Per-agent component configuration
result = await evolve_group(
    agents=agents,
    components={
        "generator": ["instruction"],
        "reviewer": ["instruction"],
    },
    ...
)
```

### Migration Steps

1. Convert agent lists to dicts:
   ```python
   # Before
   agents = [agent1, agent2]

   # After
   agents = {agent1.name: agent1, agent2.name: agent2}
   ```

2. Update `evolved_components` access to use qualified names:
   ```python
   # Before
   result.evolved_components["agent_name"]

   # After
   result.evolved_components["agent_name.instruction"]
   ```

3. Optionally add `components` parameter for per-agent control.

## Reflection Agents with Ollama

When using a <evolution:reflection> agent with Ollama, add explicit output guidance so the
extracted instruction is clean.

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve_group

reflection_agent = LlmAgent(
    name="reflector",
    model="ollama_chat/llama3.1:latest",
    instruction=(
        "Improve the instruction using the feedback.\n"
        "Return ONLY the improved instruction."
    ),
)

result = await evolve_group(
    agents={"generator": generator, "reviewer": reviewer, "validator": validator},
    primary="validator",
    trainset=trainset,
    reflection_agent=reflection_agent,
)
```

## Troubleshooting Reflection Output

- If the reflection output still includes reasoning, add a stronger instruction
  like "Return ONLY the improved instruction."

## <abbr:ADK> vs LiteLLM Reflection Paths

<abbr:GEPA> uses the <abbr:ADK> reflection path when a `reflection_agent` is provided.

!!! warning "Deprecation Notice"
    The LiteLLM fallback path is **deprecated** and will be removed in a future version. Always provide a `reflection_agent` for consistent execution. See [Issue #144](https://github.com/Alberto-Codes/gepa-adk/issues/144).

## Logging Guide for Reflection Debugging

Look for these structured logs:

- `proposer.reflection_path` with `method=adk` or `method=litellm`
- `reflection.start` and `reflection.complete` for ADK reflection operations
- `proposal.text` to see the proposed instruction text

## Round-Robin Iteration Tracking

When multiple agents are evolved together, the engine uses a round-robin strategy to select which agent's instruction to improve in each iteration. The `iteration_history` tracks which component was evolved:

```python
result = await evolve_group(
    agents={"generator": generator, "reviewer": reviewer},
    primary="reviewer",
    trainset=trainset,
    config=EvolutionConfig(max_iterations=4),
)

# Inspect which component was evolved each iteration
for record in result.iteration_history:
    print(f"Iteration {record.iteration_number}:")
    print(f"  Evolved: {record.evolved_component}")
    print(f"  Score: {record.score:.3f}")
    print(f"  Accepted: {record.accepted}")
```

With two agents and 4 iterations, the output might show:

```
Iteration 1: Evolved: generator.instruction
Iteration 2: Evolved: reviewer.instruction
Iteration 3: Evolved: generator.instruction
Iteration 4: Evolved: reviewer.instruction
```

## Unified Executor (Advanced)

When using `evolve_group()`, a unified `AgentExecutor` (from [`gepa_adk.adapters`](../reference/gepa_adk/adapters/index.md)) is automatically created to manage all agent executions consistently. This provides:

- **Consistent session management** across generator, critic, and reflection agents
- **Automatic timeout handling** for all agent types
- **Event capture** without manual session service management
- **Unified logging** with `uses_executor=True` field for observability

### How It Works

The executor is created automatically and passed to all components:

```python
from gepa_adk import evolve_group

# Executor is created and managed automatically
result = await evolve_group(
    agents={"generator": generator, "critic": critic},
    primary="generator",
    trainset=trainset,
    critic=critic_agent,
    reflection_agent=reflection_agent,
)
# All agents (generator, critic, reflection) use the same executor
```

### Manual Executor Usage (Advanced)

For advanced use cases, you can create a `MultiAgentAdapter` with an explicit executor:

```python
from google.adk.sessions import InMemorySessionService
from gepa_adk.adapters.agent_executor import AgentExecutor
from gepa_adk.adapters.multi_agent import MultiAgentAdapter

# Create session service and executor
session_service = InMemorySessionService()
executor = AgentExecutor(session_service=session_service)

# Pass executor to adapter
adapter = MultiAgentAdapter(
    agents={"generator": generator, "critic": critic},
    primary="generator",
    components={"generator": ["instruction"], "critic": ["instruction"]},
    scorer=my_scorer,
    proposer=my_proposer,
    executor=executor,  # Optional: enables unified execution path
)
```

When `executor=None` (default for `MultiAgentAdapter`), the adapter uses its legacy execution path for backward compatibility.

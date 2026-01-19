# Multi-Agent Evolution

!!! warning "Coming Soon"
    This guide is under development. Multi-agent evolution support is available in the API but documentation is in progress.

In the meantime:

- See the [Getting Started Guide](../getting-started.md) for basic usage with single agents
- Check the [Single-Agent Guide](single-agent.md) for foundational patterns
- Check the [Critic Agents Guide](critic-agents.md) for scoring patterns
- Review the [API Reference](../reference/) for `evolve_group()` documentation

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
    agents=[generator, reviewer, validator],
    primary="validator",
    trainset=trainset,
    reflection_agent=reflection_agent,
)
```

## Troubleshooting Reflection Output

- If the reflection output still includes reasoning, add a stronger instruction
  like "Return ONLY the improved instruction."

## <abbr:ADK> vs LiteLLM Reflection Paths

<abbr:GEPA> uses the <abbr:ADK> reflection path when a `reflection_agent` is provided. If no
reflection agent is configured, it falls back to LiteLLM-based <evolution:reflection>.

## Logging Guide for Reflection Debugging

Look for these structured logs:

- `proposer.reflection_path` with `method=adk` or `method=litellm`
- `reflection.start` and `reflection.complete` for ADK reflection operations
- `proposal.text` to see the proposed instruction text

## What is Multi-Agent Evolution?

Multi-agent <evolution:evolution> optimizes multiple agents working together in a pipeline, allowing them to co-evolve and improve their coordination.

**Status**: API available, full documentation coming soon.

## Accessing Evolved Components

After evolution completes, access each agent's evolved instruction via the `evolved_components` dictionary:

```python
result = await evolve_group(
    agents=[generator, reviewer, validator],
    primary="validator",
    trainset=trainset,
)

# Access evolved instructions by agent name
print(result.evolved_components["generator"])
print(result.evolved_components["reviewer"])
print(result.evolved_components["validator"])

# Iterate over all evolved components
for agent_name, instruction in result.evolved_components.items():
    print(f"{agent_name}: {instruction[:50]}...")
```

The `evolved_components` dict contains all agent instructions, not just those that changed during evolution.

## Round-Robin Iteration Tracking

When multiple agents are evolved together, the engine uses a round-robin strategy to select which agent's instruction to improve in each iteration. The `iteration_history` tracks which component was evolved:

```python
result = await evolve_group(
    agents=[generator, reviewer],
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
Iteration 1: Evolved: generator_instruction
Iteration 2: Evolved: reviewer_instruction
Iteration 3: Evolved: generator_instruction
Iteration 4: Evolved: reviewer_instruction
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
    agents=[generator, critic],
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
    agents=[generator, critic],
    primary="generator",
    scorer=my_scorer,
    executor=executor,  # Optional: enables unified execution path
)
```

When `executor=None` (default for `MultiAgentAdapter`), the adapter uses its legacy execution path for backward compatibility.

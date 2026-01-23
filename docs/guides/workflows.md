# Workflow Evolution

!!! warning "Coming Soon"
    This guide is under development. Workflow evolution support is available in the API but documentation is in progress.

In the meantime:

- See the [Getting Started Guide](../getting-started.md) for basic usage
- Check the [Single-Agent Guide](single-agent.md) for foundational patterns
- Check the [Critic Agents Guide](critic-agents.md) for scoring patterns
- Review the [API Reference](../reference/index.md) for `evolve_workflow()` documentation

## What is Workflow Evolution?

Workflow <evolution:evolution> optimizes agents within <abbr:ADK> workflow structures (like `SequentialAgent`), preserving the workflow configuration while improving agent instructions.

**Status**: API available, full documentation coming soon.

## Unified Executor Support

`evolve_workflow()` automatically benefits from unified executor support by delegating to [`evolve_group()`](multi-agent.md#unified-executor-advanced). This means:

- All agents within your workflow (SequentialAgent, LoopAgent, ParallelAgent) use consistent session management
- Automatic timeout handling and event capture work seamlessly across the workflow
- You get the same observability and logging benefits as multi-agent evolution

```python
from google.adk.agents import LlmAgent, SequentialAgent
from gepa_adk import evolve_workflow

# Create workflow
agent1 = LlmAgent(name="generator", instruction="Generate code")
agent2 = LlmAgent(name="reviewer", instruction="Review code")
workflow = SequentialAgent(name="Pipeline", sub_agents=[agent1, agent2])

# Executor is created and used automatically
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
)
```

The unified `AgentExecutor` (from [`gepa_adk.adapters`](../reference/gepa_adk/adapters/index.md)) is created internally by `evolve_group()`, so all workflow agents execute through the same executor for consistent behavior.

## Evolution Strategies

### Default: First Agent Only

By default, `evolve_workflow()` evolves only the first discovered agent's instruction across all iterations. This focuses optimization on the source agent, letting downstream agents benefit from improved input.

```python
from google.adk.agents import LlmAgent, SequentialAgent
from gepa_adk import evolve_workflow

# Create workflow with three agents
generator = LlmAgent(name="generator", instruction="Generate content")
refiner = LlmAgent(name="refiner", instruction="Refine content")
writer = LlmAgent(name="writer", instruction="Write docs")
workflow = SequentialAgent(name="Pipeline", sub_agents=[generator, refiner, writer])

# Default: only generator.instruction evolves across all iterations
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
)
```

### Round-Robin: Evolve All Agents

Use `round_robin=True` to evolve all agents in the workflow, cycling through them each iteration. This ensures all agents get equal opportunities to improve.

```python
from gepa_adk import evolve_workflow, EvolutionConfig

# Evolve all agents in round-robin: generator -> refiner -> writer -> generator -> ...
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    round_robin=True,
    config=EvolutionConfig(max_iterations=6),  # 2 iterations per agent
)

# Check which component was evolved each iteration
for record in result.iteration_history:
    print(f"Iter {record.iteration_number}: {record.evolved_component} -> {record.score:.3f}")
```

### Explicit Components Override

For fine-grained control, use the `components` parameter to specify exactly which agents to evolve. This takes precedence over `round_robin`.

```python
# Only evolve generator and writer; exclude refiner
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    components={
        "generator": ["instruction"],
        "writer": ["instruction"],
        "refiner": [],  # Excluded from evolution
    },
)
```

Use an empty list `[]` to exclude an agent from evolution while still including it in the workflow execution.

## Accessing All Evolved Instructions

After evolution completes, access each agent's final instruction from `evolved_components`:

```python
# Get evolved instructions for all workflow agents
for agent_name, instruction in result.evolved_components.items():
    print(f"{agent_name}:\n{instruction}\n")
```

## Generation Config Evolution

Workflow evolution also supports evolving LLM generation configuration parameters (temperature, top_p, etc.) alongside instructions. This allows you to optimize both what the agent says and how creatively it responds.

```python
from gepa_adk import evolve_workflow, EvolutionConfig

# Evolve both instructions and config for all workflow agents
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    components=["instruction", "generate_content_config"],
    config=EvolutionConfig(max_iterations=10),
)

# Access evolved config (YAML format)
if "generate_content_config" in result.evolved_components:
    print(result.evolved_components["generate_content_config"])
```

For more details on config evolution, see the [Single-Agent Guide](single-agent.md#generation-config-evolution).

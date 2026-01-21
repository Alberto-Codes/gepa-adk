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

## Round-Robin Component Evolution

When evolving a workflow with multiple LlmAgents, GEPA uses a round-robin strategy to select which agent's instruction to evolve each iteration. This ensures all agents get equal opportunities to improve.

```python
from google.adk.agents import LlmAgent, SequentialAgent
from gepa_adk import evolve_workflow, EvolutionConfig

# Create workflow with two agents
generator = LlmAgent(name="generator", instruction="Generate content")
refiner = LlmAgent(name="refiner", instruction="Refine content")
workflow = SequentialAgent(name="Pipeline", sub_agents=[generator, refiner])

# Evolve with enough iterations to observe round-robin
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    config=EvolutionConfig(max_iterations=6),  # 3 iterations per agent
)

# Check which component was evolved each iteration
for record in result.iteration_history:
    print(f"Iter {record.iteration_number}: {record.evolved_component} -> {record.score:.3f}")
```

The `evolved_component` field in each iteration record shows which agent's instruction was targeted for improvement. With round-robin selection:

- Iteration 1: `generator_instruction`
- Iteration 2: `refiner_instruction`
- Iteration 3: `generator_instruction`
- ...and so on

This helps understand which agent improvements contributed most to score gains.

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

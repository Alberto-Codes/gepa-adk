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

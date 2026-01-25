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

# Evolve both instructions and config for specific agents
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    components={
        "generator": ["instruction", "generate_content_config"],
        "refiner": ["instruction"],  # Only instruction for this agent
    },
    config=EvolutionConfig(max_iterations=10),
)

# Access evolved config (YAML format)
if "generator.generate_content_config" in result.evolved_components:
    print(result.evolved_components["generator.generate_content_config"])
```

For more details on config evolution, see the [Single-Agent Guide](single-agent.md#generation-config-evolution).

## Workflow Structure Preservation

`evolve_workflow()` preserves the original workflow structure during evolution. This means that LoopAgent, ParallelAgent, and nested workflows execute as designed rather than being flattened to a simple sequential pipeline.

### LoopAgent Iteration Preservation

When you use a `LoopAgent`, the `max_iterations` configuration is preserved during evolution. This enables iterative refinement workflows where agents improve their output through multiple passes.

```python
from google.adk.agents import LlmAgent, LoopAgent
from gepa_adk import evolve_workflow, EvolutionConfig

# Create an iterative refinement loop
refiner = LlmAgent(
    name="refiner",
    model="gemini-2.5-flash",
    instruction="Review and improve the code. Focus on clarity and efficiency.",
    output_key="refined_code",
)

# LoopAgent executes the inner agent 3 times per evaluation
refinement_loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[refiner],
    max_iterations=3,  # This is preserved during evolution!
)

# Evolve the refiner's instruction
result = await evolve_workflow(
    workflow=refinement_loop,
    trainset=trainset,
    config=EvolutionConfig(max_iterations=5),
)

# The evolved instruction benefits from 3-pass refinement during each evaluation
print(result.evolved_components["refiner.instruction"])
```

**Key points:**

- The `max_iterations` value is preserved when cloning the workflow for each evaluation
- Each training example is processed through all loop iterations
- The final iteration's output is used for scoring
- All iteration outputs are captured in the execution trajectory

### Multi-Agent LoopAgent Workflows

LoopAgents can contain multiple sub-agents that execute together in each iteration:

```python
from google.adk.agents import LlmAgent, LoopAgent
from gepa_adk import evolve_workflow

# Create critic-refine loop
critic = LlmAgent(
    name="critic",
    instruction="Analyze the code and identify areas for improvement.",
    output_key="feedback",
)
refiner = LlmAgent(
    name="refiner",
    instruction="Improve the code based on {feedback}.",
    output_key="refined_code",
)

# Both agents run in sequence for each of 3 iterations
refinement_loop = LoopAgent(
    name="CriticRefineLoop",
    sub_agents=[critic, refiner],
    max_iterations=3,
)

# Evolve both agents with round-robin
result = await evolve_workflow(
    workflow=refinement_loop,
    trainset=trainset,
    round_robin=True,  # Evolve critic and refiner in turn
)
```

### ParallelAgent Concurrent Execution

When you use a `ParallelAgent`, the concurrent execution semantics are preserved during evolution. This means sub-agents execute in parallel rather than being flattened into sequential execution.

```python
from google.adk.agents import LlmAgent, ParallelAgent
from gepa_adk import evolve_workflow, EvolutionConfig

# Create parallel research branches
researcher1 = LlmAgent(
    name="researcher1",
    model="gemini-2.5-flash",
    instruction="Research the historical context.",
    output_key="historical_context",
)
researcher2 = LlmAgent(
    name="researcher2",
    model="gemini-2.5-flash",
    instruction="Research current trends.",
    output_key="current_trends",
)
researcher3 = LlmAgent(
    name="researcher3",
    model="gemini-2.5-flash",
    instruction="Research future predictions.",
    output_key="future_predictions",
)

# All researchers execute concurrently
parallel_research = ParallelAgent(
    name="ParallelResearch",
    sub_agents=[researcher1, researcher2, researcher3],
)

# Evolve all branches with round-robin
result = await evolve_workflow(
    workflow=parallel_research,
    trainset=trainset,
    round_robin=True,
    config=EvolutionConfig(max_iterations=6),  # 2 iterations per researcher
)
```

**Key points:**

- The `ParallelAgent` type is preserved when cloning the workflow for each evaluation
- ADK Runner executes all sub_agents concurrently (not sequentially)
- Each sub-agent's output is available in session state via its `output_key`
- All parallel outputs are captured in the execution trajectory

### Nested Workflow Structure Preservation

Complex workflows that combine SequentialAgent, ParallelAgent, and LoopAgent are fully supported. The entire structure is preserved during evolution, regardless of nesting depth.

```python
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from gepa_adk import evolve_workflow, EvolutionConfig

# Create a complex nested workflow:
# Sequential([Parallel([Loop([Refiner]), Researcher]), Synthesizer])

# Level 3: Inner refiner in a loop
refiner = LlmAgent(
    name="refiner",
    model="gemini-2.5-flash",
    instruction="Refine the analysis iteratively.",
    output_key="refined_analysis",
)

# Level 2: Loop for iterative refinement
refinement_loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[refiner],
    max_iterations=3,  # Preserved during evolution!
)

# Level 2: Parallel researcher
researcher = LlmAgent(
    name="researcher",
    model="gemini-2.5-flash",
    instruction="Research background information.",
    output_key="research",
)

# Level 1: Parallel stage with loop and researcher
parallel_stage = ParallelAgent(
    name="ParallelAnalysis",
    sub_agents=[refinement_loop, researcher],
)

# Level 1: Synthesizer that combines all outputs
synthesizer = LlmAgent(
    name="synthesizer",
    model="gemini-2.5-flash",
    instruction="Synthesize {refined_analysis} with {research}.",
    output_key="final_output",
)

# Level 0: Root sequential workflow
workflow = SequentialAgent(
    name="ComplexPipeline",
    sub_agents=[parallel_stage, synthesizer],
)

# All structure is preserved:
# - LoopAgent runs 3 iterations
# - ParallelAgent branches execute concurrently
# - SequentialAgent maintains order
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    round_robin=True,
    config=EvolutionConfig(max_iterations=6),
)
```

**Key points:**

- Nested workflows of arbitrary depth are supported
- Each agent type (Sequential, Loop, Parallel) maintains its semantics
- Instruction overrides are applied to LlmAgents at any nesting level
- The workflow structure is cloned recursively with all properties preserved

## App/Runner Infrastructure Integration

If you have an existing ADK application with configured services (session storage,
database backends), you can pass your `Runner` instance to `evolve_workflow()`.
This enables seamless integration with your production infrastructure:

```python
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

# SQLite for local development
session_service = DatabaseSessionService(db_url="sqlite+aiosqlite:///evolution.db")

# Or PostgreSQL for production
# session_service = DatabaseSessionService(db_url="postgresql+asyncpg://user:pass@host/db")

runner = Runner(
    app_name="my_workflow_app",
    agent=workflow,
    session_service=session_service,
)

# Initialize tables before concurrent operations
await session_service.list_sessions(app_name="my_workflow_app")

# Evolution uses your runner's session_service for all operations
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    runner=runner,  # Services extracted from runner
)
```

All agents during workflow evolution (evolved agents, critic, reflection agent)
share the same session service extracted from your runner.

!!! example "Full Example"
    See [`examples/app_runner_integration.py`](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/app_runner_integration.py)
    for a complete example with SQLite persistence.

!!! tip "Backward Compatible"
    The `app` and `runner` parameters are optional. Existing code continues
    to work unchanged, using the default `InMemorySessionService`.

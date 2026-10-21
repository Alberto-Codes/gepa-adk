# Workflow Evolution

This guide covers evolving agents within ADK workflow structures (SequentialAgent, LoopAgent, ParallelAgent), preserving the workflow configuration while improving agent instructions.

!!! tip "Working Example"
    Complete runnable example:

    - **[examples/nested_workflow_evolution.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/nested_workflow_evolution.py)** — Complex nested workflow with structure preservation

## When to Use Workflow Evolution

Use `evolve_workflow()` when:

- Agents are organized in ADK workflow structures (Sequential, Loop, Parallel)
- You want to preserve workflow configuration (loop iterations, parallel branches)
- The workflow structure should remain intact while instructions improve

## Prerequisites

- Python 3.12+
- gepa-adk installed (`uv add gepa-adk`)
- Ollama running locally
- `OLLAMA_API_BASE` environment variable set

## Basic Workflow Pattern

### Step 1: Create Workflow Agents

```python
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from gepa_adk import CriticOutput

# Create agents in a sequential pipeline
generator = LlmAgent(
    name="generator",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Generate initial content based on the input.",
    output_key="generated_content",
)

reviewer = LlmAgent(
    name="reviewer",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Review and improve: {generated_content}",
    output_key="reviewed_content",
)

# Bundle into a workflow
workflow = SequentialAgent(
    name="Pipeline",
    sub_agents=[generator, reviewer],
)
```

### Step 2: Create Critic

```python
critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Score the content quality. 0.0-1.0.",
    output_schema=CriticOutput,
)
```

### Step 3: Run Evolution

```python
from gepa_adk import evolve_workflow, EvolutionConfig

trainset = [
    {"input": "Write about renewable energy."},
    {"input": "Explain machine learning."},
]

config = EvolutionConfig(
    max_iterations=5,
    patience=2,
    reflection_model="ollama_chat/llama3.2:latest",
)

result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    critic=critic,
    config=config,
)

# Keys are qualified names in agent.component format, e.g. "generator.instruction"
for qualified_name, value in result.evolved_components.items():
    print(f"{qualified_name}: {value[:50]}...")
```

### Parameters

Besides `workflow`, `trainset`, `critic`, `scorer` and `config`,
`evolve_workflow()` takes these keyword arguments:

| Parameter | Default | Meaning |
|---|---|---|
| `primary` | `None` | Name of the agent to score. Defaults to the last LlmAgent found in the workflow, typically the final output producer of a sequential workflow. |
| `max_depth` | `5` | Maximum recursion depth for nested workflows; limits how deeply nested workflow structures are traversed. |
| `round_robin` | `False` | If `False`, only the first discovered agent's instruction is evolved; if `True`, every agent's instruction is evolved in turn. Ignored when `components` is given. |
| `components` | `None` | Per-agent mapping of agent names to the component names to evolve. Takes precedence over `round_robin`; an empty list excludes an agent. |
| `component_selector` | `None` | Selector instance or selector name for choosing which components to update. |
| `state_guard` | `None` | `StateGuard` instance that validates and repairs state injection tokens in evolved component text. |
| `session_service` | `None` | ADK session service for state management; when `None`, an `InMemorySessionService` is created internally. |
| `app` | `None` | ADK `App`; its `name` is used as the session app name. An `App` holds no services, so combine it with `session_service` or pass a `runner`. |
| `runner` | `None` | ADK `Runner`; its `session_service` is used for all agent executions (evolved agents, critic and reflection agent). Takes precedence over `app` and `session_service`. |
| `registry` | `None` | `ComponentHandlerRegistry` that resolves every component name; defaults to the registry that `register_handler()` and `register_mapping_components()` fill. |

`evolve_workflow()` always shares session state between the agents
(`share_session=True`), so `output_key` values reach later agents.

## Evolution Strategies

### Default: First Agent Only

By default, `evolve_workflow()` evolves only the first discovered agent's instruction:

```python
# Only generator.instruction evolves
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    critic=critic,
)
```

### Round-Robin: Evolve All Agents

Use `round_robin=True` to evolve all agents, cycling through them each iteration:

```python
# Evolve all agents: generator -> reviewer -> generator -> ...
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    critic=critic,
    round_robin=True,
    config=EvolutionConfig(max_iterations=6),  # 3 iterations per agent
)

# Check which component was evolved each iteration
for record in result.iteration_history:
    print(f"Iter {record.iteration_number}: {record.evolved_component} -> {record.score:.3f}")
```

### Explicit Components Override

For fine-grained control, use the `components` parameter:

```python
# Only evolve generator; exclude reviewer
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    critic=critic,
    components={
        "generator": ["instruction"],
        "reviewer": [],  # Excluded from evolution
    },
)
```

Use an empty list `[]` to exclude an agent while keeping it in workflow execution.

## Workflow Structure Preservation

`evolve_workflow()` preserves the original workflow structure during evolution. LoopAgent, ParallelAgent, and nested workflows execute as designed rather than being flattened.

### LoopAgent Iteration Preservation

When you use a `LoopAgent`, the `max_iterations` configuration is preserved:

```python
from google.adk.agents import LlmAgent, LoopAgent
from google.adk.models.lite_llm import LiteLlm
from gepa_adk import evolve_workflow, EvolutionConfig

# Create an iterative refinement loop
refiner = LlmAgent(
    name="refiner",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Review and improve the content. Focus on clarity.",
    output_key="refined_content",
)

# LoopAgent executes the inner agent 3 times per evaluation
refinement_loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[refiner],
    max_iterations=3,  # Preserved during evolution!
)

result = await evolve_workflow(
    workflow=refinement_loop,
    trainset=trainset,
    critic=critic,
    config=EvolutionConfig(max_iterations=5),
)

print(result.evolved_components["refiner.instruction"])
```

**Key points:**

- The `max_iterations` value is preserved when cloning the workflow
- Each training example is processed through all loop iterations
- The final iteration's output is used for scoring

### Multi-Agent LoopAgent Workflows

LoopAgents can contain multiple sub-agents that execute together in each iteration:

```python
# Create critic-refine loop
critic_agent = LlmAgent(
    name="inner_critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Analyze the content and identify areas for improvement.",
    output_key="feedback",
)
refiner = LlmAgent(
    name="refiner",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Improve the content based on {feedback}.",
    output_key="refined_content",
)

# Both agents run in sequence for each of 3 iterations
refinement_loop = LoopAgent(
    name="CriticRefineLoop",
    sub_agents=[critic_agent, refiner],
    max_iterations=3,
)

result = await evolve_workflow(
    workflow=refinement_loop,
    trainset=trainset,
    critic=critic,
    round_robin=True,  # Evolve both agents
)
```

### ParallelAgent Concurrent Execution

When you use a `ParallelAgent`, concurrent execution semantics are preserved:

```python
from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.models.lite_llm import LiteLlm

# Create parallel research branches
researcher1 = LlmAgent(
    name="researcher1",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Research the historical context.",
    output_key="historical_context",
)
researcher2 = LlmAgent(
    name="researcher2",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Research current trends.",
    output_key="current_trends",
)

# All researchers execute concurrently
parallel_research = ParallelAgent(
    name="ParallelResearch",
    sub_agents=[researcher1, researcher2],
)

result = await evolve_workflow(
    workflow=parallel_research,
    trainset=trainset,
    critic=critic,
    round_robin=True,
    config=EvolutionConfig(max_iterations=4),
)
```

**Key points:**

- The `ParallelAgent` type is preserved when cloning
- ADK Runner executes all sub_agents concurrently
- Each sub-agent's output is available via its `output_key`

### Nested Workflow Structure Preservation

Complex workflows combining SequentialAgent, ParallelAgent, and LoopAgent are fully supported:

```python
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm

# Level 3: Inner refiner in a loop
refiner = LlmAgent(
    name="refiner",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Refine the analysis iteratively.",
    output_key="refined_analysis",
)

# Level 2: Loop for iterative refinement
refinement_loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[refiner],
    max_iterations=3,
)

# Level 2: Parallel researcher
researcher = LlmAgent(
    name="researcher",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
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
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Synthesize {refined_analysis} with {research}.",
    output_key="final_output",
)

# Level 0: Root sequential workflow
workflow = SequentialAgent(
    name="ComplexPipeline",
    sub_agents=[parallel_stage, synthesizer],
)

# All structure is preserved during evolution
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    critic=critic,
    round_robin=True,
    config=EvolutionConfig(max_iterations=6),
)
```

**Key points:**

- Nested workflows of arbitrary depth are supported
- Each agent type (Sequential, Loop, Parallel) maintains its semantics
- The workflow structure is cloned recursively with all properties preserved

## Generation Config Evolution

Workflow evolution supports evolving LLM generation parameters (temperature, top_p) alongside instructions:

```python
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    critic=critic,
    components={
        "generator": ["instruction", "generate_content_config"],
        "reviewer": ["instruction"],  # Only instruction for this agent
    },
)

# Access evolved config (YAML format)
if "generator.generate_content_config" in result.evolved_components:
    print(result.evolved_components["generator.generate_content_config"])
```

For more details, see the [Single-Agent Guide](single-agent.md#advanced-generation-config-evolution).

## Unified Executor Support

`evolve_workflow()` automatically benefits from unified executor support by delegating to `evolve_group()`. This means:

- All agents within your workflow use consistent session management
- Automatic timeout handling and event capture work seamlessly
- You get the same observability and logging benefits as multi-agent evolution

```python
# Executor is created and used automatically
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    critic=critic,
)
```

## App/Runner Infrastructure Integration

For existing ADK applications with configured services, pass your `Runner` instance:

On ADK 2.x, SQL-backed session services need SQLAlchemy. Install the
`gepa-adk[db]` extra (`pip install "gepa-adk[db]"`), which pulls in
`google-adk[db]`.

```python
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

# SQLite for local development
session_service = DatabaseSessionService(db_url="sqlite+aiosqlite:///evolution.db")

runner = Runner(
    app_name="my_workflow_app",
    agent=workflow,
    session_service=session_service,
)

# Initialize tables before concurrent operations
await session_service.list_sessions(app_name="my_workflow_app")

# Evolution uses your runner's session_service
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    runner=runner,
)
```

!!! note "SQLite under load"
    ADK's SQLite-backed session services (`SqliteSessionService`, or
    `DatabaseSessionService` with a `sqlite` URL) set no busy timeout or WAL of
    their own. On a loaded disk a session write can wait past the
    five-second default of Python's sqlite3 connection (aiosqlite uses the
    same one) and raise `database is locked`. The executor retries that
    error under its `RetryPolicy` (three attempts, 0.5 s backoff, doubling) in a
    fresh session before the row counts as a failed evaluation. Timeouts and
    other errors are not retried.

!!! example "Full Example"
    See [`examples/app_runner_integration.py`](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/app_runner_integration.py)
    for a complete example with SQLite persistence.

!!! tip "Backward Compatible"
    The `app` and `runner` parameters are optional. Existing code continues
    to work unchanged, using the default `InMemorySessionService`.

## Related Guides

- [Single-Agent](single-agent.md) — Basic evolution patterns
- [Multi-Agent](multi-agent.md) — Evolve multiple agents together
- [Critic Agents](critic-agents.md) — Custom scoring with critic agents

## API Reference

- [`evolve_workflow()`][gepa_adk.api.evolve_workflow] — Workflow evolution
- [`MultiAgentEvolutionResult`][gepa_adk.domain.MultiAgentEvolutionResult] — Result type
- [`EvolutionConfig`][gepa_adk.domain.EvolutionConfig] — Configuration options

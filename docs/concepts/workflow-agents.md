# Workflow Agents

This document explains how workflow agent evolution works, including structure preservation, scoring strategies, and the mechanics of evolving SequentialAgent, LoopAgent, and ParallelAgent workflows.

## Overview

Workflow evolution optimizes agents within ADK workflow structures while **preserving the workflow's execution semantics**.

```python
from gepa_adk import evolve_workflow

result = await evolve_workflow(
    workflow=my_sequential_agent,
    trainset=examples,
)
```

## Workflow Types

ADK provides three workflow agent types:

| Type | Execution | Use Case |
|------|-----------|----------|
| **SequentialAgent** | Agents run one after another | Pipelines, chains |
| **LoopAgent** | Agent runs N iterations | Refinement, revision |
| **ParallelAgent** | Agents run concurrently | Research, multi-perspective |

## Structure Preservation

**Key principle**: gepa-adk preserves workflow structure during evolution.

When you evolve a workflow, the engine:

1. **Discovers** all LlmAgents via `find_llm_agents()`
2. **Clones** the workflow with instruction overrides via `clone_workflow_with_overrides()`
3. **Executes** the cloned workflow preserving original semantics
4. **Scores** the final output

### What Gets Preserved

| Workflow Type | Preserved Properties |
|---------------|---------------------|
| **SequentialAgent** | Agent order, sub_agents list |
| **LoopAgent** | `max_iterations` count |
| **ParallelAgent** | Concurrent execution semantics |
| **Nested** | Full hierarchy and structure |

### The Cloning Function

`clone_workflow_with_overrides()` recursively clones a workflow while applying instruction overrides:

```python
from gepa_adk.adapters.workflow import clone_workflow_with_overrides

# Original workflow
loop = LoopAgent(name="refine", sub_agents=[inner], max_iterations=3)

# Clone with new instruction
candidate = {"inner.instruction": "Improved instruction text"}
cloned = clone_workflow_with_overrides(loop, candidate)

# Verify preservation
assert cloned.max_iterations == 3  # Preserved!
assert type(cloned) == LoopAgent   # Type preserved!
```

**Invariants:**
- `type(result) == type(workflow)`
- For LoopAgent: `result.max_iterations == workflow.max_iterations`
- `len(result.sub_agents) == len(workflow.sub_agents)`

## Scoring: Separation of Concerns

**Scoring** and **Evolution** are independent:

| Concern | Question | Default |
|---------|----------|---------|
| **Scoring** | What does the critic evaluate? | Final workflow output |
| **Evolution** | Which agent(s) get mutated? | First agent only |

Even when evolving multiple agents, the critic scores the **final output** to answer: "did the pipeline as a whole get better?"

## Default Behavior

```python
# Zero config: sensible defaults
result = await evolve_workflow(workflow, trainset)
```

| Aspect | Default | Rationale |
|--------|---------|-----------|
| **Score** | Final output | What matters is the end result |
| **Evolve** | First agent only | Improve the source, downstream benefits |
| **Trajectories** | All agents captured | Rich context for reflection |

## Round-Robin Evolution

Enable `round_robin=True` to evolve all agents in rotation:

```python
result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    round_robin=True,
)

# Iteration 1: evolve generator.instruction, score final output
# Iteration 2: evolve enhancer.instruction, score final output
# Iteration 3: evolve refiner.instruction, score final output
# Iteration 4: evolve generator.instruction, score final output
# ...
```

Each iteration:
1. Select next agent in round-robin order
2. Propose improved instruction for that agent
3. Clone workflow with the proposed change
4. Execute and score
5. Accept/reject based on score comparison

**Accepted improvements persist**: If iteration 1 improves the generator, that improvement is kept for iteration 2 when evolving the enhancer.

## Workflow Scenarios

### Scenario 1: Sequential Pipeline

```
[Generator] → [Addendumer] → [Refiner] → final output
```

- **Score**: Refiner's output (last agent)
- **Evolve (default)**: Generator only (first agent)
- **Evolve (round_robin)**: All three in rotation
- **Trajectories**: All agents captured for reflection

### Scenario 2: LoopAgent

```
[Refiner] loops 3 times → progressive output
```

- **Score**: Final iteration output
- **Evolve**: Refiner instruction (only one agent)
- **Trajectories**: All iterations captured
- **Structure**: `max_iterations=3` preserved during evolution

### Scenario 3: ParallelAgent

```
[ResearcherA] ─┐
               ├─→ outputs available via session state
[ResearcherB] ─┘
```

- **Score**: Last discovered agent's output (by traversal order)
- **Evolve**: All researchers (with round_robin)
- **Execution**: Agents run concurrently (not sequentially)
- **Session State**: Each agent's output available via `{agent_output_key}`

### Scenario 4: Nested Workflows

```python
SequentialAgent([
    ParallelAgent([ResearcherA, ResearcherB]),  # Run in parallel
    Synthesizer,                                  # Gets both outputs
    Writer,                                       # Final output
])
```

- **Score**: Writer's output (last in outermost sequence)
- **Evolve (default)**: First discovered LlmAgent (ResearcherA)
- **Evolve (round_robin)**: All discovered LlmAgents
- **Discovery**: `find_llm_agents()` traverses nested structure
- **Parallel outputs**: Available via `{researcherA_output}`, `{researcherB_output}`

## Example: Sandwich Shop (Nested Workflow)

This example demonstrates ParallelAgent inside SequentialAgent:

```python
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.models.lite_llm import LiteLlm
from gepa_adk import evolve_workflow, EvolutionConfig

model = LiteLlm(model="ollama_chat/llama3.2:latest")

# Parallel ingredient agents
bread = LlmAgent(name="bread", model=model, instruction="Suggest bread type", output_key="bread")
meat = LlmAgent(name="meat", model=model, instruction="Suggest protein", output_key="meat")
veggie = LlmAgent(name="veggie", model=model, instruction="Suggest vegetable", output_key="veggie")
cheese = LlmAgent(name="cheese", model=model, instruction="Suggest cheese", output_key="cheese")

ingredients = ParallelAgent(name="ingredients", sub_agents=[bread, meat, veggie, cheese])

# Assembler uses all ingredient outputs
assembler = LlmAgent(
    name="assembler",
    model=model,
    instruction="""
    Assemble a sandwich from:
    - Bread: {bread}
    - Meat: {meat}
    - Veggie: {veggie}
    - Cheese: {cheese}
    """,
    output_key="sandwich",
)

# Complete workflow
sandwich_shop = SequentialAgent(
    name="shop",
    sub_agents=[ingredients, assembler],
)

# Evolve with round-robin
result = await evolve_workflow(
    workflow=sandwich_shop,
    trainset=trainset,
    round_robin=True,
    config=EvolutionConfig(max_iterations=12),
)

# See what evolved
for name, text in result.evolved_components.items():
    print(f"{name}: {text}")
```

See `examples/sandwich_evolution.py` for the complete runnable example.

## Discovery Order

`find_llm_agents()` traverses workflows depth-first:

```python
from gepa_adk.adapters.workflow import find_llm_agents

agents = find_llm_agents(workflow)
# Returns: [first_discovered, ..., last_discovered]
```

| Position | Meaning |
|----------|---------|
| **First** | First LlmAgent in depth-first traversal |
| **Last** | Last LlmAgent in depth-first traversal |

For nested workflows:
- **First** = first leaf LlmAgent found
- **Last** = typically the final agent in the outermost sequence

## API Summary

```python
await evolve_workflow(
    workflow,                    # SequentialAgent, LoopAgent, ParallelAgent
    trainset,                    # List of examples

    # Scoring
    critic=None,                 # Default: score final output

    # Evolution
    round_robin=False,           # True: cycle all agents, False: first only
    components=None,             # None: auto, dict: explicit per-agent control

    # Standard options
    config=EvolutionConfig(...),
    reflection_agent=None,       # Same requirements as single/multi-agent
)
```

## Key Implementation Details

### Clone vs Flatten

**Previous approach** (flattening): Workflows were converted to flat SequentialAgent, losing:
- LoopAgent iteration counts
- ParallelAgent concurrency
- Nested structure

**Current approach** (structure preservation): `clone_workflow_with_overrides()` recursively clones while preserving all workflow properties.

### Type Safety

The cloning functions handle ADK's type system:
- `workflow.sub_agents` returns `list[BaseAgent]`
- Cloning uses `cast(AnyAgentType, sub_agent)` for type checking
- Unknown BaseAgent subclasses pass through unchanged with a warning

## Next Steps

- [Workflow Evolution Guide](../guides/workflows.md) - Practical how-to guide
- [Examples](https://github.com/Alberto-Codes/gepa-adk/tree/develop/examples) - Runnable examples
  - `sandwich_evolution.py` - Nested ParallelAgent example
  - `loop_agent_evolution.py` - LoopAgent preservation
  - `parallel_agent_evolution.py` - ParallelAgent example
  - `nested_workflow_evolution.py` - Complex nested structure

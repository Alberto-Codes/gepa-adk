# Quickstart: Execute Workflows As-Is (Preserve Structure)

**Feature**: 215-workflow-structure
**Date**: 2026-01-22

## Prerequisites

- Python 3.12+
- gepa-adk with this feature
- google-adk >= 1.22.0

## Basic Usage

### LoopAgent with Preserved Iterations

```python
from google.adk.agents import LlmAgent, LoopAgent
from gepa_adk import evolve_workflow

# Create a refinement agent
refiner = LlmAgent(
    name="Refiner",
    instruction="Refine the draft: {draft}",
    output_key="refined_draft",
)

# Create a LoopAgent that iterates 3 times
loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[refiner],
    max_iterations=3,  # This will be preserved!
)

# Training data
trainset = [
    {"input": "Write about AI", "expected_output": "A polished essay about AI"},
]

# Evolve - the Refiner will execute 3 times per example
result = await evolve_workflow(loop, trainset)
print(f"Evolved instruction: {result.evolved_components['Refiner.instruction']}")
```

### ParallelAgent with Concurrent Execution

```python
from google.adk.agents import LlmAgent, ParallelAgent
from gepa_adk import evolve_workflow

# Create parallel researchers
researcher_a = LlmAgent(
    name="ResearcherA",
    instruction="Research topic A: {topic}",
    output_key="research_a",
)

researcher_b = LlmAgent(
    name="ResearcherB",
    instruction="Research topic B: {topic}",
    output_key="research_b",
)

# Create parallel workflow
parallel = ParallelAgent(
    name="ParallelResearch",
    sub_agents=[researcher_a, researcher_b],
)

# Evolve - both researchers run concurrently
result = await evolve_workflow(
    parallel,
    trainset,
    round_robin=True,  # Evolve both agents
)
```

### Nested Workflows

```python
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from gepa_adk import evolve_workflow

# Build a complex workflow
drafter = LlmAgent(name="Drafter", instruction="Draft content about {topic}")
researcher_a = LlmAgent(name="ResearcherA", instruction="Research aspect A")
researcher_b = LlmAgent(name="ResearcherB", instruction="Research aspect B")
synthesizer = LlmAgent(name="Synthesizer", instruction="Combine research")

# Nested structure: Sequential -> Parallel -> Sequential
inner_parallel = ParallelAgent(name="Research", sub_agents=[researcher_a, researcher_b])
workflow = SequentialAgent(
    name="Pipeline",
    sub_agents=[drafter, inner_parallel, synthesizer],
)

# Structure is preserved during evolution
result = await evolve_workflow(workflow, trainset, primary="Synthesizer")
```

## Key Differences from Previous Behavior

| Aspect | Before (Flattened) | After (Preserved) |
|--------|-------------------|-------------------|
| LoopAgent(max_iterations=3) | Inner agent runs 1x | Inner agent runs 3x |
| ParallelAgent | Sequential execution | Concurrent execution |
| Nested workflows | Flat sequence | Original structure |
| Output extraction | Last agent in flat list | Designated primary agent |

## Common Patterns

### Iterative Refinement

```python
# Draft -> Critique -> Revise loop
refiner = LlmAgent(name="Refiner", instruction="Improve the draft")
critic = LlmAgent(name="Critic", instruction="Find issues")

loop = LoopAgent(
    name="RefineLoop",
    sub_agents=[refiner, critic],
    max_iterations=3,
)

result = await evolve_workflow(loop, trainset, primary="Refiner")
```

### Research and Synthesis

```python
# Parallel research -> Sequential synthesis
researchers = ParallelAgent(
    name="Research",
    sub_agents=[researcher1, researcher2, researcher3],
)

workflow = SequentialAgent(
    name="Pipeline",
    sub_agents=[researchers, synthesizer, writer],
)

result = await evolve_workflow(workflow, trainset, primary="writer")
```

## Verifying Structure Preservation

```python
# Check that iterations are preserved in trajectory
result = await evolve_workflow(loop, trainset)

# Trajectory should show 3 iterations per example
for traj in result.trajectory:
    print(f"Events: {len(traj.events)}")  # Should reflect 3 iterations
```

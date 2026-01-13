# Quickstart: Workflow Agent Evolution

**Feature**: 017-workflow-evolution  
**Date**: 2026-01-12

## Overview

The `evolve_workflow()` function enables evolutionary optimization of ADK workflow agents (SequentialAgent, LoopAgent, ParallelAgent) by automatically discovering and evolving all nested LlmAgents while preserving the workflow structure.

## Basic Usage

### Evolving a SequentialAgent Pipeline

```python
import asyncio
from google.adk.agents import LlmAgent, SequentialAgent
from gepa_adk import evolve_workflow

# Create a code development pipeline
code_writer = LlmAgent(
    name="code_writer",
    model="gemini-2.0-flash",
    instruction="Write Python code based on the requirement.",
    output_key="generated_code",
)

code_reviewer = LlmAgent(
    name="code_reviewer",
    model="gemini-2.0-flash",
    instruction="Review the code in {generated_code} for quality and correctness.",
    output_key="review_comments",
)

code_refactorer = LlmAgent(
    name="code_refactorer",
    model="gemini-2.0-flash",
    instruction="Refactor the code based on {review_comments}.",
)

# Create sequential workflow
pipeline = SequentialAgent(
    name="CodePipeline",
    sub_agents=[code_writer, code_reviewer, code_refactorer],
)

# Training data
trainset = [
    {"input": "Write a function to calculate factorial", "expected": "def factorial..."},
    {"input": "Create a class for managing users", "expected": "class UserManager..."},
]

# Evolve all agents in the workflow
async def main():
    result = await evolve_workflow(
        workflow=pipeline,
        trainset=trainset,
    )
    
    print(f"Original score: {result.original_score}")
    print(f"Final score: {result.final_score}")
    print(f"Evolved {len(result.evolved_instructions)} agents")
    
    for agent_name, instruction in result.evolved_instructions.items():
        print(f"\n{agent_name}:")
        print(f"  {instruction[:100]}...")

asyncio.run(main())
```

### With Custom Critic Scorer

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve_workflow
from pydantic import BaseModel

class QualityScore(BaseModel):
    score: float  # 0.0 to 1.0
    feedback: str

# Create a critic agent for scoring
critic = LlmAgent(
    name="quality_critic",
    model="gemini-2.0-flash",
    instruction="Score the output quality from 0.0 to 1.0.",
    output_schema=QualityScore,
)

result = await evolve_workflow(
    workflow=pipeline,
    trainset=trainset,
    critic=critic,
)
```

### Specifying a Primary Agent

By default, the last LlmAgent in the workflow is used as the primary (scored) agent. You can specify a different one:

```python
result = await evolve_workflow(
    workflow=pipeline,
    trainset=trainset,
    primary="code_reviewer",  # Score based on reviewer output
)
```

### Limiting Recursion Depth

For deeply nested workflows, control the maximum traversal depth:

```python
result = await evolve_workflow(
    workflow=deeply_nested_workflow,
    trainset=trainset,
    max_depth=3,  # Only find LlmAgents in top 3 levels
)
```

### Custom Evolution Configuration

```python
from gepa_adk.domain.models import EvolutionConfig

config = EvolutionConfig(
    max_iterations=100,      # More iterations
    patience=10,             # Stop after 10 iterations without improvement
    reflection_model="gemini-2.0-flash",
)

result = await evolve_workflow(
    workflow=pipeline,
    trainset=trainset,
    config=config,
)
```

## Workflow Types Supported

### SequentialAgent
Agents execute in order. Ideal for pipelines where later agents depend on earlier outputs.

```python
pipeline = SequentialAgent(
    name="Pipeline",
    sub_agents=[agent1, agent2, agent3],
)
```

### LoopAgent
Agents execute repeatedly. Good for iterative refinement workflows.

```python
from google.adk.agents import LoopAgent

refine_loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[critic_agent, refiner_agent],
    max_iterations=5,
)
```

### ParallelAgent
Agents execute concurrently. Perfect for independent parallel tasks.

```python
from google.adk.agents import ParallelAgent

parallel_research = ParallelAgent(
    name="ParallelResearch",
    sub_agents=[researcher1, researcher2, researcher3],
)
```

### Nested Workflows

Workflows can be nested arbitrarily:

```python
# Sequential → Parallel → LlmAgents
complex_workflow = SequentialAgent(
    name="ComplexPipeline",
    sub_agents=[
        preprocessor_agent,
        ParallelAgent(
            name="ParallelAnalysis",
            sub_agents=[analyzer1, analyzer2, analyzer3],
        ),
        synthesizer_agent,
    ],
)

# Finds all 5 LlmAgents across both levels
result = await evolve_workflow(workflow=complex_workflow, trainset=trainset)
```

## Error Handling

```python
from gepa_adk.domain.exceptions import WorkflowEvolutionError

try:
    result = await evolve_workflow(
        workflow=empty_workflow,  # No LlmAgents inside
        trainset=trainset,
    )
except WorkflowEvolutionError as e:
    print(f"Evolution failed: {e}")
    print(f"Workflow name: {e.workflow_name}")
```

## Return Value

`evolve_workflow()` returns a `MultiAgentEvolutionResult`:

```python
@dataclass
class MultiAgentEvolutionResult:
    evolved_instructions: dict[str, str]  # agent_name → new instruction
    original_score: float                  # Score before evolution
    final_score: float                     # Best score achieved
    primary_agent: str                     # Name of scored agent
    iteration_history: list[IterationRecord]  # Evolution trace
    total_iterations: int                  # Total iterations run
```

## Limitations

- **String instructions only**: LlmAgents with `InstructionProvider` callables (instead of string instructions) are skipped during evolution. Only agents with `instruction: str` can be evolved.

## Best Practices

1. **Use string instructions**: Ensure all LlmAgents use string instructions (not callable InstructionProviders) for evolution compatibility
2. **Use `output_key`**: Set `output_key` on agents whose outputs should be accessible to later agents
3. **Clear instructions**: Write initial instructions that clearly define each agent's role
4. **Quality trainset**: Include diverse examples with expected outputs
5. **Start simple**: Evolve simpler workflows first to validate your trainset
6. **Monitor progress**: Check `iteration_history` to understand evolution dynamics

## See Also

- [evolve_group()](../api.md#evolve_group) - Lower-level multi-agent evolution
- [EvolutionConfig](../domain/models.md#evolutionconfig) - Configuration options
- [ADK Workflow Agents](https://google.github.io/adk-docs/agents/workflow-agents/) - Official ADK documentation

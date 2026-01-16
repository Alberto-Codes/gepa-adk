# Workflow Evolution

This guide covers evolving agents within ADK workflow structures (SequentialAgent, LoopAgent, ParallelAgent).

## When to Use This Pattern

Use workflow evolution when:

- You have an existing ADK workflow (SequentialAgent, LoopAgent, ParallelAgent)
- You want to preserve the workflow structure while optimizing agents
- Agents are organized in pipelines or parallel branches
- You need to maintain workflow-specific configurations (loop iterations, etc.)

## Prerequisites

- Python 3.12+
- gepa-adk installed (`uv add gepa-adk`)
- GEMINI_API_KEY environment variable set

## Basic Workflow Pattern

### Step 1: Create a SequentialAgent Workflow

```python
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent


class DraftOutput(BaseModel):
    content: str


class ReviewOutput(BaseModel):
    feedback: str
    approved: bool


class FinalOutput(BaseModel):
    final: str
    score: float = Field(ge=0.0, le=1.0)


# Create individual agents
drafter = LlmAgent(
    name="drafter",
    model="gemini-2.0-flash",
    instruction="Draft initial content based on the requirement.",
    output_schema=DraftOutput,
)

reviewer = LlmAgent(
    name="reviewer",
    model="gemini-2.0-flash",
    instruction="Review the draft and provide feedback.",
    output_schema=ReviewOutput,
)

finalizer = LlmAgent(
    name="finalizer",
    model="gemini-2.0-flash",
    instruction="Produce the final version incorporating feedback.",
    output_schema=FinalOutput,
)

# Create workflow
pipeline = SequentialAgent(
    name="ContentPipeline",
    sub_agents=[drafter, reviewer, finalizer],
)
```

### Step 2: Run Workflow Evolution

```python
import asyncio
from gepa_adk import evolve_workflow

trainset = [
    {"input": "Write a blog post about Python"},
    {"input": "Write a blog post about machine learning"},
    {"input": "Write a blog post about web development"},
]


async def main():
    result = await evolve_workflow(
        workflow=pipeline,
        trainset=trainset,
        # primary defaults to last agent (finalizer)
    )

    print(f"Improvement: {result.improvement:.2%}")
    for name, instruction in result.evolved_instructions.items():
        print(f"\n{name}:\n{instruction}")


asyncio.run(main())
```

## Complete Working Example

```python
"""Workflow evolution example with SequentialAgent."""

import asyncio
import os
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from gepa_adk import evolve_workflow, EvolutionConfig


class IdeaOutput(BaseModel):
    ideas: list[str]
    best_idea: str


class OutlineOutput(BaseModel):
    outline: list[str]
    structure: str


class ArticleOutput(BaseModel):
    article: str
    word_count: int
    score: float = Field(ge=0.0, le=1.0)


async def main() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("Set GEMINI_API_KEY environment variable")

    # Ideation agent
    ideator = LlmAgent(
        name="ideator",
        model="gemini-2.0-flash",
        instruction="Generate creative ideas for the given topic.",
        output_schema=IdeaOutput,
    )

    # Outliner agent
    outliner = LlmAgent(
        name="outliner",
        model="gemini-2.0-flash",
        instruction="Create a structured outline from the best idea.",
        output_schema=OutlineOutput,
    )

    # Writer agent
    writer = LlmAgent(
        name="writer",
        model="gemini-2.0-flash",
        instruction="Write a complete article following the outline.",
        output_schema=ArticleOutput,
    )

    # Create sequential workflow
    workflow = SequentialAgent(
        name="ArticleWorkflow",
        sub_agents=[ideator, outliner, writer],
    )

    trainset = [
        {"input": "Write about sustainable living"},
        {"input": "Write about productivity tips"},
        {"input": "Write about learning new skills"},
        {"input": "Write about healthy eating habits"},
        {"input": "Write about personal finance basics"},
    ]

    config = EvolutionConfig(max_iterations=15, patience=5)

    result = await evolve_workflow(
        workflow=workflow,
        trainset=trainset,
        config=config,
    )

    print(f"Original score: {result.original_score:.3f}")
    print(f"Final score: {result.final_score:.3f}")
    print(f"Improvement: {result.improvement:.2%}")

    print("\nEvolved Instructions:")
    for name, instruction in result.evolved_instructions.items():
        print(f"\n--- {name} ---")
        print(instruction)


if __name__ == "__main__":
    asyncio.run(main())
```

## LoopAgent Workflows

Evolve agents within iterative loops:

```python
from google.adk.agents import LoopAgent


class RefineOutput(BaseModel):
    refined: str
    iterations_needed: int


class CheckOutput(BaseModel):
    passed: bool
    issues: list[str]
    score: float = Field(ge=0.0, le=1.0)


refiner = LlmAgent(
    name="refiner",
    model="gemini-2.0-flash",
    instruction="Refine the content based on feedback.",
    output_schema=RefineOutput,
)

checker = LlmAgent(
    name="checker",
    model="gemini-2.0-flash",
    instruction="Check quality and identify remaining issues.",
    output_schema=CheckOutput,
)

loop = LoopAgent(
    name="RefinementLoop",
    sub_agents=[refiner, checker],
    max_iterations=3,  # Preserved during evolution
)

result = await evolve_workflow(workflow=loop, trainset=trainset)
```

## ParallelAgent Workflows

Evolve agents that run in parallel:

```python
from google.adk.agents import ParallelAgent


class AnalysisOutput(BaseModel):
    analysis: str
    confidence: float


class AggregateOutput(BaseModel):
    combined: str
    score: float = Field(ge=0.0, le=1.0)


analyst1 = LlmAgent(
    name="analyst1",
    model="gemini-2.0-flash",
    instruction="Analyze from perspective A.",
    output_schema=AnalysisOutput,
)

analyst2 = LlmAgent(
    name="analyst2",
    model="gemini-2.0-flash",
    instruction="Analyze from perspective B.",
    output_schema=AnalysisOutput,
)

aggregator = LlmAgent(
    name="aggregator",
    model="gemini-2.0-flash",
    instruction="Combine and synthesize the analyses.",
    output_schema=AggregateOutput,
)

# Parallel analysis followed by aggregation
parallel_analysis = ParallelAgent(
    name="ParallelAnalysis",
    sub_agents=[analyst1, analyst2],
)

workflow = SequentialAgent(
    name="AnalysisPipeline",
    sub_agents=[parallel_analysis, aggregator],
)

result = await evolve_workflow(
    workflow=workflow,
    trainset=trainset,
    primary="aggregator",
)
```

## Common Patterns and Tips

### Specifying Primary Agent

Control which agent's output is scored:

```python
result = await evolve_workflow(
    workflow=pipeline,
    trainset=trainset,
    primary="reviewer",  # Score the reviewer, not the last agent
)
```

### Using External Critics

Add a critic for better evaluation:

```python
class CriticOutput(BaseModel):
    evaluation: str
    score: float = Field(ge=0.0, le=1.0)


critic = LlmAgent(
    name="critic",
    model="gemini-2.0-flash",
    instruction="Evaluate the overall workflow output quality.",
    output_schema=CriticOutput,
)

result = await evolve_workflow(
    workflow=pipeline,
    trainset=trainset,
    critic=critic,
)
```

### Nested Workflows

The `max_depth` parameter controls nested traversal:

```python
result = await evolve_workflow(
    workflow=nested_workflow,
    trainset=trainset,
    max_depth=5,  # Traverse up to 5 levels deep
)
```

### State Token Preservation

Preserve dynamic tokens in evolved instructions:

```python
from gepa_adk.utils import StateGuard

state_guard = StateGuard(tokens=["{user_input}", "{context}"])

result = await evolve_workflow(
    workflow=pipeline,
    trainset=trainset,
    state_guard=state_guard,
)
```

## Related Guides

- [Single-Agent](single-agent.md) — Basic single agent evolution
- [Critic Agents](critic-agents.md) — Using dedicated critics
- [Multi-Agent](multi-agent.md) — Direct multi-agent evolution

## API Reference

- [`evolve_workflow()`][gepa_adk.evolve_workflow] — Workflow evolution function
- [`MultiAgentEvolutionResult`][gepa_adk.MultiAgentEvolutionResult] — Evolution results
- [`EvolutionConfig`][gepa_adk.EvolutionConfig] — Configuration options

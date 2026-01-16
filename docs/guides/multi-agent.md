# Multi-Agent Co-Evolution

This guide covers evolving multiple agents together in a coordinated workflow.

## When to Use This Pattern

Use multi-agent evolution when:

- Multiple agents work together on a task
- Agents depend on each other's outputs
- You want to optimize the entire pipeline, not just individual agents
- Agents share session state during execution

## Prerequisites

- Python 3.12+
- gepa-adk installed (`uv add gepa-adk`)
- GEMINI_API_KEY environment variable set

## Basic Multi-Agent Pattern

### Step 1: Create Multiple Agents

Define agents that work together in a pipeline:

```python
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent


class DraftOutput(BaseModel):
    draft: str
    notes: str


class ReviewOutput(BaseModel):
    feedback: str
    suggestions: list[str]


class FinalOutput(BaseModel):
    final_content: str
    changes_made: list[str]
    score: float = Field(ge=0.0, le=1.0)


# First agent: drafts content
drafter = LlmAgent(
    name="drafter",
    model="gemini-2.0-flash",
    instruction="Create an initial draft based on the requirements.",
    output_schema=DraftOutput,
)

# Second agent: reviews the draft
reviewer = LlmAgent(
    name="reviewer",
    model="gemini-2.0-flash",
    instruction="Review the draft and provide constructive feedback.",
    output_schema=ReviewOutput,
)

# Third agent: produces final output (primary, provides score)
finalizer = LlmAgent(
    name="finalizer",
    model="gemini-2.0-flash",
    instruction="Incorporate feedback to produce the final version.",
    output_schema=FinalOutput,
)
```

### Step 2: Run Multi-Agent Evolution

```python
import asyncio
from gepa_adk import evolve_group

trainset = [
    {"input": "Write a product description for a smartwatch"},
    {"input": "Write a product description for wireless earbuds"},
    {"input": "Write a product description for a laptop stand"},
]


async def main():
    result = await evolve_group(
        agents=[drafter, reviewer, finalizer],
        primary="finalizer",  # Agent whose output is scored
        trainset=trainset,
        share_session=True,  # Agents see each other's outputs
    )

    print(f"Improvement: {result.improvement:.2%}")
    for name, instruction in result.evolved_instructions.items():
        print(f"\n{name}:\n{instruction}")


asyncio.run(main())
```

## Complete Working Example

```python
"""Multi-agent co-evolution example."""

import asyncio
import os
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from gepa_adk import evolve_group, EvolutionConfig


class ResearchOutput(BaseModel):
    findings: str
    sources: list[str]


class AnalysisOutput(BaseModel):
    analysis: str
    key_insights: list[str]


class ReportOutput(BaseModel):
    report: str
    summary: str
    score: float = Field(ge=0.0, le=1.0)


async def main() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("Set GEMINI_API_KEY environment variable")

    # Research agent gathers information
    researcher = LlmAgent(
        name="researcher",
        model="gemini-2.0-flash",
        instruction="Research the topic and gather relevant information.",
        output_schema=ResearchOutput,
    )

    # Analyst processes the research
    analyst = LlmAgent(
        name="analyst",
        model="gemini-2.0-flash",
        instruction="Analyze the research findings and extract insights.",
        output_schema=AnalysisOutput,
    )

    # Report writer produces final output
    reporter = LlmAgent(
        name="reporter",
        model="gemini-2.0-flash",
        instruction="Write a comprehensive report based on the analysis.",
        output_schema=ReportOutput,
    )

    trainset = [
        {"input": "Impact of AI on healthcare"},
        {"input": "Future of renewable energy"},
        {"input": "Trends in remote work"},
        {"input": "Evolution of social media"},
        {"input": "Advances in space exploration"},
    ]

    config = EvolutionConfig(max_iterations=15, patience=5)

    result = await evolve_group(
        agents=[researcher, analyst, reporter],
        primary="reporter",
        trainset=trainset,
        share_session=True,
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

## Common Patterns and Tips

### Using a Separate Critic

Add a critic agent for external evaluation:

```python
class CriticOutput(BaseModel):
    evaluation: str
    score: float = Field(ge=0.0, le=1.0)


critic = LlmAgent(
    name="critic",
    model="gemini-2.0-flash",
    instruction="Evaluate the quality of the final report.",
    output_schema=CriticOutput,
)

result = await evolve_group(
    agents=[researcher, analyst, reporter],
    primary="reporter",
    trainset=trainset,
    critic=critic,  # External scoring
)
```

### Isolated Sessions

For agents that should work independently:

```python
result = await evolve_group(
    agents=[agent1, agent2, agent3],
    primary="agent3",
    trainset=trainset,
    share_session=False,  # Each agent has isolated context
)
```

### Component Selection

Control which agent instructions evolve:

```python
from gepa_adk import RoundRobinComponentSelector

result = await evolve_group(
    agents=[agent1, agent2, agent3],
    primary="agent3",
    trainset=trainset,
    component_selector=RoundRobinComponentSelector(),
)
```

### State Token Preservation

Preserve dynamic tokens in instructions:

```python
from gepa_adk.utils import StateGuard

state_guard = StateGuard(tokens=["{user_context}", "{session_data}"])

result = await evolve_group(
    agents=[agent1, agent2, agent3],
    primary="agent3",
    trainset=trainset,
    state_guard=state_guard,
)
```

## Related Guides

- [Single-Agent](single-agent.md) — Basic single agent evolution
- [Critic Agents](critic-agents.md) — Using dedicated critics
- [Workflows](workflows.md) — SequentialAgent optimization

## API Reference

- [`evolve_group()`][gepa_adk.evolve_group] — Multi-agent evolution function
- [`MultiAgentEvolutionResult`][gepa_adk.MultiAgentEvolutionResult] — Multi-agent results
- [`EvolutionConfig`][gepa_adk.EvolutionConfig] — Configuration options

# Critic Agents

This guide covers using dedicated critic agents for scoring during <evolution:evolution>.

!!! tip "Working Example Available"
    For a complete, runnable example, see:

    - **[examples/critic_agent.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/critic_agent.py)** — Story generation with critic scoring using Ollama
    - **[Getting Started Guide](../getting-started.md)** — Step-by-step walkthrough with critic pattern

    The examples below use Gemini for illustration, but Ollama (`gpt-oss:20b`) is required for the evolution engine.

## When to Use This Pattern

Use critic agents when:

- Your main agent shouldn't self-assess (to avoid bias)
- You need specialized evaluation criteria for <trial:feedback>
- You want to separate generation from evaluation
- Self-assessment scores are unreliable

## Prerequisites

- Python 3.12+
- gepa-adk installed (`uv add gepa-adk`)
- GEMINI_API_KEY environment variable set

## Basic Critic Pattern

### Step 1: Create the Main Agent

The main agent doesn't need a `score` field since the critic handles scoring:

```python
from pydantic import BaseModel
from google.adk.agents import LlmAgent


class GeneratorOutput(BaseModel):
    """Output from the main agent (no score needed)."""

    content: str
    reasoning: str


agent = LlmAgent(
    name="generator",
    model="gemini-2.0-flash",
    instruction="Generate creative content based on the prompt.",
    output_schema=GeneratorOutput,
)
```

### Step 2: Create the Critic Agent

The critic evaluates outputs and provides a score:

```python
from pydantic import Field


class CriticOutput(BaseModel):
    """Critic evaluation with required score."""

    feedback: str
    strengths: list[str]
    weaknesses: list[str]
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality score based on evaluation criteria",
    )


critic = LlmAgent(
    name="critic",
    model="gemini-2.0-flash",
    instruction="""Evaluate the response quality. Consider:
- Accuracy and correctness
- Clarity and coherence
- Completeness of the response
Provide constructive feedback and a score from 0.0 to 1.0.""",
    output_schema=CriticOutput,
)
```

### Step 3: Run Evolution with Critic

```python
from gepa_adk import evolve_sync

trainset = [
    {"input": "Write a haiku about programming"},
    {"input": "Write a haiku about nature"},
    {"input": "Write a haiku about technology"},
]

result = evolve_sync(agent, trainset, critic=critic)
print(f"Improvement: {result.improvement:.2%}")
```

## Complete Working Example

```python
"""Critic agent evolution example."""

import os
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from gepa_adk import evolve_sync, EvolutionConfig


class StoryOutput(BaseModel):
    story: str
    genre: str


class CriticOutput(BaseModel):
    feedback: str
    creativity_score: float = Field(ge=0.0, le=1.0)
    coherence_score: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0, description="Overall quality")


def main() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("Set GEMINI_API_KEY environment variable")

    # Main agent generates stories
    agent = LlmAgent(
        name="storyteller",
        model="gemini-2.0-flash",
        instruction="Write a short story based on the given prompt.",
        output_schema=StoryOutput,
    )

    # Critic evaluates story quality
    critic = LlmAgent(
        name="story-critic",
        model="gemini-2.0-flash",
        instruction="""Evaluate the story quality. Consider:
- Creativity and originality
- Plot coherence and structure
- Character development
- Writing style and engagement
Provide an overall score from 0.0 to 1.0.""",
        output_schema=CriticOutput,
    )

    trainset = [
        {"input": "A robot learns to paint"},
        {"input": "A detective solves a mystery"},
        {"input": "Two strangers meet on a train"},
        {"input": "A child discovers a secret door"},
        {"input": "An inventor creates something unexpected"},
    ]

    config = EvolutionConfig(max_iterations=15, patience=5)
    result = evolve_sync(agent, trainset, critic=critic, config=config)

    print(f"Original score: {result.original_score:.3f}")
    print(f"Final score: {result.final_score:.3f}")
    print(f"Improvement: {result.improvement:.2%}")
    print(f"\nEvolved instruction:\n{result.evolved_component_text}")


if __name__ == "__main__":
    main()
```

## Common Patterns and Tips

### Domain-Specific Critics

Create critics tailored to your evaluation needs:

```python
# Code review critic
class CodeReviewOutput(BaseModel):
    issues: list[str]
    suggestions: list[str]
    correctness: float = Field(ge=0.0, le=1.0)
    readability: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0)


code_critic = LlmAgent(
    name="code-reviewer",
    model="gemini-2.0-flash",
    instruction="""Review the code for:
- Correctness and bug-free execution
- Code style and readability
- Best practices adherence
- Performance considerations""",
    output_schema=CodeReviewOutput,
)
```

### Multi-Criteria Scoring

Use the critic to evaluate multiple dimensions:

```python
class DetailedCriticOutput(BaseModel):
    accuracy: float = Field(ge=0.0, le=1.0)
    clarity: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    relevance: float = Field(ge=0.0, le=1.0)
    # Overall score can be a weighted average
    score: float = Field(ge=0.0, le=1.0)
```

### Critic with Context

Include context in the critic's evaluation:

```python
critic = LlmAgent(
    name="contextual-critic",
    model="gemini-2.0-flash",
    instruction="""Evaluate the response considering:
- The original input/question
- The expected answer format
- Domain-specific requirements

The input was: {input}
The expected format: {expected}""",
    output_schema=CriticOutput,
)
```

## Related Guides

- [Single-Agent](single-agent.md) — Basic self-assessed evolution
- [Multi-Agent](multi-agent.md) — Evolve multiple agents together
- [Workflows](workflows.md) — Optimize agent pipelines

## API Reference

- [`evolve()`][gepa_adk.evolve] — Async evolution with critic parameter
- [`evolve_sync()`][gepa_adk.evolve_sync] — Synchronous wrapper
- [`CriticScorer`][gepa_adk.adapters.critic_scorer.CriticScorer] — Internal <core:Scorer> implementation

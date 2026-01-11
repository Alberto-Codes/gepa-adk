# CriticScorer Quickstart Guide

**Feature**: 009-critic-scorer  
**Date**: 2026-01-10

## Overview

CriticScorer enables you to use ADK agents as critics for evaluating other agent outputs, returning structured scores with detailed feedback instead of simple 0/1 binary scores.

## Prerequisites

```bash
# Install gepa-adk (includes google-adk)
uv add gepa-adk
```

## Basic Usage

### 1. Define a Critic Agent

Create an LLM agent with a structured output schema:

```python
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent


class CriticOutput(BaseModel):
    """Structured output from the critic."""
    
    score: float = Field(ge=0.0, le=1.0, description="Quality score")
    feedback: str = Field(default="", description="Detailed feedback")
    dimension_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Per-dimension scores",
    )
    actionable_guidance: str = Field(
        default="",
        description="How to improve",
    )


critic = LlmAgent(
    name="quality_critic",
    model="gemini-2.0-flash",
    instruction="""You are a quality evaluator for AI responses.

Given an input query and the agent's output, evaluate:
1. Accuracy - Is the information correct?
2. Clarity - Is the response easy to understand?
3. Completeness - Does it fully address the query?

Provide a score from 0.0 to 1.0 and detailed feedback.
""",
    output_schema=CriticOutput,
)
```

### 2. Create a CriticScorer

```python
from gepa_adk.adapters.critic_scorer import CriticScorer

scorer = CriticScorer(critic_agent=critic)
```

### 3. Score Outputs

**Synchronous:**
```python
score, metadata = scorer.score(
    input_text="What is photosynthesis?",
    output="Photosynthesis is how plants make food from sunlight.",
    expected="Photosynthesis is the process by which plants convert light energy into chemical energy.",
)

print(f"Score: {score:.2f}")
print(f"Feedback: {metadata['feedback']}")
```

**Asynchronous (preferred):**
```python
import asyncio

async def evaluate():
    score, metadata = await scorer.async_score(
        input_text="Explain machine learning",
        output="Machine learning is AI that learns from data.",
    )
    return score, metadata

score, metadata = asyncio.run(evaluate())
```

## Advanced Usage

### Multi-Dimensional Scoring

Configure your critic to return dimension scores:

```python
critic = LlmAgent(
    name="multi_dimension_critic",
    model="gemini-2.0-flash",
    instruction="""Evaluate the response on multiple dimensions:
- accuracy: factual correctness (0.0-1.0)
- clarity: readability and structure (0.0-1.0)
- completeness: coverage of the topic (0.0-1.0)
- relevance: how well it addresses the query (0.0-1.0)

Overall score = weighted average of dimensions.
""",
    output_schema=CriticOutput,
)

scorer = CriticScorer(critic_agent=critic)
score, metadata = await scorer.async_score(...)

# Access dimension scores
for dim, dim_score in metadata.get("dimension_scores", {}).items():
    print(f"  {dim}: {dim_score:.2f}")
```

### Workflow Critics (SequentialAgent)

For complex evaluation pipelines, use a SequentialAgent:

```python
from google.adk.agents import SequentialAgent

# Step 1: Validate the response format
validator = LlmAgent(
    name="format_validator",
    model="gemini-2.0-flash",
    instruction="Check if the response follows proper formatting...",
    output_key="validation_result",  # Saves to session state
)

# Step 2: Score the validated response
evaluator = LlmAgent(
    name="quality_evaluator",
    model="gemini-2.0-flash",
    instruction="Given the validation result in {validation_result}, score the response...",
    output_schema=CriticOutput,
)

# Combine into workflow
workflow_critic = SequentialAgent(
    name="validation_and_scoring",
    sub_agents=[validator, evaluator],
)

scorer = CriticScorer(critic_agent=workflow_critic)
```

### Session Sharing

Share session context between your main agent and the critic:

```python
from google.adk.sessions import InMemorySessionService

# Create shared session service
session_service = InMemorySessionService()

# Use same session for both agent and critic
scorer = CriticScorer(
    critic_agent=critic,
    session_service=session_service,
)

# Pass session_id to share context
score, metadata = await scorer.async_score(
    input_text="...",
    output="...",
    session_id="user_123_session",  # Existing session
)
```

## Error Handling

```python
from gepa_adk.domain.exceptions import (
    CriticOutputParseError,
    MissingScoreFieldError,
    ScoringError,
)

try:
    score, metadata = await scorer.async_score(
        input_text="Test input",
        output="Test output",
    )
except CriticOutputParseError as e:
    print(f"Critic returned invalid JSON: {e.raw_output}")
except MissingScoreFieldError as e:
    print(f"Missing score field. Available: {e.available_fields}")
except ScoringError as e:
    print(f"Scoring failed: {e}")
```

## Integration with GEPA Evolution

CriticScorer implements the `Scorer` protocol, making it directly usable with GEPA's evolution engine:

```python
from gepa_adk.adapters import ADKAdapter
from gepa_adk.adapters.critic_scorer import CriticScorer

# Your agent to evolve
agent = LlmAgent(name="my_agent", ...)

# Critic for evaluation
critic_scorer = CriticScorer(critic_agent=critic)

# Create adapter with critic scorer
adapter = ADKAdapter(
    agent=agent,
    scorer=critic_scorer,
)

# Now use in evolution loop
result = await adapter.evaluate(batch, candidate)
```

## Best Practices

1. **Use Pydantic output_schema** - Ensures structured JSON output from critics
2. **Prefer async_score()** - Better performance for concurrent evaluations
3. **Keep critic instructions focused** - Clear criteria lead to consistent scoring
4. **Include examples in instructions** - Few-shot prompting improves reliability
5. **Handle errors gracefully** - LLM outputs can be unpredictable

> ⚠️ **Important ADK Constraint**: When `output_schema` is set on an LlmAgent, the agent can **ONLY reply and CANNOT use any tools**. This is by design in ADK and is acceptable for critic agents since they only need to produce structured scoring output. If your evaluation requires tool usage (e.g., web search, code execution), use a SequentialAgent with a tool-enabled agent before the output-schema-constrained scorer agent.

## Common Patterns

### Open-Ended Evaluation (No Expected Output)

```python
# Evaluate quality without a reference answer
score, metadata = await scorer.async_score(
    input_text="Write a haiku about coding",
    output="Debugging all night\nCoffee fuels the tired mind\nBug fixed at sunrise",
    expected=None,  # No expected output
)
```

### Batch Evaluation

```python
import asyncio

async def batch_evaluate(inputs, outputs):
    tasks = [
        scorer.async_score(inp, out)
        for inp, out in zip(inputs, outputs)
    ]
    return await asyncio.gather(*tasks)

results = asyncio.run(batch_evaluate(inputs, outputs))
```

## Next Steps

- See [Data Model](data-model.md) for entity details
- See [API Contract](contracts/critic-scorer-api.md) for full API reference
- See [Spec](spec.md) for requirements and acceptance criteria

# Critic Agents

This guide covers using dedicated critic agents for scoring during evolution.

!!! tip "Working Example"
    Complete runnable example:

    - **[examples/critic_agent.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/critic_agent.py)** — Story generation with critic scoring

## When to Use Critics

Use critic agents when:

- Your main agent shouldn't self-assess (to avoid bias)
- You need specialized evaluation criteria
- You want to separate generation from evaluation

## Prerequisites

- Python 3.12+
- gepa-adk installed (`uv add gepa-adk`)
- Ollama running locally
- `OLLAMA_API_BASE` environment variable set

## Basic Critic Pattern

### Step 1: Create the Main Agent

The main agent generates content. It doesn't need a score field:

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel

class StoryOutput(BaseModel):
    story: str
    genre: str

agent = LlmAgent(
    name="storyteller",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Write a short story based on the given prompt.",
    output_schema=StoryOutput,
)
```

### Step 2: Create the Critic Agent

The critic evaluates outputs and provides a score.

**Option A: Use built-in SimpleCriticOutput**

```python
from gepa_adk import SimpleCriticOutput

critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Evaluate story quality. Score 0.0-1.0.",
    output_schema=SimpleCriticOutput,
)
```

**Option B: Use built-in CriticOutput (with dimensions)**

```python
from gepa_adk import CriticOutput

critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="""Evaluate story quality. Provide:
- Overall score 0.0-1.0
- Dimension scores for: creativity, coherence, engagement
- Actionable guidance for improvement""",
    output_schema=CriticOutput,
)
```

**Option C: Custom schema**

```python
from pydantic import Field

class MyOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str
    issues: list[str] = []

critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Evaluate and list any issues.",
    output_schema=MyOutput,
)
```

### Step 3: Run Evolution

```python
from gepa_adk import evolve, run_sync, EvolutionConfig

trainset = [
    {"input": "A robot learns to paint"},
    {"input": "A detective solves a mystery"},
]

config = EvolutionConfig(
    max_iterations=5,
    patience=2,
    reflection_model="ollama_chat/llama3.2:latest",
)

result = run_sync(evolve(agent, trainset, critic=critic, config=config))
```

### What the Critic Sees

gepa-adk sends the critic a plain-text prompt with labelled sections. When
the main agent has an `output_schema`, its structured output reaches the
"Agent Output" section as JSON, so a critic can parse it field by field.
Pydantic models, dates and enums nested inside that output are rendered as
JSON values as well (objects, ISO strings and enum values), not as Python
reprs:

```text
Input Query:
A robot learns to paint

Agent Output:
{"story": "Unit 7 mixed its first colour at dawn...", "genre": "sci-fi"}

Please evaluate the agent output and provide a score with feedback.
```

An agent without an `output_schema` returns text, and that text appears in
the "Agent Output" section unchanged. An "Expected Output:" section follows
"Agent Output" when the trainset example carries an `expected` value.

## Built-in Critic Schemas

### SimpleCriticOutput

Minimal schema for basic evaluation:

```python
from gepa_adk import SimpleCriticOutput

# Fields:
# - score: float (0.0-1.0, required)
# - feedback: str (required)
```

### CriticOutput

Advanced schema with multi-dimensional scoring:

```python
from gepa_adk import CriticOutput

# Fields:
# - score: float (0.0-1.0, required)
# - feedback: str (optional, default "")
# - dimension_scores: dict[str, float] (optional)
# - actionable_guidance: str (optional)
```

### Built-in Instructions

Generic instructions for quick setup:

```python
from gepa_adk.adapters import (
    SIMPLE_CRITIC_INSTRUCTION,
    ADVANCED_CRITIC_INSTRUCTION,
)

# Simple: basic score + feedback
critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction=SIMPLE_CRITIC_INSTRUCTION,
    output_schema=SimpleCriticOutput,
)

# Advanced: dimensions + guidance
critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction=ADVANCED_CRITIC_INSTRUCTION,
    output_schema=CriticOutput,
)
```

## Advanced Patterns

### Workflow Critics

Critics can be workflow agents (SequentialAgent, etc.) for complex evaluation:

```python
from google.adk.agents import SequentialAgent

# First agent gathers context
context_gatherer = LlmAgent(
    name="context",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Extract key elements from the content.",
)

# Second agent scores using context
scorer = LlmAgent(
    name="scorer",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Score the content based on gathered context.",
    output_schema=SimpleCriticOutput,
)

# Workflow critic
critic = SequentialAgent(
    name="workflow_critic",
    sub_agents=[context_gatherer, scorer],
)

result = run_sync(evolve(agent, trainset, critic=critic, config=config))
```

### Custom Scorer Protocol

Implement the `Scorer` protocol for fully custom scoring logic:

```python
from gepa_adk import Scorer

class ExactMatchScorer:
    """Scores based on exact match with expected output."""

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict]:
        if expected is None:
            return 0.0, {"error": "Expected value required"}
        match = output.strip() == expected.strip()
        return (1.0 if match else 0.0), {"exact_match": match}

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict]:
        return self.score(input_text, output, expected)
```

Pass the instance with the `scorer=` keyword. It replaces the critic, so
`critic=` and `scorer=` are mutually exclusive, and an explicit scorer takes
precedence over the agent's `output_schema`:

```python
result = run_sync(evolve(agent, trainset, scorer=ExactMatchScorer(), config=config))
```

`evolve_group()` and `evolve_workflow()` accept the same keyword.

### Label Agreement

When each trainset row carries an `expected` label, use the built-in
`LabelAgreementScorer` instead of writing a scorer:

```python
from gepa_adk import LabelAgreementScorer, evolve, run_sync

trainset = [
    {"input": "Buy now!!!", "expected": "spam"},
    {"input": "Lunch at noon?", "expected": "ham"},
]
result = run_sync(
    evolve(agent, trainset, scorer=LabelAgreementScorer(field="label"), config=config)
)
```

With `field="label"`, the agent output is parsed as JSON and
`str(output["label"]).strip()` must equal `expected.strip()` exactly: the row
scores `1.0` on agreement and `0.0` otherwise. There is no case folding, fuzzy
matching or numeric tolerance. Without `field`, the output and `expected` agree when both
parse as equal JSON documents (key order and spacing do not matter), or
otherwise when their stripped texts are equal.

A row scores `0.0` with a `reason` in its metadata when no comparison is
possible:

| `reason` | Cause |
|---|---|
| `missing_expected` | The row has no `expected` value. |
| `output_not_json` | `field` is set and the output does not parse as JSON. |
| `field_missing` | The parsed output is not an object or lacks `field`. |

Metadata always carries `field`, `actual`, `expected` and `agreement`.

`SchemaBasedScorer`, used when an agent has an `output_schema` and no
`scorer=` or `critic=`, never reads `expected`: it uses the agent's
self-reported `score` field. Pass `LabelAgreementScorer` to score a schema
agent against labels.

### Schema-Based Scoring (Self-Assessment)

Alternative to critics: agent scores itself via `output_schema`:

```python
from pydantic import BaseModel, Field

class SelfScoredOutput(BaseModel):
    result: str
    reasoning: str
    score: float = Field(ge=0.0, le=1.0)  # Required for self-scoring

agent = LlmAgent(
    name="self-scorer",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Complete the task and honestly assess your quality.",
    output_schema=SelfScoredOutput,
)

# No critic needed - score extracted from output_schema
result = run_sync(evolve(agent, trainset, config=config))
```

!!! warning "Self-Assessment Bias"
    Self-scoring can be biased. Prefer critic agents for objective evaluation.

### Domain-Specific Critics

Tailor critics to your domain:

```python
class CodeReviewOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str
    bugs: list[str] = []
    style_issues: list[str] = []
    security_concerns: list[str] = []

code_critic = LlmAgent(
    name="code-reviewer",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="""Review code for:
- Correctness (bugs, logic errors)
- Style (readability, naming)
- Security (vulnerabilities, unsafe patterns)
Score 0.0-1.0.""",
    output_schema=CodeReviewOutput,
)
```

## Feedback Normalization

GEPA-ADK normalizes critic output for the reflection agent:

| Your Field | Normalized To |
|------------|---------------|
| `feedback` | `feedback_text` |
| `feedback_text` | `feedback_text` |
| `dimension_scores` | `dimensions` |
| `actionable_guidance` | `guidance` |
| Custom fields | Passed through unchanged |

This ensures consistent input to reflection regardless of your schema.

## Related Guides

- [Single-Agent](single-agent.md) — Basic evolution patterns
- [Multi-Agent](multi-agent.md) — Evolve multiple agents together
- [Workflows](workflows.md) — Optimize agent pipelines

## API Reference

- [`evolve()`][gepa_adk.api.evolve] — Async evolution
- [`run_sync()`][gepa_adk.api.run_sync] — Sync wrapper for async evolution
- [`SimpleCriticOutput`][gepa_adk.adapters.scoring.critic_scorer.SimpleCriticOutput] — Basic schema
- [`CriticOutput`][gepa_adk.adapters.scoring.critic_scorer.CriticOutput] — Advanced schema
- [`Scorer`][gepa_adk.ports.scorer.Scorer] — Protocol for custom scorers

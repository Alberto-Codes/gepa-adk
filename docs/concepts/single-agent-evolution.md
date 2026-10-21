# Single-Agent Evolution

This document explains how single-agent evolution works, including the roles of the scorer (usually a critic agent) and the reflection agent, trial structure, and how they work together. The loop itself is described in [GEPA Fundamentals](gepa-fundamentals.md#how-the-evolution-loop-works).

## Overview

Single-agent evolution optimizes one agent's components (by default its `instruction`; any component with a registered handler can be added) through iterative improvement.

```python
from gepa_adk import evolve

result = await evolve(
    agent=my_agent,
    trainset=examples,
    critic=critic_agent,
)
```

## Evolvable Components

| Component | Type | What It Controls |
|-----------|------|------------------|
| `instruction` | `str` | The agent's prompt/instructions |
| `output_schema` | `type[BaseModel]` | Pydantic model for structured output |
| `generate_content_config` | `GenerateContentConfig` | LLM parameters (temperature, etc.) |

These three have built-in handlers. By default, only `instruction` evolves. Specify others explicitly:

```python
result = await evolve(
    agent=my_agent,
    trainset=examples,
    components=["instruction", "output_schema"],
)
```

`components` is not limited to these names. `evolve()` resolves every name through a component handler registry (`registry=`, defaulting to the shared default registry), and any name with a handler works:

- `register_mapping_components(mapping)` (exported from `gepa_adk`) registers one component per key of a `dict[str, str]` of prompt strings, so prompts that live outside the agent can evolve too.
- `register_handler(name, handler)` (from `gepa_adk.adapters.components`) registers a custom `ComponentHandler`.

A name with no handler is rejected with a `ConfigurationError` before evolution starts.

## Scoring

Every evaluated output needs a score. `evolve()` picks the scorer in this order:

| Option | When | Scorer |
|--------|------|--------|
| `scorer=` | Any object implementing the `Scorer` protocol (`score` and `async_score`), such as `LabelAgreementScorer` for labelled rows | Used as-is |
| `critic=` | An `LlmAgent` that judges the output | Wrapped in `CriticScorer` |
| Neither | The evolving agent has an `output_schema` with a `score` field | `SchemaBasedScorer` reads the agent's self-reported score |

`critic` and `scorer` are mutually exclusive. With none of the three, `evolve()` raises a `ConfigurationError`. The rest of this page covers the critic, the most common choice; the [Critic Agents Guide](../guides/critic-agents.md) covers schema scoring and custom scorers in practice.

## The Critic Agent

The critic evaluates agent outputs and provides feedback for reflection.

### Output Schemas

**SimpleCriticOutput** - Basic evaluation:
```python
class SimpleCriticOutput(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)  # Required
    feedback: str = Field(...)                  # Required
```

**CriticOutput** - Advanced with dimensions:
```python
class CriticOutput(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)  # Required
    feedback: str = Field(default="")           # Optional
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    actionable_guidance: str = Field(default="")
```

### Default Instructions

**Simple critic:**
```
Evaluate the quality of the output.

Provide:
- A score from 0.0 (poor) to 1.0 (excellent)
- Feedback explaining what works and what doesn't

Focus on clarity, accuracy, and completeness in your evaluation.
```

**Advanced critic:**
```
Evaluate the quality of the output across multiple dimensions.

Provide:
- An overall score from 0.0 (poor) to 1.0 (excellent)
- Feedback explaining what works and what doesn't
- Dimension scores for specific quality aspects you identify
- Actionable guidance for concrete improvement steps

Be specific in your feedback - quote passages that work or don't work,
and suggest alternatives where appropriate.
```

These are `SIMPLE_CRITIC_INSTRUCTION` and `ADVANCED_CRITIC_INSTRUCTION` in `gepa_adk.adapters.scoring.critic_scorer`.

### Critic Requirements

| Requirement | Details |
|-------------|---------|
| **Output Format** | JSON with `score` field (required) |
| **Score Range** | 0.0 to 1.0 (float) |
| **Feedback** | Recommended for reflection quality |
| **Normalization** | `normalize_feedback()` converts to trial format |

## The Reflection Agent

The reflection agent analyzes trial results and proposes improved component text.

### Default Reflection Agent

Unless `reflection_agent=` is passed, `evolve()` builds **one** `LlmAgent` named `reflection_agent` on `EvolutionConfig.reflection_model`, with `EvolutionConfig.reflection_prompt` as its instruction or, when that is unset, the default below (`REFLECTION_INSTRUCTION`). That single agent reflects on every evolved component, whatever its name.

```
## Component Text to Improve
{component_text}

## Trials
{trials}

Propose an improved version of the component text based on the trials above.
Return ONLY the improved component text, nothing else.
```

### Component-Aware Reflection Agents (Opt-In)

`gepa_adk.adapters.agents` provides factories for reflection agents tuned to one kind of component. `evolve()` does not pick them automatically: build one and pass it as `reflection_agent=`, and it then reflects on every component of that run.

| Component | Factory | Special Tools |
|-----------|---------|---------------|
| `output_schema` | `create_schema_reflection_agent` | `validate_output_schema` tool |
| `generate_content_config` | `create_config_reflection_agent` | None (YAML validation) |
| *other text* | `create_text_reflection_agent` | None |

`get_reflection_agent(component_name, model)` returns the factory's agent for a component name, falling back to the text agent.

### Reflection Requirements

| Requirement | Details |
|-------------|---------|
| **Placeholders** | Must accept `{component_text}` and `{trials}` |
| **Output Key** | `proposed_component_text`; set on the agent when it has no `output_key` of its own |
| **Return Format** | Plain text (the improved component) |
| **Session State** | Receives `component_text` (str) and `trials` (JSON string) |

## Trial Structure

`make_reflective_dataset` returns one list of <trial:trials> per component. Each record has exactly two keys, <trial:feedback> and <trial:trajectory>:

```python
{
    "feedback": {
        "score": 0.85,               # From the scorer
        "feedback_text": "...",      # From the scorer; "" when it gave none
        "dimensions": {...},         # When the critic returned dimension_scores
        "guidance": "..."            # When the critic returned actionable_guidance
    },
    "trajectory": {
        "input": "...",              # Original task input
        "output": "...",             # Agent's generated output
        "trace": {...}               # Only when tool calls, tokens or an error were recorded
    }
}
```

The trajectory captures execution context—tool calls, state changes, token usage—that helps the reflection agent understand *how* the agent arrived at its output.

## How Critic + Reflection Work Together

```
┌─────────────┐    output    ┌─────────────┐    score,     ┌─────────────────┐
│   Agent     │─────────────▶│   Critic    │───feedback───▶│  Trial Builder  │
│  (evolving) │              │  (scoring)  │               │                 │
└─────────────┘              └─────────────┘               └────────┬────────┘
                                                                    │
                                                                    │ trials
                                                                    ▼
┌─────────────┐    proposed   ┌─────────────────┐                   │
│  Component  │◀─────text─────│   Reflection    │◀──────────────────┘
│   Handler   │               │     Agent       │
└─────────────┘               └─────────────────┘
```

**The flow:**

1. **Agent** produces output from input
2. **Critic** (or another scorer) scores output → `{score, feedback, dimension_scores, actionable_guidance}`
3. **Trial Builder** combines into `{feedback, trajectory}`
4. **Reflection Agent** receives `{component_text, trials}` → proposes improvement
5. **Component Handler** applies proposed text to candidate
6. **Engine** evaluates the proposal → accepts it only if its aggregate score beats the best by more than `min_improvement_threshold` (see the [acceptance rule](gepa-fundamentals.md#acceptance-rule))

When `valset` is omitted, the trainset batch is reused for scoring, so each candidate costs one evaluation pass (plus the minibatch pass when `reflection_minibatch_size` is set).

## Example: Complete Single-Agent Evolution

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from gepa_adk import evolve, SimpleCriticOutput

# Agent to evolve
writer = LlmAgent(
    name="writer",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Write a haiku about the given topic.",
)

# Critic to evaluate
critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="""
    Evaluate this haiku for:
    - Correct 5-7-5 syllable structure
    - Imagery and emotional impact
    - Connection to the topic

    Score 0.0-1.0 and explain your reasoning.
    """,
    output_schema=SimpleCriticOutput,
)

# Training examples
trainset = [
    {"topic": "autumn leaves"},
    {"topic": "morning coffee"},
    {"topic": "city rain"},
]

# Run evolution
result = await evolve(
    agent=writer,
    trainset=trainset,
    critic=critic,
)

print(f"Improved: {result.original_score:.2f} → {result.final_score:.2f}")
print(f"New instruction: {result.evolved_components['instruction']}")
```

## Next Steps

- [Multi-Agent Evolution](multi-agent-evolution.md) - How multiple agents evolve together
- [Workflow Agents](workflow-agents.md) - How workflow structures evolve
- [Critic Agents Guide](../guides/critic-agents.md) - Practical guide to building critics

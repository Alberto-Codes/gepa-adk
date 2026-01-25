# Single-Agent Evolution

This document explains how single-agent evolution works, including the roles of critic and reflection agents, trial structure, and how they work together.

## Overview

Single-agent evolution optimizes one agent's components (instruction, output_schema, generate_content_config) through iterative improvement.

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

By default, only `instruction` evolves. Specify others explicitly:

```python
result = await evolve(
    agent=my_agent,
    trainset=examples,
    components=["instruction", "output_schema"],
)
```

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
```

### Critic Requirements

| Requirement | Details |
|-------------|---------|
| **Output Format** | JSON with `score` field (required) |
| **Score Range** | 0.0 to 1.0 (float) |
| **Feedback** | Recommended for reflection quality |
| **Normalization** | `normalize_feedback()` converts to trial format |

## The Reflection Agent

The reflection agent analyzes trial results and proposes improved component text.

### Default Instruction

```
## Component Text to Improve
{component_text}

## Trials
{trials}

Propose an improved version of the component text based on the trials above.
Return ONLY the improved component text, nothing else.
```

### Component-Aware Reflection

Different components get specialized reflection agents:

| Component | Factory | Special Tools |
|-----------|---------|---------------|
| `output_schema` | `create_schema_reflection_agent` | `validate_output_schema` tool |
| `generate_content_config` | `create_config_reflection_agent` | None (YAML validation) |
| *default* | `create_text_reflection_agent` | None |

### Reflection Requirements

| Requirement | Details |
|-------------|---------|
| **Placeholders** | Must accept `{component_text}` and `{trials}` |
| **Output Key** | Must use `output_key="proposed_component_text"` |
| **Return Format** | Plain text (the improved component) |
| **Session State** | Receives `component_text` (str) and `trials` (JSON string) |

## Trial Structure

Each trial record passed to reflection contains:

```python
{
    "feedback": {
        "score": 0.85,              # From critic
        "feedback_text": "...",      # From critic
        "dimension_scores": {...},   # Optional
        "actionable_guidance": "..." # Optional
    },
    "trajectory": {
        "input": "...",             # Original task input
        "output": "...",            # Agent's generated output
        "trace": {...}              # ADK execution trace
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
2. **Critic** scores output → `{score, feedback, dimensions, guidance}`
3. **Trial Builder** combines into `{feedback, trajectory}`
4. **Reflection Agent** receives `{component_text, trials}` → proposes improvement
5. **Component Handler** applies proposed text to candidate
6. **Engine** re-evaluates → accepts if score improves

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

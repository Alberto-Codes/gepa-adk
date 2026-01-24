# Multi-Agent Evolution

This document explains how multiple agents evolve together via `evolve_group()`, including qualified component names, session sharing, and round-robin iteration.

## Overview

Multi-agent evolution optimizes multiple agents that work together, sharing session state and cycling through components.

```python
from gepa_adk import evolve_group

result = await evolve_group(
    agents={"generator": gen, "reviewer": rev},
    primary="reviewer",
    trainset=examples,
)
```

## Qualified Component Names (ADR-012)

Multi-agent evolution uses **dot-separated qualified names** to address components:

```
{agent_name}.{component_name}
```

**Examples:**
- `generator.instruction`
- `critic.output_schema`
- `refiner.generate_content_config`

**Why dot separator?** ADK agent names are Python identifiers (no dots allowed), so parsing is always unambiguous.

```python
from gepa_adk.domain.types import ComponentSpec

# Construction
spec = ComponentSpec(agent="generator", component="instruction")
name = spec.qualified  # "generator.instruction"

# Parsing
spec = ComponentSpec.parse("critic.output_schema")
print(spec.agent)      # "critic"
print(spec.component)  # "output_schema"
```

## Per-Agent Component Configuration

The `components` parameter controls which components evolve for each agent:

```python
result = await evolve_group(
    agents={"generator": gen, "reviewer": rev, "validator": val},
    primary="reviewer",
    trainset=trainset,
    components={
        "generator": ["instruction"],                # Evolve instruction only
        "reviewer": ["instruction", "output_schema"], # Evolve both
        "validator": [],                             # Exclude from evolution
    },
)
```

| Configuration | Effect |
|--------------|--------|
| `["instruction"]` | Evolve only the instruction |
| `["instruction", "output_schema"]` | Evolve both components |
| `[]` | Agent participates but is NOT evolved |

## Session State Sharing

Agents share state through ADK's `output_key` mechanism:

```python
# Generator 1 saves output to session state
generator1 = LlmAgent(
    name="generator1",
    instruction="Generate initial content...",
    output_key="gen1_output",  # Saves to session.state["gen1_output"]
)

# Generator 2 references it via template
generator2 = LlmAgent(
    name="generator2",
    instruction=(
        "You received this initial response:\n"
        "{gen1_output}\n\n"  # ADK substitutes from session state
        "Expand and improve this response..."
    ),
    output_key="gen2_output",
)
```

**State flow:**
```
┌─────────────┐   output_key    ┌─────────────────┐   {gen1_output}   ┌─────────────┐
│ Generator 1 │────────────────▶│  session.state  │──────────────────▶│ Generator 2 │
└─────────────┘                 │ ["gen1_output"] │                   └─────────────┘
                                └─────────────────┘
```

## Round-Robin Iteration

The engine cycles through components each iteration:

```python
result = await evolve_group(
    agents={"generator": gen, "reviewer": rev},
    primary="reviewer",
    trainset=trainset,
    config=EvolutionConfig(max_iterations=4),
)

# Inspect which component was evolved each iteration
for record in result.iteration_history:
    print(f"Iteration {record.iteration_number}: {record.evolved_component}")
```

Output:
```
Iteration 1: generator.instruction
Iteration 2: reviewer.instruction
Iteration 3: generator.instruction
Iteration 4: reviewer.instruction
```

Each iteration:
1. Select next component in round-robin order
2. Run evaluation with current candidate
3. Build reflective dataset for that component
4. Propose improved text
5. Accept/reject based on score comparison

## Primary Agent

The `primary` parameter designates which agent's output is scored:

```python
result = await evolve_group(
    agents={"generator": gen, "reviewer": rev, "validator": val},
    primary="reviewer",  # Critic scores reviewer's output
    trainset=trainset,
)
```

Even when evolving the generator, the **final score** comes from the primary agent's output. This answers: "did improving the generator make the overall pipeline better?"

## Trial Structure (Extended)

Multi-agent trials include additional component context:

```python
{
    "feedback": {
        "score": 0.7,
        "feedback_text": "...",
        "dimension_scores": {...},       # Optional
        "actionable_guidance": "..."     # Optional
    },
    "trajectory": {
        "input": "...",
        "output": "...",
        "component": "generator.instruction",  # Which component
        "component_value": "current instruction text...",
        "tokens": 1234                   # Total token usage
    }
}
```

The `component` field tells the reflection agent which specific component the trial is evaluating.

## How Multi-Agent Evolution Works

```
┌─────────────┐  output_key  ┌─────────────┐  output_key  ┌─────────────┐
│ Generator 1 │─────────────▶│ Generator 2 │─────────────▶│   Critic    │
│  (evolving) │              │  (evolving) │              │  (scoring)  │
└─────────────┘              └─────────────┘              └──────┬──────┘
                                                                 │
                                   score, feedback               │
                    ┌────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│         Trial Builder               │
│  - Builds trial per example         │
│  - Adds component context           │
└──────────────────┬──────────────────┘
                   │ trials
                   ▼
┌─────────────────────────────────────┐
│       Reflection Agent              │
│  - Receives {component_text, trials}│
│  - Proposes improved instruction    │
└──────────────────┬──────────────────┘
                   │ proposed text
                   ▼
┌─────────────────────────────────────┐
│       Round-Robin Selector          │
│  - Iter 1: generator1.instruction   │
│  - Iter 2: generator2.instruction   │
│  - Iter 3: generator1.instruction   │
└─────────────────────────────────────┘
```

## Key Differences from Single Agent

| Aspect | Single Agent | Multi-Agent |
|--------|--------------|-------------|
| **Component Names** | `instruction` | `generator.instruction` |
| **Configuration** | `components=["instruction"]` | `components={"gen": ["instruction"]}` |
| **Session State** | Isolated | Shared via `output_key` |
| **Iteration** | Same component each time | Round-robin across agents |
| **Trajectory** | Single agent trace | Per-agent via `partition_events_by_agent()` |

## Example: Generator-Reviewer Pipeline

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve_group
from gepa_adk.domain import SimpleCriticOutput, EvolutionConfig

# Generator creates content
generator = LlmAgent(
    name="generator",
    model="gemini-2.0-flash",
    instruction="Write a product description for the given item.",
    output_key="draft",
)

# Reviewer improves it
reviewer = LlmAgent(
    name="reviewer",
    model="gemini-2.0-flash",
    instruction="""
    Review and improve this draft:
    {draft}

    Make it more compelling and concise.
    """,
    output_key="final",
)

# Critic evaluates final output
critic = LlmAgent(
    name="critic",
    model="gemini-2.0-flash",
    instruction="Evaluate this product description for clarity and persuasiveness.",
    output_schema=SimpleCriticOutput,
)

# Training examples
trainset = [
    {"item": "wireless headphones"},
    {"item": "coffee maker"},
    {"item": "running shoes"},
]

# Evolve both agents
result = await evolve_group(
    agents={"generator": generator, "reviewer": reviewer},
    primary="reviewer",
    trainset=trainset,
    critic=critic,
    config=EvolutionConfig(max_iterations=6),
)

# See what evolved
for name, text in result.evolved_components.items():
    print(f"{name}: {text[:50]}...")
```

## Next Steps

- [Workflow Agents](workflow-agents.md) - How workflow structures evolve
- [Multi-Agent Guide](../guides/multi-agent.md) - Practical guide to multi-agent evolution
- [ADR-012](../adr/ADR-012-multi-agent-component-addressing.md) - Component addressing decision

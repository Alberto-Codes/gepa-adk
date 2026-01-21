# Quickstart: Multi-Agent Component Routing

**Feature**: 166-multi-agent-routing
**Date**: 2026-01-20

## Overview

This feature enables evolving different components on different agents in multi-agent GEPA evolution runs. You can now optimize a generator's `output_schema` while simultaneously tuning a critic's `generate_content_config`.

## Prerequisites

- gepa-adk >= 0.3.0 (breaking API change from 0.2.x)
- Familiarity with [Multi-Agent Guide](../../docs/guides/multi-agent.md)
- Understanding of [ADR-012: Multi-Agent Component Addressing](../../docs/adr/ADR-012-multi-agent-component-addressing.md)

## Basic Usage

### Define Agents with Names

```python
from google.adk.agents import LlmAgent

generator = LlmAgent(
    name="generator",
    model="gemini-1.5-flash",
    instruction="Generate creative stories based on the prompt.",
)

refiner = LlmAgent(
    name="refiner",
    model="gemini-1.5-flash",
    instruction="Improve the story's clarity and engagement.",
)

critic = LlmAgent(
    name="critic",
    model="gemini-1.5-flash",
    instruction="Evaluate the story's quality.",
)
```

### Configure Per-Agent Components

```python
from gepa_adk import evolve_group

result = await evolve_group(
    agents={"generator": generator, "refiner": refiner, "critic": critic},
    primary="generator",
    trainset=trainset,
    components={
        "generator": ["instruction", "output_schema"],
        "refiner": ["instruction"],
        "critic": ["generate_content_config"],
    },
)
```

### Access Evolved Components

```python
# Components are returned with qualified names (agent.component)
print(result.evolved_components)
# {
#     "generator.instruction": "Generate imaginative stories...",
#     "generator.output_schema": "class Story(BaseModel): ...",
#     "refiner.instruction": "Polish the narrative...",
#     "critic.generate_content_config": "temperature: 0.3\nmax_tokens: 512",
# }

# Apply to specific agent
generator.instruction = result.evolved_components["generator.instruction"]
```

## Key Concepts

### Qualified Component Names

Components are addressed using dot notation: `{agent_name}.{component_name}`

| Qualified Name | Agent | Component |
|----------------|-------|-----------|
| `generator.instruction` | generator | instruction |
| `critic.output_schema` | critic | output_schema |
| `refiner.generate_content_config` | refiner | generate_content_config |

### Available Components

| Component | Description |
|-----------|-------------|
| `instruction` | Agent's system instruction |
| `output_schema` | Structured output Pydantic model |
| `generate_content_config` | LLM generation parameters (temperature, max_tokens, etc.) |

### Migration from 0.2.x

The API has breaking changes from 0.2.x:

```python
# OLD (0.2.x) - No longer works
evolve_group(agents=[gen, critic], primary="generator", ...)

# NEW (0.3.x) - Explicit agents dict and components required
evolve_group(
    agents={"generator": gen, "critic": critic},
    primary="generator",
    components={"generator": ["instruction"], "critic": ["instruction"]},
    ...
)
```

## Common Patterns

### Evolve Different Agents Differently

```python
components = {
    "summarizer": ["instruction"],           # Text-focused
    "formatter": ["output_schema"],          # Structure-focused
    "evaluator": ["generate_content_config"], # Behavior-focused
}
```

### Skip Agent Evolution

```python
components = {
    "generator": ["instruction", "output_schema"],
    "validator": [],  # Empty list = no evolution for this agent
}
```

## Error Handling

### Unknown Agent

```python
# Raises ValueError
components = {"nonexistent": ["instruction"]}
# Error: Agent 'nonexistent' not found. Available: ['generator', 'critic']
```

### Unknown Component

```python
# Raises ValueError
components = {"generator": ["unknown_component"]}
# Error: No handler for 'unknown_component'. Available: ['instruction', 'output_schema', 'generate_content_config']
```

## Next Steps

- [Multi-Agent Guide](../../docs/guides/multi-agent.md) - Full multi-agent documentation
- [ADR-012](../../docs/adr/ADR-012-multi-agent-component-addressing.md) - Addressing scheme rationale
- [Examples](../../examples/multi_agent_component_demo.py) - Complete working example

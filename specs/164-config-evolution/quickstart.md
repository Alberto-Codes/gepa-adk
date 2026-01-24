# Quickstart: Generate Content Config Evolution

**Feature**: 164-config-evolution
**Date**: 2026-01-20

## Overview

This guide shows how to evolve an agent's `generate_content_config` to optimize LLM generation parameters like temperature, top_p, and max_output_tokens.

## Prerequisites

- gepa-adk installed with ADK dependencies
- An LlmAgent with `generate_content_config` set

## Basic Usage

### 1. Configure Evolution with Config Component

```python
from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

from gepa_adk import evolve

# Create agent with initial config
agent = LlmAgent(
    name="my_agent",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant.",
    generate_content_config=GenerateContentConfig(
        temperature=0.7,
        top_p=0.9,
        max_output_tokens=1024,
    ),
)

# Define evaluation examples
examples = [
    {"input": "Explain quantum computing", "expected": "clear explanation"},
    {"input": "Write a haiku", "expected": "creative poem"},
]

# Evolve the config alongside instruction
result = await evolve(
    agent=agent,
    examples=examples,
    components=["instruction", "generate_content_config"],  # <-- Add config
    iterations=5,
)

print(f"Best config: {result.best_candidate}")
```

### 2. Evolve Config Only

```python
# Evolve just the generation parameters
result = await evolve(
    agent=agent,
    examples=examples,
    components=["generate_content_config"],  # Only config
    iterations=10,
)
```

### 3. Access Evolved Config

```python
# After evolution, the agent has the best config applied
print(f"Temperature: {agent.generate_content_config.temperature}")
print(f"Top P: {agent.generate_content_config.top_p}")
print(f"Max tokens: {agent.generate_content_config.max_output_tokens}")
```

## Working with the Handler Directly

For advanced use cases, you can use the handler directly:

```python
from gepa_adk.adapters import get_handler

# Get the config handler
handler = get_handler("generate_content_config")

# Serialize current config to YAML
yaml_text = handler.serialize(agent)
print(yaml_text)
# Output:
# # LLM Generation Parameters
# # temperature: Controls randomness (0.0=deterministic, 2.0=creative)
# temperature: 0.7
# # top_p: Nucleus sampling threshold (0.0-1.0)
# top_p: 0.9
# # max_output_tokens: Maximum response length
# max_output_tokens: 1024

# Apply a new config
new_yaml = """
temperature: 0.5
top_p: 0.8
max_output_tokens: 2048
"""
original = handler.apply(agent, new_yaml)

# ... use agent with new config ...

# Restore original config
handler.restore(agent, original)
```

## Using Config Utilities

For validation and serialization without a handler:

```python
from gepa_adk.utils.config_utils import (
    serialize_generate_config,
    deserialize_generate_config,
    validate_generate_config,
)

# Serialize a config
yaml_text = serialize_generate_config(agent.generate_content_config)

# Validate before applying
errors = validate_generate_config({"temperature": 3.0})
if errors:
    print(f"Validation errors: {errors}")
    # Output: ["temperature must be 0.0-2.0, got 3.0"]

# Deserialize with merge
existing = agent.generate_content_config
new_config = deserialize_generate_config(
    "temperature: 0.5",
    existing=existing,  # Merge with existing
)
# new_config has temperature=0.5, but preserves other params from existing
```

## Parameter Guidelines

When evolving generation config, the reflection agent considers:

| Parameter | Low Values | High Values |
|-----------|------------|-------------|
| `temperature` | Deterministic, focused (0.0-0.3) | Creative, varied (0.7-1.5) |
| `top_p` | More focused output (0.5-0.8) | More diverse (0.9-1.0) |
| `top_k` | Constrained vocabulary (10-30) | Broader vocabulary (50-100) |
| `max_output_tokens` | Short responses | Long responses |

## Common Patterns

### Creative Tasks

```python
config = GenerateContentConfig(
    temperature=1.0,
    top_p=0.95,
    max_output_tokens=2048,
)
```

### Deterministic Tasks

```python
config = GenerateContentConfig(
    temperature=0.0,
    top_p=0.1,
    max_output_tokens=512,
)
```

### Balanced (Default)

```python
config = GenerateContentConfig(
    temperature=0.7,
    top_p=0.9,
    max_output_tokens=1024,
)
```

## Error Handling

Invalid configs are gracefully handled:

```python
# Out-of-range values are rejected
handler.apply(agent, "temperature: 999")
# Agent config unchanged, warning logged

# Malformed YAML is rejected
handler.apply(agent, "{{invalid")
# Agent config unchanged, warning logged
```

## Next Steps

- See [Single-Agent Guide](docs/guides/single-agent.md) for full evolution workflow
- See [API Reference](docs/reference/) for detailed API documentation
- Check [examples/config_evolution_demo.py](examples/config_evolution_demo.py) for complete example

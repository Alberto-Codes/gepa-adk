# Quickstart: Component-Aware Reflection Agents

**Feature**: 142-component-aware-reflection

## Overview

This feature enables automatic validation of `output_schema` proposals during evolution. When the reflection agent proposes a new Pydantic schema, it can validate the schema syntax before returning, reducing wasted iterations on invalid proposals.

## Basic Usage

### Default Behavior (Zero Configuration)

The system automatically detects when you're evolving `output_schema` and uses a validation-enabled reflection agent:

```python
from gepa_adk import evolve_sync
from google.adk.agents import LlmAgent
from pydantic import BaseModel

# Define initial schema as component text
initial_schema = '''
class ResponseSchema(BaseModel):
    answer: str
    confidence: float
'''

# Create agent with output_schema component
agent = LlmAgent(
    name="my_agent",
    model="gemini-2.0-flash",
    instruction="Answer questions accurately",
)

# Run evolution - system auto-detects output_schema needs validation
result = evolve_sync(
    agent=agent,
    trainset=[...],
    components={"output_schema": initial_schema},  # Auto-validated!
    max_iterations=10,
)

# All proposed schemas during reflection were validated
print(result.best_candidate["output_schema"])
```

### Explicit Agent Selection

If you need more control, you can explicitly create and use reflection agents:

```python
from gepa_adk.engine.reflection_agents import (
    create_schema_reflection_agent,
    create_text_reflection_agent,
)

# For schema components
schema_agent = create_schema_reflection_agent(model="gemini-2.0-flash")

# For text components (instructions, descriptions)
text_agent = create_text_reflection_agent(model="gemini-2.0-flash")
```

### Custom Reflection Agent

To use your own reflection agent with custom tools:

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from gepa_adk import evolve_sync

# Define custom validation tool
def my_validator(text: str) -> dict:
    """Validate my custom format."""
    is_valid = "REQUIRED_PREFIX" in text
    return {"valid": is_valid, "errors": [] if is_valid else ["Missing prefix"]}

# Create custom reflection agent
custom_agent = LlmAgent(
    name="custom_reflector",
    model="gemini-2.0-flash",
    instruction="Improve the text. Use my_validator to check format.",
    tools=[FunctionTool(my_validator)],
)

# Use custom agent for evolution
result = evolve_sync(
    agent=my_agent,
    trainset=[...],
    reflection_agent=custom_agent,  # Override auto-selection
)
```

## How It Works

1. **Component Detection**: When evolution starts, the system checks which component is being evolved
2. **Agent Selection**: Based on component name, the appropriate reflection agent is selected:
   - `output_schema` → Schema reflection agent with validation tool
   - `instruction`, `description`, etc. → Text reflection agent (no validation)
3. **Validation Loop**: For schema components, the reflection agent:
   - Proposes a new schema
   - Calls `validate_output_schema` tool to check syntax
   - If invalid, fixes errors and retries
   - Returns only valid schemas

## Validation Tool

The `validate_output_schema` tool provides detailed feedback:

```python
# Valid schema
{
    "valid": True,
    "class_name": "ResponseSchema",
    "field_count": 2,
    "field_names": ["answer", "confidence"],
}

# Invalid schema
{
    "valid": False,
    "errors": ["SyntaxError: unexpected indent at line 5"],
    "stage": "syntax",
    "line_number": 5,
}
```

## Registry Extension

To add validators for new component types:

```python
from gepa_adk.engine.reflection_agents import (
    component_registry,
    create_text_reflection_agent,
)
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Define factory for your component type
def create_my_component_agent(model: str) -> LlmAgent:
    return LlmAgent(
        name="my_component_reflector",
        model=model,
        instruction="...",
        tools=[FunctionTool(my_validator)],
    )

# Register it
component_registry.register("my_component", create_my_component_agent)

# Now evolution will auto-select for "my_component"
```

## Backward Compatibility

Existing code continues to work unchanged:

```python
# This still works - uses default text reflection
result = evolve_sync(agent, trainset)

# This still works - custom agent is used as-is
result = evolve_sync(agent, trainset, reflection_agent=my_agent)
```

## Next Steps

- See [Single-Agent Guide](../../docs/guides/single-agent.md) for complete evolution documentation
- See [examples/schema_evolution_validated.py](../../examples/schema_evolution_validated.py) for a full example

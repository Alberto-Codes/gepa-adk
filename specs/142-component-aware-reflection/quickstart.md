# Quickstart: Component-Aware Reflection Agents

**Feature**: 142-component-aware-reflection

## Overview

This feature enables evolving different agent components (instruction, output_schema) with specialized reflection agents. When evolving `output_schema`, the system uses a schema reflection agent with validation tools.

**Key Insight**: LLMs fill ALL fields in their output_schema. If the schema has `reasoning: str`, the generator produces reasoning. This means evolving the schema directly affects generator output.

## How It Works

1. **Component Selection**: Use `components=["output_schema"]` in `evolve()` to specify which component to evolve
2. **Agent Selection**: Based on component name, the appropriate reflection agent is selected:
   - `output_schema` → Schema reflection agent with `validate_output_schema` tool
   - `instruction`, `description`, etc. → Text reflection agent (no validation)
3. **Schema Override**: During evaluation, the ADKAdapter applies proposed schemas to the agent
4. **Validation Loop**: For schema components, the reflection agent:
   - Proposes a new schema
   - Calls `validate_output_schema` tool to check syntax
   - If invalid, fixes errors and retries
   - Returns only valid schemas

## Evolving Output Schema

### Basic Usage with `components` Parameter

To evolve the output_schema instead of instruction:

```python
from gepa_adk import evolve
from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA

# Evolve output_schema component
result = await evolve(
    agent=my_agent,
    trainset=trainset,
    critic=critic,
    reflection_agent=schema_reflector,
    components=[COMPONENT_OUTPUT_SCHEMA],  # Evolve schema, not instruction
)

print(f"Evolved schema: {result.evolved_components['output_schema']}")
```

### Critical Setup: Harsh Critic for Structure

For schema evolution to work, the critic must score based on **JSON structure**, not content:

```python
class CriticOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str

critic = LlmAgent(
    name="structural_critic",
    model=model,
    instruction="""Score STRICTLY based on JSON fields present:

- 0.1-0.2: Only "response" field, NO other structural fields
- 0.3-0.4: response + ONE additional field (reasoning OR confidence)
- 0.5-0.6: response + TWO fields (reasoning AND confidence)
- 0.7-0.8: response + reasoning + confidence + key_points
- 0.9-1.0: 4+ meaningful structural fields

Be HARSH. Only "response" field = 0.1-0.2 score MAX.""",
    output_schema=CriticOutput,
)
```

This setup ensures:
1. Simple schema (just `response`) → low scores
2. Schema with more fields → higher scores
3. Evolution adds fields → generator fills them → scores improve

## Using Schema Reflection Agents

### Explicit Agent Creation

You can explicitly create and use reflection agents:

```python
from gepa_adk.engine.reflection_agents import (
    create_schema_reflection_agent,
    create_text_reflection_agent,
)

# For schema components - has validation tool
schema_agent = create_schema_reflection_agent(model="gemini-2.5-flash")

# For text components (instructions, descriptions) - no tools
text_agent = create_text_reflection_agent(model="gemini-2.5-flash")

# Use in evolution with components parameter
from gepa_adk import evolve_sync
from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA

result = evolve_sync(
    agent=my_agent,
    trainset=[...],
    critic=critic,
    reflection_agent=schema_agent,
    components=[COMPONENT_OUTPUT_SCHEMA],  # Specify which component to evolve
)
```

### Auto-Selection via Registry

The registry automatically selects the right reflection agent:

```python
from gepa_adk.engine.reflection_agents import get_reflection_agent

# Returns schema agent with validation tool
schema_agent = get_reflection_agent("output_schema", "gemini-2.5-flash")

# Returns text agent without tools
text_agent = get_reflection_agent("instruction", "gemini-2.5-flash")

# Unknown components default to text agent
fallback_agent = get_reflection_agent("my_custom", "gemini-2.5-flash")
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
    model="gemini-2.5-flash",
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

## Validation Tool

The `validate_output_schema` tool provides detailed feedback:

```python
from gepa_adk.utils.schema_tools import validate_output_schema

# Valid schema
result = validate_output_schema("""
class ResponseSchema(BaseModel):
    answer: str
    confidence: float
""")
# Returns:
# {
#     "valid": True,
#     "class_name": "ResponseSchema",
#     "field_count": 2,
#     "field_names": ["answer", "confidence"],
# }

# Invalid schema
result = validate_output_schema("""
class BadSchema(BaseModel):
    import os  # Not allowed!
""")
# Returns:
# {
#     "valid": False,
#     "errors": ["Import statements are not allowed..."],
#     "stage": "structure",
#     "line_number": 2,
# }
```

## Registry Extension

To add validators for new component types:

```python
from gepa_adk.engine.reflection_agents import component_registry
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

# Now get_reflection_agent will auto-select for "my_component"
agent = get_reflection_agent("my_component", "gemini-2.5-flash")
```

## Backward Compatibility

Existing code continues to work unchanged:

```python
# This still works - evolves instruction by default
result = evolve_sync(agent, trainset)

# This still works - custom agent is used as-is
result = evolve_sync(agent, trainset, reflection_agent=my_agent)

# New: Explicitly evolve output_schema
result = evolve_sync(
    agent,
    trainset,
    components=["output_schema"],  # New parameter
    reflection_agent=schema_agent,
)
```

## Supported Components

| Component | Description | Reflection Agent |
|-----------|-------------|------------------|
| `instruction` | Agent's instruction text (default) | Text reflection |
| `output_schema` | Agent's Pydantic output schema | Schema reflection with validation |

## Next Steps

- See [Single-Agent Guide](../../docs/guides/single-agent.md) for complete evolution documentation
- Run [examples/schema_evolution_critic.py](../../examples/schema_evolution_critic.py) for a working demo with structured output

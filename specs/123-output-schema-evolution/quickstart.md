# Quickstart: Output Schema Evolution

**Feature**: 123-output-schema-evolution
**Time to Complete**: ~15 minutes

## Overview

This guide shows how to evolve a Pydantic output schema alongside agent instructions using gepa-adk.

## Prerequisites

- gepa-adk installed (`uv add gepa-adk`)
- An LLM provider configured (e.g., Gemini, Ollama)

## Basic Usage

### 1. Define Your Agent with Output Schema

```python
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent

class StoryOutput(BaseModel):
    """Output schema for story generation."""
    title: str = Field(description="Story title")
    content: str = Field(description="Story content")
    genre: str = Field(description="Story genre")

agent = LlmAgent(
    name="story_generator",
    model="gemini-2.5-flash",
    instruction="Generate a creative short story based on the prompt.",
    output_schema=StoryOutput,
)
```

### 2. Prepare Training Data

```python
from gepa_adk import TrainExample

train_data = [
    TrainExample(
        input="Write about a robot learning to paint",
        expected="A touching story about creativity and identity",
    ),
    TrainExample(
        input="Write about a time traveler's dilemma",
        expected="A thought-provoking tale about choices",
    ),
    # ... more examples
]
```

### 3. Evolve the Output Schema

```python
from gepa_adk import evolve, EvolutionConfig

# Configure evolution to target output_schema
config = EvolutionConfig(
    max_iterations=20,
    patience=5,
)

# Evolve with output_schema as the component
result = await evolve(
    agent=agent,
    train_data=train_data,
    components=["output_schema"],  # Target output_schema for evolution
    config=config,
)

print(f"Evolved schema:\n{result.evolved_component_text}")
```

### 4. Apply Evolved Schema

```python
from gepa_adk.utils.schema_utils import deserialize_schema

# Deserialize the evolved schema text to a usable class
EvolvedStoryOutput = deserialize_schema(result.evolved_component_text)

# Apply to agent
agent.output_schema = EvolvedStoryOutput
```

## Evolving Both Instruction and Output Schema

You can evolve multiple components simultaneously:

```python
result = await evolve(
    agent=agent,
    train_data=train_data,
    components=["instruction", "output_schema"],  # Both components
    config=config,
)

# Result contains evolved text for primary component
# Access all components via the candidate
```

## Common Patterns

### Pattern: Schema with Constraints

```python
class ConstrainedOutput(BaseModel):
    """Schema with validation constraints."""
    score: float = Field(ge=0.0, le=1.0, description="Quality score")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level")
    category: str = Field(min_length=1, max_length=50)
```

### Pattern: Schema with Optional Fields

```python
class FlexibleOutput(BaseModel):
    """Schema with optional fields."""
    primary_result: str
    secondary_result: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
```

### Pattern: Nested Schemas

```python
class InnerResult(BaseModel):
    value: str
    confidence: float

class OuterOutput(BaseModel):
    results: list[InnerResult]
    summary: str
```

**Note**: For nested schemas, ensure all classes are defined in the same schema text or use simple types.

## Validation Requirements

Evolved schemas must satisfy these requirements:

1. **Self-contained**: No import statements allowed
2. **BaseModel subclass**: Must inherit from `pydantic.BaseModel`
3. **No custom validators**: `@validator` decorators not allowed
4. **No method definitions**: Only field definitions

## Troubleshooting

### SchemaValidationError: Import not allowed

The LLM proposed a schema with import statements. The validator rejects these for security. Ensure your prompt instructs the LLM to produce self-contained schemas.

### SchemaValidationError: No BaseModel subclass found

The proposed text doesn't define a class inheriting from BaseModel. Check the evolved text and ensure the reflection prompt encourages proper Pydantic syntax.

### OSError: Could not get source

The original schema class was defined dynamically or in an interactive session. Use `inspect.getsource()` only on classes defined in .py files.

## Next Steps

- [Critic Agents Guide](../../docs/guides/critic-agents.md) - Add evaluation criteria
- [Multi-Agent Evolution](../../docs/guides/multi-agent.md) - Evolve multiple agents
- [Workflows Guide](../../docs/guides/workflows.md) - Complex evolution patterns

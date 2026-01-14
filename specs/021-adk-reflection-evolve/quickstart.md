# Quickstart: Wire ADK Reflection Agent into evolve() API

**Feature Branch**: `021-adk-reflection-evolve`
**Date**: 2026-01-14

## What This Feature Does

Enables users to pass a custom ADK LlmAgent for reflection during evolution, providing:
- ADK observability (traces, metrics)
- Customizable reflection prompts
- Integration with ADK session management

## Prerequisites

- gepa-adk installed
- Google ADK configured with valid credentials
- Understanding of LlmAgent configuration

## Basic Usage

### 1. Create a Reflection Agent

```python
from google.adk.agents import LlmAgent

reflection_agent = LlmAgent(
    name="instructor",
    model="gemini-2.0-flash",
    instruction="""You are an instruction optimizer.

Analyze the current instruction and feedback, then generate an improved version.

Current instruction:
{current_instruction}

Execution feedback:
{execution_feedback}

Based on the feedback, identify what's working and what needs improvement.
Return only the improved instruction text, with no additional commentary.""",
)
```

### 2. Evolve with Custom Reflection

```python
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from gepa_adk import evolve


class OutputSchema(BaseModel):
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)


# Target agent to evolve
agent = LlmAgent(
    name="assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant.",
    output_schema=OutputSchema,
)

# Training data
trainset = [
    {"input": "What is 2+2?", "expected": "4"},
    {"input": "Capital of France?", "expected": "Paris"},
]

# Evolve with ADK reflection
result = await evolve(
    agent=agent,
    trainset=trainset,
    reflection_agent=reflection_agent,  # <-- ADK-based reflection
)

print(f"Evolved: {result.evolved_instruction}")
```

## What Changes

| Before | After |
|--------|-------|
| `reflection_agent` parameter ignored | `reflection_agent` used for ADK reflection |
| Warning logged when `reflection_agent` provided | No warning; debug log confirms configuration |
| Always uses LiteLLM for reflection | Uses ADK Runner when `reflection_agent` provided |

## Observability

With ADK reflection enabled, you get:

1. **Traces**: Reflection calls appear in ADK tracing
2. **Session State**: Each reflection creates a session with:
   - `current_instruction`: The instruction being improved
   - `execution_feedback`: JSON-serialized evaluation results

### Viewing Traces

```python
import os
os.environ["GOOGLE_CLOUD_PROJECT"] = "your-project"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path/to/credentials.json"

# Traces automatically captured when using ADK reflection
result = await evolve(agent, trainset, reflection_agent=reflection_agent)

# View traces in Google Cloud Console or local ADK UI
```

## Default Behavior (Unchanged)

If you don't provide `reflection_agent`, behavior is unchanged:

```python
# Uses LiteLLM for reflection (default)
result = await evolve(agent, trainset)
```

## Error Handling

```python
# Invalid reflection_agent raises TypeError
try:
    result = await evolve(
        agent=agent,
        trainset=trainset,
        reflection_agent="not_an_agent",  # Wrong type
    )
except TypeError as e:
    print(e)  # "reflection_agent must be LlmAgent, got <class 'str'>"
```

## Testing Your Reflection Agent

Before using in evolution, test the reflection agent directly:

```python
from gepa_adk.engine import create_adk_reflection_fn

# Create the reflection function
reflect = create_adk_reflection_fn(reflection_agent)

# Test with sample data
improved = await reflect(
    current_instruction="Be helpful.",
    feedback=[
        {"score": 0.5, "input": "Hello", "output": "Hi", "expected": "Hello there!"},
    ],
)
print(f"Improved instruction: {improved}")
```

## Best Practices

1. **Prompt Engineering**: Design reflection prompts that:
   - Reference `{current_instruction}` and `{execution_feedback}` placeholders
   - Focus on specific improvements based on feedback
   - Return only the instruction text (no commentary)

2. **Model Selection**: Use capable models for reflection:
   - `gemini-2.0-flash` for speed
   - `gemini-1.5-pro` for complex reasoning

3. **Session Management**: For production, consider custom session services:
   ```python
   from google.adk.sessions import DatabaseSessionService

   # Sessions persist for debugging
   session_service = DatabaseSessionService(db_url="...")
   adapter = ADKAdapter(
       agent=agent,
       scorer=scorer,
       session_service=session_service,
       reflection_agent=reflection_agent,
   )
   ```

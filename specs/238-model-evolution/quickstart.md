# Quickstart: Model Evolution

## Basic Usage

Evolve the model alongside other components by providing `model_choices`:

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve

agent = LlmAgent(
    name="assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant.",
    output_schema=MyOutputSchema,
)

trainset = [
    {"input": "What is 2+2?", "expected": "4"},
    {"input": "Capital of France?", "expected": "Paris"},
]

# Evolve model from allowed choices
result = await evolve(
    agent,
    trainset,
    components=["instruction", "model"],  # Include "model" component
    model_choices=["gemini-2.0-flash", "gemini-1.5-flash", "gpt-4o"],
)

print(f"Best model: {result.evolved_components.get('model', 'unchanged')}")
print(f"Best instruction: {result.evolved_components['instruction']}")
```

## With Custom LiteLLM Wrapper

Model evolution preserves wrapper configuration:

```python
from google.adk.models.lite_llm import LiteLlm

# Custom wrapper with headers
wrapped_model = LiteLlm(
    model="ollama_chat/llama3",
    api_base="http://localhost:11434",
    custom_headers={"X-Custom": "value"},
)

agent = LlmAgent(
    name="assistant",
    model=wrapped_model,
    instruction="You are helpful.",
)

# Evolution changes only the model name, preserving wrapper config
result = await evolve(
    agent,
    trainset,
    components=["model"],
    model_choices=["ollama_chat/llama3", "ollama_chat/llama3.1"],
)
# wrapped_model.api_base and custom_headers are preserved
```

## Opt-in Behavior

Model evolution only occurs when explicitly requested:

```python
# Model NOT evolved (no model_choices)
result = await evolve(agent, trainset)

# Model NOT evolved (empty list)
result = await evolve(agent, trainset, model_choices=[])

# Model NOT evolved (single choice = no alternatives)
result = await evolve(agent, trainset, model_choices=["gemini-2.0-flash"])

# Model IS evolved (2+ choices)
result = await evolve(
    agent,
    trainset,
    components=["model"],
    model_choices=["gemini-2.0-flash", "gpt-4o"],
)
```

## Current Model Auto-included

Your current model is automatically added to the allowed list:

```python
agent = LlmAgent(model="gemini-2.0-flash", ...)

# gemini-2.0-flash is auto-added as baseline
result = await evolve(
    agent,
    trainset,
    components=["model"],
    model_choices=["gpt-4o", "claude-3-sonnet"],  # Current model auto-added
)
# Effective choices: ["gemini-2.0-flash", "gpt-4o", "claude-3-sonnet"]
```

## Key Points

1. **Opt-in**: Pass `model_choices` with 2+ models to enable model evolution
2. **Component inclusion**: Add `"model"` to the `components` list
3. **Wrapper preservation**: Custom headers, auth, and config are preserved
4. **Auto-baseline**: Current model always included in allowed choices

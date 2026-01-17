# Quickstart: Wire Reflection Model Config to Proposer

**Feature**: 031-wire-reflection-model
**Date**: 2026-01-17

## Overview

After this feature is implemented, users can configure which LLM model is used for reflection/mutation operations via `EvolutionConfig.reflection_model`.

## Usage Examples

### Basic Usage (Default Model)

```python
from gepa_adk import evolve, EvolutionConfig

# Uses default reflection_model="ollama_chat/gpt-oss:20b"
config = EvolutionConfig(max_iterations=50)

result = await evolve(
    agent=my_agent,
    trainset=my_trainset,
    scorer=my_scorer,
    config=config
)
```

### Custom Reflection Model

```python
from gepa_adk import evolve, EvolutionConfig

# Use a specific model for reflection
config = EvolutionConfig(
    max_iterations=50,
    reflection_model="gemini/gemini-2.5-pro"  # Production model
)

result = await evolve(
    agent=my_agent,
    trainset=my_trainset,
    scorer=my_scorer,
    config=config
)
```

### Using Ollama (Local Development)

```python
from gepa_adk import evolve, EvolutionConfig

# Use Ollama for local development
config = EvolutionConfig(
    max_iterations=50,
    reflection_model="ollama_chat/llama3:8b"  # Local Ollama model
)

result = await evolve(
    agent=my_agent,
    trainset=my_trainset,
    scorer=my_scorer,
    config=config
)
```

### Multi-Agent Evolution

```python
from gepa_adk import evolve_group, EvolutionConfig

# Works the same for multi-agent evolution
config = EvolutionConfig(
    max_iterations=30,
    reflection_model="anthropic/claude-3-haiku"
)

result = await evolve_group(
    agents=[generator_agent, critic_agent],
    primary="generator",
    trainset=my_trainset,
    scorer=my_scorer,
    config=config
)
```

## Supported Model Formats

The `reflection_model` value uses LiteLLM format:

| Provider | Format | Example |
|----------|--------|---------|
| Google | `gemini/{model}` | `gemini/gemini-2.0-flash` |
| OpenAI | `{model}` or `openai/{model}` | `gpt-4o-mini` |
| Anthropic | `anthropic/{model}` | `anthropic/claude-3-haiku` |
| Ollama | `ollama_chat/{model}` | `ollama_chat/llama3:8b` |
| Azure | `azure/{deployment}` | `azure/gpt-4-deployment` |

See [LiteLLM Providers](https://docs.litellm.ai/docs/providers) for the full list.

## Verifying the Model in Use

After the feature is implemented, the chosen model is logged at INFO level:

```
INFO     proposer_initialized               reflection_model=gemini/gemini-2.0-flash
```

## Error Handling

### Empty Model String

```python
# This raises ConfigurationError at config creation time
config = EvolutionConfig(reflection_model="")
# ConfigurationError: reflection_model must be a non-empty string
```

### Invalid Model at Runtime

```python
# Invalid models are passed to LiteLLM and error on first use
config = EvolutionConfig(reflection_model="invalid/nonexistent")
result = await evolve(...)
# LiteLLM raises appropriate error when first reflection call is made
```

## Migration Notes

### Before This Feature

```python
# Config had reflection_model but it was ignored
config = EvolutionConfig(reflection_model="gemini/gemini-2.0-flash")
# ^^^ This was silently ignored - proposer used hardcoded "ollama/gpt-oss:20b"
```

### After This Feature

```python
# Config reflection_model is now used
config = EvolutionConfig(reflection_model="gemini/gemini-2.0-flash")
# ^^^ Proposer correctly uses "gemini/gemini-2.0-flash"
```

No code changes needed for existing users who relied on the default - the new default (`"gemini-2.0-flash"`) is consistent with what was documented in `EvolutionConfig`.

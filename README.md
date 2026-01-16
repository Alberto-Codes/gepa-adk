# gepa-adk

Evolutionary optimization for Google ADK agents.

## What is this?

`gepa-adk` makes your AI agents better automatically. It takes an agent, runs it against examples, gets feedback, and evolves the agent's instructions until performance improves.

Think of it as natural selection for AI prompts—the best instructions survive and improve.

## Who is this for?

Teams building AI agents with Google's Agent Development Kit (ADK) who want to:

- Improve agent performance without manual prompt tweaking
- Use structured feedback (not just pass/fail) to guide improvements
- Evolve multiple agents working together
- Get 3-5x faster optimization through parallel evaluation

## Installation

### Prerequisites

Before installing gepa-adk, you need:

1. **Python 3.12+**
2. **Ollama** with the `gpt-oss:20b` model:
   ```bash
   # Install Ollama (if not already installed)
   # Visit https://ollama.ai for installation instructions

   # Pull the required model
   ollama pull gpt-oss:20b
   ```
3. **Set environment variable**:
   ```bash
   export OLLAMA_API_BASE=http://localhost:11434
   ```

**Why gpt-oss:20b?** The evolutionary optimization engine uses this model internally to generate improved agent instructions. Without it, evolution will fail.

### Install gepa-adk

**Using uv (Recommended)**

```bash
uv add gepa-adk
```

**Using pip**

```bash
pip install gepa-adk
```

## Quick Start

```python
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from gepa_adk import evolve_sync

class Output(BaseModel):
    answer: str
    score: float = Field(ge=0.0, le=1.0)

agent = LlmAgent(name="assistant", model="gemini-2.0-flash",
                 instruction="You are a helpful assistant.", output_schema=Output)
trainset = [{"input": "What is 2+2?", "expected": "4"}]
result = evolve_sync(agent, trainset)
print(f"Evolved: {result.evolved_instruction}")
```

## Examples

Two complete working examples are available in the `examples/` directory:

- **[basic_evolution.py](examples/basic_evolution.py)** — Simple greeting agent evolution with critic scoring
- **[critic_agent.py](examples/critic_agent.py)** — Story generation with dedicated critic agent for evaluation

Both examples require Ollama with `gpt-oss:20b` model (see Prerequisites above).

Run an example:
```bash
python examples/basic_evolution.py
```

## Documentation

- [Getting Started Guide](https://alberto-codes.github.io/gepa-adk/getting-started/) — Step-by-step walkthrough from installation to first evolution
- [Use Case Guides](https://alberto-codes.github.io/gepa-adk/guides/) — Patterns for single-agent, critic agents, multi-agent, and workflows
- [API Reference](https://alberto-codes.github.io/gepa-adk/reference/) — Complete documentation for all public functions and classes

## Troubleshooting

### "Model not found" or "Connection refused" errors

Ensure Ollama is running and the model is pulled:

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Pull the model if not present
ollama pull gpt-oss:20b

# Verify the model is available
ollama list | grep gpt-oss
```

### Evolution is slow or uses too many iterations

Adjust the `EvolutionConfig` parameters:

```python
from gepa_adk import EvolutionConfig

config = EvolutionConfig(
    max_iterations=3,  # Reduce iterations
    patience=2,        # Stop early if no improvement
)

result = evolve_sync(agent, trainset, config=config)
```

### Want to use a different model for evolution?

Currently, the reflection model is hardcoded to `gpt-oss:20b`. Future versions will support custom model configuration. For now, ensure this model is available in your Ollama instance.

## Status

**In Development** — Not yet ready for production use.

See [docs/proposals/](docs/proposals/) for technical design and roadmap.

## Credits

This project implements concepts from [GEPA](https://github.com/gepa-ai/gepa) (Genetic-Pareto optimization) and integrates with [Google ADK](https://github.com/google/adk-python).

## License

Apache 2.0

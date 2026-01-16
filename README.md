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

### Using uv (Recommended)

```bash
uv add gepa-adk
```

### Using pip

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

## Documentation

- [Getting Started Guide](https://alberto-codes.github.io/gepa-adk/getting-started/) — Step-by-step walkthrough from installation to first evolution
- [Use Case Guides](https://alberto-codes.github.io/gepa-adk/guides/) — Patterns for single-agent, critic agents, multi-agent, and workflows
- [API Reference](https://alberto-codes.github.io/gepa-adk/reference/) — Complete documentation for all public functions and classes

## Status

**In Development** — Not yet ready for production use.

See [docs/proposals/](docs/proposals/) for technical design and roadmap.

## Credits

This project implements concepts from [GEPA](https://github.com/gepa-ai/gepa) (Genetic-Pareto optimization) and integrates with [Google ADK](https://github.com/google/adk-python).

## License

Apache 2.0

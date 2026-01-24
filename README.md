# gepa-adk

Evolutionary optimization for Google ADK agents.

## What is this?

`gepa-adk` makes your AI agents better automatically. It takes an agent, runs it against examples, gets feedback from a critic, and evolves the agent's instructions until performance improves.

Think of it as natural selection for AI prompts—the best instructions survive and improve.

## Installation

```bash
pip install gepa-adk
```

**Requirements:** Python 3.12+, a Gemini API key (or other ADK-supported model)

```bash
export GOOGLE_API_KEY=your-api-key
```

## Quick Start

The simplest way to evolve an agent: provide a critic to score outputs.

```python
import asyncio
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from gepa_adk import evolve, CriticOutput

# Your agent to evolve
agent = LlmAgent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant.",
)

# A critic that scores the agent's output (0.0-1.0)
critic = LlmAgent(
    name="critic",
    model="gemini-2.5-flash",
    instruction="Score the response for helpfulness and accuracy.",
    output_schema=CriticOutput,  # Has score: float and feedback: str
)

# Training examples
trainset = [
    {"input": "What is 2+2?"},
    {"input": "Explain photosynthesis briefly."},
]

# Evolve!
result = asyncio.run(evolve(agent, trainset, critic=critic))

print(f"Score: {result.original_score:.2f} -> {result.final_score:.2f}")
print(f"Evolved instruction:\n{result.evolved_instruction}")
```

That's it. The critic provides feedback, a reflection agent proposes improvements, and evolution finds better instructions.

## Key Concepts

- **Agent**: The ADK agent whose instruction you want to improve
- **Critic**: Scores the agent's output (0.0-1.0) and provides feedback
- **Trainset**: Examples to evaluate against
- **Evolution**: Iterative improvement using reflection and selection

## Examples

See `examples/` for complete working code:

- **[basic_evolution.py](examples/basic_evolution.py)** — Single agent with critic scoring
- **[critic_agent.py](examples/critic_agent.py)** — Custom critic for story generation
- **[multi_agent.py](examples/multi_agent.py)** — Evolving multiple agents together

## Configuration

```python
from gepa_adk import evolve, EvolutionConfig

config = EvolutionConfig(
    max_iterations=5,   # Maximum evolution iterations
    patience=2,         # Stop early if no improvement
)

result = await evolve(agent, trainset, critic=critic, config=config)
```

## Documentation

- [Getting Started](https://alberto-codes.github.io/gepa-adk/getting-started/)
- [Single-Agent Guide](https://alberto-codes.github.io/gepa-adk/guides/single-agent/)
- [Critic Agents Guide](https://alberto-codes.github.io/gepa-adk/guides/critic-agents/)
- [API Reference](https://alberto-codes.github.io/gepa-adk/reference/)

## Status

**In Development** — API may change.

## Credits

Implements concepts from [GEPA](https://github.com/gepa-ai/gepa) (Genetic-Pareto optimization) and integrates with [Google ADK](https://github.com/google/adk-python).

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

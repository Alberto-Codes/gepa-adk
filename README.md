# gepa-adk

Evolutionary optimization for Google ADK agents.

## What is this?

`gepa-adk` evolves AI agent instructions automatically. Give it an agent and training examples, and it finds better prompts through iterative improvement.

## Installation

```bash
pip install gepa-adk
```

```bash
export GOOGLE_API_KEY=your-api-key  # or other ADK-supported model
```

## Quick Start

Evolve a greeting agent to produce formal, Dickens-style greetings:

```python
import asyncio
from google.adk.agents import LlmAgent
from gepa_adk import evolve, EvolutionConfig, SimpleCriticOutput

agent = LlmAgent(
    name="greeter",
    model="gemini-2.5-flash",
    instruction="Greet the user appropriately.",
)

critic = LlmAgent(
    name="critic",
    model="gemini-2.5-flash",
    instruction="Score for formal, Dickens-style greetings. 0.0-1.0.",
    output_schema=SimpleCriticOutput,
)

trainset = [
    {"input": "I am His Majesty, the King."},
    {"input": "I am your mother."},
    {"input": "I am a close friend."},
]

config = EvolutionConfig(
    max_iterations=5,
    patience=1,
    reflection_model="gemini-2.5-flash",  # Model for generating improvements
)
result = asyncio.run(evolve(agent, trainset, critic=critic, config=config))
print(f"Score: {result.original_score:.2f} -> {result.final_score:.2f}")
print(result.evolved_components["instruction"])
```

## Examples

- [basic_evolution.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/basic_evolution.py) — Single agent with critic
- [critic_agent.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/critic_agent.py) — Custom critic for stories
- [multi_agent.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/multi_agent.py) — Multi-agent evolution

## Documentation

[Getting Started](https://alberto-codes.github.io/gepa-adk/getting-started/) · [Guides](https://alberto-codes.github.io/gepa-adk/guides/single-agent/) · [API Reference](https://alberto-codes.github.io/gepa-adk/reference/)

## Credits

Based on [GEPA](https://arxiv.org/abs/2507.19457) ([source](https://github.com/gepa-ai/gepa)). Built on [Google ADK](https://google.github.io/adk-docs/) ([source](https://github.com/google/adk-python)).

## License

[Apache 2.0](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/LICENSE)

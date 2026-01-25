# GEPA-ADK

**Async-first evolution engine for agentic development**

GEPA-ADK is a Python framework implementing the [GEPA (Genetic-Pareto) prompt optimizer](https://arxiv.org/abs/2507.19457) for Google's Agent Development Kit. It evolves and optimizes AI agents through genetic algorithms and Pareto frontier selection.

## Quick Links

<div class="grid cards" markdown>

- :material-rocket-launch: **[Getting Started](getting-started.md)**
  
    Install GEPA-ADK and run your first evolution in under 5 minutes.

- :material-api: **[API Reference](reference/index.md)**
  
    Auto-generated documentation for all modules, classes, and functions.

- :material-file-tree: **[Architecture](adr/index.md)**
  
    Understand the design decisions behind GEPA-ADK.

- :material-book-open-variant: **[Contributing](contributing/docstring-templates.md)**
  
    Guidelines for contributing code and documentation.

</div>

## Features

- **Async-First**: Built on `asyncio` for concurrent agent evaluation
- **Hexagonal Architecture**: Clean separation between domain logic and external services
- **Protocol-Based**: Flexible interfaces using Python protocols
- **Observable**: Structured logging with `structlog` for debugging and monitoring
- **Well-Documented**: Google-style docstrings with 95%+ coverage

## Installation

```bash
uv add gepa-adk
```

## Basic Usage

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from gepa_adk import evolve_sync, EvolutionConfig, SimpleCriticOutput

agent = LlmAgent(
    name="greeter",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Greet the user appropriately.",
)

critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Score for formal, Dickens-style greetings. 0.0-1.0.",
    output_schema=SimpleCriticOutput,
)

trainset = [
    {"input": "I am His Majesty, the King."},
    {"input": "I am your mother."},
]

config = EvolutionConfig(
    max_iterations=3,
    patience=2,
    reflection_model="ollama_chat/llama3.2:latest",
)
result = evolve_sync(agent, trainset, critic=critic, config=config)

print(f"Improved by {result.improvement:.0%}")
print(result.evolved_components["instruction"])
```

See **[examples/](https://github.com/Alberto-Codes/gepa-adk/tree/HEAD/examples)** for complete working examples.

## Project Status

GEPA-ADK is under active development. See the [Architecture Decision Records](adr/index.md) for design rationale and the [Getting Started](getting-started.md) guide for current capabilities.

## License

Apache License 2.0 - see [LICENSE](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/LICENSE) for details.

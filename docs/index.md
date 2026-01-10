# GEPA-ADK

**Async-first evolution engine for agentic development**

GEPA-ADK (Genetic Evolution for Prompts and Agents - Agent Development Kit) is a Python framework for evolving and optimizing AI agents through genetic algorithms and evolutionary strategies.

## Quick Links

<div class="grid cards" markdown>

- :material-rocket-launch: **[Getting Started](getting-started.md)**
  
    Install GEPA-ADK and run your first evolution in under 5 minutes.

- :material-api: **[API Reference](reference/)**
  
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
from gepa_adk.domain.models import EvolutionConfig

# Create evolution configuration
config = EvolutionConfig(
    max_iterations=100,
    patience=10,
    fitness_threshold=0.95,
)
```

## Project Status

GEPA-ADK is under active development. See the [Architecture Decision Records](adr/index.md) for design rationale and the [Getting Started](getting-started.md) guide for current capabilities.

## License

MIT License - see LICENSE file for details.

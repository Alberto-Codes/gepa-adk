[![CI](https://img.shields.io/github/actions/workflow/status/Alberto-Codes/gepa-adk/tests.yml?branch=main)](https://github.com/Alberto-Codes/gepa-adk/actions/workflows/tests.yml)
[![Coverage](https://codecov.io/gh/Alberto-Codes/gepa-adk/graph/badge.svg)](https://codecov.io/gh/Alberto-Codes/gepa-adk)
[![PyPI](https://img.shields.io/pypi/v/gepa-adk)](https://pypi.org/project/gepa-adk/)
[![Python](https://img.shields.io/pypi/pyversions/gepa-adk)](https://pypi.org/project/gepa-adk/)
[![License](https://img.shields.io/pypi/l/gepa-adk)](https://github.com/Alberto-Codes/gepa-adk/blob/main/LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![docs vetted](https://img.shields.io/badge/docs%20vetted-docvet-purple)](https://github.com/Alberto-Codes/docvet)

# gepa-adk

Evolutionary optimization for Google ADK agents.

## What is this?

`gepa-adk` evolves AI agent instructions automatically. Give it an agent and training examples, and it finds better prompts through iterative improvement using genetic algorithms and Pareto frontier selection.

Supports single-agent evolution, multi-agent co-evolution, workflow optimization (Sequential, Loop, Parallel agents), output schema evolution, generation config tuning, and multimodal inputs including video.

## Requirements

- Python 3.12+
- [Ollama](https://ollama.ai) with a local model (recommended for development), or any model supported by [LiteLLM](https://docs.litellm.ai/)

## Installation

```bash
pip install gepa-adk
```

```bash
# For local models (recommended)
export OLLAMA_API_BASE=http://localhost:11434
```

## Quick Start

Evolve a greeting agent to produce formal, Dickens-style greetings:

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve, run_sync, EvolutionConfig, SimpleCriticOutput

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
    reflection_model="gemini-2.5-flash",
)
result = run_sync(evolve(agent, trainset, critic=critic, config=config))
print(f"Score: {result.original_score:.2f} -> {result.final_score:.2f}")
print(result.evolved_components["instruction"])
```

## Examples

**Getting started:**

- [basic_evolution.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/basic_evolution.py) — Single agent with critic
- [critic_agent.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/critic_agent.py) — Story generation with dedicated critic
- [custom_reflection_prompt.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/custom_reflection_prompt.py) — Custom reflection prompts

**Multi-agent & workflows:**

- [multi_agent.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/multi_agent.py) — Multi-agent co-evolution
- [loop_agent_evolution.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/loop_agent_evolution.py) — LoopAgent workflow evolution
- [parallel_agent_evolution.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/parallel_agent_evolution.py) — ParallelAgent workflow evolution
- [nested_workflow_evolution.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/nested_workflow_evolution.py) — Nested workflow evolution

**Advanced:**

- [schema_evolution_example.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/schema_evolution_example.py) — Output schema evolution
- [config_evolution_demo.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/config_evolution_demo.py) — Generation config evolution
- [video_transcription_evolution.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/video_transcription_evolution.py) — Video input evolution
- [app_runner_integration.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/app_runner_integration.py) — ADK App/Runner integration

## Documentation

[Getting Started](https://alberto-codes.github.io/gepa-adk/getting-started/) · [Guides](https://alberto-codes.github.io/gepa-adk/guides/single-agent/) · [API Reference](https://alberto-codes.github.io/gepa-adk/reference/)

## Credits

Based on [GEPA](https://arxiv.org/abs/2507.19457) ([source](https://github.com/gepa-ai/gepa)). Built on [Google ADK](https://google.github.io/adk-docs/) ([source](https://github.com/google/adk-python)).

## License

[Apache 2.0](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/LICENSE)

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

## Status

**In Development** — Not yet ready for production use.

See [docs/proposals/](docs/proposals/) for technical design and roadmap.

## Credits

This project implements concepts from [GEPA](https://github.com/gepa-ai/gepa) (Genetic-Pareto optimization) and integrates with [Google ADK](https://github.com/google/adk-python).

## License

Apache 2.0

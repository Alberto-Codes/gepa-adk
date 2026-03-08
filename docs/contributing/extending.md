# Extending gepa-adk

gepa-adk uses Protocol-based extension points (ADR-002) so you can add new
capabilities without modifying the core library. Implement the required methods
on a plain class — no inheritance needed.

## Available Extension Points

- **[Evolvable Surfaces](extending-surfaces.md)** — Add new agent attributes to the evolution loop via the `ComponentHandler` protocol (e.g., temperature, tool configs).
- **[Agent Providers](extending-providers.md)** — Implement custom agent loading and persistence backends via the `AgentProvider` protocol (e.g., database, file system).

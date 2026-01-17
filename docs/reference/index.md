# API Reference

This reference documents all public APIs in gepa-adk.

## Quick Navigation

**Start here for most use cases:**

### Core Evolution Functions
- **[`evolve()`](gepa_adk/api.md#gepa_adk.api.evolve)** — Async single-agent evolution
- **[`evolve_sync()`](gepa_adk/api.md#gepa_adk.api.evolve_sync)** — Sync single-agent evolution
- **[`evolve_group()`](gepa_adk/api.md#gepa_adk.api.evolve_group)** — Multi-agent co-evolution
- **[`evolve_workflow()`](gepa_adk/api.md#gepa_adk.api.evolve_workflow)** — Workflow agent evolution

### Configuration & Results
- **[`EvolutionConfig`](gepa_adk/domain/models.md#gepa_adk.domain.models.EvolutionConfig)** — Evolution parameters
- **[`EvolutionResult`](gepa_adk/domain/models.md#gepa_adk.domain.models.EvolutionResult)** — Single-agent results
- **[`MultiAgentEvolutionResult`](gepa_adk/domain/models.md#gepa_adk.domain.models.MultiAgentEvolutionResult)** — Multi-agent results
- **[`TrajectoryConfig`](gepa_adk/domain/types.md#gepa_adk.domain.types.TrajectoryConfig)** — Trajectory capture settings
- **[`StateGuard`](gepa_adk/domain/state.md#gepa_adk.domain.state.StateGuard)** — State token preservation

---

## Module Organization

gepa-adk follows hexagonal architecture (see [ADR-000](../adr/ADR-000-hexagonal-architecture.md)):

### Core Modules
- **[`gepa_adk.api`](gepa_adk/api.md)** — Public API entry points (start here!)
- **[`gepa_adk.domain`](gepa_adk/domain/index.md)** — Core models, types, and exceptions

### Advanced Modules
- **[`gepa_adk.adapters`](gepa_adk/adapters/index.md)** — External integrations (ADK, multi-agent, workflows)
- **[`gepa_adk.engine`](gepa_adk/engine/index.md)** — Evolution orchestration and mutation
- **[`gepa_adk.ports`](gepa_adk/ports/index.md)** — Protocol interfaces for extensibility
- **[`gepa_adk.utils`](gepa_adk/utils/index.md)** — Helper utilities (state guard, trajectory extraction)

---

## Detailed Documentation

For complete documentation of all modules, classes, and functions:

- **[Core API](gepa_adk/api.md)** — Main evolution functions
- **[Domain Models](gepa_adk/domain/models.md)** — Data structures
- **[Configuration Types](gepa_adk/domain/types.md)** — Configuration and trajectory settings
- **[Exceptions](gepa_adk/domain/exceptions.md)** — Exception hierarchy
- **[Full Module Index](gepa_adk/index.md)** — Browse all modules

---

## Common Use Cases

**Single-agent evolution:**
```python
from gepa_adk import evolve_sync
result = evolve_sync(agent, trainset, critic=critic)
```
See [`evolve_sync()`](gepa_adk/api.md#gepa_adk.api.evolve_sync) for details.

**Multi-agent evolution:**
```python
from gepa_adk import evolve_group
result = await evolve_group(agents, primary="final_agent", trainset=trainset)
```
See [`evolve_group()`](gepa_adk/api.md#gepa_adk.api.evolve_group) for details.

**State token preservation:**
```python
from gepa_adk.domain.state import StateGuard
guard = StateGuard(state_keys=["conversation_id", "user_id"])
result = evolve_sync(agent, trainset, state_guard=guard)
```
See [`StateGuard`](gepa_adk/domain/state.md#gepa_adk.domain.state.StateGuard) for details.

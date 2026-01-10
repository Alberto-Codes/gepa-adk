# ADR-006: External Library Integration

> **Status**: Accepted
> **Date**: 2026-01-10
> **Deciders**: gepa-adk maintainers

## Context

gepa-adk integrates with two major external libraries:

1. **Google ADK**: Agent execution, sessions, events, structured output
2. **LiteLLM**: Model abstraction for reflection (fallback when ADK reflection not available)

Additionally, gepa-adk **reimplements GEPA's core algorithm** rather than depending on the `gepa` package directly.

We need clear guidelines for:
- Where external library imports should live
- How to isolate domain logic from external dependencies
- How to handle library version changes

## Decision

### Principle: External Libraries Behind Ports

External library code should:
1. **Only appear in `adapters/`** layer
2. **Be accessed via port protocols** by the engine
3. **Never leak into `domain/`** layer

```
┌─────────────────────────────────────────────────────────────┐
│                        domain/                               │
│   Pure Python - NO external imports (except stdlib)          │
│   EvolutionConfig, EvolutionResult, exceptions               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                        ports/                                │
│   Protocol definitions - NO external imports                 │
│   AsyncGEPAAdapter, Scorer protocols                         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                       adapters/                              │
│   EXTERNAL IMPORTS LIVE HERE                                 │
│   from google.adk.agents import LlmAgent                     │
│   from google.adk.sessions import Session                    │
│   import litellm                                             │
└─────────────────────────────────────────────────────────────┘
```

### gepa-adk IS the Adapter

Unlike typical hexagonal apps where you'd have:
- Domain (your code)
- Port (interface)
- Adapter (external lib wrapper)

gepa-adk **is itself an adapter** bridging GEPA concepts to ADK execution:

```
┌──────────────────────────────────────────────────────────────────────┐
│                     User Application                                  │
│            (e.g., agent-workflow-suite, notebooks)                   │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         gepa-adk                                      │
│   ┌─────────────────────────────────────────────────────────────┐    │
│   │ Reimplemented GEPA Algorithm (domain/ + engine/)            │    │
│   │ - AsyncGEPAEngine (our implementation)                      │    │
│   │ - Pareto selection, reflective mutation                     │    │
│   └─────────────────────────────────────────────────────────────┘    │
│                                │                                      │
│   ┌─────────────────────────────────────────────────────────────┐    │
│   │ ADK Integration (adapters/)                                  │    │
│   │ - ADKAdapter: Execute agents via ADK AgentExecutor          │    │
│   │ - CriticScorer: ADK agent with output_schema                │    │
│   │ - Event extraction from ADK sessions                        │    │
│   └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│      google-adk         │         │        litellm          │
│  (Agent Execution)      │         │   (Model Abstraction)   │
└─────────────────────────┘         └─────────────────────────┘
```

### Import Guidelines

#### ✅ CORRECT: External imports in adapters only

```python
# adapters/adk_adapter.py
from google.adk.agents import LlmAgent
from google.adk.sessions import Session
from google.adk.runners import Runner

from gepa_adk.ports.adapter import AsyncGEPAAdapter
from gepa_adk.domain.models import EvaluationBatch

class ADKAdapter:
    """Implements AsyncGEPAAdapter using Google ADK."""

    async def evaluate(self, batch, candidate, capture_traces=False):
        # ADK-specific code here
        result = await self.runner.run_async(...)
        return EvaluationBatch(...)  # Return domain type
```

#### ❌ WRONG: External imports in domain

```python
# domain/models.py
from google.adk.agents import LlmAgent  # ❌ NO! Domain must be pure

@dataclass
class EvolutionConfig:
    agent: LlmAgent  # ❌ NO! Use generic type or string reference
```

#### ✅ CORRECT: Domain uses generic types

```python
# domain/models.py
from typing import Any
from dataclasses import dataclass

@dataclass
class EvolutionConfig:
    """Configuration for evolution run.

    Attributes:
        max_iterations: Maximum evolution iterations
        ...
    """
    max_iterations: int = 50
    # Agent passed separately to evolve(), not stored in config
```

### Lazy Imports for Optional Dependencies

For optional features, use lazy imports:

```python
# adapters/litellm_reflection.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import litellm

class LiteLLMReflector:
    """Fallback reflector using LiteLLM (when ADK reflection not available)."""

    async def propose(self, current: str, feedback: str) -> str:
        import litellm  # Lazy import - only when actually used

        response = await litellm.acompletion(
            model=self.model,
            messages=[{"role": "user", "content": f"Improve: {current}"}]
        )
        return response.choices[0].message.content
```

### Version Pinning Strategy

In `pyproject.toml`:

```toml
[project]
dependencies = [
    "google-adk>=1.21.0",   # Minimum version with features we need
    "litellm>=1.0.0",       # Stable API
]
```

**Guidelines**:
- Pin minimum versions for required features
- Test against latest versions in CI
- Document breaking changes from upstream in CHANGELOG

### Why Reimplement GEPA (Not Fork/Depend)

We chose to **reimplement GEPA's core algorithm** rather than depend on the `gepa` package:

| Approach | Pros | Cons |
|----------|------|------|
| **Depend on gepa** | Less code, automatic updates | Sync-only API, DSPy baggage, less control |
| **Fork gepa** | Full control | Fork maintenance burden, complex history |
| **Reimplement** ✅ | Async-first, minimal, full control | Must track algorithm changes manually |

**Decision**: Reimplement because:
1. GEPA core is only ~1,000 lines
2. We need native async (GEPA is sync)
3. We don't need GEPA's DSPy/RAG adapters
4. Clean repo history with Apache 2.0 attribution

## Consequences

### Positive

- **Testable**: Domain logic can be tested without external libraries
- **Swappable**: Can replace ADK adapter without changing engine
- **Async-native**: No sync/async bridging needed
- **Minimal dependencies**: Only import what we use

### Negative

- **More code**: Adapters wrap external APIs
- **Version drift**: Must manually track GEPA algorithm improvements
- **Duplication**: Some concepts duplicated from upstream

### Neutral

- **Type hints**: External types don't appear in public API
- **Documentation**: Must document which ADK features we support

## Alternatives Considered

### 1. Depend on GEPA Package Directly

```python
from gepa import GEPAEngine  # Use upstream directly
```

**Rejected**: GEPA is sync-only; would require ugly `asyncio.run()` bridges.

### 2. Fork GEPA Repository

```bash
git clone --fork gepa-ai/gepa gepa-adk
```

**Rejected**: Fork maintenance burden, confusing history, unnecessary DSPy code.

### 3. External Imports Everywhere

```python
# Allow ADK imports in domain
from google.adk.agents import LlmAgent
```

**Rejected**: Couples domain to specific libraries, harder to test.

## References

- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [GEPA GitHub](https://github.com/gepa-ai/gepa)
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- **ADR-000**: Hexagonal Architecture (layer rules)
- **ADR-008**: Structured Logging Pattern (adapter logging)
- **ADR-009**: Exception Hierarchy (wrapping external exceptions)
- [ADR Index](index.md) - All architectural decisions

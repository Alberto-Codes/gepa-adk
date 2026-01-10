# ADR-000: Hexagonal Architecture

> **Status**: Accepted
> **Date**: 2026-01-10
> **Deciders**: gepa-adk maintainers

## Context

gepa-adk bridges two external libraries (GEPA's evolutionary optimization and Google ADK's agent execution framework). We need an architecture that:

1. Keeps core evolution logic independent of external dependencies
2. Makes external library integration clean and testable
3. Allows swapping implementations without changing business logic
4. Enables easy testing with mocks at boundaries

## Decision

Adopt **Hexagonal Architecture** (Ports & Adapters) for gepa-adk with three distinct layers:

### Layer Structure

```
gepa-adk/
├── domain/                    # 🏢 CORE - Pure evolution logic
│   ├── models.py             # EvolutionConfig, EvolutionResult, Candidate
│   ├── types.py              # Type aliases, DTOs
│   └── exceptions.py         # EvolutionError hierarchy
│
├── ports/                     # 🔌 INTERFACES - Protocols
│   ├── adapter.py            # AsyncGEPAAdapter protocol
│   ├── scorer.py             # Scorer protocol
│   └── agent_provider.py     # AgentProvider protocol (optional persistence)
│
├── adapters/                  # 🔧 IMPLEMENTATIONS - ADK-specific
│   ├── adk_adapter.py        # ADKAdapter implements AsyncGEPAAdapter
│   ├── critic_scorer.py      # CriticScorer implements Scorer
│   └── workflow.py           # Workflow utilities
│
├── engine/                    # 🔄 ORCHESTRATION - Async engine
│   ├── async_engine.py       # AsyncGEPAEngine
│   └── proposer.py           # AsyncReflectiveMutationProposer
│
└── utils/                     # 🛠️ UTILITIES
    ├── state_guard.py        # State key preservation
    ├── events.py             # ADK event parsing
    └── parsing.py            # JSON/YAML parsing
```

### Layer Rules

| Layer | Can Import From | Cannot Import From |
|-------|-----------------|-------------------|
| `domain/` | Standard library only | `ports/`, `adapters/`, external libs |
| `ports/` | `domain/` | `adapters/`, external libs |
| `adapters/` | `ports/`, `domain/`, external libs (ADK, LiteLLM) | — |
| `engine/` | `ports/`, `domain/` | `adapters/` (receives via injection) |
| `utils/` | Standard library, minimal external | — |

### Dependency Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      User Application                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     api.py (Public API)                      │
│                evolve(), evolve_sync()                       │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│      engine/             │  │      adapters/           │
│  AsyncGEPAEngine         │  │  ADKAdapter              │
│  (depends on ports)      │  │  CriticScorer            │
└──────────────────────────┘  │  (implements ports)      │
           │                  └──────────────────────────┘
           │                              │
           └──────────────┬───────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        ports/                                │
│           AsyncGEPAAdapter, Scorer protocols                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        domain/                               │
│         EvolutionConfig, EvolutionResult, exceptions         │
└─────────────────────────────────────────────────────────────┘
```

## Consequences

### Positive

- **Testability**: Core engine can be tested with mock adapters (no ADK required)
- **Flexibility**: Swap ADK adapter for alternative implementations
- **Clear boundaries**: External library changes don't leak into domain logic
- **Maintainability**: Each layer has single responsibility
- **Dependency injection**: Engine receives adapters, doesn't create them

### Negative

- **More files**: More structure than a flat module
- **Indirection**: Must trace through layers to understand flow
- **Protocol overhead**: Defining interfaces adds initial development time

### Neutral

- **Learning curve**: Team must understand port/adapter pattern
- **Async everywhere**: Async-first design permeates all layers

## Alternatives Considered

### 1. Flat Module Structure

```python
# Single gepa_adk.py with everything
```

**Rejected**: Doesn't scale, mixes concerns, hard to test without external dependencies.

### 2. Service-Based Architecture

```python
# services/evolution_service.py
# services/scoring_service.py
```

**Rejected**: Services tend to accumulate logic; hexagonal provides clearer boundaries.

### 3. Plugin Architecture

```python
# plugins/adk.py, plugins/litellm.py
```

**Rejected**: Over-engineering for current scope; hexagonal is simpler.

## References

- [Hexagonal Architecture (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- [Ports and Adapters Pattern](https://jmgarridopaz.github.io/content/hexagonalarchitecture.html)
- **ADR-002**: Protocol for Interfaces (port definitions)
- **ADR-005**: Three-Layer Testing Strategy (testing each layer)
- **ADR-006**: External Library Integration (adapter implementations)
- [ADR Index](index.md) - All architectural decisions

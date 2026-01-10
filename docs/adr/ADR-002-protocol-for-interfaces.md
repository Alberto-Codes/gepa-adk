# ADR-002: Protocol for Interfaces

> **Status**: Accepted
> **Date**: 2026-01-10
> **Deciders**: gepa-adk maintainers

## Context

gepa-adk needs to define interfaces for its ports layer (e.g., `AsyncGEPAAdapter`, `Scorer`, `AgentProvider`). Python offers two main approaches:

1. **Abstract Base Classes (ABC)**: Traditional OOP inheritance
2. **Protocol (PEP 544)**: Structural subtyping ("duck typing" with type hints)

We need to choose the right approach for gepa-adk's interface definitions.

## Decision

Use **Protocol** (from `typing`) for all port interfaces in gepa-adk.

### Decision Flowchart

When to use Protocol vs ABC:

```
Need lifecycle management (context managers)?
├─ YES → Use ABC
└─ NO ↓

Need isinstance() checks at runtime?
├─ YES → Use ABC (or @runtime_checkable Protocol)
└─ NO ↓

Need complex generic type variables?
├─ YES → Consider ABC
└─ NO ↓

Simple method signatures only?
├─ YES → Use Protocol ✅
└─ NO → Use ABC
```

For gepa-adk:
- ❌ No lifecycle management (no context managers needed)
- ❌ No `isinstance()` checks needed (dependency injection handles this)
- ❌ No complex generic type variables
- ✅ Simple async method signatures → **Use Protocol**

### Protocol Definitions

```python
# ports/adapter.py
from typing import Protocol, TypeVar, Mapping, Sequence, Any, runtime_checkable

DataInst = TypeVar("DataInst")
Trajectory = TypeVar("Trajectory")
RolloutOutput = TypeVar("RolloutOutput")

@runtime_checkable
class AsyncGEPAAdapter(Protocol[DataInst, Trajectory, RolloutOutput]):
    """Async-first GEPA adapter protocol for ADK integration."""

    async def evaluate(
        self,
        batch: list[DataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Trajectory, RolloutOutput]:
        """Execute candidate on batch."""
        ...

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build reflective dataset for proposal generation."""
        ...

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose new instruction texts."""
        ...
```

```python
# ports/scorer.py
from typing import Protocol

@runtime_checkable
class Scorer(Protocol):
    """Protocol for scoring agent outputs."""

    async def score(
        self,
        input_text: str,
        output: str,
        session_id: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score an agent output.

        Returns:
            Tuple of (score, feedback_dict) where score is 0.0-1.0
        """
        ...
```

```python
# ports/agent_provider.py
from typing import Protocol

@runtime_checkable
class AgentProvider(Protocol):
    """Protocol for loading and persisting agent definitions."""

    def get_agent(self, name: str) -> Any:
        """Load an agent by name."""
        ...

    def save_instruction(self, name: str, instruction: str) -> None:
        """Persist an evolved instruction."""
        ...
```

### Using @runtime_checkable

We add `@runtime_checkable` to allow optional `isinstance()` checks for debugging/validation:

```python
from gepa_adk.ports import AsyncGEPAAdapter, Scorer
from gepa_adk.adapters import ADKAdapter, CriticScorer

# Contract test
def test_adapter_implements_protocol():
    adapter = ADKAdapter(...)
    assert isinstance(adapter, AsyncGEPAAdapter)  # Works with @runtime_checkable
```

**Note**: `@runtime_checkable` only checks method existence, not signatures. Full type checking happens via mypy/pyright.

## Consequences

### Positive

- **Structural subtyping**: Implementations don't need to explicitly inherit
- **Flexibility**: Any class with matching methods satisfies the protocol
- **Simpler testing**: Mock objects automatically satisfy protocols
- **Modern Python**: Aligns with PEP 544 and type checking best practices
- **No import coupling**: Implementations don't need to import the protocol

### Negative

- **Less explicit**: Not immediately obvious what protocol a class implements
- **Runtime checks limited**: `@runtime_checkable` only checks method names
- **Generic variance**: Protocol generics can be tricky to get right

### Neutral

- **Type checker dependent**: Full protocol checking requires mypy/pyright
- **Documentation needed**: Must document expected method signatures clearly

## Alternatives Considered

### 1. Abstract Base Classes (ABC)

```python
from abc import ABC, abstractmethod

class AsyncGEPAAdapter(ABC):
    @abstractmethod
    async def evaluate(self, ...): ...
```

**Rejected**:
- Requires explicit inheritance (`class ADKAdapter(AsyncGEPAAdapter)`)
- Couples implementations to interface definition
- Overkill for simple async method signatures

### 2. Duck Typing (No Interface)

```python
# Just document expected methods, no formal interface
```

**Rejected**:
- No type checking support
- Easy to miss method signature changes
- Harder to understand API contract

### 3. Zope Interface

```python
from zope.interface import Interface, implementer

class IAsyncGEPAAdapter(Interface):
    def evaluate(): ...
```

**Rejected**:
- External dependency
- Not integrated with modern type checkers
- Unfamiliar to most Python developers

## References

- [PEP 544 – Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- [typing.Protocol documentation](https://docs.python.org/3/library/typing.html#typing.Protocol)
- **ADR-000**: Hexagonal Architecture (ports layer)
- **ADR-001**: Async-First Architecture (async protocols)
- **ADR-009**: Exception Hierarchy (exception types in protocols)
- [ADR Index](README.md) - All architectural decisions

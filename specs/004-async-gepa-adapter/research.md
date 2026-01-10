# Research: AsyncGEPAAdapter Protocol

**Feature**: 004-async-gepa-adapter
**Date**: 2026-01-10
**Purpose**: Resolve technical questions and document best practices for async protocol design

## Research Questions

### Q1: GEPA GEPAAdapter Reference Analysis

**Source**: `.venv/lib/python3.12/site-packages/gepa/core/adapter.py` (gepa v0.0.24)

**Findings**:

The original GEPA `GEPAAdapter` is a synchronous `Protocol` with three methods:

```python
class GEPAAdapter(Protocol[DataInst, Trajectory, RolloutOutput]):
    def evaluate(
        self,
        batch: list[DataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Trajectory, RolloutOutput]: ...

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[Trajectory, RolloutOutput],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]: ...

    propose_new_texts: ProposalFn | None = None  # Optional attribute
```

**Key Observations**:
1. Uses three generic type parameters: `DataInst`, `Trajectory`, `RolloutOutput`
2. `EvaluationBatch` is a dataclass with `outputs`, `scores`, `trajectories`, `objective_scores`
3. `propose_new_texts` is an optional class attribute (not a method), typed as `ProposalFn | None`
4. GEPA uses `dict[str, str]` directly for candidates; we use `Candidate.components`

**Decision**: Adapt to async while maintaining semantic compatibility.

**Rationale**:
- Keep same method names and conceptual signatures
- Convert all methods to `async def` per ADR-001
- Make `propose_new_texts` a proper async method (not optional attribute)
- Use our `Candidate` class via `.components` for compatibility

### Q2: Async Protocol Best Practices

**Sources**:
- [Python typing documentation](https://docs.python.org/3/library/typing.html)
- [PEP 544 - Protocols](https://peps.python.org/pep-0544/)
- [Real Python - Python Protocols](https://realpython.com/python-protocol/)

**Decision**: Use `@runtime_checkable` with awareness of limitations.

**Rationale**:
- `@runtime_checkable` allows `isinstance()` checks at runtime
- Limitation: Only checks method presence, NOT signatures or types
- Best practice: Rely on static type checkers (mypy, pyright) for full validation
- Performance: Minimize `isinstance()` checks in hot paths; check once at injection time

**Implementation Pattern**:
```python
from typing import Protocol, TypeVar, runtime_checkable

@runtime_checkable
class AsyncGEPAAdapter(Protocol[DataInst, Trajectory, RolloutOutput]):
    async def evaluate(self, ...) -> EvaluationBatch[...]: ...
```

### Q3: EvaluationBatch Design

**Decision**: Define `EvaluationBatch` as a frozen dataclass in `ports/adapter.py`.

**GEPA Original**:
```python
@dataclass
class EvaluationBatch(Generic[Trajectory, RolloutOutput]):
    outputs: list[RolloutOutput]
    scores: list[float]
    trajectories: list[Trajectory] | None = None
    objective_scores: list[dict[str, float]] | None = None
```

**gepa-adk Adaptation**:
- Keep same structure for GEPA compatibility
- Use `slots=True` for memory efficiency per 002-domain-models research
- Use `frozen=True` since evaluation results shouldn't be mutated
- Keep in `ports/` layer (it's part of the adapter interface, not pure domain)

### Q4: Generic Type Parameter Strategy

**Decision**: Use covariant TypeVars where appropriate.

**Analysis**:
| Type Parameter | Purpose | Variance |
|----------------|---------|----------|
| `DataInst` | Input data type | Invariant (consumed) |
| `Trajectory` | Trace data type | Covariant (produced) |
| `RolloutOutput` | Output data type | Covariant (produced) |

**Implementation**:
```python
DataInst = TypeVar("DataInst")
Trajectory = TypeVar("Trajectory", covariant=True)
RolloutOutput = TypeVar("RolloutOutput", covariant=True)
```

**Note**: For Protocol methods, variance is less critical since Protocols use structural subtyping. We'll use invariant TypeVars for simplicity matching GEPA's approach.

### Q5: Method Signature Differences from GEPA

**Decision**: Modify `propose_new_texts` from optional attribute to required async method.

**GEPA Original**:
- `propose_new_texts` is an optional class attribute typed as `ProposalFn | None`
- Default is `None`, meaning GEPA provides default proposal logic

**gepa-adk Approach**:
- Make it a required async method in the protocol
- Rationale: Async-first design requires consistent async interface
- Adapters that want default behavior can delegate to a shared utility

**Method Signature Comparison**:

| Method | GEPA | gepa-adk |
|--------|------|----------|
| `evaluate` | sync | `async def` |
| `make_reflective_dataset` | sync | `async def` |
| `propose_new_texts` | Optional `ProposalFn` attr | Required `async def` |

### Q6: Integration with Existing Domain Models

**Decision**: Reference `Candidate` and `EvolutionConfig` from domain layer.

**Integration Points**:
- `candidate: dict[str, str]` in GEPA → Use `candidate.components` from our `Candidate`
- Config parameters like `max_concurrent_evals` come from `EvolutionConfig`
- Error handling follows `EvolutionError` hierarchy from ADR-009

**Import Strategy** (per ADR-000):
```python
# In ports/adapter.py
from gepa_adk.domain.types import Score, ComponentName  # OK - domain deps allowed
# NOT: from gepa_adk.adapters import ...  # Forbidden - no adapter imports in ports
```

## Resolved Questions Summary

| Question | Resolution |
|----------|------------|
| GEPA alignment | Same methods, adapted to async, compatible via `.components` |
| Protocol decorator | `@runtime_checkable` with static type checker reliance |
| EvaluationBatch location | `ports/adapter.py`, frozen dataclass with slots |
| Type parameters | Invariant TypeVars matching GEPA |
| propose_new_texts | Required async method (not optional attribute) |
| Domain integration | Import from domain/, use Candidate.components |

## No Outstanding NEEDS CLARIFICATION

All technical questions resolved. Ready for Phase 1 design.

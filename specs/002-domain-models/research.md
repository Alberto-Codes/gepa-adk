# Research: Domain Models Implementation

**Feature**: 002-domain-models  
**Date**: 2026-01-10  
**Purpose**: Resolve technical questions and document best practices for domain model implementation

## Research Questions

### Q1: Python Dataclass Best Practices for Domain Models

**Decision**: Use `@dataclass` with `slots=True` for performance and `frozen=True` for immutable result types.

**Rationale**:
- `slots=True` (Python 3.10+): Reduces memory footprint, faster attribute access
- `frozen=True`: Prevents accidental mutation of result objects (EvolutionResult, IterationRecord)
- `kw_only=True` (Python 3.10+): Forces keyword arguments for clarity, prevents positional arg mistakes

**Alternatives Considered**:
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Pydantic | Rich validation, serialization | External dependency (violates ADR-000) | ❌ Rejected |
| attrs | Slots, validators, converters | External dependency | ❌ Rejected |
| NamedTuple | Immutable, lightweight | No defaults, no methods, awkward update | ❌ Rejected |
| dataclass | Stdlib, slots, frozen, kw_only | Manual validation via __post_init__ | ✅ Selected |

### Q2: Validation Strategy Without External Libraries

**Decision**: Use `__post_init__` for validation with custom `ConfigurationError`.

**Rationale**:
- `__post_init__` runs after `__init__`, perfect for validation
- Raise `ConfigurationError` (subclass of `EvolutionError` per ADR-009)
- Keep validation simple: non-negative checks, type assertions

**Implementation Pattern**:
```python
@dataclass(slots=True)
class EvolutionConfig:
    max_iterations: int = 50

    def __post_init__(self) -> None:
        if self.max_iterations < 0:
            raise ConfigurationError(
                "max_iterations must be non-negative",
                field="max_iterations",
                value=self.max_iterations,
            )
```

### Q3: Type Aliases and Score Representation

**Decision**: Use `typing.TypeAlias` for semantic clarity without runtime overhead.

**Rationale**:
- `Score = float` provides documentation but no runtime validation
- Score range [0.0, 1.0] is a convention, not enforced by type system
- Keep domain layer simple; validation happens at boundaries (adapters)

**Type Aliases Defined**:
```python
# types.py
from typing import TypeAlias

Score: TypeAlias = float  # Normalized score in [0.0, 1.0]
ComponentName: TypeAlias = str  # e.g., "instruction", "output_schema"
ModelName: TypeAlias = str  # e.g., "gemini-2.5-flash"
```

### Q4: Mutable vs Immutable Design

**Decision**: 
- `EvolutionConfig`: Mutable (users may want to modify before passing to engine)
- `EvolutionResult`: Frozen (immutable after creation by engine)
- `IterationRecord`: Frozen (immutable historical record)
- `Candidate`: Mutable (components dict is modified during evolution)

**Rationale**:
- Config is input, may be adjusted programmatically before use
- Results are output, should not be modified after creation
- Candidates are working state, need mutation during evolution loop

### Q5: Default Factory for Mutable Defaults

**Decision**: Use `field(default_factory=dict)` for `Candidate.components`.

**Rationale**:
- Mutable default arguments are a Python gotcha (shared across instances)
- `default_factory` creates a new dict for each instance
- Standard dataclass pattern for mutable defaults

**Implementation**:
```python
from dataclasses import dataclass, field

@dataclass(slots=True)
class Candidate:
    components: dict[str, str] = field(default_factory=dict)
```

## Resolved Questions Summary

| Question | Resolution |
|----------|------------|
| Dataclass features | `slots=True`, `frozen` for results, `kw_only=True` |
| Validation | `__post_init__` with `ConfigurationError` |
| Type aliases | `typing.TypeAlias` for Score, ComponentName, ModelName |
| Mutability | Config/Candidate mutable; Result/Record frozen |
| Mutable defaults | `field(default_factory=...)` |

## GEPA Package Reference Alignment (v0.0.24)

**Purpose**: Document alignment and intentional deviations from the original `gepa` package to ensure `gepa-adk` builds upon GEPA concepts while being async-first.

### Key Findings from GEPA Core

#### 1. Candidate Representation

**GEPA (Original)**:
```python
Candidate = dict[str, str]  # Type alias only
```

**gepa-adk (Our Design)**:
```python
@dataclass(slots=True)
class Candidate:
    components: dict[str, str] = field(default_factory=dict)
    generation: int = 0
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Decision**: Create a wrapper class instead of a type alias.

**Rationale**:
- GEPA's `dict[str, str]` is simple but lacks structure for async tracking
- gepa-adk needs: generation tracking, parent lineage, metadata for async operations
- Wrapper class enables: rich serialization, state management, async coordination
- Still compatible: `candidate.components` returns `dict[str, str]` for GEPA adapter compatibility

#### 2. Result Structure

**GEPA (Original)** - `GEPAResult`:
```python
@dataclass(frozen=True)
class GEPAResult(Generic[RolloutOutput, DataId]):
    candidates: list[dict[str, str]]
    parents: list[list[ProgramIdx | None]]
    val_aggregate_scores: list[float]
    val_subscores: list[dict[DataId, float]]
    per_val_instance_best_candidates: dict[DataId, set[ProgramIdx]]
    # ... extensive pareto front tracking
```

**gepa-adk (Our Design)** - `EvolutionResult`:
- Simplified for single-objective optimization in v1
- Focus on best candidate and iteration history
- Async-friendly with immutable frozen dataclass

**Decision**: Simplify result structure for v1, with extension path for multi-objective.

**Rationale**:
- GEPA's result has complex pareto front tracking for multi-objective
- gepa-adk v1 focuses on single-objective to nail async patterns first
- Can extend to multi-objective in future version

#### 3. State vs Result Separation

**GEPA Pattern**:
- `GEPAState`: Mutable, tracks evolution progress (`program_candidates`, `prog_candidate_val_subscores`, `full_program_trace`)
- `GEPAResult`: Immutable, constructed from `GEPAState.result()` after evolution

**gepa-adk (Our Design)**:
- `EvolutionResult`: Final immutable result (matches GEPA pattern)
- `IterationRecord`: Immutable snapshot of each iteration
- Internal mutable state managed by Engine (not in domain models spec)

**Decision**: Align with GEPA's state/result separation pattern.

#### 4. Evaluation Batch Structure

**GEPA (Original)**:
```python
@dataclass
class EvaluationBatch(Generic[Trajectory, RolloutOutput]):
    outputs: list[RolloutOutput]
    scores: list[float]
    trajectories: list[Trajectory] | None = None
    objective_scores: list[dict[str, float]] | None = None
```

**gepa-adk Consideration**:
- EvaluationBatch is part of the adapter interface, not domain models
- Will be defined when implementing adapter ports (separate spec)
- gepa-adk will make evaluation async

#### 5. Proposal Structure

**GEPA (Original)**:
```python
@dataclass
class CandidateProposal(Generic[DataId]):
    candidate: dict[str, str]
    parent_program_ids: list[int]
    subsample_indices: list[DataId] | None = None
    subsample_scores_before: list[float] | None = None
    subsample_scores_after: list[float] | None = None
    tag: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
```

**gepa-adk Consideration**:
- Proposal structure is part of proposer interface (separate spec)
- gepa-adk's `Candidate` class subsumes some of this functionality
- Will align when implementing proposer ports

### Alignment Summary

| GEPA Concept | gepa-adk Equivalent | Alignment Status |
|--------------|---------------------|------------------|
| `Candidate` (dict alias) | `Candidate` (dataclass) | ✅ Compatible via `.components` |
| `GEPAState` | Internal Engine state | ✅ Same pattern |
| `GEPAResult` | `EvolutionResult` | ✅ Simplified, extensible |
| `ValsetEvaluation` | `IterationRecord` | ✅ Conceptually aligned |
| `CandidateProposal` | Future proposer spec | ⏳ Deferred |
| `EvaluationBatch` | Future adapter spec | ⏳ Deferred |
| `GEPAAdapter` Protocol | Future adapter spec | ⏳ Deferred |
| `GEPAEngine` | Future engine spec | ⏳ Deferred |

### Key Differences (Intentional)

1. **Async-First**: GEPA is synchronous; gepa-adk will use `async/await` throughout
2. **Rich Candidate**: GEPA uses `dict[str, str]`; we use a class with metadata
3. **Simplified v1**: Focus on single-objective before multi-objective complexity
4. **ADK Integration**: Designed for Google ADK patterns (streaming, agents)

## No Outstanding NEEDS CLARIFICATION

All technical questions resolved. Ready for Phase 1 design.

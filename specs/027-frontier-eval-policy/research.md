# Research: Frontier Types and Valset Evaluation Policies

**Feature**: 027-frontier-eval-policy
**Date**: 2026-01-15

## Overview

This document captures research findings from analyzing the upstream GEPA library's implementation of frontier types and evaluation policies, informing the gepa-adk port strategy.

---

## Upstream GEPA Analysis

### Source Files Reviewed

| File | Purpose |
|------|---------|
| `.venv/lib/python3.12/site-packages/gepa/core/state.py` | GEPAState with frontier tracking |
| `.venv/lib/python3.12/site-packages/gepa/strategies/eval_policy.py` | EvaluationPolicy protocol and FullEvaluationPolicy |
| `.venv/lib/python3.12/site-packages/gepa/strategies/candidate_selector.py` | ParetoCandidateSelector using frontier mappings |

### Frontier Type Implementation (Upstream)

**Type Definition** (state.py:21-22):
```python
FrontierType: TypeAlias = Literal["instance", "objective", "hybrid", "cartesian"]
"""Strategy for tracking Pareto frontiers: 'instance' (per validation example),
'objective' (per objective metric), 'hybrid' (both), or 'cartesian' (per example × objective)."""
```

**State Attributes for Each Frontier Type**:

| Frontier Type | Primary Mapping | Key Structure |
|---------------|-----------------|---------------|
| instance | `pareto_front_valset` | `dict[DataId, float]` |
| objective | `objective_pareto_front` | `ObjectiveScores` (dict[str, float]) |
| hybrid | Both of above | Combined mapping |
| cartesian | `pareto_front_cartesian` | `dict[tuple[DataId, str], float]` |

**Frontier Tracking Logic** (state.py:394-411):
```python
def _get_pareto_front_mapping(self, frontier_type: FrontierType) -> dict[FrontierKey, set[ProgramIdx]]:
    if frontier_type == "instance":
        return {val_id: set(front) for val_id, front in self.program_at_pareto_front_valset.items()}
    if frontier_type == "objective":
        return {objective: set(front) for objective, front in self.program_at_pareto_front_objectives.items()}
    if frontier_type == "hybrid":
        combined: dict[FrontierKey, set[ProgramIdx]] = {
            ("val_id", val_id): set(front) for val_id, front in self.program_at_pareto_front_valset.items()
        }
        for objective, front in self.program_at_pareto_front_objectives.items():
            combined[("objective", objective)] = set(front)
        return combined
    if frontier_type == "cartesian":
        return {
            ("cartesian", val_id, objective): set(front)
            for (val_id, objective), front in self.program_at_pareto_front_cartesian.items()
        }
```

**Validation for Objective-Based Types** (state.py:91-96):
```python
if frontier_type in ("objective", "hybrid", "cartesian"):
    if not base_evaluation.objective_scores_by_val_id:
        raise ValueError(
            f"frontier_type='{frontier_type}' requires objective_scores to be provided by the evaluator, "
            f"but none were found. Use an evaluator that returns objective_scores or use frontier_type='instance'."
        )
```

### Evaluation Policy Protocol (Upstream)

**Protocol Definition** (eval_policy.py:13-31):
```python
@runtime_checkable
class EvaluationPolicy(Protocol[DataId, DataInst]):
    """Strategy for choosing validation ids to evaluate and identifying best programs."""

    @abstractmethod
    def get_eval_batch(
        self, loader: DataLoader[DataId, DataInst], state: GEPAState, target_program_idx: ProgramIdx | None = None
    ) -> list[DataId]:
        """Select examples for evaluation for a program"""
        ...

    @abstractmethod
    def get_best_program(self, state: GEPAState) -> ProgramIdx:
        """Return 'best' program given all validation results so far across candidates"""
        ...

    @abstractmethod
    def get_valset_score(self, program_idx: ProgramIdx, state: GEPAState) -> float:
        """Return the score of the program on the valset"""
        ...
```

**FullEvaluationPolicy Implementation** (eval_policy.py:34-57):
- `get_eval_batch()`: Returns all validation IDs from loader
- `get_best_program()`: Returns candidate with highest average score across evaluated examples
- `get_valset_score()`: Delegates to `state.get_program_average_val_subset()`

---

## Design Decisions

### Decision 1: Frontier Type Support

**Decision**: Support all four frontier types (instance, objective, hybrid, cartesian)

**Rationale**:
- Upstream GEPA already implements all four types
- Current gepa-adk has FrontierType enum with all values defined but only INSTANCE is enabled
- Feature 026-objective-scores added objective_scores passthrough, enabling objective-based tracking
- Port upstream logic directly, removing the artificial INSTANCE-only restriction

**Alternatives Considered**:
1. Only support INSTANCE and OBJECTIVE - Rejected because cartesian provides valuable granularity for multi-objective optimization
2. Implement custom dominance logic - Rejected because upstream patterns are well-tested

### Decision 2: Evaluation Policy Architecture

**Decision**: Create EvaluationPolicyProtocol in ports/selector.py with FullEvaluationPolicy and SubsetEvaluationPolicy adapters

**Rationale**:
- Follows hexagonal architecture (port protocol + adapter implementations)
- Consistent with existing CandidateSelectorProtocol pattern
- Enables extensibility for future policies (e.g., bandit-based sampling)

**Alternatives Considered**:
1. Single configurable class with policy parameter - Rejected because Protocol pattern enables cleaner injection
2. Embed policy logic in engine - Rejected because violates separation of concerns

### Decision 3: Subset Evaluation Strategy

**Decision**: Implement SubsetEvaluationPolicy with configurable subset size and round-robin coverage

**Rationale**:
- For large valsets (1000+ examples), full evaluation per iteration is expensive
- Round-robin ensures all examples eventually get evaluated
- Subset size as percentage or absolute count provides flexibility

**Implementation Approach**:
```python
class SubsetEvaluationPolicy:
    def __init__(self, subset_size: int | float = 0.2):
        """
        Args:
            subset_size: If int, absolute count. If float, fraction of total valset.
        """
        self.subset_size = subset_size
        self._last_offset = 0
```

### Decision 4: Frontier State Storage

**Decision**: Extend ParetoFrontier with parallel tracking dictionaries for each frontier type

**Rationale**:
- Upstream GEPA maintains separate dictionaries per frontier type
- Enables efficient lookup for configured frontier type
- Memory overhead is acceptable for typical valset sizes

**Data Structures**:
```python
@dataclass
class ParetoFrontier:
    # Instance-level (existing)
    example_leaders: dict[int, set[int]]
    best_scores: dict[int, float]

    # Objective-level (new)
    objective_leaders: dict[str, set[int]]
    objective_best_scores: dict[str, float]

    # Cartesian (new)
    cartesian_leaders: dict[tuple[int, str], set[int]]
    cartesian_best_scores: dict[tuple[int, str], float]
```

### Decision 5: API Integration Point

**Decision**: Add `evaluation_policy` parameter to AsyncGEPAEngine constructor

**Rationale**:
- Consistent with existing `candidate_selector` injection pattern
- Defaults to FullEvaluationPolicy for backward compatibility
- Engine calls `policy.get_eval_batch()` before evaluation

**Integration**:
```python
class AsyncGEPAEngine:
    def __init__(
        self,
        ...
        evaluation_policy: EvaluationPolicyProtocol | None = None,
    ):
        self._evaluation_policy = evaluation_policy or FullEvaluationPolicy()
```

---

## Existing gepa-adk State

### FrontierType Enum (domain/types.py:126-138)

Already defines all four values:
```python
class FrontierType(str, Enum):
    INSTANCE = "instance"
    OBJECTIVE = "objective"
    HYBRID = "hybrid"
    CARTESIAN = "cartesian"
```

### ParetoState Restriction (domain/state.py:163-171)

Currently raises error for non-INSTANCE types:
```python
def __post_init__(self) -> None:
    if self.frontier_type is not FrontierType.INSTANCE:
        raise ConfigurationError(
            "frontier_type is not supported in this feature",
            field="frontier_type",
            value=self.frontier_type,
            constraint="FrontierType.INSTANCE",
        )
```

**Action**: Remove this restriction and implement full frontier type support.

### Objective Scores Support (026-objective-scores)

Feature 026 added `objective_scores: list[dict[str, float]] | None` to:
- EvaluationBatch
- IterationRecord
- EvolutionResult
- _EngineState

This provides the objective scores needed for objective/hybrid/cartesian frontier types.

---

## Implementation Strategy

### Phase 1: Domain Layer
1. Remove INSTANCE-only restriction from ParetoState
2. Extend ParetoFrontier with objective and cartesian tracking
3. Implement `update()` for all frontier types
4. Implement `get_pareto_front_mapping()` returning appropriate key structure

### Phase 2: Ports Layer
1. Define EvaluationPolicyProtocol in ports/selector.py
2. Methods: `get_eval_batch()`, `get_best_program()`, `get_valset_score()`

### Phase 3: Adapters Layer
1. Implement FullEvaluationPolicy (mirrors upstream)
2. Implement SubsetEvaluationPolicy with round-robin coverage
3. Update candidate selectors to use frontier mappings

### Phase 4: Engine Integration
1. Add `evaluation_policy` parameter to AsyncGEPAEngine
2. Wire `get_eval_batch()` into evaluation flow
3. Update `_initialize_baseline()` to respect evaluation policy

### Phase 5: Testing
1. Contract tests for EvaluationPolicyProtocol
2. Unit tests for each frontier type's update/dominance logic
3. Integration tests for evolution with different configurations

---

## References

- Upstream GEPA: `.venv/lib/python3.12/site-packages/gepa/`
- Feature 022-pareto-frontier: `specs/022-pareto-frontier/`
- Feature 026-objective-scores: `specs/026-objective-scores/`
- GitHub Issue #62: Feature request with acceptance criteria

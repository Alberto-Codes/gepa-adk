# Research: Pareto Frontier Tracking and Candidate Selection

**Feature**: 022-pareto-frontier
**Date**: 2026-01-14

## Research Summary

This research covers the integration of Pareto frontier tracking and candidate selection strategies into gepa-adk, inspired by the reference GEPA library implementation.

---

## 1. GEPA Reference Implementation Analysis

### Decision
Adapt GEPA's Pareto frontier design for gepa-adk's async/hexagonal architecture, implementing `GEPAState` equivalent as a domain model and candidate selectors as port protocol + adapters.

### Rationale
- GEPA's `GEPAState` (483 lines) provides mature, tested Pareto frontier tracking
- GEPA's `candidate_selector.py` (51 lines) offers clean selector abstractions
- Direct port is not possible due to architectural differences (gepa-adk uses hexagonal architecture, async-first design)
- Key patterns to adopt:
  - Per-validation-example score tracking (`prog_candidate_val_subscores`)
  - Multi-dimensional frontier types (`instance`, `objective`, `hybrid`, `cartesian`)
  - Probability-weighted selection from Pareto front

### Alternatives Considered
1. **Direct import of GEPA classes**: Rejected - violates hexagonal architecture (external imports in domain)
2. **Simple adaptation layer**: Rejected - GEPA's synchronous design conflicts with async-first principle
3. **Complete reimplementation**: Chosen - allows full architectural alignment while preserving core algorithms

---

## 2. Domain Model Design

### Decision
Create new domain models in `src/gepa_adk/domain/`:
- `ParetoState` - Evolution state with per-example tracking
- `ParetoFrontier` - Non-dominated candidate collection
- `CandidateScore` - Per-example score record

### Rationale
- Follows ADR-000: Pure Python domain models with no external imports
- Separates frontier logic from engine orchestration
- Enables unit testing without mocks

### Key Mappings from GEPA
| GEPA Concept | gepa-adk Equivalent |
|--------------|---------------------|
| `GEPAState` | `ParetoState` (domain model) |
| `prog_candidate_val_subscores` | `ParetoState.candidate_scores: dict[CandidateId, dict[ExampleId, float]]` |
| `program_at_pareto_front_valset` | `ParetoFrontier.example_leaders: dict[ExampleId, set[CandidateId]]` |
| `FrontierType` literal | `FrontierType` enum in domain/types.py |

---

## 3. Candidate Selector Protocol

### Decision
Define `CandidateSelectorProtocol` in `src/gepa_adk/ports/selector.py` with three async implementations in `src/gepa_adk/adapters/candidate_selector.py`:
- `ParetoCandidateSelector` - Sample from Pareto front proportional to frequency
- `CurrentBestCandidateSelector` - Always return highest average scorer
- `EpsilonGreedyCandidateSelector` - ε-greedy exploration

### Rationale
- Follows ADR-002: Protocol-based interfaces for structural subtyping
- Enables dependency injection into `AsyncGEPAEngine`
- Allows custom selector implementations

### Protocol Signature
```python
@runtime_checkable
class CandidateSelectorProtocol(Protocol):
    async def select_candidate(self, state: ParetoState) -> CandidateId:
        """Select next candidate for mutation."""
        ...
```

---

## 4. Engine Integration

### Decision
Modify `AsyncGEPAEngine` to:
1. Accept optional `candidate_selector: CandidateSelectorProtocol` parameter
2. Maintain `ParetoState` instead of simple `_EngineState`
3. Track per-example scores from `EvaluationBatch`

### Rationale
- Backward compatible: Default selector is `CurrentBestCandidateSelector` (current greedy behavior)
- Minimal API change: Single new parameter
- Leverages existing `EvaluationBatch.scores` list (per-example)

### Integration Points
1. `_initialize_baseline()`: Create `ParetoState` with initial scores
2. `_accept_proposal()`: Update frontier on acceptance
3. `_propose_mutation()`: Use selector to choose parent candidate

---

## 5. Frontier Type Scoping

### Decision
Initial implementation supports only `instance` frontier type. Other types (`objective`, `hybrid`, `cartesian`) are deferred.

### Rationale
- `instance` is GEPA's default and most commonly used
- Reduces initial complexity
- Other types require `objective_scores` in `EvaluationBatch` (already supported but not widely used)
- Can be added incrementally without breaking changes

---

## 6. Testing Strategy

### Decision
Three-layer testing per ADR-005:
- **Contract tests**: Verify selector protocol compliance
- **Unit tests**: Test frontier update logic, selection probability distribution
- **Integration tests**: End-to-end evolution with Pareto selection

### Key Test Scenarios
1. Pareto selection explores non-best candidates
2. Instance frontier retains specialists
3. Empty frontier handling
4. Epsilon-greedy exploration rate verification

---

## 7. Performance Considerations

### Decision
Use `dict`-based lookups for O(1) candidate access; avoid full frontier recalculation on each update.

### Rationale
- GEPA's `remove_dominated_programs` is O(n²) in worst case
- For typical evolution (< 100 candidates), this is acceptable
- Lazy dominance removal only when selecting (not on every update)

---

## Open Questions Resolved

| Question | Resolution |
|----------|------------|
| How to handle empty frontier? | Raise `NoCandidateAvailableError`; engine handles baseline or no-op |
| Where to store per-example scores? | In `EvaluationBatch` (already exists as `scores` list) |
| How to map examples to IDs? | Use batch index as example ID (matches GEPA's `DataId`) |
| Should frontier be persisted? | Deferred - current `EvolutionResult` doesn't persist state |

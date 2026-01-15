# Research: Objective Scores Passthrough

**Feature**: 026-objective-scores
**Date**: 2026-01-15
**Status**: Complete

## Research Questions

### Q1: How does upstream GEPA handle objective_scores?

**Decision**: Follow upstream GEPA's passthrough + aggregation pattern but simplify for gepa-adk's async-first design.

**Rationale**: Upstream GEPA (gepa/core/state.py) stores objective_scores at two levels:
1. **Per-example level**: `objective_scores_by_val_id: dict[DataId, ObjectiveScores]` in `ValsetEvaluation`
2. **Per-candidate aggregated level**: `prog_candidate_objective_scores: list[ObjectiveScores]` in `GEPAState`

GEPA aggregates per-example scores using mean aggregation (`_aggregate_objective_scores` method). For gepa-adk, we'll passthrough the raw list from EvaluationBatch without aggregation, letting users aggregate as needed.

**Alternatives considered**:
- Full GEPA parity with per-example storage → Rejected (adds complexity, not needed for passthrough feature)
- Aggregate to single dict per iteration → Rejected (loses per-example granularity)
- Passthrough raw list from EvaluationBatch → **Selected** (simplest, preserves all data)

### Q2: What type should objective_scores use in domain models?

**Decision**: Use `list[dict[str, float]] | None` matching EvaluationBatch structure.

**Rationale**: The EvaluationBatch in ports/adapter.py already defines:
```python
objective_scores: list[dict[ComponentName, Score]] | None = None
```

Where `ComponentName = str` and `Score = float`. This structure allows:
- Per-example objective breakdown (list[dict])
- Multiple objectives per example (dict[str, float])
- Optional presence (| None)

Domain models should use the same structure for consistency.

**Alternatives considered**:
- Create ObjectiveScores type alias → Deferred (types.py doesn't have it, add only if needed elsewhere)
- Use dict[str, float] aggregated → Rejected (loses per-example data)
- Use list[tuple[str, float]] → Rejected (dict is more readable and matches upstream)

### Q3: Where should objective_scores be stored in engine state?

**Decision**: Store in `_EngineState` as `best_objective_scores: list[dict[str, float]] | None` and pass to `IterationRecord`.

**Rationale**: Following the existing pattern for scores:
1. Engine state tracks `best_score` (aggregated) and `best_valset_mean` (mean)
2. Iteration history records `score` per iteration
3. Results expose `final_score`, `valset_score`, `trainset_score`

For objective_scores:
1. Engine state tracks `best_objective_scores` (from best candidate's evaluation)
2. Iteration history records `objective_scores` per iteration
3. Results expose `objective_scores` (from best candidate)

**Alternatives considered**:
- Store only in EvolutionResult → Rejected (no iteration-level tracking)
- Store per-candidate in ParetoState → Deferred (future Pareto feature)
- Store both raw and aggregated → Rejected (over-engineering)

### Q4: How should backward compatibility be ensured?

**Decision**: Use optional fields with `None` defaults throughout.

**Rationale**: Following existing patterns in the codebase:
- `IterationRecord` is frozen dataclass with immutable fields
- `EvolutionResult` has optional `valset_score: float | None = None`
- `EvaluationBatch` has optional `objective_scores: list[dict[...]] | None = None`

All new fields will:
- Default to `None`
- Only be populated when adapter provides objective_scores
- Not affect existing code paths

**Alternatives considered**:
- Default to empty list `[]` → Rejected (inconsistent with existing `None` pattern)
- Required field with validation → Rejected (breaks backward compatibility)
- Separate result type for multi-objective → Rejected (over-engineering)

### Q5: Should objective_scores be aggregated in results?

**Decision**: No aggregation - passthrough only in this feature scope.

**Rationale**:
- Feature spec explicitly states "passthrough without transformation" (FR-007)
- Aggregation logic varies by use case (mean, sum, weighted, etc.)
- Users can aggregate in their analysis code
- Future feature can add aggregation helpers if needed

**Alternatives considered**:
- Add aggregation helper methods → Deferred (future enhancement)
- Add both raw and aggregated fields → Rejected (over-engineering)
- Add configurable aggregation → Rejected (scope creep)

## Technical Findings

### Existing Infrastructure

1. **EvaluationBatch** (ports/adapter.py:20-71) already supports objective_scores:
   ```python
   objective_scores: list[dict[ComponentName, Score]] | None = None
   ```

2. **Type aliases** (domain/types.py) define:
   - `Score: TypeAlias = float`
   - `ComponentName: TypeAlias = str`

3. **Engine state** (_EngineState in async_engine.py) tracks:
   - `best_score: float` - aggregated acceptance score
   - `best_valset_mean: float | None` - mean valset score
   - `best_reflection_score: float` - mean trainset score

4. **Upstream GEPA pattern** (gepa/core/state.py:20):
   ```python
   ObjectiveScores: TypeAlias = dict[str, float]
   ```

### Data Flow Analysis

Current flow (without objective_scores):
```
Adapter.evaluate() → EvaluationBatch.scores → Engine._aggregate_acceptance_score() → _EngineState.best_score → EvolutionResult.final_score
```

Proposed flow (with objective_scores):
```
Adapter.evaluate() → EvaluationBatch.objective_scores → Engine (passthrough) → _EngineState.best_objective_scores → IterationRecord.objective_scores → EvolutionResult.objective_scores
```

### Affected Files Summary

| File | Change Type | Description |
|------|-------------|-------------|
| domain/models.py | MODIFY | Add objective_scores to IterationRecord, EvolutionResult |
| engine/async_engine.py | MODIFY | Extract and store objective_scores from EvaluationBatch |
| tests/contracts/* | NEW | Protocol compliance tests |
| tests/unit/engine/* | NEW | Engine state passthrough tests |
| tests/integration/* | NEW | End-to-end objective_scores flow tests |

## Conclusion

The implementation is straightforward:
1. Add optional `objective_scores: list[dict[str, float]] | None = None` to `IterationRecord` and `EvolutionResult`
2. Add `best_objective_scores: list[dict[str, float]] | None = None` to `_EngineState`
3. Extract objective_scores from `EvaluationBatch` in evaluation methods
4. Pass through to iteration recording and result building
5. Add three-layer tests following existing patterns

No architectural decisions needed - feature aligns with existing hexagonal architecture and constitution principles.

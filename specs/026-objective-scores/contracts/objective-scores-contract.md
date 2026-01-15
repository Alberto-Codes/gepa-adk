# Contract: Objective Scores Passthrough

**Feature**: 026-objective-scores
**Date**: 2026-01-15

## Overview

This contract defines the behavior for passing through `objective_scores` from adapter evaluation results to engine state, iteration history, and evolution results.

## Contract 1: EvaluationBatch Objective Scores

**Location**: ports/adapter.py

**Existing Contract** (no changes required):
```python
@dataclass(frozen=True, slots=True)
class EvaluationBatch(Generic[Trajectory, RolloutOutput]):
    outputs: list[RolloutOutput]
    scores: list[Score]
    trajectories: list[Trajectory] | None = None
    objective_scores: list[dict[ComponentName, Score]] | None = None
    metadata: list[dict[str, Any]] | None = None
```

**Invariants**:
- When `objective_scores` is not None: `len(objective_scores) == len(scores)`
- Each dict in the list may have different keys (objectives vary by example)
- Values are floats (Score type alias)

---

## Contract 2: IterationRecord Objective Scores

**Location**: domain/models.py

**New Field**:
```python
@dataclass(slots=True, frozen=True, kw_only=True)
class IterationRecord:
    iteration_number: int
    score: float
    instruction: str
    accepted: bool
    objective_scores: list[dict[str, float]] | None = None  # NEW
```

**Invariants**:
- `objective_scores` is None when adapter evaluation did not provide them
- When not None, represents the valset evaluation batch's objective_scores
- Immutable (frozen dataclass)

**Contract Tests**:
```python
def test_iteration_record_with_objective_scores():
    """IterationRecord stores objective_scores when provided."""
    record = IterationRecord(
        iteration_number=1,
        score=0.85,
        instruction="Be helpful",
        accepted=True,
        objective_scores=[{"accuracy": 0.9, "latency": 0.8}],
    )
    assert record.objective_scores == [{"accuracy": 0.9, "latency": 0.8}]

def test_iteration_record_without_objective_scores():
    """IterationRecord defaults objective_scores to None."""
    record = IterationRecord(
        iteration_number=1,
        score=0.85,
        instruction="Be helpful",
        accepted=True,
    )
    assert record.objective_scores is None
```

---

## Contract 3: EvolutionResult Objective Scores

**Location**: domain/models.py

**New Field**:
```python
@dataclass(slots=True, frozen=True, kw_only=True)
class EvolutionResult:
    original_score: float
    final_score: float
    evolved_instruction: str
    iteration_history: list[IterationRecord]
    total_iterations: int
    valset_score: float | None = None
    trainset_score: float | None = None
    objective_scores: list[dict[str, float]] | None = None  # NEW
```

**Invariants**:
- `objective_scores` is None when no objective scores were tracked
- When not None, represents the best candidate's final objective scores
- Immutable (frozen dataclass)

**Contract Tests**:
```python
def test_evolution_result_with_objective_scores():
    """EvolutionResult includes objective_scores from best candidate."""
    result = EvolutionResult(
        original_score=0.6,
        final_score=0.85,
        evolved_instruction="Be helpful",
        iteration_history=[],
        total_iterations=10,
        objective_scores=[{"accuracy": 0.95}],
    )
    assert result.objective_scores == [{"accuracy": 0.95}]

def test_evolution_result_without_objective_scores():
    """EvolutionResult defaults objective_scores to None."""
    result = EvolutionResult(
        original_score=0.6,
        final_score=0.85,
        evolved_instruction="Be helpful",
        iteration_history=[],
        total_iterations=10,
    )
    assert result.objective_scores is None
```

---

## Contract 4: Engine Passthrough Behavior

**Location**: engine/async_engine.py

**Behavior Specification**:

### 4.1 Baseline Initialization

When initializing baseline:
- Extract `objective_scores` from scoring_batch (valset evaluation)
- Store in `_EngineState.best_objective_scores`

### 4.2 Iteration Recording

When recording an iteration:
- Pass `objective_scores` from scoring_batch to `IterationRecord`
- Include regardless of whether proposal was accepted

### 4.3 Proposal Acceptance

When accepting a proposal:
- Update `_EngineState.best_objective_scores` from scoring_batch

### 4.4 Result Building

When building final result:
- Include `_EngineState.best_objective_scores` in `EvolutionResult`

**Contract Tests**:
```python
async def test_engine_passes_through_objective_scores():
    """Engine passes objective_scores from adapter to result."""
    adapter = MockAdapterWithObjectiveScores()  # Returns objective_scores
    engine = AsyncGEPAEngine(adapter, config, candidate, batch)
    result = await engine.run()
    assert result.objective_scores is not None

async def test_engine_handles_missing_objective_scores():
    """Engine handles adapters without objective_scores gracefully."""
    adapter = MockAdapterWithoutObjectiveScores()  # Returns None
    engine = AsyncGEPAEngine(adapter, config, candidate, batch)
    result = await engine.run()
    assert result.objective_scores is None

async def test_iteration_history_includes_objective_scores():
    """Each iteration record includes objective_scores from that iteration."""
    adapter = MockAdapterWithObjectiveScores()
    engine = AsyncGEPAEngine(adapter, config, candidate, batch)
    result = await engine.run()
    for record in result.iteration_history:
        # Each record should have objective_scores (from mock)
        assert record.objective_scores is not None
```

---

## Contract 5: Backward Compatibility

**Guarantee**: Existing code that does not use `objective_scores` continues to work without modification.

**Contract Tests**:
```python
def test_iteration_record_backward_compatible():
    """Creating IterationRecord without objective_scores works."""
    record = IterationRecord(
        iteration_number=1,
        score=0.85,
        instruction="Be helpful",
        accepted=True,
    )
    # Old code accessing existing fields works
    assert record.iteration_number == 1
    assert record.score == 0.85

def test_evolution_result_backward_compatible():
    """Creating EvolutionResult without objective_scores works."""
    result = EvolutionResult(
        original_score=0.6,
        final_score=0.85,
        evolved_instruction="Be helpful",
        iteration_history=[],
        total_iterations=10,
    )
    # Old code accessing existing fields works
    assert result.final_score == 0.85
    assert result.improvement == 0.25
```

---

## Summary

| Contract | Type | Validation |
|----------|------|------------|
| EvaluationBatch | Existing | Length alignment when not None |
| IterationRecord | New field | Optional, defaults to None |
| EvolutionResult | New field | Optional, defaults to None |
| Engine passthrough | Behavior | Extract, store, pass through |
| Backward compatibility | Guarantee | Existing code unchanged |

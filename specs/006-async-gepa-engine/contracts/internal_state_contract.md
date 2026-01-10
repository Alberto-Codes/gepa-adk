# Internal State Contract

**Feature**: 006-async-gepa-engine
**Date**: 2026-01-10
**Version**: 1.0

## Overview

This document defines the internal state management contract for `AsyncGEPAEngine`. While internal, documenting this ensures consistent behavior and aids testing.

## _EngineState (Private)

Internal mutable state during evolution run.

### Fields

```python
@dataclass
class _EngineState:
    """Internal engine state (not exported)."""
    
    iteration: int = 0
    """Current iteration number (0-based internally, 1-indexed in records)."""
    
    best_candidate: Candidate
    """Best candidate found so far."""
    
    best_score: float
    """Score of best candidate (updated on acceptance)."""
    
    stagnation_counter: int = 0
    """Iterations since last improvement (reset on acceptance)."""
    
    iteration_history: list[IterationRecord] = field(default_factory=list)
    """All iteration records (grows with each iteration)."""
    
    original_score: float
    """Baseline score from first evaluation (immutable after set)."""
```

### State Transitions

#### Initialization Flow

```
AsyncGEPAEngine.__init__()
       │
       ▼
  _state = None (uninitialized)
       │
       ▼ run() called
       │
  await _initialize_baseline()
       │
       ▼
  _state = _EngineState(
      iteration=0,
      best_candidate=initial_candidate,
      best_score=baseline_score,
      stagnation_counter=0,
      iteration_history=[],
      original_score=baseline_score,
  )
```

#### Iteration Flow

```
Each iteration:
       │
       ▼
  _state.iteration += 1
       │
       ▼ Evaluate proposal
       │
  ┌────┴────┐
  ▼         ▼
ACCEPT    REJECT
  │         │
  ▼         ▼
_state.best_candidate = proposal    (no change)
_state.best_score = proposal_score  (no change)
_state.stagnation_counter = 0       _state.stagnation_counter += 1
  │         │
  └────┬────┘
       ▼
  _state.iteration_history.append(
      IterationRecord(
          iteration_number=_state.iteration,
          score=proposal_score,
          instruction=proposal_text,
          accepted=<True|False>,
      )
  )
```

#### Completion Flow

```
_should_stop() returns True
       │
       ▼
  _build_result()
       │
       ▼
  return EvolutionResult(
      original_score=_state.original_score,
      final_score=_state.best_score,
      evolved_instruction=_state.best_candidate.components["instruction"],
      iteration_history=_state.iteration_history,
      total_iterations=_state.iteration,
  )
```

## State Invariants

### Throughout Execution

| Invariant | Description |
|-----------|-------------|
| `iteration >= 0` | Never negative |
| `best_score >= 0` | Scores assumed non-negative |
| `stagnation_counter >= 0` | Never negative |
| `stagnation_counter <= patience` | Reset or stop before exceeding |
| `len(iteration_history) == iteration` | One record per iteration |

### After Initialization

| Invariant | Description |
|-----------|-------------|
| `original_score == first evaluation result` | Never changes |
| `best_score >= original_score` (typical) | Only accepts improvements |

### After Acceptance

| Invariant | Description |
|-----------|-------------|
| `stagnation_counter == 0` | Reset on every acceptance |
| `best_candidate.generation == previous + 1` | Lineage tracking |

### After Rejection

| Invariant | Description |
|-----------|-------------|
| `stagnation_counter == previous + 1` | Incremented |
| `best_candidate unchanged` | Preserved |
| `best_score unchanged` | Preserved |

## Helper Method Contracts

### _should_stop() -> bool

```python
def _should_stop(self) -> bool:
    """Check if evolution should terminate.
    
    Returns:
        True if any stopping condition met.
    
    Contract:
        - Returns True if iteration >= config.max_iterations
        - Returns True if patience > 0 AND stagnation_counter >= patience
        - Returns False otherwise
    """
```

### _should_accept(proposal_score, best_score) -> bool

```python
def _should_accept(self, proposal_score: float, best_score: float) -> bool:
    """Check if proposal should be accepted.
    
    Args:
        proposal_score: Score of the proposed candidate.
        best_score: Current best score.
    
    Returns:
        True if proposal_score > best_score + min_improvement_threshold.
    
    Contract:
        - Strict inequality (>) not (>=)
        - Threshold from config.min_improvement_threshold
        - No side effects
    """
```

### _record_iteration(score, instruction, accepted) -> None

```python
def _record_iteration(
    self,
    score: float,
    instruction: str,
    accepted: bool,
) -> None:
    """Record iteration outcome.
    
    Args:
        score: Score achieved in this iteration.
        instruction: Instruction text evaluated.
        accepted: Whether proposal was accepted.
    
    Contract:
        - Creates IterationRecord with current iteration number
        - Appends to iteration_history
        - No other state mutations
    """
```

### _build_result() -> EvolutionResult

```python
def _build_result(self) -> EvolutionResult:
    """Build final result from current state.
    
    Returns:
        Frozen EvolutionResult with all metrics.
    
    Contract:
        - Uses current state values
        - Returns new frozen instance
        - Does not modify state
    """
```

## Testing Contracts

### Unit Test Requirements

| Test Case | State Before | Action | State After |
|-----------|--------------|--------|-------------|
| Acceptance | stagnation=2 | Accept proposal | stagnation=0, best updated |
| Rejection | stagnation=0 | Reject proposal | stagnation=1, best unchanged |
| Early stop | stagnation=patience-1 | Reject | should_stop=True |
| Max iterations | iteration=max-1 | Any | should_stop=True |
| Threshold check | best=0.80, proposal=0.805, thresh=0.01 | Check | reject |
| Threshold check | best=0.80, proposal=0.82, thresh=0.01 | Check | accept |

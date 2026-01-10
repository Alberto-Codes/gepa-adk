# AsyncGEPAEngine API Contract

**Feature**: 006-async-gepa-engine
**Date**: 2026-01-10
**Version**: 1.0

## Overview

This document defines the public API contract for `AsyncGEPAEngine`, the core evolution orchestrator for gepa-adk.

## Module

```
src/gepa_adk/engine/async_engine.py
```

## Public API

### AsyncGEPAEngine

The main engine class for orchestrating async evolution loops.

#### Constructor

```python
def __init__(
    self,
    adapter: AsyncGEPAAdapter[DataInst, Trajectory, RolloutOutput],
    config: EvolutionConfig,
    initial_candidate: Candidate,
    batch: list[DataInst],
) -> None:
    """Initialize the evolution engine.

    Args:
        adapter: Implementation of AsyncGEPAAdapter protocol for evaluation
            and proposal generation.
        config: Evolution parameters controlling iterations, thresholds,
            and early stopping.
        initial_candidate: Starting candidate with 'instruction' component.
        batch: Evaluation data instances for scoring candidates.

    Raises:
        ValueError: If batch is empty or initial_candidate lacks 'instruction'.
        ConfigurationError: If config validation fails (via EvolutionConfig).

    Examples:
        ```python
        from gepa_adk.engine import AsyncGEPAEngine
        from gepa_adk.domain.models import EvolutionConfig, Candidate

        engine = AsyncGEPAEngine(
            adapter=my_adapter,
            config=EvolutionConfig(max_iterations=50),
            initial_candidate=Candidate(components={"instruction": "Be helpful"}),
            batch=training_data,
        )
        ```
    """
```

#### run() Method

```python
async def run(self) -> EvolutionResult:
    """Execute the evolution loop.

    Runs the core evolution loop:
    1. Evaluate baseline candidate
    2. For each iteration until max_iterations or convergence:
       a. Generate reflective dataset from traces
       b. Propose new candidate text
       c. Evaluate proposal
       d. Accept if improves above threshold
       e. Record iteration
    3. Return frozen EvolutionResult

    Returns:
        EvolutionResult containing:
            - original_score: Baseline score before evolution
            - final_score: Best score achieved
            - evolved_instruction: Best instruction text found
            - iteration_history: List of IterationRecord objects
            - total_iterations: Number of iterations performed

    Raises:
        Exception: Any exceptions from adapter methods propagate unchanged.

    Examples:
        ```python
        result = await engine.run()
        print(f"Improved: {result.improved}")
        print(f"Best score: {result.final_score}")
        ```

    Notes:
        - Engine instance should not be reused after run() completes
        - Method is idempotent if called multiple times (restarts fresh)
        - Fail-fast behavior: adapter exceptions are not caught
    """
```

## Type Signatures

### Imports Required

```python
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.domain.models import (
    EvolutionConfig,
    EvolutionResult,
    IterationRecord,
    Candidate,
)
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch
```

### Full Type Signature

```python
class AsyncGEPAEngine(Generic[DataInst, Trajectory, RolloutOutput]):
    """Async evolution engine orchestrating the GEPA loop."""
    
    adapter: AsyncGEPAAdapter[DataInst, Trajectory, RolloutOutput]
    config: EvolutionConfig
    
    def __init__(
        self,
        adapter: AsyncGEPAAdapter[DataInst, Trajectory, RolloutOutput],
        config: EvolutionConfig,
        initial_candidate: Candidate,
        batch: list[DataInst],
    ) -> None: ...
    
    async def run(self) -> EvolutionResult: ...
```

## Behavioral Contracts

### Invariants

| Invariant | Description |
|-----------|-------------|
| `result.total_iterations <= config.max_iterations` | Never exceeds configured max |
| `len(result.iteration_history) == result.total_iterations` | One record per iteration |
| `result.final_score >= result.original_score` (usually) | Best score returned |
| `all(r.iteration_number > 0 for r in history)` | 1-indexed iteration numbers |

### Preconditions

| Method | Preconditions |
|--------|---------------|
| `__init__` | `len(batch) > 0` |
| `__init__` | `"instruction" in initial_candidate.components` |
| `run` | Engine not currently running |

### Postconditions

| Method | Postconditions |
|--------|----------------|
| `run` | Returns valid `EvolutionResult` |
| `run` | `result.evolved_instruction` is non-empty string |
| `run` | `result.original_score` equals first evaluation score |

### Stopping Conditions

The engine stops when **either**:

1. **Max iterations reached**: `iteration >= config.max_iterations`
2. **Patience exhausted**: `stagnation_counter >= config.patience` (when `patience > 0`)

### Acceptance Logic

A proposal is accepted when:
```
proposal_score > best_score + config.min_improvement_threshold
```

## Error Handling

### Constructor Errors

| Condition | Exception | Message |
|-----------|-----------|---------|
| Empty batch | `ValueError` | "batch must contain at least one data instance" |
| Missing instruction | `ValueError` | "initial_candidate must have 'instruction' component" |
| Invalid config | `ConfigurationError` | Field-specific message from config validation |

### Runtime Errors

| Condition | Behavior |
|-----------|----------|
| Adapter.evaluate raises | Exception propagates to caller |
| Adapter.make_reflective_dataset raises | Exception propagates to caller |
| Adapter.propose_new_texts raises | Exception propagates to caller |

## Thread Safety

- `AsyncGEPAEngine` is **not** thread-safe
- Single instance should be used by one async task
- For concurrent evolution runs, create separate engine instances

## Versioning

This contract follows semantic versioning:
- **Major**: Breaking changes to method signatures or behavior
- **Minor**: New methods, optional parameters
- **Patch**: Bug fixes without API changes


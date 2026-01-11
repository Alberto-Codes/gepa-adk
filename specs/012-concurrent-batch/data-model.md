# Data Model: Concurrent Batch Evaluation

**Feature**: 012-concurrent-batch
**Date**: 2026-01-11
**Status**: Complete

## Entity Changes

This feature modifies existing entities rather than introducing new ones. The core data model remains unchanged; only internal implementation patterns change.

### Modified Entities

#### ADKAdapter (adapters/adk_adapter.py)

**New Attribute**:

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_concurrent_evals` | `int` | `5` | Maximum number of concurrent evaluations to run in parallel |

**Validation Rules**:
- Must be >= 1 (enforced at construction time)
- Values <= 0 treated as invalid and raise `ValueError`

**Constructor Signature Change**:
```python
def __init__(
    self,
    agent: LlmAgent,
    scorer: Scorer,
    max_concurrent_evals: int = 5,  # NEW
    session_service: BaseSessionService | None = None,
    app_name: str = "gepa_adk_eval",
    trajectory_config: TrajectoryConfig | None = None,
) -> None:
```

### Unchanged Entities

The following entities from the spec remain unchanged in structure:

#### EvaluationBatch (ports/adapter.py)

No changes. Already supports:
- `outputs: list[RolloutOutput]` - Parallel results maintain order
- `scores: list[Score]` - Parallel scores maintain order
- `trajectories: list[Trajectory] | None` - Optional parallel trajectories

#### DataInst (ports/adapter.py)

No changes. Type variable `DataInst` bound to input example format.

#### EvolutionConfig (domain/models.py)

No changes. Already contains `max_concurrent_evals: int = 5` which engines can pass to adapters.

#### ADKTrajectory (domain/trajectory.py)

No changes. Error trajectories already support `error: str | None` field.

## State Transitions

### Evaluation State (per batch)

```
┌─────────────┐
│   PENDING   │ Batch received, semaphore not yet created
└──────┬──────┘
       │ evaluate() called
       ▼
┌─────────────┐
│  EXECUTING  │ Tasks submitted to asyncio.gather
└──────┬──────┘
       │ All tasks complete (success or exception)
       ▼
┌─────────────┐
│  COMPLETE   │ Results assembled into EvaluationBatch
└─────────────┘
```

### Per-Example State (within batch)

```
┌─────────────┐
│   QUEUED    │ Waiting for semaphore slot
└──────┬──────┘
       │ Semaphore acquired
       ▼
┌─────────────┐
│  EXECUTING  │ Running _run_single_example
└──────┬──────┘
       │ Execution complete
       ▼
┌─────────────────────────────────────┐
│  SUCCESS         │      FAILED     │
│  output, score   │  "", 0.0, error │
└─────────────────────────────────────┘
```

## Internal Data Structures

### Semaphore-Wrapped Coroutine Result

Internal tuple returned by `_eval_single_with_semaphore()`:

```python
# Success case
tuple[str, float, ADKTrajectory | None]
# (output_text, score, trajectory_or_none)

# Failure case (via return_exceptions=True)
Exception
# Original exception preserved for error message extraction
```

### Gather Results Processing

```python
results: list[tuple[str, float, ADKTrajectory | None] | Exception]
# List maintains batch ordering
# Exceptions appear in-place where evaluation failed
```

## Relationships

```
EvolutionConfig
    └── max_concurrent_evals ──────┐
                                   │ passed to
                                   ▼
                            ADKAdapter
                                │
                                │ creates
                                ▼
                        asyncio.Semaphore(max_concurrent_evals)
                                │
                                │ controls
                                ▼
                    ┌───────────────────────┐
                    │  Concurrent Tasks     │
                    │  _eval_single_*()     │
                    │  (up to N at once)    │
                    └───────────────────────┘
                                │
                                │ produces
                                ▼
                        EvaluationBatch
                            ├── outputs
                            ├── scores
                            └── trajectories
```

## Error Handling Data

When an evaluation fails, the following data structure is used:

```python
# Failed evaluation result
{
    "output": "",           # Empty string for failed output
    "score": 0.0,           # Zero score for failures
    "trajectory": ADKTrajectory(
        tool_calls=[],
        state_deltas=[],
        token_usage=None,
        final_output="",
        error=str(exception),  # Error message preserved
    )
}
```

## Logging Context

Structured log events include:

| Event | Fields |
|-------|--------|
| `adapter.evaluate.start` | `batch_size`, `max_concurrent`, `capture_traces` |
| `adapter.evaluate.complete` | `batch_size`, `successful`, `failed`, `avg_score` |
| `adapter.evaluate.example.error` | `example_index`, `error` (DEBUG level) |

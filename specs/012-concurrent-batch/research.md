# Research: Concurrent Batch Evaluation

**Feature**: 012-concurrent-batch
**Date**: 2026-01-11
**Status**: Complete

## Research Tasks

### 1. asyncio.Semaphore for Rate Limiting

**Question**: How to implement controlled concurrency with asyncio.Semaphore?

**Decision**: Use `asyncio.Semaphore(max_concurrent_evals)` with async context manager pattern.

**Rationale**:
- Semaphore is the idiomatic Python approach for limiting concurrent coroutines
- Context manager ensures proper acquire/release even on exceptions
- Creates backpressure naturally - tasks wait when limit reached

**Implementation Pattern**:
```python
semaphore = asyncio.Semaphore(max_concurrent_evals)

async def eval_one(example: DataInst) -> tuple[str, float, dict]:
    async with semaphore:
        # Only max_concurrent_evals can be here simultaneously
        result = await self._execute_single(example, candidate)
        score = await self.scorer.async_score(...)
        return result.output, score, trajectory
```

**Alternatives Considered**:
- `asyncio.TaskGroup` (Python 3.11+): Good for structured concurrency but doesn't provide rate limiting
- `asyncio.Queue` with worker pool: More complex, better for unbounded streams
- Third-party libraries (aiometer, aiolimiter): Adds dependencies, overkill for this use case

### 2. asyncio.gather with Exception Handling

**Question**: How to run parallel tasks and handle individual failures without blocking others?

**Decision**: Use `asyncio.gather(*tasks, return_exceptions=True)` pattern.

**Rationale**:
- `return_exceptions=True` returns exceptions as results instead of raising
- Preserves result ordering (critical for FR-009)
- All tasks complete regardless of individual failures
- No partial results - always get full batch response

**Implementation Pattern**:
```python
results = await asyncio.gather(
    *[eval_one(ex) for ex in batch],
    return_exceptions=True,
)

for i, r in enumerate(results):
    if isinstance(r, Exception):
        # Handle failure case
        outputs.append("")
        scores.append(0.0)
        trajectories.append({"error": str(r)})
    else:
        # Unpack success case
        outputs.append(r[0])
        scores.append(r[1])
        trajectories.append(r[2])
```

**Alternatives Considered**:
- `asyncio.TaskGroup`: Cancels all tasks on first exception (not desired behavior)
- `asyncio.as_completed`: Doesn't preserve ordering
- Manual task management: More complex, error-prone

### 3. Concurrency Configuration Source

**Question**: Where should max_concurrent_evals come from?

**Decision**: Add `max_concurrent_evals` as constructor parameter to ADKAdapter, defaulting to 5.

**Rationale**:
- `EvolutionConfig.max_concurrent_evals` already exists in domain/models.py with default of 5
- ADKAdapter should receive this value via constructor (dependency injection)
- Keeps configuration centralized in EvolutionConfig
- Engine passes config value to adapter at construction time

**Implementation**:
```python
class ADKAdapter:
    def __init__(
        self,
        agent: LlmAgent,
        scorer: Scorer,
        max_concurrent_evals: int = 5,  # NEW PARAMETER
        session_service: BaseSessionService | None = None,
        ...
    ) -> None:
        self.max_concurrent_evals = max_concurrent_evals
```

**Alternatives Considered**:
- Pass config to each `evaluate()` call: Breaks interface, adds complexity
- Global configuration: Violates hexagonal architecture
- Environment variable: Less explicit, harder to test

### 4. Thread Safety of ADK Agent

**Question**: Is it safe to run multiple concurrent evaluations with same agent instance?

**Decision**: Safe with per-evaluation session isolation (already implemented).

**Rationale**:
- ADKAdapter already creates unique session IDs per evaluation: `_create_session_id()`
- Each `_run_single_example()` call uses isolated session
- Agent instruction override is applied once per batch, before parallel execution
- InMemorySessionService handles concurrent sessions correctly

**Evidence from existing code** (`adk_adapter.py:583-584`):
```python
# Create unique session for isolation (US4)
session_id = self._create_session_id()
```

**Risk Mitigation**:
- Instruction override happens BEFORE gather (single-threaded)
- Restore happens AFTER gather completes (single-threaded)
- Each evaluation gets unique session ID (UUID-based)

### 5. Memory Considerations for Large Batches

**Question**: How to prevent memory exhaustion with batches of 100+ examples?

**Decision**: Semaphore naturally limits concurrent memory usage; no additional measures needed for target scale.

**Rationale**:
- With concurrency=20 and 100 examples, only 20 are in-flight at once
- Each evaluation's memory footprint is bounded by:
  - ADK event stream (flushed after each example)
  - Trajectory data structure
  - Output string
- Results are collected incrementally via gather

**Calculations**:
- Assume 10KB per trajectory (generous estimate)
- 20 concurrent × 10KB = 200KB concurrent memory
- Final results: 100 × 10KB = 1MB total
- Well within reasonable limits

**Alternatives Considered**:
- Chunked processing: Unnecessary complexity for target scale
- Streaming results: Breaks EvaluationBatch contract

### 6. Logging Strategy for Concurrent Execution

**Question**: How to log concurrent evaluation progress meaningfully?

**Decision**: Log at batch level (start/complete) with aggregate metrics, plus per-example debug logs.

**Rationale**:
- Too many logs overwhelm stdout in parallel execution
- Batch-level logs provide actionable information
- Per-example logs at DEBUG level for troubleshooting

**Implementation**:
```python
self._logger.info(
    "adapter.evaluate.start",
    batch_size=len(batch),
    max_concurrent=self.max_concurrent_evals,
)

# After gather completes
self._logger.info(
    "adapter.evaluate.complete",
    batch_size=len(batch),
    successful=sum(1 for r in results if not isinstance(r, Exception)),
    failed=sum(1 for r in results if isinstance(r, Exception)),
    avg_score=avg_score,
)
```

## Key Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rate limiting | asyncio.Semaphore | Idiomatic, simple, handles backpressure |
| Parallel execution | asyncio.gather + return_exceptions=True | Preserves order, handles failures gracefully |
| Configuration | Constructor parameter with default | Matches existing EvolutionConfig pattern |
| Session isolation | Existing UUID-based sessions | Already implemented, thread-safe |
| Memory management | Semaphore-bounded concurrency | Natural limit, no additional measures needed |
| Logging | Batch-level info, example-level debug | Readable output, full debug available |

---

## Validation from Installed Dependencies

### ADK `LocalEvalService` Pattern (google-adk 1.22.0)

The ADK evaluation package (`google.adk.evaluation.local_eval_service`) implements the **exact same pattern** we're proposing:

```python
# From .venv/lib/python3.12/site-packages/google/adk/evaluation/local_eval_service.py

semaphore = asyncio.Semaphore(
    value=inference_request.inference_config.parallelism
)

async def run_inference(eval_case):
    async with semaphore:
        return await self._perform_inference_single_eval_item(
            app_name=inference_request.app_name,
            eval_set_id=inference_request.eval_set_id,
            eval_case=eval_case,
            root_agent=self._root_agent,
        )

inference_results = [run_inference(eval_case) for eval_case in eval_cases]
for inference_result in asyncio.as_completed(inference_results):
    yield await inference_result
```

**Key Observations**:
1. ADK uses `InferenceConfig.parallelism` with default=4 (we use `max_concurrent_evals` default=5)
2. ADK wraps single-item execution in semaphore context manager
3. ADK uses `asyncio.as_completed()` for streaming results (yields as they complete)
4. Our approach uses `asyncio.gather()` to preserve ordering (required by FR-009)

### ADK `EvaluateConfig` for Parallelism

```python
# From .venv/lib/python3.12/site-packages/google/adk/evaluation/base_eval_service.py

class InferenceConfig(BaseModel):
    parallelism: int = Field(
        default=4,
        description="""Number of parallel inferences to run during an Eval. Few
factors to consider while changing this value:

1) Your available quota with the model. Models tend to enforce per-minute or
per-second SLAs. Using a larger value could result in the eval quickly consuming
the quota.

2) The tools used by the Agent could also have their SLA. Using a larger value
could also overwhelm those tools.""",
    )
```

This validates our design to expose `max_concurrent_evals` as a configurable parameter.

### GEPA Core Adapter Protocol (gepa 0.0.24)

The GEPA `GEPAAdapter` protocol shows the **synchronous** batch interface we need to maintain compatibility with:

```python
# From .venv/lib/python3.12/site-packages/gepa/core/adapter.py

def evaluate(
    self,
    batch: list[DataInst],
    candidate: dict[str, str],
    capture_traces: bool = False,
) -> EvaluationBatch[Trajectory, RolloutOutput]:
    """Run the program defined by `candidate` on a batch of data."""
```

**Key Insights**:
1. GEPA's core engine is synchronous (no async evaluate)
2. GEPA MCP adapter uses `asyncio.run()` to bridge sync/async
3. Our `ADKAdapter` is async-first (matches ADK patterns)
4. Sequential iteration in GEPA engine is appropriate - concurrency is within batch

### GEPA MCP Adapter Error Handling

```python
# From .venv/lib/python3.12/site-packages/gepa/adapters/mcp_adapter/mcp_adapter.py

except Exception as e:
    logger.exception(f"Failed to evaluate item: {item['user_query']}")
    outputs.append({
        "final_answer": "",
        "tool_called": False,
        "selected_tool": None,
        "tool_response": None,
    })
    scores.append(self.failure_score)
```

This validates our error handling approach: catch exceptions per-example, log them, return empty output with 0.0 score.

---

## Implementation Approach

1. **Add `max_concurrent_evals` parameter** to `ADKAdapter.__init__()`
2. **Create helper method** `_eval_single_with_semaphore()` that wraps single example evaluation
3. **Refactor `evaluate()` method**:
   - Create semaphore from config
   - Build list of coroutines for all batch items
   - Execute with `asyncio.gather(return_exceptions=True)`
   - Process results, handling exceptions as failures
   - Return EvaluationBatch with all results
4. **Update tests** across all three layers
5. **Update docstrings** for modified methods


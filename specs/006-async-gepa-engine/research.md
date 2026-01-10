# Research: AsyncGEPAEngine Implementation

**Feature**: 006-async-gepa-engine
**Date**: 2026-01-10
**Purpose**: Resolve technical questions and document design decisions for the async evolution engine

## Research Questions

### Q1: GEPA Engine Loop Pattern Analysis

**Decision**: Adapt GEPA's synchronous loop pattern to async-first design while simplifying for single-objective v1.

**Findings from GEPA's `GEPAEngine` (`.venv/lib/python3.12/site-packages/gepa/core/engine.py`)**:

GEPA's engine follows this core loop structure:
```python
# GEPA's synchronous pattern
def run(self) -> GEPAState:
    state = initialize_gepa_state(...)

    while not self._should_stop(state):
        state.i += 1

        # 1. Propose new candidate via reflective mutation
        proposal = self.reflective_proposer.propose(state)

        # 2. Check acceptance (subsample scores)
        if new_sum > old_sum:  # strict improvement
            # 3. Full evaluation and add to pool
            self._run_full_eval_and_add(proposal.candidate, state, ...)

    return state
```

**gepa-adk Async Adaptation**:
```python
# Our async pattern
async def run(self) -> EvolutionResult:
    await self._initialize_baseline()

    while not self._should_stop():
        self._iteration += 1

        # 1. Async evaluation of current best
        eval_batch = await self.adapter.evaluate(batch, candidate, ...)

        # 2. Async proposal generation
        reflective_data = await self.adapter.make_reflective_dataset(...)
        new_texts = await self.adapter.propose_new_texts(...)

        # 3. Async evaluation of proposal
        proposal_eval = await self.adapter.evaluate(batch, proposal, ...)

        # 4. Acceptance check
        if self._should_accept(proposal_score, best_score):
            self._accept_proposal(...)

    return self._build_result()
```

**Key Differences**:
| Aspect | GEPA | gepa-adk |
|--------|------|----------|
| Execution | Synchronous | Async (await-based) |
| State | Mutable `GEPAState` class | Internal mutable state, frozen result |
| Proposer | Separate class (`ReflectiveMutationProposer`) | Delegated to adapter protocol |
| Stopping | Callback-based (`StopperProtocol`) | Direct check (max_iterations + patience) |
| Pareto | Multi-objective tracking | Single-objective v1, extensible |

**Rationale**: Simplify for v1 while maintaining architectural extensibility. GEPA's complexity (merge proposer, pareto fronts, multiple stoppers) deferred to future versions.

---

### Q2: Internal State Design

**Decision**: Use internal mutable state during `run()`, return frozen `EvolutionResult`.

**Analysis**:

GEPA uses a complex `GEPAState` class with:
- Multiple candidate pools
- Pareto front tracking per validation example
- Objective scores aggregation
- Persistence via pickle

gepa-adk v1 needs simpler state:

```python
# Internal state (mutable during run)
class _EngineState:
    iteration: int = 0
    best_candidate: Candidate
    best_score: float
    stagnation_counter: int = 0
    iteration_history: list[IterationRecord] = []
    original_score: float
```

**Rationale**:
- Separation of concerns: mutable state for processing, frozen result for output
- Aligns with existing `EvolutionResult` (frozen dataclass)
- Simpler than GEPA's generic `GEPAState[RolloutOutput, DataId]`

---

### Q3: Stopping Conditions

**Decision**: Implement two stopping conditions directly, no stopper protocol in v1.

**GEPA's Approach**:
- `StopperProtocol` with composable stoppers
- `MaxMetricCallsStopper`, `FileStopper`, `TimeoutStopCondition`
- `CompositeStopper` for combining

**gepa-adk v1 Simplification**:
```python
def _should_stop(self) -> bool:
    # Condition 1: Max iterations reached
    if self._state.iteration >= self.config.max_iterations:
        return True

    # Condition 2: Early stopping (patience exhausted)
    if self.config.patience > 0:
        if self._state.stagnation_counter >= self.config.patience:
            return True

    return False
```

**Rationale**:
- Two conditions sufficient for v1 use cases
- Stopper protocol adds complexity without immediate benefit
- Can extend to protocol-based stoppers in v2 if needed

---

### Q4: Acceptance Logic

**Decision**: Accept when `proposal_score > best_score + min_improvement_threshold`.

**GEPA's Pattern**:
```python
# Strict improvement on subsample
old_sum = sum(proposal.subsample_scores_before or [])
new_sum = sum(proposal.subsample_scores_after or [])
if new_sum <= old_sum:
    continue  # Skip, no improvement
```

**gepa-adk Design**:
```python
def _should_accept(self, proposal_score: float, best_score: float) -> bool:
    threshold = self.config.min_improvement_threshold
    return proposal_score > best_score + threshold
```

**Rationale**:
- `min_improvement_threshold` allows configurable noise filtering
- Single score comparison (not sum of subscores) for v1 simplicity
- Matches spec FR-005

---

### Q5: Batch Handling and Score Aggregation

**Decision**: Aggregate batch scores via mean for single score per iteration.

**GEPA's Pattern**:
- Tracks per-example scores in `prog_candidate_val_subscores`
- Aggregates via policy (`FullEvaluationPolicy`)

**gepa-adk v1 Approach**:
```python
async def _evaluate_candidate(self, candidate: Candidate) -> float:
    eval_batch = await self.adapter.evaluate(
        self._batch,
        candidate.components,
        capture_traces=True,
    )
    # Aggregate: mean of per-example scores
    return sum(eval_batch.scores) / len(eval_batch.scores)
```

**Rationale**:
- Mean aggregation is standard for single-objective
- `EvaluationBatch.scores` already provides per-example scores
- Can extend to weighted/custom aggregation in v2

---

### Q6: Candidate Lineage Tracking

**Decision**: Update `Candidate.generation` and `parent_id` on acceptance.

**Design**:
```python
def _accept_proposal(self, proposal: Candidate, score: float) -> None:
    # Create new candidate with lineage
    new_candidate = Candidate(
        components=dict(proposal.components),
        generation=self._state.best_candidate.generation + 1,
        parent_id=f"gen-{self._state.best_candidate.generation}",
    )
    self._state.best_candidate = new_candidate
    self._state.best_score = score
    self._state.stagnation_counter = 0
```

**Rationale**:
- Matches spec FR-012
- `Candidate` dataclass already has `generation` and `parent_id` fields
- Enables future visualization/debugging of evolution path

---

### Q7: Iteration Record Creation

**Decision**: Create `IterationRecord` for every iteration, capturing proposal outcome.

**Design**:
```python
def _record_iteration(
    self,
    score: float,
    instruction: str,
    accepted: bool,
) -> None:
    record = IterationRecord(
        iteration_number=self._state.iteration,
        score=score,
        instruction=instruction,
        accepted=accepted,
    )
    self._state.iteration_history.append(record)
```

**Rationale**:
- Complete history for analysis (spec SC-004)
- 1-indexed `iteration_number` for human readability (per existing model)
- Records both accepted and rejected proposals

---

### Q8: Error Handling Strategy

**Decision**: Fail-fast in v1 - propagate adapter exceptions to caller.

**GEPA's Pattern**:
```python
try:
    # ... iteration logic
except Exception as e:
    self.logger.log(f"Exception: {e}")
    if self.raise_on_exception:
        raise e
    else:
        continue  # Skip iteration
```

**gepa-adk v1**:
```python
# No try/catch in core loop - let exceptions propagate
async def run(self) -> EvolutionResult:
    await self._initialize_baseline()

    while not self._should_stop():
        # Exceptions from adapter.evaluate() propagate to caller
        eval_batch = await self.adapter.evaluate(...)
```

**Rationale**:
- Simpler debugging in development phase
- Caller can implement retry logic if needed
- Matches spec assumption: "fail-fast behavior"

---

## Resolved Questions Summary

| Question | Resolution |
|----------|------------|
| Loop pattern | Async adaptation of GEPA's while-not-stop loop |
| Internal state | Mutable `_EngineState` class, frozen `EvolutionResult` output |
| Stopping | Direct check: max_iterations OR patience exhausted |
| Acceptance | `proposal_score > best_score + min_improvement_threshold` |
| Score aggregation | Mean of batch scores |
| Lineage | Update `generation` and `parent_id` on acceptance |
| Iteration records | Record every iteration with outcome |
| Error handling | Fail-fast, propagate exceptions |

## Implementation Notes

### Constructor Signature

```python
class AsyncGEPAEngine:
    def __init__(
        self,
        adapter: AsyncGEPAAdapter,
        config: EvolutionConfig,
        initial_candidate: Candidate,
        batch: list[Any],  # DataInst instances
    ) -> None:
        ...
```

**Notes**:
- `batch` parameter provides evaluation data (trainset/valset)
- No proposer parameter - adapter handles proposal generation
- No logger parameter in v1 - use structlog at call site

### Public API

```python
async def run(self) -> EvolutionResult:
    """Execute the evolution loop.

    Returns:
        EvolutionResult with best candidate and iteration history.

    Raises:
        Exceptions from adapter methods propagate unchanged.
    """
```

Single public method for v1. Future versions may add:
- `run_with_callback(on_iteration: Callable)` for progress tracking
- `stop()` for graceful shutdown (like GEPA's `request_stop()`)

## No Outstanding NEEDS CLARIFICATION

All technical questions resolved. Ready for Phase 1 design.

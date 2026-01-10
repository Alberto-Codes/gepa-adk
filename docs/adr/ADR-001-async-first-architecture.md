# ADR-001: Async-First Architecture

> **Status**: Accepted
> **Date**: 2026-01-10
> **Deciders**: gepa-adk maintainers

## Context

gepa-adk bridges GEPA's evolutionary optimization with Google ADK's agent execution. We face a fundamental design choice:

1. **GEPA** (upstream): Synchronous API (`def run()`, `def evaluate()`)
2. **Google ADK**: Async-native (`async def run_async()`, `await runner.run_async()`)

The current agent-workflow-suite bridges these with `asyncio.run()` wrappers:

```python
# Current approach (problematic)
def run_async(coro):
    return asyncio.run(coro)  # Creates new event loop per call!

result = run_async(executor.execute_agent(...))  # Blocks, inefficient
```

This creates problems:
- **Performance**: New event loop per call prevents concurrent execution
- **Nesting issues**: Can't call from existing async context
- **Resource waste**: No benefit from async I/O multiplexing

## Decision

Adopt **async-first architecture** throughout gepa-adk:

1. **All core APIs are async** (`async def`)
2. **Sync wrappers provided** only at top-level for convenience
3. **No internal sync/async bridging** - async all the way down

### Async Protocol

```python
# ports/adapter.py
class AsyncGEPAAdapter(Protocol):
    """All methods are coroutines."""

    async def evaluate(
        self,
        batch: list[DataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Execute candidate on batch - can await ADK calls directly."""
        ...

    async def make_reflective_dataset(self, ...) -> Mapping:
        """Build reflective dataset - can await critic scoring."""
        ...

    async def propose_new_texts(self, ...) -> dict[str, str]:
        """Propose new instructions - can await reflection agent."""
        ...
```

### Async Engine

```python
# engine/async_engine.py
class AsyncGEPAEngine:
    """Async-first evolution engine."""

    async def run(self) -> EvolutionResult:
        """Main evolution loop - fully async."""
        state = await self._initialize_state()

        while not self._should_stop(state):
            # Async evaluation - no blocking!
            eval_batch = await self.adapter.evaluate(
                batch, candidate, capture_traces=True
            )

            # Async proposal via ADK reflection agent
            proposal = await self.proposer.propose(state, eval_batch)

            if proposal and self._should_accept(proposal, state):
                await self._run_full_eval_and_add(proposal, state)

        return self._build_result(state)
```

### Concurrent Batch Evaluation

The key performance win from async-first:

```python
async def evaluate(self, batch: list[DataInst], candidate: dict[str, str], ...):
    """Evaluate batch with controlled concurrency."""
    semaphore = asyncio.Semaphore(self.config.max_concurrent_evals)  # e.g., 5

    async def eval_one(example: DataInst) -> EvalResult:
        async with semaphore:
            result = await self.executor.execute_agent(
                agent_name=self.agent_name,
                input_text=example["input"],
                instruction_override=candidate.get("instruction"),
            )
            score, feedback = await self.critic_scorer.score(
                example["input"], result.output, result.session_id
            )
            return EvalResult(result.output, score, feedback)

    # Parallel evaluation with rate limiting
    results = await asyncio.gather(*[eval_one(ex) for ex in batch])
    return EvaluationBatch.from_results(results)
```

**Performance Impact** (10 examples, 30s each):
- Sequential (sync): 10 × 30s = **300s**
- Concurrent (5 parallel): 2 × 30s = **60s** (5x faster)

### Public API

```python
# api.py - Public interface

async def evolve(
    agent: LlmAgent,
    trainset: list[dict],
    *,
    critic: LlmAgent | None = None,
    config: EvolutionConfig | None = None,
) -> EvolutionResult:
    """Evolve agent instructions (async).

    This is the primary API. Use in async contexts:

        result = await evolve(agent, trainset, critic=critic)

    Args:
        agent: ADK agent to evolve.
        trainset: Training examples.
        critic: Optional critic agent for scoring.
        config: Evolution configuration.

    Returns:
        EvolutionResult with evolved instruction and metrics.
    """
    ...


def evolve_sync(
    agent: LlmAgent,
    trainset: list[dict],
    **kwargs,
) -> EvolutionResult:
    """Synchronous wrapper for evolve().

    Convenience function for scripts/notebooks without async.
    Creates event loop internally - do NOT call from async context.

        result = evolve_sync(agent, trainset, critic=critic)

    For CLI commands and async applications, use `evolve()` directly.
    """
    return asyncio.run(evolve(agent, trainset, **kwargs))
```

### Usage Patterns

#### Async Context (Preferred)

```python
# In async application or CLI
async def main():
    result = await evolve(agent, trainset, critic=critic)
    print(f"Evolved: {result.evolved_instruction}")

asyncio.run(main())  # Single event loop at top level
```

#### Sync Context (Convenience)

```python
# In Jupyter notebook or simple script
from gepa_adk import evolve_sync

result = evolve_sync(agent, trainset, critic=critic)
print(f"Evolved: {result.evolved_instruction}")
```

#### Streaming Updates

```python
# Async generator for progress updates
async for update in evolve_stream(agent, trainset, critic=critic):
    print(f"Iteration {update.iteration}: score={update.score:.3f}")

# Final result
print(f"Final: {update.result.evolved_instruction}")
```

## Consequences

### Positive

- **Performance**: 3-5x speedup via concurrent evaluation
- **Native ADK integration**: No sync/async impedance mismatch
- **Scalability**: Easy to add more concurrent operations
- **Modern Python**: Aligns with async ecosystem (httpx, aiofiles, etc.)
- **Resource efficiency**: Single event loop, proper I/O multiplexing

### Negative

- **Learning curve**: Developers must understand async/await
- **Debugging complexity**: Async stack traces can be harder to read
- **Testing overhead**: Need `pytest-asyncio` and async fixtures
- **Sync compatibility**: Must provide `evolve_sync()` wrapper for some users

### Neutral

- **No GEPA dependency**: We reimplement algorithm as async (not wrapping sync GEPA)
- **LiteLLM support**: LiteLLM has `acompletion()` for async

## Alternatives Considered

### 1. Sync-First with Async Wrappers

```python
def evolve(...):  # Sync
    ...

async def evolve_async(...):  # Wrapper
    return await asyncio.to_thread(evolve, ...)
```

**Rejected**: 
- Loses concurrency benefits (thread pool, not true async)
- ADK is async-native, would require blocking bridges
- Opposite of ADK's design direction

### 2. Hybrid (Sync Engine, Async Adapters)

```python
class GEPAEngine:  # Sync
    def run(self):
        for batch in batches:
            results = asyncio.run(self.adapter.evaluate(batch))  # Bridge per call
```

**Rejected**:
- Creates new event loop per batch (expensive)
- Can't nest in existing async context
- No concurrent evaluation benefit

### 3. Depend on Sync GEPA Package

```python
from gepa import GEPAEngine  # Upstream sync API
```

**Rejected**:
- GEPA is sync-only
- Would require ugly bridging everywhere
- Lose control over concurrency

### 4. Callback-Based Async

```python
def evolve(agent, trainset, on_complete: Callable):
    # Callback hell
    ...
```

**Rejected**:
- Unidiomatic modern Python
- Hard to compose and reason about
- async/await is the standard

## Implementation Notes

### Testing Async Code

```python
# tests/unit/test_engine.py
import pytest

@pytest.mark.asyncio
async def test_engine_runs_evolution():
    engine = AsyncGEPAEngine(adapter=mock_adapter)
    result = await engine.run()
    assert result.iterations_completed > 0
```

### Async Fixtures

```python
# tests/conftest.py
import pytest_asyncio

@pytest_asyncio.fixture
async def adk_executor():
    """Real ADK executor for integration tests."""
    executor = AgentExecutor(...)
    yield executor
    await executor.close()
```

### Error Handling in Async

```python
async def evaluate(self, batch, ...):
    try:
        results = await asyncio.gather(
            *[self._eval_one(ex) for ex in batch],
            return_exceptions=True,  # Don't fail fast
        )
        # Handle partial failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Example {i} failed: {result}")
                results[i] = self._default_result()
        return results
    except Exception as e:
        raise EvaluationError("Batch evaluation failed", cause=e) from e
```

## References

- [PEP 492 – Coroutines with async and await syntax](https://peps.python.org/pep-0492/)
- [asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [Google ADK async patterns](https://google.github.io/adk-docs/)
- [LiteLLM async usage](https://docs.litellm.ai/docs/completion/async)
- **ADR-002**: Protocol for Interfaces (async protocol definitions)
- **ADR-005**: Three-Layer Testing Strategy (async test patterns)
- **ADR-006**: External Library Integration (async adapters)
- [ADR Index](README.md) - All architectural decisions

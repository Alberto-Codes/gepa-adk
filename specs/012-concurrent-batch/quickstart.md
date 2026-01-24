# Quickstart: Concurrent Batch Evaluation

**Feature**: 012-concurrent-batch
**Date**: 2026-01-11

## Overview

This feature adds parallel batch evaluation to the ADKAdapter, improving evolution run performance by 3-5x through controlled concurrency.

## Basic Usage

### Default Concurrency (5 parallel evaluations)

```python
from google.adk.agents import LlmAgent
from gepa_adk.adapters import ADKAdapter

# Create agent and scorer
agent = LlmAgent(
    name="helper",
    model="gemini-2.5-flash",
    instruction="Be helpful and concise",
)
scorer = MyScorer()

# Adapter uses default concurrency of 5
adapter = ADKAdapter(agent=agent, scorer=scorer)

# Evaluate batch - runs up to 5 evaluations in parallel
batch = [
    {"input": "What is 2+2?", "expected": "4"},
    {"input": "Capital of France?", "expected": "Paris"},
    {"input": "Color of sky?", "expected": "Blue"},
    # ... more examples
]
candidate = {"instruction": "Be precise and brief"}

result = await adapter.evaluate(batch, candidate)
# Returns: EvaluationBatch with outputs, scores, trajectories
```

### Custom Concurrency Limit

```python
# Higher concurrency for faster execution
adapter = ADKAdapter(
    agent=agent,
    scorer=scorer,
    max_concurrent_evals=10,  # Run up to 10 in parallel
)

# Lower concurrency for rate-limited APIs
adapter = ADKAdapter(
    agent=agent,
    scorer=scorer,
    max_concurrent_evals=2,  # Conservative rate limiting
)

# Sequential execution (no parallelism)
adapter = ADKAdapter(
    agent=agent,
    scorer=scorer,
    max_concurrent_evals=1,  # One at a time
)
```

### With Trajectory Capture

```python
# Enable trajectory capture for debugging/reflection
result = await adapter.evaluate(
    batch=batch,
    candidate=candidate,
    capture_traces=True,  # Capture execution traces
)

# Trajectories available for each example
for i, trajectory in enumerate(result.trajectories):
    if trajectory.error:
        print(f"Example {i} failed: {trajectory.error}")
    else:
        print(f"Example {i}: {len(trajectory.tool_calls)} tool calls")
```

## Integration with Evolution Engine

The evolution engine passes configuration to the adapter:

```python
from gepa_adk.domain.models import EvolutionConfig
from gepa_adk.engine import AsyncEvolutionEngine

# Configure evolution with desired concurrency
config = EvolutionConfig(
    max_iterations=50,
    max_concurrent_evals=10,  # Passed to adapter
    patience=5,
)

# Engine constructs adapter with config values
adapter = ADKAdapter(
    agent=agent,
    scorer=scorer,
    max_concurrent_evals=config.max_concurrent_evals,
)

# Run evolution
engine = AsyncEvolutionEngine(adapter=adapter, config=config)
result = await engine.evolve(batch, initial_candidate)
```

## Error Handling

Failed evaluations don't block others:

```python
# Some examples may fail (network errors, timeouts, etc.)
result = await adapter.evaluate(batch, candidate, capture_traces=True)

# Check for failures
for i, (output, score, trajectory) in enumerate(
    zip(result.outputs, result.scores, result.trajectories)
):
    if score == 0.0 and trajectory.error:
        print(f"Example {i} failed: {trajectory.error}")
    else:
        print(f"Example {i} succeeded with score {score:.2f}")
```

## Performance Expectations

| Batch Size | Concurrency | Single Eval Time | Expected Total Time |
|------------|-------------|------------------|---------------------|
| 10 | 5 | 30s | ~60s |
| 20 | 10 | 30s | ~60s |
| 100 | 20 | 30s | ~150s |

Linear speedup: `total_time ≈ (batch_size / concurrency) × single_eval_time`

## Best Practices

1. **Match concurrency to API limits**: If your LLM provider has rate limits, set `max_concurrent_evals` accordingly.

2. **Start conservative**: Begin with lower concurrency (2-5) and increase if stable.

3. **Monitor for failures**: High concurrency can trigger rate limiting or resource exhaustion.

4. **Use trajectory capture for debugging**: Enable `capture_traces=True` when investigating issues.

5. **Consider memory**: Each concurrent evaluation uses memory for events and trajectories. For very large batches, keep concurrency moderate (10-20).

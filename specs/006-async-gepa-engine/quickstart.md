# Quickstart: AsyncGEPAEngine

**Feature**: 006-async-gepa-engine
**Date**: 2026-01-10

## Overview

This guide demonstrates how to use `AsyncGEPAEngine` to evolve agent instructions using the GEPA optimization algorithm with async support.

## Installation

```bash
# From project root
uv sync
```

## Basic Usage

### 1. Create an Adapter

First, implement the `AsyncGEPAAdapter` protocol:

```python
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch
from typing import Any


class MyAdapter:
    """Example adapter implementation."""
    
    async def evaluate(
        self,
        batch: list[dict],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate candidate on data batch."""
        # Your evaluation logic here
        scores = [0.8 for _ in batch]  # Placeholder
        return EvaluationBatch(
            outputs=["output" for _ in batch],
            scores=scores,
            trajectories=None if not capture_traces else [{} for _ in batch],
        )
    
    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> dict[str, list]:
        """Build reflection data from traces."""
        return {comp: [] for comp in components_to_update}
    
    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: dict[str, list],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Generate improved text proposals."""
        return {comp: candidate[comp] + " (improved)" for comp in components_to_update}
```

### 2. Configure Evolution

```python
from gepa_adk.domain.models import EvolutionConfig, Candidate

# Create configuration
config = EvolutionConfig(
    max_iterations=50,         # Maximum evolution steps
    patience=5,                # Stop after 5 iterations without improvement
    min_improvement_threshold=0.01,  # Minimum score gain to accept
    max_concurrent_evals=5,    # Reserved for future concurrent evaluation
)

# Create initial candidate
initial_candidate = Candidate(
    components={"instruction": "You are a helpful assistant."},
    generation=0,
)

# Prepare evaluation batch
training_data = [
    {"input": "Hello", "expected": "Hi there!"},
    {"input": "Help me", "expected": "Sure, what do you need?"},
]
```

### 3. Run Evolution

```python
import asyncio
from gepa_adk.engine import AsyncGEPAEngine


async def main():
    # Create engine
    engine = AsyncGEPAEngine(
        adapter=MyAdapter(),
        config=config,
        initial_candidate=initial_candidate,
        batch=training_data,
    )
    
    # Run evolution
    result = await engine.run()
    
    # Analyze results
    print(f"Original score: {result.original_score:.3f}")
    print(f"Final score: {result.final_score:.3f}")
    print(f"Improvement: {result.improvement:.3f}")
    print(f"Iterations: {result.total_iterations}")
    print(f"Evolved instruction:\n{result.evolved_instruction}")
    
    return result


# Run
result = asyncio.run(main())
```

## Configuration Options

### EvolutionConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_iterations` | `int` | `50` | Maximum evolution iterations |
| `patience` | `int` | `5` | Iterations without improvement before early stop (0 = disabled) |
| `min_improvement_threshold` | `float` | `0.01` | Minimum score delta to accept proposal |
| `max_concurrent_evals` | `int` | `5` | Reserved for concurrent evaluation |
| `reflection_model` | `str` | `"gemini-2.5-flash"` | Model for reflection (passed to adapter) |

### Common Configurations

#### Quick Test Run

```python
config = EvolutionConfig(
    max_iterations=5,
    patience=2,
)
```

#### Production Run

```python
config = EvolutionConfig(
    max_iterations=100,
    patience=10,
    min_improvement_threshold=0.005,
)
```

#### No Early Stopping

```python
config = EvolutionConfig(
    max_iterations=50,
    patience=0,  # Disabled
)
```

#### Baseline Only (No Evolution)

```python
config = EvolutionConfig(
    max_iterations=0,  # Just evaluate baseline
)
```

## Working with Results

### EvolutionResult Properties

```python
result = await engine.run()

# Basic metrics
print(result.original_score)    # Starting score
print(result.final_score)       # Best score achieved
print(result.improvement)       # final - original
print(result.improved)          # True if final > original
print(result.total_iterations)  # Iterations performed

# Best instruction
print(result.evolved_instruction)

# Iteration history
for record in result.iteration_history:
    print(f"Iteration {record.iteration_number}: "
          f"score={record.score:.3f}, accepted={record.accepted}")
```

### Analyzing Iteration History

```python
# Find acceptance rate
accepted = sum(1 for r in result.iteration_history if r.accepted)
total = len(result.iteration_history)
acceptance_rate = accepted / total if total > 0 else 0
print(f"Acceptance rate: {acceptance_rate:.1%}")

# Find best iteration
if result.iteration_history:
    best_iter = max(result.iteration_history, key=lambda r: r.score)
    print(f"Best iteration: {best_iter.iteration_number} "
          f"(score: {best_iter.score:.3f})")
```

## Error Handling

```python
from gepa_adk.domain.exceptions import ConfigurationError


async def safe_evolution():
    try:
        result = await engine.run()
        return result
    except ConfigurationError as e:
        print(f"Invalid configuration: {e}")
        raise
    except ValueError as e:
        print(f"Invalid input: {e}")
        raise
    except Exception as e:
        # Adapter errors propagate through
        print(f"Evolution failed: {e}")
        raise
```

## Testing with Mock Adapter

For unit tests, create a controllable mock:

```python
from gepa_adk.ports.adapter import EvaluationBatch


class MockAdapter:
    """Predictable adapter for testing."""
    
    def __init__(self, scores: list[float]):
        """Initialize with predetermined scores."""
        self._scores = iter(scores)
        self._call_count = 0
    
    async def evaluate(self, batch, candidate, capture_traces=False):
        self._call_count += 1
        score = next(self._scores, 0.5)  # Default if exhausted
        return EvaluationBatch(
            outputs=[None] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
        )
    
    async def make_reflective_dataset(self, candidate, eval_batch, components):
        return {c: [] for c in components}
    
    async def propose_new_texts(self, candidate, dataset, components):
        return {c: f"Improved: {candidate[c]}" for c in components}


# Test with known behavior
async def test_convergence():
    # Scores: baseline 0.5, then improving, then stagnant
    mock = MockAdapter(scores=[0.5, 0.6, 0.7, 0.7, 0.7, 0.7])
    
    engine = AsyncGEPAEngine(
        adapter=mock,
        config=EvolutionConfig(max_iterations=10, patience=3),
        initial_candidate=Candidate(components={"instruction": "Test"}),
        batch=[{"x": 1}],
    )
    
    result = await engine.run()
    
    # Should stop early due to patience
    assert result.total_iterations < 10
    assert result.final_score >= result.original_score
```

## Next Steps

- See `data-model.md` for entity relationships
- See `contracts/async_engine_api.md` for full API contract
- See `research.md` for design decisions and GEPA patterns


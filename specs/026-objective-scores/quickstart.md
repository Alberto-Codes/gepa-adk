# Quickstart: Objective Scores Passthrough

**Feature**: 026-objective-scores
**Date**: 2026-01-15

## Overview

This feature enables passing through multi-objective scores from adapter evaluations to evolution results, allowing users to track and analyze individual objective metrics (e.g., accuracy, latency, cost) alongside the aggregate score.

## Basic Usage

### Adapter Returns Objective Scores

When your adapter's `evaluate()` method returns an `EvaluationBatch` with `objective_scores`, the engine automatically passes them through:

```python
from gepa_adk.ports.adapter import EvaluationBatch

class MyMultiObjectiveAdapter:
    async def evaluate(self, batch, candidate, capture_traces=False):
        # Evaluate each example
        outputs = []
        scores = []
        objective_scores = []

        for example in batch:
            output, score, objectives = await self._evaluate_example(example, candidate)
            outputs.append(output)
            scores.append(score)
            objective_scores.append(objectives)  # e.g., {"accuracy": 0.9, "latency": 0.8}

        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            objective_scores=objective_scores,  # Pass through objectives
        )
```

### Accessing Objective Scores in Results

After evolution completes, access objective scores from the result:

```python
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.domain.models import EvolutionConfig, Candidate

# Run evolution
engine = AsyncGEPAEngine(
    adapter=my_adapter,
    config=EvolutionConfig(max_iterations=50),
    initial_candidate=Candidate(components={"instruction": "Be helpful"}),
    batch=training_data,
)
result = await engine.run()

# Access objective scores from best candidate
if result.objective_scores:
    for i, example_scores in enumerate(result.objective_scores):
        print(f"Example {i}:")
        for objective, score in example_scores.items():
            print(f"  {objective}: {score:.3f}")
```

### Accessing Iteration History

Each iteration record also includes objective scores:

```python
# Analyze objective scores across iterations
for record in result.iteration_history:
    if record.objective_scores:
        # Calculate mean per objective
        objectives = {}
        for example_scores in record.objective_scores:
            for obj, score in example_scores.items():
                objectives.setdefault(obj, []).append(score)

        means = {obj: sum(scores)/len(scores) for obj, scores in objectives.items()}
        print(f"Iteration {record.iteration_number}: {means}")
```

## Backward Compatibility

If your adapter doesn't return `objective_scores`, everything works as before:

```python
class MySimpleAdapter:
    async def evaluate(self, batch, candidate, capture_traces=False):
        outputs = [...]
        scores = [...]

        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            # objective_scores defaults to None
        )

# Result will have objective_scores = None
result = await engine.run()
assert result.objective_scores is None  # No objectives provided
```

## Example: Multi-Objective Analysis

```python
import matplotlib.pyplot as plt

async def run_and_analyze():
    result = await engine.run()

    if not result.objective_scores:
        print("No objective scores available")
        return

    # Extract objectives from iteration history
    iterations = []
    accuracy_means = []
    latency_means = []

    for record in result.iteration_history:
        if record.objective_scores:
            iterations.append(record.iteration_number)
            acc = [s.get("accuracy", 0) for s in record.objective_scores]
            lat = [s.get("latency", 0) for s in record.objective_scores]
            accuracy_means.append(sum(acc) / len(acc))
            latency_means.append(sum(lat) / len(lat))

    # Plot objectives over iterations
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.plot(iterations, accuracy_means)
    ax1.set_xlabel("Iteration")
    ax1.set_ylabel("Mean Accuracy")
    ax1.set_title("Accuracy Over Evolution")

    ax2.plot(iterations, latency_means)
    ax2.set_xlabel("Iteration")
    ax2.set_ylabel("Mean Latency Score")
    ax2.set_title("Latency Over Evolution")

    plt.tight_layout()
    plt.show()
```

## Data Structure Reference

### EvaluationBatch.objective_scores

```python
list[dict[str, float]] | None
```

- **list**: One entry per evaluated example (aligned with `scores`)
- **dict**: Maps objective name to score value
- **None**: When not provided by adapter

### IterationRecord.objective_scores

Same structure as above. Captures the objective scores from the valset evaluation for that iteration.

### EvolutionResult.objective_scores

Same structure as above. Contains the objective scores from the best candidate's final evaluation.

## Key Points

1. **Passthrough Only**: The engine does not aggregate or transform objective scores
2. **Optional**: All fields default to `None` - no changes needed for existing adapters
3. **Index-Aligned**: `objective_scores[i]` corresponds to `scores[i]`
4. **Heterogeneous**: Different examples can have different objective keys

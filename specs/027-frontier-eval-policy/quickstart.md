# Quickstart: Frontier Types and Valset Evaluation Policies

**Feature**: 027-frontier-eval-policy
**Date**: 2026-01-15

## Overview

This quickstart demonstrates how to use the new frontier type and evaluation policy features for multi-objective optimization and scalable validation set handling.

---

## Basic Usage

### Using Different Frontier Types

```python
from gepa_adk.domain.types import FrontierType
from gepa_adk.domain.models import EvolutionConfig, Candidate
from gepa_adk.engine import AsyncGEPAEngine

# Instance-level frontier (default - existing behavior)
config_instance = EvolutionConfig(
    max_iterations=50,
    frontier_type=FrontierType.INSTANCE,  # Default
)

# Objective-level frontier (requires objective_scores from adapter)
config_objective = EvolutionConfig(
    max_iterations=50,
    frontier_type=FrontierType.OBJECTIVE,
)

# Hybrid frontier (tracks both instance and objective)
config_hybrid = EvolutionConfig(
    max_iterations=50,
    frontier_type=FrontierType.HYBRID,
)

# Cartesian frontier (per example × objective pair)
config_cartesian = EvolutionConfig(
    max_iterations=50,
    frontier_type=FrontierType.CARTESIAN,
)
```

### Using Evaluation Policies

```python
from gepa_adk.adapters.evaluation_policy import (
    FullEvaluationPolicy,
    SubsetEvaluationPolicy,
)

# Full evaluation (default - evaluates all validation examples every iteration)
full_policy = FullEvaluationPolicy()

# Subset evaluation (evaluates 20% of validation examples per iteration)
subset_policy = SubsetEvaluationPolicy(subset_size=0.2)

# Subset with fixed count (evaluates exactly 100 examples per iteration)
subset_fixed = SubsetEvaluationPolicy(subset_size=100)

# Create engine with evaluation policy
engine = AsyncGEPAEngine(
    adapter=my_adapter,
    config=config,
    initial_candidate=Candidate(components={"instruction": "Be helpful"}),
    batch=training_data,
    valset=validation_data,  # 1000+ examples
    evaluation_policy=subset_policy,  # Reduces cost by 80%
)
```

---

## Complete Example: Multi-Objective Optimization

```python
import asyncio
from gepa_adk.domain.types import FrontierType
from gepa_adk.domain.models import EvolutionConfig, Candidate
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.adapters.evaluation_policy import SubsetEvaluationPolicy
from gepa_adk.adapters.candidate_selector import ParetoCandidateSelector


async def run_multi_objective_evolution():
    """Run evolution with multi-objective Pareto tracking."""

    # Configure for objective-level frontier tracking
    config = EvolutionConfig(
        max_iterations=100,
        frontier_type=FrontierType.OBJECTIVE,
        min_improvement_threshold=0.01,
        patience=10,
    )

    # Use subset evaluation for large validation set
    evaluation_policy = SubsetEvaluationPolicy(subset_size=0.2)

    # Use Pareto-aware candidate selection
    candidate_selector = ParetoCandidateSelector()

    # Initialize engine
    engine = AsyncGEPAEngine(
        adapter=my_multi_objective_adapter,  # Must provide objective_scores
        config=config,
        initial_candidate=Candidate(
            components={"instruction": "Generate high-quality, efficient code"}
        ),
        batch=training_data,
        valset=large_validation_set,  # 1000+ examples
        evaluation_policy=evaluation_policy,
        candidate_selector=candidate_selector,
    )

    # Run evolution
    result = await engine.run()

    print(f"Original score: {result.original_score}")
    print(f"Final score: {result.final_score}")
    print(f"Objective scores: {result.objective_scores}")
    print(f"Total iterations: {result.total_iterations}")

    return result


if __name__ == "__main__":
    asyncio.run(run_multi_objective_evolution())
```

---

## Adapter Requirements

### For Instance Frontier (default)

```python
class MyAdapter:
    async def evaluate(self, data, components, capture_traces):
        return EvaluationBatch(
            scores=[0.8, 0.7, 0.9],  # Required: per-example scores
            trajectories=[...] if capture_traces else None,
            # objective_scores not required for INSTANCE
        )
```

### For Objective/Hybrid/Cartesian Frontiers

```python
class MyMultiObjectiveAdapter:
    async def evaluate(self, data, components, capture_traces):
        return EvaluationBatch(
            scores=[0.8, 0.7, 0.9],  # Required: per-example aggregate scores
            trajectories=[...] if capture_traces else None,
            objective_scores=[  # Required: per-example, per-objective breakdown
                {"accuracy": 0.9, "latency": 0.7},   # Example 0
                {"accuracy": 0.8, "latency": 0.6},   # Example 1
                {"accuracy": 0.95, "latency": 0.85}, # Example 2
            ],
        )
```

---

## Frontier Type Selection Guide

| Use Case | Recommended Frontier | Rationale |
|----------|---------------------|-----------|
| Single objective (accuracy only) | INSTANCE | Simple per-example tracking |
| Multiple objectives (accuracy + latency) | OBJECTIVE | Balances across objectives |
| Complex tradeoffs | HYBRID | Captures both instance and objective dimensions |
| Fine-grained analysis | CARTESIAN | Maximum granularity for debugging |

---

## Evaluation Policy Selection Guide

| Validation Set Size | Recommended Policy | Subset Size |
|---------------------|-------------------|-------------|
| < 100 examples | FullEvaluationPolicy | N/A |
| 100-500 examples | FullEvaluationPolicy | N/A |
| 500-1000 examples | SubsetEvaluationPolicy | 0.5 (50%) |
| 1000+ examples | SubsetEvaluationPolicy | 0.2 (20%) |
| 10000+ examples | SubsetEvaluationPolicy | 100 (fixed) |

---

## Error Handling

### ConfigurationError for Missing Objective Scores

```python
from gepa_adk.domain.exceptions import ConfigurationError

try:
    # This will fail if adapter doesn't provide objective_scores
    engine = AsyncGEPAEngine(
        config=EvolutionConfig(frontier_type=FrontierType.OBJECTIVE),
        # ... adapter without objective_scores support
    )
    await engine.run()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    print(f"Field: {e.field}")  # "objective_scores"
    print(f"Constraint: {e.constraint}")  # "required for OBJECTIVE frontier"
```

---

## Migration from Existing Code

### Before (INSTANCE only)

```python
# Old code - worked fine
config = EvolutionConfig(max_iterations=50)
engine = AsyncGEPAEngine(adapter=adapter, config=config, ...)
result = await engine.run()
```

### After (backward compatible)

```python
# Same code still works - INSTANCE is default
config = EvolutionConfig(max_iterations=50)
engine = AsyncGEPAEngine(adapter=adapter, config=config, ...)
result = await engine.run()
```

### Upgrade to multi-objective

```python
# Add frontier_type and ensure adapter provides objective_scores
config = EvolutionConfig(
    max_iterations=50,
    frontier_type=FrontierType.OBJECTIVE,
)
engine = AsyncGEPAEngine(
    adapter=multi_objective_adapter,  # Must provide objective_scores
    config=config,
    ...
)
result = await engine.run()
print(result.objective_scores)  # Now available
```

# Quickstart: Acceptance Scoring Alignment

This feature adds a configurable acceptance aggregation mode so evolution
acceptance can follow upstream GEPA semantics while keeping existing behavior
available.

## Use sum-based acceptance (upstream parity)

```python
from gepa_adk import EvolutionConfig, evolve_sync

config = EvolutionConfig(
    max_iterations=10,
    acceptance_metric="sum",
)

result = evolve_sync(
    agent=my_agent,
    trainset=my_trainset,
    config=config,
)

print(result.final_score)  # sum-based acceptance score
print(result.valset_score)  # mean valset score if valset provided
```

## Use mean-based acceptance (legacy behavior)

```python
from gepa_adk import EvolutionConfig, evolve_sync

config = EvolutionConfig(
    max_iterations=10,
    acceptance_metric="mean",
)

result = evolve_sync(
    agent=my_agent,
    trainset=my_trainset,
    config=config,
)

print(result.final_score)  # mean-based acceptance score
```

## Notes

- Acceptance aggregation applies to iteration evaluation batches.
- Validation-set tracking remains mean-based for comparability.

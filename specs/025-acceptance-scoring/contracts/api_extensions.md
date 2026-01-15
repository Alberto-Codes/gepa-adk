# API Extensions: Acceptance Scoring

## EvolutionConfig

Add an acceptance scoring configuration option for acceptance aggregation.

```python
EvolutionConfig(
    acceptance_metric: Literal["sum", "mean"] = "sum",
)
```

**Behavior**
- "sum": acceptance uses the sum of per-example scores from the iteration
  evaluation batch.
- "mean": acceptance uses the mean of per-example scores from the iteration
  evaluation batch (legacy behavior).

**Validation**
- Invalid values raise ConfigurationError with constraint "sum|mean".

## Public API

Expose acceptance_metric via EvolutionConfig passed into evolution entrypoints.

### evolve()
- Accepts EvolutionConfig with acceptance_metric.
- Acceptance decisions follow configured aggregation.

### evolve_group()
- Passes EvolutionConfig to engine; uses acceptance_metric for acceptance.

### evolve_workflow()
- Passes EvolutionConfig to engine; uses acceptance_metric for acceptance.

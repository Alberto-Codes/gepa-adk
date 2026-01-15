# Data Model: Acceptance Scoring Alignment

## Entities

### EvolutionConfig (existing)

Add configuration for acceptance aggregation.

| Field | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| acceptance_metric | "sum" \| "mean" | No | "sum" | Controls acceptance aggregation for iteration evaluation batches. |

**Validation Rules**
- acceptance_metric must be one of "sum" or "mean".

### Engine Acceptance Summary (derived)

Represents the per-iteration aggregation used for acceptance.

| Field | Type | Source | Notes |
| --- | --- | --- | --- |
| acceptance_score | float | iteration evaluation batch | Sum or mean of per-example scores depending on acceptance_metric. |
| valset_score | float \| None | valset evaluation batch | Mean of valset scores when valset is provided. |

**Notes**
- acceptance_score drives accept/reject comparisons.
- valset_score is tracked separately for reporting and EvolutionResult.

### EvolutionResult (existing)

No new fields required, but clarify semantics:

| Field | Current Meaning | Updated Meaning |
| --- | --- | --- |
| final_score | best acceptance score | best acceptance score (sum or mean) |
| valset_score | best acceptance score | mean valset score (if valset provided) |
| trainset_score | mean trainset reflection score | unchanged |

**Note**
If acceptance_metric is "sum", final_score represents a sum-based score and
valset_score captures the mean-based validation metric.

## Relationships

- EvolutionConfig.acceptance_metric determines how acceptance_score is computed.
- Acceptance decisions update EvolutionResult.final_score and valset_score.

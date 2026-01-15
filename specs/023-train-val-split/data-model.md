# Data Model: Train/Val Split for Evolution Scoring

**Feature**: 023-train-val-split
**Date**: 2026-01-14

## Entity Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│    Trainset     │────▶│ Reflection Batch │────▶│ Reflection Dataset │
└─────────────────┘     └──────────────────┘     └───────────────────┘

┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│     Valset      │────▶│  Scoring Batch   │────▶│  Scoring Results   │
└─────────────────┘     └──────────────────┘     └───────────────────┘
```

---

## Domain Entities

### Trainset

**Purpose**: Example set used for reflection and trace capture during evolution.

| Field | Type | Description |
|-------|------|-------------|
| `examples` | `list[Example]` | Input/expected pairs used for reflection |

**Validation Rules**:
- Must be non-empty for evolution runs.
- Examples must follow the expected schema (input + expected output).

---

### Valset

**Purpose**: Example set used for baseline/proposal scoring, acceptance decisions, and candidate selection.

| Field | Type | Description |
|-------|------|-------------|
| `examples` | `list[Example]` | Inputs used to score candidates |
| `is_defaulted` | `bool` | True when valset is derived from trainset |

**Validation Rules**:
- May be omitted; defaults to trainset.
- When provided, must use the same schema as trainset.

---

### Reflection Batch

**Purpose**: A minibatch of trainset examples used for trace capture and reflective dataset generation.

| Field | Type | Description |
|-------|------|-------------|
| `example_ids` | `list[int]` | Indices of trainset examples in the batch |
| `scores` | `list[float]` | Reflection-only scores for the minibatch |
| `trajectories` | `list[Trajectory]` | Execution traces for reflection |

**Validation Rules**:
- `example_ids`, `scores`, and `trajectories` must align in length.

---

### Scoring Batch

**Purpose**: A batch of valset examples used for scoring candidates and making acceptance decisions.

| Field | Type | Description |
|-------|------|-------------|
| `example_ids` | `list[int]` | Indices of valset examples in the batch |
| `scores` | `list[float]` | Scores that determine acceptance and selection |

**Validation Rules**:
- `scores` length must match `example_ids` length.
- Scores are recorded separately from reflection data.

---

### Reflection Dataset

**Purpose**: Structured feedback derived from trainset evaluations, used to propose candidate updates.

| Field | Type | Description |
|-------|------|-------------|
| `component_name` | `str` | Component being updated |
| `feedback_items` | `list[FeedbackItem]` | Trace-driven feedback examples |

**Validation Rules**:
- Must only contain data derived from trainset evaluations.

---

### Scoring Results

**Purpose**: Aggregated valset-based results that drive acceptance decisions and reporting.

| Field | Type | Description |
|-------|------|-------------|
| `candidate_id` | `int` | Candidate index in evolution state |
| `valset_score` | `float` | Aggregate valset score used for acceptance |
| `per_example_scores` | `list[float]` | Optional per-example scores for selection |

**Validation Rules**:
- `valset_score` is computed only from valset examples.
- `per_example_scores` are indexed to valset examples.

---

## Relationships

```
Trainset 1:N Reflection Batch 1:1 Reflection Dataset
Valset 1:N Scoring Batch 1:1 Scoring Results
```

---

## Integration with Existing Models

### EvolutionResult (existing, modified)
- Adds or updates fields to surface valset-based scores separately from reflection data.

### AsyncGEPAEngine (modified)
- Maintains separate evaluation flows for reflection (trainset) and scoring (valset).
- Uses valset scores for acceptance decisions and candidate selection.

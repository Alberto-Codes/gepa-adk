# Data Model: Pass CriticScorer Metadata to Reflection Agent

**Date**: 2026-01-13
**Feature**: 019-critic-metadata-passthrough

## Entity Definitions

### EvaluationBatch (Modified)

Container for evaluation outputs, scores, and optional metadata from scoring.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| outputs | `list[RolloutOutput]` | Yes | Per-example outputs produced during evaluation |
| scores | `list[Score]` | Yes | Per-example normalized scores (higher is better) |
| trajectories | `list[Trajectory] \| None` | No | Optional per-example execution traces |
| objective_scores | `list[dict[ComponentName, Score]] \| None` | No | Optional multi-objective scores per example |
| **metadata** | `list[dict[str, Any]] \| None` | **No (NEW)** | **Optional per-example scorer metadata** |

**Invariants**:
- `len(outputs) == len(scores)`
- If `trajectories` is not None: `len(trajectories) == len(outputs)`
- If `objective_scores` is not None: `len(objective_scores) == len(outputs)`
- **If `metadata` is not None: `len(metadata) == len(outputs)`**

**Index Alignment**: `metadata[i]` contains the scorer metadata for evaluation example `i`, corresponding to `outputs[i]`, `scores[i]`, and optionally `trajectories[i]`.

---

### Scorer Metadata (Value Object)

Dictionary structure returned by scorers alongside numeric scores.

| Field | Type | Required | Source |
|-------|------|----------|--------|
| feedback | `str` | No | CriticScorer - human-readable evaluation feedback |
| actionable_guidance | `str` | No | CriticScorer - specific improvement suggestions |
| dimension_scores | `dict[str, float]` | No | CriticScorer - per-dimension scores (e.g., accuracy, clarity) |
| *(additional fields)* | `Any` | No | Custom scorers may add arbitrary fields |

**Note**: The metadata dict is intentionally flexible (`dict[str, Any]`) to support future scorer implementations with different metadata schemas.

---

### Reflection Example (Value Object)

Dictionary structure passed to the reflection agent for instruction improvement.

| Field | Type | Description |
|-------|------|-------------|
| Inputs | `dict[str, str]` | Component name to value mapping |
| Generated Outputs | `str` | Agent output text |
| Feedback | `str` | **Enhanced feedback string including scorer metadata** |

**Feedback String Format** (enhanced):

```
score: {score:.3f}[, tool_calls: {n}][, tokens: {total}][, error: {msg}]
[Feedback: {feedback_text}]
[Guidance: {actionable_guidance}]
[Dimensions: {key1}={val1}, {key2}={val2}, ...]
```

Sections in brackets are included only when the corresponding metadata field is present and non-empty.

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ADKAdapter.evaluate()                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────┐       ┌─────────────────┐                        │
│   │  Input Example  │──────▶│  Agent Runner   │                        │
│   │  (batch[i])     │       │  (run_async)    │                        │
│   └─────────────────┘       └────────┬────────┘                        │
│                                      │                                  │
│                                      ▼                                  │
│                             ┌─────────────────┐                        │
│                             │  output_text    │                        │
│                             │  (trajectory)   │                        │
│                             └────────┬────────┘                        │
│                                      │                                  │
│                                      ▼                                  │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                      Scorer.async_score()                        │  │
│   │  ┌──────────────────────────────────────────────────────────┐   │  │
│   │  │  CriticScorer returns: (score, metadata)                  │   │  │
│   │  │                                                           │   │  │
│   │  │  metadata = {                                             │   │  │
│   │  │    "feedback": "Good but verbose",                        │   │  │
│   │  │    "actionable_guidance": "Reduce length by 30%",         │   │  │
│   │  │    "dimension_scores": {"accuracy": 0.9, "clarity": 0.6}  │   │  │
│   │  │  }                                                        │   │  │
│   │  └──────────────────────────────────────────────────────────┘   │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                      │                                  │
│                                      ▼                                  │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │              EvaluationBatch (with metadata)                     │  │
│   │  outputs: [output_text, ...]                                     │  │
│   │  scores: [score, ...]                                            │  │
│   │  trajectories: [trajectory, ...]                                 │  │
│   │  metadata: [metadata, ...] ◀─── NEW                              │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ADKAdapter.make_reflective_dataset()                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   For each example i:                                                   │
│     ┌─────────────────────────────────────────────────────────────┐    │
│     │  _build_reflection_example(                                  │    │
│     │    output=outputs[i],                                        │    │
│     │    score=scores[i],                                          │    │
│     │    trajectory=trajectories[i],                               │    │
│     │    metadata=metadata[i]  ◀─── NEW                            │    │
│     │  )                                                           │    │
│     └─────────────────────────────────────────────────────────────┘    │
│                                      │                                  │
│                                      ▼                                  │
│     ┌─────────────────────────────────────────────────────────────┐    │
│     │  Reflection Example:                                         │    │
│     │  {                                                           │    │
│     │    "Inputs": {"instruction": "..."},                         │    │
│     │    "Generated Outputs": "...",                               │    │
│     │    "Feedback": "score: 0.650, tool_calls: 2, tokens: 150    │    │
│     │                 Feedback: Good but verbose                   │    │
│     │                 Guidance: Reduce length by 30%               │    │
│     │                 Dimensions: accuracy=0.9, clarity=0.6"       │    │
│     │  }                                                           │    │
│     └─────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Reflection Agent                                │
│  (Receives enhanced feedback in execution_feedback)                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## State Transitions

This feature does not introduce new state transitions. EvaluationBatch is an immutable data container (frozen dataclass).

---

## Validation Rules

| Rule | Description | Enforcement |
|------|-------------|-------------|
| Index alignment | `len(metadata) == len(scores)` when metadata is not None | Runtime assertion in EvaluationBatch or ADKAdapter |
| Type compatibility | `metadata` must be `list[dict[str, Any]] \| None` | Type hints + mypy |
| Serializable metadata | All metadata values should be JSON-serializable | Caller responsibility (documented) |
| Backward compatibility | `metadata=None` is valid and equivalent to pre-feature behavior | Default value in dataclass |

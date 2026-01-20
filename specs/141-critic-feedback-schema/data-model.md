# Data Model: Critic Feedback Schema

**Feature**: 141-critic-feedback-schema
**Date**: 2026-01-20

## Entities

### CriticFeedback (Normalized)

The canonical feedback structure after normalization. Always contains required fields; optional fields included when provided.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `score` | `float` | ✅ Yes | Evaluation score (0.0-1.0) |
| `feedback_text` | `str` | ✅ Yes | Explanation of score (empty string if not provided) |
| `dimensions` | `dict[str, float]` | ❌ No | Per-dimension scores (e.g., `{"voice": 0.2, "urgency": 0.4}`) |
| `guidance` | `str` | ❌ No | Actionable improvement suggestions |
| `*` | `Any` | ❌ No | Custom fields pass through unchanged |

**Validation Rules**:
- `score`: Float, passed through as-is (validation handled by scorer)
- `feedback_text`: String, defaults to `""` if missing/None
- `dimensions`: Dict preserved if present and non-empty
- `guidance`: String preserved if present and non-empty
- Custom fields: All other keys pass through unchanged

### SimpleFeedback (Input)

Raw input format for basic scorers returning a string.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `score` | `float` | ✅ Yes | First tuple element |
| `feedback` | `str` | ✅ Yes | Second tuple element (string) |

**Example**: `(0.75, "Good clarity but needs more examples")`

**Normalization**: Wrapped into `{"score": 0.75, "feedback_text": "Good clarity but needs more examples"}`

### AdvancedFeedback (Input)

Raw input format for power users returning a dictionary.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `score` | `float` | ✅ Yes | First tuple element |
| `metadata` | `dict` | ✅ Yes | Second tuple element (dict) |

**Metadata Fields** (all optional):
| Key | Type | Maps To |
|-----|------|---------|
| `feedback_text` | `str` | `feedback_text` |
| `feedback` | `str` | `feedback_text` (fallback) |
| `dimension_scores` | `dict` | `dimensions` |
| `actionable_guidance` | `str` | `guidance` |
| `*` | `Any` | Passed through |

**Example**:
```python
(0.45, {
    "feedback_text": "Too clinical, needs personal voice",
    "dimension_scores": {"voice": 0.2, "urgency": 0.4},
    "actionable_guidance": "Add first-person 'I' statements",
    "custom_metric": 42
})
```

**Normalization**:
```python
{
    "score": 0.45,
    "feedback_text": "Too clinical, needs personal voice",
    "dimensions": {"voice": 0.2, "urgency": 0.4},
    "guidance": "Add first-person 'I' statements",
    "custom_metric": 42
}
```

### Trial (Existing - Unchanged)

Contains normalized feedback alongside trajectory.

| Field | Type | Description |
|-------|------|-------------|
| `feedback` | `CriticFeedback` | Normalized feedback object |
| `trajectory` | `dict` | Input/output pair with optional trace |

**Trajectory Structure**:
| Field | Type | Required |
|-------|------|----------|
| `input` | `str` | ✅ Yes |
| `output` | `str` | ✅ Yes |
| `trace` | `dict` | ❌ No |

## Field Mapping Table

| Input Key | Output Key | Notes |
|-----------|------------|-------|
| `feedback_text` | `feedback_text` | Primary |
| `feedback` | `feedback_text` | Fallback if `feedback_text` missing |
| `dimension_scores` | `dimensions` | Renamed for brevity |
| `actionable_guidance` | `guidance` | Renamed for brevity |
| (string input) | `feedback_text` | Simple format wrapped |
| `*` | `*` | All other keys preserved |

## State Transitions

N/A - Normalization is a stateless transformation.

## Constraints

1. **Backwards Compatibility**: Existing scorers returning `(float, dict)` must continue to work
2. **Required Fields**: Output always has `score` and `feedback_text`
3. **No Data Loss**: Custom fields in advanced format must pass through
4. **Type Coercion**: None/missing `feedback_text` → empty string

# Contract: normalize_feedback

**Feature**: 141-critic-feedback-schema
**Date**: 2026-01-20

## Function Signature

```python
def normalize_feedback(
    score: float,
    raw_feedback: str | dict[str, Any] | None,
) -> dict[str, Any]:
    """Normalize simple or advanced feedback to consistent trial format.

    Args:
        score: The evaluation score (0.0-1.0).
        raw_feedback: Either a string (simple format) or dict (advanced format).
            If None, feedback_text defaults to empty string.

    Returns:
        Normalized feedback dict with at minimum:
        - score: float
        - feedback_text: str

        Plus optional fields if provided in advanced format:
        - dimensions: dict[str, float]
        - guidance: str
        - Any custom fields from input dict

    Examples:
        >>> normalize_feedback(0.75, "Good but verbose")
        {"score": 0.75, "feedback_text": "Good but verbose"}

        >>> normalize_feedback(0.45, {
        ...     "feedback_text": "Too clinical",
        ...     "dimension_scores": {"voice": 0.2},
        ...     "actionable_guidance": "Add I statements"
        ... })
        {
            "score": 0.45,
            "feedback_text": "Too clinical",
            "dimensions": {"voice": 0.2},
            "guidance": "Add I statements"
        }
    """
```

## Input Contract

### Score Parameter

| Condition | Behavior |
|-----------|----------|
| Valid float (0.0-1.0) | Pass through to output |
| Float outside range | Pass through (validation elsewhere) |

### Raw Feedback Parameter

| Input Type | Behavior |
|------------|----------|
| `str` | Wrap: `{"feedback_text": input}` |
| `dict` | Extract and map fields |
| `None` | Use `{"feedback_text": ""}` |

### Dict Field Extraction

| Input Key | Extraction Rule | Output Key |
|-----------|-----------------|------------|
| `feedback_text` | Primary source | `feedback_text` |
| `feedback` | Fallback if `feedback_text` missing | `feedback_text` |
| `dimension_scores` | Preserve if non-empty dict | `dimensions` |
| `actionable_guidance` | Preserve if non-empty string | `guidance` |
| `score` (in dict) | **Ignored** - explicit parameter takes precedence | N/A |
| Other keys | Pass through unchanged | Same key |

## Output Contract

### Required Fields

| Field | Type | Guarantee |
|-------|------|-----------|
| `score` | `float` | Always present, from score parameter |
| `feedback_text` | `str` | Always present, empty string if not provided |

### Optional Fields

| Field | Type | Presence Condition |
|-------|------|-------------------|
| `dimensions` | `dict[str, float]` | Input has non-empty `dimension_scores` |
| `guidance` | `str` | Input has non-empty `actionable_guidance` |
| `*` | `Any` | Input dict contains other keys |

## Edge Cases

| Scenario | Input | Output |
|----------|-------|--------|
| Empty string feedback | `(0.5, "")` | `{"score": 0.5, "feedback_text": ""}` |
| None feedback | `(0.5, None)` | `{"score": 0.5, "feedback_text": ""}` |
| Dict with None feedback_text | `(0.5, {"feedback_text": None})` | `{"score": 0.5, "feedback_text": ""}` |
| Dict with score key | `(0.5, {"score": 0.9, "feedback": "x"})` | `{"score": 0.5, "feedback_text": "x"}` |
| Non-string feedback_text | `(0.5, {"feedback_text": 123})` | `{"score": 0.5, "feedback_text": "123"}` |
| Empty dimensions dict | `(0.5, {"dimension_scores": {}})` | `{"score": 0.5, "feedback_text": ""}` |
| Custom fields | `(0.5, {"feedback": "x", "foo": "bar"})` | `{"score": 0.5, "feedback_text": "x", "foo": "bar"}` |

## Test Scenarios

```python
# Simple format - string input
def test_normalize_string_feedback():
    result = normalize_feedback(0.75, "Good but verbose")
    assert result == {"score": 0.75, "feedback_text": "Good but verbose"}

# Simple format - empty string
def test_normalize_empty_string():
    result = normalize_feedback(0.0, "")
    assert result == {"score": 0.0, "feedback_text": ""}

# Simple format - None
def test_normalize_none_feedback():
    result = normalize_feedback(1.0, None)
    assert result == {"score": 1.0, "feedback_text": ""}

# Advanced format - full dict
def test_normalize_advanced_full():
    result = normalize_feedback(0.45, {
        "feedback_text": "Too clinical",
        "dimension_scores": {"voice": 0.2, "urgency": 0.4},
        "actionable_guidance": "Add I statements"
    })
    assert result == {
        "score": 0.45,
        "feedback_text": "Too clinical",
        "dimensions": {"voice": 0.2, "urgency": 0.4},
        "guidance": "Add I statements"
    }

# Advanced format - fallback to "feedback" key
def test_normalize_fallback_feedback_key():
    result = normalize_feedback(0.6, {"feedback": "Legacy format"})
    assert result == {"score": 0.6, "feedback_text": "Legacy format"}

# Advanced format - custom fields preserved
def test_normalize_custom_fields():
    result = normalize_feedback(0.7, {
        "feedback_text": "OK",
        "custom_metric": 42,
        "user_data": {"id": 123}
    })
    assert result == {
        "score": 0.7,
        "feedback_text": "OK",
        "custom_metric": 42,
        "user_data": {"id": 123}
    }

# Edge case - score in dict ignored
def test_normalize_dict_score_ignored():
    result = normalize_feedback(0.5, {"score": 0.9, "feedback": "X"})
    assert result["score"] == 0.5  # Explicit param wins

# Edge case - non-string feedback_text
def test_normalize_nonstring_feedback():
    result = normalize_feedback(0.5, {"feedback_text": 123})
    assert result["feedback_text"] == "123"
```

## Integration Points

- **Caller**: `TrialBuilder.build_feedback()`
- **Consumer**: `TrialBuilder.build_trial()` → `ADKAdapter.make_reflective_dataset()` → Reflection agent

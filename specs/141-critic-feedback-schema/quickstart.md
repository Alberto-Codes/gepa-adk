# Quickstart: Critic Feedback Schema

**Feature**: 141-critic-feedback-schema
**Date**: 2026-01-20

## Overview

This feature standardizes how critic scorers return feedback, supporting both simple (string) and advanced (dict) formats with automatic normalization.

## Simple Format (Recommended for Most Users)

Return a tuple of score and feedback string:

```python
from gepa_adk.adapters import CriticScorer

class MySimpleCritic(CriticScorer):
    async def async_score(self, input_text: str, output: str, expected: str | None = None):
        # Evaluate the output...
        score = 0.75
        feedback = "Good clarity but needs more specific examples"

        return (score, {"feedback": feedback})
```

The system normalizes this to:
```python
{
    "score": 0.75,
    "feedback_text": "Good clarity but needs more specific examples"
}
```

## Advanced Format (Power Users)

Return a tuple of score and detailed metadata dict:

```python
class MyAdvancedCritic(CriticScorer):
    async def async_score(self, input_text: str, output: str, expected: str | None = None):
        score = 0.45
        metadata = {
            "feedback_text": "Too clinical, needs personal voice",
            "dimension_scores": {
                "voice": 0.2,
                "urgency": 0.4,
                "accuracy": 0.8
            },
            "actionable_guidance": "Add first-person 'I' statements",
            "custom_metric": 42  # Your own fields pass through
        }

        return (score, metadata)
```

The system normalizes this to:
```python
{
    "score": 0.45,
    "feedback_text": "Too clinical, needs personal voice",
    "dimensions": {"voice": 0.2, "urgency": 0.4, "accuracy": 0.8},
    "guidance": "Add first-person 'I' statements",
    "custom_metric": 42
}
```

## Field Mapping Reference

| Your Input Key | Normalized Output Key |
|----------------|----------------------|
| `feedback_text` | `feedback_text` |
| `feedback` (fallback) | `feedback_text` |
| `dimension_scores` | `dimensions` |
| `actionable_guidance` | `guidance` |
| Any other key | Passed through unchanged |

## What the Reflector Receives

Regardless of which format you use, the reflection agent always sees consistent trial records:

```python
{
    "feedback": {
        "score": 0.45,
        "feedback_text": "Too clinical, needs personal voice",
        "dimensions": {"voice": 0.2, "urgency": 0.4},  # if provided
        "guidance": "Add first-person statements"       # if provided
    },
    "trajectory": {
        "input": "What does exhaustion feel like?",
        "output": "Exhaustion is a state of..."
    }
}
```

## Required Output Structure

Your scorer must always provide:
- `score`: float (0.0-1.0)
- `feedback` or `feedback_text`: string explaining the score

Optional fields:
- `dimension_scores` / `dimensions`: dict of per-aspect scores
- `actionable_guidance` / `guidance`: string with improvement suggestions
- Any custom fields you need

## Testing Your Scorer

```python
import pytest
from your_module import MySimpleCritic

@pytest.mark.asyncio
async def test_my_critic():
    critic = MySimpleCritic(model="gpt-4o-mini")

    score, metadata = await critic.async_score(
        input_text="Test prompt",
        output="Test response",
        expected=None
    )

    assert 0.0 <= score <= 1.0
    assert "feedback" in metadata or "feedback_text" in metadata
```

## Migration Notes

If you have existing scorers:

1. **No breaking changes** - Existing `(score, {"feedback": "..."})` format continues to work
2. **Optional upgrade** - Use new field names (`feedback_text`, `dimensions`, `guidance`) for clarity
3. **Custom fields safe** - Any extra keys in your metadata dict are preserved

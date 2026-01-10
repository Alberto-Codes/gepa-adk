# Quickstart: Scorer Protocol

**Feature**: 005-scorer-protocol
**Date**: 2026-01-10

## Overview

The Scorer protocol allows you to implement custom scoring logic for evaluating agent outputs. This guide shows how to implement and use scorers with gepa-adk.

## Basic Implementation

### Step 1: Implement the Protocol

Create a class with both `score()` and `async_score()` methods:

```python
from typing import Any

class MyScorer:
    """Simple scorer that checks for keyword presence."""

    def __init__(self, required_keyword: str):
        self.required_keyword = required_keyword

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        has_keyword = self.required_keyword.lower() in output.lower()
        return (
            1.0 if has_keyword else 0.0,
            {
                "keyword_found": has_keyword,
                "keyword": self.required_keyword,
            },
        )

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        # For simple scorers, delegate to sync method
        return self.score(input_text, output, expected)
```

### Step 2: Verify Protocol Compliance

```python
from gepa_adk.ports.scorer import Scorer

scorer = MyScorer("hello")
assert isinstance(scorer, Scorer)  # Passes if protocol is satisfied
```

### Step 3: Use the Scorer

```python
# Synchronous usage
score, meta = scorer.score(
    input_text="Say hello to the user",
    output="Hello! How can I help you today?",
)
print(f"Score: {score}, Found: {meta['keyword_found']}")
# Output: Score: 1.0, Found: True

# Asynchronous usage
import asyncio

async def main():
    score, meta = await scorer.async_score(
        input_text="Say hello",
        output="Hi there!",
    )
    print(f"Score: {score}")

asyncio.run(main())
```

## Common Patterns

### Exact Match Scorer

```python
class ExactMatchScorer:
    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        if expected is None:
            return 0.0, {"error": "Expected value required for exact match"}

        is_match = output.strip() == expected.strip()
        return (
            1.0 if is_match else 0.0,
            {"exact_match": is_match, "expected": expected},
        )

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        return self.score(input_text, output, expected)
```

### Contains Answer Scorer

```python
class ContainsAnswerScorer:
    """Check if expected answer appears in output (case-insensitive)."""

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        if expected is None:
            return 0.5, {"note": "No expected value, using neutral score"}

        contains = expected.lower() in output.lower()
        return (
            1.0 if contains else 0.0,
            {
                "contains_answer": contains,
                "feedback": f"Output {'contains' if contains else 'missing'} expected: '{expected}'",
            },
        )

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        return self.score(input_text, output, expected)
```

### Async LLM-Based Scorer

```python
import asyncio

class LLMScorer:
    """Score using an external LLM API (async required)."""

    def __init__(self, llm_client):
        self.llm = llm_client

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        # For LLM-based scoring, run async version synchronously
        return asyncio.run(self.async_score(input_text, output, expected))

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        prompt = f"""Rate this output from 0 to 1:
        Input: {input_text}
        Output: {output}
        {"Expected: " + expected if expected else ""}
        Respond with JSON: {{"score": <float>, "feedback": "<string>"}}"""

        response = await self.llm.complete(prompt)
        result = json.loads(response)

        return result["score"], {"feedback": result["feedback"]}
```

## Testing Your Scorer

### Unit Test Example

```python
import pytest

def test_my_scorer_finds_keyword():
    scorer = MyScorer("hello")
    score, meta = scorer.score("greet", "Hello world!", None)

    assert score == 1.0
    assert meta["keyword_found"] is True


def test_my_scorer_missing_keyword():
    scorer = MyScorer("hello")
    score, meta = scorer.score("greet", "Goodbye!", None)

    assert score == 0.0
    assert meta["keyword_found"] is False


@pytest.mark.asyncio
async def test_async_score_matches_sync():
    scorer = MyScorer("test")
    sync_result = scorer.score("input", "test output", None)
    async_result = await scorer.async_score("input", "test output", None)

    assert sync_result == async_result
```

### Contract Test Example

```python
from gepa_adk.ports.scorer import Scorer


def test_implements_scorer_protocol():
    """Verify MyScorer implements the Scorer protocol."""
    scorer = MyScorer("keyword")
    assert isinstance(scorer, Scorer)


def test_score_returns_correct_types():
    """Verify score() returns (float, dict)."""
    scorer = MyScorer("keyword")
    result = scorer.score("input", "output", None)

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], float)
    assert isinstance(result[1], dict)
```

## Integration with Evolution Engine

Once you have a Scorer, use it with the evolution engine:

```python
from gepa_adk import evolve

# Your custom scorer
scorer = ContainsAnswerScorer()

# Evolve an agent using your scorer
result = await evolve(
    agent=my_agent,
    trainset=examples,
    scorer=scorer,  # Your custom scorer
    max_iterations=50,
)

print(f"Improved from {result.original_score:.2f} to {result.final_score:.2f}")
```

## Best Practices

1. **Normalize scores**: Keep scores in 0.0-1.0 range for consistency
2. **Include feedback**: Add `feedback` key to metadata for reflection agent
3. **Handle None expected**: Return sensible defaults when expected is None
4. **Keep metadata serializable**: Use JSON-compatible types in dict
5. **Make async efficient**: For I/O-bound work, use true async; for CPU-bound, delegate to sync

## Troubleshooting

### "Not a valid Scorer" Error
Ensure both `score()` and `async_score()` methods exist with correct signatures.

### Score Range Issues
The protocol doesn't enforce 0.0-1.0 range, but the evolution engine expects it. Normalize your scores.

### Metadata Serialization Errors
If metadata contains non-serializable objects, wrap them in strings or remove them.

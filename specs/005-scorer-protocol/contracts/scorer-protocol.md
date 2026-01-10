# API Contract: Scorer Protocol

**Feature**: 005-scorer-protocol
**Date**: 2026-01-10
**Type**: Python Protocol (typing.Protocol)

## Overview

The Scorer protocol defines a contract for implementing custom scoring logic that evaluates agent outputs against expected results.

## Protocol Definition

```python
from typing import Any, Protocol, runtime_checkable

@runtime_checkable
class Scorer(Protocol):
    """Protocol for scoring agent outputs.

    Implementations provide scoring logic that evaluates how well
    an agent's output matches expected results or quality criteria.

    Both synchronous and asynchronous methods are defined. Implementations
    should provide both, though callers may use only one based on context.

    Attributes:
        None required by protocol.

    Examples:
        Implement a simple exact-match scorer:

        ```python
        class ExactMatchScorer:
            def score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict]:
                if expected is None:
                    return 0.0, {"error": "Expected value required"}
                match = output.strip() == expected.strip()
                return (1.0 if match else 0.0), {"exact_match": match}

            async def async_score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict]:
                return self.score(input_text, output, expected)
        ```

    Note:
        Score values should be normalized between 0.0 and 1.0 by convention,
        with higher values indicating better performance. The protocol does
        not enforce this range.
    """

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score an agent output synchronously.

        Args:
            input_text: The input provided to the agent.
            output: The agent's generated output to score.
            expected: Optional expected/reference output for comparison.
                Pass None for open-ended evaluation without expected output.

        Returns:
            A tuple of (score, metadata) where:
            - score: Float value, conventionally 0.0-1.0, higher is better
            - metadata: Dict with arbitrary scoring details (e.g., feedback,
              dimension_scores, reasoning). Should be JSON-serializable.

        Examples:
            Basic usage:

            ```python
            score, meta = scorer.score("What is 2+2?", "4", "4")
            assert score == 1.0
            assert meta.get("exact_match") is True
            ```

        Note:
            This method blocks until scoring completes. Use async_score()
            for I/O-bound operations like LLM calls.
        """
        ...

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score an agent output asynchronously.

        Args:
            input_text: The input provided to the agent.
            output: The agent's generated output to score.
            expected: Optional expected/reference output for comparison.
                Pass None for open-ended evaluation without expected output.

        Returns:
            A tuple of (score, metadata) where:
            - score: Float value, conventionally 0.0-1.0, higher is better
            - metadata: Dict with arbitrary scoring details (e.g., feedback,
              dimension_scores, reasoning). Should be JSON-serializable.

        Examples:
            Async usage:

            ```python
            score, meta = await scorer.async_score("Explain gravity", response)
            print(f"Quality: {score:.2f} - {meta.get('feedback')}")
            ```

        Note:
            Prefer this method for I/O-bound scoring operations such as
            LLM-based evaluation or external API calls.
        """
        ...
```

## Parameters

### score() / async_score()

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `input_text` | `str` | Yes | - | Original input given to the agent |
| `output` | `str` | Yes | - | Agent's generated output to evaluate |
| `expected` | `str \| None` | No | `None` | Expected output for comparison |

## Return Value

| Field | Type | Description |
|-------|------|-------------|
| `score` | `float` | Numeric score (convention: 0.0-1.0, higher is better) |
| `metadata` | `dict[str, Any]` | Arbitrary key-value pairs with scoring details |

### Common Metadata Keys

| Key | Type | Description |
|-----|------|-------------|
| `feedback` | `str` | Human-readable feedback for reflection agent |
| `dimension_scores` | `dict[str, float]` | Scores per quality dimension |
| `reasoning` | `str` | Explanation of how score was derived |
| `error` | `str` | Error message if scoring failed gracefully |
| `exact_match` | `bool` | Whether output exactly matched expected |

## Behavioral Contracts

### BC-001: Identical Return Format
Both `score()` and `async_score()` MUST return the same tuple structure `(float, dict)`.

### BC-002: No Side Effects Required
Protocol methods SHOULD NOT produce side effects. Scoring should be idempotent.

### BC-003: Exception Handling
- Implementations MAY raise exceptions for unrecoverable errors
- Implementations SHOULD return graceful failure scores (e.g., 0.0) with error metadata for recoverable issues
- Callers MUST handle potential exceptions

### BC-004: Thread/Async Safety
- `score()`: No thread safety guarantees required by protocol
- `async_score()`: Must be awaitable and non-blocking

### BC-005: None Expected Handling
When `expected=None`:
- Scorer SHOULD still return a valid score based on other criteria
- Scorer MAY return 0.0 with error metadata if expected is required

## Implementation Requirements

### Required for Protocol Compliance
1. Define `score()` with exact signature
2. Define `async_score()` with exact signature
3. Return `tuple[float, dict]` from both methods

### Recommended for Quality
1. Normalize scores to 0.0-1.0 range
2. Include `feedback` in metadata for reflection
3. Make metadata JSON-serializable
4. Handle None expected gracefully

## Verification

Protocol compliance can be verified at runtime:

```python
from gepa_adk.ports.scorer import Scorer

def verify_scorer(scorer: object) -> bool:
    """Verify an object implements the Scorer protocol."""
    return isinstance(scorer, Scorer)
```

## Usage Examples

### In AsyncGEPAAdapter

```python
class ADKAdapter:
    def __init__(self, scorer: Scorer):
        self.scorer = scorer

    async def evaluate(self, batch, candidate, capture_traces=False):
        results = []
        for example in batch:
            output = await self._execute(example, candidate)
            score, metadata = await self.scorer.async_score(
                input_text=example["input"],
                output=output,
                expected=example.get("expected"),
            )
            results.append((output, score, metadata))
        return self._build_batch(results)
```

### Direct Usage

```python
from gepa_adk.ports.scorer import Scorer

async def evaluate_output(scorer: Scorer, input_text: str, output: str) -> float:
    score, meta = await scorer.async_score(input_text, output)
    if "error" in meta:
        logger.warning(f"Scoring issue: {meta['error']}")
    return score
```

## Related Contracts

- **AsyncGEPAAdapter**: May use Scorer internally for evaluation
- **EvaluationBatch**: Contains scores produced by Scorer implementations

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-10 | Initial protocol definition |

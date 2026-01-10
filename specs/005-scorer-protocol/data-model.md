# Data Model: Scorer Protocol

**Feature**: 005-scorer-protocol
**Date**: 2026-01-10

## Overview

The Scorer protocol defines a minimal contract for scoring agent outputs. It follows the hexagonal architecture pattern, residing in the `ports/` layer with no external dependencies.

## Entities

### Scorer (Protocol)

The core protocol defining the scoring contract.

| Attribute | Type | Description |
|-----------|------|-------------|
| `score` | method | Synchronous scoring method |
| `async_score` | method | Asynchronous scoring method |

**Method Signatures**:

```
score(input_text: str, output: str, expected: str | None = None) -> tuple[float, dict]
async_score(input_text: str, output: str, expected: str | None = None) -> tuple[float, dict]
```

**Constraints**:
- Both methods return identical tuple structure
- Protocol is `@runtime_checkable` for isinstance() validation
- No state requirements imposed by the protocol

### Score Result (Tuple)

The return value from scoring methods. Not a formal entity but documented for clarity.

| Position | Type | Description | Constraints |
|----------|------|-------------|-------------|
| 0 | `float` | Score value | Convention: 0.0-1.0, higher is better |
| 1 | `dict` | Metadata | Any key-value pairs, should be JSON-serializable |

**Common Metadata Keys** (by convention):
- `feedback`: str - Human-readable feedback for reflection
- `dimension_scores`: dict[str, float] - Component-level scores
- `error`: str - Error message if scoring failed gracefully
- `reasoning`: str - Explanation of score rationale

## Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                     ports/ layer                             │
│  ┌─────────────┐                    ┌─────────────────────┐ │
│  │   Scorer    │                    │  AsyncGEPAAdapter   │ │
│  │  (protocol) │◄───uses internally─│    (protocol)       │ │
│  └─────────────┘                    └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                      │
                      │ implements
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   adapters/ layer                            │
│  ┌─────────────────────┐     ┌────────────────────────────┐ │
│  │    CriticScorer     │     │   ExactMatchScorer         │ │
│  │ (uses ADK agents)   │     │ (simple comparison)        │ │
│  └─────────────────────┘     └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Type Aliases

From `domain/types.py`:

| Alias | Base Type | Usage |
|-------|-----------|-------|
| `Score` | `float` | Normalized score values |

## Validation Rules

### Score Value
- **Convention**: Should be normalized between 0.0 and 1.0
- **Enforcement**: Not enforced at protocol level
- **Boundary behavior**: 0.0 and 1.0 are valid scores

### Metadata Dict
- **Required**: Must be a dict (not None)
- **Convention**: Should be JSON-serializable for logging/persistence
- **Empty allowed**: `{}` is valid

### Expected Parameter
- **Optional**: Defaults to `None`
- **Use case**: Omit for open-ended tasks without expected outputs

## State Transitions

The Scorer protocol is stateless by design. Implementations may maintain state but the protocol does not require or prescribe it.

## Examples

### Minimal Scorer Implementation
```python
class FixedScorer:
    def score(self, input_text: str, output: str, expected: str | None = None) -> tuple[float, dict]:
        return 0.5, {"note": "Fixed score for testing"}

    async def async_score(self, input_text: str, output: str, expected: str | None = None) -> tuple[float, dict]:
        return self.score(input_text, output, expected)
```

### Exact Match Scorer
```python
class ExactMatchScorer:
    def score(self, input_text: str, output: str, expected: str | None = None) -> tuple[float, dict]:
        if expected is None:
            return 0.0, {"error": "Expected value required for exact match"}

        is_match = output.strip() == expected.strip()
        return (1.0 if is_match else 0.0), {"exact_match": is_match}

    async def async_score(self, input_text: str, output: str, expected: str | None = None) -> tuple[float, dict]:
        return self.score(input_text, output, expected)
```

## Integration with Existing Models

The Scorer protocol complements existing domain models:

| Model | Relationship |
|-------|--------------|
| `EvaluationBatch` | Contains `scores: list[Score]` populated by Scorer |
| `EvolutionConfig` | May configure which Scorer to use |
| `IterationRecord` | Records `score: float` from Scorer output |
| `EvolutionResult` | Contains `original_score` and `final_score` from Scorer |

## Notes

- Protocol location: `src/gepa_adk/ports/scorer.py`
- No imports from `domain/` (pure protocol)
- No imports from `adapters/` (dependency inversion)
- Test location: `tests/contracts/test_scorer_protocol.py`

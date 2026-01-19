# Contract: EvolutionResult

**Feature**: 126-evolved-components
**Date**: 2026-01-19

## Overview

This contract defines the expected behavior of the modified `EvolutionResult` dataclass with the new `evolved_components` field.

## Type Definition

```python
from dataclasses import dataclass

@dataclass(slots=True, frozen=True, kw_only=True)
class EvolutionResult:
    """Outcome of a completed evolution run."""

    # Required fields
    original_score: float
    final_score: float
    evolved_components: dict[str, str]  # NEW: replaces evolved_component_text
    iteration_history: list[IterationRecord]
    total_iterations: int

    # Optional fields
    valset_score: float | None = None
    trainset_score: float | None = None
    objective_scores: list[dict[str, float]] | None = None

    @property
    def improvement(self) -> float:
        """Calculate score improvement from original to final."""
        return self.final_score - self.original_score

    @property
    def improved(self) -> bool:
        """Check if final score is better than original."""
        return self.final_score > self.original_score
```

## Contract Tests

### CT-001: Default Evolution Returns Instruction Component

**Precondition**: Evolution completes with default configuration (instruction-only)

**Expected**:
- `result.evolved_components` contains key `"instruction"`
- `result.evolved_components["instruction"]` is a non-empty string
- `len(result.evolved_components) >= 1`

```python
def test_default_evolution_returns_instruction_component():
    result = await evolve(agent, trainset)

    assert "instruction" in result.evolved_components
    assert isinstance(result.evolved_components["instruction"], str)
    assert len(result.evolved_components["instruction"]) > 0
```

### CT-002: Multi-Component Evolution Returns All Components

**Precondition**: Evolution completes with output_schema component enabled

**Expected**:
- `result.evolved_components` contains keys `"instruction"` and `"output_schema"`
- Both values are non-empty strings

```python
def test_multi_component_evolution_returns_all_components():
    result = await evolve(agent, trainset, component_selector=round_robin_selector)

    assert "instruction" in result.evolved_components
    assert "output_schema" in result.evolved_components
    assert all(isinstance(v, str) for v in result.evolved_components.values())
```

### CT-003: Evolved Components Match Best Candidate

**Precondition**: Evolution completes

**Expected**:
- `result.evolved_components` matches `best_candidate.components`

```python
def test_evolved_components_match_best_candidate():
    # Internal contract - verified via engine state
    assert result.evolved_components == state.best_candidate.components
```

### CT-004: Iteration Records Track Evolved Component

**Precondition**: Evolution completes with at least one iteration

**Expected**:
- Each `IterationRecord` has `evolved_component` field set
- `evolved_component` value is a valid component key

```python
def test_iteration_records_track_evolved_component():
    result = await evolve(agent, trainset)

    for record in result.iteration_history:
        assert hasattr(record, "evolved_component")
        assert record.evolved_component in ["instruction", "output_schema"]
        assert isinstance(record.component_text, str)
```

### CT-005: Frozen Dataclass Immutability

**Precondition**: `EvolutionResult` instance created

**Expected**:
- Attempting to modify `evolved_components` raises `FrozenInstanceError`

```python
def test_evolution_result_is_frozen():
    result = EvolutionResult(
        original_score=0.5,
        final_score=0.8,
        evolved_components={"instruction": "test"},
        iteration_history=[],
        total_iterations=1,
    )

    with pytest.raises(FrozenInstanceError):
        result.evolved_components = {}
```

## Error Conditions

| Condition | Expected Behavior |
|-----------|-------------------|
| Missing component key access | Raises `KeyError` (standard dict behavior) |
| Empty evolved_components | Should never occur; engine always populates |
| Invalid component value type | Type checker catches at development time |

## Backward Compatibility

This is a **breaking change**. The following migration is required:

```python
# Before
result.evolved_component_text

# After
result.evolved_components["instruction"]
```

No backward compatibility wrapper is provided per specification requirements.

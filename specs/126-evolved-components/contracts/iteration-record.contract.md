# Contract: IterationRecord

**Feature**: 126-evolved-components
**Date**: 2026-01-19

## Overview

This contract defines the expected behavior of the modified `IterationRecord` dataclass with the new `evolved_component` field.

## Type Definition

```python
from dataclasses import dataclass

@dataclass(slots=True, frozen=True, kw_only=True)
class IterationRecord:
    """Captures metrics for a single evolution iteration."""

    iteration_number: int
    score: float
    component_text: str
    evolved_component: str  # NEW: which component was evolved
    accepted: bool
    objective_scores: list[dict[str, float]] | None = None
```

## Contract Tests

### CT-101: Evolved Component Field Required

**Precondition**: Creating an `IterationRecord`

**Expected**:
- `evolved_component` is a required field
- Cannot create record without specifying `evolved_component`

```python
def test_evolved_component_required():
    # Valid creation
    record = IterationRecord(
        iteration_number=1,
        score=0.85,
        component_text="Be helpful",
        evolved_component="instruction",
        accepted=True,
    )
    assert record.evolved_component == "instruction"

    # Invalid - missing evolved_component
    with pytest.raises(TypeError):
        IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            accepted=True,
        )
```

### CT-102: Component Text Matches Evolved Component Value

**Precondition**: Record created during evolution

**Expected**:
- `component_text` contains the text value of the component named by `evolved_component`

```python
def test_component_text_matches_evolved_component():
    record = IterationRecord(
        iteration_number=1,
        score=0.85,
        component_text="Be helpful and concise",
        evolved_component="instruction",
        accepted=True,
    )

    # The component_text should be the value for the evolved_component key
    assert record.component_text == "Be helpful and concise"
    assert record.evolved_component == "instruction"
```

### CT-103: Valid Component Names

**Precondition**: Record created with component name

**Expected**:
- `evolved_component` accepts standard component keys
- No validation at dataclass level (validation at engine level)

```python
def test_valid_component_names():
    # Standard component names
    for component in ["instruction", "output_schema"]:
        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="test",
            evolved_component=component,
            accepted=True,
        )
        assert record.evolved_component == component
```

### CT-104: Frozen Dataclass Immutability

**Precondition**: `IterationRecord` instance created

**Expected**:
- Attempting to modify any field raises `FrozenInstanceError`

```python
def test_iteration_record_is_frozen():
    record = IterationRecord(
        iteration_number=1,
        score=0.85,
        component_text="test",
        evolved_component="instruction",
        accepted=True,
    )

    with pytest.raises(FrozenInstanceError):
        record.evolved_component = "output_schema"
```

### CT-105: Round-Robin Evolution Tracking

**Precondition**: Evolution alternates between components

**Expected**:
- Consecutive records may have different `evolved_component` values
- History accurately reflects which component was evolved in each iteration

```python
def test_round_robin_evolution_tracking():
    records = [
        IterationRecord(
            iteration_number=1,
            score=0.80,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
        ),
        IterationRecord(
            iteration_number=2,
            score=0.82,
            component_text='{"type": "object"}',
            evolved_component="output_schema",
            accepted=True,
        ),
        IterationRecord(
            iteration_number=3,
            score=0.85,
            component_text="Be helpful and concise",
            evolved_component="instruction",
            accepted=True,
        ),
    ]

    # Verify alternating pattern is tracked
    assert records[0].evolved_component == "instruction"
    assert records[1].evolved_component == "output_schema"
    assert records[2].evolved_component == "instruction"
```

## Error Conditions

| Condition | Expected Behavior |
|-----------|-------------------|
| Missing evolved_component | `TypeError` at construction |
| Empty evolved_component | Allowed (no validation at dataclass level) |
| Invalid component name | No dataclass validation; engine should validate |

## Backward Compatibility

This is a **breaking change** for any code that constructs `IterationRecord` directly:

```python
# Before
record = IterationRecord(
    iteration_number=1,
    score=0.85,
    component_text="test",
    accepted=True,
)

# After
record = IterationRecord(
    iteration_number=1,
    score=0.85,
    component_text="test",
    evolved_component="instruction",  # NEW: required
    accepted=True,
)
```

Most users don't construct `IterationRecord` directly (it's created by the engine), but tests and internal code must be updated.

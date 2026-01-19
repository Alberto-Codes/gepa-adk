# Data Model: Evolved Components Dictionary

**Feature**: 126-evolved-components
**Date**: 2026-01-19
**Status**: Draft

## Entities

### EvolutionResult (Modified)

**Location**: `src/gepa_adk/domain/models.py`

**Purpose**: Outcome of a completed evolution run. Contains the final results after evolution completes, including all evolved component values, performance metrics, and full history.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| original_score | float | Yes | Starting performance score (baseline) |
| final_score | float | Yes | Ending performance score (best achieved) |
| **evolved_components** | dict[str, str] | Yes | **NEW**: Dictionary mapping component names to their final evolved text values |
| iteration_history | list[IterationRecord] | Yes | Chronological list of iteration records |
| total_iterations | int | Yes | Number of iterations performed |
| valset_score | float \| None | No | Score on validation set used for acceptance decisions |
| trainset_score | float \| None | No | Score on trainset used for reflection diagnostics |
| objective_scores | list[dict[str, float]] \| None | No | Per-example multi-objective scores from best candidate |

**Removed Field**:
- `evolved_component_text: str` - Replaced by `evolved_components["instruction"]` access

**Validation Rules**:
- `evolved_components` must contain at least one key
- For default evolution, must contain "instruction" key
- All values must be non-empty strings

**State Transitions**: N/A (immutable frozen dataclass)

---

### IterationRecord (Modified)

**Location**: `src/gepa_adk/domain/models.py`

**Purpose**: Captures metrics for a single evolution iteration. Immutable record of what happened during one iteration of the evolution process.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| iteration_number | int | Yes | 1-indexed iteration number |
| score | float | Yes | Score achieved in this iteration |
| component_text | str | Yes | The component text that was evaluated |
| **evolved_component** | str | Yes | **NEW**: Which component was evolved (e.g., "instruction", "output_schema") |
| accepted | bool | Yes | Whether this proposal was accepted as the new best |
| objective_scores | list[dict[str, float]] \| None | No | Per-example multi-objective scores |

**Validation Rules**:
- `evolved_component` must be a valid component key
- `component_text` corresponds to the value of `evolved_component`

**State Transitions**: N/A (immutable frozen dataclass)

---

### Candidate (Unchanged - Reference)

**Location**: `src/gepa_adk/domain/models.py`

**Purpose**: Represents an instruction candidate being evolved. Source of truth for component values.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| components | dict[str, str] | Yes | Component name to text value mapping |
| generation | int | No | Generation number in evolution lineage |
| parent_id | str \| None | No | ID of parent candidate (legacy) |
| parent_ids | list[int] \| None | No | Multi-parent indices for merge operations |
| metadata | dict[str, Any] | No | Extensible metadata for tracking |

**Common component keys**:
- `"instruction"`: Main agent prompt being evolved
- `"output_schema"`: Optional schema component for output validation

---

## Relationships

```
┌─────────────────────────────────────────────────────────┐
│                    EvolutionResult                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │ evolved_components: dict[str, str]               │    │
│  │   "instruction" → "Be helpful and concise"      │    │
│  │   "output_schema" → "{...schema...}"            │    │
│  └─────────────────────────────────────────────────┘    │
│                          │                               │
│                          │ populated from                │
│                          ▼                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │ best_candidate.components (Candidate)            │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ iteration_history: list[IterationRecord]         │    │
│  │   ┌─────────────────────────────────────────┐   │    │
│  │   │ IterationRecord #1                       │   │    │
│  │   │   evolved_component: "instruction"       │   │    │
│  │   │   component_text: "Be helpful"           │   │    │
│  │   └─────────────────────────────────────────┘   │    │
│  │   ┌─────────────────────────────────────────┐   │    │
│  │   │ IterationRecord #2                       │   │    │
│  │   │   evolved_component: "output_schema"     │   │    │
│  │   │   component_text: "{...}"                │   │    │
│  │   └─────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Migration Guide

### Before (Current API)

```python
result = await evolve(agent, trainset)

# Accessing evolved instruction
instruction = result.evolved_component_text

# Iteration history
for record in result.iteration_history:
    print(f"Iteration {record.iteration_number}: {record.component_text}")
```

### After (New API)

```python
result = await evolve(agent, trainset)

# Accessing evolved instruction (explicit key)
instruction = result.evolved_components["instruction"]

# Accessing evolved schema (if evolved)
schema = result.evolved_components.get("output_schema")

# Iteration history (now includes which component was evolved)
for record in result.iteration_history:
    print(f"Iteration {record.iteration_number}: "
          f"evolved {record.evolved_component} = {record.component_text}")
```

### Key Differences

| Aspect | Before | After |
|--------|--------|-------|
| Access pattern | `.evolved_component_text` | `.evolved_components["instruction"]` |
| Multi-component | Not supported | Dictionary with all components |
| Iteration tracking | Implicit (always instruction) | Explicit `evolved_component` field |
| Type | `str` | `dict[str, str]` |

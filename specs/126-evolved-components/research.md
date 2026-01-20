# Research: Evolved Components Dictionary

**Feature**: 126-evolved-components
**Date**: 2026-01-19
**Status**: Complete

## Research Tasks

### 1. Current Implementation Analysis

**Question**: How is `evolved_component_text` currently used and what is the migration impact?

**Findings**:

The current implementation extracts only the "instruction" component at `async_engine.py:721`:

```python
evolved_component_text=self._state.best_candidate.components["instruction"]
```

**Files referencing `evolved_component_text`** (30 total):
- **Source code**: `api.py`, `async_engine.py`, `domain/models.py`
- **Tests**: 8 test files across contracts/, unit/, integration/
- **Examples**: 4 example files
- **Documentation**: 6 doc files including guides and glossary

**Decision**: Replace `evolved_component_text: str` with `evolved_components: dict[str, str]`
**Rationale**: The `Candidate.components` dictionary already stores all component values. Exposing the full dictionary provides flexibility for multi-component evolution without losing the simple single-component use case.
**Alternatives Rejected**:
- Adding a second field alongside `evolved_component_text`: Increases API surface, encourages confusion
- Keeping both with deprecation warning: Prolongs migration pain, complicates maintenance

---

### 2. IterationRecord Enhancement

**Question**: How should `IterationRecord` track which component was evolved?

**Findings**:

Current `IterationRecord` structure (models.py:218-262):
```python
@dataclass(slots=True, frozen=True, kw_only=True)
class IterationRecord:
    iteration_number: int
    score: float
    component_text: str      # Currently stores the instruction text
    accepted: bool
    objective_scores: list[dict[str, float]] | None = None
```

The `_record_iteration` method (async_engine.py:541-569) currently extracts only "instruction":
```python
self._record_iteration(
    score=proposal_score,
    instruction=proposal.components["instruction"],  # Hardcoded
    accepted=accepted,
    objective_scores=scoring_batch.objective_scores,
)
```

**Decision**: Add `evolved_component: str` field to `IterationRecord` to track which component was evolved
**Rationale**: Round-robin evolution strategies need to know which component changed in each iteration. The field name should match the key used in the components dictionary.
**Alternatives Rejected**:
- Replacing `component_text` with a dict: Breaks existing consumers expecting a string
- Inferring from diff: Computationally expensive and error-prone

**New IterationRecord structure**:
```python
@dataclass(slots=True, frozen=True, kw_only=True)
class IterationRecord:
    iteration_number: int
    score: float
    component_text: str              # The evolved component's text value
    evolved_component: str           # NEW: Which component was evolved (e.g., "instruction")
    accepted: bool
    objective_scores: list[dict[str, float]] | None = None
```

---

### 3. Migration Pattern for Examples and Tests

**Question**: What is the cleanest migration pattern for existing code?

**Findings**:

**Before**:
```python
result = await evolve(agent, trainset)
print(result.evolved_component_text)
```

**After**:
```python
result = await evolve(agent, trainset)
print(result.evolved_components["instruction"])
```

**Migration checklist**:
1. Replace all `.evolved_component_text` with `.evolved_components["instruction"]`
2. Update docstrings and type hints
3. Update test assertions to use dictionary access
4. Update examples to demonstrate both single and multi-component access

**Decision**: Direct replacement with dictionary access
**Rationale**: The `["instruction"]` key access is explicit about which component is being accessed, improving readability for future multi-component scenarios.
**Alternatives Rejected**:
- Adding a property `evolved_instruction` as shorthand: Adds API surface, encourages tight coupling to instruction-only evolution

---

### 4. Default Behavior Preservation

**Question**: How to ensure default instruction-only evolution works without extra configuration?

**Findings**:

The current flow already handles this correctly:
1. `api.py:553` initializes seed candidate with `components["instruction"]`
2. `async_engine.py` evolves via component selector (defaults to instruction)
3. `_build_result()` just needs to return all components instead of extracting one

**Decision**: No configuration changes required
**Rationale**: The `evolved_components` dictionary will always contain "instruction" for default evolution. Users access `result.evolved_components["instruction"]` which works identically to the current behavior, just with different syntax.

---

## Summary

| Topic | Decision | Impact |
|-------|----------|--------|
| Field replacement | `evolved_component_text` → `evolved_components: dict[str, str]` | 30+ files |
| IterationRecord | Add `evolved_component: str` field | 2 files |
| Migration pattern | Direct `.evolved_components["instruction"]` access | Examples, tests, docs |
| Default behavior | No config changes needed | Transparent |

**All research tasks complete. No NEEDS CLARIFICATION items remain.**

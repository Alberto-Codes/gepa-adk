# Research: Pass CriticScorer Metadata to Reflection Agent

**Date**: 2026-01-13
**Feature**: 019-critic-metadata-passthrough

## Research Summary

This document captures the technical research for passing CriticScorer metadata through to the reflection agent. The implementation is straightforward based on the existing architecture.

---

## Decision 1: Metadata Storage Location

**Decision**: Add `metadata: list[dict[str, Any]] | None = None` field to `EvaluationBatch` dataclass.

**Rationale**:
- `EvaluationBatch` is the canonical container for evaluation results
- The field parallels the existing `trajectories` field pattern (optional list, index-aligned)
- Upstream GEPA's `EvaluationBatch` uses the same pattern for optional data
- Maintains backward compatibility (default None)

**Alternatives Considered**:
1. **Embed metadata in trajectories**: Rejected - trajectories have a specific structure (ADKTrajectory dataclass), and metadata is scorer-specific, not execution-specific
2. **Store in separate data structure**: Rejected - would complicate the data flow and require additional state management
3. **Create new container class**: Rejected - over-engineering for a simple field addition

---

## Decision 2: Metadata Capture Point

**Decision**: Capture metadata in `ADKAdapter._eval_single_with_semaphore()` when calling `scorer.async_score()`.

**Rationale**:
- The scorer already returns `tuple[float, dict[str, Any]]`
- Current code discards the metadata dict: `score = score_result[0] if isinstance(score_result, tuple) else float(score_result)`
- Minimal change: store the second element when available

**Code Location**: `src/gepa_adk/adapters/adk_adapter.py:615-623`

**Current Code**:
```python
score_result = await self.scorer.async_score(input_text, output_text, expected)
score = score_result[0] if isinstance(score_result, tuple) else float(score_result)
# metadata discarded here
```

**New Code**:
```python
score_result = await self.scorer.async_score(input_text, output_text, expected)
if isinstance(score_result, tuple):
    score, metadata = score_result
else:
    score, metadata = float(score_result), {}
# Return metadata alongside score and trajectory
```

---

## Decision 3: Feedback String Format

**Decision**: Append critic metadata to the existing feedback string format in `_build_reflection_example()`.

**Rationale**:
- The upstream GEPA reflection pattern uses a "Feedback" field in the reflective dataset
- The `InstructionProposalSignature` renders this field in the reflection prompt
- Adding structured critic feedback here provides context to the reflection LLM

**Current Format** (line 816):
```
"score: 0.750, tool_calls: 2, tokens: 150"
```

**New Format** (with metadata):
```
"score: 0.750, tool_calls: 2, tokens: 150
Feedback: Good response but could be more concise
Guidance: Reduce response length by 30%
Dimensions: accuracy=0.9, clarity=0.6"
```

**Alternatives Considered**:
1. **JSON format**: Rejected - less readable for the LLM, and the reflection prompt already uses markdown-style formatting
2. **Separate fields**: Rejected - would require changing the reflective dataset schema and break compatibility with GEPA's `InstructionProposalSignature`
3. **Replace score with text-only**: Rejected - numeric score still provides valuable signal

---

## Decision 4: Handling Partial Metadata

**Decision**: Use defensive access with defaults for missing metadata fields.

**Rationale**:
- Not all scorers return metadata (simple scorers return empty dict)
- CriticScorer metadata fields are all optional (feedback, dimension_scores, actionable_guidance)
- Must handle mixed scenarios where some examples have metadata and others don't

**Pattern**:
```python
feedback_text = metadata.get("feedback", "") if metadata else ""
guidance = metadata.get("actionable_guidance", "") if metadata else ""
dimensions = metadata.get("dimension_scores", {}) if metadata else {}
```

---

## Decision 5: Metadata Index Alignment

**Decision**: Metadata list must be index-aligned with scores list (FR-007).

**Rationale**:
- Matches the pattern used by `trajectories` field
- `metadata[i]` corresponds to `scores[i]` and `outputs[i]`
- Enables direct lookup in `_build_reflection_example()` without complex mapping

**Implementation**: Collect metadata in the same loop that collects scores in `evaluate()`.

---

## Technical Findings

### Upstream GEPA Pattern

From `gepa/core/adapter.py`:
- `EvaluationBatch` is a frozen dataclass with optional fields
- The recommended reflective dataset schema includes "Inputs", "Generated Outputs", and "Feedback"
- Feedback is rendered directly in the reflection prompt

From `gepa/strategies/instruction_proposal.py`:
- The reflection prompt template uses `<inputs_outputs_feedback>` placeholder
- Each example's "Feedback" field is rendered with markdown headers
- The LLM sees the full feedback text when proposing improvements

### CriticScorer Metadata Structure

From `src/gepa_adk/adapters/critic_scorer.py:351-369`:
```python
metadata = {
    "feedback": str,           # Human-readable feedback
    "dimension_scores": dict,  # e.g., {"accuracy": 0.9, "clarity": 0.6}
    "actionable_guidance": str # Specific improvement suggestions
}
```

### Scorer Protocol

From `src/gepa_adk/ports/scorer.py:151-156`:
- `async_score()` returns `tuple[float, dict[str, Any]]`
- All scorers must return this tuple format
- Metadata dict should be JSON-serializable

---

## Implementation Checklist

1. **EvaluationBatch Update** (`ports/adapter.py`)
   - [ ] Add `metadata: list[dict[str, Any]] | None = None` field
   - [ ] Update docstring with metadata description

2. **ADKAdapter.evaluate() Update** (`adapters/adk_adapter.py`)
   - [ ] Capture metadata from scorer result in `_eval_single_with_semaphore()`
   - [ ] Collect metadata list alongside scores
   - [ ] Pass metadata to EvaluationBatch constructor

3. **ADKAdapter._build_reflection_example() Update**
   - [ ] Accept optional metadata parameter
   - [ ] Append feedback text to feedback string
   - [ ] Append actionable_guidance to feedback string
   - [ ] Format dimension_scores in feedback string

4. **ADKAdapter.make_reflective_dataset() Update**
   - [ ] Pass metadata to `_build_reflection_example()` by index

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | Low | Medium | All new fields have defaults; backward compatible |
| Performance overhead | Low | Low | Metadata is already computed; just storing it |
| Reflection prompt too long | Low | Medium | Metadata is typically short; LLM context handles it |
| Type compatibility issues | Low | Low | Using `dict[str, Any]` for flexibility |

---

## References

- **GitHub Issue**: #45
- **CriticScorer Spec**: specs/009-critic-scorer/spec.md (FR-005, FR-006, FR-007)
- **ADK Reflection Spec**: specs/010-adk-reflection-agent/spec.md (FR-005)
- **Upstream GEPA**: `.venv/lib/python3.12/site-packages/gepa/core/adapter.py`

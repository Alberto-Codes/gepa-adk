# Research: Critic Feedback Schema Normalization

**Feature**: 141-critic-feedback-schema
**Date**: 2026-01-20
**Status**: Complete

## Academic Foundation

### GEPA Paper Reference

**Source**: [GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning](https://arxiv.org/pdf/2507.19457)

**Authors**: Lakshya A Agrawal, Shangyin Tan, Dilara Soylu, Noah Ziems, Rishi Khare, Krista Opsahl-Ong, Arnav Singhvi, Herumb Shandilya, Michael J Ryan, Meng Jiang, Christopher Potts, Koushik Sen, Alexandros G. Dimakis, Ion Stoica, Dan Klein, Matei Zaharia, Omar Khattab

**Key Findings Relevant to This Feature**:

1. **Trial-Based Feedback Loop**: The paper validates the iterative cycle where a critic evaluates prompt performance and a reflector generates improved prompts based on structured feedback. This is exactly the architecture implemented in this codebase.

2. **Feedback Components Confirmed**: The paper describes feedback containing:
   - **Trajectories**: Complete task execution paths (input → output)
   - **Scores**: Quantitative performance metrics
   - **Feedback text**: Qualitative performance analysis
   - **Dimensions**: Multiple evaluation axes for prompt assessment
   - **Trials**: Individual prompt evaluation iterations

3. **GEPA Loop Validates Our Approach**:
   - Propose a prompt variant
   - Execute the prompt on benchmark tasks
   - Collect quantitative scores and qualitative feedback
   - Reflect on results using an LLM evaluator
   - Generate improved prompts based on analysis
   - Repeat until convergence

4. **Performance Validation**: GEPA achieves competitive performance relative to reinforcement learning baselines across HotpotQA, HOVER, IFBench, and Papillon benchmarks, demonstrating that reflective prompt evolution with structured feedback is a viable approach.

**Implications for This Feature**:

- The paper confirms `score` and `feedback_text` as core required fields
- Multi-dimensional scoring (`dimensions`) is validated as useful for complex evaluation
- The KISS principle aligns with paper's finding that simpler feedback structures enable effective reflection
- Normalization ensures the reflector receives consistent trial data regardless of scorer complexity

---

## Research Tasks

### 1. Existing Normalization Patterns

**Task**: Find existing normalization code and understand current field mappings.

**Finding**: A `normalize_feedback()` function already exists in `critic_scorer.py` (lines 210-305) but is **not integrated** into the trial-building flow.

**Current Function Signature**:
```python
def normalize_feedback(
    score: float,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
```

**Current Output Fields**:
- `score`: Passed through
- `feedback_text`: From `metadata["feedback_text"]` or `metadata["feedback"]`
- `dimension_scores`: From `metadata["dimension_scores"]` (preserved if dict)
- `actionable_guidance`: From `metadata["actionable_guidance"]` (preserved if string)

**Decision**: Refactor and move `normalize_feedback()` to `trial_builder.py` to consolidate trial-building concerns. Update to support string input per KISS spec.

**Rationale**: TrialBuilder is the single point of truth for trial construction. Moving normalization there ensures all trial paths use the same logic.

**Alternatives considered**:
- Keep in critic_scorer.py: Rejected - violates single responsibility, creates cross-adapter dependency
- Create new utils/normalize.py: Rejected - over-engineering for single-use function

---

### 2. Current TrialBuilder Field Mappings

**Task**: Understand how TrialBuilder currently maps feedback fields.

**Finding**: `TrialBuilder.build_feedback()` (lines 182-203) has hardcoded field extraction:

| Input Field | Output Field |
|-------------|--------------|
| `metadata["feedback"]` | `feedback["feedback_text"]` |
| `metadata["actionable_guidance"]` | `feedback["feedback_guidance"]` |
| `metadata["dimension_scores"]` | `feedback["feedback_dimensions"]` |

**Issue**: Output field naming inconsistent with spec requirements:
- Spec expects `guidance` for optional guidance field
- Current code outputs `feedback_guidance`

**Decision**: Standardize on spec field names: `score`, `feedback_text`, `dimensions`, `guidance`. Custom fields pass through unchanged.

**Rationale**: Aligns with GEPA paper's feedback components (score, feedback text, dimensions, trajectories) and simplifies reflector instruction templates. The paper validates these as the core fields needed for effective reflective prompt evolution.

**Alternatives considered**:
- Keep `feedback_guidance`/`feedback_dimensions` prefixes: Rejected - verbose, spec says `dimensions`/`guidance`
- Add both field names (aliasing): Rejected - unnecessary complexity

---

### 3. Scorer Return Type Contract

**Task**: Confirm scorer protocol supports both simple and advanced returns.

**Finding**: `Scorer` protocol in `ports/scorer.py` specifies:
```python
async def async_score(
    self,
    input_text: str,
    output: str,
    expected: str | None = None,
) -> tuple[float, dict[str, Any]]:
```

**Issue**: Protocol requires `dict[str, Any]` as second tuple element, but KISS spec wants to support `string` directly.

**Decision**: Keep protocol unchanged. The spec's "simple" format `(score, string)` is a **scorer implementation convenience** that gets normalized before reaching adapters. CriticScorer already returns dict; documentation will show both patterns.

**Rationale**: Changing protocol breaks existing implementations. Normalization handles type coercion internally.

**Alternatives considered**:
- Change protocol to `tuple[float, str | dict[str, Any]]`: Rejected - breaks existing code, complicates type checking
- Create new SimplerScorer protocol: Rejected - over-engineering

---

### 4. Reflector Instruction Template Integration

**Task**: Understand how normalized feedback reaches the reflector.

**Finding**: Reflection flow in `adk_reflection.py`:
1. Trials JSON-serialized and stored in session state
2. Template uses `{trials}` placeholder
3. ADK's `inject_session_state()` substitutes JSON into instruction

**Current Template Reference** (REFLECTION_INSTRUCTION, line 82):
```
Based on the trial results:
{trials}
```

**Decision**: No changes to reflection instruction template. Normalization ensures consistent JSON structure.

**Rationale**: Template is format-agnostic; it receives JSON array of trial objects. Normalization happens before serialization.

---

### 5. Test Coverage Strategy

**Task**: Identify required test updates for three-layer testing.

**Finding**: Existing test files:
- `tests/contracts/test_reflection_example_metadata.py` - Contract tests for feedback structure
- `tests/integration/test_critic_reflection_metadata.py` - End-to-end tests
- `tests/unit/adapters/test_trial_builder.py` - TrialBuilder unit tests

**Decision**: Add/update tests in each layer:

| Layer | File | Test Cases |
|-------|------|------------|
| Contract | `test_reflection_example_metadata.py` | Verify normalized output has `score`, `feedback_text` |
| Unit | `test_trial_builder.py` | Test `normalize_feedback()` with string input, dict input, missing fields, custom fields |
| Integration | `test_critic_reflection_metadata.py` | End-to-end with simple and advanced scorers |

**Rationale**: ADR-005 requires three-layer testing. Each layer validates different concerns.

---

### 6. Documentation Requirements

**Task**: Identify documentation that must be updated per Constitution VI.

**Finding**: Per documentation synchronization table:
- `docs/guides/critic-agents.md` - Critic/scorer changes → **Required update**
- `examples/` - Should include working example of both formats

**Decision**: Update critic-agents.md with:
1. Simple feedback format section
2. Advanced feedback format section
3. Normalized output schema reference
4. Migration notes (if any breaking changes)

**Rationale**: Constitution requires docs updates alongside implementation for user-facing changes.

---

## Summary of Decisions

| Area | Decision | Implementation |
|------|----------|----------------|
| **Normalization Location** | Move to TrialBuilder | `adapters/trial_builder.py` |
| **Field Names** | `score`, `feedback_text`, `dimensions`, `guidance` | Update TrialBuilder mapping |
| **Scorer Protocol** | Unchanged (returns dict) | Documentation shows simple pattern |
| **Simple Format Support** | String input normalized to dict | `normalize_feedback()` handles |
| **Testing** | Three layers | Contract + unit + integration |
| **Documentation** | Critic Agents guide | `docs/guides/critic-agents.md` |

## Open Questions

None - all technical decisions resolved.

## Related Issues

- GitHub #140 - DRY consolidation of trial-building logic (completed, TrialBuilder exists)
- GitHub #141 - This feature (standardize feedback schema)

## References

- [GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning](https://arxiv.org/pdf/2507.19457) - Foundational paper validating the trial-based feedback approach

# Research: Shared ADK Event Output Extraction Utility

**Feature Branch**: `033-event-output-extraction`
**Created**: 2026-01-17

## Research Questions

### RQ-1: Current Extraction Logic Patterns

**Question**: What are the current patterns used across the 4 adapter locations?

**Findings**:

| Location | File:Lines | response_content | content.parts | Filters thought | Pattern |
|----------|-----------|:----------------:|:-------------:|:---------------:|---------|
| ADKAdapter._run_single_example | adk_adapter.py:753-760 | No | Yes | No | Break on first text |
| MultiAgentAdapter._run_shared_session | multi_agent.py:747-769 | Yes (primary) | Yes (fallback) | No | Collect + join all texts |
| MultiAgentAdapter._run_isolated_sessions | multi_agent.py:847-869 | Yes (primary) | Yes (fallback) | No | Collect + join all texts |
| CriticScorer.async_score | critic_scorer.py:542-549 | No | Yes | No | Break on first text |

**Decision**: Use the most comprehensive pattern (MultiAgentAdapter style) with dual-path handling:
1. Primary: `event.actions.response_content`
2. Fallback: `event.content.parts`

**Rationale**:
- The MultiAgentAdapter pattern handles both response sources, making it more robust
- Two patterns exist: "break on first" vs "collect all" - the `prefer_concatenated` flag addresses this

**Alternatives Considered**:
- Only use `content.parts`: Rejected because `response_content` is the preferred location per ADK patterns observed in multi-agent scenarios

---

### RQ-2: The `part.thought` Filtering Bug

**Question**: How should `part.thought` filtering be implemented?

**Findings**:

From GitHub issue #82 comments, ADK source code uses the pattern `if not part.thought`:
- `llm_agent.py:828`: `if part.text and not part.thought`
- `llm_agent.py:1018`: `if not part.thought`
- `llm_agent.py:1111`: `if not part.thought`
- `base_agent.py:212`: `if not part.thought`

The `part.thought` attribute is a boolean:
- `True` = reasoning/thinking content (should be filtered out)
- `False` or absent = actual output (should be returned)

**Decision**: Filter parts where `getattr(part, "thought", False)` is True

**Rationale**:
- Matches ADK's established patterns
- Using `getattr` with default `False` handles cases where the attribute doesn't exist
- Fixes the observed bug causing 72 parse errors with models that emit reasoning content

**Alternatives Considered**:
- `hasattr(part, "thought") and part.thought`: More verbose but equivalent
- Only check on specific model types: Rejected - filtering should be universal for consistency

---

### RQ-3: Function Signature Design

**Question**: What should the function signature be?

**Findings**:

Current usage patterns:
1. **Single event lists with break-on-first** (ADKAdapter, CriticScorer): Need just the final output text
2. **Multi-event streaming scenarios** (CriticScorer advanced): Need concatenation of all text parts

The `extract_trajectory` function in the same module accepts `list[Any]` for events (duck-typed to avoid ADK imports).

**Decision**:
```python
def extract_final_output(events: list[Any], *, prefer_concatenated: bool = False) -> str
```

**Rationale**:
- `list[Any]` type maintains consistency with existing `extract_trajectory` signature
- Keyword-only `prefer_concatenated` makes the flag explicit and prevents positional mistakes
- Default `False` maintains backward compatibility with existing "break on first" behavior
- Returns `str` (empty string if no output found) for predictable handling

**Alternatives Considered**:
- Return `Optional[str]`: Rejected - empty string is cleaner for concatenation/formatting downstream
- Add `filter_thoughts: bool = True` parameter: Rejected - filtering should always happen (the bug fix)
- Use ADK type hints: Rejected - would couple `utils/` to external library (violates hexagonal)

---

### RQ-4: Module Location

**Question**: Where should the utility function be placed?

**Findings**:

- `extract_trajectory` is already in `gepa_adk/utils/events.py`
- The `utils/` layer allows minimal external dependencies per hexagonal architecture
- All 4 adapter locations already import from `gepa_adk.utils` module

**Decision**: Add `extract_final_output` to `gepa_adk/utils/events.py`

**Rationale**:
- Follows precedent set by `extract_trajectory`
- Minimizes import changes in adapters
- Maintains hexagonal architecture (no external deps in utils)

**Alternatives Considered**:
- Create `utils/output.py`: Rejected - the function is event-processing related, fits better in events.py
- Add to each adapter as private method: Rejected - still causes duplication (4 copies)

---

### RQ-5: Concatenation Mode Behavior

**Question**: How should `prefer_concatenated=True` work?

**Findings**:

CriticScorer's streaming scenario processes multiple events where JSON may be split across parts.

Current MultiAgentAdapter pattern collects all texts and joins:
```python
parts_text = []
for part in event.content.parts:
    if hasattr(part, "text") and part.text:
        parts_text.append(part.text)
if parts_text:
    final_output = "".join(parts_text)
```

**Decision**:
- `prefer_concatenated=False` (default): Return first non-thought text part from final event only
- `prefer_concatenated=True`: Concatenate all non-thought text parts from ALL events

**Rationale**:
- Default behavior matches current ADKAdapter/CriticScorer simple pattern
- Concatenated mode handles streaming JSON use case for CriticScorer
- Clear semantic distinction between modes

**Alternatives Considered**:
- Always concatenate: Rejected - may produce unexpected results for single-response scenarios
- Separate functions: Rejected - single function with flag is simpler API surface

---

## Summary of Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Response source | Primary: `response_content`, Fallback: `content.parts` | Most robust pattern from MultiAgentAdapter |
| Thought filtering | `getattr(part, "thought", False)` check | Matches ADK patterns, fixes the bug |
| Function signature | `extract_final_output(events: list[Any], *, prefer_concatenated: bool = False) -> str` | Consistent with existing utilities, explicit flag |
| Module location | `gepa_adk/utils/events.py` | Follows `extract_trajectory` precedent |
| Concatenation mode | Flag-controlled behavior | Supports both simple and streaming scenarios |

## Implementation Approach

1. Add `extract_final_output` function to `utils/events.py`
2. Write comprehensive unit tests first (TDD per Constitution)
3. Refactor each adapter location to use the utility
4. Verify all existing tests pass
5. Add contract tests for the utility function

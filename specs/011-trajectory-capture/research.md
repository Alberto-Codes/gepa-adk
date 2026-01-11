# Research: Trajectory Capture from ADK Sessions

**Feature**: 011-trajectory-capture  
**Date**: 2026-01-10  
**Status**: Complete

## Research Questions

### RQ-1: ADK Event Structure for Tool Calls

**Question**: How does Google ADK expose tool/function call information in events?

**Finding**: ADK `Event` class (inherits from `LlmResponse`) provides:
- `get_function_calls()` → `list[types.FunctionCall]` - returns function calls from `event.content.parts`
- `get_function_responses()` → `list[types.FunctionResponse]` - returns function responses
- Each `FunctionCall` has: `name: str`, `args: dict`
- Each `FunctionResponse` has: `name: str`, `response: dict`

**Source**: `.venv/lib/python3.12/site-packages/google/adk/events/event.py` lines 97-118

**Decision**: Use `event.get_function_calls()` method (cleaner than accessing `actions.function_calls`)

---

### RQ-2: ADK State Delta Structure

**Question**: How are state changes exposed in ADK events?

**Finding**: State deltas are in `EventActions`:
- `event.actions.state_delta: dict[str, object]` - direct key-value changes
- NOT before/after format; just the new values
- Spec assumption about "before/after" doesn't match ADK reality

**Source**: `.venv/lib/python3.12/site-packages/google/adk/events/event_actions.py` line 66

**Decision**: Capture state_delta as-is (dict of changed values). Update spec assumption.

**Spec Clarification**: FR-010 states "before and after values" but ADK only provides the delta (new values). Implementation will capture the delta dict directly.

---

### RQ-3: Token Usage Metadata Structure

**Question**: What token usage fields are available in ADK responses?

**Finding**: `LlmResponse.usage_metadata` is `Optional[types.GenerateContentResponseUsageMetadata]`:
- `prompt_token_count: int` - input tokens
- `candidates_token_count: int` - output tokens  
- `total_token_count: int` - sum of all token types
- Additional fields: `cached_content_token_count`, `tool_use_prompt_token_count`

**Source**: `.venv/lib/python3.12/site-packages/google/genai/types.py`

**Decision**: Map to existing `TokenUsage(input_tokens, output_tokens, total_tokens)` model:
- `input_tokens` ← `prompt_token_count`
- `output_tokens` ← `candidates_token_count`
- `total_tokens` ← `total_token_count`

---

### RQ-4: Existing Codebase Analysis

**Question**: What trajectory-related code already exists?

**Finding**: Significant existing implementation in `src/gepa_adk/`:

| Component | Location | Status |
|-----------|----------|--------|
| `ToolCallRecord` | domain/trajectory.py | ✅ Exists |
| `TokenUsage` | domain/trajectory.py | ✅ Exists |
| `ADKTrajectory` | domain/trajectory.py | ✅ Exists |
| `_extract_tool_calls` | adapters/adk_adapter.py | ✅ Exists (private) |
| `_extract_state_deltas` | adapters/adk_adapter.py | ✅ Exists (private) |
| `_extract_token_usage` | adapters/adk_adapter.py | ✅ Exists (private) |
| `_build_trajectory` | adapters/adk_adapter.py | ✅ Exists (private) |
| `TrajectoryConfig` | — | ❌ Missing |
| Redaction utility | — | ❌ Missing |
| Public extract API | — | ❌ Missing |

**Decision**: Refactor existing private methods into public `utils/events.py` module with configuration support.

---

### RQ-5: Redaction Best Practices

**Question**: What's the best approach for recursive sensitive data redaction?

**Finding**: Standard approaches:
1. **Recursive traversal**: Handle dict, list, tuple, primitives
2. **Exact key matching**: Case-sensitive, no partial/fuzzy matching
3. **Immutable output**: Return new structure, don't mutate input
4. **Marker constant**: Use `[REDACTED]` as replacement value

**Decision**: Implement `_redact_sensitive(data, sensitive_keys, marker="[REDACTED]")` with:
- `isinstance` checks for dict/list/tuple
- Recursion for nested structures
- Return new dict/list (copy-on-write pattern)

---

### RQ-6: Truncation for Large Values

**Question**: How should we handle large string values (DOM snapshots, screenshots, verbose API responses)?

**Finding**: Common scenarios producing large outputs:
- **Browser automation**: DOM snapshots (10KB-500KB), accessibility trees
- **Screenshot tools**: Base64-encoded images (100KB-2MB)
- **API responses**: Verbose JSON from external services
- **File content tools**: Reading large files

**Best Practices**:
1. **Truncate strings only**: Don't truncate dicts/lists (lose structure)
2. **Preserve beginning**: First N chars are most informative (headers, structure)
3. **Clear marker**: Indicate truncation occurred and how much was removed
4. **Configurable limit**: Different use cases need different limits
5. **Opt-out option**: None to disable truncation entirely

**Decision**: Implement `_truncate_strings(data, max_length)` with:
- Recursive traversal (same pattern as redaction)
- Only truncate `str` values
- Default 10000 chars (reasonable for reflection context)
- Marker format: `"...[truncated {N} chars]"`
- Process AFTER redaction (redacted values are already short)

**Order of Operations**:
1. Extract raw data from events
2. Apply redaction (sensitive keys → `[REDACTED]`)
3. Apply truncation (long strings → truncated with marker)
4. Build immutable trajectory

---

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Config location | `domain/types.py` | Pure Python, no external deps, aligns with existing types |
| Extraction location | `utils/events.py` | Infrastructure concern, not domain logic |
| Config type | `@dataclass(frozen=True)` | Immutable, hashable, matches existing patterns |
| sensitive_keys type | `tuple[str, ...]` | Immutable default, hashable |
| Redaction marker | `"[REDACTED]"` constant | Simple, recognizable, sufficient for MVP |
| max_string_length default | `10000` | Balances context richness vs memory/token usage |
| Truncation marker | `"...[truncated N chars]"` | Clear, informative, consistent with redaction style |

## Alternatives Considered

### Config in adapters/ vs domain/

**Rejected**: Placing `TrajectoryConfig` in adapters/ would couple configuration to ADK-specific code. Config is a domain concept that could apply to other adapters.

### Regex-based key matching

**Rejected**: Spec explicitly states exact key matching is acceptable for MVP. Regex adds complexity and potential security issues (ReDoS).

### Mutable trajectory output

**Rejected**: ADR-000 and existing `ADKTrajectory` use immutable patterns (`frozen=True`, tuples). Consistency is more important than flexibility here.

### Truncate from end vs beginning

**Rejected**: Keeping the beginning of strings is more useful - headers, structure, and initial content are typically more informative than trailing data.

### Separate truncation config object

**Rejected**: Single `TrajectoryConfig` with all options is simpler. If complexity grows, can refactor later.

## Open Questions

None remaining - all clarifications resolved.

## References

- Google ADK 1.22.0 source: `.venv/lib/python3.12/site-packages/google/adk/`
- Existing trajectory types: `src/gepa_adk/domain/trajectory.py`
- Existing extraction: `src/gepa_adk/adapters/adk_adapter.py` lines 360-520

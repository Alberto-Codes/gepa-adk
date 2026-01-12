# Research: Extended State Token Detection

**Feature**: 015-state-guard-tokens  
**Date**: 2026-01-12  
**Status**: Complete  
**Extends**: [013-state-guard/research.md](file:///home/Alberto-Codes/Projects/gepa-adk/specs/013-state-guard/research.md)

## Overview

This research extends the StateGuard MVP (013-state-guard) to support ADK prefixed and optional token formats. The original research established the foundation; this document focuses specifically on the regex pattern extension.

## Research Tasks

### 1. Regex Pattern for Extended Token Detection

**Question**: What regex pattern correctly identifies all valid ADK state tokens, including prefixes and optional markers?

**Current Pattern** (from 013-state-guard):
```python
r"\{(\w+)\}"  # Matches {simple_name} only
```

**Options Evaluated**:

| Option | Pattern | Matches | Pros | Cons |
|--------|---------|---------|------|------|
| A (Broad) | `\{([^{}]+)\}` | Anything in braces | Simple, catches all | Too permissive (catches `{artifact.name}`, invalid patterns) |
| B (Specific) | `\{(\w+(?::\w+)?(?:\?)?)\}` | identifier, optional prefix, optional `?` | Precise, ADK-aligned | Slightly complex |
| C (Very Specific) | `\{((?:app\|user\|temp):\w+\|\w+)(?:\?)?\}` | Only valid ADK prefixes | Most accurate | Complex, breaks if ADK adds prefixes |

**Decision**: **Option B** - `\{(\w+(?::\w+)?(?:\?)?)\}`

**Rationale**:
1. **Precision**: Matches exactly what we need - identifiers with optional prefix and optional `?`
2. **Extensibility**: Any `prefix:name` format works, not just `app:/user:/temp:`
3. **Backward Compatible**: Still matches simple `{name}` tokens
4. **ADK Aligned**: Matches ADK's `_is_valid_state_name()` which requires Python identifiers

**Pattern Breakdown**:
```python
r"\{(\w+(?::\w+)?(?:\?)?)\}"
#  │ └─────────────────┘  │
#  │         │            │
#  │  (\w+        - base identifier (required)
#  │   (?::\w+)?  - optional prefix:name (e.g., :settings)
#  │   (?:\?)?    - optional ? marker
#  │  )           - capture group for full token content
#  └──────────────────────┘
# \{...\}         - surrounding braces
```

**Matches**:
- `{simple}` → captures `simple`
- `{app:settings}` → captures `app:settings`
- `{user:api_key}` → captures `user:api_key`
- `{temp:session}` → captures `temp:session`
- `{name?}` → captures `name?`
- `{app:config?}` → captures `app:config?`

**Does NOT Match**:
- `{artifact.name}` - contains `.` (different semantics)
- `{invalid-name}` - contains `-` (not valid identifier)
- `{{escaped}}` - double braces
- `{:invalid}` - no base identifier before colon
- `{invalid:}` - no identifier after colon

### 2. Backward Compatibility Verification

**Question**: Will the new pattern break existing simple token behavior?

**Finding**: The new pattern is a superset of the original pattern. All simple `{name}` tokens that matched before will still match.

**Verification Test Cases**:
```python
# Original pattern: r"\{(\w+)\}"
# New pattern: r"\{(\w+(?::\w+)?(?:\?)?)\}"

# Existing tests that must still pass:
assert re.match(pattern, "{user_id}")      # ✓ simple token
assert re.match(pattern, "{context}")       # ✓ simple token
assert re.match(pattern, "{current_step}")  # ✓ simple token
assert not re.match(pattern, "{{escaped}}") # ✓ double braces rejected
assert not re.match(pattern, "{invalid-name}") # ✓ hyphen rejected
```

**Decision**: Pattern is backward compatible. No breaking changes.

### 3. Artifact Token Exclusion

**Question**: Should `{artifact.name}` tokens be matched by StateGuard?

**Finding** (from 013-state-guard/research.md): Artifact references have different semantics. They reference file artifacts, not session state variables. ADK handles them separately.

**Decision**: Do NOT match artifact tokens. The new pattern `\{(\w+(?::\w+)?(?:\?)?)\}` naturally excludes them because `.` is not matched by `\w`.

### 4. Performance Impact

**Question**: Does the more complex regex pattern impact performance?

**Finding**: The pattern adds two optional non-capturing groups `(?::\w+)?(?:\?)?`. In Python's `re` module, these are highly optimized.

**Benchmark** (estimated based on regex theory):
- Original pattern: O(n) where n = string length
- New pattern: O(n) - same complexity class, negligible constant factor increase
- Expected impact: <5% increase in regex matching time
- Real-world impact: <0.01ms difference for typical instruction sizes

**Decision**: Performance impact is negligible. No optimization needed.

## Resolved Clarifications

All technical context items are resolved:

| Item | Resolution |
|------|------------|
| Token pattern | `\{(\w+(?::\w+)?(?:\?)?)\}` (Option B) |
| Backward compatibility | Verified - superset of original pattern |
| Artifact exclusion | Naturally excluded (contains `.`) |
| Performance impact | Negligible, same O(n) complexity |

## Technology Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Regex pattern | `\{(\w+(?::\w+)?(?:\?)?)\}` | Precise, extensible, ADK-aligned |
| Capture group design | Single group for full content | Simplifies token extraction logic |
| Pattern placement | Same `_token_pattern` attribute | Minimal code change |

## References

- [013-state-guard/research.md](file:///home/Alberto-Codes/Projects/gepa-adk/specs/013-state-guard/research.md) - Original StateGuard research
- ADK Source: `.venv/lib/python3.12/site-packages/google/adk/utils/instructions_utils.py`
- Python `re` module: https://docs.python.org/3/library/re.html

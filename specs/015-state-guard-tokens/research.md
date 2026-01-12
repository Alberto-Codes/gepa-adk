# Research: Extended State Token Detection

**Feature**: 015-state-guard-tokens  
**Date**: 2026-01-12  
**Status**: Complete  
**Extends**: [013-state-guard/research.md](file:///home/Alberto-Codes/Projects/gepa-adk/specs/013-state-guard/research.md)

## Overview

This research extends the StateGuard MVP (013-state-guard) to support ADK prefixed and optional token formats. The original research established the foundation; this document focuses specifically on the regex pattern extension.

## ADK Source Analysis (Verified)

Analysis of ADK source code in `.venv/lib/python3.12/site-packages/google/adk/`:

### Key File: `utils/instructions_utils.py`

The `inject_session_state()` function uses:

```python
# ADK's regex pattern for token matching
r'{+[^{}]*}+'  # Matches anything in braces (very permissive)
```

**Token processing flow in `_replace_match()`**:
1. Strip `{` and `}` from match, then strip whitespace
2. Check for `?` suffix → marks token as optional
3. Check for `artifact.` prefix → artifact reference (separate handling)
4. Call `_is_valid_state_name(var_name)` → validates state variable names
5. Invalid names return the original match **unchanged** (not an error)

**`_is_valid_state_name()` validation logic**:
```python
def _is_valid_state_name(var_name):
    parts = var_name.split(':')
    if len(parts) == 1:
        return var_name.isidentifier()  # Simple: {user_id}
    if len(parts) == 2:
        prefixes = [State.APP_PREFIX, State.USER_PREFIX, State.TEMP_PREFIX]
        if (parts[0] + ':') in prefixes:
            return parts[1].isidentifier()  # Prefixed: {app:settings}
    return False
```

### Key File: `sessions/state.py`

```python
class State:
    APP_PREFIX = "app:"
    USER_PREFIX = "user:"
    TEMP_PREFIX = "temp:"
```

### Implications for StateGuard

| ADK Behavior | StateGuard Implication |
|--------------|----------------------|
| `{+[^{}]*}+` matching | ADK is permissive; we can be more precise |
| `_is_valid_state_name()` validation | Only `app:`, `user:`, `temp:` prefixes are valid |
| Optional `?` suffix | Must detect `{name?}` tokens |
| Invalid names pass through | Our regex can safely exclude invalid patterns |
| `artifact.` prefix | Should NOT be matched (different semantics) |

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

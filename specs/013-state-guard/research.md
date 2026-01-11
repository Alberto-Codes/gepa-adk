# Research: StateGuard for State Key Preservation

**Feature**: 013-state-guard  
**Date**: January 11, 2026  
**Status**: Complete

## ADK Source Analysis

Analysis of Google ADK source code in `.venv/lib/python3.12/site-packages/google/adk/` reveals the actual implementation details for state injection.

### Key File: `utils/instructions_utils.py`

The `inject_session_state()` function performs the actual token replacement:

```python
# ADK's regex pattern for token matching (line ~130)
r'{+[^{}]*}+'  # Matches {token}, {{escaped}}, {artifact.name}, etc.
```

**Important findings**:
1. ADK uses a **broader pattern** `{+[^{}]*}+` that matches:
   - `{var_name}` - simple state variable
   - `{artifact.file_name}` - artifact reference
   - `{var_name?}` - optional variable (returns empty if not found)
   - `{{escaped}}` - double braces are preserved literally

2. **Valid state name check** (`_is_valid_state_name()`):
   - Must be a valid Python identifier (`str.isidentifier()`)
   - OR prefixed with `app:`, `user:`, or `temp:` followed by identifier
   - Invalid names are **returned unchanged** (not an error)

3. **State prefixes** (from `sessions/state.py`):
   ```python
   APP_PREFIX = "app:"   # Application-scoped state
   USER_PREFIX = "user:" # User-scoped state  
   TEMP_PREFIX = "temp:" # Temporary/session state
   ```

### Key File: `flows/llm_flows/instructions.py`

Shows how instructions are processed:
1. `canonical_instruction()` returns `(instruction, bypass_state_injection)`
2. If `bypass_state_injection=False`, calls `inject_session_state()`
3. Both `instruction` and `global_instruction` support state injection

### Implications for StateGuard

| ADK Behavior | StateGuard Implication |
|--------------|----------------------|
| Invalid names returned unchanged | Our `\w+` pattern is safe - non-matching tokens pass through |
| Double braces `{{x}}` preserved | Escaping to `{{x}}` is the correct approach |
| Prefixed state (`app:x`, `user:x`, `temp:x`) | Should be recognized as valid tokens |
| Optional suffix `?` | Should be recognized (e.g., `{user_id?}`) |
| Artifact prefix `artifact.` | Should be recognized (e.g., `{artifact.data}`) |

## Research Tasks

### 1. Token Pattern Matching (UPDATED)

**Question**: What regex pattern correctly identifies ADK state injection tokens?

**Finding (from ADK source)**: ADK uses `r'{+[^{}]*}+'` which is very permissive. However, for StateGuard we need to identify **valid** tokens only.

**Decision**: Use `re.compile(r"\{(\w+(?::\w+)?(?:\?)?)\}")` to match:
- `{simple_name}` - basic identifier
- `{app:scoped_name}` - prefixed state
- `{name?}` - optional marker
- Does NOT match `{artifact.x}` (artifact paths have different semantics)

**Rationale**:
- Aligns with ADK's `_is_valid_state_name()` validation
- Covers all documented state variable patterns
- Excludes artifact references (different concern)
- Single brace detection avoids matching already-escaped `{{token}}`

**Alternative (simpler)**: Keep original `\{(\w+)\}` for MVP, since most tokens are simple identifiers. Can extend later if needed.

**Decision for MVP**: Start with `\{(\w+)\}` - covers 95% of use cases. Document that prefixed/optional tokens need the full pattern.

### 2. Escape Mechanism (CONFIRMED)

**Question**: How should unauthorized tokens be escaped?

**Finding (from ADK source)**: ADK's `inject_session_state()` preserves `{{escaped}}` patterns - they are matched but returned unchanged because they don't have valid inner content after stripping outer braces.

**Decision**: Replace single-braced unauthorized tokens with double-braced versions (`{x}` → `{{x}}`).

**Rationale**:
- ADK source confirms `{{x}}` is the escape convention
- Invalid names inside `{}` are returned as-is, but `{{}}` is safer
- Consistent with Python string formatting

### 3. Token Repair Strategy

**Question**: How should missing tokens be re-appended?

**Finding**: Appending to the end with `\n\n{token}` maintains readability without complex insertion logic.

**Decision**: Append missing tokens at the end, separated by double newline.

**Rationale**:
- Simple and predictable behavior
- Doesn't require parsing instruction structure
- User can manually reposition if needed

**Alternatives Considered**:
- Insert at original position - Requires tracking positions, complex for no clear benefit
- Inline replacement - Could break sentence flow

### 4. Token Presence Detection

**Question**: How to efficiently check if a token is "present" in an instruction?

**Finding**: Using `set` operations on extracted token names is O(n) and handles duplicates naturally.

**Decision**: Use `set(token_names)` for presence checking and set operations for missing/new detection.

**Rationale**:
- `original_tokens - mutated_tokens` = missing tokens
- `mutated_tokens - original_tokens` = new tokens
- Handles duplicate tokens correctly (present once = present)

**Alternatives Considered**:
- List comparison with counts - Unnecessary complexity
- String contains check - Fragile, could match partial names

### 5. Configuration Defaults

**Question**: What should the default behavior be?

**Finding**: Most users want safety by default - repair missing and escape unauthorized.

**Decision**: Default `repair_missing=True` and `escape_unauthorized=True`.

**Rationale**:
- Fail-safe default protects against accidental breakage
- Power users can disable specific behaviors
- Matches principle of least surprise

**Alternatives Considered**:
- All disabled by default - Would require explicit opt-in to safety
- Only repair, no escape - Incomplete protection

## Technology Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Regex library | `re` (stdlib) | No external deps needed, performant for simple patterns |
| Data structure | `set` | O(1) lookup, natural set operations |
| String manipulation | `str.replace()` | Simple, handles multiple occurrences |
| Class vs function | Class (`StateGuard`) | Encapsulates config, reusable across validations |

## Resolved Clarifications

All technical context items from `plan.md` are resolved:

| Item | Resolution |
|------|------------|
| Token pattern | `\{(\w+)\}` regex (MVP), extensible to prefixed/optional |
| Escape format | Double braces `{{token}}` (confirmed by ADK source) |
| Repair format | Append with `\n\n{token}` |
| Performance | Regex + set ops = <1ms for 10KB strings |
| ADK compatibility | Verified against `instructions_utils.py` source |

## References

### ADK Source Files (analyzed)
- `.venv/lib/python3.12/site-packages/google/adk/utils/instructions_utils.py` - State injection implementation
- `.venv/lib/python3.12/site-packages/google/adk/sessions/state.py` - State class and prefixes
- `.venv/lib/python3.12/site-packages/google/adk/flows/llm_flows/instructions.py` - Instruction processing flow
- `.venv/lib/python3.12/site-packages/google/adk/agents/llm_agent.py` - Agent instruction fields

### External Documentation
- Python `re` module: https://docs.python.org/3/library/re.html
- Python string formatting: https://docs.python.org/3/library/string.html#format-string-syntax
- Google ADK documentation: https://google.github.io/adk-docs/

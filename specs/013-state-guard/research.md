# Research: StateGuard for State Key Preservation

**Feature**: 013-state-guard  
**Date**: January 11, 2026  
**Status**: Complete

## Research Tasks

### 1. Token Pattern Matching

**Question**: What regex pattern correctly identifies ADK state injection tokens?

**Finding**: The pattern `\{(\w+)\}` correctly matches single-braced tokens containing word characters only (a-z, A-Z, 0-9, underscore).

**Decision**: Use `re.compile(r"\{(\w+)\}")` for token extraction.

**Rationale**:
- `\w+` matches Python identifier-like names (aligns with ADK conventions)
- Single brace detection avoids matching already-escaped `{{token}}`
- Capturing group extracts token name for comparison

**Alternatives Considered**:
- `\{([^}]+)\}` - Would match any characters including hyphens, but ADK tokens follow Python naming
- Template string parsing - Overkill for simple pattern matching

### 2. Escape Mechanism

**Question**: How should unauthorized tokens be escaped?

**Finding**: Doubling braces (`{x}` → `{{x}}`) is the standard Python string formatting escape pattern.

**Decision**: Replace single-braced unauthorized tokens with double-braced versions.

**Rationale**:
- Python's `.format()` and f-strings use `{{` to represent literal `{`
- ADK likely follows this convention for template safety
- Consistent with Python ecosystem expectations

**Alternatives Considered**:
- Backtick escaping - Not Python-native
- Complete removal - Would lose information

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
| Token pattern | `\{(\w+)\}` regex |
| Escape format | Double braces `{{token}}` |
| Repair format | Append with `\n\n{token}` |
| Performance | Regex + set ops = <1ms for 10KB strings |

## References

- Python `re` module: https://docs.python.org/3/library/re.html
- Python string formatting: https://docs.python.org/3/library/string.html#format-string-syntax
- ADK state injection (internal pattern observed in gepa-adk codebase)

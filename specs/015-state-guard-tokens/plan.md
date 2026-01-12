# Implementation Plan: Extended State Token Detection

**Branch**: `015-state-guard-tokens` | **Date**: 2026-01-12 | **Spec**: [spec.md](file:///home/Alberto-Codes/Projects/gepa-adk/specs/015-state-guard-tokens/spec.md)  
**Input**: Feature specification from `/specs/015-state-guard-tokens/spec.md`

## Summary

Extend StateGuard's token detection regex to recognize ADK prefixed tokens (`{app:x}`, `{user:x}`, `{temp:x}`) and optional tokens (`{name?}`), enabling repair and escape functionality for these advanced token formats. Currently, the regex `\{(\w+)\}` only matches simple identifier tokens, missing ~5% of valid ADK state patterns.

> [!NOTE]
> **Verified against ADK source**: See [research.md](file:///home/Alberto-Codes/Projects/gepa-adk/specs/015-state-guard-tokens/research.md#adk-source-analysis-verified) for analysis of `utils/instructions_utils.py` and `sessions/state.py` confirming the regex pattern aligns with ADK's `_is_valid_state_name()` validation.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: `re` (stdlib only - no new dependencies)  
**Storage**: N/A (string manipulation utility)  
**Testing**: pytest with three-layer testing (contract, unit, integration)  
**Target Platform**: Linux/macOS/Windows (pure Python)  
**Project Type**: Single project (hexagonal architecture)  
**Performance Goals**: <1ms for 10KB instruction strings (current performance maintained)  
**Constraints**: Backward compatibility with existing simple tokens; no breaking changes  
**Scale/Scope**: Single file modification with test updates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | ✅ PASS | StateGuard is in `utils/` layer, no external dependencies |
| II. Async-First Design | ✅ N/A | StateGuard is synchronous string manipulation (no I/O) |
| III. Protocol-Based Interfaces | ✅ N/A | StateGuard is a utility class, not a port interface |
| IV. Three-Layer Testing | ✅ REQUIRED | Unit tests exist, will update; no contract/integration needed for utils |
| V. Observability & Documentation | ✅ REQUIRED | Update docstrings to document new token patterns |

**ADR Compliance**:
- ADR-010 (Docstring Quality): Docstrings will be updated with new pattern documentation

## Project Structure

### Documentation (this feature)

```text
specs/015-state-guard-tokens/
├── plan.md              # This file
├── research.md          # Research on regex pattern options (Phase 0)
├── spec.md              # Feature specification
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
src/
└── gepa_adk/
    └── utils/
        └── state_guard.py    # MODIFY: Update _token_pattern regex

tests/
└── unit/
    └── utils/
        └── test_state_guard.py  # MODIFY: Add/update token detection tests
```

**Structure Decision**: Minimal change to existing structure. Only modify StateGuard utility and its tests.

---

## Proposed Changes

### Utils Component

#### [MODIFY] [state_guard.py](file:///home/Alberto-Codes/Projects/gepa-adk/src/gepa_adk/utils/state_guard.py)

1. **Update `_token_pattern` regex** (line 83):
   - Current: `r"\{(\w+)\}"`
   - New: `r"\{(\w+(?::\w+)?(?:\?)?)\}"`
   - Matches:
     - `{simple}` - simple identifier (backward compatible)
     - `{app:name}` - prefixed with `app:`, `user:`, or `temp:`
     - `{name?}` - optional marker
     - `{app:name?}` - combined prefix and optional

2. **Update class docstring** to document supported token patterns

3. **Update `_extract_tokens` docstring** to document extended matching

---

### Tests Component

#### [MODIFY] [test_state_guard.py](file:///home/Alberto-Codes/Projects/gepa-adk/tests/unit/utils/test_state_guard.py)

1. **Remove passthrough tests** (lines 284-306):
   - Remove `test_prefixed_tokens_passthrough` - this behavior will change
   - Remove `test_optional_tokens_passthrough` - this behavior will change

2. **Add new test class `TestPrefixedTokenDetection`**:
   - `test_repair_missing_app_prefixed_token` - verify `{app:settings}` is repaired
   - `test_repair_missing_user_prefixed_token` - verify `{user:api_key}` is repaired
   - `test_repair_missing_temp_prefixed_token` - verify `{temp:session}` is repaired
   - `test_escape_unauthorized_prefixed_token` - verify new prefixed tokens are escaped

3. **Add new test class `TestOptionalTokenDetection`**:
   - `test_repair_missing_optional_token` - verify `{name?}` is repaired
   - `test_escape_unauthorized_optional_token` - verify `{unauthorized?}` is escaped

4. **Add new test class `TestCombinedTokenFormats`**:
   - `test_repair_combined_prefix_optional` - verify `{app:config?}` is repaired
   - `test_mixed_token_formats` - verify all formats work together

5. **Add edge case tests**:
   - `test_artifact_token_not_matched` - verify `{artifact.name}` passes through (contains `.`)
   - `test_invalid_prefix_not_matched` - verify `{invalid:name}` without valid prefix not matched

---

## Verification Plan

### Unit Tests

Run the existing and new unit tests:

```bash
uv run pytest tests/unit/utils/test_state_guard.py -v
```

**Expected outcome**: All tests pass, including:
- Existing simple token tests (backward compatibility)
- New prefixed token tests
- New optional token tests
- Updated edge case tests

### Code Quality Gates

```bash
uv run ruff check src/gepa_adk/utils/state_guard.py
uv run ruff format --check src/gepa_adk/utils/state_guard.py
uv run ty check src/gepa_adk/utils/state_guard.py
```

**Expected outcome**: No linting errors, formatting correct, type checks pass.

### Manual Verification (Quick Smoke Test)

```python
from gepa_adk.utils.state_guard import StateGuard

# Test prefixed token
guard = StateGuard(required_tokens=["{app:settings}"])
result = guard.validate("Use {app:settings}", "Use something")
assert "{app:settings}" in result
print("✓ Prefixed token repair works")

# Test optional token
guard = StateGuard(required_tokens=["{name?}"])
result = guard.validate("Hello {name?}", "Hello")
assert "{name?}" in result
print("✓ Optional token repair works")

# Test escape unauthorized
guard = StateGuard(escape_unauthorized=True)
result = guard.validate("Hello", "Hello {user:secret}")
assert "{{user:secret}}" in result
print("✓ Unauthorized prefixed token escaped")
```

---

## Complexity Tracking

No constitution violations. Implementation is straightforward regex update with test additions.

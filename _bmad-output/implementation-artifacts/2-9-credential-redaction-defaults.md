# Story 2.9: Credential Redaction Defaults

Status: done
Branch: feat/2-9-credential-redaction-defaults

## Story

As a developer,
I want sensible default credential redaction in trajectory logging,
so that API keys and tokens never leak into logs or evolution results without explicit configuration.

## Acceptance Criteria

1. **Given** `TrajectoryConfig` currently has `sensitive_keys` defaulting to `("password", "api_key", "token")`,
   **When** the defaults are updated,
   **Then** a `DEFAULT_SENSITIVE_KEYS` constant is defined in `domain/types.py` containing `("api_key", "token", "secret", "password", "credential", "authorization", "bearer")` and `TrajectoryConfig.sensitive_keys` defaults to `DEFAULT_SENSITIVE_KEYS`.

2. **Given** `TrajectoryConfig.redact_sensitive` already defaults to `True`,
   **When** the constant is applied,
   **Then** the default behavior is secure-by-default (opt-out, not opt-in) — no behavioral change needed for `redact_sensitive`.

3. **Given** a user explicitly passes `sensitive_keys=()` or `redact_sensitive=False`,
   **When** trajectory extraction runs,
   **Then** all values are preserved without redaction (backward compatibility).

4. **Given** default `TrajectoryConfig()` is used,
   **When** trajectory extraction encounters tool_call arguments/results or state_deltas containing keys matching `DEFAULT_SENSITIVE_KEYS`,
   **Then** those values are replaced with `[REDACTED]` via the existing `_redact_sensitive()` function.

5. **Given** the existing test suite,
   **When** `DEFAULT_SENSITIVE_KEYS` replaces the hardcoded tuple,
   **Then** all existing tests continue to pass (the three original keys are a subset of the new defaults).

## Tasks / Subtasks

- [x] Task 1: Define `DEFAULT_SENSITIVE_KEYS` constant (AC: 1)
  - [x] Add `DEFAULT_SENSITIVE_KEYS: tuple[str, ...]` constant to `src/gepa_adk/domain/types.py` above `TrajectoryConfig`
  - [x] Set value to `("api_key", "token", "secret", "password", "credential", "authorization", "bearer")`
  - [x] Update `TrajectoryConfig.sensitive_keys` field default from hardcoded tuple to `DEFAULT_SENSITIVE_KEYS`
  - [x] Export `DEFAULT_SENSITIVE_KEYS` in module `__all__` (types.py defines `__all__` at line 659 — add entry alongside existing constants)
- [x] Task 2: Update `TrajectoryConfig` docstring (AC: 1)
  - [x] Update the `sensitive_keys` field docstring to reference `DEFAULT_SENSITIVE_KEYS` instead of listing `("password", "api_key", "token")`
  - [x] Update the class-level docstring examples that show custom `sensitive_keys` usage
- [x] Task 3: Unit tests for new defaults (AC: 1, 3, 5)
  - [x] Test `TrajectoryConfig()` default `sensitive_keys` matches `DEFAULT_SENSITIVE_KEYS`
  - [x] Test `TrajectoryConfig()` default `redact_sensitive` is `True`
  - [x] Test all seven keys are present in `DEFAULT_SENSITIVE_KEYS`
  - [x] Test `TrajectoryConfig(sensitive_keys=())` produces empty tuple (opt-out)
  - [x] Test `TrajectoryConfig(redact_sensitive=False)` disables redaction flag
- [x] Task 4: Unit tests for redaction with new default keys (AC: 4)
  - [x] Test `_redact_sensitive()` with each of the four NEW keys (`secret`, `credential`, `authorization`, `bearer`) in a nested dict
  - [x] Test `extract_trajectory()` with default config (no explicit `TrajectoryConfig`) redacts a new key (e.g., `{"secret": "mysecret", "name": "test"}` in tool-call args → `"secret"` is `"[REDACTED]"`)
- [x] Task 5: Backward compatibility verification (AC: 3, 5)
  - [x] Run full test suite (`uv run pytest`) — confirm zero regressions
  - [x] Verify `evolution_result_v1.json` fixture still loads correctly (deserialization not affected by default changes)
- [ ] [TEA Review] Split test_models.py: Break 2528-line file into per-model test files for maintainability (from test-review, optional)

## Dev Notes

- **This is a small, focused change.** Only two files need production changes: `domain/types.py` (constant + default) and its docstring. No logic changes to `_redact_sensitive()` or `extract_trajectory()`.
- **Constant location: `domain/types.py`, NOT `utils/events.py`.** The epics file suggests `utils/events.py`, but `TrajectoryConfig` is defined in `domain/types.py` and `events.py` imports from `types.py`. Placing the constant in `events.py` would create a circular import. Keep it co-located with the dataclass that uses it.
- `redact_sensitive` already defaults to `True` (changed in a prior story). No action needed on that field's default value.
- Redaction is case-sensitive and uses exact key matching. `"password"` will NOT match `"Password"` or `"user_password"`. Case-sensitive by design; ADK tool schemas enforce consistent key naming, so mixed-case credential keys do not occur in practice.
- The `_redact_sensitive()` function (events.py:60-130) is a pure recursive transformation. It handles dicts, lists, tuples, and primitives. No modification needed.
- The `extract_trajectory()` function applies redaction conditionally: `if config.redact_sensitive and config.sensitive_keys` — empty tuple short-circuits correctly.
- TEA test-review item picked up: see `_bmad-output/test-artifacts/test-review.md` § Split test_models.py into Per-Model Test Files

### Documentation Impact

- Update `TrajectoryConfig` docstring in `domain/types.py` (in-scope, Task 2)
- No external documentation impact — `DEFAULT_SENSITIVE_KEYS` is an internal constant; the public API (`TrajectoryConfig` constructor) remains unchanged
- No ADR needed — this is a configuration default change, not an architectural decision

### Project Structure Notes

- **Alignment confirmed**: Constant in `domain/types.py` follows hexagonal architecture (domain layer = stdlib + structlog only)
- **No layer violations**: `domain/types.py` has no new imports; `utils/events.py` already imports `TrajectoryConfig` from `domain/types.py`
- **Test location**: New unit tests go in `tests/unit/domain/test_types.py` (for `DEFAULT_SENSITIVE_KEYS` and `TrajectoryConfig` defaults) and `tests/unit/utils/test_events.py` (for redaction behavior with new keys)

### References

- [Source: `src/gepa_adk/domain/types.py:220-226`] — `TrajectoryConfig` dataclass with current defaults
- [Source: `src/gepa_adk/utils/events.py:60-130`] — `_redact_sensitive()` recursive redaction function
- [Source: `src/gepa_adk/utils/events.py:688-707`] — `extract_trajectory()` redaction application point
- [Source: `_bmad-output/planning-artifacts/epics.md:690-703`] — Story 2.9 acceptance criteria
- [Source: `_bmad-output/planning-artifacts/epics.md:94-95`] — NFR6 credential redaction requirement
- [Source: `_bmad-output/planning-artifacts/architecture.md`] — Pattern 4: structlog event conventions, logging sensitive data at DEBUG level
- [Source: `_bmad-output/test-artifacts/test-review.md:94-114`] — TEA recommendation: split test_models.py

### Previous Story Intelligence (Story 2.8)

- **Pattern**: Optional fields on frozen dataclasses use `field_name: type | None = None` with `.get()` default in `from_dict()`
- **Pattern**: Serialization includes `None` fields as JSON `null` for forward compatibility
- **Pattern**: New constants/types co-located with their consuming dataclass
- **Learnings**: 26 new tests added across 18 files; mechanical mock updates needed when changing type signatures — NOT the case here (no signature changes)
- **No mock updates expected**: This story changes only default values, not function signatures or return types

### Git Intelligence (Recent Commits)

- `141596a` chore(rules): split project-context into glob-filtered rule files
- `9732a72` chore(docs): remove manual quality gate instructions
- `94780e3` chore(sprint): fix stale status for story 2-8
- `151a89f` feat(engine): add mutation rationale capture to iteration records
- `e1241dc` feat(engine): add seed-based determinism for reproducible evolution
- Pattern: conventional commits, scope matches affected layer (domain/engine/api)
- Suggested commit: `feat(domain): add default credential redaction keys to TrajectoryConfig`

## Dev Agent Record

### Agent Model Used

claude-opus-4-6

### Debug Log References

None

### Completion Notes List

- Defined `DEFAULT_SENSITIVE_KEYS` constant in `domain/types.py` with 7 credential patterns
- Updated `TrajectoryConfig.sensitive_keys` default from hardcoded tuple to `DEFAULT_SENSITIVE_KEYS`
- Updated docstrings: field description references constant, example shows extending defaults
- Added 5 new unit tests in `test_types.py` (constant contents, config defaults, opt-out, export)
- Added 5 new unit tests in `test_events.py` (4 parametrized `_redact_sensitive` tests for new keys + 1 `extract_trajectory` default-config test)
- Updated 2 existing tests in `test_types.py` to reference `DEFAULT_SENSITIVE_KEYS` instead of hardcoded tuple
- Full suite: 2089 passed, 0 regressions

### AC-to-Test Mapping

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 | `test_default_sensitive_keys_contains_all_seven_keys`, `test_default_sensitive_keys_matches_config_default`, `test_default_configuration`, `test_default_sensitive_keys_exported` | Pass |
| AC2 | `test_default_configuration` (redact_sensitive=True) | Pass |
| AC3 | `test_empty_sensitive_keys_opt_out`, `test_redact_sensitive_false_disables_redaction`, `test_redaction_disabled`, `test_custom_sensitive_keys` | Pass |
| AC4 | `test_redact_new_default_keys[secret/credential/authorization/bearer]`, `test_default_config_redacts_new_key` | Pass |
| AC5 | Full suite 2089 passed — 0 regressions | Pass |

### Change Log

- 2026-03-06: Implemented credential redaction defaults (Tasks 1-5)
- 2026-03-06: Code review fixes — re-export constant from domain/__init__.py, fix stale docstring in utils/__init__.py, move inline import in test_events.py, correct test count in File List

### File List

- `src/gepa_adk/domain/types.py` (modified — added constant, updated default and docstrings)
- `tests/unit/domain/test_types.py` (modified — updated imports, updated 2 existing tests, added 5 new tests)
- `tests/unit/utils/test_events.py` (modified — added 5 new tests for new default key redaction)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — status update)
- `_bmad-output/implementation-artifacts/2-9-credential-redaction-defaults.md` (modified — task tracking)

# Tasks: Extended State Token Detection

**Input**: Design documents from `/specs/015-state-guard-tokens/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓

**Tests**: Included (TDD required per constitution - Three-Layer Testing principle)

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Implementation Status

**Status**: ✅ **COMPLETE** (All 36 tasks completed, including Phase 8 bug fix)

**Completed**: 2026-01-12

**Summary**:
- ✅ Phase 1: Setup - Review completed
- ✅ Phase 2: Foundational - Regex pattern updated, obsolete tests removed
- ✅ Phase 3: User Story 1 - Prefixed token detection implemented and tested
- ✅ Phase 4: User Story 2 - Unauthorized prefixed token escape implemented
- ✅ Phase 5: User Story 3 - Optional token detection implemented
- ✅ Phase 6: Combined formats and edge cases verified
- ✅ Phase 7: Polish - All quality gates passed
- ✅ Phase 8: FR-008 Bug Fix - Already-escaped tokens now pass through unchanged

**Code Quality**: All checks passed (linting, formatting, type checking, docstring quality)

**Files Modified**:
- `src/gepa_adk/utils/state_guard.py` - Updated regex pattern with lookbehind/lookahead and docstrings
- `tests/unit/utils/test_state_guard.py` - Added comprehensive test coverage, strengthened assertions

**Verification**: All tests pass, backward compatibility verified, FR-008 fixed

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No project setup needed - modifying existing files only

- [X] T001 Review existing `_token_pattern` regex in src/gepa_adk/utils/state_guard.py line 83
- [X] T002 Review existing passthrough tests in tests/unit/utils/test_state_guard.py lines 284-306

**Checkpoint**: Understand current implementation before making changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core regex change that ALL user stories depend on

**⚠️ CRITICAL**: No user story tests will pass until regex is updated

- [X] T003 Update `_token_pattern` regex from `r"\{(\w+)\}"` to `r"\{(\w+(?::\w+)?(?:\?)?)\}"` in src/gepa_adk/utils/state_guard.py
- [X] T004 Update class docstring to document new token patterns in src/gepa_adk/utils/state_guard.py
- [X] T005 Update `_extract_tokens` docstring to document extended matching in src/gepa_adk/utils/state_guard.py
- [X] T006 Remove obsolete `test_prefixed_tokens_passthrough` in tests/unit/utils/test_state_guard.py lines 284-294
- [X] T007 Remove obsolete `test_optional_tokens_passthrough` in tests/unit/utils/test_state_guard.py lines 296-306

**Checkpoint**: Regex updated, old passthrough tests removed - ready for user story tests

---

## Phase 3: User Story 1 - Protect Prefixed State Tokens (Priority: P1) 🎯 MVP

**Goal**: Detect and repair `{app:x}`, `{user:x}`, `{temp:x}` tokens when missing

**Independent Test**: Run `uv run pytest tests/unit/utils/test_state_guard.py::TestPrefixedTokenDetection -v`

### Tests for User Story 1 (TDD - Write First, Ensure FAIL)

- [X] T008 [P] [US1] Create `TestPrefixedTokenDetection` class in tests/unit/utils/test_state_guard.py
- [X] T009 [P] [US1] Add `test_repair_missing_app_prefixed_token` for `{app:settings}` in tests/unit/utils/test_state_guard.py
- [X] T010 [P] [US1] Add `test_repair_missing_user_prefixed_token` for `{user:api_key}` in tests/unit/utils/test_state_guard.py
- [X] T011 [P] [US1] Add `test_repair_missing_temp_prefixed_token` for `{temp:session}` in tests/unit/utils/test_state_guard.py

### Verification for User Story 1

- [X] T012 [US1] Run tests and verify all pass: `uv run pytest tests/unit/utils/test_state_guard.py::TestPrefixedTokenDetection -v`
- [X] T013 [US1] Verify backward compatibility: `uv run pytest tests/unit/utils/test_state_guard.py::TestRepairSingleMissingToken -v`

**Checkpoint**: Prefixed tokens `{app:x}`, `{user:x}`, `{temp:x}` are now detected and repaired

---

## Phase 4: User Story 2 - Escape Unauthorized Prefixed Tokens (Priority: P2)

**Goal**: Escape newly introduced unauthorized prefixed tokens like `{user:secret}`

**Independent Test**: Run `uv run pytest tests/unit/utils/test_state_guard.py::TestPrefixedTokenDetection::test_escape_unauthorized_prefixed_token -v`

### Tests for User Story 2 (TDD - Write First)

- [X] T014 [US2] Add `test_escape_unauthorized_prefixed_token` for new `{user:secret}` in tests/unit/utils/test_state_guard.py
- [X] T015 [US2] Add `test_no_escape_authorized_prefixed_token` for token in required_tokens in tests/unit/utils/test_state_guard.py

### Verification for User Story 2

- [X] T016 [US2] Run escape tests: `uv run pytest tests/unit/utils/test_state_guard.py -k "escape" -v`

**Checkpoint**: Unauthorized prefixed tokens are now escaped to `{{prefix:name}}`

---

## Phase 5: User Story 3 - Protect Optional Tokens (Priority: P3)

**Goal**: Detect and repair `{name?}` tokens when missing

**Independent Test**: Run `uv run pytest tests/unit/utils/test_state_guard.py::TestOptionalTokenDetection -v`

### Tests for User Story 3 (TDD - Write First)

- [X] T017 [P] [US3] Create `TestOptionalTokenDetection` class in tests/unit/utils/test_state_guard.py
- [X] T018 [P] [US3] Add `test_repair_missing_optional_token` for `{name?}` in tests/unit/utils/test_state_guard.py
- [X] T019 [P] [US3] Add `test_escape_unauthorized_optional_token` for new `{unknown?}` in tests/unit/utils/test_state_guard.py

### Verification for User Story 3

- [X] T020 [US3] Run optional token tests: `uv run pytest tests/unit/utils/test_state_guard.py::TestOptionalTokenDetection -v`

**Checkpoint**: Optional tokens `{x?}` are now detected and repaired/escaped

---

## Phase 6: Combined Formats & Edge Cases

**Goal**: Verify combined prefix+optional and edge cases work correctly

**Independent Test**: Run `uv run pytest tests/unit/utils/test_state_guard.py::TestCombinedTokenFormats -v`

### Tests for Combined Formats

- [X] T021 [P] Create `TestCombinedTokenFormats` class in tests/unit/utils/test_state_guard.py
- [X] T022 [P] Add `test_repair_combined_prefix_optional` for `{app:config?}` in tests/unit/utils/test_state_guard.py
- [X] T023 [P] Add `test_mixed_token_formats` for `{simple}`, `{app:x}`, `{name?}` together in tests/unit/utils/test_state_guard.py
- [X] T024 [P] Add `test_artifact_token_not_matched` for `{artifact.name}` passthrough in tests/unit/utils/test_state_guard.py

### Verification for Combined Formats

- [X] T025 Run combined tests: `uv run pytest tests/unit/utils/test_state_guard.py::TestCombinedTokenFormats -v`

**Checkpoint**: All token formats work correctly together

---

## Phase 7: Polish & Cross-Cutting Concerns (Original)

**Purpose**: Final verification and documentation

- [X] T026 Run full test suite: `uv run pytest tests/unit/utils/test_state_guard.py -v`
- [X] T027 Run code quality gates: `uv run ruff check src/gepa_adk/utils/state_guard.py`
- [X] T028 Run formatting check: `uv run ruff format --check src/gepa_adk/utils/state_guard.py`
- [X] T029 Run type check: `uv run ty check src/gepa_adk/utils/state_guard.py`
- [X] T030 Manual smoke test using verification script from plan.md

---

## Phase 8: FR-008 Bug Fix - Already-Escaped Tokens (Post-Review)

**Purpose**: Fix bug where `{{already_escaped}}` tokens were being modified to `{{{already_escaped}}}`

**Discovery**: Validation review found weak test assertions were hiding a bug. The regex `\{(\w+(?::\w+)?(?:\?)?)\}` matched `{escaped}` inside `{{escaped}}`, causing triple-braces.

**Research**: Analyzed ADK source at `.venv/lib/python3.12/site-packages/google/adk/utils/instructions_utils.py`:
- ADK uses `r'{+[^{}]*}+'` which matches `{{escaped}}` as a whole unit
- ADK's `_is_valid_state_name()` validates after match and returns original if invalid
- For StateGuard, we need to NOT match already-escaped tokens (different goal than ADK)

### Tasks for Phase 8

- [X] T031 Research ADK's actual regex pattern in `.venv/.../instructions_utils.py`
- [X] T032 Update `_token_pattern` regex to use lookbehind/lookahead: `(?<!\{)\{(\w+(?::\w+)?(?:\?)?)\}(?!\})`
- [X] T033 Update `_extract_tokens` docstring to document lookbehind/lookahead
- [X] T034 Strengthen `test_already_escaped_tokens_ignored` assertion (check exact output, not just `in`)
- [X] T035 Run tests to verify fix: `uv run pytest tests/unit/utils/test_state_guard.py -v`
- [X] T036 Update research.md with ADK source findings

**Checkpoint**: `{{token}}` patterns now pass through completely unchanged

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - review only
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion
- **User Story 2 (Phase 4)**: Depends on Phase 2 completion, can parallel with US1
- **User Story 3 (Phase 5)**: Depends on Phase 2 completion, can parallel with US1/US2
- **Combined (Phase 6)**: Depends on all user stories complete
- **Polish (Phase 7)**: Depends on Phase 6 completion

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories - MVP
- **User Story 2 (P2)**: Independent of US1, tests escape behavior
- **User Story 3 (P3)**: Independent of US1/US2, tests optional tokens

### Parallel Opportunities

```bash
# After Phase 2, can run US1/US2/US3 test writing in parallel:
T008, T009, T010, T011  # US1 tests - parallel
T014, T015              # US2 tests - parallel  
T017, T018, T019        # US3 tests - parallel

# Phase 6 tests can run in parallel:
T021, T022, T023, T024  # Combined format tests - parallel
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Review existing code
2. Complete Phase 2: Update regex (CRITICAL)
3. Complete Phase 3: User Story 1 tests and verification
4. **STOP and VALIDATE**: All prefixed tokens work
5. Continue to US2/US3 if needed

### Incremental Delivery

1. Phase 2 → Regex updated
2. Add US1 → Prefixed tokens work → Test independently
3. Add US2 → Escape unauthorized works → Test independently  
4. Add US3 → Optional tokens work → Test independently
5. Phase 6 → Combined formats verified
6. Phase 7 → All quality gates pass

---

## Summary

| Metric | Count | Status |
|--------|-------|--------|
| Total Tasks | 36 | ✅ All Complete |
| US1 Tasks | 6 | ✅ Complete |
| US2 Tasks | 3 | ✅ Complete |
| US3 Tasks | 4 | ✅ Complete |
| Combined/Edge | 5 | ✅ Complete |
| Polish | 5 | ✅ Complete |
| Phase 8 Bug Fix | 6 | ✅ Complete |
| Parallel Opportunities | 12 | ✅ Utilized |

**MVP Scope**: Phases 1-3 (User Story 1) = 13 tasks ✅ **Completed**

**Full Implementation**: All 36 tasks completed, including all user stories (US1, US2, US3), combined formats, edge cases, quality gates, and Phase 8 FR-008 bug fix.

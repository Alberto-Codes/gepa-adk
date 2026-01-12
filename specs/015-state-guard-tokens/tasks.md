# Tasks: Extended State Token Detection

**Input**: Design documents from `/specs/015-state-guard-tokens/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓

**Tests**: Included (TDD required per constitution - Three-Layer Testing principle)

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No project setup needed - modifying existing files only

- [ ] T001 Review existing `_token_pattern` regex in src/gepa_adk/utils/state_guard.py line 83
- [ ] T002 Review existing passthrough tests in tests/unit/utils/test_state_guard.py lines 284-306

**Checkpoint**: Understand current implementation before making changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core regex change that ALL user stories depend on

**⚠️ CRITICAL**: No user story tests will pass until regex is updated

- [ ] T003 Update `_token_pattern` regex from `r"\{(\w+)\}"` to `r"\{(\w+(?::\w+)?(?:\?)?)\}"` in src/gepa_adk/utils/state_guard.py
- [ ] T004 Update class docstring to document new token patterns in src/gepa_adk/utils/state_guard.py
- [ ] T005 Update `_extract_tokens` docstring to document extended matching in src/gepa_adk/utils/state_guard.py
- [ ] T006 Remove obsolete `test_prefixed_tokens_passthrough` in tests/unit/utils/test_state_guard.py lines 284-294
- [ ] T007 Remove obsolete `test_optional_tokens_passthrough` in tests/unit/utils/test_state_guard.py lines 296-306

**Checkpoint**: Regex updated, old passthrough tests removed - ready for user story tests

---

## Phase 3: User Story 1 - Protect Prefixed State Tokens (Priority: P1) 🎯 MVP

**Goal**: Detect and repair `{app:x}`, `{user:x}`, `{temp:x}` tokens when missing

**Independent Test**: Run `uv run pytest tests/unit/utils/test_state_guard.py::TestPrefixedTokenDetection -v`

### Tests for User Story 1 (TDD - Write First, Ensure FAIL)

- [ ] T008 [P] [US1] Create `TestPrefixedTokenDetection` class in tests/unit/utils/test_state_guard.py
- [ ] T009 [P] [US1] Add `test_repair_missing_app_prefixed_token` for `{app:settings}` in tests/unit/utils/test_state_guard.py
- [ ] T010 [P] [US1] Add `test_repair_missing_user_prefixed_token` for `{user:api_key}` in tests/unit/utils/test_state_guard.py
- [ ] T011 [P] [US1] Add `test_repair_missing_temp_prefixed_token` for `{temp:session}` in tests/unit/utils/test_state_guard.py

### Verification for User Story 1

- [ ] T012 [US1] Run tests and verify all pass: `uv run pytest tests/unit/utils/test_state_guard.py::TestPrefixedTokenDetection -v`
- [ ] T013 [US1] Verify backward compatibility: `uv run pytest tests/unit/utils/test_state_guard.py::TestRepairSingleMissingToken -v`

**Checkpoint**: Prefixed tokens `{app:x}`, `{user:x}`, `{temp:x}` are now detected and repaired

---

## Phase 4: User Story 2 - Escape Unauthorized Prefixed Tokens (Priority: P2)

**Goal**: Escape newly introduced unauthorized prefixed tokens like `{user:secret}`

**Independent Test**: Run `uv run pytest tests/unit/utils/test_state_guard.py::TestPrefixedTokenDetection::test_escape_unauthorized_prefixed_token -v`

### Tests for User Story 2 (TDD - Write First)

- [ ] T014 [US2] Add `test_escape_unauthorized_prefixed_token` for new `{user:secret}` in tests/unit/utils/test_state_guard.py
- [ ] T015 [US2] Add `test_no_escape_authorized_prefixed_token` for token in required_tokens in tests/unit/utils/test_state_guard.py

### Verification for User Story 2

- [ ] T016 [US2] Run escape tests: `uv run pytest tests/unit/utils/test_state_guard.py -k "escape" -v`

**Checkpoint**: Unauthorized prefixed tokens are now escaped to `{{prefix:name}}`

---

## Phase 5: User Story 3 - Protect Optional Tokens (Priority: P3)

**Goal**: Detect and repair `{name?}` tokens when missing

**Independent Test**: Run `uv run pytest tests/unit/utils/test_state_guard.py::TestOptionalTokenDetection -v`

### Tests for User Story 3 (TDD - Write First)

- [ ] T017 [P] [US3] Create `TestOptionalTokenDetection` class in tests/unit/utils/test_state_guard.py
- [ ] T018 [P] [US3] Add `test_repair_missing_optional_token` for `{name?}` in tests/unit/utils/test_state_guard.py
- [ ] T019 [P] [US3] Add `test_escape_unauthorized_optional_token` for new `{unknown?}` in tests/unit/utils/test_state_guard.py

### Verification for User Story 3

- [ ] T020 [US3] Run optional token tests: `uv run pytest tests/unit/utils/test_state_guard.py::TestOptionalTokenDetection -v`

**Checkpoint**: Optional tokens `{x?}` are now detected and repaired/escaped

---

## Phase 6: Combined Formats & Edge Cases

**Goal**: Verify combined prefix+optional and edge cases work correctly

**Independent Test**: Run `uv run pytest tests/unit/utils/test_state_guard.py::TestCombinedTokenFormats -v`

### Tests for Combined Formats

- [ ] T021 [P] Create `TestCombinedTokenFormats` class in tests/unit/utils/test_state_guard.py
- [ ] T022 [P] Add `test_repair_combined_prefix_optional` for `{app:config?}` in tests/unit/utils/test_state_guard.py
- [ ] T023 [P] Add `test_mixed_token_formats` for `{simple}`, `{app:x}`, `{name?}` together in tests/unit/utils/test_state_guard.py
- [ ] T024 [P] Add `test_artifact_token_not_matched` for `{artifact.name}` passthrough in tests/unit/utils/test_state_guard.py

### Verification for Combined Formats

- [ ] T025 Run combined tests: `uv run pytest tests/unit/utils/test_state_guard.py::TestCombinedTokenFormats -v`

**Checkpoint**: All token formats work correctly together

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation

- [ ] T026 Run full test suite: `uv run pytest tests/unit/utils/test_state_guard.py -v`
- [ ] T027 Run code quality gates: `uv run ruff check src/gepa_adk/utils/state_guard.py`
- [ ] T028 Run formatting check: `uv run ruff format --check src/gepa_adk/utils/state_guard.py`
- [ ] T029 Run type check: `uv run ty check src/gepa_adk/utils/state_guard.py`
- [ ] T030 Manual smoke test using verification script from plan.md

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

| Metric | Count |
|--------|-------|
| Total Tasks | 30 |
| US1 Tasks | 6 |
| US2 Tasks | 3 |
| US3 Tasks | 4 |
| Combined/Edge | 5 |
| Polish | 5 |
| Parallel Opportunities | 12 |

**MVP Scope**: Phases 1-3 (User Story 1) = 13 tasks

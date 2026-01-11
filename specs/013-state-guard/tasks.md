# Tasks: StateGuard for State Key Preservation

**Input**: Design documents from `/specs/013-state-guard/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Tests**: TDD required per constitution - tests MUST be written before implementation and FAIL first.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in descriptions

## Path Conventions

- **Source**: `src/gepa_adk/utils/state_guard.py`
- **Tests**: `tests/unit/utils/test_state_guard.py`

---

## Phase 1: Setup

**Purpose**: Project structure and test file scaffolding

- [ ] T001 Create test file scaffold `tests/unit/utils/test_state_guard.py` with imports and pytest marker
- [ ] T002 [P] Create source file scaffold `src/gepa_adk/utils/state_guard.py` with module docstring

---

## Phase 2: User Story 1 & 3 - Token Repair (Priority: P1) 🎯 MVP

**Goal**: Detect missing required tokens and re-append them to mutated instructions

**Independent Test**: Create StateGuard with `required_tokens=["{user_id}"]`, pass original with `{user_id}`, mutated without it, verify token is appended.

**Note**: US3 (Required Token Configuration) is implemented together with US1 as it defines the configuration mechanism that drives repair behavior.

### Tests for User Story 1 & 3 (TDD - Write First, Must FAIL)

- [ ] T003 [US1] Write test `test_repair_single_missing_token` - verify missing `{current_step}` is re-appended in `tests/unit/utils/test_state_guard.py`
- [ ] T004 [US1] Write test `test_repair_multiple_missing_tokens` - verify only missing tokens from required_tokens are appended in `tests/unit/utils/test_state_guard.py`
- [ ] T005 [US1] Write test `test_no_repair_when_tokens_present` - verify instruction unchanged when all tokens present in `tests/unit/utils/test_state_guard.py`
- [ ] T006 [US3] Write test `test_required_tokens_configuration` - verify required_tokens list drives repair behavior in `tests/unit/utils/test_state_guard.py`
- [ ] T007 [US3] Write test `test_empty_required_tokens` - verify only original tokens considered when required_tokens is empty in `tests/unit/utils/test_state_guard.py`
- [ ] T008 Run tests T003-T007 to confirm they FAIL (Red phase)

### Implementation for User Story 1 & 3

- [ ] T009 [US1] Implement `StateGuard.__init__()` with `required_tokens`, `repair_missing`, `escape_unauthorized`, `_token_pattern` in `src/gepa_adk/utils/state_guard.py`
- [ ] T010 [US1] Implement private method `_extract_tokens(text: str) -> set[str]` using regex in `src/gepa_adk/utils/state_guard.py`
- [ ] T011 [US1] Implement `StateGuard.validate(original: str, mutated: str) -> str` with repair logic in `src/gepa_adk/utils/state_guard.py`
- [ ] T012 Run tests T003-T007 to confirm they PASS (Green phase)

**Checkpoint**: User Story 1 & 3 complete - token repair works independently

---

## Phase 3: User Story 2 - Escape Unauthorized Tokens (Priority: P2)

**Goal**: Escape new tokens introduced by reflection that weren't in the original instruction

**Independent Test**: Create StateGuard, pass original without `{malicious}`, mutated with `{malicious}`, verify it becomes `{{malicious}}`.

### Tests for User Story 2 (TDD - Write First, Must FAIL)

- [ ] T013 [US2] Write test `test_escape_single_unauthorized_token` - verify new `{malicious}` becomes `{{malicious}}` in `tests/unit/utils/test_state_guard.py`
- [ ] T014 [US2] Write test `test_escape_multiple_unauthorized_tokens` - verify all new unauthorized tokens are escaped in `tests/unit/utils/test_state_guard.py`
- [ ] T015 [US2] Write test `test_no_escape_authorized_new_token` - verify token in required_tokens is NOT escaped even if new in `tests/unit/utils/test_state_guard.py`
- [ ] T016 [US2] Write test `test_no_escape_existing_token` - verify tokens in both original and mutated are not escaped in `tests/unit/utils/test_state_guard.py`
- [ ] T017 Run tests T013-T016 to confirm they FAIL (Red phase)

### Implementation for User Story 2

- [ ] T018 [US2] Add escape logic to `StateGuard.validate()` - detect new tokens and double their braces in `src/gepa_adk/utils/state_guard.py`
- [ ] T019 Run tests T013-T016 to confirm they PASS (Green phase)

**Checkpoint**: User Stories 1, 2 & 3 complete - both repair and escape work

---

## Phase 4: User Story 4 - Configurable Behavior (Priority: P3)

**Goal**: Allow toggling repair and escape behaviors via configuration flags

**Independent Test**: Set `repair_missing=False`, verify missing tokens are NOT repaired. Set `escape_unauthorized=False`, verify new tokens are NOT escaped.

### Tests for User Story 4 (TDD - Write First, Must FAIL)

- [ ] T020 [US4] Write test `test_repair_disabled` - verify missing tokens NOT repaired when `repair_missing=False` in `tests/unit/utils/test_state_guard.py`
- [ ] T021 [US4] Write test `test_escape_disabled` - verify new tokens NOT escaped when `escape_unauthorized=False` in `tests/unit/utils/test_state_guard.py`
- [ ] T022 [US4] Write test `test_passthrough_mode` - verify no changes when both behaviors disabled in `tests/unit/utils/test_state_guard.py`
- [ ] T023 Run tests T020-T022 to confirm they FAIL (Red phase)

### Implementation for User Story 4

- [ ] T024 [US4] Add conditional checks for `repair_missing` and `escape_unauthorized` flags in `StateGuard.validate()` in `src/gepa_adk/utils/state_guard.py`
- [ ] T025 Run tests T020-T022 to confirm they PASS (Green phase)

**Checkpoint**: All user stories complete - full configurable behavior

---

## Phase 5: Edge Cases & Polish

**Purpose**: Handle edge cases and finalize implementation

### Edge Case Tests

- [ ] T026 [P] Write test `test_empty_original_instruction` - verify new tokens escaped when original has no tokens in `tests/unit/utils/test_state_guard.py`
- [ ] T027 [P] Write test `test_empty_mutated_instruction` - verify missing tokens appended to empty result in `tests/unit/utils/test_state_guard.py`
- [ ] T028 [P] Write test `test_already_escaped_tokens_ignored` - verify `{{escaped}}` patterns are not matched in `tests/unit/utils/test_state_guard.py`
- [ ] T029 [P] Write test `test_malformed_tokens_ignored` - verify `{invalid-name}` with hyphens passes through unchanged in `tests/unit/utils/test_state_guard.py`
- [ ] T030 [P] Write test `test_duplicate_tokens_in_original` - verify token counted once even if appears multiple times in `tests/unit/utils/test_state_guard.py`

### Polish

- [ ] T031 Add Google-style docstrings to all public methods in `src/gepa_adk/utils/state_guard.py`
- [ ] T032 Export `StateGuard` from `src/gepa_adk/utils/__init__.py`
- [ ] T033 Run `uv run ruff check --fix` and `uv run ruff format` on all modified files
- [ ] T034 Run `uv run ty check` to verify type annotations
- [ ] T035 Run full test suite: `uv run pytest tests/unit/utils/test_state_guard.py -v`
- [ ] T036 Validate against quickstart.md examples manually

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup
    ↓
Phase 2: US1 & US3 (Token Repair + Config) ← MVP COMPLETE
    ↓
Phase 3: US2 (Escape Unauthorized)
    ↓
Phase 4: US4 (Configurable Behavior)
    ↓
Phase 5: Edge Cases & Polish
```

### Within Each Phase (TDD Cycle)

1. Write tests → Run tests (RED - must fail)
2. Implement code → Run tests (GREEN - must pass)
3. Refactor if needed → Run tests (still GREEN)

### Parallel Opportunities

**Phase 1** (both can run in parallel):
```
T001: Create test file scaffold
T002: Create source file scaffold
```

**Phase 2 Tests** (all can run in parallel):
```
T003-T007: All US1/US3 tests
```

**Phase 5 Edge Case Tests** (all can run in parallel):
```
T026-T030: All edge case tests
```

---

## Implementation Strategy

### MVP First (Phase 1 + 2)

1. Complete Setup (T001-T002)
2. Write US1/US3 tests (T003-T007) → Verify RED
3. Implement StateGuard class (T009-T011) → Verify GREEN
4. **STOP and VALIDATE**: Token repair works independently

### Incremental Delivery

1. **MVP**: Setup + US1/US3 → Token repair functional
2. **+US2**: Add escape logic → Both repair and escape work
3. **+US4**: Add config flags → Full flexibility
4. **+Polish**: Edge cases, docstrings, exports

---

## Summary

| Metric | Count |
|--------|-------|
| Total Tasks | 36 |
| Phase 1 (Setup) | 2 |
| Phase 2 (US1+US3 MVP) | 10 |
| Phase 3 (US2) | 7 |
| Phase 4 (US4) | 6 |
| Phase 5 (Polish) | 11 |
| Parallel Opportunities | T001-T002, T003-T007, T026-T030 |

**Suggested MVP Scope**: Phase 1 + Phase 2 (12 tasks) - delivers core token repair functionality.

# Tasks: Optional Stoppers (MaxEvaluations and File-based)

**Input**: Design documents from `/specs/197-optional-stoppers/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/stopper-api.md, research.md, quickstart.md

**Tests**: Included per Constitution ADR-005 (Three-Layer Testing) - contract and unit tests required.

**Documentation**: Per Constitution Principle VI, these are new public APIs. Documentation tasks are included within each user story phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Documentation Scope

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| New public API (stoppers) | Required | Recommended |

Per Constitution Principle VI, documentation tasks are part of each user story phase (T008a, T013a).

---

## Phase 1: Setup

**Purpose**: Verify project structure and ensure dependencies are available

- [x] T001 Verify existing stopper infrastructure in src/gepa_adk/adapters/stoppers/__init__.py
- [x] T002 Verify StopperState has total_evaluations field in src/gepa_adk/domain/stopper.py
- [x] T003 Verify StopperProtocol exists in src/gepa_adk/ports/stopper.py

**Checkpoint**: Infrastructure confirmed - implementation can proceed

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: None required - existing stopper infrastructure is already in place

**⚠️ CRITICAL**: No foundational tasks needed. Both stoppers only depend on existing infrastructure (StopperState, StopperProtocol) which is already implemented.

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Control API Costs with Evaluation Limits (Priority: P1) 🎯 MVP

**Goal**: Implement MaxEvaluationsStopper to stop evolution after N total evaluations

**Independent Test**: Configure evaluation limit, verify stopper returns True when limit reached, False otherwise

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Add contract test for MaxEvaluationsStopper protocol compliance in tests/contracts/test_stopper_protocol.py
- [x] T005 [P] [US1] Create unit test file tests/unit/adapters/stoppers/test_evaluations.py with test cases:
  - test_stops_at_exact_limit (100 evals, limit 100 → True)
  - test_stops_above_limit (150 evals, limit 100 → True)
  - test_stops_when_limit_exceeded_between_checks (105 evals, limit 100 → True)
  - test_continues_below_limit (50 evals, limit 100 → False)
  - test_rejects_zero_evaluations (ValueError)
  - test_rejects_negative_evaluations (ValueError)

### Implementation for User Story 1

- [x] T006 [US1] Implement MaxEvaluationsStopper class in src/gepa_adk/adapters/stoppers/evaluations.py:
  - `__init__(max_evaluations: int)` with validation
  - `__call__(state: StopperState) -> bool` comparing total_evaluations
  - Google-style docstrings per ADR-010
- [x] T007 [US1] Export MaxEvaluationsStopper in src/gepa_adk/adapters/stoppers/__init__.py
- [x] T008 [US1] Run tests and verify all pass: `uv run pytest tests/unit/adapters/stoppers/test_evaluations.py tests/contracts/test_stopper_protocol.py -v`

### Documentation for User Story 1

- [x] T008a [P] [US1] Update docs/guides/ with MaxEvaluationsStopper usage example (add to existing stopper guide or create section)

**Checkpoint**: User Story 1 complete - MaxEvaluationsStopper stops evolution at evaluation limit

---

## Phase 4: User Story 2 - External Orchestration with File-based Stop Signal (Priority: P2)

**Goal**: Implement FileStopper to stop evolution when a specified file exists

**Independent Test**: Configure stop file path, create file, verify stopper returns True; verify remove_on_stop removes file

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US2] Add contract test for FileStopper protocol compliance in tests/contracts/test_stopper_protocol.py
- [x] T010 [P] [US2] Create unit test file tests/unit/adapters/stoppers/test_file.py with test cases:
  - test_stops_when_file_exists (file exists → True)
  - test_continues_when_file_missing (file missing → False)
  - test_remove_on_stop_deletes_file (remove_on_stop=True deletes file)
  - test_remove_on_stop_false_keeps_file (remove_on_stop=False keeps file)
  - test_handles_nonexistent_directory (graceful handling)
  - test_accepts_string_path (str input converted to Path)
  - test_accepts_path_object (Path input accepted)

### Implementation for User Story 2

- [x] T011 [US2] Implement FileStopper class in src/gepa_adk/adapters/stoppers/file.py:
  - `__init__(stop_file_path: str | Path, remove_on_stop: bool = False)`
  - `__call__(state: StopperState) -> bool` checking file existence
  - Handle remove_on_stop with `missing_ok=True`
  - Google-style docstrings per ADR-010
- [x] T012 [US2] Export FileStopper in src/gepa_adk/adapters/stoppers/__init__.py
- [x] T013 [US2] Run tests and verify all pass: `uv run pytest tests/unit/adapters/stoppers/test_file.py tests/contracts/test_stopper_protocol.py -v`

### Documentation for User Story 2

- [x] T013a [P] [US2] Update docs/guides/ with FileStopper usage example (add to existing stopper guide or create section)

**Checkpoint**: User Story 2 complete - FileStopper stops evolution when file exists

---

## Phase 5: User Story 3 - Manual Stop File Cleanup (Priority: P3)

**Goal**: Add remove_stop_file() method to FileStopper for manual cleanup

**Independent Test**: Create stop file, call remove_stop_file(), verify file removed; call again, verify no error

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T014 [P] [US3] Add test cases to tests/unit/adapters/stoppers/test_file.py:
  - test_remove_stop_file_deletes_existing (file removed)
  - test_remove_stop_file_idempotent (no error when file missing)

### Implementation for User Story 3

- [x] T015 [US3] Add remove_stop_file() method to FileStopper in src/gepa_adk/adapters/stoppers/file.py:
  - `remove_stop_file() -> None` using `unlink(missing_ok=True)`
  - Google-style docstring
- [x] T016 [US3] Run tests and verify all pass: `uv run pytest tests/unit/adapters/stoppers/test_file.py -v`

**Checkpoint**: User Story 3 complete - Manual stop file cleanup available

---

## Phase 6: Verification & Cross-Cutting Concerns

**Purpose**: Final verification and code quality checks

### Verification Tasks

- [x] T017 Run full test suite: `uv run pytest tests/unit/adapters/stoppers/ tests/contracts/test_stopper_protocol.py -v`
- [x] T018 Run linter: `uv run ruff check src/gepa_adk/adapters/stoppers/evaluations.py src/gepa_adk/adapters/stoppers/file.py`
- [x] T019 Run formatter: `uv run ruff format src/gepa_adk/adapters/stoppers/evaluations.py src/gepa_adk/adapters/stoppers/file.py`
- [x] T020 Run type checker: `uv run ty check src/gepa_adk/adapters/stoppers/`
- [x] T021 Verify docstring coverage with interrogate (if configured)

### Build Verification (Required per Constitution VI)

- [x] T022 Verify `uv run mkdocs build` passes without warnings

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verification only
- **Foundational (Phase 2)**: Skipped - no new foundation needed
- **User Story 1 (Phase 3)**: Can start immediately after Setup
- **User Story 2 (Phase 4)**: Can start in parallel with US1 (different files)
- **User Story 3 (Phase 5)**: Depends on US2 (adds method to FileStopper)
- **Verification (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

```
US1 (MaxEvaluationsStopper) ──────────────────────────────┐
                                                          ├──→ Verification
US2 (FileStopper) ──→ US3 (remove_stop_file method) ──────┘
```

- **User Story 1 (P1)**: Independent - can start after Setup
- **User Story 2 (P2)**: Independent - can start after Setup, parallel with US1
- **User Story 3 (P3)**: Depends on US2 (adds method to FileStopper class)

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Implementation follows tests
3. All tests pass before story complete

### Parallel Opportunities

- T004, T005 (US1 tests) can run in parallel
- T009, T010 (US2 tests) can run in parallel
- US1 and US2 can be implemented in parallel (different files)
- T008a, T013a (docs) can run in parallel with implementation tasks

---

## Parallel Example: User Stories 1 and 2

```bash
# Launch US1 and US2 tests in parallel:
Task: "Add contract test for MaxEvaluationsStopper in tests/contracts/test_stopper_protocol.py"
Task: "Create unit test file tests/unit/adapters/stoppers/test_evaluations.py"
Task: "Add contract test for FileStopper in tests/contracts/test_stopper_protocol.py"
Task: "Create unit test file tests/unit/adapters/stoppers/test_file.py"

# Launch US1 and US2 implementation in parallel:
Task: "Implement MaxEvaluationsStopper in src/gepa_adk/adapters/stoppers/evaluations.py"
Task: "Implement FileStopper in src/gepa_adk/adapters/stoppers/file.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verification)
2. Complete Phase 3: User Story 1 (MaxEvaluationsStopper)
3. **STOP and VALIDATE**: Test MaxEvaluationsStopper independently
4. Can ship MVP with just evaluation limiting

### Incremental Delivery

1. Complete Setup → Infrastructure verified
2. Add User Story 1 → MaxEvaluationsStopper available (MVP!)
3. Add User Story 2 → FileStopper available
4. Add User Story 3 → Manual cleanup available
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Developer A: User Story 1 (MaxEvaluationsStopper)
2. Developer B: User Story 2 + 3 (FileStopper + cleanup)
3. Both complete independently, merge at Verification phase

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Run `uv run pytest` to verify all tests pass before PR

# Tasks: Concurrent Batch Evaluation

**Input**: Design documents from `/specs/012-concurrent-batch/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Included per three-layer testing strategy (ADR-005).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/gepa_adk/`
- **Tests**: `tests/` (contracts/, integration/, unit/)

---

## Phase 1: Setup

**Purpose**: Verify existing infrastructure supports this feature

- [X] T001 Verify `EvolutionConfig.max_concurrent_evals` exists in `src/gepa_adk/domain/models.py` with default=5 (validates FR-004)
- [X] T002 Verify `ADKAdapter` class structure in `src/gepa_adk/adapters/adk_adapter.py` supports modification
- [X] T003 [P] Verify `EvaluationBatch` type in `src/gepa_adk/ports/adapter.py` is unchanged (no modifications needed)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add constructor parameter and validation that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Add `max_concurrent_evals: int = 5` parameter to `ADKAdapter.__init__()` in `src/gepa_adk/adapters/adk_adapter.py`
- [X] T005 Add validation in `ADKAdapter.__init__()` to raise `ValueError` if `max_concurrent_evals < 1`
- [X] T006 Store `self.max_concurrent_evals` as instance attribute in `ADKAdapter`
- [X] T007 Update `ADKAdapter.__init__()` docstring with new parameter documentation
- [X] T008 [P] Add unit test for constructor parameter in `tests/unit/adapters/test_adk_adapter.py`
- [X] T009 [P] Add unit test for validation rejection of invalid values in `tests/unit/adapters/test_adk_adapter.py`

**Checkpoint**: Foundation ready - ADKAdapter accepts and validates concurrency parameter

---

## Phase 3: User Story 1 - Parallel Batch Evaluation (Priority: P1) 🎯 MVP

**Goal**: Execute batch evaluations in parallel using asyncio.Semaphore + asyncio.gather

**Independent Test**: Run batch of N examples with concurrency C and verify total time ≈ (N/C) × single_eval_time

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Contract test for parallel execution behavior in `tests/contracts/test_adk_adapter_contracts.py`
- [X] T011 [P] [US1] Contract test for result ordering preservation (FR-009) in `tests/contracts/test_adk_adapter_contracts.py`
- [X] T012 [P] [US1] Unit test for `_eval_single_with_semaphore()` method in `tests/unit/adapters/test_adk_adapter.py`
- [X] T013 [P] [US1] Unit test verifying semaphore limits concurrent execution in `tests/unit/adapters/test_adk_adapter.py`
- [X] T014 [P] [US1] Integration test for parallel batch evaluation with real ADK in `tests/integration/adapters/test_adk_adapter_integration.py`

### Implementation for User Story 1

- [X] T015 [US1] Create helper method `_eval_single_with_semaphore()` in `src/gepa_adk/adapters/adk_adapter.py`
- [X] T016 [US1] Refactor `evaluate()` method to create `asyncio.Semaphore(self.max_concurrent_evals)` in `src/gepa_adk/adapters/adk_adapter.py`
- [X] T017 [US1] Replace sequential loop with `asyncio.gather(*tasks, return_exceptions=True)` in `src/gepa_adk/adapters/adk_adapter.py`
- [X] T018 [US1] Update `evaluate()` to process gather results (unpack tuples or handle exceptions) in `src/gepa_adk/adapters/adk_adapter.py`
- [X] T019 [US1] Add structured logging for batch start/complete with concurrency metrics in `src/gepa_adk/adapters/adk_adapter.py`
- [X] T020 [US1] Update `evaluate()` docstring to document parallel execution behavior

**Checkpoint**: Parallel batch evaluation works - 3-5x speedup achieved

---

## Phase 4: User Story 2 - Concurrency Limit Control (Priority: P2)

**Goal**: Users can configure concurrency from 1 to 20+ and observe correct limiting

**Independent Test**: Set different concurrency limits and verify at most N evaluations run simultaneously

### Tests for User Story 2

- [X] T021 [P] [US2] Contract test for concurrency=1 (sequential) behavior in `tests/contracts/test_adk_adapter_contracts.py`
- [X] T022 [P] [US2] Contract test for concurrency > batch_size behavior in `tests/contracts/test_adk_adapter_contracts.py`
- [X] T023 [P] [US2] Unit test for various concurrency configurations (1, 5, 10, 20) in `tests/unit/adapters/test_adk_adapter.py`

### Implementation for User Story 2

- [X] T024 [US2] Verify semaphore correctly limits concurrent tasks at runtime (via logging) in `src/gepa_adk/adapters/adk_adapter.py`
- [X] T025 [US2] Add debug-level logging inside `_eval_single_with_semaphore()` showing semaphore acquire/release in `src/gepa_adk/adapters/adk_adapter.py`

**Checkpoint**: Concurrency control verified across all valid configurations

---

## Phase 5: User Story 3 - Graceful Error Handling (Priority: P3)

**Goal**: Individual failures don't block other evaluations; complete result set always returned

**Independent Test**: Cause one evaluation to fail and verify others complete successfully

### Tests for User Story 3

- [X] T026 [P] [US3] Contract test for individual failure isolation in `tests/contracts/test_adk_adapter_contracts.py`
- [X] T027 [P] [US3] Contract test for error information capture in `tests/contracts/test_adk_adapter_contracts.py`
- [X] T028 [P] [US3] Contract test for 0.0 score on failures in `tests/contracts/test_adk_adapter_contracts.py`
- [X] T029 [P] [US3] Contract test for complete result set with mixed success/failure in `tests/contracts/test_adk_adapter_contracts.py`
- [X] T030 [P] [US3] Unit test for exception handling in gather results in `tests/unit/adapters/test_adk_adapter.py`
- [X] T031 [P] [US3] Integration test with intentional failure scenarios in `tests/integration/adapters/test_adk_adapter_integration.py`

### Implementation for User Story 3

- [X] T032 [US3] Implement exception detection in gather results processing (`isinstance(r, Exception)`) in `src/gepa_adk/adapters/adk_adapter.py`
- [X] T033 [US3] Add error trajectory creation for failed evaluations (set `trajectory.error = str(e)`) in `src/gepa_adk/adapters/adk_adapter.py`
- [X] T034 [US3] Add warning-level logging for individual example failures in `src/gepa_adk/adapters/adk_adapter.py`
- [X] T035 [US3] Verify empty output ("") and 0.0 score assigned to failures

**Checkpoint**: All user stories complete - error handling verified

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T036 [P] Update `docs/` with concurrent evaluation documentation
- [X] T037 [P] Add edge case test for empty batch in `tests/unit/adapters/test_adk_adapter.py`
- [X] T038 [P] Add edge case test for all-failures batch in `tests/unit/adapters/test_adk_adapter.py`
- [X] T039 Run `quickstart.md` validation examples to verify documentation accuracy
- [X] T040 Run full test suite with `uv run pytest -n auto` to verify no regressions
- [X] T041 Run `uv run ruff check --fix && uv run ruff format` for code quality

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verification only
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - core parallel implementation
- **User Story 2 (Phase 4)**: Depends on Foundational - can run parallel with US1
- **User Story 3 (Phase 5)**: Depends on US1 implementation (error handling in gather results)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1
- **User Story 3 (P3)**: Depends on US1 implementation (error handling builds on gather pattern)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Helper methods before main method refactoring
- Core implementation before logging/documentation
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T001, T002, T003 can run in parallel (verification tasks)
```

**Phase 2 (Foundational)**:
```
T008, T009 can run in parallel (different test functions)
```

**Phase 3 (US1 - Tests)**:
```
T010, T011, T012, T013, T014 can run in parallel (different test files/functions)
```

**Phase 4 (US2 - Tests)**:
```
T021, T022, T023 can run in parallel (different test functions)
```

**Phase 5 (US3 - Tests)**:
```
T026, T027, T028, T029, T030, T031 can run in parallel (different test files/functions)
```

**Phase 6 (Polish)**:
```
T036, T037, T038 can run in parallel (different files)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify existing infrastructure)
2. Complete Phase 2: Foundational (add constructor parameter)
3. Complete Phase 3: User Story 1 (parallel execution)
4. **STOP and VALIDATE**: Run performance test to verify 3-5x speedup
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Constructor accepts concurrency config
2. Add User Story 1 → Parallel execution works → **MVP ready!**
3. Add User Story 2 → Concurrency control verified
4. Add User Story 3 → Error handling robust
5. Polish → Documentation and edge cases

---

## Notes

- Primary file modified: `src/gepa_adk/adapters/adk_adapter.py`
- No changes to ports/protocols (hexagonal architecture preserved)
- `EvolutionConfig.max_concurrent_evals` already exists - adapter receives via constructor
- Uses validated patterns from ADK's `LocalEvalService` (see research.md)
- All tests follow three-layer strategy (ADR-005)

---

## Code Review Summary (2026-01-11)

**Reviewer**: Code Review Agent
**Status**: ✅ APPROVED with minor fixes applied

### Test Results

- **361 tests pass**, 1 skipped
- All 69 concurrency-specific tests pass
- No regressions introduced

### Issues Found & Fixed

| Issue | Location | Fix Applied |
|-------|----------|-------------|
| Missing `MockerFixture` import | `tests/contracts/test_adk_adapter_contracts.py` | Added `from pytest_mock import MockerFixture` |
| Unused variables `batch`, `candidate` | `tests/unit/adapters/test_adk_adapter.py:957-958` | Removed and updated comment |
| Incorrect `@pytest.mark.asyncio` on sync class | `tests/unit/adapters/test_adk_adapter.py:67` | Removed decorator from `TestADKAdapterConstructor` |

### Implementation Quality

✅ **Correct**: `asyncio.Semaphore` + `asyncio.gather(return_exceptions=True)` pattern
✅ **Correct**: Result ordering preserved (FR-009)
✅ **Correct**: Error handling with 0.0 score and error trajectory
✅ **Correct**: Structured logging at batch and example levels
✅ **Correct**: Constructor validation for `max_concurrent_evals < 1`
✅ **Correct**: Docstrings updated for new parameter

### Remaining Work

- [ ] **T036**: Documentation update in `docs/` still pending (non-blocking for feature)

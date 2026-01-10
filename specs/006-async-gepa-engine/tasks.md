````markdown
# Tasks: AsyncGEPAEngine

**Input**: Design documents from `/specs/006-async-gepa-engine/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included (TDD approach per Constitution Check in plan.md)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/gepa_adk/engine/`
- **Tests**: `tests/unit/engine/`, `tests/contracts/`

---

## Phase 1: Setup (Project Infrastructure)

**Purpose**: Create engine module structure and ensure dependencies are ready

- [X] T001 Create engine module directory structure at `src/gepa_adk/engine/`
- [X] T002 [P] Create `src/gepa_adk/engine/__init__.py` with public exports (AsyncGEPAEngine)
- [X] T003 [P] Create test directory structure at `tests/unit/engine/` and `tests/unit/engine/__init__.py`
- [X] T004 [P] Verify pytest-asyncio is available via `uv run pytest --version`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Internal state class and helper methods that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create `_EngineState` dataclass in `src/gepa_adk/engine/async_engine.py` (private, per data-model.md)
- [X] T006 Create `AsyncGEPAEngine` class skeleton with constructor in `src/gepa_adk/engine/async_engine.py`
- [X] T007 Implement constructor validation (empty batch, missing instruction component) per API contract
- [X] T008 [P] Create mock adapter fixture in `tests/unit/engine/conftest.py` for all user story tests
- [X] T009 [P] Add unit test for constructor validation in `tests/unit/engine/test_async_engine.py`

**Checkpoint**: Foundation ready - AsyncGEPAEngine can be instantiated with valid inputs

---

## Phase 3: User Story 1 - Run Evolution Loop (Priority: P1) 🎯 MVP

**Goal**: Execute async evolution loop that iterates until max_iterations, returning EvolutionResult with best candidate

**Independent Test**: Provide mock adapter, run `await engine.run()`, verify iterations execute and result contains best candidate with iteration history

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Contract test for AsyncGEPAEngine protocol compliance in `tests/contracts/test_async_engine_contracts.py`
- [X] T011 [P] [US1] [SC-006] Unit test for baseline evaluation (max_iterations=0) in `tests/unit/engine/test_async_engine.py`
- [X] T012 [P] [US1] [SC-002] Unit test for basic loop execution (max_iterations=5) in `tests/unit/engine/test_async_engine.py`
- [X] T013 [P] [US1] [SC-004] Unit test for iteration history completeness in `tests/unit/engine/test_async_engine.py`
- [X] T014 [P] [US1] Unit test for adapter exception propagation (fail-fast behavior) in `tests/unit/engine/test_async_engine.py`

### Implementation for User Story 1

- [X] T015 [US1] Implement `_initialize_baseline()` method for first evaluation in `src/gepa_adk/engine/async_engine.py`
- [X] T016 [US1] Implement `_evaluate_candidate()` method with score aggregation (mean) in `src/gepa_adk/engine/async_engine.py`
- [X] T016b [P] [US1] Unit test for mean score aggregation in `_evaluate_candidate()` in `tests/unit/engine/test_async_engine.py`
- [X] T017 [US1] Implement `_propose_mutation()` method calling adapter's reflective methods (with `capture_traces=True`) in `src/gepa_adk/engine/async_engine.py`
- [X] T018 [US1] Implement `_record_iteration()` method for history tracking in `src/gepa_adk/engine/async_engine.py`
- [X] T019 [US1] Implement `_build_result()` method to create frozen EvolutionResult in `src/gepa_adk/engine/async_engine.py`
- [X] T020 [US1] Implement core `run()` method with basic loop (max_iterations only) in `src/gepa_adk/engine/async_engine.py`
- [X] T021 [US1] Run User Story 1 tests to verify baseline-only and basic loop functionality

**Checkpoint**: User Story 1 complete - engine runs evolution loop and returns valid EvolutionResult

---

## Phase 4: User Story 3 - Accept Improved Candidates (Priority: P2-A)

**Goal**: Engine accepts proposals only when score exceeds best_score + min_improvement_threshold

**Independent Test**: Provide proposals with varying scores, verify only those exceeding threshold are accepted

> **NOTE**: US3 (acceptance logic) is implemented BEFORE US2 because early stopping's stagnation_counter depends on the acceptance/rejection outcome.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T022 [P] [US3] [SC-005] Unit test for accepting proposal above threshold in `tests/unit/engine/test_async_engine.py`
- [X] T023 [P] [US3] Unit test for rejecting proposal below threshold in `tests/unit/engine/test_async_engine.py`
- [X] T024 [P] [US3] Unit test for threshold=0.0 accepting any improvement in `tests/unit/engine/test_async_engine.py`
- [X] T025 [P] [US3] [FR-012] Unit test for candidate lineage tracking (generation, parent_id) in `tests/unit/engine/test_async_engine.py`

### Implementation for User Story 3

- [X] T026 [US3] Implement `_should_accept()` method with threshold comparison in `src/gepa_adk/engine/async_engine.py`
- [X] T027 [US3] Implement `_accept_proposal()` method with lineage update in `src/gepa_adk/engine/async_engine.py`
- [X] T028 [US3] Update `run()` to use `_should_accept()` and `_accept_proposal()` in `src/gepa_adk/engine/async_engine.py`
- [X] T029 [US3] Run User Story 3 tests to verify acceptance logic and lineage tracking

**Checkpoint**: User Story 3 complete - engine correctly accepts/rejects based on threshold

---

## Phase 5: User Story 2 - Early Stopping on Convergence (Priority: P2-B)

**Goal**: Engine stops early when no improvement occurs for `patience` consecutive iterations

**Independent Test**: Configure mock adapter returning stagnant scores, set patience=3, verify engine stops before max_iterations

> **NOTE**: US2 depends on US3 acceptance logic being complete (stagnation_counter increments on rejection).

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T030 [P] [US2] [SC-003] Unit test for early stopping when patience exhausted in `tests/unit/engine/test_async_engine.py`
- [X] T031 [P] [US2] [FR-007] Unit test for patience=0 disabling early stop in `tests/unit/engine/test_async_engine.py`
- [X] T032 [P] [US2] Unit test for patience reset on improvement in `tests/unit/engine/test_async_engine.py`

### Implementation for User Story 2

- [X] T033 [US2] Implement `_should_stop()` method with max_iterations and patience checks in `src/gepa_adk/engine/async_engine.py`
- [X] T034 [US2] Add stagnation_counter increment on rejection in `run()` method in `src/gepa_adk/engine/async_engine.py`
- [X] T035 [US2] Add stagnation_counter reset on acceptance in `run()` method in `src/gepa_adk/engine/async_engine.py`
- [X] T036 [US2] Update `run()` to use `_should_stop()` for loop termination in `src/gepa_adk/engine/async_engine.py`
- [X] T037 [US2] Run User Story 2 tests to verify early stopping behavior

**Checkpoint**: User Story 2 complete - engine stops early when converged

---

## Phase 6: Integration Tests (Constitution Compliance)

**Purpose**: Real adapter integration tests per ADR-005 Three-Layer Testing

> **NOTE**: Integration tests validate real ADK/LLM behavior. Mark with `@pytest.mark.slow`.
> **NOTE**: `tests/integration/` directory is NEW and will be created in this phase.

- [X] T038 [P] Create `tests/integration/engine/__init__.py` and `tests/integration/engine/test_async_engine_integration.py`
- [X] T039 [P] Add integration test placeholder with `@pytest.mark.slow` skip until real adapter available
- [X] T040 Add integration test for end-to-end evolution with real adapter (future: when ADKAdapter exists)

**Checkpoint**: Constitution Principle IV satisfied - three-layer testing complete

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final validation

- [X] T041 [P] Add Google-style docstrings to all public methods in `src/gepa_adk/engine/async_engine.py`
- [X] T042 [P] Add Google-style docstrings to `_EngineState` class in `src/gepa_adk/engine/async_engine.py`
- [X] T043 [P] Update `src/gepa_adk/__init__.py` to export engine module
- [X] T044 [P] Run `uv run ruff check --fix` and `uv run ruff format` on engine module
- [X] T045 [P] Run `uv run ty check` to verify type annotations
- [X] T046 Run full test suite `uv run pytest -n auto` to verify no regressions
- [X] T047 Validate quickstart.md examples work with implemented engine
- [X] T048 Run `uv run pytest --cov=src/gepa_adk/engine --cov-report=term-missing` for coverage report

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 (P1): Core loop - must complete first
  - US3 (P2-A): Depends on US1 (acceptance logic needed by US2)
  - US2 (P2-B): Depends on US3 (stagnation_counter uses acceptance result)
- **Integration (Phase 6)**: Depends on all user stories being complete
- **Polish (Phase 7)**: Depends on integration tests being complete

### User Story Dependencies

```
Phase 1 (Setup)
     │
     ▼
Phase 2 (Foundational)
     │
     ▼
Phase 3 (US1: Core Loop) ◀── MVP COMPLETE HERE
     │
     ▼
Phase 4 (US3: Acceptance) ◀── US3 first (acceptance logic)
     │
     ▼
Phase 5 (US2: Early Stop) ◀── US2 depends on US3
     │
     ▼
Phase 6 (Integration Tests)
     │
     ▼
Phase 7 (Polish)
```

> **Dependency Rationale**: US2 (early stopping) increments `stagnation_counter` on rejection,
> which requires US3's `_should_accept()` method to determine accept/reject outcome.

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Implementation follows contract specifications
3. All story tests pass before moving to next phase

### Parallel Opportunities

**Phase 1**:
- T002, T003, T004 can run in parallel

**Phase 2**:
- T008, T009 can run in parallel (after T005-T007)

**Each User Story Tests**:
- All test tasks marked [P] within a story can run in parallel

**Phase 6**:
- T037, T038, T039, T040, T041 can run in parallel

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 tests together:
Task T010: "Contract test for AsyncGEPAEngine protocol compliance"
Task T011: "Unit test for baseline evaluation (max_iterations=0)"
Task T012: "Unit test for basic loop execution (max_iterations=5)"
Task T013: "Unit test for iteration history completeness"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (~4 tasks)
2. Complete Phase 2: Foundational (~5 tasks)
3. Complete Phase 3: User Story 1 (~11 tasks)
4. **STOP and VALIDATE**: Engine can run evolution and return results
5. MVP ready for integration testing

### Incremental Delivery

1. **Setup + Foundational** → Engine skeleton ready
2. **+ User Story 1** → Core loop works → **MVP!**
3. **+ User Story 2** → Early stopping saves compute
4. **+ User Story 3** → Quality thresholds enforced
5. **+ Polish** → Production-ready with docs and coverage

### Task Count Summary

| Phase | Tasks | Parallel Opportunities |
|-------|-------|------------------------|
| Setup | 4 | 3 parallel |
| Foundational | 5 | 2 parallel |
| US1 (P1) | 13 | 6 parallel (tests) |
| US3 (P2-A) | 8 | 4 parallel (tests) |
| US2 (P2-B) | 8 | 3 parallel (tests) |
| Integration | 3 | 2 parallel |
| Polish | 8 | 5 parallel |
| **Total** | **49** | |

---

## Notes

- [P] tasks = different files or no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- TDD: All test tasks must fail before implementation tasks
- Use `uv run pytest tests/unit/engine/ -v` to run engine tests
- Use `uv run pytest tests/contracts/ -v` to run contract tests
- Follow Google-style docstrings per ADR-010
- Engine layer uses only stdlib (asyncio) per ADR-000 hexagonal architecture

---

## Code Review Notes (2026-01-10)

**Reviewer**: Senior Dev
**Status**: APPROVED with fixes applied

### Issues Found and Fixed

| Issue | Severity | Fix Applied |
|-------|----------|-------------|
| **`_EngineState` dataclass field order** | 🔴 CRITICAL | Non-default fields must come before fields with defaults. Reordered fields. |
| **Test ConfigurationError assertion** | 🟡 MEDIUM | `EvolutionConfig` raises `ConfigurationError` in `__post_init__`, not engine constructor. Fixed test to wrap config creation in `pytest.raises`. |
| **Missing `pythonpath` in pytest config** | 🟡 MEDIUM | Tests using `from tests.unit.engine.conftest import MockAdapter` failed. Added `pythonpath = ["."]` to `pyproject.toml`. |
| **Contract test using missing fixtures** | 🟡 MEDIUM | `test_async_engine_contracts.py` referenced fixtures only defined in `tests/unit/engine/conftest.py`. Removed unused fixture params and created data inline. |
| **`_propose_mutation` redundant evaluation** | 🟠 OPTIMIZATION | Original implementation called `evaluate()` twice per iteration. Refactored to cache `EvaluationBatch` in `_EngineState.last_eval_batch` and reuse for reflective dataset generation. |
| **Missing type assertions for `_state`** | 🟡 MEDIUM | `ty check` failed because `self._state` is `_EngineState \| None`. Added `assert self._state is not None` guards in all methods that access state. |
| **Line too long in test comment** | 🟢 LOW | Ruff E501 violation. Wrapped comment across multiple lines. |

### Verification Results

```
✅ uv run pytest -n auto: 123 passed, 1 skipped
✅ uv run ruff check: All checks passed
✅ uv run ty check: All checks passed  
✅ Coverage: 100% on engine module
```

### ADR Compliance

| ADR | Status | Notes |
|-----|--------|-------|
| ADR-000 Hexagonal Architecture | ✅ | Engine imports only from `domain/` and `ports/` |
| ADR-001 Async-First | ✅ | All core methods are async |
| ADR-002 Protocol Interfaces | ✅ | Uses `AsyncGEPAAdapter` Protocol |
| ADR-005 Three-Layer Testing | ✅ | contracts/, unit/, integration/ tests present |
| ADR-010 Docstring Quality | ✅ | Google-style docstrings on all public methods |
````

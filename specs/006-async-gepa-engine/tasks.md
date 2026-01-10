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

- [ ] T001 Create engine module directory structure at `src/gepa_adk/engine/`
- [ ] T002 [P] Create `src/gepa_adk/engine/__init__.py` with public exports (AsyncGEPAEngine)
- [ ] T003 [P] Create test directory structure at `tests/unit/engine/` and `tests/unit/engine/__init__.py`
- [ ] T004 [P] Verify pytest-asyncio is available via `uv run pytest --version`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Internal state class and helper methods that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Create `_EngineState` dataclass in `src/gepa_adk/engine/async_engine.py` (private, per data-model.md)
- [ ] T006 Create `AsyncGEPAEngine` class skeleton with constructor in `src/gepa_adk/engine/async_engine.py`
- [ ] T007 Implement constructor validation (empty batch, missing instruction component) per API contract
- [ ] T008 [P] Create mock adapter fixture in `tests/unit/engine/conftest.py` for all user story tests
- [ ] T009 [P] Add unit test for constructor validation in `tests/unit/engine/test_async_engine.py`

**Checkpoint**: Foundation ready - AsyncGEPAEngine can be instantiated with valid inputs

---

## Phase 3: User Story 1 - Run Evolution Loop (Priority: P1) 🎯 MVP

**Goal**: Execute async evolution loop that iterates until max_iterations, returning EvolutionResult with best candidate

**Independent Test**: Provide mock adapter, run `await engine.run()`, verify iterations execute and result contains best candidate with iteration history

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Contract test for AsyncGEPAEngine protocol compliance in `tests/contracts/test_async_engine_contracts.py`
- [ ] T011 [P] [US1] [SC-006] Unit test for baseline evaluation (max_iterations=0) in `tests/unit/engine/test_async_engine.py`
- [ ] T012 [P] [US1] [SC-002] Unit test for basic loop execution (max_iterations=5) in `tests/unit/engine/test_async_engine.py`
- [ ] T013 [P] [US1] [SC-004] Unit test for iteration history completeness in `tests/unit/engine/test_async_engine.py`
- [ ] T014 [P] [US1] Unit test for adapter exception propagation (fail-fast behavior) in `tests/unit/engine/test_async_engine.py`

### Implementation for User Story 1

- [ ] T015 [US1] Implement `_initialize_baseline()` method for first evaluation in `src/gepa_adk/engine/async_engine.py`
- [ ] T016 [US1] Implement `_evaluate_candidate()` method with score aggregation (mean) in `src/gepa_adk/engine/async_engine.py`
- [ ] T017 [US1] Implement `_propose_mutation()` method calling adapter's reflective methods (with `capture_traces=True`) in `src/gepa_adk/engine/async_engine.py`
- [ ] T018 [US1] Implement `_record_iteration()` method for history tracking in `src/gepa_adk/engine/async_engine.py`
- [ ] T019 [US1] Implement `_build_result()` method to create frozen EvolutionResult in `src/gepa_adk/engine/async_engine.py`
- [ ] T020 [US1] Implement core `run()` method with basic loop (max_iterations only) in `src/gepa_adk/engine/async_engine.py`
- [ ] T021 [US1] Run User Story 1 tests to verify baseline-only and basic loop functionality

**Checkpoint**: User Story 1 complete - engine runs evolution loop and returns valid EvolutionResult

---

## Phase 4: User Story 3 - Accept Improved Candidates (Priority: P2-A)

**Goal**: Engine accepts proposals only when score exceeds best_score + min_improvement_threshold

**Independent Test**: Provide proposals with varying scores, verify only those exceeding threshold are accepted

> **NOTE**: US3 (acceptance logic) is implemented BEFORE US2 because early stopping's stagnation_counter depends on the acceptance/rejection outcome.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T022 [P] [US3] [SC-005] Unit test for accepting proposal above threshold in `tests/unit/engine/test_async_engine.py`
- [ ] T023 [P] [US3] Unit test for rejecting proposal below threshold in `tests/unit/engine/test_async_engine.py`
- [ ] T024 [P] [US3] Unit test for threshold=0.0 accepting any improvement in `tests/unit/engine/test_async_engine.py`
- [ ] T025 [P] [US3] [FR-012] Unit test for candidate lineage tracking (generation, parent_id) in `tests/unit/engine/test_async_engine.py`

### Implementation for User Story 3

- [ ] T026 [US3] Implement `_should_accept()` method with threshold comparison in `src/gepa_adk/engine/async_engine.py`
- [ ] T027 [US3] Implement `_accept_proposal()` method with lineage update in `src/gepa_adk/engine/async_engine.py`
- [ ] T028 [US3] Update `run()` to use `_should_accept()` and `_accept_proposal()` in `src/gepa_adk/engine/async_engine.py`
- [ ] T029 [US3] Run User Story 3 tests to verify acceptance logic and lineage tracking

**Checkpoint**: User Story 3 complete - engine correctly accepts/rejects based on threshold

---

## Phase 5: User Story 2 - Early Stopping on Convergence (Priority: P2-B)

**Goal**: Engine stops early when no improvement occurs for `patience` consecutive iterations

**Independent Test**: Configure mock adapter returning stagnant scores, set patience=3, verify engine stops before max_iterations

> **NOTE**: US2 depends on US3 acceptance logic being complete (stagnation_counter increments on rejection).

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T030 [P] [US2] [SC-003] Unit test for early stopping when patience exhausted in `tests/unit/engine/test_async_engine.py`
- [ ] T031 [P] [US2] [FR-007] Unit test for patience=0 disabling early stop in `tests/unit/engine/test_async_engine.py`
- [ ] T032 [P] [US2] Unit test for patience reset on improvement in `tests/unit/engine/test_async_engine.py`

### Implementation for User Story 2

- [ ] T033 [US2] Implement `_should_stop()` method with max_iterations and patience checks in `src/gepa_adk/engine/async_engine.py`
- [ ] T034 [US2] Add stagnation_counter increment on rejection in `run()` method in `src/gepa_adk/engine/async_engine.py`
- [ ] T035 [US2] Add stagnation_counter reset on acceptance in `run()` method in `src/gepa_adk/engine/async_engine.py`
- [ ] T036 [US2] Update `run()` to use `_should_stop()` for loop termination in `src/gepa_adk/engine/async_engine.py`
- [ ] T037-a [US2] Run User Story 2 tests to verify early stopping behavior

**Checkpoint**: User Story 2 complete - engine stops early when converged

---

## Phase 6: Integration Tests (Constitution Compliance)

**Purpose**: Real adapter integration tests per ADR-005 Three-Layer Testing

> **NOTE**: Integration tests validate real ADK/LLM behavior. Mark with `@pytest.mark.slow`.

- [ ] T037 [P] Create `tests/integration/engine/__init__.py` and `tests/integration/engine/test_async_engine_integration.py`
- [ ] T038 [P] Add integration test placeholder with `@pytest.mark.slow` skip until real adapter available
- [ ] T039 Add integration test for end-to-end evolution with real adapter (future: when ADKAdapter exists)

**Checkpoint**: Constitution Principle IV satisfied - three-layer testing complete

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final validation

- [ ] T040 [P] Add Google-style docstrings to all public methods in `src/gepa_adk/engine/async_engine.py`
- [ ] T041 [P] Add Google-style docstrings to `_EngineState` class in `src/gepa_adk/engine/async_engine.py`
- [ ] T042 [P] Update `src/gepa_adk/__init__.py` to export engine module
- [ ] T043 [P] Run `uv run ruff check --fix` and `uv run ruff format` on engine module
- [ ] T044 [P] Run `uv run ty check` to verify type annotations
- [ ] T045 Run full test suite `uv run pytest -n auto` to verify no regressions
- [ ] T046 Validate quickstart.md examples work with implemented engine
- [ ] T047 Run `uv run pytest --cov=src/gepa_adk/engine --cov-report=term-missing` for coverage report

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 (P1): Core loop - must complete first
  - US2 (P2): Depends on US1 (uses loop structure)
  - US3 (P3): Depends on US1 (uses loop structure)
- **Polish (Phase 6)**: Depends on all user stories being complete

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
| US1 (P1) | 12 | 5 parallel (tests) |
| US3 (P2-A) | 8 | 4 parallel (tests) |
| US2 (P2-B) | 7 | 3 parallel (tests) |
| Integration | 3 | 2 parallel |
| Polish | 8 | 5 parallel |
| **Total** | **47** | |

---

## Notes

- [P] tasks = different files or no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- TDD: All test tasks must fail before implementation tasks
- Use `uv run pytest tests/unit/engine/ -v` to run engine tests
- Use `uv run pytest tests/contracts/ -v` to run contract tests
- Follow Google-style docstrings per ADR-010
- Engine layer uses only stdlib (asyncio) per ADR-000 hexagonal architecture
````

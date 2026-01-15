# Tasks: Objective Scores Passthrough

**Input**: Design documents from `/specs/026-objective-scores/`
**Prerequisites**: plan.md (complete), spec.md (complete), data-model.md (complete), contracts/ (complete)

**Tests**: Three-layer testing is mandated by the project constitution (ADR-005). Contract, unit, and integration tests are included.

**Organization**: Tasks are grouped by user story. Note that US1 and US2 are both P1 priority and tightly coupled (backward compatibility is required for the core feature), so they share implementation but have separate tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root (hexagonal architecture)

---

## Phase 1: Setup

**Purpose**: Verify existing infrastructure supports the feature

- [ ] T001 Verify EvaluationBatch already has objective_scores field in src/gepa_adk/ports/adapter.py (read-only check)
- [ ] T002 Review existing _EngineState structure in src/gepa_adk/engine/async_engine.py to identify insertion points

---

## Phase 2: Foundational (Domain Model Updates)

**Purpose**: Add objective_scores fields to domain models - MUST complete before engine updates

**⚠️ CRITICAL**: Engine changes depend on domain model fields existing

- [ ] T003 [P] Add objective_scores field to IterationRecord in src/gepa_adk/domain/models.py
- [ ] T004 [P] Add objective_scores field to EvolutionResult in src/gepa_adk/domain/models.py
- [ ] T005 Update IterationRecord docstring with objective_scores documentation in src/gepa_adk/domain/models.py
- [ ] T006 Update EvolutionResult docstring with objective_scores documentation in src/gepa_adk/domain/models.py

**Checkpoint**: Domain models ready - engine implementation can begin

---

## Phase 3: User Story 1 - Access Objective Scores in Results (Priority: P1) 🎯 MVP

**Goal**: Pass through objective_scores from adapter evaluations to engine state, iteration history, and evolution results

**Independent Test**: Run evolution with mock adapter returning objective_scores, verify they appear in result.objective_scores and iteration_history[*].objective_scores

### Contract Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T007 [P] [US1] Contract test for IterationRecord with objective_scores in tests/contracts/test_objective_scores_models.py
- [ ] T008 [P] [US1] Contract test for EvolutionResult with objective_scores in tests/contracts/test_objective_scores_models.py

### Unit Tests for User Story 1

- [ ] T009 [P] [US1] Unit test for _EngineState with best_objective_scores in tests/unit/engine/test_objective_scores_engine.py
- [ ] T010 [P] [US1] Unit test for _record_iteration passing objective_scores in tests/unit/engine/test_objective_scores_engine.py
- [ ] T011 [P] [US1] Unit test for _build_result including objective_scores in tests/unit/engine/test_objective_scores_engine.py
- [ ] T012 [P] [US1] Unit test for _initialize_baseline extracting objective_scores in tests/unit/engine/test_objective_scores_engine.py
- [ ] T013 [P] [US1] Unit test for _accept_proposal updating best_objective_scores in tests/unit/engine/test_objective_scores_engine.py

### Implementation for User Story 1

- [ ] T014 [US1] Add best_objective_scores field to _EngineState in src/gepa_adk/engine/async_engine.py
- [ ] T015 [US1] Update _EngineState docstring with best_objective_scores documentation in src/gepa_adk/engine/async_engine.py
- [ ] T016 [US1] Update _initialize_baseline to extract and store objective_scores from scoring_batch in src/gepa_adk/engine/async_engine.py
- [ ] T017 [US1] Update _record_iteration signature to accept objective_scores parameter in src/gepa_adk/engine/async_engine.py
- [ ] T018 [US1] Update _record_iteration to pass objective_scores to IterationRecord in src/gepa_adk/engine/async_engine.py
- [ ] T019 [US1] Update _accept_proposal to store objective_scores in _EngineState.best_objective_scores in src/gepa_adk/engine/async_engine.py
- [ ] T020 [US1] Update _build_result to include best_objective_scores in EvolutionResult in src/gepa_adk/engine/async_engine.py
- [ ] T021 [US1] Update run() method to pass objective_scores from scoring_batch to _record_iteration in src/gepa_adk/engine/async_engine.py

**Checkpoint**: User Story 1 complete - objective_scores flow from adapter to results

---

## Phase 4: User Story 2 - Backward Compatibility (Priority: P1)

**Goal**: Ensure existing adapters without objective_scores continue to work without modification

**Independent Test**: Run evolution with mock adapter NOT returning objective_scores, verify evolution completes successfully with result.objective_scores == None

### Contract Tests for User Story 2

- [ ] T022 [P] [US2] Contract test for IterationRecord without objective_scores (backward compat) in tests/contracts/test_objective_scores_models.py
- [ ] T023 [P] [US2] Contract test for EvolutionResult without objective_scores (backward compat) in tests/contracts/test_objective_scores_models.py

### Unit Tests for User Story 2

- [ ] T024 [P] [US2] Unit test for engine handling None objective_scores in tests/unit/engine/test_objective_scores_engine.py
- [ ] T025 [P] [US2] Unit test for _record_iteration with None objective_scores in tests/unit/engine/test_objective_scores_engine.py
- [ ] T026 [P] [US2] Unit test for _build_result with None objective_scores in tests/unit/engine/test_objective_scores_engine.py

### Edge Case Tests for User Story 2

- [ ] T026a [P] [US2] Unit test for partially populated objective_scores (some examples have scores, others None) in tests/unit/engine/test_objective_scores_engine.py
- [ ] T026b [P] [US2] Unit test for empty dict objective_scores ({}) passthrough in tests/unit/engine/test_objective_scores_engine.py
- [ ] T026c [P] [US2] Unit test for heterogeneous keys across examples in tests/unit/engine/test_objective_scores_engine.py

### Implementation for User Story 2

> **NOTE**: Most backward compatibility is achieved via None defaults in Phase 2. These tasks verify edge cases.

- [ ] T027 [US2] Verify _initialize_baseline handles missing objective_scores gracefully in src/gepa_adk/engine/async_engine.py
- [ ] T028 [US2] Verify _accept_proposal handles None objective_scores in src/gepa_adk/engine/async_engine.py

**Checkpoint**: User Story 2 complete - backward compatibility verified

---

## Phase 5: Integration & Polish

**Purpose**: End-to-end validation and cross-cutting improvements

### Integration Tests

- [ ] T029 [P] Integration test for full evolution with objective_scores in tests/integration/test_objective_scores_e2e.py
- [ ] T030 [P] Integration test for full evolution without objective_scores in tests/integration/test_objective_scores_e2e.py

### Polish

- [ ] T031 Run existing test suite to verify no regressions (pytest tests/)
- [ ] T032 Run linting and type checking (ruff check . && ty check)
- [ ] T033 Validate quickstart.md code examples work correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS engine implementation
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion (can run parallel with US1)
- **Integration (Phase 5)**: Depends on both user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Requires domain model fields from Phase 2
- **User Story 2 (P1)**: Requires domain model fields from Phase 2, independent of US1 implementation

### Within Each User Story

- Contract tests MUST be written and FAIL before implementation
- Unit tests MUST be written and FAIL before implementation
- Domain model changes before engine changes
- Engine state changes before method updates
- Method signature changes before call site updates

### Parallel Opportunities

**Phase 2 (Foundational):**
```
T003 (IterationRecord field) || T004 (EvolutionResult field)
```

**Phase 3 (US1 Tests):**
```
T007 || T008 || T009 || T010 || T011 || T012 || T013
```

**Phase 4 (US2 Tests):**
```
T022 || T023 || T024 || T025 || T026 || T026a || T026b || T026c
```

**Phase 5 (Integration):**
```
T029 || T030
```

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all contract tests for US1 together:
Task: "Contract test for IterationRecord with objective_scores in tests/contracts/test_objective_scores_models.py"
Task: "Contract test for EvolutionResult with objective_scores in tests/contracts/test_objective_scores_models.py"

# Launch all unit tests for US1 together:
Task: "Unit test for _EngineState with best_objective_scores in tests/unit/engine/test_objective_scores_engine.py"
Task: "Unit test for _record_iteration passing objective_scores in tests/unit/engine/test_objective_scores_engine.py"
Task: "Unit test for _build_result including objective_scores in tests/unit/engine/test_objective_scores_engine.py"
Task: "Unit test for _initialize_baseline extracting objective_scores in tests/unit/engine/test_objective_scores_engine.py"
Task: "Unit test for _accept_proposal updating best_objective_scores in tests/unit/engine/test_objective_scores_engine.py"
```

---

## Implementation Strategy

### MVP First (Both User Stories Required)

1. Complete Phase 1: Setup (verification)
2. Complete Phase 2: Foundational (domain model fields)
3. Complete Phase 3: User Story 1 (objective_scores passthrough)
4. Complete Phase 4: User Story 2 (backward compatibility)
5. **STOP and VALIDATE**: Run all tests, verify both stories work
6. Complete Phase 5: Integration tests

### Incremental Delivery

1. Complete Setup + Foundational → Domain models ready
2. Add US1 tests (should fail) → Write implementation → Tests pass
3. Add US2 tests (should fail) → Verify implementation handles None → Tests pass
4. Add integration tests → Verify end-to-end
5. Run full test suite → No regressions

### Critical Path

```
T001 → T002 → T003/T004 → T005/T006 → T007-T013 → T014-T021 → T022-T028 → T029-T033
```

---

## Summary

| Category | Count |
|----------|-------|
| Setup tasks | 2 |
| Foundational tasks | 4 |
| US1 tasks (tests + impl) | 15 |
| US2 tasks (tests + impl) | 10 |
| Integration tasks | 5 |
| **Total** | **36** |

| User Story | Test Tasks | Implementation Tasks |
|------------|------------|---------------------|
| US1 (Passthrough) | 7 | 8 |
| US2 (Backward Compat) | 8 | 2 |

---

## Notes

- [P] tasks = different files, no dependencies - can run in parallel
- [Story] label maps task to specific user story for traceability
- US1 and US2 are both P1 and must be delivered together
- Domain model changes are backward compatible via None defaults
- All engine changes are internal - no public API changes
- Existing tests must continue to pass (backward compatibility)
- Constitution requires three-layer testing (contract, unit, integration)

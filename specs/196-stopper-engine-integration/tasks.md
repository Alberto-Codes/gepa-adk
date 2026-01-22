# Tasks: Wire stop_callbacks into AsyncGEPAEngine

**Input**: Design documents from `/specs/196-stopper-engine-integration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included as specified in plan.md (three-layer testing strategy: unit, contracts, integration per ADR-005).

**Documentation**: Internal engine change - no user-facing API changes. Existing stopper documentation covers usage. Per plan.md documentation scope: "N/A - Internal engine change - no user-facing API changes requiring guide updates."

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add engine state attributes required for StopperState construction

- [X] T001 Add `_start_time: float | None = None` attribute to AsyncGEPAEngine in src/gepa_adk/engine/async_engine.py
- [X] T002 Add `_total_evaluations: int = 0` attribute to AsyncGEPAEngine in src/gepa_adk/engine/async_engine.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add `_build_stopper_state()` method to AsyncGEPAEngine that constructs StopperState snapshot in src/gepa_adk/engine/async_engine.py
- [X] T004 Initialize `_start_time = time.monotonic()` at the start of `run()` method in src/gepa_adk/engine/async_engine.py
- [X] T005 Increment `_total_evaluations` by batch size after each `adapter.evaluate()` call in src/gepa_adk/engine/async_engine.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Custom Stopper Invocation (Priority: P1) 🎯 MVP

**Goal**: Stoppers in `stop_callbacks` are checked during evolution and can terminate the loop

**Independent Test**: Provide a mock stopper that tracks invocation count and verify it receives valid state each iteration

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US1] Unit test: stopper invoked each iteration in tests/unit/engine/test_stopper_integration.py
- [X] T007 [P] [US1] Unit test: stopper receives valid StopperState in tests/unit/engine/test_stopper_integration.py
- [X] T008 [P] [US1] Unit test: stopper returning True stops evolution in tests/unit/engine/test_stopper_integration.py
- [X] T009 [P] [US1] Unit test: empty stop_callbacks has no effect in tests/unit/engine/test_stopper_integration.py

### Implementation for User Story 1

- [X] T010 [US1] Extend `_should_stop()` to iterate over `config.stop_callbacks` and invoke each stopper with StopperState in src/gepa_adk/engine/async_engine.py
- [X] T011 [US1] Return True from `_should_stop()` when any stopper returns True (short-circuit) in src/gepa_adk/engine/async_engine.py
- [X] T012 [US1] Handle `stop_callbacks` being None or empty without error in src/gepa_adk/engine/async_engine.py
- [X] T013 [US1] Log stopper trigger with structlog including stopper class name and iteration in src/gepa_adk/engine/async_engine.py

**Checkpoint**: User Story 1 complete - stoppers are invoked and can stop evolution

---

## Phase 4: User Story 2 - Accurate State Tracking (Priority: P1)

**Goal**: Stoppers receive accurate elapsed time and evaluation counts in StopperState

**Independent Test**: Verify elapsed_seconds increases monotonically and total_evaluations accumulates correctly

### Tests for User Story 2

- [X] T014 [P] [US2] Integration test: TimeoutStopper triggers after elapsed time in tests/integration/test_stopper_integration.py
- [X] T015 [P] [US2] Unit test: elapsed_seconds accuracy within 50ms in tests/unit/engine/test_stopper_integration.py
- [X] T016 [P] [US2] Unit test: total_evaluations matches sum of batch sizes in tests/unit/engine/test_stopper_integration.py

### Implementation for User Story 2

- [X] T017 [US2] Ensure `_build_stopper_state()` computes `elapsed_seconds = time.monotonic() - self._start_time` in src/gepa_adk/engine/async_engine.py
- [X] T018 [US2] Ensure `_build_stopper_state()` uses `self._total_evaluations` for total_evaluations field in src/gepa_adk/engine/async_engine.py
- [X] T019 [US2] Ensure `_build_stopper_state()` derives candidates_count from `len(self._pareto_state.candidates)` in src/gepa_adk/engine/async_engine.py

**Checkpoint**: User Story 2 complete - state tracking is accurate

---

## Phase 5: User Story 3 - SignalStopper Lifecycle Management (Priority: P2)

**Goal**: SignalStopper setup/cleanup are called for proper signal handler management

**Independent Test**: Verify setup() is called before loop and cleanup() after (even on exceptions)

### Tests for User Story 3

- [X] T020 [P] [US3] Integration test: SignalStopper setup() called before loop in tests/integration/test_stopper_integration.py
- [X] T021 [P] [US3] Integration test: SignalStopper cleanup() called after loop in tests/integration/test_stopper_integration.py
- [X] T022 [P] [US3] Integration test: cleanup() called even on exception in tests/integration/test_stopper_integration.py

### Implementation for User Story 3

- [X] T023 [US3] Add lifecycle setup: call `setup()` on stoppers that have it (via hasattr) before evolution loop in `run()` method in src/gepa_adk/engine/async_engine.py
- [X] T024 [US3] Add lifecycle cleanup: call `cleanup()` on stoppers that have it in `finally` block of `run()` method in src/gepa_adk/engine/async_engine.py
- [X] T025 [US3] Call cleanup() in reverse order of setup() calls per contract in src/gepa_adk/engine/async_engine.py
- [X] T026 [US3] If cleanup() raises exception, log error and continue cleanup for remaining stoppers in src/gepa_adk/engine/async_engine.py

**Checkpoint**: User Story 3 complete - lifecycle management works correctly

---

## Phase 6: User Story 4 - Multiple Stopper Coordination (Priority: P2)

**Goal**: Multiple stoppers work together with first-to-fire winning

**Independent Test**: Configure multiple stoppers with different triggers and verify first match causes termination

### Tests for User Story 4

- [X] T027 [P] [US4] Unit test: multiple stoppers - short circuit on first True in tests/unit/engine/test_stopper_integration.py
- [X] T028 [P] [US4] Unit test: all stoppers checked when none return True in tests/unit/engine/test_stopper_integration.py
- [X] T029 [P] [US4] Integration test: first stopper to trigger is logged in tests/integration/test_stopper_integration.py

### Implementation for User Story 4

- [X] T030 [US4] Ensure stoppers are checked in list order in `_should_stop()` in src/gepa_adk/engine/async_engine.py
- [X] T031 [US4] Ensure short-circuit evaluation stops checking after first True in src/gepa_adk/engine/async_engine.py

**Checkpoint**: User Story 4 complete - multiple stoppers coordinate correctly

---

## Phase 7: Verification & Cross-Cutting Concerns

**Purpose**: Final verification and edge case handling

### Edge Case Handling

- [X] T032 Handle stopper exception gracefully: log error and continue or terminate safely in src/gepa_adk/engine/async_engine.py
- [X] T033 Ensure built-in conditions (max_iterations, patience) are checked BEFORE custom stoppers in src/gepa_adk/engine/async_engine.py

### Verification

- [X] T034 Run full test suite: `uv run pytest tests/unit/engine/test_stopper_integration.py tests/integration/test_stopper_integration.py -v`
- [X] T035 Verify backward compatibility: evolution with empty stop_callbacks behaves identically to before
- [X] T036 Run quickstart.md validation examples

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001, T002) - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion - can run parallel with US1
- **User Story 3 (Phase 5)**: Depends on Foundational completion - can run parallel with US1, US2
- **User Story 4 (Phase 6)**: Depends on US1 completion (needs stopper checking in place)
- **Verification (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - Core stopper invocation
- **User Story 2 (P1)**: Can start after Foundational - Parallel with US1, focuses on state accuracy
- **User Story 3 (P2)**: Can start after Foundational - Parallel with US1/US2, focuses on lifecycle
- **User Story 4 (P2)**: Requires US1 completion - Builds on stopper checking logic

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation tasks are sequential within the story
- Story complete before marking checkpoint done

### Parallel Opportunities

**Phase 2 (Foundational)**:
```bash
# All foundational tasks are sequential (same file, dependent logic)
```

**Phase 3 (User Story 1 Tests)**:
```bash
Task: T006 "Unit test: stopper invoked each iteration"
Task: T007 "Unit test: stopper receives valid StopperState"
Task: T008 "Unit test: stopper returning True stops evolution"
Task: T009 "Unit test: empty stop_callbacks has no effect"
# All can run in parallel (different test functions, same file)
```

**Phase 4 (User Story 2 Tests)**:
```bash
Task: T014 "Integration test: TimeoutStopper triggers"
Task: T015 "Unit test: elapsed_seconds accuracy"
Task: T016 "Unit test: total_evaluations matches batch sizes"
# All can run in parallel
```

**Phase 5 (User Story 3 Tests)**:
```bash
Task: T020 "Integration test: setup() called before loop"
Task: T021 "Integration test: cleanup() called after loop"
Task: T022 "Integration test: cleanup() called on exception"
# All can run in parallel
```

**Phase 6 (User Story 4 Tests)**:
```bash
Task: T027 "Unit test: short circuit on first True"
Task: T028 "Unit test: all stoppers checked when none True"
Task: T029 "Integration test: first trigger logged"
# All can run in parallel
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T005)
3. Complete Phase 3: User Story 1 - Core stopper invocation
4. Complete Phase 4: User Story 2 - Accurate state tracking
5. **STOP and VALIDATE**: Run tests, verify stoppers work
6. This provides functional stopper support

### Incremental Delivery

1. **MVP**: Setup + Foundational + US1 + US2 → Basic stopper support works
2. **+US3**: Add SignalStopper lifecycle → Graceful Ctrl+C handling
3. **+US4**: Add multi-stopper coordination → Full feature complete
4. **Verification**: Edge cases and final validation

---

## Notes

- All modifications are in single file: `src/gepa_adk/engine/async_engine.py` (~50 lines)
- Tests split between: `tests/unit/engine/test_stopper_integration.py` and `tests/integration/test_stopper_integration.py` (~100 lines total)
- Scope is intentionally small per plan.md - this is wiring, not new functionality
- Backward compatibility: empty `stop_callbacks` must have zero behavior change
- Performance: stoppers checked after built-in conditions for fast path

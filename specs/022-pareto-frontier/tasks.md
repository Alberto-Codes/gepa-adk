# Tasks: Pareto Frontier Tracking and Candidate Selection

**Input**: Design documents from `/specs/022-pareto-frontier/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Three-layer testing required per ADR-005 (contract, unit, integration)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project structure for Pareto frontier feature

- [X] T001 [P] Create selector module at src/gepa_adk/adapters/candidate_selector.py
- [X] T002 [P] Verify existing test directories exist (tests/contracts/, tests/unit/, tests/integration/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types and protocols that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add FrontierType enum to src/gepa_adk/domain/types.py with values INSTANCE, OBJECTIVE, HYBRID, CARTESIAN (only INSTANCE implemented)
- [X] T004 Create CandidateSelectorProtocol (async def select_candidate(...)) in src/gepa_adk/ports/selector.py
- [X] T005 Export CandidateSelectorProtocol from src/gepa_adk/ports/__init__.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Pareto Frontier Candidate Selection (Priority: P1) 🎯 MVP

**Goal**: Enable evolution to select candidates from a Pareto frontier instead of always picking the single best candidate

**Independent Test**: Run evolution with multiple validation examples and verify that candidates with different strengths are selected proportionally, not just the highest-scoring one

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US1] Contract test for async CandidateSelectorProtocol in tests/contracts/test_candidate_selector_protocol.py
- [X] T007 [P] [US1] Unit tests for ParetoFrontier in tests/unit/test_pareto_state.py (frontier methods only)
- [X] T008 [P] [US1] Unit tests for ParetoState in tests/unit/test_pareto_state.py (state methods)
- [X] T009 [P] [US1] Unit tests for ParetoCandidateSelector in tests/unit/test_candidate_selectors.py
- [X] T009a [P] [US1] Unit test for empty frontier handling (NoCandidateAvailableError) in tests/unit/test_pareto_state.py
- [X] T009b [P] [US1] Unit test for identical scores (equal selection probability) in tests/unit/test_pareto_state.py
- [X] T009c [P] [US1] Unit test for dominant candidate frontier reduction in tests/unit/test_pareto_state.py
- [X] T009d [P] [US1] Add NoCandidateAvailableError to src/gepa_adk/domain/exceptions.py and export it

### Implementation for User Story 1

- [X] T010 [P] [US1] Implement ParetoFrontier dataclass in src/gepa_adk/domain/state.py with update(), get_non_dominated(), get_selection_weights() methods
- [X] T011 [US1] Implement ParetoState dataclass in src/gepa_adk/domain/state.py with add_candidate(), get_average_score(), update_best_average() methods (depends on T010)
- [X] T012 [US1] Export ParetoState and ParetoFrontier from src/gepa_adk/domain/__init__.py
- [X] T013 [US1] Implement ParetoCandidateSelector (async select_candidate) in src/gepa_adk/adapters/candidate_selector.py
- [X] T014 [US1] Export ParetoCandidateSelector from src/gepa_adk/adapters/__init__.py
- [X] T015 [US1] Modify AsyncGEPAEngine.__init__ to accept optional candidate_selector parameter in src/gepa_adk/engine/async_engine.py
- [X] T016 [US1] Modify AsyncGEPAEngine._initialize_baseline() to create ParetoState when selector provided in src/gepa_adk/engine/async_engine.py
- [X] T017 [US1] Modify AsyncGEPAEngine._propose_mutation() to await selector for parent selection in src/gepa_adk/engine/async_engine.py
- [X] T018 [US1] Modify AsyncGEPAEngine._accept_proposal() to update ParetoState in src/gepa_adk/engine/async_engine.py
- [X] T019 [US1] Add candidate_selector parameter to evolve() function in src/gepa_adk/api.py
- [X] T020 [US1] Add candidate_selector parameter to evolve_sync() function in src/gepa_adk/api.py
- [X] T021 [US1] Add structlog events for candidate selection in src/gepa_adk/engine/async_engine.py

**Checkpoint**: User Story 1 should be fully functional - Pareto selection works with ParetoCandidateSelector

---

## Phase 4: User Story 2 - Per-Example Best Score Tracking (Priority: P2)

**Goal**: Track which candidates perform best on each specific validation example (instance frontier)

**Independent Test**: Configure `frontier_type="instance"`, run evolution with 3+ diverse validation examples, verify that candidates best on any single example remain in the frontier

### Tests for User Story 2

- [X] T022 [P] [US2] Unit tests for frontier update with specialist candidates in tests/unit/test_pareto_state.py
- [X] T023 [P] [US2] Unit tests for selection weights reflecting example leadership in tests/unit/test_pareto_state.py

### Implementation for User Story 2

- [X] T024 [US2] Enhance ParetoFrontier.update() to handle tied scores (multiple leaders per example) in src/gepa_adk/domain/state.py
- [X] T025 [US2] Add frontier_type parameter to ParetoState constructor in src/gepa_adk/domain/state.py
- [X] T026 [US2] Add frontier_type to EvolutionConfig in src/gepa_adk/domain/models.py
- [X] T027 [US2] Pass frontier_type from config to ParetoState in AsyncGEPAEngine in src/gepa_adk/engine/async_engine.py
- [X] T028 [US2] Add structlog events for frontier updates (new leader, tied) in src/gepa_adk/domain/state.py

**Checkpoint**: User Story 2 complete - Per-example tracking enables specialist preservation

---

## Phase 5: User Story 3 - Multiple Candidate Selection Strategies (Priority: P3)

**Goal**: Provide three candidate selection strategies: Pareto, greedy, epsilon-greedy

**Independent Test**: Configure each selector type and verify selection behavior matches expected strategy

### Tests for User Story 3

- [X] T029 [P] [US3] Unit tests for CurrentBestCandidateSelector in tests/unit/test_candidate_selectors.py
- [X] T030 [P] [US3] Unit tests for EpsilonGreedyCandidateSelector in tests/unit/test_candidate_selectors.py
- [X] T031 [P] [US3] Statistical test for epsilon-greedy exploration rate in tests/unit/test_candidate_selectors.py

### Implementation for User Story 3

- [X] T032 [P] [US3] Implement CurrentBestCandidateSelector (async) in src/gepa_adk/adapters/candidate_selector.py
- [X] T033 [P] [US3] Implement EpsilonGreedyCandidateSelector (async) in src/gepa_adk/adapters/candidate_selector.py
- [X] T034 [US3] Export all selectors from src/gepa_adk/adapters/__init__.py
- [X] T035 [US3] Add selector factory function to create selector by name in src/gepa_adk/adapters/candidate_selector.py
- [X] T036 [US3] Update public API to support selector type string in src/gepa_adk/api.py

**Checkpoint**: All three selectors available and configurable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing and documentation

- [X] T037 [P] Integration test for Pareto evolution end-to-end in tests/integration/test_pareto_evolution.py (asserts SC-001 and SC-002)
- [X] T038 [P] Integration test for selector switching in tests/integration/test_pareto_evolution.py
- [X] T039 Verify all docstrings are Google-style with 95%+ coverage in src/gepa_adk/domain/state.py
- [X] T040 Verify all docstrings are Google-style with 95%+ coverage in src/gepa_adk/adapters/candidate_selector.py
- [ ] T041 Run quickstart.md examples to validate documentation
- [X] T042 Run ruff check and ruff format on all new files
- [X] T043 Run ty check for type validation
- [X] T044 [P] Add performance benchmark for frontier update (<10ms for 100 candidates x 50 examples) in tests/unit/test_pareto_state.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 can start immediately after Foundational
  - US2 can start after US1 (builds on ParetoState)
  - US3 can start after Foundational (independent selectors)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Phase 2 - Core implementation
- **User Story 2 (P2)**: Depends on US1 completion (extends ParetoState/ParetoFrontier)
- **User Story 3 (P3)**: Depends on Phase 2 only - Can run in parallel with US1

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Domain models before selector adapters
- Selector adapters before engine integration
- Engine before public API
- Core implementation before logging/observability

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T003, T004, T005 must be sequential (dependencies)

**Phase 3 (US1)**:
- T006, T007, T008, T009 can run in parallel (all tests)
- T010 can run in parallel with tests
- T013, T014 can run after T010 but parallel to T011

**Phase 4 (US2)**:
- T022, T023 can run in parallel

**Phase 5 (US3)**:
- T029, T030, T031 can run in parallel (all tests)
- T032, T033 can run in parallel (different classes)

**Phase 6 (Polish)**:
- T037, T038 can run in parallel
- T039, T040 can run in parallel
- T044 can run in parallel with other Phase 6 tasks

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for CandidateSelectorProtocol in tests/contracts/test_candidate_selector_protocol.py"
Task: "Unit tests for ParetoFrontier in tests/unit/test_pareto_state.py"
Task: "Unit tests for ParetoState in tests/unit/test_pareto_state.py"
Task: "Unit tests for ParetoCandidateSelector in tests/unit/test_candidate_selectors.py"
```

---

## Parallel Example: User Story 3 Selectors

```bash
# Launch selector implementations in parallel:
Task: "Implement CurrentBestCandidateSelector in src/gepa_adk/adapters/candidate_selector.py"
Task: "Implement EpsilonGreedyCandidateSelector in src/gepa_adk/adapters/candidate_selector.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Pareto selection)
4. **STOP and VALIDATE**: Test with ParetoCandidateSelector
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → **MVP: Pareto selection works!**
3. Add User Story 2 → Per-example tracking, specialist preservation
4. Add User Story 3 → All selector strategies available
5. Polish → Integration tests, documentation validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (core integration)
   - Developer B: User Story 3 (selector implementations)
3. After US1 complete:
   - Developer A: User Story 2 (extends US1)
   - Developer B: Continue US3 if needed
4. Integration tests after all stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD per ADR-005)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All code must pass: ruff check, ruff format, ty check

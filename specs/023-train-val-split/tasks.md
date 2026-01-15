# Tasks: Train/Val Split for Evolution Scoring

**Input**: Design documents from `/var/home/Alberto-Codes/Projects/gepa-adk/specs/023-train-val-split/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required by constitution (contract, unit, integration).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Shared test scaffolding and fixtures used across all stories

- [ ] T001 [P] Add shared trainset/valset fixtures in `tests/conftest.py`
- [ ] T002 [P] Create contract test scaffold in `tests/contracts/test_train_val_contract.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core changes required before any user story implementation

- [ ] T003 Update dataset validation helper to validate valset schema in `src/gepa_adk/api.py`
- [ ] T004 Add valset-aware result fields to `EvolutionResult` in `src/gepa_adk/domain/models.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Separate reflection vs scoring datasets (Priority: P1) 🎯 MVP

**Goal**: Reflection uses trainset while scoring/acceptance use valset.

**Independent Test**: Run evolution with distinct trainset/valset and verify reflection and scoring are sourced from the correct datasets.

### Tests for User Story 1

- [ ] T005 [P] [US1] Implement contract assertions in `tests/contracts/test_train_val_contract.py`
- [ ] T006 [P] [US1] Add unit tests for valset-based acceptance in `tests/unit/test_valset_scoring.py`
- [ ] T007 [P] [US1] Add integration test for train/val split in `tests/integration/test_train_val_split.py`

### Implementation for User Story 1

- [ ] T008 [US1] Split reflection vs scoring evaluation flows in `src/gepa_adk/engine/async_engine.py`
- [ ] T009 [US1] Pass valset into engine and use valset scores for acceptance in `src/gepa_adk/api.py`
- [ ] T010 [P] [US1] Add structured logging for trainset vs valset evaluations in `src/gepa_adk/api.py`

**Checkpoint**: User Story 1 functional and testable independently

---

## Phase 4: User Story 2 - Backward-compatible defaults (Priority: P2)

**Goal**: Valset defaults to trainset when not provided.

**Independent Test**: Run evolution with only a trainset and verify behavior matches trainset-as-valset scoring.

### Tests for User Story 2

- [ ] T011 [P] [US2] Add unit test for valset defaulting in `tests/unit/test_valset_scoring.py`
- [ ] T012 [P] [US2] Add integration test for default valset behavior in `tests/integration/test_train_val_split.py`

### Implementation for User Story 2

- [ ] T013 [US2] Default valset to trainset and update validation in `src/gepa_adk/api.py`
- [ ] T014 [US2] Ensure engine aliases valset to trainset when omitted in `src/gepa_adk/engine/async_engine.py`

**Checkpoint**: User Story 2 functional and testable independently

---

## Phase 5: User Story 3 - Candidate selection uses valset (Priority: P3)

**Goal**: Candidate selection and Pareto scoring use valset results.

**Independent Test**: Enable candidate selection with a valset and verify selection scores derive from valset evaluations.

### Tests for User Story 3

- [ ] T015 [P] [US3] Add unit test for valset-based Pareto scoring in `tests/unit/test_valset_scoring.py`

### Implementation for User Story 3

- [ ] T016 [US3] Route candidate selection scoring to valset results in `src/gepa_adk/engine/async_engine.py`

**Checkpoint**: User Story 3 functional and testable independently

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and validation steps that span stories

- [ ] T017 [P] Validate quickstart examples against updated API in `specs/023-train-val-split/quickstart.md`
- [ ] T018 [P] Update usage notes or docstrings if needed in `src/gepa_adk/api.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup completion
- **User Stories (Phase 3+)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational; no dependency on other stories
- **US2 (P2)**: Can start after Foundational; recommended after US1 due to shared files
- **US3 (P3)**: Can start after Foundational; recommended after US1 due to shared scoring flow

### Parallel Opportunities

- Phase 1 tasks T001 and T002 can run in parallel
- US1 tests (T005-T007) can run in parallel
- US2 tests (T011-T012) can run in parallel
- US3 test (T015) can run in parallel with US2 tests
- Documentation tasks (T017-T018) can run in parallel after implementation

---

## Parallel Example: User Story 1

```bash
Task: "Implement contract assertions in tests/contracts/test_train_val_contract.py"
Task: "Add unit tests for valset-based acceptance in tests/unit/test_valset_scoring.py"
Task: "Add integration test for train/val split in tests/integration/test_train_val_split.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate User Story 1 independently

### Incremental Delivery

1. Add User Story 2 → validate backward compatibility
2. Add User Story 3 → validate candidate selection uses valset
3. Finish Polish phase

---

## Task Summary

- **Total tasks**: 18
- **US1 tasks**: 6
- **US2 tasks**: 4
- **US3 tasks**: 2
- **Setup/Foundational/Polish tasks**: 6

# Tasks: Align Acceptance Scoring with Upstream GEPA

**Input**: Design documents from `/var/home/Alberto-Codes/Projects/gepa-adk/specs/025-acceptance-scoring/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Required by constitution (contract, unit, integration).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Shared test scaffolding used across user stories

- [ ] T001 [P] Add deterministic score fixtures/helpers in `tests/conftest.py`
- [ ] T002 [P] Create contract test scaffold in `tests/contracts/test_acceptance_scoring_contract.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core configuration and validation needed by all stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Add `acceptance_metric` field, docstrings, and validation to `src/gepa_adk/domain/models.py`
- [ ] T004 Add/extend validation errors for empty or non-finite scores in `src/gepa_adk/domain/exceptions.py`

**Checkpoint**: Configuration ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Acceptance Uses Minibatch Sum (Priority: P1) 🎯 MVP

**Goal**: Acceptance decisions use sum aggregation on iteration evaluation batches.

**Independent Test**: Run a deterministic evolution step and verify acceptance compares summed scores.

### Tests for User Story 1

- [ ] T005 [US1] Add contract assertions for acceptance_metric validation in `tests/contracts/test_acceptance_scoring_contract.py`
- [ ] T006 [P] [US1] Add unit test for sum-based acceptance comparisons in `tests/unit/engine/test_acceptance_scoring.py`
- [ ] T007 [US1] Add unit test for empty/non-finite score handling in `tests/unit/engine/test_acceptance_scoring.py`
- [ ] T008 [P] [US1] Add integration test for sum acceptance mode in `tests/integration/test_acceptance_scoring.py`

### Implementation for User Story 1

- [ ] T009 [US1] Add acceptance score aggregation helper in `src/gepa_adk/engine/async_engine.py`
- [ ] T010a [US1] Validate eval_batch.scores is non-empty and finite in `src/gepa_adk/engine/async_engine.py`
- [ ] T010 [US1] Use sum aggregation by default for acceptance comparisons in `src/gepa_adk/engine/async_engine.py`

**Checkpoint**: Sum-based acceptance behavior is functional and testable independently

---

## Phase 4: User Story 2 - Valset Tracking Uses Mean (Priority: P2)

**Goal**: Valset tracking remains mean-based and is stored separately from acceptance.

**Independent Test**: Evaluate a candidate on a known valset and verify mean tracking is reported.

### Tests for User Story 2

- [ ] T011 [US2] Add unit test for valset mean tracking in `tests/unit/engine/test_acceptance_scoring.py`
- [ ] T012 [US2] Add integration test for valset mean reporting in `tests/integration/test_acceptance_scoring.py`

### Implementation for User Story 2

- [ ] T013 [US2] Track best valset mean separately in `src/gepa_adk/engine/async_engine.py`
- [ ] T014 [US2] Use valset mean for `EvolutionResult.valset_score` in `src/gepa_adk/engine/async_engine.py`

**Checkpoint**: Valset reporting is mean-based and independent of acceptance aggregation

---

## Phase 5: User Story 3 - Backward Compatibility Toggle (Priority: P3)

**Goal**: Allow mean-based acceptance via configuration.

**Independent Test**: Run the same deterministic evolution step with acceptance_metric="mean" and verify legacy acceptance behavior.

### Tests for User Story 3

- [ ] T015 [US3] Add unit test for acceptance_metric="mean" in `tests/unit/engine/test_acceptance_scoring.py`
- [ ] T016 [US3] Add integration test for acceptance_metric="mean" in `tests/integration/test_acceptance_scoring.py`

### Implementation for User Story 3

- [ ] T017 [US3] Respect acceptance_metric selection in `src/gepa_adk/engine/async_engine.py`
- [ ] T018 [US3] Wire acceptance_metric into evolve/evolve_group/evolve_workflow config handling in `src/gepa_adk/api.py`

**Checkpoint**: Backward compatibility is confirmed and configurable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation validation and final checks

- [ ] T019 [P] Update examples if needed in `specs/025-acceptance-scoring/quickstart.md`
- [ ] T020 [P] Validate quickstart example manually from `specs/025-acceptance-scoring/quickstart.md`
- [ ] T021 Run contract tests: `uv run pytest tests/contracts/test_acceptance_scoring_contract.py`
- [ ] T022 Run unit tests: `uv run pytest tests/unit/engine/test_acceptance_scoring.py`
- [ ] T023 Run integration tests: `uv run pytest tests/integration/test_acceptance_scoring.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: Depend on Foundational phase completion
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P2)**: Can start after Foundational; recommended after US1
- **User Story 3 (P3)**: Can start after Foundational; recommended after US1

### Parallel Opportunities

- T001 and T002 can run in parallel
- US1 tests T006 and T008 can run in parallel
- US2 tests T011 and T012 can run in parallel with US3 tests T015 and T016
- Polish tasks T019 and T020 can run in parallel

---

## Parallel Example: User Story 1

```bash
Task: "Add unit test for sum-based acceptance comparisons in tests/unit/engine/test_acceptance_scoring.py"
Task: "Add integration test for sum acceptance mode in tests/integration/test_acceptance_scoring.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate User Story 1 independently

### Incremental Delivery

1. Add User Story 2 → validate valset mean tracking
2. Add User Story 3 → validate mean-based acceptance compatibility
3. Finish Polish phase

---

## Task Summary

- **Total tasks**: 24
- **US1 tasks**: 7
- **US2 tasks**: 4
- **US3 tasks**: 4
- **Setup/Foundational/Polish tasks**: 9

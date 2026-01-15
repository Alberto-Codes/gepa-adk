# Tasks: MergeProposer for Combining Pareto-Optimal Candidates

**Input**: Design documents from `/specs/028-merge-proposer/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included per constitution three-layer testing requirement (contract/unit/integration).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root
- Follows hexagonal architecture: domain/, ports/, engine/, adapters/

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and type definitions

- [X] T001 Add type aliases (MergeAttempt, AncestorLog) in src/gepa_adk/domain/types.py
- [X] T002 [P] Add ProposalResult dataclass in src/gepa_adk/domain/types.py (move from ports/proposer.py and update imports)
- [X] T003 [P] Create ProposerProtocol in src/gepa_adk/ports/proposer.py
- [X] T004 Export new types from src/gepa_adk/domain/__init__.py
- [X] T005 Export ProposerProtocol from src/gepa_adk/ports/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend existing models and state to support genealogy tracking - MUST complete before user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Extend Candidate dataclass with parent_ids field in src/gepa_adk/domain/models.py
- [X] T007 Extend ParetoState with parent_indices tracking in src/gepa_adk/domain/state.py
- [X] T008 Update ParetoState.add_candidate() to track parent indices in src/gepa_adk/domain/state.py
- [X] T009 Add use_merge and max_merge_invocations to EvolutionConfig in src/gepa_adk/domain/models.py
- [X] T010 [P] Create contract test for ProposerProtocol in tests/contracts/test_proposer_protocol.py

**Checkpoint**: Foundation ready - genealogy tracking available, ProposerProtocol defined

---

## Phase 3: User Story 2 - Track Candidate Genealogy (Priority: P2)

**Goal**: Track parent-child relationships between candidates throughout evolution

**Independent Test**: Run evolution for multiple iterations and verify parent chain traversal back to seed candidates

> **Note**: US2 is implemented before US1 because genealogy tracking is a prerequisite for merge operations

### Tests for User Story 2

- [X] T011 [P] [US2] Unit test for get_ancestors() in tests/unit/test_genealogy.py
- [X] T012 [P] [US2] Unit test for find_common_ancestor() in tests/unit/test_genealogy.py
- [X] T013 [P] [US2] Unit test for ancestry traversal with deep trees in tests/unit/test_genealogy.py

### Implementation for User Story 2

- [X] T014 [US2] Create genealogy.py with get_ancestors() function in src/gepa_adk/engine/genealogy.py
- [X] T015 [US2] Implement find_common_ancestor() in src/gepa_adk/engine/genealogy.py
- [X] T016 [US2] Add cycle detection to prevent circular ancestry in src/gepa_adk/engine/genealogy.py
- [X] T017 [US2] Export genealogy functions from src/gepa_adk/engine/__init__.py
- [X] T018 [US2] Add structlog events for genealogy operations in src/gepa_adk/engine/genealogy.py

**Checkpoint**: Genealogy tracking works - can traverse ancestry and find common ancestors

---

## Phase 4: User Story 3 - Find Common Ancestors (Priority: P3)

**Goal**: Identify the common ancestor between two candidates being merged

**Independent Test**: Create known genealogy tree and verify common ancestor algorithm returns correct ancestor

### Tests for User Story 3

- [X] T019 [P] [US3] Unit test for common ancestor with shared lineage in tests/unit/test_genealogy.py
- [X] T020 [P] [US3] Unit test for no common ancestor case in tests/unit/test_genealogy.py
- [X] T021 [P] [US3] Unit test for most recent ancestor selection in tests/unit/test_genealogy.py
- [X] T022 [P] [US3] Unit test for one-is-ancestor-of-other case in tests/unit/test_genealogy.py

### Implementation for User Story 3

- [X] T023 [US3] Implement ancestor filtering by score constraints in src/gepa_adk/engine/genealogy.py
- [X] T024 [US3] Implement component divergence detection in src/gepa_adk/engine/genealogy.py
- [X] T025 [US3] Add has_desirable_predictors check for merge viability in src/gepa_adk/engine/genealogy.py

**Checkpoint**: Common ancestor identification works correctly for all edge cases

---

## Phase 5: User Story 1 - Merge Complementary Candidates (Priority: P1) 🎯 MVP

**Goal**: Automatically combine two candidates that excel in different areas

**Independent Test**: Run evolution with two known candidates having complementary profiles, verify merged candidate inherits components from both

### Tests for User Story 1

- [X] T026 [P] [US1] Contract test for MergeProposer.propose() in tests/contracts/test_merge_proposer_protocol.py
- [X] T027 [P] [US1] Unit test for merge_components() in tests/unit/test_merge_proposer.py
- [X] T028 [P] [US1] Unit test for component selection logic in tests/unit/test_merge_proposer.py
- [X] T029 [P] [US1] Unit test for merge with overlapping improvements in tests/unit/test_merge_proposer.py
- [X] T030 [P] [US1] Unit test for merge attempt deduplication in tests/unit/test_merge_proposer.py
- [X] T031 [P] [US1] Integration test for full merge evolution in tests/integration/test_merge_evolution.py

### Implementation for User Story 1

- [X] T032 [US1] Create MergeProposer class skeleton in src/gepa_adk/engine/merge_proposer.py
- [X] T033 [US1] Implement _find_merge_candidates() for frontier selection in src/gepa_adk/engine/merge_proposer.py
- [X] T034 [US1] Implement merge_components() function in src/gepa_adk/engine/merge_proposer.py
- [X] T035 [US1] Implement async propose() method in src/gepa_adk/engine/merge_proposer.py
- [X] T036 [US1] Add merge attempt tracking (AncestorLog) in src/gepa_adk/engine/merge_proposer.py
- [X] T037 [US1] Add validation overlap floor check in src/gepa_adk/engine/merge_proposer.py
- [X] T038 [US1] Add structlog events for merge operations in src/gepa_adk/engine/merge_proposer.py
- [X] T039 [US1] Export MergeProposer from src/gepa_adk/engine/__init__.py

**Checkpoint**: MergeProposer can combine complementary candidates

---

## Phase 6: Engine Integration

**Purpose**: Integrate MergeProposer into the evolution loop

### Tests for Engine Integration

- [X] T040 [P] Unit test for engine with merge enabled in tests/unit/test_async_engine_merge.py
- [X] T041 [P] Unit test for merge scheduling logic in tests/unit/test_async_engine_merge.py
- [X] T042 [P] Integration test for evolution with both mutation and merge in tests/integration/test_merge_evolution.py

### Implementation for Engine Integration

- [X] T043 Update AsyncGEPAEngine.__init__() to accept merge_proposer in src/gepa_adk/engine/async_engine.py
- [X] T044 Add merge scheduling logic (schedule_if_needed) in src/gepa_adk/engine/async_engine.py
- [X] T045 Integrate merge proposal after successful mutation in src/gepa_adk/engine/async_engine.py
- [X] T046 Add parent_indices tracking to engine state in src/gepa_adk/engine/async_engine.py
- [X] T047 Add structlog events for merge scheduling in src/gepa_adk/engine/async_engine.py

**Checkpoint**: Evolution engine supports merge proposals alongside mutations

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T048 [P] Add Google-style docstrings to all new modules
- [X] T049 [P] Update src/gepa_adk/__init__.py exports for MergeProposer
- [X] T050 Run ruff check and fix any linting issues
- [X] T051 Run ty check and fix any type errors
- [X] T052 Validate quickstart.md examples work correctly
- [X] T053 Run full test suite (pytest -n auto) and verify all pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 2 (Phase 3)**: Depends on Foundational - prerequisite for US1/US3
- **User Story 3 (Phase 4)**: Depends on User Story 2 (uses genealogy functions)
- **User Story 1 (Phase 5)**: Depends on User Stories 2 and 3 (uses genealogy + common ancestor)
- **Engine Integration (Phase 6)**: Depends on User Story 1 (MergeProposer must exist)
- **Polish (Phase 7)**: Depends on all implementations being complete

### User Story Dependencies

- **User Story 2 (P2)**: Genealogy tracking - No dependencies on other stories, but blocks US1 and US3
- **User Story 3 (P3)**: Common ancestor - Depends on US2 genealogy functions
- **User Story 1 (P1)**: Merge operation - Depends on US2 and US3 (genealogy + ancestor finding)

> **Note**: Story priority order (P1, P2, P3) differs from implementation order due to technical dependencies

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation follows: algorithm → protocol compliance → integration
- Story complete before moving to dependent stories
- All tasks within a story should be completed before checkpoint

### Parallel Opportunities

- All Setup tasks T002-T003 can run in parallel
- Test tasks within each story marked [P] can run in parallel
- T011-T013 (US2 tests) can run in parallel
- T019-T022 (US3 tests) can run in parallel
- T026-T031 (US1 tests) can run in parallel
- T040-T042 (Engine tests) can run in parallel

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for MergeProposer.propose() in tests/contracts/test_merge_proposer_protocol.py"
Task: "Unit test for merge_components() in tests/unit/test_merge_proposer.py"
Task: "Unit test for component selection logic in tests/unit/test_merge_proposer.py"
Task: "Unit test for merge with overlapping improvements in tests/unit/test_merge_proposer.py"
Task: "Unit test for merge attempt deduplication in tests/unit/test_merge_proposer.py"
Task: "Integration test for full merge evolution in tests/integration/test_merge_evolution.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

Due to technical dependencies, MVP requires implementing in this order:

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 2 (Genealogy)
4. Complete Phase 4: User Story 3 (Common Ancestor)
5. Complete Phase 5: User Story 1 (Merge)
6. **STOP and VALIDATE**: Test merge functionality independently
7. Deploy/demo if ready (merge works without engine integration)

### Full Integration

1. Complete MVP (Phases 1-5)
2. Complete Phase 6: Engine Integration
3. Complete Phase 7: Polish
4. Run full test suite
5. Validate quickstart examples

### Single Developer Strategy

Execute phases sequentially in order 1 → 2 → 3 → 4 → 5 → 6 → 7, completing each checkpoint before proceeding.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Tests follow three-layer strategy: contracts → unit → integration
- Story order differs from priority due to technical dependencies (genealogy must exist before merge)
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Avoid: vague tasks, same file conflicts, circular dependencies

# Tasks: Frontier Types and Valset Evaluation Policies

**Input**: Design documents from `/specs/027-frontier-eval-policy/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required per constitution (ADR-005: Three-Layer Testing Strategy)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Extend existing project structure for new feature

- [x] T001 Add FrontierKey type alias in src/gepa_adk/domain/types.py with definition: `FrontierKey: TypeAlias = int | str | tuple[str, int] | tuple[str, int, str]` (int for INSTANCE, str for OBJECTIVE, tuple variants for HYBRID/CARTESIAN)
- [x] T002 [P] Create evaluation_policy.py file in src/gepa_adk/adapters/evaluation_policy.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Domain Layer Foundation

- [x] T003 Remove INSTANCE-only restriction from ParetoState.__post_init__ in src/gepa_adk/domain/state.py
- [x] T004 Add objective_leaders and objective_best_scores fields to ParetoFrontier in src/gepa_adk/domain/state.py
- [x] T005 Add cartesian_leaders and cartesian_best_scores fields to ParetoFrontier in src/gepa_adk/domain/state.py
- [x] T006 Add candidate_objective_scores field to ParetoState in src/gepa_adk/domain/state.py

### Ports Layer Foundation

- [x] T007 Define EvaluationPolicyProtocol in src/gepa_adk/ports/selector.py with get_eval_batch, get_best_candidate, get_valset_score methods

### Contract Tests Foundation

- [x] T008 [P] Create test_evaluation_policy_protocol.py in tests/contracts/test_evaluation_policy_protocol.py with protocol compliance base class

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Objective-Level Pareto Selection (Priority: P1) 🎯 MVP

**Goal**: Enable frontier tracking with objective-level dominance for multi-objective optimization

**Independent Test**: Configure frontier_type="objective", verify Pareto selection uses objective-level scores

### Tests for User Story 1

- [x] T009 [P] [US1] Unit test for update_objective method in tests/unit/domain/test_frontier_types.py
- [x] T010 [P] [US1] Unit test for objective frontier dominance logic in tests/unit/domain/test_frontier_types.py
- [x] T011 [P] [US1] Unit test for objective_scores validation in tests/unit/domain/test_frontier_types.py

### Implementation for User Story 1

- [x] T012 [US1] Implement update_objective method in ParetoFrontier in src/gepa_adk/domain/state.py
- [x] T013 [US1] Modify add_candidate to accept optional objective_scores parameter in src/gepa_adk/domain/state.py
- [x] T014 [US1] Add validation for objective_scores when frontier_type is OBJECTIVE in src/gepa_adk/domain/state.py
- [x] T015 [US1] Route frontier updates to update_objective for OBJECTIVE frontier_type in src/gepa_adk/domain/state.py
- [x] T016 [US1] Implement get_pareto_front_mapping for OBJECTIVE type in ParetoFrontier in src/gepa_adk/domain/state.py
- [x] T017 [US1] Add structured logging for objective frontier updates in src/gepa_adk/domain/state.py

**Checkpoint**: User Story 1 complete - objective-level Pareto selection functional

---

## Phase 4: User Story 4 - Full Valset Evaluation Policy (Priority: P1) 🎯 MVP

**Goal**: Implement full evaluation policy as the default behavior for complete valset scoring

**Independent Test**: Configure val_evaluation_policy="full_eval", verify all valset IDs scored each iteration

### Tests for User Story 4

- [x] T018 [P] [US4] Contract test for FullEvaluationPolicy compliance in tests/contracts/test_evaluation_policy_protocol.py
- [x] T019 [P] [US4] Unit test for get_eval_batch returns all IDs in tests/unit/adapters/test_evaluation_policy.py
- [x] T020 [P] [US4] Unit test for get_best_candidate returns highest average in tests/unit/adapters/test_evaluation_policy.py
- [x] T021 [P] [US4] Unit test for get_valset_score calculation in tests/unit/adapters/test_evaluation_policy.py

### Implementation for User Story 4

- [x] T022 [US4] Implement FullEvaluationPolicy class in src/gepa_adk/adapters/evaluation_policy.py
- [x] T023 [US4] Implement get_eval_batch to return all valset_ids in src/gepa_adk/adapters/evaluation_policy.py
- [x] T024 [US4] Implement get_best_candidate with highest average score logic in src/gepa_adk/adapters/evaluation_policy.py
- [x] T025 [US4] Implement get_valset_score with mean calculation in src/gepa_adk/adapters/evaluation_policy.py
- [x] T026 [US4] Add evaluation_policy parameter to AsyncGEPAEngine.__init__ in src/gepa_adk/engine/async_engine.py
- [x] T027 [US4] Default evaluation_policy to FullEvaluationPolicy() in AsyncGEPAEngine in src/gepa_adk/engine/async_engine.py
- [x] T028 [US4] Wire get_eval_batch into _evaluate_scoring flow in src/gepa_adk/engine/async_engine.py

**Checkpoint**: User Story 4 complete - full evaluation policy functional, MVP deliverable

---

## Phase 5: User Story 2 - Hybrid Frontier Tracking (Priority: P2)

**Goal**: Enable combined instance-level and objective-level frontier tracking

**Independent Test**: Configure frontier_type="hybrid", verify both instance and objective frontiers updated

### Tests for User Story 2

- [x] T029 [P] [US2] Unit test for hybrid frontier updates both structures in tests/unit/domain/test_frontier_types.py
- [x] T030 [P] [US2] Unit test for get_pareto_front_mapping returns combined mapping in tests/unit/domain/test_frontier_types.py

### Implementation for User Story 2

- [x] T031 [US2] Add HYBRID branch in add_candidate to update both frontiers in src/gepa_adk/domain/state.py
- [x] T032 [US2] Implement get_pareto_front_mapping for HYBRID type with type tags in src/gepa_adk/domain/state.py
- [x] T033 [US2] Add structured logging for hybrid frontier updates in src/gepa_adk/domain/state.py

**Checkpoint**: User Story 2 complete - hybrid frontier tracking functional

---

## Phase 6: User Story 3 - Cartesian Frontier Tracking (Priority: P2)

**Goal**: Enable per (example, objective) pair Pareto frontier tracking

**Independent Test**: Configure frontier_type="cartesian", verify separate frontiers per (example, objective) pair

### Tests for User Story 3

- [x] T034 [P] [US3] Unit test for update_cartesian method in tests/unit/domain/test_frontier_types.py
- [x] T035 [P] [US3] Unit test for cartesian key structure in tests/unit/domain/test_frontier_types.py
- [x] T036 [P] [US3] Unit test for get_pareto_front_mapping CARTESIAN type in tests/unit/domain/test_frontier_types.py

### Implementation for User Story 3

- [x] T037 [US3] Implement update_cartesian method in ParetoFrontier in src/gepa_adk/domain/state.py
- [x] T038 [US3] Add per_example_objective_scores parameter handling in add_candidate in src/gepa_adk/domain/state.py
- [x] T039 [US3] Route frontier updates to update_cartesian for CARTESIAN type in src/gepa_adk/domain/state.py
- [x] T040 [US3] Implement get_pareto_front_mapping for CARTESIAN type in src/gepa_adk/domain/state.py
- [x] T041 [US3] Add structured logging for cartesian frontier updates in src/gepa_adk/domain/state.py

**Checkpoint**: User Story 3 complete - cartesian frontier tracking functional

---

## Phase 7: User Story 5 - Subset Valset Evaluation Policy (Priority: P2)

**Goal**: Enable configurable subset evaluation for large validation sets with round-robin coverage

**Independent Test**: Configure val_evaluation_policy="subset" with subset_size=0.2, verify 20% of valset scored per iteration

### Tests for User Story 5

- [x] T042 [P] [US5] Contract test for SubsetEvaluationPolicy compliance in tests/contracts/test_evaluation_policy_protocol.py
- [x] T043 [P] [US5] Unit test for get_eval_batch returns subset in tests/unit/adapters/test_evaluation_policy.py
- [x] T044 [P] [US5] Unit test for round-robin offset advancement in tests/unit/adapters/test_evaluation_policy.py
- [x] T045 [P] [US5] Unit test for subset_size as int vs float handling in tests/unit/adapters/test_evaluation_policy.py
- [x] T046 [P] [US5] Unit test for subset_size exceeding valset falls back in tests/unit/adapters/test_evaluation_policy.py

### Implementation for User Story 5

- [x] T047 [US5] Implement SubsetEvaluationPolicy class in src/gepa_adk/adapters/evaluation_policy.py
- [x] T048 [US5] Add subset_size parameter (int | float) and _offset state in src/gepa_adk/adapters/evaluation_policy.py
- [x] T049 [US5] Implement get_eval_batch with round-robin slicing in src/gepa_adk/adapters/evaluation_policy.py
- [x] T050 [US5] Implement fallback when subset_size > valset_size in src/gepa_adk/adapters/evaluation_policy.py
- [x] T051 [US5] Implement get_best_candidate consistent with FullEvaluationPolicy in src/gepa_adk/adapters/evaluation_policy.py
- [x] T052 [US5] Implement get_valset_score consistent with FullEvaluationPolicy in src/gepa_adk/adapters/evaluation_policy.py

**Checkpoint**: User Story 5 complete - subset evaluation policy functional

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Integration tests, backward compatibility verification, final cleanup

### Integration Tests

- [x] T053 [P] Integration test for evolution with OBJECTIVE frontier in tests/integration/test_frontier_evolution.py
- [x] T054 [P] Integration test for evolution with HYBRID frontier in tests/integration/test_frontier_evolution.py
- [x] T055 [P] Integration test for evolution with CARTESIAN frontier in tests/integration/test_frontier_evolution.py
- [x] T056 [P] Integration test for evolution with SubsetEvaluationPolicy in tests/integration/test_frontier_evolution.py
- [ ] T064 [P] Integration test validating SC-002: verify subset evaluation reduces per-iteration cost by ≥80% for large valsets (1000+ examples) in tests/integration/test_frontier_evolution.py
- [x] T065 [P] Integration test validating SC-005: verify objective/hybrid/cartesian frontier types produce ≥20% more unique non-dominated candidates or ≥3 distinct objective tradeoff regions compared to instance-only in tests/integration/test_frontier_evolution.py

### Backward Compatibility

- [ ] T057 Verify existing tests pass with default INSTANCE frontier type
- [ ] T058 Verify existing tests pass without evaluation_policy parameter

### Final Cleanup

- [x] T059 [P] Export EvaluationPolicyProtocol from gepa_adk.ports
- [x] T060 [P] Export FullEvaluationPolicy, SubsetEvaluationPolicy from gepa_adk.adapters
- [ ] T061 Run quickstart.md validation scenarios
- [ ] T062 Run ruff check and format
- [ ] T063 Run full test suite (pytest -n auto) (run via `uv run pytest -n auto`: 6 failed, 6 errors)

---

## Phase 9: Gap Fixes After yxh Apply

**Purpose**: Address remaining issues discovered during worktree review.

### Engine and State Fixes

- [x] T066 Fix subset evaluation mapping so EvaluationBatch outputs/scores lengths match the evaluated batch (no valset-sized score lists) in src/gepa_adk/engine/async_engine.py
- [x] T067 Compute valset_mean using only evaluated scores to avoid -inf contamination in src/gepa_adk/engine/async_engine.py
- [x] T068 Wire subset objective scores into ParetoState updates for OBJECTIVE/HYBRID/CARTESIAN when using SubsetEvaluationPolicy in src/gepa_adk/engine/async_engine.py
- [x] T069 Enforce frontier_type immutability after ParetoState initialization (raise ConfigurationError on change) in src/gepa_adk/domain/state.py

### Integration Test Corrections

- [x] T070 Fix integration adapters to return outputs/scores lists sized to batch length per adapter contract in tests/integration/test_frontier_evolution.py
- [ ] T071 Tighten SC-002 cost reduction assertion to >= 80% as specified in tests/integration/test_frontier_evolution.py

### Test Failures to Address (uv run pytest -n auto)

- [ ] T072 Prevent base EvaluationPolicyProtocol compliance class from being collected (set `__test__ = False` or mark abstract) in tests/contracts/test_evaluation_policy_protocol.py
- [ ] T073 Restore full valset scoring for default policy so acceptance score equals sum/mean over full valset in src/gepa_adk/engine/async_engine.py
- [ ] T074 Ensure scoring batches use valset identity where required by contracts/tests (train/val split expectations) or update tests to accept subset batches in tests/contracts/test_train_val_contract.py, tests/integration/test_train_val_split.py, tests/unit/test_valset_scoring.py
- [ ] T075 Ensure ParetoState candidate_scores for valset use valset scores (not trainset) when candidate_selector is enabled in src/gepa_adk/engine/async_engine.py

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────────────────┐
                                     │
Phase 2: Foundational ◄──────────────┘
         ↓ (BLOCKS ALL USER STORIES)
         │
    ┌────┴────┬────────────┬────────────┬────────────┐
    ▼         ▼            ▼            ▼            ▼
Phase 3   Phase 4      Phase 5      Phase 6      Phase 7
  US1       US4          US2          US3          US5
  (P1)      (P1)         (P2)         (P2)         (P2)
    │         │            │            │            │
    └────┬────┴────────────┴────────────┴────────────┘
         ▼
Phase 8: Polish
```

### User Story Dependencies

- **US1 (Objective Frontier)**: Foundation only - independent
- **US4 (Full Eval Policy)**: Foundation only - independent (MVP with US1)
- **US2 (Hybrid Frontier)**: Foundation + uses US1 patterns - can implement in parallel
- **US3 (Cartesian Frontier)**: Foundation + uses US1 patterns - can implement in parallel
- **US5 (Subset Eval Policy)**: Foundation + uses US4 patterns - can implement in parallel

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Domain modifications before engine wiring
3. Core implementation before logging
4. Story complete before checkpoint

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T008 can run in parallel with T003-T007

**Phase 3 (US1) + Phase 4 (US4) can run in parallel**:
- Different file paths, independent implementations
- US1: domain/state.py modifications
- US4: adapters/evaluation_policy.py + engine wiring

**Phase 5, 6, 7 (US2, US3, US5) can all run in parallel**:
- US2: domain/state.py HYBRID branch
- US3: domain/state.py CARTESIAN branch
- US5: adapters/evaluation_policy.py SubsetEvaluationPolicy

**Phase 8 integration tests all parallelizable**

---

## Parallel Example: MVP (US1 + US4)

```bash
# After Foundation complete, launch US1 tests:
Task: "Unit test for update_objective method in tests/unit/domain/test_frontier_types.py"
Task: "Unit test for objective frontier dominance logic in tests/unit/domain/test_frontier_types.py"
Task: "Unit test for objective_scores validation in tests/unit/domain/test_frontier_types.py"

# Simultaneously launch US4 tests:
Task: "Contract test for FullEvaluationPolicy in tests/contracts/test_evaluation_policy_protocol.py"
Task: "Unit test for get_eval_batch in tests/unit/adapters/test_evaluation_policy.py"
Task: "Unit test for get_best_candidate in tests/unit/adapters/test_evaluation_policy.py"
Task: "Unit test for get_valset_score in tests/unit/adapters/test_evaluation_policy.py"
```

---

## Implementation Strategy

### MVP First (US1 + US4)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: US1 - Objective Frontier
4. Complete Phase 4: US4 - Full Evaluation Policy
5. **STOP and VALIDATE**: Test US1 + US4 independently with integration test
6. Deploy/demo if ready - MVP delivers multi-objective optimization capability

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 + US4 → Test independently → **MVP!** (multi-objective with full eval)
3. Add US2 → Test independently → Hybrid frontier support
4. Add US3 → Test independently → Cartesian granularity
5. Add US5 → Test independently → Scalable evaluation for large valsets
6. Polish → Final integration validation

### Parallel Team Strategy

With multiple developers after Foundational complete:
- **Developer A**: US1 (Objective) + US3 (Cartesian) - domain/state.py focus
- **Developer B**: US4 (Full Policy) + US5 (Subset Policy) - adapters focus
- **Developer C**: US2 (Hybrid) + Integration tests

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Constitution requires three-layer testing (contract, unit, integration)
- Verify tests fail before implementing
- Commit after each task or logical group
- Backward compatibility: existing code MUST work with defaults
- Avoid: cross-story dependencies that break independence

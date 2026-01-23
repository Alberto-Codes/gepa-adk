# Tasks: Execute Workflows As-Is (Preserve Structure)

**Input**: Design documents from `/specs/215-workflow-structure/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, architecture.md
**GitHub Issue**: #215

**Tests**: Included per Constitution Principle IV (Three-Layer Testing) requirement in plan.md.

**Documentation**: Per Constitution Principle VI, this feature changes user-facing workflow behavior and requires documentation updates.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| Breaking change | Required + migration | Required |

This feature changes workflow execution semantics (breaking change for users relying on flattening behavior).

---

## Phase 1: Setup

**Purpose**: No new project setup needed - extending existing codebase

- [x] T001 Verify branch `215-workflow-structure` is checked out and up to date with develop

---

## Phase 2: Foundational (Core Cloning Function)

**Purpose**: Implement the recursive cloning function that ALL user stories depend on

**CRITICAL**: This function is the foundation for all three user stories

### Contract Tests (Constitution Principle IV - NON-NEGOTIABLE)

- [x] T002 [P] Add contract test verifying `clone_workflow_with_overrides()` returns same type as input in tests/contracts/test_workflow_contracts.py
- [x] T003 [P] Add contract test verifying cloned workflow maintains sub_agents count invariant in tests/contracts/test_workflow_contracts.py

### Unit Tests

- [x] T004 [P] Add unit test for `clone_workflow_with_overrides()` with LlmAgent in tests/unit/test_workflow.py
- [x] T005 [P] Add unit test for `clone_workflow_with_overrides()` with SequentialAgent in tests/unit/test_workflow.py

### Implementation

- [x] T006 Implement `clone_workflow_with_overrides()` function in src/gepa_adk/adapters/workflow.py
- [x] T007 Store original workflow reference in `MultiAgentAdapter.__init__` in src/gepa_adk/adapters/multi_agent.py
- [x] T008 Refactor `_build_pipeline()` to use `clone_workflow_with_overrides()` in src/gepa_adk/adapters/multi_agent.py

**Checkpoint**: Foundation ready - cloning preserves SequentialAgent and LlmAgent structure

---

## Phase 3: User Story 1 - LoopAgent Iteration Preservation (Priority: P1)

**Goal**: LoopAgent executes configured number of iterations (max_iterations preserved)

**Independent Test**: Create LoopAgent(max_iterations=3), run evolve_workflow, verify inner agent executes 3 times per example

### Tests for User Story 1

- [ ] T009 [P] [US1] Add unit test for cloning LoopAgent preserves max_iterations in tests/unit/test_workflow.py
- [ ] T010 [P] [US1] Add integration test for LoopAgent executing N iterations in tests/integration/test_workflow_integration.py

### Implementation for User Story 1

- [ ] T011 [US1] Add LoopAgent handling to `clone_workflow_with_overrides()` in src/gepa_adk/adapters/workflow.py
- [ ] T012 [US1] Update `_extract_primary_output()` to handle loop iteration outputs in src/gepa_adk/adapters/multi_agent.py
- [ ] T013 [US1] Update trajectory capture to include all loop iteration events in src/gepa_adk/adapters/multi_agent.py

### Documentation for User Story 1

- [ ] T014 [P] [US1] Update docs/guides/workflows.md with LoopAgent iteration preservation behavior
- [ ] T015 [P] [US1] Add LoopAgent evolution example to examples/ directory

**Checkpoint**: LoopAgent workflows execute with preserved iterations

---

## Phase 4: User Story 2 - ParallelAgent Concurrent Execution (Priority: P1)

**Goal**: ParallelAgent sub-agents execute concurrently, not sequentially

**Independent Test**: Create ParallelAgent with two sub-agents, run evolve_workflow, verify both execute concurrently with outputs in session state

### Tests for User Story 2

- [ ] T016 [P] [US2] Add unit test for cloning ParallelAgent preserves structure in tests/unit/test_workflow.py
- [ ] T017 [P] [US2] Add integration test for ParallelAgent concurrent execution in tests/integration/test_workflow_integration.py

### Implementation for User Story 2

- [ ] T018 [US2] Add ParallelAgent handling to `clone_workflow_with_overrides()` in src/gepa_adk/adapters/workflow.py
- [ ] T019 [US2] Ensure `_extract_primary_output()` handles parallel outputs correctly in src/gepa_adk/adapters/multi_agent.py

### Documentation for User Story 2

- [ ] T020 [P] [US2] Update docs/guides/workflows.md with ParallelAgent concurrent execution behavior
- [ ] T021 [P] [US2] Add ParallelAgent evolution example to examples/ directory

**Checkpoint**: ParallelAgent workflows execute with concurrent semantics

---

## Phase 5: User Story 3 - Nested Workflow Structure Preservation (Priority: P2)

**Goal**: Nested workflows of arbitrary depth preserve their structure (Sequential containing Parallel containing Loop, etc.)

**Independent Test**: Create Sequential([Parallel([A, B]), Synthesizer, Writer]), run evolve_workflow, verify correct execution order with proper data flow

### Tests for User Story 3

- [ ] T022 [P] [US3] Add unit test for cloning nested workflows (4+ levels) in tests/unit/test_workflow.py
- [ ] T023 [P] [US3] Add integration test for nested workflow end-to-end execution in tests/integration/test_workflow_integration.py

### Implementation for User Story 3

- [ ] T024 [US3] Verify recursive cloning handles arbitrary nesting depth in src/gepa_adk/adapters/workflow.py
- [ ] T025 [US3] Add edge case handling for deeply nested workflows (respect max_depth) in src/gepa_adk/adapters/workflow.py

### Documentation for User Story 3

- [ ] T026 [P] [US3] Update docs/guides/workflows.md with nested workflow examples
- [ ] T027 [P] [US3] Add nested workflow evolution example to examples/ directory

**Checkpoint**: Nested workflows of any structure execute correctly

---

## Phase 6: Verification & Cross-Cutting Concerns

**Purpose**: Final verification, backward compatibility, and documentation build

### Backward Compatibility

- [ ] T028 Run existing evolve_workflow tests to verify backward compatibility
- [ ] T029 Update any failing tests that relied on flattening behavior

### Edge Cases (from spec.md)

- [ ] T030 [P] Add test for LoopAgent with max_iterations=0 in tests/unit/test_workflow.py
- [ ] T031 [P] Add test for ParallelAgent with single sub-agent in tests/unit/test_workflow.py
- [ ] T032 [P] Add test for unsupported agent types (custom BaseAgent subclasses) in tests/unit/test_workflow.py
- [ ] T033 [P] Add test for LlmAgent appearing multiple times in same workflow in tests/unit/test_workflow.py

### Documentation Build Verification

- [ ] T034 Verify `uv run mkdocs build` passes without warnings
- [ ] T035 Preview docs with `uv run mkdocs serve` and verify changes render correctly

### Final Validation

- [ ] T036 Run full test suite: `uv run pytest`
- [ ] T037 Run linting: `uv run ruff check .`
- [ ] T038 Validate quickstart.md scenarios work as documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories
- **Phase 3-5 (User Stories)**: All depend on Phase 2 completion
  - US1 and US2 can run in parallel (both P1 priority)
  - US3 can run in parallel with US1/US2 or after
- **Phase 6 (Verification)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (LoopAgent)**: Depends on Phase 2 - No dependencies on other stories
- **US2 (ParallelAgent)**: Depends on Phase 2 - No dependencies on other stories
- **US3 (Nested)**: Depends on Phase 2 - Benefits from US1/US2 being done but can proceed independently

### Within Each User Story

1. Tests written first (e.g., T009-T010 before T011-T013 for US1)
2. Implementation before documentation
3. Documentation before checkpoint

### Parallel Opportunities

**Phase 2 (Foundational)**:
```
T002 (contract test type) || T003 (contract test invariant) || T004 (unit test LlmAgent) || T005 (unit test Sequential)
→ T006 (implement cloning)
→ T007 (store workflow) || T008 (refactor _build_pipeline)
```

**User Stories (after Phase 2)**:
```
US1 || US2 || US3  (all can proceed in parallel)
```

**Within US1**:
```
T009 (unit test) || T010 (integration test)
→ T011, T012, T013 (implementation - sequential)
→ T014 (docs) || T015 (examples)
```

---

## Parallel Example: Phase 2 + User Stories

```bash
# Phase 2 - Foundation (must complete first)
Task: T002 "Add contract test verifying type preservation"
Task: T003 "Add contract test verifying sub_agents invariant"
Task: T004 "Add unit test for clone_workflow_with_overrides() with LlmAgent"
Task: T005 "Add unit test for clone_workflow_with_overrides() with SequentialAgent"
# Wait for T002-T005
Task: T006 "Implement clone_workflow_with_overrides() function"
# Then T007, T008

# After Phase 2 - User Stories can run in parallel
# Developer A: US1
Task: T009 "[US1] Add unit test for cloning LoopAgent"
Task: T010 "[US1] Add integration test for LoopAgent"

# Developer B: US2 (simultaneously)
Task: T016 "[US2] Add unit test for cloning ParallelAgent"
Task: T017 "[US2] Add integration test for ParallelAgent"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (core cloning function)
3. Complete Phase 3: User Story 1 (LoopAgent)
4. **STOP and VALIDATE**: Test LoopAgent workflows independently
5. Ship if LoopAgent is the primary use case

### Incremental Delivery

1. Setup + Foundational → Core cloning works
2. Add US1 (LoopAgent) → Test → Ship (iteration use case)
3. Add US2 (ParallelAgent) → Test → Ship (concurrent use case)
4. Add US3 (Nested) → Test → Ship (complex workflow use case)

### Suggested MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 3 (User Story 1)**

This delivers:
- Core cloning function
- LoopAgent iteration preservation
- Primary use case for iterative refinement workflows

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 38 |
| **Phase 2 (Foundational)** | 7 tasks (includes 2 contract tests) |
| **US1 (LoopAgent)** | 7 tasks |
| **US2 (ParallelAgent)** | 6 tasks |
| **US3 (Nested)** | 6 tasks |
| **Phase 6 (Verification)** | 11 tasks |
| **Parallel Opportunities** | 16 tasks marked [P] |
| **Files Modified** | 4 (workflow.py, multi_agent.py, workflows.md, examples/) |
| **Files Created** | 3 (test_workflow_contracts.py, test_workflow_integration.py additions, new examples) |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Tests are written before implementation (TDD per Constitution)
- Run `uv run mkdocs build` before PR to verify docs build cleanly
- Dependency: Issue #213 (output extraction fix) should be resolved first

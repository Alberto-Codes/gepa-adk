# Tasks: Workflow Agent Evolution

**Input**: Design documents from `/specs/017-workflow-evolution/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Tests included (follows project's three-layer testing strategy per ADR-005)

**Organization**: Tasks grouped by user story to enable independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, etc.)
- Exact file paths included in all descriptions

## Path Conventions

- **Source**: `src/gepa_adk/`
- **Tests**: `tests/contracts/`, `tests/unit/`, `tests/integration/`

---

## Phase 1: Setup

**Purpose**: Create new module structure for workflow evolution

- [ ] T001 [P] Create `src/gepa_adk/adapters/workflow.py` with module docstring and imports
- [ ] T002 [P] Add `WorkflowEvolutionError` exception to `src/gepa_adk/domain/exceptions.py`

---

## Phase 2: Foundational (Type Detection - US2)

**Purpose**: Implement workflow type detection utilities that ALL other stories depend on

**⚠️ CRITICAL**: User Stories 1, 3, 4, 5 cannot proceed until type detection is complete

### User Story 2 - Detect and Classify Workflow Agent Types (Priority: P1)

**Goal**: Automatically detect whether an agent is a workflow type (SequentialAgent, LoopAgent, ParallelAgent)

**Independent Test**: Pass various agent types to `is_workflow_agent()` and verify correct True/False responses

#### Tests for User Story 2

- [ ] T003 [P] [US2] Contract test for `is_workflow_agent()` in `tests/contracts/test_workflow_contract.py`
- [ ] T004 [P] [US2] Unit test for `is_workflow_agent()` in `tests/unit/test_workflow.py`

#### Implementation for User Story 2

- [ ] T005 [US2] Implement `is_workflow_agent()` function in `src/gepa_adk/adapters/workflow.py`
- [ ] T006 [US2] Add type alias `WorkflowAgentType` to `src/gepa_adk/adapters/workflow.py`

**Checkpoint**: Type detection works for all workflow types - enables Phase 3+

---

## Phase 3: User Story 1 - Evolve Sequential Workflow Pipeline (Priority: P1) 🎯 MVP

**Goal**: Evolve all LlmAgents in a SequentialAgent workflow with a single function call

**Independent Test**: Create a SequentialAgent with 2-3 LlmAgents, call `evolve_workflow()`, verify all sub-agents have updated instructions while sequential structure is preserved

### Tests for User Story 1

- [ ] T007 [P] [US1] Contract test for `evolve_workflow()` in `tests/contracts/test_workflow_contract.py`
- [ ] T008 [P] [US1] Contract test for `find_llm_agents()` basic case in `tests/contracts/test_workflow_contract.py`
- [ ] T009 [P] [US1] Unit test for `find_llm_agents()` with SequentialAgent in `tests/unit/test_workflow.py`
- [ ] T010 [P] [US1] Integration test for `evolve_workflow()` with SequentialAgent in `tests/integration/test_workflow_integration.py`

### Implementation for User Story 1

- [ ] T011 [US1] Implement `find_llm_agents()` function (basic, non-recursive) in `src/gepa_adk/adapters/workflow.py`
- [ ] T012 [US1] Implement `evolve_workflow()` async function in `src/gepa_adk/api.py`
- [ ] T013 [US1] Add `evolve_workflow` export to `src/gepa_adk/__init__.py`
- [ ] T014 [US1] Add structlog logging to workflow traversal in `src/gepa_adk/adapters/workflow.py`
- [ ] T015 [US1] Handle empty workflow error (no LlmAgents found) with `WorkflowEvolutionError`

**Checkpoint**: SequentialAgent workflows can be evolved - MVP complete

---

## Phase 4: User Story 3 - Recursively Find Nested LlmAgents (Priority: P2)

**Goal**: Discover all LlmAgents within nested workflow structures (workflows containing workflows)

**Independent Test**: Create a workflow with 3+ levels of nesting and verify all LlmAgents at each level are discovered

### Tests for User Story 3

- [ ] T016 [P] [US3] Unit test for `find_llm_agents()` with nested workflows in `tests/unit/test_workflow.py`
- [ ] T017 [P] [US3] Unit test for `find_llm_agents()` with `max_depth` limiting in `tests/unit/test_workflow.py`
- [ ] T018 [P] [US3] Unit test for `find_llm_agents()` skipping non-string instructions in `tests/unit/test_workflow.py`

### Implementation for User Story 3

- [ ] T019 [US3] Extend `find_llm_agents()` with recursive traversal in `src/gepa_adk/adapters/workflow.py`
- [ ] T020 [US3] Add `max_depth` parameter support to `find_llm_agents()` in `src/gepa_adk/adapters/workflow.py`
- [ ] T021 [US3] Add check to skip LlmAgents with non-string instructions (InstructionProvider) in `src/gepa_adk/adapters/workflow.py`
- [ ] T022 [US3] Add logging for skipped agents (non-string instruction warning) in `src/gepa_adk/adapters/workflow.py`

**Checkpoint**: Nested workflows are fully supported with depth limiting

---

## Phase 5: User Story 4 - Evolve LoopAgent Workflows (Priority: P2)

**Goal**: Evolve LlmAgents within LoopAgent workflows while preserving loop configuration

**Independent Test**: Create a LoopAgent with LlmAgent sub-agents and verify evolution completes while loop config is preserved

### Tests for User Story 4

- [ ] T023 [P] [US4] Unit test for `find_llm_agents()` with LoopAgent in `tests/unit/test_workflow.py`
- [ ] T024 [P] [US4] Integration test for `evolve_workflow()` with LoopAgent in `tests/integration/test_workflow_integration.py`

### Implementation for User Story 4

- [ ] T025 [US4] Verify `is_workflow_agent()` handles LoopAgent correctly in `src/gepa_adk/adapters/workflow.py`
- [ ] T026 [US4] Add LoopAgent-specific documentation to `evolve_workflow()` docstring in `src/gepa_adk/api.py`

**Checkpoint**: LoopAgent workflows can be evolved

---

## Phase 6: User Story 5 - Evolve ParallelAgent Workflows (Priority: P2)

**Goal**: Evolve all parallel branch agents in a ParallelAgent workflow

**Independent Test**: Create a ParallelAgent with multiple LlmAgent branches and verify all are evolved

### Tests for User Story 5

- [ ] T027 [P] [US5] Unit test for `find_llm_agents()` with ParallelAgent in `tests/unit/test_workflow.py`
- [ ] T028 [P] [US5] Integration test for `evolve_workflow()` with ParallelAgent in `tests/integration/test_workflow_integration.py`

### Implementation for User Story 5

- [ ] T029 [US5] Verify `is_workflow_agent()` handles ParallelAgent correctly in `src/gepa_adk/adapters/workflow.py`
- [ ] T030 [US5] Add ParallelAgent-specific documentation to `evolve_workflow()` docstring in `src/gepa_adk/api.py`

**Checkpoint**: ParallelAgent workflows can be evolved

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and quality improvements

- [ ] T031 [P] Add module exports to `src/gepa_adk/adapters/__init__.py` for workflow utilities
- [ ] T032 [P] Update `src/gepa_adk/__init__.py` `__all__` list with `evolve_workflow`
- [ ] T033 [P] Add comprehensive docstrings to all functions following Google style (ADR-010)
- [ ] T034 Run `uv run ruff check --fix` and `uv run ruff format` on all modified files
- [ ] T035 Run `uv run ty check` for type checking
- [ ] T036 Run full test suite: `uv run pytest -n auto`
- [ ] T037 Validate against `specs/017-workflow-evolution/quickstart.md` examples

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──────────────────────────────────────┐
                                                      ▼
Phase 2 (US2: Type Detection) ◄── BLOCKS ALL ──► Phase 3-6
                                                      │
                                                      ▼
Phase 3 (US1: Sequential) ─── MVP ───────────────────►│
                                                      │
Phase 4 (US3: Recursive) ─────────────────────────────┤
                                                      │
Phase 5 (US4: LoopAgent) ─────────────────────────────┤
                                                      │
Phase 6 (US5: ParallelAgent) ─────────────────────────┤
                                                      ▼
Phase 7 (Polish) ◄────────────────────────────────────┘
```

### User Story Dependencies

| Story | Depends On | Can Start After |
|-------|------------|-----------------|
| **US2** (Type Detection) | Phase 1 | T001, T002 complete |
| **US1** (Sequential) | US2 | T005, T006 complete |
| **US3** (Recursive) | US1 | T011 complete (extends find_llm_agents) |
| **US4** (LoopAgent) | US2 | T005, T006 complete |
| **US5** (ParallelAgent) | US2 | T005, T006 complete |

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Utility functions before API functions
3. Implementation before logging/error handling refinements
4. Story complete before moving to next priority

### Parallel Opportunities

**Phase 1** (all parallel):
- T001 and T002 can run simultaneously

**Phase 2** (within US2):
- T003 and T004 (tests) can run in parallel
- T005 then T006 (sequential - type alias needs function)

**Phase 3** (within US1):
- T007, T008, T009, T010 (all tests) can run in parallel
- T011 → T012 → T013 (implementation chain)
- T014, T015 can run in parallel after T012

**After Phase 2 completes**:
- US4 (Phase 5) and US5 (Phase 6) can run in parallel with US3 (Phase 4)

---

## Parallel Example: Phase 3 (User Story 1)

```bash
# Launch all tests for US1 together (they should FAIL initially):
# T007: Contract test for evolve_workflow()
# T008: Contract test for find_llm_agents()
# T009: Unit test for find_llm_agents()
# T010: Integration test for evolve_workflow()

# Then implement sequentially:
# T011 → T012 → T013 (main implementation chain)

# Then in parallel:
# T014: Add logging
# T015: Error handling
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. ✅ Complete Phase 1: Setup (T001-T002)
2. ✅ Complete Phase 2: Type Detection - US2 (T003-T006)
3. ✅ Complete Phase 3: Sequential Workflow - US1 (T007-T015)
4. **STOP and VALIDATE**: Test with quickstart.md SequentialAgent example
5. Deploy/demo if ready - MVP delivers core value!

### Incremental Delivery

1. Setup + US2 → Foundation ready
2. Add US1 → MVP! Sequential workflows work
3. Add US3 → Nested workflows work
4. Add US4 + US5 → All workflow types supported
5. Polish → Production ready

### Test-Driven Development

Each user story follows TDD:
1. Write contract/unit/integration tests (they FAIL)
2. Implement minimum code to pass tests
3. Refactor while keeping tests green
4. Add logging and polish

---

## Task Summary

| Phase | User Story | Task Count | Parallel Tasks |
|-------|------------|------------|----------------|
| 1 | Setup | 2 | 2 |
| 2 | US2 (Type Detection) | 4 | 2 |
| 3 | US1 (Sequential) 🎯 | 9 | 4 |
| 4 | US3 (Recursive) | 7 | 3 |
| 5 | US4 (LoopAgent) | 4 | 2 |
| 6 | US5 (ParallelAgent) | 4 | 2 |
| 7 | Polish | 7 | 3 |
| **Total** | | **37** | **18** |

---

## Notes

- MVP scope: Phases 1-3 (Setup + US2 + US1) = 15 tasks
- Full feature: All phases = 37 tasks
- [P] tasks can run in parallel (different files, no dependencies)
- Three-layer testing per ADR-005: contracts → unit → integration
- Google-style docstrings per ADR-010
- Structured logging per ADR-008
- Exception hierarchy per ADR-009 (WorkflowEvolutionError)

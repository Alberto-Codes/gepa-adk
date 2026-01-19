# Tasks: Multi-Agent Unified Executor

**Input**: Design documents from `/specs/125-multi-agent-executor/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included as this is an internal API change requiring contract verification per Constitution IV.

**Documentation**: Per Constitution Principle VI, this feature requires updates to `docs/guides/multi-agent.md` and `examples/multi_agent.py`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root
- Paths shown below use gepa-adk structure from plan.md

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| New public API | Required | Required |

**Static pages** (manual updates): `docs/guides/multi-agent.md`
**Auto-generated** (no manual updates): `docs/reference/` (from docstrings via mkdocstrings)

---

## Phase 1: Setup

**Purpose**: No new setup needed - feature extends existing modules

- [ ] T001 Verify PR #138 (AgentExecutor) is merged and available in develop branch
- [ ] T002 Verify existing multi-agent tests pass before modifications with `pytest tests/unit/adapters/test_multi_agent.py -v`

**Checkpoint**: Baseline verified - ready for implementation

---

## Phase 2: Foundational

**Purpose**: Core infrastructure that MUST be complete before user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Create MockExecutor test utility in tests/conftest.py for contract testing (from contracts/multi-agent-executor.md)
- [ ] T004 Add AgentExecutorProtocol import to src/gepa_adk/adapters/multi_agent.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Unified Multi-Agent Evolution (Priority: P1) 🎯 MVP

**Goal**: `evolve_group()` creates and uses unified AgentExecutor for all agent types

**Independent Test**: Call `evolve_group()` with multiple agents and critic, verify logs show `uses_executor=True`

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T005 [P] [US1] Contract test for evolve_group executor creation (FR-003) in tests/contracts/test_multi_agent_executor_contract.py
- [ ] T006 [P] [US1] Contract test for evolve_group executor passing (FR-004, FR-005, FR-006) in tests/contracts/test_multi_agent_executor_contract.py
- [ ] T007 [P] [US1] Contract test for uses_executor logging (FR-008) in tests/contracts/test_multi_agent_executor_contract.py

### Implementation for User Story 1

- [ ] T008 [US1] Modify evolve_group() to create AgentExecutor at start in src/gepa_adk/api.py (FR-003)
- [ ] T009 [US1] Modify evolve_group() to pass executor to CriticScorer in src/gepa_adk/api.py (FR-005)
- [ ] T010 [US1] Modify evolve_group() to pass executor to create_adk_reflection_fn in src/gepa_adk/api.py (FR-006)
- [ ] T011 [US1] Modify evolve_group() to pass executor to MultiAgentAdapter in src/gepa_adk/api.py (FR-004)
- [ ] T012 [US1] Run tests to verify US1 implementation with `pytest tests/contracts/test_multi_agent_executor_contract.py -v`

**Checkpoint**: evolve_group() now uses unified executor for all components

---

## Phase 4: User Story 2 - MultiAgentAdapter Executor Integration (Priority: P1)

**Goal**: `MultiAgentAdapter` accepts executor parameter and uses it for all executions

**Independent Test**: Instantiate `MultiAgentAdapter` with explicit executor, verify all executions use it

### Tests for User Story 2

- [ ] T013 [P] [US2] Contract test for MultiAgentAdapter executor parameter (FR-001) in tests/contracts/test_multi_agent_executor_contract.py
- [ ] T014 [P] [US2] Contract test for executor used in executions (FR-002) in tests/contracts/test_multi_agent_executor_contract.py
- [ ] T015 [P] [US2] Contract test for backward compatibility (FR-009) in tests/contracts/test_multi_agent_executor_contract.py

### Implementation for User Story 2

- [ ] T016 [US2] Add executor parameter to MultiAgentAdapter.__init__() in src/gepa_adk/adapters/multi_agent.py (FR-001)
- [ ] T017 [US2] Store executor as self._executor and add uses_executor to logger binding in src/gepa_adk/adapters/multi_agent.py
- [ ] T018 [US2] Modify _run_shared_session() to use executor when available in src/gepa_adk/adapters/multi_agent.py (FR-002)
- [ ] T019 [US2] Modify _run_isolated_sessions() to use executor when available in src/gepa_adk/adapters/multi_agent.py (FR-002)
- [ ] T020 [US2] Update MultiAgentAdapter docstrings with executor parameter documentation in src/gepa_adk/adapters/multi_agent.py
- [ ] T021 [US2] Run tests to verify US2 implementation with `pytest tests/contracts/test_multi_agent_executor_contract.py tests/unit/adapters/test_multi_agent.py -v`

### Documentation for User Story 2

- [ ] T022 [P] [US2] Update docs/guides/multi-agent.md with executor parameter documentation
- [ ] T023 [P] [US2] Update examples/multi_agent.py to demonstrate executor usage (optional advanced example)

**Checkpoint**: MultiAgentAdapter now supports executor parameter with full backward compatibility

---

## Phase 5: User Story 3 - Workflow Evolution Executor Support (Priority: P2)

**Goal**: `evolve_workflow()` inherits executor support via `evolve_group()` delegation

**Independent Test**: Call `evolve_workflow()` with SequentialAgent, verify executor is used

### Tests for User Story 3

- [ ] T024 [P] [US3] Contract test for evolve_workflow executor inheritance (FR-007) in tests/contracts/test_multi_agent_executor_contract.py

### Implementation for User Story 3

- [ ] T025 [US3] Verify evolve_workflow() delegates to evolve_group() correctly in src/gepa_adk/api.py (no code change expected)
- [ ] T026 [US3] Run tests to verify US3 implementation with `pytest tests/contracts/test_multi_agent_executor_contract.py -v -k workflow`

**Checkpoint**: Workflow evolution uses unified executor automatically

---

## Phase 6: Integration & Verification

**Purpose**: End-to-end verification and cross-cutting concerns

### Integration Tests

- [ ] T027 [P] Integration test for multi-agent evolution with executor in tests/integration/test_multi_agent_executor_integration.py
- [ ] T028 [P] Integration test for workflow evolution with executor in tests/integration/test_multi_agent_executor_integration.py

### Documentation Build Verification (REQUIRED)

- [ ] T029 Verify `uv run mkdocs build` passes without warnings
- [ ] T030 Preview docs with `uv run mkdocs serve` and verify multi-agent guide renders correctly

### Final Verification

- [ ] T031 Run full test suite with `pytest -n auto` to verify no regressions
- [ ] T032 Run code quality checks with `scripts/code_quality_check.sh --all`
- [ ] T033 Run quickstart.md validation manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verify baseline
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - core evolve_group changes
- **User Story 2 (Phase 4)**: Depends on Foundational - can run parallel with US1
- **User Story 3 (Phase 5)**: Depends on US1 completion (evolve_workflow uses evolve_group)
- **Integration (Phase 6)**: Depends on all user stories

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Independent of US1
- **User Story 3 (P2)**: Depends on US1 (evolve_workflow delegates to evolve_group)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation tasks are sequential within each story
- Documentation can run parallel with implementation
- Story complete before moving to next priority

### Parallel Opportunities

**User Stories 1 & 2 can be developed in parallel** since:
- US1 modifies `api.py` (evolve_group)
- US2 modifies `adapters/multi_agent.py` (MultiAgentAdapter)
- Different files, no conflicts

**Within each story**, test tasks marked [P] can run in parallel.

---

## Parallel Example: User Stories 1 & 2 Together

```bash
# Developer A works on User Story 1 (api.py):
Task T005: Contract test for evolve_group executor creation
Task T006: Contract test for evolve_group executor passing
Task T008-T011: Implementation in api.py

# Developer B works on User Story 2 (multi_agent.py):
Task T013: Contract test for executor parameter
Task T014: Contract test for executor usage
Task T016-T020: Implementation in multi_agent.py

# Both merge when complete, then US3 can verify workflow support
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify baseline)
2. Complete Phase 2: Foundational (MockExecutor)
3. Complete Phase 3: User Story 1 (evolve_group changes)
4. **STOP and VALIDATE**: Test evolve_group independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → evolve_group has executor (MVP!)
3. Add User Story 2 → Test independently → MultiAgentAdapter has executor
4. Add User Story 3 → Test independently → evolve_workflow verified
5. Integration tests → Full verification

### Parallel Team Strategy

With two developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (api.py)
   - Developer B: User Story 2 (multi_agent.py)
3. After both complete: User Story 3 (verification only)
4. Integration tests together

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Run `uv run mkdocs build` before PR to verify docs build cleanly
- FR-xxx references map to Functional Requirements in spec.md

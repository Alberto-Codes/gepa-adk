# Tasks: Unified Agent Executor

**Input**: Design documents from `/specs/124-unified-agent-executor/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, architecture.md
**Related Issue**: [#135](https://github.com/Alberto-Codes/gepa-adk/issues/135)

**Tests**: Included per architecture.md testing strategy (ADR-005 three-layer testing)

**Documentation**: Per Constitution Principle VI, this is an internal refactor with no user-facing API changes. Documentation tasks are NOT required (see scope table).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| Internal refactor | Not required | Not required |

This feature is an internal refactor - no public API changes. Auto-generated reference docs will update from docstrings automatically.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new files and project structure for AgentExecutor

- [x] T001 Create ports module file `src/gepa_adk/ports/agent_executor.py` with module docstring
- [x] T002 Create adapters module file `src/gepa_adk/adapters/agent_executor.py` with module docstring
- [x] T003 [P] Create contract test file `tests/contracts/test_agent_executor_protocol.py`
- [x] T004 [P] Create unit test file `tests/unit/adapters/test_agent_executor.py`
- [x] T005 [P] Create integration test file `tests/integration/test_unified_execution.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types and protocol that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Define `ExecutionStatus` enum (SUCCESS/FAILED/TIMEOUT) in `src/gepa_adk/ports/agent_executor.py`
- [x] T007 Define `ExecutionResult` dataclass in `src/gepa_adk/ports/agent_executor.py`
- [x] T008 Define `AgentExecutorProtocol` with `execute_agent()` signature in `src/gepa_adk/ports/agent_executor.py`
- [x] T009 Export new types from `src/gepa_adk/ports/__init__.py`
- [x] T010 Write contract test verifying AgentExecutor implements AgentExecutorProtocol in `tests/contracts/test_agent_executor_protocol.py`

**Checkpoint**: Foundation ready - protocol and types defined, contract test written (failing)

---

## Phase 3: User Story 1 - Unified Agent Execution (Priority: P1) MVP

**Goal**: All agent types (generator, critic, reflection) execute through a single unified mechanism with consistent result handling

**Independent Test**: Configure an agent with any ADK feature and verify the feature works identically for all agent types

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T011 [P] [US1] Unit test: AgentExecutor creates session and executes agent in `tests/unit/adapters/test_agent_executor.py`
- [x] T012 [P] [US1] Unit test: AgentExecutor captures events during execution in `tests/unit/adapters/test_agent_executor.py`
- [x] T013 [P] [US1] Unit test: AgentExecutor extracts output from session state in `tests/unit/adapters/test_agent_executor.py`
- [x] T014 [P] [US1] Unit test: AgentExecutor returns consistent ExecutionResult in `tests/unit/adapters/test_agent_executor.py`

### Implementation for User Story 1

- [x] T015 [US1] Implement `AgentExecutor.__init__()` with session_service and app_name in `src/gepa_adk/adapters/agent_executor.py`
- [x] T016 [US1] Implement `AgentExecutor._create_session()` for new session creation in `src/gepa_adk/adapters/agent_executor.py`
- [x] T017 [US1] Implement `AgentExecutor._execute_runner()` core Runner.run_async() loop in `src/gepa_adk/adapters/agent_executor.py`
- [x] T018 [US1] Implement `AgentExecutor._extract_output()` from session state with event fallback in `src/gepa_adk/adapters/agent_executor.py`
- [x] T019 [US1] Implement `AgentExecutor.execute_agent()` orchestrating session, runner, extraction in `src/gepa_adk/adapters/agent_executor.py`
- [x] T020 [US1] Add structlog logging for execution lifecycle in `src/gepa_adk/adapters/agent_executor.py`
- [x] T021 [US1] Export AgentExecutor from `src/gepa_adk/adapters/__init__.py`
- [x] T022 [US1] Verify contract test passes (AgentExecutor implements protocol)

**Checkpoint**: AgentExecutor can execute any agent and return consistent ExecutionResult

---

## Phase 4: User Story 2 - Session Sharing Between Agents (Priority: P2)

**Goal**: Agents can optionally share session state so critic can access generator state

**Independent Test**: Run generator that sets session state, then run critic with same session ID and verify it reads those values

### Tests for User Story 2

- [x] T023 [P] [US2] Unit test: AgentExecutor retrieves existing session by ID in `tests/unit/adapters/test_agent_executor.py`
- [x] T024 [P] [US2] Unit test: AgentExecutor raises error for invalid session ID in `tests/unit/adapters/test_agent_executor.py`
- [x] T025 [P] [US2] Integration test: Critic accesses generator session state in `tests/integration/test_unified_execution.py`

### Implementation for User Story 2

- [x] T026 [US2] Implement `AgentExecutor._get_session()` for session retrieval in `src/gepa_adk/adapters/agent_executor.py`
- [x] T027 [US2] Add `existing_session_id` parameter handling in `execute_agent()` in `src/gepa_adk/adapters/agent_executor.py`
- [x] T028 [US2] Implement `SessionNotFoundError` exception in `src/gepa_adk/adapters/agent_executor.py` (moved from domain/exceptions.py)
- [x] T029 [US2] Add validation for session existence when `existing_session_id` provided in `src/gepa_adk/adapters/agent_executor.py`

**Checkpoint**: Agents can share session state via existing_session_id parameter

---

## Phase 5: User Story 3 - Runtime Configuration Overrides (Priority: P3)

**Goal**: Override agent instructions or output schemas at runtime without modifying original agent

**Independent Test**: Provide instruction override during execution and verify agent uses override while original remains unchanged

### Tests for User Story 3

- [x] T030 [P] [US3] Unit test: instruction_override replaces agent instruction for single execution in `tests/unit/adapters/test_agent_executor.py`
- [x] T031 [P] [US3] Unit test: output_schema_override replaces agent schema for single execution in `tests/unit/adapters/test_agent_executor.py`
- [x] T032 [P] [US3] Unit test: Original agent unchanged after override execution in `tests/unit/adapters/test_agent_executor.py`

### Implementation for User Story 3

- [x] T033 [US3] Implement `AgentExecutor._apply_overrides()` to create modified agent copy in `src/gepa_adk/adapters/agent_executor.py`
- [x] T034 [US3] Add `instruction_override` handling in `execute_agent()` in `src/gepa_adk/adapters/agent_executor.py`
- [x] T035 [US3] Add `output_schema_override` handling in `execute_agent()` in `src/gepa_adk/adapters/agent_executor.py`
- [x] T036 [US3] Add `session_state` parameter for template variable injection in `execute_agent()` in `src/gepa_adk/adapters/agent_executor.py`

**Checkpoint**: Runtime overrides work without side effects on original agent

---

## Phase 6: User Story 4 - Configurable Timeout and Error Handling (Priority: P4)

**Goal**: Configurable timeout handling for agent execution with graceful TIMEOUT status

**Independent Test**: Configure short timeout and verify execution terminates gracefully with TIMEOUT status

### Tests for User Story 4

- [x] T037 [P] [US4] Unit test: Execution returns TIMEOUT status when timeout exceeded in `tests/unit/adapters/test_agent_executor.py`
- [x] T038 [P] [US4] Unit test: Partial events captured even on timeout in `tests/unit/adapters/test_agent_executor.py`
- [x] T039 [P] [US4] Unit test: Execution returns FAILED status with error_message on exception in `tests/unit/adapters/test_agent_executor.py`

### Implementation for User Story 4

- [x] T040 [US4] Implement `AgentExecutor._execute_with_timeout()` using asyncio.timeout in `src/gepa_adk/adapters/agent_executor.py`
- [x] T041 [US4] Add timeout_seconds parameter handling in `execute_agent()` in `src/gepa_adk/adapters/agent_executor.py`
- [x] T042 [US4] Implement error handling to return FAILED status with error_message in `src/gepa_adk/adapters/agent_executor.py`
- [x] T043 [US4] Ensure captured_events populated even on timeout/failure in `src/gepa_adk/adapters/agent_executor.py`

**Checkpoint**: Timeout and error handling work gracefully with proper status codes

---

## Phase 7: Migration (Consumer Updates)

**Purpose**: Migrate existing code to use AgentExecutor

**Prerequisite**: All user stories (US1-US4) must be complete before migration

### Integration Tests for Migration

- [ ] T044 [P] Integration test: ADKAdapter produces identical results with AgentExecutor in `tests/integration/test_unified_execution.py`
- [ ] T045 [P] Integration test: CriticScorer produces identical results with AgentExecutor in `tests/integration/test_unified_execution.py`
- [ ] T046 [P] Integration test: Reflection function produces identical results with AgentExecutor in `tests/integration/test_unified_execution.py`
- [ ] T047 [P] Integration test: Existing evolution tests still pass (backward compatibility) in `tests/integration/test_unified_execution.py`

### Migration Implementation

- [ ] T048 Update `ADKAdapter.__init__()` to accept optional `executor: AgentExecutorProtocol` in `src/gepa_adk/adapters/adk_adapter.py`
- [ ] T049 Refactor `ADKAdapter._run_single_example()` to use AgentExecutor in `src/gepa_adk/adapters/adk_adapter.py`
- [ ] T050 Remove duplicated Runner/session code from ADKAdapter in `src/gepa_adk/adapters/adk_adapter.py`
- [ ] T051 Update `CriticScorer.__init__()` to accept optional `executor: AgentExecutorProtocol` in `src/gepa_adk/adapters/critic_scorer.py`
- [ ] T052 Refactor `CriticScorer.async_score()` to use AgentExecutor in `src/gepa_adk/adapters/critic_scorer.py`
- [ ] T053 Remove duplicated Runner/session code from CriticScorer in `src/gepa_adk/adapters/critic_scorer.py`
- [ ] T054 Update `create_adk_reflection_fn()` to accept optional `executor: AgentExecutorProtocol` in `src/gepa_adk/engine/adk_reflection.py`
- [ ] T055 Refactor reflection function to use AgentExecutor in `src/gepa_adk/engine/adk_reflection.py`
- [ ] T056 Remove duplicated Runner/session code from adk_reflection in `src/gepa_adk/engine/adk_reflection.py`

**Checkpoint**: All consumers migrated, backward compatibility verified

---

## Phase 8: Verification & Cross-Cutting Concerns

**Purpose**: Final verification and cleanup

### Verification

- [ ] T057 Run full test suite: `uv run pytest` - all tests pass
- [ ] T058 Run type checking: `uv run pyright` - no errors
- [ ] T059 Run linting: `uv run ruff check .` - no errors
- [ ] T060 Verify `uv run mkdocs build` passes without warnings (docstrings valid)

### Cleanup

- [ ] T061 [P] Consolidate duplicate extraction utilities from ADKAdapter to `src/gepa_adk/utils/events.py`
- [ ] T062 [P] Remove any dead code from migrated files
- [ ] T063 Run quickstart.md validation manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (Phase 3): Foundation for all other stories
  - US2 (Phase 4): Can start after US1 (session reuse builds on basic execution)
  - US3 (Phase 5): Can start after US1 (overrides extend basic execution)
  - US4 (Phase 6): Can start after US1 (timeout extends basic execution)
- **Migration (Phase 7)**: Depends on ALL user stories being complete
- **Verification (Phase 8)**: Depends on Migration completion

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after US1 - builds on session creation
- **User Story 3 (P3)**: Can start after US1 - builds on basic execution
- **User Story 4 (P4)**: Can start after US1 - builds on basic execution

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation tasks are sequential (build on each other)
- Story complete when tests pass

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T003, T004, T005 can run in parallel (different test files)
```

**Phase 2 (Foundational)**:
```
T006, T007, T008 are sequential (build on each other in same file)
```

**Phase 3 (US1 Tests)**:
```
T011, T012, T013, T014 can run in parallel (different test cases)
```

**Phase 4, 5, 6 (US2, US3, US4)**:
```
After US1 complete, US2/US3/US4 can proceed in parallel if desired
```

**Phase 7 (Migration)**:
```
T044, T045, T046, T047 can run in parallel (integration tests)
T048-T050 (ADKAdapter), T051-T053 (CriticScorer), T054-T056 (Reflection) can run in parallel
```

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all unit tests for User Story 1 together:
Task: "Unit test: AgentExecutor creates session and executes agent"
Task: "Unit test: AgentExecutor captures events during execution"
Task: "Unit test: AgentExecutor extracts output from session state"
Task: "Unit test: AgentExecutor returns consistent ExecutionResult"
```

## Parallel Example: Migration Implementation

```bash
# Launch all consumer migrations in parallel:
Task: "Update ADKAdapter to use AgentExecutor" (T048-T050)
Task: "Update CriticScorer to use AgentExecutor" (T051-T053)
Task: "Update adk_reflection to use AgentExecutor" (T054-T056)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test AgentExecutor independently
5. Can proceed with migration even without US2-US4 if basic execution is sufficient

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Core execution works (MVP!)
3. Add User Story 2 → Test independently → Session sharing works
4. Add User Story 3 → Test independently → Overrides work
5. Add User Story 4 → Test independently → Timeout/error handling works
6. Complete Migration → Backward compatibility verified
7. Each story adds capability without breaking previous stories

### Recommended Order for Solo Developer

1. Phase 1: Setup (T001-T005)
2. Phase 2: Foundational (T006-T010)
3. Phase 3: User Story 1 (T011-T022) - MVP milestone
4. Phase 4: User Story 2 (T023-T029)
5. Phase 5: User Story 3 (T030-T036)
6. Phase 6: User Story 4 (T037-T043)
7. Phase 7: Migration (T044-T056)
8. Phase 8: Verification (T057-T063)

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1. Setup | T001-T005 | Create files and project structure |
| 2. Foundational | T006-T010 | Core types and protocol |
| 3. US1 (P1) MVP | T011-T022 | Unified agent execution |
| 4. US2 (P2) | T023-T029 | Session sharing |
| 5. US3 (P3) | T030-T036 | Runtime overrides |
| 6. US4 (P4) | T037-T043 | Timeout and error handling |
| 7. Migration | T044-T056 | Consumer updates |
| 8. Verification | T057-T063 | Final verification |

**Total Tasks**: 63
**Parallel Opportunities**: Multiple per phase (marked with [P])
**MVP Scope**: Phases 1-3 (22 tasks) for core functionality

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

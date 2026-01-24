# Tasks: Support ADK App/Runner Pattern for Evolution

**Input**: Design documents from `/specs/227-app-runner-pattern/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Three-layer testing required per plan.md (unit + integration)

**Documentation**: Per Constitution Principle VI, this is a new public API feature - docs/ updates REQUIRED within each user story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root
- Paths based on plan.md structure

---

## Phase 1: Setup

**Purpose**: Add imports and create helper function foundation

- [ ] T001 Add `App` and `Runner` imports to `src/gepa_adk/api.py`
- [ ] T002 Create `_resolve_evolution_services()` helper function in `src/gepa_adk/api.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modify reflection agent to accept session_service - required by all user stories

**CRITICAL**: This must complete before user story implementation

- [ ] T003 Add optional `session_service` parameter to `create_adk_reflection_fn()` in `src/gepa_adk/engine/adk_reflection.py`
- [ ] T004 Update internal Runner creation in `create_adk_reflection_fn()` to use provided session_service

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Existing Infrastructure Integration (Priority: P1)

**Goal**: Enable passing pre-configured App instance to all evolution APIs, with services extracted and used for all agent executions (evolved agents, critic, reflection)

**Independent Test**: Configure an App with custom session service, invoke `evolve()`, verify sessions are created using the custom service

### Implementation for User Story 1

- [ ] T005 [US1] Add `app` and `runner` parameters to `evolve()` signature in `src/gepa_adk/api.py`
- [ ] T006 [US1] Add service resolution logic to `evolve()` using `_resolve_evolution_services()` in `src/gepa_adk/api.py`
- [ ] T007 [US1] Pass resolved session_service to AgentExecutor creation in `evolve()` in `src/gepa_adk/api.py`
- [ ] T008 [US1] Pass resolved session_service to reflection agent setup in `evolve()` in `src/gepa_adk/api.py`
- [ ] T009 [US1] Add precedence warning when both runner and executor provided in `evolve()` in `src/gepa_adk/api.py`
- [ ] T010 [US1] Update `evolve()` docstring with app/runner parameter documentation in `src/gepa_adk/api.py`

### Tests for User Story 1

- [ ] T011 [P] [US1] Unit test: `evolve()` with app parameter uses default session in `tests/unit/test_api_app_runner.py`
- [ ] T012 [P] [US1] Unit test: `evolve()` runner takes precedence over executor in `tests/unit/test_api_app_runner.py`
- [ ] T013 [P] [US1] Unit test: `_resolve_evolution_services()` precedence logic in `tests/unit/test_api_app_runner.py`

### Documentation for User Story 1

- [ ] T014 [P] [US1] Add App/Runner integration example for `evolve()` in `docs/guides/single-agent.md`

**Checkpoint**: Single agent evolution with App/Runner works independently

---

## Phase 4: User Story 2 - Runner-Based Evolution (Priority: P2)

**Goal**: Enable passing pre-configured Runner to `evolve_group()` and `evolve_workflow()`, extracting session_service and artifact_service

**Independent Test**: Create Runner with custom session service, pass to `evolve_workflow()`, verify all sessions use the Runner's service

### Implementation for User Story 2

- [ ] T015 [US2] Add `app` and `runner` parameters to `evolve_group()` signature in `src/gepa_adk/api.py`
- [ ] T016 [US2] Add service resolution logic to `evolve_group()` using `_resolve_evolution_services()` in `src/gepa_adk/api.py`
- [ ] T017 [US2] Pass resolved session_service through `evolve_group()` to AgentExecutor in `src/gepa_adk/api.py`
- [ ] T018 [US2] Pass resolved session_service to reflection agent setup in `evolve_group()` in `src/gepa_adk/api.py`
- [ ] T019 [US2] Add `app` and `runner` parameters to `evolve_workflow()` signature in `src/gepa_adk/api.py`
- [ ] T020 [US2] Pass app/runner through `evolve_workflow()` to `evolve_group()` call in `src/gepa_adk/api.py`
- [ ] T021 [US2] Update `evolve_group()` docstring with app/runner parameter documentation in `src/gepa_adk/api.py`
- [ ] T022 [US2] Update `evolve_workflow()` docstring with app/runner parameter documentation in `src/gepa_adk/api.py`

### Tests for User Story 2

- [ ] T023 [P] [US2] Unit test: `evolve_group()` with runner extracts services in `tests/unit/test_api_app_runner.py`
- [ ] T024 [P] [US2] Unit test: `evolve_workflow()` passes runner to evolve_group in `tests/unit/test_api_app_runner.py`
- [ ] T025 [P] [US2] Unit test: runner takes precedence over session_service param in `tests/unit/test_api_app_runner.py`
- [ ] T026 [P] [US2] Integration test: Runner services used across workflow evolution in `tests/integration/test_app_runner_integration.py`

### Documentation for User Story 2

- [ ] T027 [P] [US2] Add App/Runner integration example for `evolve_group()` in `docs/guides/multi-agent.md`
- [ ] T028 [P] [US2] Add App/Runner integration example for `evolve_workflow()` in `docs/guides/workflows.md`

**Checkpoint**: Multi-agent and workflow evolution with Runner works independently

---

## Phase 5: User Story 3 - Backward Compatible Direct Workflow (Priority: P3)

**Goal**: Verify existing code without app/runner parameters continues to work unchanged

**Independent Test**: Run existing tests and verify no regressions; call all APIs without new params

### Tests for User Story 3

- [ ] T029 [P] [US3] Unit test: `evolve()` without app/runner uses existing defaults in `tests/unit/test_api_app_runner.py`
- [ ] T030 [P] [US3] Unit test: `evolve_group()` without app/runner uses InMemorySessionService in `tests/unit/test_api_app_runner.py`
- [ ] T031 [P] [US3] Unit test: `evolve_workflow()` without app/runner behavior unchanged in `tests/unit/test_api_app_runner.py`
- [ ] T032 [US3] Run existing test suite to verify no regressions via `pytest tests/`

### Documentation for User Story 3

- [ ] T033 [US3] Add backward compatibility note to quickstart in `docs/guides/quickstart.md`

**Checkpoint**: All existing integrations work without modification

---

## Phase 6: Verification & Cross-Cutting Concerns

**Purpose**: Final verification and polish

### Validation

- [ ] T034 Add warning log when both runner and app provided in `_resolve_evolution_services()` in `src/gepa_adk/api.py`
- [ ] T035 [P] Integration test: warning logged when runner and app both provided in `tests/integration/test_app_runner_integration.py`

### Documentation Build Verification

- [ ] T036 Verify `uv run mkdocs build` passes without warnings
- [ ] T037 Preview docs with `uv run mkdocs serve` and verify App/Runner examples render correctly

### Cross-Cutting

- [ ] T038 Run full test suite `pytest tests/` to verify all tests pass
- [ ] T039 Run linter `ruff check src/gepa_adk/api.py src/gepa_adk/engine/adk_reflection.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2
- **User Story 2 (Phase 4)**: Depends on Phase 2 (can run in parallel with US1)
- **User Story 3 (Phase 5)**: Depends on Phases 3 and 4 (verification of both)
- **Verification (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent after Foundational - focuses on `evolve()`
- **User Story 2 (P2)**: Independent after Foundational - focuses on `evolve_group()` and `evolve_workflow()`
- **User Story 3 (P3)**: Depends on US1 and US2 completion (regression testing)

### Within Each User Story

- Implementation tasks in sequence (signature → logic → docstrings)
- Tests can run in parallel (marked [P])
- Documentation can run in parallel with tests (marked [P])

### Parallel Opportunities

**Phase 1**: T001 and T002 are sequential (T002 needs imports from T001)

**Phase 2**: T003 and T004 are sequential (T004 uses T003's parameter)

**Phase 3 (US1)**:
- Tests T011, T012, T013 can run in parallel
- T014 (docs) can run in parallel with tests

**Phase 4 (US2)**:
- Tests T023, T024, T025, T026 can run in parallel
- Docs T027, T028 can run in parallel with tests

**Phase 5 (US3)**:
- Tests T029, T030, T031 can run in parallel

**Cross-story parallelism**:
- US1 and US2 can proceed in parallel after Foundational phase completes

---

## Parallel Example: User Story 2

```bash
# After US2 implementation tasks complete, launch tests in parallel:
Task: "Unit test: evolve_group() with runner extracts services"
Task: "Unit test: evolve_workflow() passes runner to evolve_group"
Task: "Unit test: runner takes precedence over session_service param"
Task: "Integration test: Runner services used across workflow evolution"

# Launch docs in parallel with tests:
Task: "Add App/Runner integration example for evolve_group()"
Task: "Add App/Runner integration example for evolve_workflow()"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T004)
3. Complete Phase 3: User Story 1 (T005-T014)
4. **STOP and VALIDATE**: Test `evolve()` with App/Runner
5. Deploy if single-agent evolution is sufficient

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → `evolve()` works with App/Runner
3. Add User Story 2 → `evolve_group()` and `evolve_workflow()` work with App/Runner
4. Add User Story 3 → Backward compatibility verified
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With 2 developers after Foundational:
- Developer A: User Story 1 (`evolve()`)
- Developer B: User Story 2 (`evolve_group()`, `evolve_workflow()`)

Then together: User Story 3 (regression verification)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- All new parameters are optional - backward compatibility is guaranteed
- Reflection agent shares session_service with evolved agents (research.md decision)
- Plugin passthrough deferred to #231
- No new domain models or ports needed (research.md decision)

# Tasks: Public API (evolve, evolve_sync)

**Input**: Design documents from `/specs/018-public-api/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Three-layer testing required per Constitution (ADR-005). Contract and unit tests included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)

## Path Conventions

- Source: `src/gepa_adk/`
- Tests: `tests/contracts/`, `tests/unit/`, `tests/integration/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add dependency and verify existing infrastructure

- [X] T001 Add nest_asyncio dependency via `uv add nest_asyncio`
- [X] T002 [P] Verify ADKAdapter exists in src/gepa_adk/adapters/adk_adapter.py
- [X] T003 [P] Verify CriticScorer exists in src/gepa_adk/adapters/critic_scorer.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Input validation helper that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create _validate_evolve_inputs() helper function in src/gepa_adk/api.py
- [X] T005 [P] Add ConfigurationError import and validation logic for agent type
- [X] T006 [P] Add validation logic for trainset (non-empty, has "input" keys)

**Checkpoint**: Validation infrastructure ready - user story implementation can begin

---

## Phase 3: User Story 1 & 2 - Core API Functions (Priority: P1) 🎯 MVP

**Goal**: Implement `evolve()` async function and `evolve_sync()` wrapper

**Independent Test**: Call `await evolve(agent, trainset)` with mock adapter, verify EvolutionResult returned

### Contract Tests for US1/US2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T007 [P] [US1] Contract test for evolve() signature in tests/contracts/test_api_contract.py
- [X] T008 [P] [US2] Contract test for evolve_sync() signature in tests/contracts/test_api_contract.py
- [X] T009 [P] [US1] Contract test for package exports in tests/contracts/test_api_contract.py

### Unit Tests for US1/US2

- [X] T010 [P] [US1] Unit test evolve() with mocked engine in tests/unit/test_api.py
- [X] T011 [P] [US1] Unit test evolve() validation errors in tests/unit/test_api.py
- [X] T012 [P] [US2] Unit test evolve_sync() calls evolve() in tests/unit/test_api.py
- [X] T013 [P] [US2] Unit test evolve_sync() nested event loop handling in tests/unit/test_api.py

### Implementation for US1 - evolve()

- [X] T014 [US1] Add evolve() function stub with correct signature in src/gepa_adk/api.py
- [X] T015 [US1] Implement scorer building logic (CriticScorer if critic provided, else schema-based scorer using agent.output_schema)
- [X] T016 [US1] Implement ADKAdapter instantiation with agent, scorer, trajectory_config
- [X] T017 [US1] Implement initial Candidate creation from agent.instruction
- [X] T018 [US1] Implement AsyncGEPAEngine instantiation and run() call
- [X] T019 [US1] Add structlog events for evolve() start and completion
- [X] T020 [US1] Add Google-style docstring with full parameter documentation

### Implementation for US2 - evolve_sync()

- [X] T021 [US2] Add evolve_sync() function stub in src/gepa_adk/api.py
- [X] T022 [US2] Implement asyncio.run() with try/except for nested loop detection
- [X] T023 [US2] Implement nest_asyncio fallback for Jupyter compatibility
- [X] T024 [US2] Add Google-style docstring with examples

### Package Exports

- [X] T025 [US1] Export evolve from src/gepa_adk/__init__.py
- [X] T026 [US2] Export evolve_sync from src/gepa_adk/__init__.py
- [X] T027 [P] Update __all__ list in src/gepa_adk/__init__.py

**Checkpoint**: Core API functional - `evolve()` and `evolve_sync()` work with defaults

---

## Phase 4: User Story 3 - Progressive Configuration (Priority: P2)

**Goal**: Support all optional parameters (config, critic, trajectory_config, etc.)

**Independent Test**: Call evolve with custom config and verify settings applied

### Unit Tests for US3

- [X] T028 [P] [US3] Unit test evolve() with custom EvolutionConfig in tests/unit/test_api.py
- [X] T029 [P] [US3] Unit test evolve() with critic agent in tests/unit/test_api.py
- [X] T030 [P] [US3] Unit test evolve() with trajectory_config in tests/unit/test_api.py
- [X] T031 [P] [US3] Unit test evolve() logs warning for reflection_agent in tests/unit/test_api.py

### Implementation for US3

- [X] T032 [US3] Add config parameter handling (default to EvolutionConfig())
- [X] T033 [US3] Add trajectory_config parameter handling (default to TrajectoryConfig())
- [X] T034 [US3] Add reflection_agent parameter with warning log (not yet implemented)
- [X] T035 [US3] Add state_guard parameter with optional validation hook

**Checkpoint**: All optional parameters supported with sensible defaults

---

## Phase 5: User Story 4 - Validation Dataset (Priority: P3)

**Goal**: Support valset parameter for held-out evaluation

**Independent Test**: Pass trainset and valset, verify both are used in evolution

### Unit Tests for US4

- [X] T036 [P] [US4] Unit test evolve() with valset parameter in tests/unit/test_api.py

### Implementation for US4

- [X] T037 [US4] Add valset parameter handling in evolve() (store for post-evolution evaluation; MVP evaluates final instruction on valset separately)
- [X] T038 [US4] Add structlog event for valset evaluation and include valset_score in logs

**Checkpoint**: Validation dataset support complete

---

## Phase 6: Integration Tests (Slow - CI Only)

**Purpose**: Real ADK integration tests

- [ ] T039 [P] Integration test evolve() with real LlmAgent in tests/integration/test_api_integration.py
- [ ] T040 [P] Integration test evolve_sync() in script-like context in tests/integration/test_api_integration.py
- [ ] T041 Integration test evolve() with critic agent in tests/integration/test_api_integration.py

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final quality checks and documentation

- [X] T042 Run ruff check --fix and ruff format on src/gepa_adk/api.py
- [X] T043 Run ty check for type validation
- [X] T044 Verify all tests pass with uv run pytest -n auto
- [X] T045 Validate quickstart.md examples work correctly
- [X] T046 Update docstrings to ensure 95%+ coverage (interrogate)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **US1/US2 (Phase 3)**: Depends on Foundational - core MVP
- **US3 (Phase 4)**: Can start after Phase 3 foundation or in parallel
- **US4 (Phase 5)**: Can start after Phase 3 foundation
- **Integration (Phase 6)**: Depends on all implementation phases
- **Polish (Phase 7)**: Depends on all tests passing

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US1 | Foundational | US2 (same functions) |
| US2 | US1 (wraps evolve) | - |
| US3 | US1/US2 complete | US4 |
| US4 | US1/US2 complete | US3 |

### Parallel Opportunities by Phase

**Phase 1 (Setup)**:
```
T001 (add dep) → T002, T003 (verify existing) [parallel]
```

**Phase 2 (Foundational)**:
```
T004 → T005, T006 [parallel after T004]
```

**Phase 3 (US1/US2 Tests)**:
```
T007, T008, T009 [all parallel - different test classes]
T010, T011, T012, T013 [all parallel - different test functions]
```

**Phase 3 (US1/US2 Implementation)**:
```
T014 → T015 → T016 → T017 → T018 [sequential - builds on previous]
T019, T020 [parallel - logging/docs]
T021 → T022 → T023 → T024 [sequential for evolve_sync]
T025, T026, T027 [parallel - different lines in __init__.py]
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. ✅ Phase 1: Setup (add nest_asyncio)
2. ✅ Phase 2: Foundational (validation helper)
3. ✅ Phase 3: Core API (evolve + evolve_sync)
4. **STOP and VALIDATE**: Run contract + unit tests
5. Deploy/demo basic functionality

### Incremental Delivery

1. MVP → Phase 3 complete → Basic evolution works
2. Add US3 → Configuration options → Power users happy
3. Add US4 → Validation dataset → ML practitioners happy
4. Integration tests → Full confidence
5. Polish → Production ready

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 52 |
| Setup Tasks | 3 |
| Foundational Tasks | 3 |
| US1/US2 Tasks (MVP) | 21 |
| US3 Tasks | 8 |
| US4 Tasks | 3 |
| Integration Tasks | 3 |
| Polish Tasks | 5 |
| Code Review Fixes | 6 |
| Parallel Opportunities | 24 tasks marked [P] |

**Suggested MVP Scope**: Complete through Phase 3 (T001-T027) for working `evolve()` and `evolve_sync()` functions.

---

## Phase 8: Code Review Fixes (Post-Implementation)

**Purpose**: Address issues found during code review

- [X] T047 Fix MissingScoreFieldError usage - use `parsed_output` instead of incorrect `schema_name` parameter
- [X] T048 Fix type conversion in SchemaBasedScorer - use `getattr()` to properly extract score value
- [X] T049 Fix contract test return annotation checks - handle string annotations from `__future__` imports
- [X] T050 Fix nested event loop test - patch `sys.modules` instead of non-existent module attribute
- [X] T051 Fix line length violation (E501) - shorten reflection_agent warning message
- [X] T052 Update module docstring TACOS watermark - ensure Note starts with "T"

**Checkpoint**: All tests passing (26/26 API tests, 497/501 total)

---

## Phase 9: Workflow Integration Test Fixes

**Purpose**: Fix failing workflow integration tests caused by agent parent relationship issue

**Root Cause**: When `model_copy()` clones an agent that already has a `parent_agent` (because it was added to a workflow like `ParallelAgent`), the clone retains the parent reference. When `MultiAgentAdapter._build_pipeline()` tries to add the cloned agent to a new `SequentialAgent`, Pydantic validation fails because the agent already has a parent.

- [ ] T053 Fix MultiAgentAdapter._build_pipeline() to clear parent_agent when cloning agents
- [ ] T054 [P] Verify test_evolve_workflow_with_sequential_agent passes
- [ ] T055 [P] Verify test_evolve_workflow_uses_share_session_true passes
- [ ] T056 [P] Verify test_evolve_workflow_with_loop_agent passes
- [ ] T057 [P] Verify test_evolve_workflow_with_parallel_agent passes

**Checkpoint**: All 501 tests passing

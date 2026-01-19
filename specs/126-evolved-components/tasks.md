# Tasks: Evolved Components Dictionary

**Input**: Design documents from `/specs/126-evolved-components/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Three-layer testing required per Constitution Principle IV.

**Documentation**: Breaking change requires docs/guides updates + example migrations per Constitution Principle VI.

**Organization**: Tasks grouped by user story. US1 and US2 are combined as they share core implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| Breaking change | Required + migration | Required |

This is a **breaking change** - all documentation and examples must be updated.

---

## Phase 1: Setup

**Purpose**: Verify current state and prepare for changes

- [x] T001 Run existing test suite to establish baseline in tests/
- [x] T002 [P] Create feature branch checkpoint (git commit before changes)

---

## Phase 2: Foundational (Domain Model Changes)

**Purpose**: Core domain model changes that MUST complete before user story implementation

**⚠️ CRITICAL**: These changes are shared by all user stories and must complete first

### Domain Model Updates

- [x] T003 Add `evolved_component: str` field to IterationRecord in src/gepa_adk/domain/models.py
- [x] T004 Update IterationRecord docstring with new field documentation in src/gepa_adk/domain/models.py
- [x] T005 Replace `evolved_component_text: str` with `evolved_components: dict[str, str]` in EvolutionResult in src/gepa_adk/domain/models.py
- [x] T006 Update EvolutionResult docstring and examples in src/gepa_adk/domain/models.py
- [x] T007 Verify domain/__init__.py re-exports are correct in src/gepa_adk/domain/__init__.py
- [x] T008 Run type checker to verify domain model changes with `uv run ty check`

**Checkpoint**: Domain models updated - engine and test updates can proceed

---

## Phase 3: User Stories 1 & 2 - Multi-Component Access + Default Evolution (Priority: P1) 🎯 MVP

**Goal**: Enable access to all evolved components via dictionary while maintaining default instruction-only behavior

**Independent Test**: Run evolution with default config and verify `result.evolved_components["instruction"]` contains evolved text

### Engine Implementation

- [x] T009 Update `_record_iteration()` to accept `evolved_component` parameter in src/gepa_adk/engine/async_engine.py
- [x] T010 Update `_build_result()` to populate `evolved_components` from `best_candidate.components` in src/gepa_adk/engine/async_engine.py
- [x] T011 Update all `_record_iteration()` call sites to pass `evolved_component="instruction"` in src/gepa_adk/engine/async_engine.py
- [x] T012 Update api.py result handling for `evolved_components` access in src/gepa_adk/api.py
- [ ] T012a [US1] Add component name validation in evolve() to reject invalid names early in src/gepa_adk/api.py

### Tests - Contract Layer

- [ ] T013 [P] [US1] Update EvolutionResult contract tests for `evolved_components` in tests/contracts/test_async_engine_contracts.py
- [ ] T014 [P] [US1] Add contract test for dictionary access pattern and verify non-evolved components are included in tests/contracts/test_async_engine_contracts.py
- [ ] T015 [P] [US1] Check test_objective_scores_models.py for EvolutionResult usage in tests/contracts/test_objective_scores_models.py

### Tests - Unit Layer

- [ ] T016 [P] [US1] Update IterationRecord unit tests with `evolved_component` field in tests/unit/domain/test_models.py
- [ ] T017 [P] [US1] Update EvolutionResult unit tests for `evolved_components` in tests/unit/domain/test_models.py
- [ ] T018 [P] [US2] Update async_engine unit tests for new field in tests/unit/engine/test_async_engine.py
- [ ] T019 [P] [US2] Update api unit tests for result access pattern in tests/unit/test_api.py
- [ ] T020 [P] [US2] Update test_reflection_model_wiring.py if affected in tests/unit/test_reflection_model_wiring.py
- [ ] T021 [P] [US2] Update test_api_state_guard.py if affected in tests/unit/test_api_state_guard.py

> **Note**: T020-T021 are conditional - verify these files reference `evolved_component_text` before modifying. Skip if no references found.

### Tests - Integration Layer

- [ ] T022 [US2] Update test_adk_reflection.py integration tests in tests/integration/engine/test_adk_reflection.py
- [ ] T023 [US2] Update test_api_state_guard_logging.py if affected in tests/integration/test_api_state_guard_logging.py
- [ ] T023a [US2] Add integration test for mid-evolution failure returning partial evolved_components in tests/integration/engine/test_async_engine_failure.py

> **Note**: T023 is conditional - verify file references `evolved_component_text` before modifying. Skip if no references found.

### Documentation Updates

- [ ] T024 [P] [US1] Update docs/index.md with breaking change note in docs/index.md
- [ ] T025 [P] [US1] Update docs/getting-started.md API examples in docs/getting-started.md
- [ ] T026 [P] [US2] Update docs/guides/single-agent.md result access patterns in docs/guides/single-agent.md
- [ ] T027 [P] [US2] Update docs/guides/critic-agents.md result access patterns in docs/guides/critic-agents.md
- [ ] T027a [P] [US2] Update docs/guides/multi-agent.md if multi-component access affects multi-agent workflows in docs/guides/multi-agent.md
- [ ] T028 [P] [US1] Update docs/reference/glossary.md term definitions in docs/reference/glossary.md

### Example Migrations

- [ ] T029 [P] [US2] Migrate examples/basic_evolution.py to use `evolved_components` in examples/basic_evolution.py
- [ ] T030 [P] [US2] Migrate examples/basic_evolution_adk_reflection.py in examples/basic_evolution_adk_reflection.py
- [ ] T031 [P] [US2] Migrate examples/critic_agent.py in examples/critic_agent.py
- [ ] T032 [P] [US2] Migrate examples/schema_evolution_critic.py in examples/schema_evolution_critic.py

**Checkpoint**: US1 & US2 complete - default evolution works with new API, all tests pass

---

## Phase 4: User Story 3 - Round-Robin Component Evolution Tracking (Priority: P2)

**Goal**: Track which component was evolved in each iteration for round-robin strategies

**Independent Test**: Configure alternating evolution and verify each iteration record has correct `evolved_component` value

### Engine Enhancement

- [ ] T033 [US3] Update `_record_iteration()` call sites to pass dynamic component name from component selector in src/gepa_adk/engine/async_engine.py
- [ ] T034 [US3] Verify component selector integration passes evolved component name in src/gepa_adk/engine/async_engine.py

### Tests

- [ ] T035 [P] [US3] Add unit test for round-robin iteration tracking in tests/unit/engine/test_async_engine.py
- [ ] T036 [P] [US3] Add contract test CT-105 for alternating component tracking in tests/contracts/test_async_engine_contracts.py

### Documentation

- [ ] T037 [US3] Add round-robin tracking example to docs/guides/workflows.md if applicable in docs/guides/workflows.md

**Checkpoint**: US3 complete - iteration history tracks evolved component per iteration

---

## Phase 5: Verification & Cross-Cutting Concerns

**Purpose**: Final verification and documentation build

### Test Suite Verification

- [ ] T038 Run full test suite with `uv run pytest -n auto`
- [ ] T039 Run type checker with `uv run ty check`
- [ ] T040 Run linter with `uv run ruff check --fix`

### Documentation Build Verification

- [ ] T041 Verify `uv run mkdocs build` passes without warnings
- [ ] T042 Preview docs with `uv run mkdocs serve` and verify changes render correctly

### Quickstart Validation

- [ ] T043 Run quickstart.md code examples to verify they work

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ──── BLOCKS all user stories
    │
    ├──────────────────────┐
    ▼                      ▼
Phase 3 (US1+US2)     [Could be parallel with US3 setup]
    │
    ▼
Phase 4 (US3)
    │
    ▼
Phase 5 (Verification)
```

### User Story Dependencies

- **User Stories 1 & 2 (P1)**: Depend on Phase 2 completion - shared implementation
- **User Story 3 (P2)**: Depends on Phase 2 completion + benefits from US1/US2 being done first

### Within Each Phase

- Domain models (T003-T008) must complete before engine changes (T009-T012)
- Tests can run in parallel within their layer (marked [P])
- Documentation and examples can run in parallel (marked [P])

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T003, T004 (IterationRecord) can run together
- T005, T006 (EvolutionResult) can run together
- After both complete: T007, T008

**Phase 3 (US1+US2)**:
```bash
# Contract tests - parallel
T013, T014, T015

# Unit tests - parallel
T016, T017, T018, T019, T020, T021

# Docs - parallel
T024, T025, T026, T027, T027a, T028

# Examples - parallel
T029, T030, T031, T032
```

**Phase 4 (US3)**:
```bash
# Tests - parallel
T035, T036
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational domain model changes
3. Complete Phase 3: Engine + tests + docs
4. **STOP and VALIDATE**: All tests pass, docs build clean
5. Can deploy/demo with basic multi-component access

### Full Feature (Add User Story 3)

1. Complete Phase 4: Round-robin tracking
2. Complete Phase 5: Final verification
3. Feature complete with full iteration tracking

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- US1 and US2 are combined because they share the same core implementation
- Breaking change: No backward compatibility wrapper
- Total tasks: 46
- Estimated parallel opportunities: ~70% of tasks can run in parallel within their phase
- Conditional tasks (T020, T021, T023): Pre-verify file references before implementation

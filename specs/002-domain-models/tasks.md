# Tasks: Domain Models for Evolution Engine

**Input**: Design documents from `/specs/002-domain-models/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Project Structure)

**Purpose**: Create domain layer directory structure and package initialization

- [ ] T001 Create domain layer directory structure at `src/gepa_adk/domain/`
- [ ] T002 [P] Create `src/gepa_adk/domain/__init__.py` with public exports
- [ ] T003 [P] Create test directory structure at `tests/unit/domain/`
- [ ] T004 [P] Create `tests/unit/domain/__init__.py` (empty)
- [ ] T005 [P] Create `tests/unit/__init__.py` (empty, if not exists)

---

## Phase 2: Foundational (Types & Exceptions)

**Purpose**: Core infrastructure that ALL domain models depend on - MUST complete before user stories

**⚠️ CRITICAL**: No model implementation can begin until this phase is complete

- [ ] T006 [P] Create type aliases (Score, ComponentName, ModelName) in `src/gepa_adk/domain/types.py`
- [ ] T007 [P] Create exception hierarchy (EvolutionError, ConfigurationError) in `src/gepa_adk/domain/exceptions.py`
- [ ] T008 [P] Create unit tests for types in `tests/unit/domain/test_types.py`
- [ ] T009 [P] Create unit tests for exceptions in `tests/unit/domain/test_exceptions.py`

**Checkpoint**: Foundation ready - model implementation can now begin

---

## Phase 3: User Story 1 - Configure Evolution Parameters (Priority: P1) 🎯 MVP

**Goal**: Developers can create EvolutionConfig with sensible defaults and custom values

**Independent Test**: Create EvolutionConfig instance, verify all defaults and custom value preservation

### Tests for User Story 1

- [ ] T010 [US1] Create unit tests for EvolutionConfig defaults in `tests/unit/domain/test_models.py`
- [ ] T011 [US1] Create unit tests for EvolutionConfig custom values in `tests/unit/domain/test_models.py`
- [ ] T012 [US1] Create unit tests for EvolutionConfig validation (negative max_iterations, zero max_concurrent_evals, empty reflection_model) in `tests/unit/domain/test_models.py`

### Implementation for User Story 1

- [ ] T013 [US1] Implement EvolutionConfig dataclass with defaults in `src/gepa_adk/domain/models.py`
- [ ] T014 [US1] Add `__post_init__` validation for non-negative numeric fields in `src/gepa_adk/domain/models.py`
- [ ] T015 [US1] Export EvolutionConfig from `src/gepa_adk/domain/__init__.py`
- [ ] T016 [US1] Run tests and verify all acceptance scenarios pass

**Checkpoint**: EvolutionConfig is fully functional with defaults and validation

---

## Phase 4: User Story 2 - Track Evolution Results (Priority: P1)

**Goal**: Developers can receive and inspect comprehensive evolution results with computed properties

**Independent Test**: Create EvolutionResult with sample data, verify all metrics accessible including `improvement` property

### Tests for User Story 2

- [ ] T017 [US2] Create unit tests for EvolutionResult field access in `tests/unit/domain/test_models.py`
- [ ] T018 [US2] Create unit tests for EvolutionResult computed properties (improvement, improved) in `tests/unit/domain/test_models.py`
- [ ] T019 [US2] Create unit tests for EvolutionResult immutability (frozen) in `tests/unit/domain/test_models.py`

### Implementation for User Story 2

- [ ] T020 [US2] Implement EvolutionResult frozen dataclass in `src/gepa_adk/domain/models.py`
- [ ] T021 [US2] Add `improvement` and `improved` computed properties to EvolutionResult in `src/gepa_adk/domain/models.py`
- [ ] T022 [US2] Export EvolutionResult from `src/gepa_adk/domain/__init__.py`
- [ ] T023 [US2] Run tests and verify all acceptance scenarios pass

**Checkpoint**: EvolutionResult is fully functional with computed properties and immutability

---

## Phase 5: User Story 3 - Manage Candidate Instructions (Priority: P1)

**Goal**: Developers can create and manipulate Candidate instances with component-based access and lineage tracking

**Independent Test**: Create Candidate, verify component get/set, generation/parent_id defaults

### Tests for User Story 3

- [ ] T024 [US3] Create unit tests for Candidate component access in `tests/unit/domain/test_models.py`
- [ ] T025 [US3] Create unit tests for Candidate lineage fields (generation, parent_id, metadata) in `tests/unit/domain/test_models.py`
- [ ] T026 [US3] Create unit tests for Candidate mutable defaults (dict fields) in `tests/unit/domain/test_models.py`

### Implementation for User Story 3

- [ ] T027 [US3] Implement Candidate dataclass with components, generation, parent_id, metadata in `src/gepa_adk/domain/models.py`
- [ ] T028 [US3] Use `field(default_factory=dict)` for mutable defaults in `src/gepa_adk/domain/models.py`
- [ ] T029 [US3] Export Candidate from `src/gepa_adk/domain/__init__.py`
- [ ] T030 [US3] Run tests and verify all acceptance scenarios pass

**Checkpoint**: Candidate is fully functional with GEPA-compatible components and lineage tracking

---

## Phase 6: User Story 4 - Record Iteration History (Priority: P2)

**Goal**: Developers can examine iteration records with all per-iteration metrics

**Independent Test**: Create IterationRecord instances, verify all fields captured correctly

### Tests for User Story 4

- [ ] T031 [US4] Create unit tests for IterationRecord field access in `tests/unit/domain/test_models.py`
- [ ] T032 [US4] Create unit tests for IterationRecord immutability (frozen) in `tests/unit/domain/test_models.py`

### Implementation for User Story 4

- [ ] T033 [US4] Implement IterationRecord frozen dataclass in `src/gepa_adk/domain/models.py`
- [ ] T034 [US4] Export IterationRecord from `src/gepa_adk/domain/__init__.py`
- [ ] T035 [US4] Run tests and verify all acceptance scenarios pass

**Checkpoint**: IterationRecord is fully functional and immutable

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and code quality

- [ ] T036 [P] Add Google-style docstrings to all models in `src/gepa_adk/domain/models.py`
- [ ] T037 [P] Add Google-style docstrings to types in `src/gepa_adk/domain/types.py`
- [ ] T038 [P] Add Google-style docstrings to exceptions in `src/gepa_adk/domain/exceptions.py`
- [ ] T039 Run `uv run ruff check --fix` to lint all domain code
- [ ] T040 Run `uv run ruff format` to format all domain code
- [ ] T041 Run `uv run ty check` to verify type checking passes
- [ ] T042 Run `uv run pytest tests/unit/domain/ --cov=src/gepa_adk/domain --cov-report=term-missing` to verify 100% coverage
- [ ] T043 Validate quickstart.md examples work by running them interactively
- [ ] T044 Update `src/gepa_adk/__init__.py` to export domain models for top-level access

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────┐
                         ├──▶ Phase 2: Foundational ──▶ Phase 3-6: User Stories ──▶ Phase 7: Polish
```

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational completion
  - US1, US2, US3 are P1 (can proceed in priority order or parallel)
  - US4 is P2 (can proceed after US1-3 or in parallel if staffed)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

| Story | Priority | Dependencies | Can Parallel With |
|-------|----------|--------------|-------------------|
| US1 (EvolutionConfig) | P1 | Phase 2 only | US2, US3, US4 |
| US2 (EvolutionResult) | P1 | Phase 2, US4 (for IterationRecord type) | US1, US3 |
| US3 (Candidate) | P1 | Phase 2 only | US1, US2, US4 |
| US4 (IterationRecord) | P2 | Phase 2 only | US1, US3 |

**Note**: US2 (EvolutionResult) has a soft dependency on US4 (IterationRecord) because `iteration_history: list[IterationRecord]`. For parallel execution, can use forward reference or implement US4 first.

### Within Each User Story

1. Write tests FIRST - verify they FAIL
2. Implement model
3. Run tests - verify they PASS
4. Export from `__init__.py`
5. Checkpoint complete

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T002, T003, T004, T005 can run in parallel
```

**Phase 2 (Foundational)**:
```
T006 (types) ──┬──▶ Done
T007 (exceptions) ─┤
T008 (test types) ─┤
T009 (test exceptions)
```

**User Stories (after Phase 2)**:
```
US1 (EvolutionConfig) ──┐
US3 (Candidate) ────────┼──▶ US2 (EvolutionResult) ──▶ Done
US4 (IterationRecord) ──┘
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T009)
3. Complete Phase 3: User Story 1 - EvolutionConfig (T010-T016)
4. **STOP and VALIDATE**: `uv run pytest tests/unit/domain/ -v`
5. MVP complete - developers can configure evolution!

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (EvolutionConfig) → Test → **MVP!**
3. Add US4 (IterationRecord) → Test (needed for US2)
4. Add US2 (EvolutionResult) → Test
5. Add US3 (Candidate) → Test
6. Polish phase → **Feature complete!**

### Recommended Execution Order (Solo Developer)

```
T001 → T002-T005 (parallel) → T006-T009 (parallel) →
T010-T016 (US1) → T031-T035 (US4) → T017-T023 (US2) → T024-T030 (US3) →
T036-T044 (Polish)
```

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [USn] label maps task to specific user story
- All models in single file `models.py` (small scope, high cohesion)
- Tests also in single file `test_models.py` for this feature
- Verify tests FAIL before implementing
- Commit after each phase or user story completion
- Run `uv run ruff check --fix && uv run ruff format` frequently

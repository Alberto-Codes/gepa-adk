# Tasks: Multi-Component Evolution with Component Selectors

**Input**: Design documents from `/specs/024-component-selector/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included per ADR-005 three-layer testing strategy (contract, unit, integration).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root
- Structure follows hexagonal architecture: ports/, adapters/, engine/, domain/

---

## Phase 1: Setup

**Purpose**: Ensure development environment is ready

- [ ] T001 Verify branch `024-component-selector` is checked out and up to date
- [ ] T002 Run `uv sync` to ensure all dependencies are installed
- [ ] T003 Run `uv run pytest tests/` to verify baseline tests pass

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core protocol infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Add `ComponentSelectorProtocol` to `src/gepa_adk/ports/selector.py` with async `select_components(components: list[str], iteration: int, candidate_idx: int) -> list[str]` method
- [ ] T005 Export `ComponentSelectorProtocol` from `src/gepa_adk/ports/__init__.py`
- [ ] T006 [P] Add contract test for `ComponentSelectorProtocol` in `tests/contracts/test_component_selector_protocol.py`

**Checkpoint**: Protocol defined and exported - selector implementations can now begin

---

## Phase 3: User Story 1 - Round-Robin Component Evolution (Priority: P1) 🎯 MVP

**Goal**: Implement round-robin component selector that cycles through components sequentially, one per iteration

**Independent Test**: Run evolution for 4 iterations on 2-component candidate, verify iteration 1 mutates component A, iteration 2 mutates component B, iteration 3 cycles back to A

### Tests for User Story 1

- [ ] T007 [P] [US1] Unit test for `RoundRobinComponentSelector` basic cycling in `tests/unit/adapters/test_component_selector.py`
- [ ] T008 [P] [US1] Unit test for round-robin with single component (returns same component every time) in `tests/unit/adapters/test_component_selector.py`
- [ ] T009 [P] [US1] Unit test for round-robin per-candidate-idx state tracking in `tests/unit/adapters/test_component_selector.py`
- [ ] T010 [P] [US1] Unit test for round-robin modulo wrap-around in `tests/unit/adapters/test_component_selector.py`

### Implementation for User Story 1

- [ ] T011 [US1] Create `src/gepa_adk/adapters/component_selector.py` with module docstring and imports
- [ ] T012 [US1] Implement `RoundRobinComponentSelector` class with `__init__` and `_next_index: dict[int, int]` attribute in `src/gepa_adk/adapters/component_selector.py`
- [ ] T013 [US1] Implement `RoundRobinComponentSelector.select_components()` async method with per-candidate-idx cycling logic in `src/gepa_adk/adapters/component_selector.py`
- [ ] T014 [US1] Add Google-style docstrings and examples to `RoundRobinComponentSelector` in `src/gepa_adk/adapters/component_selector.py`
- [ ] T015 [US1] Run unit tests for User Story 1 and verify all pass

**Checkpoint**: Round-robin selector complete and tested - core MVP functionality ready

---

## Phase 4: User Story 2 - All-Components Simultaneous Evolution (Priority: P2)

**Goal**: Implement all-components selector that returns every component each iteration

**Independent Test**: Configure all-components selector, verify single iteration proposes changes to ALL components

### Tests for User Story 2

- [ ] T016 [P] [US2] Unit test for `AllComponentSelector` returns all components in `tests/unit/adapters/test_component_selector.py`
- [ ] T017 [P] [US2] Unit test for `AllComponentSelector` stateless behavior (same result regardless of iteration/candidate_idx) in `tests/unit/adapters/test_component_selector.py`

### Implementation for User Story 2

- [ ] T018 [US2] Implement `AllComponentSelector` class in `src/gepa_adk/adapters/component_selector.py`
- [ ] T019 [US2] Implement `AllComponentSelector.select_components()` async method returning all components in `src/gepa_adk/adapters/component_selector.py`
- [ ] T020 [US2] Add Google-style docstrings and examples to `AllComponentSelector` in `src/gepa_adk/adapters/component_selector.py`
- [ ] T021 [US2] Run unit tests for User Story 2 and verify all pass

**Checkpoint**: Both selector implementations complete - ready for engine integration

---

## Phase 5: User Story 3 - Multi-Agent Workflow Evolution (Priority: P2)

**Goal**: Integrate component selector into AsyncGEPAEngine with multi-agent component discovery

**Independent Test**: Create multi-agent candidate with `generator_instruction` and `critic_instruction`, verify round-robin cycles through both agents

### Tests for User Story 3

- [ ] T022 [P] [US3] Unit test for `_build_component_list()` helper extracting candidate keys in `tests/unit/engine/test_engine_component_selection.py`
- [ ] T023 [P] [US3] Unit test for `_build_component_list()` excluding generic `instruction` alias when per-agent instructions exist in `tests/unit/engine/test_engine_component_selection.py`
- [ ] T024 [P] [US3] Unit test for engine using component selector in `_propose_mutation()` in `tests/unit/engine/test_engine_component_selection.py`
- [ ] T025 [P] [US3] Unit test for engine defaulting to round-robin when no selector provided in `tests/unit/engine/test_engine_component_selection.py`

### Implementation for User Story 3

- [ ] T026 [US3] Add `component_selector: ComponentSelectorProtocol | None = None` parameter to `AsyncGEPAEngine.__init__()` in `src/gepa_adk/engine/async_engine.py`
- [ ] T027 [US3] Add `_component_selector` attribute storage in `AsyncGEPAEngine.__init__()` in `src/gepa_adk/engine/async_engine.py`
- [ ] T028 [US3] Implement `_build_component_list()` helper method in `src/gepa_adk/engine/async_engine.py` that extracts component keys and excludes `instruction` alias when per-agent keys exist
- [ ] T029 [US3] Replace hardcoded `components_to_update = ["instruction"]` in `AsyncGEPAEngine._propose_mutation()` with call to component selector in `src/gepa_adk/engine/async_engine.py`
- [ ] T030 [US3] Add structlog event for component selection in `AsyncGEPAEngine._propose_mutation()` in `src/gepa_adk/engine/async_engine.py`
- [ ] T031 [US3] Run unit tests for User Story 3 and verify all pass

**Checkpoint**: Engine integration complete - selectors work with multi-agent candidates

---

## Phase 6: User Story 4 - Selector Configuration via API (Priority: P3)

**Goal**: Expose component_selector parameter in public API functions and add factory function

**Independent Test**: Call `evolve()` with `component_selector="round_robin"` and `component_selector="all"`, verify correct behavior applied

### Tests for User Story 4

- [ ] T032 [P] [US4] Unit test for `create_component_selector("round_robin")` factory in `tests/unit/adapters/test_component_selector.py`
- [ ] T033 [P] [US4] Unit test for `create_component_selector("all")` factory in `tests/unit/adapters/test_component_selector.py`
- [ ] T034 [P] [US4] Unit test for `create_component_selector()` with invalid type raises ConfigurationError in `tests/unit/adapters/test_component_selector.py`
- [ ] T035 [P] [US4] Unit test for `create_component_selector()` with alias variations (round-robin, roundrobin) in `tests/unit/adapters/test_component_selector.py`

### Implementation for User Story 4

- [ ] T036 [US4] Implement `create_component_selector(selector_type: str) -> ComponentSelectorProtocol` factory function in `src/gepa_adk/adapters/component_selector.py`
- [ ] T037 [US4] Add `__all__` exports to `src/gepa_adk/adapters/component_selector.py`
- [ ] T038 [US4] Export component selector classes and factory from `src/gepa_adk/adapters/__init__.py`
- [ ] T039 [US4] Add `component_selector: ComponentSelectorProtocol | str | None = None` parameter to `evolve()` in `src/gepa_adk/api.py`
- [ ] T040 [US4] Add component selector resolution logic to `evolve()` (string to instance via factory, default to RoundRobin) in `src/gepa_adk/api.py`
- [ ] T041 [US4] Pass resolved component selector to `AsyncGEPAEngine` constructor in `evolve()` in `src/gepa_adk/api.py`
- [ ] T042 [US4] Add `component_selector` parameter to `evolve_group()` in `src/gepa_adk/api.py`
- [ ] T043 [US4] Add `component_selector` parameter to `evolve_workflow()` in `src/gepa_adk/api.py`
- [ ] T044 [US4] Update docstrings for `evolve()`, `evolve_group()`, `evolve_workflow()` with component_selector documentation in `src/gepa_adk/api.py`
- [ ] T045 [US4] Export `ComponentSelectorProtocol`, `RoundRobinComponentSelector`, `AllComponentSelector`, `create_component_selector` from `src/gepa_adk/__init__.py`
- [ ] T046 [US4] Run unit tests for User Story 4 and verify all pass

**Checkpoint**: Public API complete - users can configure component selection

---

## Phase 7: Integration Testing

**Purpose**: End-to-end validation of complete feature

- [ ] T047 [P] Add integration test for round-robin evolution with multi-component candidate in `tests/integration/test_multi_component_evolution.py`
- [ ] T048 [P] Add integration test for all-components evolution in `tests/integration/test_multi_component_evolution.py`
- [ ] T049 [P] Add integration test for multi-agent workflow component cycling in `tests/integration/test_multi_component_evolution.py`
- [ ] T050 Add integration test for backward compatibility (single-component candidate unchanged behavior) in `tests/integration/test_multi_component_evolution.py`
- [ ] T051 Run full test suite: `uv run pytest tests/` and verify all pass

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and validation

- [ ] T052 Run linter: `uv run ruff check src/gepa_adk/`
- [ ] T053 Run formatter: `uv run ruff format src/gepa_adk/`
- [ ] T054 Run type checker: `uv run ty check`
- [ ] T055 Verify docstring coverage with interrogate
- [ ] T056 Run quickstart.md examples manually to validate documentation accuracy
- [ ] T057 Final test run: `uv run pytest tests/ -v`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - can start after T006
- **User Story 2 (Phase 4)**: Depends on Foundational - can start in parallel with US1
- **User Story 3 (Phase 5)**: Depends on US1 and US2 completion (needs both selectors)
- **User Story 4 (Phase 6)**: Depends on US3 completion (needs engine integration)
- **Integration (Phase 7)**: Depends on US4 completion
- **Polish (Phase 8)**: Depends on Integration completion

### User Story Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (Protocol)
    ↓
┌───────┴───────┐
↓               ↓
Phase 3: US1    Phase 4: US2
(RoundRobin)    (All)
└───────┬───────┘
        ↓
Phase 5: US3 (Engine Integration)
        ↓
Phase 6: US4 (API Integration)
        ↓
Phase 7: Integration Tests
        ↓
Phase 8: Polish
```

### Parallel Opportunities

Within Phase 2 (Foundational):
- T006 can run in parallel after T004-T005

Within Phase 3 (US1):
- T007, T008, T009, T010 (all tests) can run in parallel

Within Phase 4 (US2):
- T016, T017 (tests) can run in parallel

Within Phase 5 (US3):
- T022, T023, T024, T025 (tests) can run in parallel

Within Phase 6 (US4):
- T032, T033, T034, T035 (tests) can run in parallel

Within Phase 7 (Integration):
- T047, T048, T049 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "T007 [P] [US1] Unit test for RoundRobinComponentSelector basic cycling"
Task: "T008 [P] [US1] Unit test for round-robin with single component"
Task: "T009 [P] [US1] Unit test for round-robin per-candidate-idx state tracking"
Task: "T010 [P] [US1] Unit test for round-robin modulo wrap-around"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - defines protocol)
3. Complete Phase 3: User Story 1 (RoundRobinComponentSelector)
4. **STOP and VALIDATE**: Run unit tests, verify round-robin cycling works
5. Can demo round-robin selection with mock adapter

### Incremental Delivery

1. Setup + Foundational → Protocol ready
2. Add User Story 1 → Test RoundRobin independently → Core MVP!
3. Add User Story 2 → Test All selector → Both selectors complete
4. Add User Story 3 → Test engine integration → Multi-agent support
5. Add User Story 4 → Test API → Full feature ready
6. Integration tests → Polish → Production ready

### Single Developer Strategy

Execute phases sequentially in order:
1. Phase 1 (Setup) → Phase 2 (Foundational)
2. Phase 3 (US1) → Phase 4 (US2)
3. Phase 5 (US3) → Phase 6 (US4)
4. Phase 7 (Integration) → Phase 8 (Polish)

---

## Summary

| Phase | Tasks | Story | Parallel Tasks |
|-------|-------|-------|----------------|
| Setup | T001-T003 | - | 0 |
| Foundational | T004-T006 | - | 1 |
| US1 (P1) | T007-T015 | Round-Robin | 4 |
| US2 (P2) | T016-T021 | All-Components | 2 |
| US3 (P2) | T022-T031 | Multi-Agent | 4 |
| US4 (P3) | T032-T046 | API Config | 4 |
| Integration | T047-T051 | - | 3 |
| Polish | T052-T057 | - | 0 |
| **Total** | **57 tasks** | **4 stories** | **18 parallel** |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests written BEFORE implementation per TDD approach
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently

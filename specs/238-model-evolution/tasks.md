# Tasks: Model Evolution Support

**Input**: Design documents from `/specs/238-model-evolution/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included per ADR-005 Three-Layer Testing requirement (contract, unit, integration).

**Documentation**: Per Constitution Principle VI, this feature adds a new public API parameter (`model_choices`) - documentation tasks are included within each user story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Feature branch and basic structure verification

- [x] T001 Verify feature branch `238-model-evolution` is active
- [x] T002 [P] Verify existing component handler infrastructure in src/gepa_adk/adapters/component_handlers.py
- [x] T003 [P] Verify existing reflection agent infrastructure in src/gepa_adk/engine/reflection_agents.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `COMPONENT_MODEL = "model"` constant to src/gepa_adk/domain/types.py
- [x] T005 Add `ModelConstraints` frozen dataclass to src/gepa_adk/domain/types.py
- [x] T006 Add ModelConstraints export to src/gepa_adk/domain/__init__.py
- [x] T007 [P] Contract test for ModelHandler protocol compliance in tests/contracts/test_component_handler_contract.py
- [x] T008 Unit test skeleton for ModelConstraints in tests/unit/domain/test_model_constraints.py

**Checkpoint**: Foundation ready - ModelConstraints exists and is tested, user story implementation can begin

---

## Phase 3: User Story 1 - Opt-in Model Evolution (Priority: P1) 🎯 MVP

**Goal**: Enable users to evolve models by providing explicit model choices through the `model_choices` parameter

**Independent Test**: Call `evolve()` with `model_choices=["model-a", "model-b"]` and verify model evolution occurs; call without `model_choices` and verify model is NOT evolved

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T009 [P] [US1] Unit tests for ModelHandler.serialize() with string models in tests/unit/adapters/test_model_handler.py
- [ ] T010 [P] [US1] Unit tests for ModelHandler.apply() with string models in tests/unit/adapters/test_model_handler.py
- [ ] T011 [P] [US1] Unit tests for ModelHandler.restore() with string models in tests/unit/adapters/test_model_handler.py
- [ ] T012 [P] [US1] Unit tests for auto-include current model behavior in tests/unit/adapters/test_model_handler.py
- [ ] T013 [P] [US1] Unit tests for opt-in behavior (no model_choices = no evolution) in tests/unit/api/test_evolve_model.py
- [ ] T013a [P] [US1] Unit test for warning when model_choices provided without "model" component in tests/unit/api/test_evolve_model.py

### Implementation for User Story 1

- [ ] T014 [US1] Implement ModelHandler.serialize() for string models in src/gepa_adk/adapters/component_handlers.py
- [ ] T015 [US1] Implement ModelHandler.apply() for string models in src/gepa_adk/adapters/component_handlers.py
- [ ] T016 [US1] Implement ModelHandler.restore() for string models in src/gepa_adk/adapters/component_handlers.py
- [ ] T017 [US1] Implement ModelHandler.set_constraints() in src/gepa_adk/adapters/component_handlers.py
- [ ] T018 [US1] Register ModelHandler in ComponentHandlerRegistry in src/gepa_adk/adapters/component_handlers.py
- [ ] T019 [US1] Implement create_model_reflection_agent() factory in src/gepa_adk/engine/reflection_agents.py
- [ ] T020 [US1] Register model reflection agent factory in ComponentReflectionRegistry in src/gepa_adk/engine/reflection_agents.py
- [ ] T021 [US1] Add `model_choices: Sequence[str] | None = None` parameter to evolve() in src/gepa_adk/api.py
- [ ] T022 [US1] Implement model_choices processing and auto-include logic in evolve() in src/gepa_adk/api.py
- [ ] T023 [US1] Add structlog events for model evolution in src/gepa_adk/adapters/component_handlers.py
- [ ] T023a [US1] Add warning log when model_choices provided but "model" not in components list in src/gepa_adk/api.py

### Documentation for User Story 1

- [ ] T024 [P] [US1] Update docs/guides/single-agent.md with model_choices parameter documentation
- [ ] T025 [P] [US1] Add model evolution example to examples/ directory

**Checkpoint**: At this point, User Story 1 should be fully functional - users can evolve string models with explicit choices

---

## Phase 4: User Story 2 - Wrapper Preservation (Priority: P2)

**Goal**: Preserve wrapper configuration (LiteLLM custom headers, auth, etc.) when evolving wrapped model objects

**Independent Test**: Create agent with LiteLlm wrapper containing custom_headers, run evolution, verify headers preserved and only model name changed

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T026 [P] [US2] Unit tests for ModelHandler.serialize() with wrapped models in tests/unit/adapters/test_model_handler.py
- [ ] T027 [P] [US2] Unit tests for ModelHandler.apply() with wrapped models in tests/unit/adapters/test_model_handler.py
- [ ] T028 [P] [US2] Unit tests for ModelHandler.restore() with wrapped models in tests/unit/adapters/test_model_handler.py
- [ ] T029 [P] [US2] Unit tests for wrapper configuration preservation in tests/unit/adapters/test_model_handler.py

### Implementation for User Story 2

- [ ] T030 [US2] Extend ModelHandler.serialize() to handle wrapped models (duck-type on .model) in src/gepa_adk/adapters/component_handlers.py
- [ ] T031 [US2] Extend ModelHandler.apply() to mutate wrapper.model in-place in src/gepa_adk/adapters/component_handlers.py
- [ ] T032 [US2] Extend ModelHandler.restore() to restore wrapper.model in src/gepa_adk/adapters/component_handlers.py
- [ ] T033 [US2] Add wrapper detection logging in src/gepa_adk/adapters/component_handlers.py

### Documentation for User Story 2

- [ ] T034 [P] [US2] Update quickstart.md with wrapper preservation example
- [ ] T035 [P] [US2] Add LiteLLM wrapper example to examples/ directory

**Checkpoint**: At this point, both string and wrapped models can be evolved with configuration preservation

---

## Phase 5: User Story 3 - Invalid Model Rejection (Priority: P3)

**Goal**: Reject model proposals outside the allowed list and preserve original model with warning

**Independent Test**: Configure handler with allowed_models=["a", "b"], call apply("c"), verify returns None and original preserved

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T036 [P] [US3] Unit tests for constraint validation (valid model accepted) in tests/unit/adapters/test_model_handler.py
- [ ] T037 [P] [US3] Unit tests for constraint validation (invalid model rejected) in tests/unit/adapters/test_model_handler.py
- [ ] T038 [P] [US3] Unit tests for warning logging on rejection in tests/unit/adapters/test_model_handler.py
- [ ] T039 [P] [US3] Unit tests for no constraints = accept all in tests/unit/adapters/test_model_handler.py

### Implementation for User Story 3

- [ ] T040 [US3] Add constraint validation to ModelHandler.apply() in src/gepa_adk/adapters/component_handlers.py
- [ ] T041 [US3] Add warning logging for invalid model rejection in src/gepa_adk/adapters/component_handlers.py
- [ ] T042 [US3] Ensure apply() returns None on constraint violation (graceful degradation) in src/gepa_adk/adapters/component_handlers.py

### Documentation for User Story 3

- [ ] T043 [P] [US3] Update quickstart.md with constraint behavior documentation

**Checkpoint**: All user stories should now be independently functional - full model evolution with constraints

---

## Phase 6: Integration & Verification

**Purpose**: End-to-end testing and final verification

### Integration Tests

- [ ] T044 [P] Integration test for model evolution with string model in tests/integration/test_model_evolution.py
- [ ] T045 [P] Integration test for model evolution with wrapped model in tests/integration/test_model_evolution.py
- [ ] T046 [P] Integration test for model evolution combined with other components in tests/integration/test_model_evolution.py
- [ ] T047 Integration test for model_choices without "model" in components list (warning) in tests/integration/test_model_evolution.py

### Documentation Build Verification

- [ ] T048 Verify `uv run mkdocs build` passes without warnings
- [ ] T049 Preview docs with `uv run mkdocs serve` and verify model_choices documentation renders correctly

### Final Validation

- [ ] T050 Run quickstart.md validation (execute examples)
- [ ] T051 Verify all contract tests pass: `pytest tests/contracts/ -m contract`
- [ ] T052 Verify all unit tests pass: `pytest tests/unit/ -m unit`
- [ ] T053 Verify all integration tests pass: `pytest tests/integration/ -m integration`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - MVP functionality
- **User Story 2 (Phase 4)**: Depends on US1 (extends handler logic)
- **User Story 3 (Phase 5)**: Depends on US1 (extends handler logic)
- **Integration (Phase 6)**: Depends on all user stories complete

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Handler methods before registry registration
- Handler registration before API integration
- API integration before reflection agent wiring
- Documentation updates complete before story is done

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All tests for a user story marked [P] can run in parallel
- Documentation tasks (docs/ and examples/) can run in parallel with each other
- Integration tests marked [P] can run in parallel

---

## Key Files Summary

| Layer | File | Changes |
|-------|------|---------|
| domain/ | src/gepa_adk/domain/types.py | Add COMPONENT_MODEL, ModelConstraints |
| adapters/ | src/gepa_adk/adapters/component_handlers.py | Add ModelHandler class + registration |
| engine/ | src/gepa_adk/engine/reflection_agents.py | Add create_model_reflection_agent() |
| api/ | src/gepa_adk/api.py | Add model_choices parameter |
| tests/ | tests/contracts/test_component_handler_contract.py | Add ModelHandler protocol tests |
| tests/ | tests/unit/adapters/test_model_handler.py | Add handler unit tests |
| tests/ | tests/unit/domain/test_model_constraints.py | Add constraints unit tests |
| tests/ | tests/integration/test_model_evolution.py | Add end-to-end tests |
| docs/ | docs/guides/single-agent.md | Add model_choices documentation |
| examples/ | examples/model_evolution.py | Add usage example |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Run `uv run mkdocs build` before PR to verify docs build cleanly

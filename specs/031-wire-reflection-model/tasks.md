# Tasks: Wire Reflection Model Config to Proposer

**Input**: Design documents from `/specs/031-wire-reflection-model/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Unit tests are included per Constitution IV (Three-Layer Testing) and plan.md requirements.

**Documentation**: Per Constitution Principle VI, this feature (new config option) requires `examples/` update.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| New config option | Required (guides) | Recommended |

**This feature**: New config option → Update `docs/getting-started.md` (recommended) + `examples/basic_evolution.py` (required)

---

## Phase 1: Setup

**Purpose**: No setup needed - this is a modification to an existing codebase

**Status**: SKIP - Project already initialized with all dependencies

---

## Phase 2: Foundational

**Purpose**: No foundational work needed - all infrastructure exists

**Status**: SKIP - Adapters and proposer already exist; this is wiring only

---

## Phase 3: User Story 1 - Configure Custom Reflection Model (Priority: P1) 🎯 MVP

**Goal**: Allow users to specify which LLM model is used for reflection/mutation via `EvolutionConfig.reflection_model`

**Independent Test**: Create `EvolutionConfig` with custom `reflection_model`, run evolution, verify proposer uses that model

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T001 [P] [US1] Create unit test file `tests/unit/test_reflection_model_wiring.py` with test stubs
- [x] T002 [P] [US1] Add test `test_adk_adapter_passes_reflection_model_to_proposer` verifying ADKAdapter wiring
- [x] T003 [P] [US1] Add test `test_multi_agent_adapter_passes_reflection_model_to_proposer` verifying MultiAgentAdapter wiring
- [x] T004 [P] [US1] Add test `test_evolve_passes_config_reflection_model_to_adapter` verifying api.evolve() wiring
- [x] T005 [P] [US1] Add test `test_evolve_group_passes_config_reflection_model_to_adapter` verifying api.evolve_group() wiring

### Implementation for User Story 1

- [x] T006 [P] [US1] Add `reflection_model: str = "ollama_chat/gpt-oss:20b"` parameter to `ADKAdapter.__init__()` in `src/gepa_adk/adapters/adk_adapter.py`
- [x] T007 [P] [US1] Add `reflection_model: str = "ollama_chat/gpt-oss:20b"` parameter to `MultiAgentAdapter.__init__()` in `src/gepa_adk/adapters/multi_agent.py`
- [x] T008 [US1] Update `ADKAdapter.__init__()` to pass `model=reflection_model` to `AsyncReflectiveMutationProposer` in default path (path 3)
- [x] T009 [US1] Update `MultiAgentAdapter.__init__()` to pass `model=reflection_model` to `AsyncReflectiveMutationProposer`
- [x] T010 [US1] Update `evolve()` in `src/gepa_adk/api.py` to pass `reflection_model=config.reflection_model` to `ADKAdapter`
- [x] T011 [US1] Update `evolve_group()` in `src/gepa_adk/api.py` to pass `reflection_model=config.reflection_model` to `MultiAgentAdapter`
- [x] T012 [US1] Run unit tests and verify all T001-T005 pass

### Documentation for User Story 1

- [x] T013 [P] [US1] Update `examples/basic_evolution.py` to demonstrate `reflection_model` config option in `EvolutionConfig`

**Checkpoint**: Custom reflection model configuration works for both single-agent and multi-agent evolution

---

## Phase 4: User Story 2 - Default Reflection Model Behavior (Priority: P2)

**Goal**: Ensure default `reflection_model` works without explicit configuration

**Independent Test**: Create `EvolutionConfig` without `reflection_model`, verify proposer uses documented default

### Tests for User Story 2

- [x] T014 [P] [US2] Add test `test_default_reflection_model_used_when_not_specified` in `tests/unit/test_reflection_model_wiring.py`
- [x] T015 [P] [US2] Add test `test_adapter_default_matches_config_default` verifying consistency

### Implementation for User Story 2

- [x] T016 [US2] Verify `ADKAdapter` default parameter matches `EvolutionConfig.reflection_model` default (`"ollama_chat/gpt-oss:20b"`)
- [x] T017 [US2] Verify `MultiAgentAdapter` default parameter matches `EvolutionConfig.reflection_model` default
- [x] T018 [US2] Run unit tests and verify T014-T015 pass

**Checkpoint**: Default behavior works without explicit configuration; defaults are consistent across config and adapters

---

## Phase 5: User Story 3 - Transparency Through Logging (Priority: P3)

**Goal**: Log chosen reflection model at INFO level when proposer initializes

**Independent Test**: Run evolution, check logs contain INFO message with reflection model

### Tests for User Story 3

- [x] T019 [P] [US3] Add test `test_proposer_logs_reflection_model_on_init` in `tests/unit/test_reflection_model_wiring.py`

### Implementation for User Story 3

- [x] T020 [US3] Add INFO log in `AsyncReflectiveMutationProposer.__init__()` in `src/gepa_adk/engine/proposer.py`: `log.info("proposer_initialized", reflection_model=self.model)`
- [x] T021 [US3] Run unit test T019 and verify it passes

**Checkpoint**: Reflection model choice is visible in logs at INFO level

---

## Phase 6: Verification & Cross-Cutting Concerns

**Purpose**: Final verification and documentation build check

### Documentation Build Verification (REQUIRED)

- [x] T022 Verify `uv run mkdocs build` passes without warnings
- [ ] T023 Preview docs with `uv run mkdocs serve` and verify examples render correctly

### Cross-Cutting Tasks

- [x] T024 Run full test suite: `uv run pytest` (732 passed, 5 pre-existing failures unrelated to this feature)
- [x] T025 Run linting: `uv run ruff check --fix`
- [x] T026 Run type check: `uv run ty check`
- [x] T027 Verify existing integration tests still pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: SKIP - already complete
- **Foundational (Phase 2)**: SKIP - already complete
- **User Story 1 (Phase 3)**: Can start immediately - core wiring
- **User Story 2 (Phase 4)**: Can start after US1 - verifies defaults
- **User Story 3 (Phase 5)**: Can start after US1 - adds logging
- **Verification (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies - core implementation
- **User Story 2 (P2)**: Depends on US1 (needs wiring in place to test defaults)
- **User Story 3 (P3)**: Depends on US1 (needs wiring in place to test logging)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation follows tests
- Documentation updates (if user-facing) complete before story is done
- Story complete before moving to next priority

### Parallel Opportunities

- T001-T005 (US1 tests) can all run in parallel
- T006-T007 (adapter parameters) can run in parallel
- T014-T015 (US2 tests) can run in parallel after US1 implementation
- Documentation tasks (T013) can run in parallel with other implementation

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: T001 "Create unit test file tests/unit/test_reflection_model_wiring.py"
Task: T002 "Add test test_adk_adapter_passes_reflection_model_to_proposer"
Task: T003 "Add test test_multi_agent_adapter_passes_reflection_model_to_proposer"
Task: T004 "Add test test_evolve_passes_config_reflection_model_to_adapter"
Task: T005 "Add test test_evolve_group_passes_config_reflection_model_to_adapter"

# Launch adapter parameter additions together:
Task: T006 "Add reflection_model parameter to ADKAdapter.__init__()"
Task: T007 "Add reflection_model parameter to MultiAgentAdapter.__init__()"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 3: User Story 1 (T001-T013)
2. **STOP and VALIDATE**: Test custom reflection model works
3. Deploy/demo if ready - users can now configure reflection models

### Incremental Delivery

1. Complete User Story 1 → Custom model configuration works (MVP!)
2. Complete User Story 2 → Default behavior verified
3. Complete User Story 3 → Logging transparency added
4. Complete Verification → Ready for PR

### File Change Summary

| File | Tasks | Changes |
|------|-------|---------|
| `src/gepa_adk/api.py` | T010, T011 | Pass `reflection_model` to adapters |
| `src/gepa_adk/adapters/adk_adapter.py` | T006, T008 | Add parameter, pass to proposer |
| `src/gepa_adk/adapters/multi_agent.py` | T007, T009 | Add parameter, pass to proposer |
| `src/gepa_adk/engine/proposer.py` | T020 | Add INFO log |
| `tests/unit/test_reflection_model_wiring.py` | T001-T005, T014-T015, T019 | New test file |
| `examples/basic_evolution.py` | T013 | Demonstrate reflection_model usage |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable, testable, AND documented
- Verify tests fail before implementing
- Commit after each task or logical group
- Run `uv run mkdocs build` before PR to verify docs build cleanly
- This is a small wiring change (~20 lines) with comprehensive test coverage

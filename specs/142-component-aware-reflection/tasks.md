# Tasks: Component-Aware Reflection Agents

**Input**: Design documents from `/specs/142-component-aware-reflection/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, architecture.md, contracts/

**Tests**: Included per three-layer testing strategy (Constitution IV).

**Documentation**: User-facing feature - requires guide updates and example per Constitution VI.

**Organization**: Tasks grouped by user story. US1 and US2 are both P1 but US1 is MVP (core validation). US2 depends on US1 (auto-selection needs factories from US1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| New public API | Required | Required |
| New config option | Required (guides) | Recommended |

This feature adds new public API (reflection agent factories, validation tool). Requires:
- `docs/guides/single-agent.md` update
- `examples/schema_evolution_validated.py` creation

---

## Phase 1: Setup

**Purpose**: No project setup needed - working within existing codebase

- [x] T001 Verify branch `142-component-aware-reflection` is checked out and up to date

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the validation tool and type definitions that ALL user stories depend on

**⚠️ CRITICAL**: US1-US4 cannot begin until this phase is complete

- [x] T002 Create validate_output_schema tool function in src/gepa_adk/utils/schema_tools.py
- [x] T003 [P] Add component name constants to src/gepa_adk/domain/types.py (COMPONENT_OUTPUT_SCHEMA, COMPONENT_INSTRUCTION)
- [x] T004 [P] Create unit test for validate_output_schema in tests/unit/utils/test_schema_tools.py

**Checkpoint**: Foundation ready - validation tool works, constants defined

---

## Phase 3: User Story 1 - Output Schema Evolution with Validation (Priority: P1) 🎯 MVP

**Goal**: Create schema reflection agent factory with validation tool. Reflection agent can validate proposed schemas before returning.

**Independent Test**: Call `create_schema_reflection_agent(model)`, verify returned agent has `validate_output_schema` tool and schema-focused instruction.

### Tests for User Story 1

- [x] T005 [P] [US1] Unit test for create_schema_reflection_agent factory in tests/unit/engine/test_reflection_agents.py
- [x] T006 [P] [US1] Unit test for create_text_reflection_agent factory in tests/unit/engine/test_reflection_agents.py
- [x] T007 [P] [US1] Unit test for SCHEMA_REFLECTION_INSTRUCTION template in tests/unit/engine/test_reflection_agents.py

### Implementation for User Story 1

- [x] T008 [US1] Create SCHEMA_REFLECTION_INSTRUCTION constant in src/gepa_adk/engine/reflection_agents.py
- [x] T009 [US1] Create create_text_reflection_agent factory function in src/gepa_adk/engine/reflection_agents.py
- [x] T010 [US1] Create create_schema_reflection_agent factory function in src/gepa_adk/engine/reflection_agents.py (depends on T008)
- [x] T011 [US1] Add structlog logging for agent creation in src/gepa_adk/engine/reflection_agents.py

**Checkpoint**: Schema reflection agent factory works. Can create agents with validation tools.

---

## Phase 4: User Story 2 - Automatic Reflection Agent Selection (Priority: P1)

**Goal**: System auto-selects appropriate reflection agent based on component name. Proposer passes component_name to reflection.

**Independent Test**: Evolve "output_schema" component - verify schema reflection agent is used. Evolve "instruction" component - verify text reflection agent is used.

### Tests for User Story 2

- [x] T012 [P] [US2] Unit test for ComponentReflectionRegistry in tests/unit/engine/test_reflection_agents.py
- [x] T013 [P] [US2] Unit test for get_reflection_agent function in tests/unit/engine/test_reflection_agents.py
- [x] T014 [P] [US2] Unit test for updated ReflectionFn signature in tests/unit/engine/test_adk_reflection.py

### Implementation for User Story 2

- [x] T015 [US2] Create ComponentReflectionRegistry class in src/gepa_adk/engine/reflection_agents.py
- [x] T016 [US2] Create get_reflection_agent convenience function in src/gepa_adk/engine/reflection_agents.py
- [x] T017 [US2] Create default registry instance with output_schema registered in src/gepa_adk/engine/reflection_agents.py
- [x] T018 [US2] Modify proposer.py to pass component_name to reflection function in src/gepa_adk/engine/proposer.py
- [x] T019 [US2] Modify create_adk_reflection_fn to accept component_name parameter in src/gepa_adk/engine/adk_reflection.py
- [x] T020 [US2] Implement auto-selection logic in create_adk_reflection_fn in src/gepa_adk/engine/adk_reflection.py (depends on T019)

**Checkpoint**: Auto-selection works. output_schema → schema agent, instruction → text agent.

---

## Phase 5: User Story 3 - Custom Reflection Agent Override (Priority: P2)

**Goal**: Users can provide their own reflection agent, bypassing auto-selection.

**Independent Test**: Provide custom reflection agent to evolve() - verify it is used instead of auto-selected default.

### Tests for User Story 3

- [x] T021 [P] [US3] Unit test for custom agent override in tests/unit/engine/test_adk_reflection.py

### Implementation for User Story 3

- [x] T022 [US3] Ensure create_adk_reflection_fn uses provided agent when not None in src/gepa_adk/engine/adk_reflection.py
- [x] T023 [US3] Add docstring examples showing custom agent usage in src/gepa_adk/engine/adk_reflection.py

**Checkpoint**: Custom override works. User-provided agents take precedence.

---

## Phase 6: User Story 4 - Extensible Validator Registry (Priority: P2)

**Goal**: Registry supports adding new validators without modifying core code.

**Independent Test**: Register mock validator for "my_component" - verify it is invoked during evolution of that component.

### Tests for User Story 4

- [x] T024 [P] [US4] Unit test for registry.register() method in tests/unit/engine/test_reflection_agents.py
- [x] T025 [P] [US4] Unit test for registering custom factory in tests/unit/engine/test_reflection_agents.py

### Implementation for User Story 4

- [x] T026 [US4] Ensure registry.register() allows new component validators in src/gepa_adk/engine/reflection_agents.py
- [x] T027 [US4] Add docstring examples showing registry extension in src/gepa_adk/engine/reflection_agents.py

**Checkpoint**: Registry is extensible. New validators can be added without core changes.

---

## Phase 7: Integration & Documentation

**Purpose**: End-to-end validation, documentation, and examples

### Integration Tests

- [ ] T028 [P] Integration test for schema reflection with real validation in tests/integration/test_schema_reflection.py
- [ ] T029 [P] Integration test for backward compatibility (existing code unchanged) in tests/integration/test_schema_reflection.py

### Documentation (Required per Constitution VI)

- [ ] T030 [P] Update docs/guides/single-agent.md with schema evolution validation section
- [ ] T031 [P] Create examples/schema_evolution_validated.py demonstrating validated schema evolution

### Verification

- [ ] T032 Verify `uv run mkdocs build` passes without warnings
- [ ] T033 Run full test suite with `uv run pytest`
- [ ] T034 Run quickstart.md validation manually

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKS all user stories)
    ↓
Phase 3: US1 (MVP - schema factory)
    ↓
Phase 4: US2 (auto-selection - depends on US1)
    ↓ (can run in parallel with US2 completion)
Phase 5: US3 (custom override)
Phase 6: US4 (registry extension)
    ↓
Phase 7: Integration & Documentation
```

### User Story Dependencies

- **US1 (P1 - MVP)**: Depends on Phase 2 (Foundational). Creates factory functions.
- **US2 (P1)**: Depends on US1 (needs factories to register). Creates registry and auto-selection.
- **US3 (P2)**: Depends on US2 (modifies same reflection code). Ensures override works.
- **US4 (P2)**: Can start after US2. Registry extension doesn't conflict with US3.

### Parallel Opportunities

**Within Phase 2:**
- T003 (constants) and T004 (tests) can run in parallel with T002

**Within US1:**
- T005, T006, T007 (tests) can run in parallel

**Within US2:**
- T012, T013, T014 (tests) can run in parallel

**Within US3/US4:**
- Tests can run in parallel within each story

**Within Phase 7:**
- T028, T029 (integration tests) can run in parallel
- T030, T031 (docs) can run in parallel with integration tests

---

## Parallel Example: Phase 2

```bash
# Launch all foundational tasks in parallel:
Task: "Create validate_output_schema tool function in src/gepa_adk/utils/schema_tools.py"
Task: "Add component name constants to src/gepa_adk/domain/types.py"
Task: "Create unit test for validate_output_schema in tests/unit/utils/test_schema_tools.py"
```

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 tests in parallel:
Task: "Unit test for create_schema_reflection_agent factory"
Task: "Unit test for create_text_reflection_agent factory"
Task: "Unit test for SCHEMA_REFLECTION_INSTRUCTION template"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (verify branch)
2. Complete Phase 2: Foundational (validation tool)
3. Complete Phase 3: User Story 1 (schema factory)
4. **STOP and VALIDATE**: Test factory creates working schema agent
5. Can demo/use schema reflection manually at this point

### Full Feature

1. Setup + Foundational → validation tool ready
2. US1 → schema reflection factory works
3. US2 → auto-selection works (main value)
4. US3 → custom override works (power users)
5. US4 → registry is extensible (future-proofing)
6. Integration + Docs → production ready

### Incremental Value

| Checkpoint | Value Delivered |
|------------|-----------------|
| After US1 | Can manually create schema reflection agents |
| After US2 | Zero-config schema validation during evolution |
| After US3 | Power users can customize reflection |
| After US4 | Future validators can be added easily |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each story is independently testable except US2 depends on US1
- Constitution requires three-layer testing (unit, integration)
- Constitution requires docs/examples for user-facing features
- Run `uv run mkdocs build` before PR to verify docs build

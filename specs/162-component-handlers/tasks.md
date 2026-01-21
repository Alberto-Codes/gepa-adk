# Tasks: ComponentHandler Protocol and Registry

**Input**: Design documents from `/specs/162-component-handlers/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, architecture.md

**Tests**: Three-layer testing is REQUIRED per Constitution Principle IV and ADR-005.

**Documentation**: Internal refactor - no user-facing API changes. Per Constitution VI scope table, docs/ and examples/ updates are NOT required.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root
- Follows hexagonal architecture: ports/ (protocols), adapters/ (implementations)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify project readiness and create necessary test directories

- [x] T001 Verify branch is on 162-component-handlers and git status is clean
- [x] T002 [P] Create test directory tests/unit/ports/ if not exists
- [x] T003 [P] Create test directory tests/contracts/ if not exists

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the ComponentHandler protocol that ALL handlers and registry depend on

**Note**: User Story 1 (Protocol) IS the foundational work - no separate foundational phase needed. US1 must complete before US2 and US3 can begin.

**Checkpoint**: Protocol definition complete - registry and handler implementation can proceed

---

## Phase 3: User Story 1 - Define Component Handling Contract (Priority: P1)

**Goal**: Create the ComponentHandler protocol with serialize, apply, and restore methods

**Independent Test**: Can be fully tested by creating a mock implementation that satisfies the protocol and verifying type compliance

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Contract test for ComponentHandler protocol compliance in tests/contracts/test_component_handler_protocol.py
- [x] T005 [P] [US1] Unit test for protocol definition (method signatures, runtime_checkable) in tests/unit/ports/test_component_handler.py

### Implementation for User Story 1

- [x] T006 [US1] Create ComponentHandler protocol in src/gepa_adk/ports/component_handler.py
  - Define `@runtime_checkable` Protocol class
  - Add `serialize(agent: LlmAgent) -> str` method signature
  - Add `apply(agent: LlmAgent, value: str) -> Any` method signature
  - Add `restore(agent: LlmAgent, original: Any) -> None` method signature
  - Include Google-style docstrings per contracts/component_handler_protocol.md

- [x] T007 [US1] Update src/gepa_adk/ports/__init__.py to export ComponentHandler protocol

**Checkpoint**: Protocol is defined, tests pass - US2 can now begin

---

## Phase 4: User Story 2 - Lookup Registered Handlers (Priority: P1)

**Goal**: Create ComponentHandlerRegistry with register, get, and has operations

**Independent Test**: Can be fully tested by registering handlers and verifying they are retrievable by name

**Dependency**: Requires US1 (ComponentHandler protocol) to be complete

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T008 [P] [US2] Unit test for ComponentHandlerRegistry CRUD operations in tests/unit/adapters/test_component_handlers.py
- [x] T009 [P] [US2] Unit test for registry error handling (empty name, invalid handler, missing handler) in tests/unit/adapters/test_component_handlers.py

### Implementation for User Story 2

- [x] T010 [US2] Create ComponentHandlerRegistry class in src/gepa_adk/adapters/component_handlers.py
  - Implement `__init__` with empty `_handlers: dict[str, ComponentHandler]`
  - Implement `register(name, handler)` with validation per contracts/component_handler_registry.md
  - Implement `get(name)` with KeyError for missing handlers
  - Implement `has(name)` returning bool (no exceptions)
  - Add structlog logging for errors

- [x] T011 [US2] Create default registry instance and convenience functions in src/gepa_adk/adapters/component_handlers.py
  - Add module-level `component_handlers = ComponentHandlerRegistry()`
  - Add `get_handler(name)` convenience function
  - Add `register_handler(name, handler)` convenience function

- [x] T012 [US2] Update src/gepa_adk/adapters/__init__.py to export registry and convenience functions

**Checkpoint**: Registry works, tests pass - US3 can now begin

---

## Phase 5: User Story 3 - Extend Registry with Custom Handlers (Priority: P2)

**Goal**: Implement InstructionHandler and OutputSchemaHandler, pre-register them in default registry

**Independent Test**: Can be fully tested by creating a custom handler, registering it, and verifying it can be retrieved and used

**Dependency**: Requires US1 (protocol) and US2 (registry) to be complete

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T013 [P] [US3] Contract test for InstructionHandler protocol compliance in tests/contracts/test_component_handler_protocol.py
- [x] T014 [P] [US3] Contract test for OutputSchemaHandler protocol compliance in tests/contracts/test_component_handler_protocol.py
- [x] T015 [P] [US3] Unit test for InstructionHandler serialize/apply/restore in tests/unit/adapters/test_component_handlers.py
- [x] T016 [P] [US3] Unit test for OutputSchemaHandler serialize/apply/restore in tests/unit/adapters/test_component_handlers.py
- [x] T017 [P] [US3] Unit test for custom handler registration and retrieval in tests/unit/adapters/test_component_handlers.py
- [x] T018 [P] [US3] Integration test for full serialize/apply/restore cycle with real LlmAgent in tests/integration/test_component_handler_integration.py

### Implementation for User Story 3

- [x] T019 [US3] Implement InstructionHandler class in src/gepa_adk/adapters/component_handlers.py
  - `serialize`: Return `str(agent.instruction)`, empty string if None
  - `apply`: Set `agent.instruction = value`, return original
  - `restore`: Set `agent.instruction = original`
  - Include Google-style docstrings

- [x] T020 [US3] Implement OutputSchemaHandler class in src/gepa_adk/adapters/component_handlers.py
  - `serialize`: Use `serialize_schema(agent.output_schema)`, empty string if None
  - `apply`: Deserialize value, set schema, return original; log warning and keep original on SchemaValidationError
  - `restore`: Set `agent.output_schema = original`
  - Include Google-style docstrings

- [x] T021 [US3] Register default handlers in module initialization in src/gepa_adk/adapters/component_handlers.py
  - Register InstructionHandler for "instruction" component
  - Register OutputSchemaHandler for "output_schema" component

- [x] T022 [US3] Update src/gepa_adk/adapters/__init__.py to export InstructionHandler and OutputSchemaHandler

**Checkpoint**: All handlers work, extensibility proven via custom handler test

---

## Phase 6: Verification & Cross-Cutting Concerns

**Purpose**: Final verification and quality checks

### Quality Verification

- [x] T023 Run full test suite: `uv run pytest tests/contracts/test_component_handler_protocol.py tests/unit/adapters/test_component_handlers.py tests/unit/ports/test_component_handler.py tests/integration/test_component_handler_integration.py -v`
- [x] T024 Run linting: `uv run ruff check src/gepa_adk/ports/component_handler.py src/gepa_adk/adapters/component_handlers.py`
- [x] T025 Run type checking: `uv run ty check src/gepa_adk/ports/component_handler.py src/gepa_adk/adapters/component_handlers.py`
- [x] T026 Verify docstring coverage: `uv run interrogate src/gepa_adk/ports/component_handler.py src/gepa_adk/adapters/component_handlers.py`

### Layer Import Verification (Hexagonal Architecture)

- [x] T027 Verify ports/component_handler.py has NO external imports (only typing, stdlib)
- [x] T028 Verify adapters/component_handlers.py imports only from allowed layers (ports/, domain/, external libs)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **User Story 1 (Phase 3)**: Depends on Setup - BLOCKS US2 and US3
- **User Story 2 (Phase 4)**: Depends on US1 completion
- **User Story 3 (Phase 5)**: Depends on US1 and US2 completion
- **Verification (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

```
US1 (Protocol Definition) ─────────────────────┐
         │                                      │
         ▼                                      │
US2 (Registry & Lookup) ──────────────────────┼───→ US3 (Handlers & Extensibility)
                                               │
                                               ▼
                                    Phase 6 (Verification)
```

- **User Story 1 (P1)**: Foundation - must complete first
- **User Story 2 (P1)**: Depends on US1 - registry needs protocol
- **User Story 3 (P2)**: Depends on US1 and US2 - handlers need both protocol and registry

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Protocol before registry
- Registry before handlers
- Core implementation before convenience functions
- Story complete before moving to next

### Parallel Opportunities

**Within US1**:
- T004 and T005 (tests) can run in parallel

**Within US2**:
- T008 and T009 (tests) can run in parallel

**Within US3**:
- T013, T014, T015, T016, T017, T018 (all tests) can run in parallel
- After tests pass and T019/T020 complete, T021 and T022 are sequential

---

## Parallel Example: User Story 3 Tests

```bash
# Launch all tests for User Story 3 together:
Task: "Contract test for InstructionHandler in tests/contracts/test_component_handler_protocol.py"
Task: "Contract test for OutputSchemaHandler in tests/contracts/test_component_handler_protocol.py"
Task: "Unit test for InstructionHandler in tests/unit/adapters/test_component_handlers.py"
Task: "Unit test for OutputSchemaHandler in tests/unit/adapters/test_component_handlers.py"
Task: "Unit test for custom handler registration in tests/unit/adapters/test_component_handlers.py"
Task: "Integration test for full cycle in tests/integration/test_component_handler_integration.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 3: User Story 1 (Protocol Definition)
3. **STOP and VALIDATE**: Protocol tests pass, isinstance() works
4. This provides the foundational abstraction

### Incremental Delivery

1. Add User Story 1 → Protocol exists → Can define handlers
2. Add User Story 2 → Registry works → Can register/lookup handlers
3. Add User Story 3 → Built-in handlers → Full functionality
4. Each story adds value without breaking previous stories

### Suggested Flow

1. **Day 1**: Setup + US1 (Protocol) - minimal, testable foundation
2. **Day 2**: US2 (Registry) - enables dynamic handler access
3. **Day 3**: US3 (Handlers) - full implementation with built-in handlers
4. **Day 4**: Verification - ensure all quality gates pass

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- This is an internal refactor - no docs/examples updates required per Constitution VI
- Follow hexagonal architecture: protocol in ports/, implementations in adapters/

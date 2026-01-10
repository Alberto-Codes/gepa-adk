# Tasks: AsyncGEPAAdapter Protocol

**Input**: Design documents from `/specs/004-async-gepa-adapter/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Contract tests are REQUIRED per ADR-005 (Three-Layer Testing). This feature defines a protocol interface, so contract tests verify protocol compliance.

**Testing Scope**: This feature defines a **protocol interface only** (no business logic). Per ADR-005:
- **Contract tests**: ✅ Required - verify protocol compliance
- **Unit tests**: N/A - no business logic to test
- **Integration tests**: N/A - no external system integration

Adapter implementations (Issue #8) will require all three layers.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root
- Follows hexagonal architecture: `domain/`, `ports/`, `adapters/`, `engine/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the ports directory structure for protocol definitions

- [ ] T001 Create ports directory structure in src/gepa_adk/ports/
- [ ] T002 [P] Create src/gepa_adk/ports/__init__.py with module docstring
- [ ] T003 [P] Create tests/contracts/ directory for protocol compliance tests
- [ ] T004 [P] Create tests/contracts/__init__.py

**Checkpoint**: Directory structure ready for protocol implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define TypeVars and EvaluationBatch dataclass that ALL protocol methods depend on

**⚠️ CRITICAL**: Protocol definition cannot proceed without these types

- [ ] T005 Define TypeVars (DataInst, Trajectory, RolloutOutput) in src/gepa_adk/ports/adapter.py
- [ ] T006 Implement EvaluationBatch frozen dataclass with slots=True in src/gepa_adk/ports/adapter.py

**Checkpoint**: Foundation types ready - protocol definition can now begin

---

## Phase 3: User Story 1 - Define Adapter Protocol (Priority: P1) 🎯 MVP

**Goal**: Define the AsyncGEPAAdapter protocol with three async methods (evaluate, make_reflective_dataset, propose_new_texts)

**Independent Test**: Create a mock implementation that satisfies the protocol; verify methods have correct signatures

### Contract Tests for User Story 1 (Required per ADR-005)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T007 [P] [US1] Create MockAdapter class skeleton in tests/contracts/test_adapter_protocol.py
- [ ] T008 [P] [US1] Write contract test CR-003 for evaluate() method structure in tests/contracts/test_adapter_protocol.py
- [ ] T009 [P] [US1] Write contract test CR-004 for make_reflective_dataset() structure in tests/contracts/test_adapter_protocol.py
- [ ] T010 [P] [US1] Write contract test CR-005 for propose_new_texts() structure in tests/contracts/test_adapter_protocol.py

### Implementation for User Story 1

- [ ] T011 [US1] Define evaluate() async method signature in AsyncGEPAAdapter protocol in src/gepa_adk/ports/adapter.py
- [ ] T012 [US1] Define make_reflective_dataset() async method signature in AsyncGEPAAdapter protocol in src/gepa_adk/ports/adapter.py
- [ ] T013 [US1] Define propose_new_texts() async method signature in AsyncGEPAAdapter protocol in src/gepa_adk/ports/adapter.py
- [ ] T014 [US1] Add Google-style docstrings for AsyncGEPAAdapter and all methods in src/gepa_adk/ports/adapter.py
- [ ] T015 [US1] Add Google-style docstrings for EvaluationBatch in src/gepa_adk/ports/adapter.py
- [ ] T016 [US1] Complete MockAdapter implementation with all three methods in tests/contracts/test_adapter_protocol.py
- [ ] T017 [US1] Run contract tests T008-T010 and verify they pass

**Checkpoint**: Protocol is defined with three async methods; MockAdapter passes contract tests

---

## Phase 4: User Story 2 - Runtime Type Checking (Priority: P1)

**Goal**: Add @runtime_checkable decorator so isinstance() checks work at runtime

**Independent Test**: Verify isinstance(mock_adapter, AsyncGEPAAdapter) returns True; verify incomplete implementation returns False

### Contract Tests for User Story 2 (Required per ADR-005)

- [ ] T018 [P] [US2] Write contract test CR-001 for runtime checkable isinstance() in tests/contracts/test_adapter_protocol.py
- [ ] T019 [P] [US2] Write contract test CR-002 for async method coroutine verification in tests/contracts/test_adapter_protocol.py
- [ ] T020 [P] [US2] Write negative test for incomplete implementation rejection in tests/contracts/test_adapter_protocol.py
- [ ] T020a [P] [US2] Write test for sync method rejection (edge case: non-async method) in tests/contracts/test_adapter_protocol.py

### Implementation for User Story 2

- [ ] T021 [US2] Add @runtime_checkable decorator to AsyncGEPAAdapter in src/gepa_adk/ports/adapter.py
- [ ] T022 [US2] Run contract tests T018-T020 and verify they pass

**Checkpoint**: Protocol supports isinstance() checks; incomplete implementations are correctly rejected

---

## Phase 5: User Story 3 - Generic Type Parameters (Priority: P2)

**Goal**: Support generic type parameters so adapters can use domain-specific types

**Independent Test**: Create two mock adapters with different generic type arguments; verify both satisfy the protocol

### Contract Tests for User Story 3 (Required per ADR-005)

- [ ] T023 [P] [US3] Write test for protocol with specific generic types in tests/contracts/test_adapter_protocol.py
- [ ] T024 [P] [US3] Write test for multiple adapters with different generic types in tests/contracts/test_adapter_protocol.py

### Implementation for User Story 3

- [ ] T025 [US3] Add Generic[DataInst, Trajectory, RolloutOutput] to protocol class definition in src/gepa_adk/ports/adapter.py
- [ ] T026 [US3] Update EvaluationBatch to use Generic[Trajectory, RolloutOutput] in src/gepa_adk/ports/adapter.py
- [ ] T027 [US3] Run contract tests T023-T024 and verify they pass

**Checkpoint**: Protocol supports generic types; type checkers enforce type safety

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, exports, and type checking

- [ ] T028 [P] Export AsyncGEPAAdapter, EvaluationBatch, and TypeVars from src/gepa_adk/ports/__init__.py
- [ ] T029 [P] Add ports module to src/gepa_adk/__init__.py exports
- [ ] T030 Run uv run ty check to verify zero type errors
- [ ] T031 Run uv run ruff check --fix and uv run ruff format
- [ ] T032 Run full contract test suite: uv run pytest tests/contracts/ -v
- [ ] T033 Validate quickstart.md code examples compile correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (TypeVars, EvaluationBatch)
- **User Story 2 (Phase 4)**: Depends on User Story 1 (protocol must exist to add decorator)
- **User Story 3 (Phase 5)**: Can run in parallel with User Story 2 after User Story 1
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational types - Core protocol definition
- **User Story 2 (P1)**: Depends on US1 - Adds @runtime_checkable to existing protocol
- **User Story 3 (P2)**: Depends on US1 - Adds Generic parameters (can parallel with US2)

### Within Each User Story

- Contract tests MUST be written and FAIL before implementation (TDD per ADR-005)
- Method signatures before docstrings
- Implementation before test verification
- All tests must pass before story is complete

### Parallel Opportunities

**Phase 1 (Setup):**
```
T002 [P] ports/__init__.py
T003 [P] tests/contracts/ directory
T004 [P] tests/contracts/__init__.py
```

**Phase 3 (US1 Tests):**
```
T007 [P] MockAdapter skeleton
T008 [P] evaluate() contract test
T009 [P] make_reflective_dataset() contract test
T010 [P] propose_new_texts() contract test
```

**Phase 4 (US2 Tests):**
```
T018 [P] isinstance() test
T019 [P] coroutine verification test
T020 [P] incomplete implementation test
```

**Phase 5 (US3 Tests):**
```
T023 [P] specific generic types test
T024 [P] multiple adapters test
```

**Phase 6 (Polish):**
```
T028 [P] ports/__init__.py exports
T029 [P] main __init__.py exports
```

---

## Parallel Example: User Story 1 Contract Tests

```bash
# Launch all contract tests for US1 together:
Task: "Create MockAdapter class skeleton in tests/contracts/test_adapter_protocol.py"
Task: "Write contract test CR-003 for evaluate() method structure"
Task: "Write contract test CR-004 for make_reflective_dataset() structure"
Task: "Write contract test CR-005 for propose_new_texts() structure"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (directory structure)
2. Complete Phase 2: Foundational (TypeVars, EvaluationBatch)
3. Complete Phase 3: User Story 1 (protocol with 3 methods)
4. **STOP and VALIDATE**: Run contract tests, verify MockAdapter works
5. Protocol is usable for downstream features (Issue #6, #8)

### Incremental Delivery

1. Complete Setup + Foundational → Types ready
2. Add User Story 1 → Protocol defined → Can be used by engine (Issue #6)
3. Add User Story 2 → isinstance() works → Better runtime validation
4. Add User Story 3 → Generics work → Type safety for adapters (Issue #8)

### Single Developer Sequence

```
T001 → T002-T004 (parallel) → T005 → T006 →
T007-T010 (parallel) → T011-T017 (sequential) →
T018-T020 (parallel) → T021-T022 (sequential) →
T023-T024 (parallel) → T025-T027 (sequential) →
T028-T029 (parallel) → T030-T033 (sequential)
```

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Contract tests are REQUIRED per ADR-005 Three-Layer Testing
- Verify tests FAIL before implementing (Red-Green-Refactor)
- All code must have Google-style docstrings per ADR-010
- Commit after each phase completion
- Total: 34 tasks across 6 phases

# Tasks: Output Schema Evolution

**Input**: Design documents from `/specs/123-output-schema-evolution/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, architecture.md, contracts/

**Tests**: Three-layer testing required per Constitution (ADR-005) and plan.md.

**Documentation**: Per Constitution Principle VI, this feature adds new public API capabilities and requires docs/ and examples/ updates.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/gepa_adk/`
- **Tests**: `tests/` (contracts/, unit/, integration/)
- **Docs**: `docs/guides/`, `examples/`

---

## Phase 1: Setup

**Purpose**: Verify existing infrastructure supports the feature

- [x] T001 Verify existing SchemaValidationError in src/gepa_adk/domain/exceptions.py has required fields (raw_output, validation_error, cause)
- [x] T002 [P] Verify Candidate.components supports arbitrary keys in src/gepa_adk/domain/models.py
- [x] T003 [P] Create empty src/gepa_adk/utils/schema_utils.py with module docstring

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the schema_utils module structure and data types needed by all user stories

**⚠️ CRITICAL**: All user stories depend on this phase completing first

- [x] T004 Define SCHEMA_NAMESPACE constant with allowed types in src/gepa_adk/utils/schema_utils.py
- [x] T005 Define SchemaValidationResult dataclass in src/gepa_adk/utils/schema_utils.py
- [x] T006 [P] Extend SchemaValidationError with line_number and validation_stage fields in src/gepa_adk/domain/exceptions.py
- [x] T007 Add schema_utils exports to src/gepa_adk/utils/__init__.py
- [x] T008 Copy contract tests from specs/123-output-schema-evolution/contracts/schema_utils_contract.py to tests/contracts/test_schema_utils_contract.py

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Evolve Output Schema (Priority: P1) 🎯 MVP

**Goal**: Enable serialization of Pydantic schemas to text for evolution as components

**Independent Test**: Configure evolution with `components=["output_schema"]` on an agent with output_schema, verify schema text is stored in Candidate.components

### Tests for User Story 1

- [x] T009 [P] [US1] Create unit tests for serialize_pydantic_schema() in tests/unit/utils/test_schema_utils.py
- [x] T010 [P] [US1] Run contract tests for serialization (TestSerializePydanticSchemaContract) - verify they FAIL

### Implementation for User Story 1

- [x] T011 [US1] Implement serialize_pydantic_schema() using inspect.getsource() in src/gepa_adk/utils/schema_utils.py
- [x] T012 [US1] Add type checking to reject non-BaseModel classes in serialize_pydantic_schema()
- [x] T013 [US1] Add structured logging for serialization operations in src/gepa_adk/utils/schema_utils.py
- [x] T014 [US1] Run contract tests for serialization - verify they PASS

### Documentation for User Story 1

- [x] T015 [P] [US1] Add "Output Schema Evolution" section to docs/guides/single-agent.md
- [x] T016 [P] [US1] Add schema_utils terms to docs/reference/glossary.md

**Checkpoint**: Serialization complete - schemas can be converted to text for evolution

---

## Phase 4: User Story 2 - Validate Schema Mutations (Priority: P2)

**Goal**: Validate proposed schema text before acceptance to reject invalid schemas

**Independent Test**: Pass valid/invalid schema texts to validator, verify correct accept/reject decisions

### Tests for User Story 2

- [x] T017 [P] [US2] Create unit tests for validate_schema_text() syntax validation in tests/unit/utils/test_schema_utils.py
- [x] T018 [P] [US2] Create unit tests for validate_schema_text() structure validation (BaseModel check) in tests/unit/utils/test_schema_utils.py
- [x] T019 [P] [US2] Create unit tests for validate_schema_text() security rules (no imports, no functions) in tests/unit/utils/test_schema_utils.py
- [x] T020 [P] [US2] Run contract tests for validation (TestValidateSchemaTextContract) - verify they FAIL

### Implementation for User Story 2

- [x] T021 [US2] Implement AST parsing for syntax validation in validate_schema_text() in src/gepa_adk/utils/schema_utils.py
- [x] T022 [US2] Implement AST checks to reject import statements in validate_schema_text()
- [x] T023 [US2] Implement AST checks to reject function definitions in validate_schema_text()
- [x] T024 [US2] Implement AST check for BaseModel inheritance in validate_schema_text()
- [x] T025 [US2] Implement controlled exec() with SCHEMA_NAMESPACE in validate_schema_text()
- [x] T026 [US2] Return SchemaValidationResult with class metadata from validate_schema_text()
- [x] T027 [US2] Add structured logging for validation operations with stage indicators
- [x] T028 [US2] Run contract tests for validation - verify they PASS

**Checkpoint**: Validation complete - invalid schemas are rejected with clear error messages

---

## Phase 5: User Story 3 - Use Evolved Schema (Priority: P3)

**Goal**: Convert evolved schema text back to usable Pydantic model class

**Independent Test**: Deserialize valid schema text, verify resulting class works as agent.output_schema

### Tests for User Story 3

- [x] T029 [P] [US3] Create unit tests for deserialize_schema() in tests/unit/utils/test_schema_utils.py
- [x] T030 [P] [US3] Create round-trip tests (serialize → deserialize) in tests/unit/utils/test_schema_utils.py
- [x] T031 [P] [US3] Run contract tests for deserialization (TestDeserializeSchemaContract, TestRoundTripContract) - verify they FAIL

### Implementation for User Story 3

- [x] T032 [US3] Implement deserialize_schema() as convenience wrapper around validate_schema_text() in src/gepa_adk/utils/schema_utils.py
- [x] T033 [US3] Add structured logging for deserialization operations
- [x] T034 [US3] Run contract tests for deserialization - verify they PASS

### Documentation for User Story 3

- [x] T035 [P] [US3] Create examples/schema_evolution_example.py demonstrating full workflow
- [x] T036 [P] [US3] Update docs/guides/single-agent.md with deserialization usage

**Checkpoint**: Full schema evolution workflow complete - serialize → evolve → deserialize

---

## Phase 6: Integration & Verification

**Purpose**: End-to-end integration and cross-cutting concerns

### Engine Integration

- [x] T037 Add validation hook in src/gepa_adk/engine/async_engine.py to call validate_schema_text() before accepting proposals with "output_schema" component

### Integration Tests

- [x] T038 Create integration test for schema evolution in tests/integration/test_output_schema_evolution.py
- [x] T039 Test evolution with components=["output_schema"] produces valid evolved schema
- [x] T040 Test evolution with components=["instruction", "output_schema"] works for both components

### Documentation Build Verification

- [x] T041 Verify `uv run mkdocs build` passes without warnings
- [x] T042 Preview docs with `uv run mkdocs serve` and verify schema evolution sections render correctly

### Final Verification

- [x] T043 Run full test suite with `uv run pytest -n auto`
- [x] T044 Run type checking with `uv run ty check`
- [x] T045 Run linting with `uv run ruff check`
- [x] T046 Validate quickstart.md scenarios work end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verify existing infrastructure
- **Foundational (Phase 2)**: Depends on Setup - creates shared data types
- **User Story 1 (Phase 3)**: Depends on Foundational - serialization
- **User Story 2 (Phase 4)**: Depends on Foundational - validation (can run parallel to US1)
- **User Story 3 (Phase 5)**: Depends on US2 completion - deserialization uses validation
- **Integration (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKS all stories)
    ↓
    ├──→ Phase 3: US1 (Serialization) ──────────────────────────┐
    │                                                           │
    └──→ Phase 4: US2 (Validation) ─→ Phase 5: US3 (Deserialize)┤
                                                                ↓
                                              Phase 6: Integration
```

### Within Each User Story

1. Tests written and FAIL before implementation
2. Implementation tasks in dependency order
3. Tests PASS after implementation
4. Documentation updates complete before story done

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T006 (exceptions) can run parallel to T004-T005 (schema_utils)

**Phase 3 (US1)**:
- T009, T010 (tests) can run parallel
- T015, T016 (docs) can run parallel after implementation

**Phase 4 (US2)**:
- T017, T018, T019, T020 (tests) can all run parallel
- US2 can start parallel to US1 (different functions)

**Phase 5 (US3)**:
- T029, T030, T031 (tests) can run parallel
- T035, T036 (docs) can run parallel after implementation

---

## Parallel Example: User Story 2 Tests

```bash
# Launch all US2 tests together:
Task: "Create unit tests for validate_schema_text() syntax validation"
Task: "Create unit tests for validate_schema_text() structure validation"
Task: "Create unit tests for validate_schema_text() security rules"
Task: "Run contract tests for validation"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup verification
2. Complete Phase 2: Foundational (data types)
3. Complete Phase 3: User Story 1 (serialization)
4. **STOP and VALIDATE**: Can serialize schemas to text
5. Useful even without validation/deserialization

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Serialization) → Schemas become component text (MVP!)
3. Add US2 (Validation) → Invalid proposals rejected
4. Add US3 (Deserialization) → Full round-trip workflow
5. Integration → End-to-end validation

### File Summary

| File | Action | Stories |
|------|--------|---------|
| `src/gepa_adk/utils/schema_utils.py` | CREATE | US1, US2, US3 |
| `src/gepa_adk/domain/exceptions.py` | MODIFY | Foundational |
| `src/gepa_adk/utils/__init__.py` | MODIFY | Foundational |
| `src/gepa_adk/engine/async_engine.py` | MODIFY | Integration |
| `tests/contracts/test_schema_utils_contract.py` | CREATE | Foundational |
| `tests/unit/utils/test_schema_utils.py` | CREATE | US1, US2, US3 |
| `tests/integration/test_output_schema_evolution.py` | CREATE | Integration |
| `docs/guides/single-agent.md` | MODIFY | US1, US3 |
| `docs/reference/glossary.md` | MODIFY | US1 |
| `examples/schema_evolution_example.py` | CREATE | US3 |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each story independently testable per spec.md acceptance scenarios
- Three-layer testing per ADR-005: contract → unit → integration
- Security: AST validation before exec() per research.md
- All schemas must be self-contained (no imports) per A-004

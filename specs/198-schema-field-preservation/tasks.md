# Tasks: Required Field Preservation for Output Schema Evolution

**Input**: Design documents from `/specs/198-schema-field-preservation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, architecture.md

**Tests**: This feature requires three-layer testing per ADR-005 (contract, unit, integration).

**Documentation**: Per Constitution Principle VI, this feature adds a new public API parameter (`schema_constraints`) and requires documentation updates.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| New public API (`schema_constraints`) | Required | Required |

---

## Phase 1: Setup

**Purpose**: Verify project structure and existing code patterns

- [ ] T001 Verify existing OutputSchemaHandler in src/gepa_adk/adapters/component_handlers.py
- [ ] T002 Verify existing schema_utils.py patterns in src/gepa_adk/utils/schema_utils.py
- [ ] T003 [P] Verify domain/types.py patterns (TrajectoryConfig, ComponentSpec) in src/gepa_adk/domain/types.py

---

## Phase 2: Foundational (Domain Layer)

**Purpose**: Add SchemaConstraints dataclass that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational

- [ ] T004 [P] Contract test for SchemaConstraints immutability in tests/contracts/test_schema_constraints_contract.py
- [ ] T005 [P] Unit test for SchemaConstraints dataclass in tests/unit/domain/test_schema_constraints.py

### Implementation for Foundational

- [ ] T006 Add SchemaConstraints frozen dataclass to src/gepa_adk/domain/types.py
- [ ] T007 Export SchemaConstraints in src/gepa_adk/domain/__init__.py and src/gepa_adk/__init__.py

**Checkpoint**: SchemaConstraints dataclass is available for all user stories

---

## Phase 3: User Story 1 - Preserve Critical Fields in Critic Agents (Priority: P1) 🎯 MVP

**Goal**: Reject schema mutations that remove required fields, preserving schema integrity for critic agents

**Independent Test**: Evolve a critic agent with `required_fields=["score"]` and verify mutations removing `score` are rejected

### Tests for User Story 1

- [ ] T008 [P] [US1] Contract test for required field validation in tests/contracts/test_schema_constraints_contract.py
- [ ] T009 [P] [US1] Unit test for validate_schema_against_constraints (required fields) in tests/unit/utils/test_schema_constraint_validation.py
- [ ] T010 [P] [US1] Unit test for OutputSchemaHandler constraint integration in tests/unit/adapters/test_output_schema_handler_constraints.py

### Implementation for User Story 1

- [ ] T011 [US1] Add validate_schema_against_constraints() for required fields in src/gepa_adk/utils/schema_utils.py
- [ ] T012 [US1] Add set_constraints() method to OutputSchemaHandler in src/gepa_adk/adapters/component_handlers.py
- [ ] T013 [US1] Modify OutputSchemaHandler.apply() to validate against constraints in src/gepa_adk/adapters/component_handlers.py
- [ ] T014 [US1] Add schema_constraints parameter to evolve() in src/gepa_adk/api.py
- [ ] T015 [US1] Thread schema_constraints to OutputSchemaHandler in evolve() in src/gepa_adk/api.py
- [ ] T016 [US1] Add configuration-time validation (fail fast) in src/gepa_adk/api.py

### Documentation for User Story 1

- [ ] T017 [P] [US1] Update docs/guides/single-agent.md with schema_constraints example
- [ ] T018 [P] [US1] Add schema constraints example to examples/ directory

**Checkpoint**: Required field preservation works end-to-end. Critic agents can protect `score` and `feedback` fields.

---

## Phase 4: User Story 2 - Preserve Field Types During Evolution (Priority: P2)

**Goal**: Reject schema mutations that change constrained field types to incompatible types

**Independent Test**: Evolve an agent with `preserve_types={"score": float}` and verify mutations changing `score` to `str` are rejected

### Tests for User Story 2

- [ ] T019 [P] [US2] Contract test for type preservation in tests/contracts/test_schema_constraints_contract.py
- [ ] T020 [P] [US2] Unit test for type compatibility checking in tests/unit/utils/test_schema_constraint_validation.py
- [ ] T021 [P] [US2] Unit test for tuple type matching in tests/unit/utils/test_schema_constraint_validation.py

### Implementation for User Story 2

- [ ] T022 [US2] Add _extract_field_type() helper for Pydantic type extraction in src/gepa_adk/utils/schema_utils.py
- [ ] T023 [US2] Add _is_type_compatible() helper for type matching in src/gepa_adk/utils/schema_utils.py
- [ ] T024 [US2] Extend validate_schema_against_constraints() for preserve_types in src/gepa_adk/utils/schema_utils.py
- [ ] T025 [US2] Add type constraint validation to configuration-time checks in src/gepa_adk/api.py

### Documentation for User Story 2

- [ ] T026 [P] [US2] Update docs/guides/single-agent.md with preserve_types examples
- [ ] T027 [P] [US2] Update examples/ with type preservation scenario

**Checkpoint**: Type preservation works. Users can constrain `score` to `(float, int)` to prevent string mutations.

---

## Phase 5: User Story 3 - Preserve Field Constraints/Bounds (Priority: P3)

**Goal**: Optional enhancement to preserve field validation bounds (ge, le, etc.)

**Status**: OUT OF SCOPE for this implementation per spec.md (FR-010: "MAY support")

**Note**: This user story is deferred to a future iteration. The architecture supports extension but bounds preservation is not implemented in this feature.

---

## Phase 6: Integration & Verification

**Purpose**: End-to-end validation and cross-cutting concerns

### Integration Tests

- [ ] T028 [P] Integration test for schema-constrained evolution in tests/integration/test_schema_constrained_evolution.py
- [ ] T029 [P] Integration test for backward compatibility (no constraints) in tests/integration/test_schema_constrained_evolution.py

### Documentation Build Verification

- [ ] T030 Verify `uv run mkdocs build` passes without warnings
- [ ] T031 Preview docs with `uv run mkdocs serve` and verify changes render correctly

### Cross-Cutting Tasks

- [ ] T032 Run full test suite with `uv run pytest tests/ -x --ignore=tests/integration --ignore=tests/api`
- [ ] T033 Run quickstart.md validation scenarios manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verification only
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 (extends validation function)
- **User Story 3 (Phase 5)**: DEFERRED - not implemented
- **Integration (Phase 6)**: Depends on User Stories 1 & 2 completion

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Extends US1's validate_schema_against_constraints() - should follow US1

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Domain types before utils
- Utils before adapters
- Adapters before API
- Documentation updates complete before story is done

### Parallel Opportunities

**Phase 2 (Foundational):**
- T004 and T005 can run in parallel (different test files)

**Phase 3 (User Story 1):**
- T008, T009, T010 can run in parallel (different test files)
- T017, T018 can run in parallel (docs and examples)

**Phase 4 (User Story 2):**
- T019, T020, T021 can run in parallel (test files)
- T026, T027 can run in parallel (docs and examples)

**Phase 6 (Integration):**
- T028, T029 can run in parallel (same file but independent tests)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for required field validation in tests/contracts/test_schema_constraints_contract.py"
Task: "Unit test for validate_schema_against_constraints in tests/unit/utils/test_schema_constraint_validation.py"
Task: "Unit test for OutputSchemaHandler constraint integration in tests/unit/adapters/test_output_schema_handler_constraints.py"

# After tests pass, launch documentation in parallel:
Task: "Update docs/guides/single-agent.md with schema_constraints example"
Task: "Add schema constraints example to examples/ directory"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verification)
2. Complete Phase 2: Foundational (SchemaConstraints dataclass)
3. Complete Phase 3: User Story 1 (required_fields)
4. **STOP and VALIDATE**: Test required field preservation independently
5. Can deploy with just required_fields support

### Incremental Delivery

1. Complete Setup + Foundational → SchemaConstraints available
2. Add User Story 1 → Test → Deploy (MVP: required_fields)
3. Add User Story 2 → Test → Deploy (preserve_types)
4. User Story 3 → Deferred to future iteration

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Story 3 (P3) is explicitly out of scope per spec.md FR-010
- Backward compatibility is critical - all existing tests must pass
- Validation < 1ms per mutation (performance goal from plan.md)
- Commit after each task or logical group
- Run `uv run mkdocs build` before PR to verify docs build cleanly

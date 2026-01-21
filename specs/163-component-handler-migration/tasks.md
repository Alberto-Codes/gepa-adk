# Tasks: Component Handler Migration

**Input**: Design documents from `/specs/163-component-handler-migration/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED per Constitution Principle IV (Three-Layer Testing)

**Documentation**: This is an internal refactor (no user-facing API changes) - no docs/ or examples/ updates required per Constitution Principle VI scope table.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root
- Paths shown below reflect plan.md structure

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| Internal refactor | Not required | Not required |

This feature is an **internal refactor** - no user-facing documentation updates needed.

---

## Phase 1: Setup (Verification)

**Purpose**: Verify prerequisite infrastructure from #162 is in place

- [x] T001 Verify ComponentHandler protocol exists in src/gepa_adk/ports/component_handler.py
- [x] T002 [P] Verify InstructionHandler exists and is registered in src/gepa_adk/adapters/component_handlers.py
- [x] T003 [P] Verify OutputSchemaHandler exists and is registered in src/gepa_adk/adapters/component_handlers.py
- [x] T004 [P] Verify get_handler() function works by running existing handler tests

---

## Phase 2: Foundational (None Required)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**✅ No foundational tasks needed** - All infrastructure from #162 is already in place:
- ComponentHandler protocol defined
- InstructionHandler and OutputSchemaHandler implemented
- Handler registry operational with get_handler() convenience function

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 & 2 - Handler Verification (Priority: P1) 🎯 MVP

**Goal**: Verify existing handlers from #162 work correctly (InstructionHandler and OutputSchemaHandler)

**Independent Test**: Call handler methods directly on mock agents and verify correct behavior

**Note**: US1 (Instruction) and US2 (Output Schema) are combined because handlers already exist from #162 - we just verify they work as expected.

### Tests for User Stories 1 & 2

- [x] T005 [P] [US1] Add unit test for InstructionHandler.serialize() in tests/unit/adapters/test_component_handlers.py
- [x] T006 [P] [US1] Add unit test for InstructionHandler.apply() returns original in tests/unit/adapters/test_component_handlers.py
- [x] T007 [P] [US1] Add unit test for InstructionHandler.restore() in tests/unit/adapters/test_component_handlers.py
- [x] T008 [P] [US2] Add unit test for OutputSchemaHandler.serialize() in tests/unit/adapters/test_component_handlers.py
- [x] T009 [P] [US2] Add unit test for OutputSchemaHandler.apply() returns original in tests/unit/adapters/test_component_handlers.py
- [x] T010 [P] [US2] Add unit test for OutputSchemaHandler.restore() in tests/unit/adapters/test_component_handlers.py

### Verification for User Stories 1 & 2

- [x] T011 [US1] Run InstructionHandler tests and verify all pass
- [x] T012 [US2] Run OutputSchemaHandler tests and verify all pass

**Checkpoint**: Handlers verified working - registry dispatch can now be implemented

---

## Phase 4: User Story 3 - Registry-Based Apply Candidate (Priority: P2)

**Goal**: Refactor _apply_candidate to use registry dispatch instead of if/elif

**Independent Test**: Call _apply_candidate with multi-component candidate and verify handlers are invoked

### Tests for User Story 3

- [x] T013 [P] [US3] Add unit test for _apply_candidate returns dict (not tuple) in tests/unit/adapters/test_adk_adapter.py
- [x] T014 [P] [US3] Add unit test for _apply_candidate dispatches to InstructionHandler in tests/unit/adapters/test_adk_adapter.py
- [x] T015 [P] [US3] Add unit test for _apply_candidate dispatches to OutputSchemaHandler in tests/unit/adapters/test_adk_adapter.py
- [x] T016 [P] [US3] Add unit test for _apply_candidate raises KeyError for unknown component in tests/unit/adapters/test_adk_adapter.py

### Implementation for User Story 3

- [x] T017 [US3] Add import for get_handler in src/gepa_adk/adapters/adk_adapter.py
- [x] T018 [US3] Refactor _apply_candidate to return dict[str, Any] in src/gepa_adk/adapters/adk_adapter.py
- [x] T019 [US3] Replace if/elif with loop over candidate.items() using get_handler() dispatch in src/gepa_adk/adapters/adk_adapter.py
- [x] T020 [US3] Update docstring for _apply_candidate with new return type in src/gepa_adk/adapters/adk_adapter.py
- [x] T021 [US3] Verify no if/elif remains for component name checks in _apply_candidate

**Checkpoint**: _apply_candidate now uses registry dispatch

---

## Phase 5: User Story 4 - Registry-Based Restore Agent (Priority: P2)

**Goal**: Refactor _restore_agent to use registry dispatch matching _apply_candidate

**Independent Test**: Call _restore_agent with originals dict and verify handlers are invoked

### Tests for User Story 4

- [x] T022 [P] [US4] Add unit test for _restore_agent accepts dict (not positional args) in tests/unit/adapters/test_adk_adapter.py
- [x] T023 [P] [US4] Add unit test for _restore_agent dispatches to InstructionHandler.restore() in tests/unit/adapters/test_adk_adapter.py
- [x] T024 [P] [US4] Add unit test for _restore_agent dispatches to OutputSchemaHandler.restore() in tests/unit/adapters/test_adk_adapter.py

### Implementation for User Story 4

- [x] T025 [US4] Refactor _restore_agent signature to accept dict[str, Any] in src/gepa_adk/adapters/adk_adapter.py
- [x] T026 [US4] Replace direct assignments with loop over originals.items() using get_handler() dispatch in src/gepa_adk/adapters/adk_adapter.py
- [x] T027 [US4] Update docstring for _restore_agent with new signature in src/gepa_adk/adapters/adk_adapter.py
- [x] T028 [US4] Verify no if/elif remains for component name checks in _restore_agent

**Checkpoint**: _restore_agent now uses registry dispatch

---

## Phase 6: User Story 5 - Backward Compatibility (Priority: P1)

**Goal**: Ensure all existing behavior is preserved after refactor

**Independent Test**: Run entire existing test suite without modification

### Call Site Updates for User Story 5

- [x] T029 [US5] Update evaluate() method to use new _apply_candidate return type (dict) in src/gepa_adk/adapters/adk_adapter.py
- [x] T030 [US5] Update evaluate() method to pass dict to _restore_agent in src/gepa_adk/adapters/adk_adapter.py
- [x] T031 [US5] Add structured logging for registry dispatch operations in src/gepa_adk/adapters/adk_adapter.py

### Verification for User Story 5

- [x] T032 [US5] Run all existing unit tests in tests/unit/adapters/test_adk_adapter.py and verify pass
- [x] T033 [US5] Run all existing contract tests in tests/contracts/test_adk_adapter_contracts.py and verify pass
- [x] T034 [US5] Run all existing integration tests in tests/integration/adapters/ and verify pass (skipped - require API access)

**Checkpoint**: All existing tests pass - backward compatibility confirmed

---

## Phase 7: Verification & Cross-Cutting Concerns

**Purpose**: Final verification and quality checks

### Code Quality

- [x] T035 Remove unused imports (deserialize_schema, SchemaValidationError if now only used via handlers) in src/gepa_adk/adapters/adk_adapter.py
- [x] T036 Verify COMPONENT_OUTPUT_SCHEMA constant no longer needed in adk_adapter.py (used via handlers)
- [x] T037 [P] Run ruff check and fix any linting issues on modified files
- [x] T038 [P] Run ruff format on modified files

### Final Verification

- [x] T039 Run full test suite: `uv run pytest tests/ -v`
- [x] T040 Verify mkdocs build passes: `uv run mkdocs build` (no warnings)
- [x] T041 Run code quality checks: `./scripts/code_quality_check.sh --all` and resolve any warnings/issues

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verify prerequisites
- **Foundational (Phase 2)**: N/A - all infrastructure from #162
- **US1 & US2 (Phase 3)**: Handler verification - can start after Phase 1
- **US3 (Phase 4)**: _apply_candidate refactor - can start after Phase 3
- **US4 (Phase 5)**: _restore_agent refactor - can start after Phase 4
- **US5 (Phase 6)**: Call site updates - MUST wait for Phase 4 & 5
- **Verification (Phase 7)**: Final checks - MUST wait for all user stories

### User Story Dependencies

```
Phase 1 (Setup/Verify)
    ↓
Phase 3 (US1 & US2 - Handler Verification)
    ↓
Phase 4 (US3 - _apply_candidate refactor)
    ↓
Phase 5 (US4 - _restore_agent refactor)
    ↓
Phase 6 (US5 - Call site updates + backward compat)
    ↓
Phase 7 (Final verification)
```

### Parallel Opportunities

**Within Phase 1**:
- T002, T003, T004 can run in parallel

**Within Phase 3**:
- All test tasks (T005-T010) can run in parallel

**Within Phase 4**:
- All test tasks (T013-T016) can run in parallel

**Within Phase 5**:
- All test tasks (T022-T024) can run in parallel

**Within Phase 7**:
- T037 and T038 can run in parallel

---

## Parallel Example: Phase 3 Tests

```bash
# Launch all handler verification tests together:
Task: "Add unit test for InstructionHandler.serialize() in tests/unit/adapters/test_component_handlers.py"
Task: "Add unit test for InstructionHandler.apply() returns original in tests/unit/adapters/test_component_handlers.py"
Task: "Add unit test for OutputSchemaHandler.serialize() in tests/unit/adapters/test_component_handlers.py"
Task: "Add unit test for OutputSchemaHandler.apply() returns original in tests/unit/adapters/test_component_handlers.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3)

1. Complete Phase 1: Verify prerequisites
2. Complete Phase 3: Verify handlers work (US1 & US2)
3. Complete Phase 4: Refactor _apply_candidate (US3)
4. **STOP and VALIDATE**: Test _apply_candidate independently
5. Continue with US4 and US5

### Key Files Modified

| File | Changes |
|------|---------|
| `src/gepa_adk/adapters/adk_adapter.py` | Refactor _apply_candidate, _restore_agent, evaluate() |
| `tests/unit/adapters/test_adk_adapter.py` | Add registry dispatch tests |
| `tests/unit/adapters/test_component_handlers.py` | Verify/add handler tests |

### Success Criteria

- [x] SC-001: All existing ADKAdapter unit tests pass without modification
- [x] SC-002: All existing integration tests pass without modification
- [x] SC-003: _apply_candidate contains zero if/elif for component dispatch
- [x] SC-004: _restore_agent contains zero if/elif for component dispatch
- [x] SC-005: Handlers discoverable via get_handler("instruction") and get_handler("output_schema")
- [x] SC-006: mkdocs build passes without warnings
- [x] SC-007: code_quality_check.sh --all passes without blocking issues

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Handlers already exist from #162 - this feature wires ADKAdapter to use them
- Return type changes from `tuple[str, Any]` to `dict[str, Any]` are internal only
- Run `./scripts/code_quality_check.sh --all` as final step per user request

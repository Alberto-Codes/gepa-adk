# Tasks: Wire ADK Reflection Agent into evolve() API

**Input**: Design documents from `/specs/021-adk-reflection-evolve/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included per constitution requirement (three-layer testing: contract, unit, integration)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root

---

## Phase 1: Setup (No Changes Needed)

**Purpose**: This feature requires no project setup - infrastructure already exists

This phase is empty because:
- Project structure already exists
- Dependencies already configured (google-adk, litellm, structlog)
- Linting and testing tools already configured

**Checkpoint**: Proceeding directly to implementation phases

---

## Phase 2: Foundational (No Changes Needed)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

This phase is empty because all foundational components exist:
- `create_adk_reflection_fn()` already implemented in `src/gepa_adk/engine/proposer.py`
- `AsyncReflectiveMutationProposer` already accepts `adk_reflection_fn` parameter
- `ReflectionFn` type alias already defined
- Session state management already implemented

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Custom ADK Reflection Agent (Priority: P1) MVP

**Goal**: Enable users to pass a custom ADK LlmAgent as reflection_agent to evolve() and have it used for instruction improvement via ADK Runner.

**Independent Test**: Call `evolve()` with a custom reflection agent and verify:
1. The reflection agent is invoked via ADK Runner
2. Session state contains `current_instruction` and `execution_feedback`
3. Reflection operations appear in ADK traces

### Tests for User Story 1

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [ ] T001 [P] [US1] Contract test verifying ADKAdapter with reflection_agent satisfies protocol in tests/contracts/test_adk_adapter_contract.py
- [ ] T002 [P] [US1] Unit test for ADKAdapter accepting reflection_agent in tests/unit/test_adk_adapter.py
- [ ] T003 [P] [US1] Unit test for evolve() passing reflection_agent to adapter in tests/unit/test_api.py
- [ ] T004 [P] [US1] Integration test for evolve() with real ADK reflection agent in tests/integration/test_adk_reflection.py

### Implementation for User Story 1

- [ ] T005 [US1] Add reflection_agent parameter to ADKAdapter.__init__() in src/gepa_adk/adapters/adk_adapter.py
- [ ] T006 [US1] Create adk_reflection_fn when reflection_agent provided in src/gepa_adk/adapters/adk_adapter.py
- [ ] T007 [US1] Pass adk_reflection_fn to AsyncReflectiveMutationProposer in src/gepa_adk/adapters/adk_adapter.py
- [ ] T008 [US1] Update evolve() to pass reflection_agent to ADKAdapter in src/gepa_adk/api.py
- [ ] T009 [US1] Remove "not yet implemented" warning log in src/gepa_adk/api.py
- [ ] T010 [US1] Add debug log when reflection_agent is configured in src/gepa_adk/api.py
- [ ] T011 [US1] Update ADKAdapter docstring with reflection_agent parameter in src/gepa_adk/adapters/adk_adapter.py

**Checkpoint**: User Story 1 complete - custom ADK reflection agent now functional

---

## Phase 4: User Story 2 - Default LiteLLM Reflection Behavior (Priority: P2)

**Goal**: Ensure backward compatibility - existing workflows without reflection_agent continue to work identically.

**Independent Test**: Call `evolve()` without reflection_agent and verify:
1. Default LiteLLM-based reflection is used
2. No warnings or deprecation messages logged
3. Behavior identical to before this feature

### Tests for User Story 2

- [ ] T012 [P] [US2] Unit test for default behavior (no reflection_agent) in tests/unit/test_api.py
- [ ] T013 [P] [US2] Unit test verifying no warning logged when reflection_agent omitted in tests/unit/test_api.py

### Implementation for User Story 2

- [ ] T014 [US2] Verify ADKAdapter creates default proposer when reflection_agent is None in src/gepa_adk/adapters/adk_adapter.py
- [ ] T015 [US2] Verify explicit None treated same as omitted parameter in src/gepa_adk/adapters/adk_adapter.py
- [ ] T016 [US2] Add test for proposer precedence (proposer param takes priority over reflection_agent) in tests/unit/test_adk_adapter.py

**Checkpoint**: User Story 2 complete - backward compatibility verified

---

## Phase 5: User Story 3 - Clear Error Handling (Priority: P3)

**Goal**: Provide clear error messages when invalid reflection_agent is provided.

**Independent Test**: Provide various invalid inputs as reflection_agent and verify appropriate TypeError messages.

### Tests for User Story 3

- [ ] T017 [P] [US3] Unit test for TypeError when reflection_agent is invalid type in tests/unit/test_adk_adapter.py
- [ ] T018 [P] [US3] Unit test for clear error message content in tests/unit/test_adk_adapter.py

### Implementation for User Story 3

- [ ] T019 [US3] Add type validation for reflection_agent in ADKAdapter.__init__() in src/gepa_adk/adapters/adk_adapter.py
- [ ] T020 [US3] Ensure error message includes expected type (LlmAgent) in src/gepa_adk/adapters/adk_adapter.py

### Edge Case Handling

- [ ] T021 [P] [US3] Unit test for reflection agent exception handling in tests/unit/test_adk_adapter.py
- [ ] T022 [US3] Handle reflection agent exception with EvolutionError wrapping in src/gepa_adk/adapters/adk_adapter.py
- [ ] T023 [P] [US3] Unit test for malformed response handling in tests/unit/test_adk_adapter.py
- [ ] T024 [US3] Validate reflection response is non-empty string in src/gepa_adk/adapters/adk_adapter.py

**Checkpoint**: User Story 3 complete - error handling and edge cases implemented

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation

- [ ] T025 [P] Run all tests to verify no regressions: `uv run pytest tests/`
- [ ] T026 [P] Run linting: `uv run ruff check src/gepa_adk/api.py src/gepa_adk/adapters/adk_adapter.py`
- [ ] T027 [P] Run type checking: `uv run ty check`
- [ ] T028 Validate quickstart.md examples work correctly
- [ ] T029 Update __init__.py exports if needed in src/gepa_adk/__init__.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Empty - no setup needed
- **Foundational (Phase 2)**: Empty - infrastructure exists
- **User Story 1 (Phase 3)**: Can start immediately - core feature
- **User Story 2 (Phase 4)**: Can start after US1 tests written (shares test file)
- **User Story 3 (Phase 5)**: Can start after US1 implementation (validation depends on parameter existing)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies - implements core wiring
- **User Story 2 (P2)**: No dependencies on US1 implementation, but shares test files
- **User Story 3 (P3)**: Depends on US1 T005 (parameter must exist to validate it)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation follows order: adapter changes → API changes → docstrings
- Story complete before moving to next priority

### Parallel Opportunities

- T001, T002, T003, T004: All US1 tests can run in parallel (different files)
- T012, T013: All US2 tests can run in parallel
- T017, T018, T021, T023: All US3 tests can run in parallel
- T025, T026, T027: All polish verification can run in parallel

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test verifying ADKAdapter with reflection_agent satisfies protocol in tests/contracts/test_adk_adapter_contract.py"
Task: "Unit test for ADKAdapter accepting reflection_agent in tests/unit/test_adk_adapter.py"
Task: "Unit test for evolve() passing reflection_agent to adapter in tests/unit/test_api.py"
Task: "Integration test for evolve() with real ADK reflection agent in tests/integration/test_adk_reflection.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Skip Phase 1 & 2 (no setup/foundational work needed)
2. Write US1 tests (T001-T004) - verify they fail
3. Implement US1 (T005-T011) - verify tests pass
4. **STOP and VALIDATE**: Test User Story 1 independently with real ADK agent
5. Deploy/demo if ready - users can now use custom reflection agents

### Incremental Delivery

1. Complete User Story 1 → Test independently → Custom reflection works
2. Add User Story 2 → Test independently → Backward compatibility verified
3. Add User Story 3 → Test independently → Error handling complete
4. Each story adds confidence without breaking previous stories

### Estimated Scope

- **Total Tasks**: 29
- **US1 Tasks**: 11 (core feature, includes contract test)
- **US2 Tasks**: 5 (backward compatibility)
- **US3 Tasks**: 8 (error handling + edge cases)
- **Polish Tasks**: 5 (verification)
- **Parallel Opportunities**: 15 tasks can run in parallel with others

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- This is a small feature (~50 lines of code changes)
- Most complexity is in testing, not implementation

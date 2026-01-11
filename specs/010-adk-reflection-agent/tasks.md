# Tasks: ADK-First Reflection Agent Support

**Input**: Design documents from `/specs/010-adk-reflection-agent/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Included per three-layer testing strategy (contract, unit, integration)

**Organization**: Tasks grouped by user story for independent implementation and testing

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Type definitions and shared contracts

- [X] T001 Add ReflectionFn type alias and SESSION_STATE_KEYS to src/gepa_adk/engine/proposer.py
- [X] T002 [P] Create reflection function contract module at tests/contracts/engine/test_reflection_fn_contract.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before user story implementation

⚠️ **CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add adk_reflection_fn parameter to AsyncReflectiveMutationProposer.__init__ in src/gepa_adk/engine/proposer.py
- [X] T004 Update __init__.py exports to include ReflectionFn type alias in src/gepa_adk/engine/__init__.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - ADK Agent Reflection (Priority: P1) 🎯 MVP

**Goal**: Enable users to configure ADK agents for reflection via `create_adk_reflection_fn()` factory

**Independent Test**: Configure an ADK LlmAgent with custom instruction and verify proposer uses it via Runner.run_async()

### Tests for User Story 1

> **TDD**: Write tests FIRST, ensure they FAIL before implementation

- [ ] T005 [P] [US1] Contract test for create_adk_reflection_fn signature in tests/contracts/engine/test_reflection_fn_contract.py
- [ ] T006 [P] [US1] Contract test for ReflectionFn callable protocol compliance in tests/contracts/engine/test_reflection_fn_contract.py
- [ ] T007 [P] [US1] Unit test for create_adk_reflection_fn with mocked ADK in tests/unit/engine/test_proposer.py
- [ ] T008 [P] [US1] Integration test for create_adk_reflection_fn with real ADK agent (include custom SessionService scenario) in tests/integration/engine/test_adk_reflection.py

### Implementation for User Story 1

- [ ] T009 [US1] Implement create_adk_reflection_fn factory function in src/gepa_adk/engine/proposer.py
- [ ] T010 [US1] Add Runner.run_async event extraction logic in create_adk_reflection_fn in src/gepa_adk/engine/proposer.py
- [ ] T011 [US1] Add structlog logging for reflection operations in src/gepa_adk/engine/proposer.py
- [ ] T012 [US1] Handle empty/None ADK response with fallback to empty string in src/gepa_adk/engine/proposer.py

**Checkpoint**: User Story 1 complete - users can create ADK reflection functions and use them directly

---

## Phase 4: User Story 2 - Context Passing to Reflection Agent (Priority: P2)

**Goal**: Reflection agent receives current_instruction and execution_feedback via session state

**Independent Test**: Verify session_state contains expected keys and values before Runner.run_async() is called

### Tests for User Story 2

- [ ] T013 [P] [US2] Unit test for session state initialization with current_instruction in tests/unit/engine/test_proposer.py
- [ ] T014 [P] [US2] Unit test for session state initialization with execution_feedback JSON in tests/unit/engine/test_proposer.py
- [ ] T015 [P] [US2] Integration test for context passing to ADK agent in tests/integration/engine/test_adk_reflection.py

### Implementation for User Story 2

- [ ] T016 [US2] Implement session creation with state dictionary in create_adk_reflection_fn in src/gepa_adk/engine/proposer.py
- [ ] T017 [US2] Add JSON serialization for execution_feedback in session state in src/gepa_adk/engine/proposer.py
- [ ] T018 [US2] Default to InMemorySessionService when session_service is None in src/gepa_adk/engine/proposer.py

**Checkpoint**: User Story 2 complete - ADK agents receive full context via session state

---

## Phase 5: User Story 3 - LiteLLM Fallback (Priority: P3)

**Goal**: Proposer falls back to litellm.acompletion() when no ADK reflection agent is configured

**Independent Test**: Create proposer without adk_reflection_fn and verify it uses litellm.acompletion()

### Tests for User Story 3

- [ ] T019 [P] [US3] Unit test for proposer with adk_reflection_fn=None uses LiteLLM in tests/unit/engine/test_proposer.py
- [ ] T020 [P] [US3] Unit test for proposer with adk_reflection_fn provided uses ADK in tests/unit/engine/test_proposer.py
- [ ] T021 [P] [US3] Contract test for backwards-compatible propose() signature in tests/contracts/engine/test_proposer_contracts.py

### Implementation for User Story 3

- [ ] T022 [US3] Add conditional branch in propose() to use adk_reflection_fn when provided in src/gepa_adk/engine/proposer.py
- [ ] T023 [US3] Ensure empty feedback early return behavior is preserved in src/gepa_adk/engine/proposer.py
- [ ] T024 [US3] Verify ADK exceptions propagate to caller (no try/except suppression) in src/gepa_adk/engine/proposer.py

**Checkpoint**: User Story 3 complete - existing LiteLLM workflows continue to work without modification

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, integration, and validation

- [ ] T025 [P] Update src/gepa_adk/engine/__init__.py to export create_adk_reflection_fn (extends T004 exports)
- [ ] T026 [P] Add Google-style docstrings to create_adk_reflection_fn in src/gepa_adk/engine/proposer.py
- [ ] T027 [P] Update src/gepa_adk/__init__.py with new public exports if needed
- [ ] T028 Run quickstart.md validation scenarios manually
- [ ] T029 Run uv run pytest -n auto to verify all tests pass
- [ ] T030 Run uv run ruff check --fix and uv run ruff format for code quality

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1, US2, US3 can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Can Start After | Dependencies |
|-------|-----------------|--------------|
| US1 (P1) | Phase 2 | None - core factory function |
| US2 (P2) | US1 complete | Depends on US1 - session state is part of factory function |
| US3 (P3) | Phase 2 | None - fallback logic in proposer (can parallel with US1/US2) |

**Note**: US1 and US2 are **sequential** (US2 builds on US1's factory function). Implement US1 → US2 in order. US3 is independent and can run in parallel with US1/US2 if staffed.

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Core implementation before edge case handling
3. Logging and error handling last

### Parallel Opportunities

```text
Phase 1: T001 and T002 can run in parallel
Phase 2: T003 and T004 must be sequential
Phase 3: T005, T006, T007, T008 can run in parallel (all tests)
Phase 4: T013, T014, T015 can run in parallel (all tests)
Phase 5: T019, T020, T021 can run in parallel (all tests)
Phase 6: T025, T026, T027 can run in parallel
```

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all User Story 1 tests together:
# T005: Contract test for create_adk_reflection_fn signature
# T006: Contract test for ReflectionFn callable protocol
# T007: Unit test for create_adk_reflection_fn with mocked ADK
# T008: Integration test with real ADK agent
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Complete Phase 1: Setup (type definitions)
2. Complete Phase 2: Foundational (proposer parameter)
3. Complete Phase 3: User Story 1 (factory function core)
4. Complete Phase 4: User Story 2 (context passing)
5. **STOP and VALIDATE**: Test ADK reflection works end-to-end
6. This is the MVP - users can use ADK reflection

### Full Feature Delivery

1. MVP above → ADK reflection functional
2. Add Phase 5: User Story 3 → Backwards compatibility verified
3. Add Phase 6: Polish → Production ready

### Task Count Summary

| Phase | Tasks | Parallel Tasks |
|-------|-------|----------------|
| Phase 1: Setup | 2 | 1 |
| Phase 2: Foundational | 2 | 0 |
| Phase 3: US1 | 8 | 4 |
| Phase 4: US2 | 6 | 3 |
| Phase 5: US3 | 6 | 3 |
| Phase 6: Polish | 6 | 3 |
| **Total** | **30** | **14** |

---

## Files Modified/Created

### Modified Files

- `src/gepa_adk/engine/proposer.py` - Add factory function, extend proposer
- `src/gepa_adk/engine/__init__.py` - Update exports
- `tests/unit/engine/test_proposer.py` - Add ADK reflection tests

### New Files

- `tests/contracts/engine/test_reflection_fn_contract.py` - Contract tests
- `tests/integration/engine/test_adk_reflection.py` - Integration tests

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently

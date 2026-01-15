# Tasks: AgentProvider Protocol

**Input**: Design documents from `/specs/029-agent-provider-protocol/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Contract tests are REQUIRED per constitution (ADR-005: Three-Layer Testing). Unit tests included for mock provider validation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root
- Protocol definition in `src/gepa_adk/ports/`
- Contract tests in `tests/contracts/`

---

## Phase 1: Setup

**Purpose**: Verify project structure and dependencies are ready

- [ ] T001 Verify existing ports/ structure in src/gepa_adk/ports/__init__.py
- [ ] T002 [P] Verify pytest and test structure exists in tests/contracts/

---

## Phase 2: Foundational (Protocol Definition)

**Purpose**: Define the AgentProvider protocol that ALL user stories depend on

**CRITICAL**: The protocol must be defined before any user story can be implemented or tested

- [ ] T003 Create AgentProvider protocol in src/gepa_adk/ports/agent_provider.py
  - Define `@runtime_checkable` Protocol class
  - Add `get_agent(name: str) -> LlmAgent` method signature (FR-002)
  - Add `save_instruction(name: str, instruction: str) -> None` method signature (FR-003)
  - Add `list_agents() -> list[str]` method signature (FR-004)
  - Use TYPE_CHECKING for LlmAgent import (ADR-000: no external imports in ports/)
  - Include comprehensive Google-style docstrings with Examples sections (FR-007)
- [ ] T004 Export AgentProvider from src/gepa_adk/ports/__init__.py

**Checkpoint**: Protocol defined - contract tests and user story implementation can now begin

---

## Phase 3: User Story 1 - Load Agent by Name (Priority: P1) MVP

**Goal**: Enable integrators to retrieve a configured agent by its unique name

**Independent Test**: Implement a mock provider, register an agent, call `get_agent("agent_name")`, verify it returns a properly configured agent instance

### Contract Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementing mock provider**

- [ ] T005 [P] [US1] Create test file tests/contracts/test_agent_provider_protocol.py with imports and test class structure
- [ ] T006 [P] [US1] Add test_agent_provider_protocol_is_runtime_checkable() in tests/contracts/test_agent_provider_protocol.py
- [ ] T007 [US1] Add test_get_agent_returns_llm_agent() in tests/contracts/test_agent_provider_protocol.py
- [ ] T008 [US1] Add test_get_agent_raises_for_nonexistent() in tests/contracts/test_agent_provider_protocol.py
- [ ] T009 [US1] Add test_get_agent_handles_multiple_agents() in tests/contracts/test_agent_provider_protocol.py

### Implementation for User Story 1

- [ ] T010 [US1] Create InMemoryAgentProvider test fixture in tests/contracts/test_agent_provider_protocol.py
  - Implement `get_agent()` method that returns LlmAgent from internal dict
  - Implement `save_instruction()` stub (for protocol compliance)
  - Implement `list_agents()` stub (for protocol compliance)
  - Verify fixture satisfies `isinstance(provider, AgentProvider)`
- [ ] T011 [US1] Run contract tests and verify all US1 tests pass

**Checkpoint**: User Story 1 complete - agents can be loaded by name

---

## Phase 4: User Story 2 - Save Evolved Instruction (Priority: P2)

**Goal**: Enable integrators to persist evolved instructions back to storage

**Independent Test**: Load an agent, call `save_instruction("agent_name", "new instruction")`, then call `get_agent()` again and verify the instruction was updated

### Contract Tests for User Story 2

- [ ] T012 [P] [US2] Add test_save_instruction_persists() in tests/contracts/test_agent_provider_protocol.py
- [ ] T013 [P] [US2] Add test_save_instruction_raises_for_nonexistent() in tests/contracts/test_agent_provider_protocol.py
- [ ] T014 [US2] Add test_save_instruction_visible_in_subsequent_get() in tests/contracts/test_agent_provider_protocol.py

### Implementation for User Story 2

- [ ] T015 [US2] Update InMemoryAgentProvider.save_instruction() in tests/contracts/test_agent_provider_protocol.py
  - Update agent instruction in internal dict
  - Raise KeyError for non-existent agents
- [ ] T016 [US2] Run contract tests and verify all US2 tests pass

**Checkpoint**: User Story 2 complete - evolved instructions can be persisted

---

## Phase 5: User Story 3 - List Available Agents (Priority: P3)

**Goal**: Enable integrators to discover what agents are available in a provider

**Independent Test**: Register multiple agents with a provider, call `list_agents()`, verify all registered names are returned

### Contract Tests for User Story 3

- [ ] T017 [P] [US3] Add test_list_agents_returns_list() in tests/contracts/test_agent_provider_protocol.py
- [ ] T018 [P] [US3] Add test_list_agents_empty_when_no_agents() in tests/contracts/test_agent_provider_protocol.py
- [ ] T019 [US3] Add test_list_agents_contains_all_registered() in tests/contracts/test_agent_provider_protocol.py

### Implementation for User Story 3

- [ ] T020 [US3] Update InMemoryAgentProvider.list_agents() in tests/contracts/test_agent_provider_protocol.py
  - Return list of keys from internal agent dict
- [ ] T021 [US3] Run contract tests and verify all US3 tests pass

**Checkpoint**: User Story 3 complete - available agents can be discovered

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect the overall quality

- [ ] T022 [P] Add edge case tests in tests/contracts/test_agent_provider_protocol.py
  - test_protocol_requires_all_three_methods()
  - test_get_agent_with_empty_name() (edge case)
- [ ] T023 Run full test suite with `pytest tests/contracts/test_agent_provider_protocol.py -v`
- [ ] T024 Run ruff check on new files: `ruff check src/gepa_adk/ports/agent_provider.py`
- [ ] T025 Run type checker on new files: `ty check src/gepa_adk/ports/agent_provider.py`
- [ ] T026 Validate quickstart.md examples work with the protocol

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can proceed sequentially in priority order (P1 → P2 → P3)
  - All user stories extend the same test file and fixture
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after US1 (shares fixture) - Independently testable
- **User Story 3 (P3)**: Can start after US1 (shares fixture) - Independently testable

### Within Each User Story

- Contract tests MUST be written and FAIL before implementation
- Fixture implementation satisfies tests
- Verify tests pass before moving to next story

### Parallel Opportunities

- T001, T002: Can run in parallel (verification only)
- T005, T006: Can run in parallel (test file setup)
- T012, T013: Can run in parallel (different tests)
- T017, T018: Can run in parallel (different tests)
- T022, T024, T025: Can run in parallel (different concerns)

---

## Parallel Example: User Story 1 Tests

```bash
# Launch US1 tests in parallel:
Task: "T005 [P] [US1] Create test file tests/contracts/test_agent_provider_protocol.py"
Task: "T006 [P] [US1] Add test_agent_provider_protocol_is_runtime_checkable()"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational Protocol (T003-T004)
3. Complete Phase 3: User Story 1 (T005-T011)
4. **STOP and VALIDATE**: Run `pytest tests/contracts/test_agent_provider_protocol.py -v`
5. Protocol is usable for loading agents - MVP complete!

### Incremental Delivery

1. Setup + Foundational → Protocol defined
2. Add User Story 1 → Test independently → Agents can be loaded (MVP!)
3. Add User Story 2 → Test independently → Instructions can be persisted
4. Add User Story 3 → Test independently → Agents can be discovered
5. Polish → Full test coverage, documentation validated

### Single Developer Approach

Since this is a focused protocol feature:
1. Complete all phases sequentially
2. Each phase builds on previous
3. Tests written before implementation
4. Total estimated tasks: 26

---

## Notes

- [P] tasks = different files or independent test functions, no dependencies
- [Story] label maps task to specific user story for traceability
- All protocol code in ports/ - NO external imports except via TYPE_CHECKING
- InMemoryAgentProvider is a test fixture only, not exported publicly
- Contract tests verify protocol compliance per ADR-005
- Commit after each phase completion

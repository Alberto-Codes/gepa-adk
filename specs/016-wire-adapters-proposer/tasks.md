# Tasks: Wire Adapters to AsyncReflectiveMutationProposer

**Input**: Design documents from `/specs/016-wire-adapters-proposer/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Unit tests included per Constitution Principle IV (Three-Layer Testing).

**Organization**: Tasks grouped by user story. US1 and US2 are both P1 priority and can be implemented in parallel after foundational phase.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3, US4 (maps to spec.md user stories)
- Exact file paths included

---

## Phase 1: Setup

**Purpose**: No new project setup needed - modifying existing codebase

- [ ] T001 Verify existing tests pass with `uv run pytest -n auto`
- [ ] T002 [P] Review AsyncReflectiveMutationProposer interface in `src/gepa_adk/engine/proposer.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared test infrastructure for all user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Create mock proposer fixture in `tests/unit/adapters/conftest.py`
- [ ] T004 [P] Verify import path `from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer` works

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - ADKAdapter Delegates to Proposer (Priority: P1) 🎯 MVP

**Goal**: ADKAdapter generates actual instruction mutations via LLM instead of returning stub values

**Independent Test**: Create ADKAdapter with mock proposer, call `propose_new_texts()`, verify delegation occurs

### Unit Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T005 [P] [US1] Write test `test_constructor_accepts_proposer_parameter` in `tests/unit/adapters/test_adk_adapter.py`
- [ ] T006 [P] [US1] Write test `test_constructor_creates_default_proposer` in `tests/unit/adapters/test_adk_adapter.py`
- [ ] T007 [P] [US1] Write test `test_propose_new_texts_delegates_to_proposer` in `tests/unit/adapters/test_adk_adapter.py`

### Implementation for User Story 1

- [ ] T008 [US1] Add `proposer` parameter to ADKAdapter `__init__` in `src/gepa_adk/adapters/adk_adapter.py`
- [ ] T009 [US1] Add import for AsyncReflectiveMutationProposer in `src/gepa_adk/adapters/adk_adapter.py`
- [ ] T010 [US1] Initialize `self._proposer` with default or injected proposer in `src/gepa_adk/adapters/adk_adapter.py`
- [ ] T011 [US1] Update `__init__` docstring with proposer parameter documentation in `src/gepa_adk/adapters/adk_adapter.py`
- [ ] T012 [US1] Replace stub `propose_new_texts()` with delegation to `self._proposer.propose()` in `src/gepa_adk/adapters/adk_adapter.py`
- [ ] T013 [US1] Add logging for delegation in `propose_new_texts()` in `src/gepa_adk/adapters/adk_adapter.py`
- [ ] T014 [US1] Verify US1 tests pass with `uv run pytest tests/unit/adapters/test_adk_adapter.py -k proposer`

**Checkpoint**: ADKAdapter now delegates to proposer - testable independently

---

## Phase 4: User Story 2 - MultiAgentAdapter Delegates to Proposer (Priority: P1)

**Goal**: MultiAgentAdapter generates actual instruction mutations via LLM for all agents instead of heuristic selection

**Independent Test**: Create MultiAgentAdapter with mock proposer, call `propose_new_texts()`, verify delegation occurs

### Unit Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T015 [P] [US2] Write test `test_constructor_accepts_proposer_parameter` in `tests/unit/adapters/test_multi_agent_adapter.py`
- [ ] T016 [P] [US2] Write test `test_constructor_creates_default_proposer` in `tests/unit/adapters/test_multi_agent_adapter.py`
- [ ] T017 [P] [US2] Write test `test_propose_new_texts_delegates_to_proposer` in `tests/unit/adapters/test_multi_agent_adapter.py`

### Implementation for User Story 2

- [ ] T018 [US2] Add `proposer` parameter to MultiAgentAdapter `__init__` in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T019 [US2] Add import for AsyncReflectiveMutationProposer in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T020 [US2] Initialize `self._proposer` with default or injected proposer in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T021 [US2] Update `__init__` docstring with proposer parameter documentation in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T022 [US2] Replace heuristic `propose_new_texts()` with delegation to `self._proposer.propose()` in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T023 [US2] Add logging for delegation in `propose_new_texts()` in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T024 [US2] Verify US2 tests pass with `uv run pytest tests/unit/adapters/test_multi_agent_adapter.py -k proposer`

**Checkpoint**: MultiAgentAdapter now delegates to proposer - testable independently

---

## Phase 5: User Story 3 - Custom Proposer Injection (Priority: P2)

**Goal**: Developers can inject custom proposers with different model/temperature configurations

**Independent Test**: Create adapter with custom proposer instance, verify custom proposer is used instead of default

### Unit Tests for User Story 3

- [ ] T025 [P] [US3] Write test `test_custom_proposer_is_used` for ADKAdapter in `tests/unit/adapters/test_adk_adapter.py`
- [ ] T026 [P] [US3] Write test `test_custom_proposer_is_used` for MultiAgentAdapter in `tests/unit/adapters/test_multi_agent_adapter.py`

### Implementation for User Story 3

- [ ] T027 [US3] Verify custom proposer injection works in ADKAdapter (implementation done in US1)
- [ ] T028 [US3] Verify custom proposer injection works in MultiAgentAdapter (implementation done in US2)
- [ ] T029 [US3] Verify US3 tests pass with `uv run pytest -k custom_proposer`

**Checkpoint**: Custom proposer injection works for both adapters

---

## Phase 6: User Story 4 - Graceful Fallback on Empty Dataset (Priority: P2)

**Goal**: Adapters handle empty reflective datasets gracefully, returning unchanged candidate values

**Independent Test**: Call `propose_new_texts()` with empty dataset, verify unchanged values returned without errors

### Unit Tests for User Story 4

- [ ] T030 [P] [US4] Write test `test_propose_new_texts_fallback_on_none` for ADKAdapter in `tests/unit/adapters/test_adk_adapter.py`
- [ ] T031 [P] [US4] Write test `test_propose_new_texts_fallback_on_none` for MultiAgentAdapter in `tests/unit/adapters/test_multi_agent_adapter.py`
- [ ] T032 [P] [US4] Write test `test_propose_new_texts_merges_partial_result` for ADKAdapter in `tests/unit/adapters/test_adk_adapter.py`
- [ ] T033 [P] [US4] Write test `test_propose_new_texts_merges_partial_result` for MultiAgentAdapter in `tests/unit/adapters/test_multi_agent_adapter.py`

### Implementation for User Story 4

- [ ] T034 [US4] Add None-handling logic in ADKAdapter `propose_new_texts()` in `src/gepa_adk/adapters/adk_adapter.py`
- [ ] T035 [US4] Add None-handling logic in MultiAgentAdapter `propose_new_texts()` in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T036 [US4] Add fallback logging per FR-008 in both adapters
- [ ] T037 [US4] Verify US4 tests pass with `uv run pytest -k fallback`

**Checkpoint**: All edge cases handled gracefully

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [ ] T038 Run full test suite `uv run pytest -n auto` to verify backward compatibility (FR-010)
- [ ] T039 [P] Run linting `uv run ruff check --fix`
- [ ] T040 [P] Run type checking `uv run ty check`
- [ ] T041 [P] Verify existing contract tests still pass in `tests/contracts/`
- [ ] T042 Run quickstart.md validation scenarios manually
- [ ] T043 Update `src/gepa_adk/adapters/__init__.py` exports if needed

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ─────────────────────────────────────────────────┐
                                                                 │
Phase 2: Foundational ──────────────────────────────────────────┤
                                                                 │
    ┌────────────────────────────────────────────────────────────┤
    │                                                            │
    ▼                                                            ▼
Phase 3: US1 (ADKAdapter)                    Phase 4: US2 (MultiAgentAdapter)
    │                                                            │
    └────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
                   Phase 5: US3 (Custom Injection)
                             │
                             ▼
                   Phase 6: US4 (Fallback Handling)
                             │
                             ▼
                   Phase 7: Polish
```

### Parallel Opportunities

**Within Phase 2 (Foundational)**:
- T003 and T004 can run in parallel

**Within Phase 3 (US1) - Tests**:
- T005, T006, T007 can run in parallel (same file but different test functions)

**Within Phase 4 (US2) - Tests**:
- T015, T016, T017 can run in parallel

**Between Phase 3 and Phase 4**:
- US1 and US2 can be implemented in parallel (different files)

**Within Phase 5 (US3) - Tests**:
- T025 and T026 can run in parallel (different files)

**Within Phase 6 (US4) - Tests**:
- T030, T031, T032, T033 can run in parallel

**Within Phase 7 (Polish)**:
- T039, T040, T041 can run in parallel

---

## Parallel Example: US1 + US2 Together

```bash
# After Phase 2 complete, launch US1 and US2 tests in parallel:
# Terminal 1:
uv run pytest tests/unit/adapters/test_adk_adapter.py -k proposer

# Terminal 2:
uv run pytest tests/unit/adapters/test_multi_agent_adapter.py -k proposer
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (verify tests pass)
2. Complete Phase 2: Foundational (mock proposer fixture)
3. Complete Phase 3: US1 (ADKAdapter delegation)
4. **STOP and VALIDATE**: Test ADKAdapter independently
5. Can deploy/demo ADKAdapter working with proposer

### Full Feature Delivery

1. Complete Setup + Foundational → Foundation ready
2. US1 + US2 in parallel → Both adapters delegate to proposer
3. US3 → Custom injection verified
4. US4 → Edge cases handled
5. Polish → All tests pass, linting clean

---

## Task Count Summary

| Phase | Task Count | Parallel Tasks |
|-------|------------|----------------|
| Setup | 2 | 1 |
| Foundational | 2 | 1 |
| US1 (P1) | 10 | 3 |
| US2 (P1) | 10 | 3 |
| US3 (P2) | 5 | 2 |
| US4 (P2) | 8 | 4 |
| Polish | 6 | 3 |
| **Total** | **43** | **17** |

---

## Notes

- US1 and US2 are both P1 priority and can run in parallel since they modify different files
- US3 and US4 build on top of US1/US2 but add test coverage and edge case handling
- Existing contract tests in `tests/contracts/` should continue to pass (FR-010)
- Mock proposer fixture shared across all adapter tests to avoid duplication

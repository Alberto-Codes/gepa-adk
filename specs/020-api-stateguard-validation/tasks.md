# Tasks: API StateGuard Validation

**Input**: Design documents from `/specs/020-api-stateguard-validation/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Tests are REQUIRED per Constitution (Three-Layer Testing principle)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing code and prepare for wiring

- [X] T001 Verify existing StateGuard implementation works with `uv run pytest tests/unit/test_state_guard.py -v`
- [X] T002 [P] Update type annotation for `state_guard` parameter from `Any | None` to `StateGuard | None` in src/gepa_adk/api.py
- [X] T003 [P] Add import for StateGuard in src/gepa_adk/api.py (from gepa_adk.utils import StateGuard)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create test file structure

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Create test file tests/unit/test_api_state_guard.py with imports and fixtures
- [X] T005 [P] Create helper function `_apply_state_guard_validation()` in src/gepa_adk/api.py for reuse across functions

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Automatic Token Repair During Evolution (Priority: P1) 🎯 MVP

**Goal**: Wire StateGuard into `evolve()` to repair missing tokens in evolved instructions

**Independent Test**: Call `evolve()` with `state_guard=StateGuard(required_tokens=["{user_id}"])` and verify missing tokens are repaired

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US1] Unit test: StateGuard repairs missing token in tests/unit/test_api_state_guard.py::test_evolve_state_guard_repairs_missing_token
- [X] T007 [P] [US1] Unit test: StateGuard no-op when state_guard=None in tests/unit/test_api_state_guard.py::test_evolve_no_state_guard_returns_unchanged
- [X] T008 [P] [US1] Unit test: StateGuard respects repair_missing=False in tests/unit/test_api_state_guard.py::test_evolve_state_guard_repair_disabled
- [X] T008a [P] [US1] Unit test: StateGuard instance is not mutated after validation in tests/unit/test_api_state_guard.py::test_evolve_state_guard_not_mutated
- [X] T008b [P] [US1] Unit test: Identical evolved instruction produces no changes in tests/unit/test_api_state_guard.py::test_evolve_state_guard_unchanged_instruction

### Implementation for User Story 1

- [X] T009 [US1] Replace TODO block in evolve() function with StateGuard validation in src/gepa_adk/api.py (lines 837-843)
- [X] T010 [US1] Add structured logging when StateGuard modifies instruction in src/gepa_adk/api.py
- [X] T011 [US1] Add structured logging when StateGuard produces no changes in src/gepa_adk/api.py
- [X] T012 [US1] Verify evolve_sync() automatically inherits StateGuard behavior (passes state_guard to evolve)

**Checkpoint**: User Story 1 complete - `evolve()` and `evolve_sync()` support StateGuard

---

## Phase 4: User Story 2 - Unauthorized Token Escaping (Priority: P2)

**Goal**: Verify token escaping works through the API (StateGuard already implements this)

**Independent Test**: Call `evolve()` with state_guard and verify unauthorized new tokens are escaped with double braces

### Tests for User Story 2

- [X] T013 [P] [US2] Unit test: StateGuard escapes unauthorized tokens in tests/unit/test_api_state_guard.py::test_evolve_state_guard_escapes_unauthorized
- [X] T014 [P] [US2] Unit test: StateGuard respects escape_unauthorized=False in tests/unit/test_api_state_guard.py::test_evolve_state_guard_escape_disabled
- [X] T015 [P] [US2] Unit test: Authorized tokens (in required_tokens) are NOT escaped in tests/unit/test_api_state_guard.py::test_evolve_state_guard_authorized_token_not_escaped

### Implementation for User Story 2

- [X] T016 [US2] Verify escaping behavior works through API (no new code needed - covered by US1 implementation)

**Checkpoint**: User Story 2 complete - token escaping verified through API

---

## Phase 5: User Story 3 - StateGuard in Multi-Agent Evolution (Priority: P2)

**Goal**: Wire StateGuard into `evolve_group()` to protect all agents' instructions

**Independent Test**: Call `evolve_group()` with state_guard and verify each agent's evolved instruction is validated

### Tests for User Story 3

- [X] T017 [P] [US3] Unit test: evolve_group applies StateGuard to each agent in tests/unit/test_api_state_guard.py::test_evolve_group_state_guard_each_agent
- [X] T018 [P] [US3] Unit test: evolve_group uses each agent's original instruction as reference in tests/unit/test_api_state_guard.py::test_evolve_group_state_guard_per_agent_original

### Implementation for User Story 3

- [X] T019 [US3] Add `state_guard: StateGuard | None = None` parameter to evolve_group() in src/gepa_adk/api.py
- [X] T020 [US3] Capture original instructions dict for all agents at evolve_group() entry
- [X] T021 [US3] Apply StateGuard validation to evolved_instructions dict before returning MultiAgentEvolutionResult
- [X] T022 [US3] Add structured logging for multi-agent StateGuard validation

**Checkpoint**: User Story 3 complete - `evolve_group()` supports StateGuard

---

## Phase 6: User Story 4 - StateGuard in Workflow Evolution (Priority: P3)

**Goal**: Wire StateGuard into `evolve_workflow()` to protect workflow agents' instructions

**Independent Test**: Call `evolve_workflow()` with state_guard and verify internal LlmAgents' instructions are validated

### Tests for User Story 4

- [X] T023 [P] [US4] Unit test: evolve_workflow applies StateGuard to internal agents in tests/unit/test_api_state_guard.py::test_evolve_workflow_state_guard

### Implementation for User Story 4

- [X] T024 [US4] Add `state_guard: StateGuard | None = None` parameter to evolve_workflow() in src/gepa_adk/api.py
- [X] T025 [US4] Pass state_guard parameter to evolve_group() call within evolve_workflow()

**Checkpoint**: User Story 4 complete - `evolve_workflow()` supports StateGuard

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [X] T026 [P] Run full test suite: `uv run pytest -n auto`
- [X] T027 [P] Run type check: `uv run ty check` (warnings remain for unused `type: ignore` in tests)
- [X] T028 [P] Run linting: `uv run ruff check --fix`
- [X] T029 [P] Verify existing API tests still pass unchanged
- [X] T030 Validate quickstart.md examples work correctly (StateGuard integration verified through tests)
- [X] T031 Update docstrings for modified functions (state_guard parameter docs)

---

## Phase 8: Alignment & Best Practices

**Purpose**: Align with spec/ADR expectations and public API patterns

- [X] T032 [P] Use public re-export for StateGuard imports in src/gepa_adk/api.py and tests/unit/test_api_state_guard.py
- [X] T033 [P] Reuse captured original_instruction when building initial_candidate in src/gepa_adk/api.py
- [X] T034 [US1/US2] Enrich StateGuard logging to indicate whether tokens were repaired vs escaped (FR-005)
- [ ] T035 [P] Clean up ty warnings from unused `type: ignore` in tests/unit/adapters/test_adk_adapter.py and tests/unit/test_adk_adapter_metadata.py

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1: Setup ──────────────────┐
                                 ▼
Phase 2: Foundational ───────────┤
                                 ▼
                    ┌────────────┴────────────┐
                    ▼                         ▼
Phase 3: US1 (P1) ─────────► Phase 4: US2 (P2)
        │                           │
        ▼                           ▼
Phase 5: US3 (P2) ──────────────────┤
        │                           │
        ▼                           ▼
Phase 6: US4 (P3) ──────────────────┤
                                    │
                                    ▼
                        Phase 7: Polish
```

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational - Core implementation 🎯 MVP
- **User Story 2 (P2)**: Depends on US1 - Verifies escaping behavior (no new code, tests only)
- **User Story 3 (P2)**: Depends on Foundational only - **Can run parallel with US1** (different functions)
- **User Story 4 (P3)**: Depends on US3 - evolve_workflow calls evolve_group

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Implementation after tests
- Logging after core implementation
- Checkpoint validation before moving to next story

### Parallel Opportunities

**Setup Phase:**
```bash
# T002 and T003 can run in parallel:
T002: Update type annotation in api.py
T003: Add import for StateGuard
```

**Foundational Phase:**
```bash
# T004 and T005 can run in parallel:
T004: Create test file
T005: Create helper function
```

**User Story 1 Tests:**
```bash
# T006, T007, T008 can run in parallel:
T006: test_evolve_state_guard_repairs_missing_token
T007: test_evolve_no_state_guard_returns_unchanged
T008: test_evolve_state_guard_repair_disabled
```

**User Story 2 Tests:**
```bash
# T013, T014, T015 can run in parallel:
T013: test_evolve_state_guard_escapes_unauthorized
T014: test_evolve_state_guard_escape_disabled
T015: test_evolve_state_guard_authorized_token_not_escaped
```

**Polish Phase:**
```bash
# T026, T027, T028, T029 can run in parallel:
T026: Run pytest
T027: Run ty check
T028: Run ruff
T029: Verify existing tests
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T005)
3. Complete Phase 3: User Story 1 (T006-T012)
4. **STOP and VALIDATE**: Test `evolve()` and `evolve_sync()` with StateGuard
5. If only basic protection needed, MVP is complete

### Full Implementation

1. Complete Setup + Foundational
2. User Story 1 → Core API protection (MVP)
3. User Story 2 → Verify escaping (low effort)
4. User Story 3 → Multi-agent protection (new parameter)
5. User Story 4 → Workflow protection (passes through to evolve_group)
6. Polish → Final validation

---

## Task Summary

| Phase | Task Count | Parallel Opportunities |
|-------|------------|------------------------|
| Setup | 3 | T002, T003 |
| Foundational | 2 | T004, T005 |
| US1 (P1) | 9 | T006, T007, T008, T008a, T008b |
| US2 (P2) | 4 | T013, T014, T015 |
| US3 (P2) | 6 | T017, T018 |
| US4 (P3) | 3 | T023 |
| Polish | 6 | T026, T027, T028, T029 |
| **Total** | **33** | |

---

## Test Case Coverage Mapping

| Contract Test Case | Covered By Task |
|--------------------|------------------|
| TC-001: Repairs missing token | T006 |
| TC-002: Escapes unauthorized token | T013 |
| TC-003: No-op when tokens preserved | T008b |
| TC-004: StateGuard disabled (None) | T007 |
| TC-005: Multi-agent validation | T017, T018 |
| TC-006: repair_missing=False | T008 |
| TC-007: escape_unauthorized=False | T014 |

---

## Notes

- StateGuard class is already fully implemented and tested (spec 013, 015)
- `evolve_sync()` automatically gets StateGuard support (wraps `evolve()`)
- `evolve_workflow()` delegates to `evolve_group()`, so only needs to pass state_guard through
- All test cases from contracts/api-state-guard.md should be covered by unit tests
- **Contract tests not required**: This feature wires an existing utility (StateGuard) into the API. No new protocols are defined, so tests/contracts/ layer is not applicable per ADR-005 (contract tests verify protocol compliance).

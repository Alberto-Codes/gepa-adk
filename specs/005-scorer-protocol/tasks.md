# Tasks: Scorer Protocol

**Input**: Design documents from `/specs/005-scorer-protocol/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Contract tests are included as per constitution ADR-005 (Three-Layer Testing) and plan.md test strategy.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root (hexagonal architecture)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify project structure and test infrastructure is ready

- [X] T001 Verify tests/contracts/ directory exists and create if missing
- [X] T002 Verify pytest and pytest-asyncio are available in dev dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core protocol that MUST be complete before user story validation

**⚠️ CRITICAL**: No user story validation can occur until the protocol exists

- [X] T003 Create Scorer protocol in src/gepa_adk/ports/scorer.py with @runtime_checkable decorator
- [X] T004 Add score() method signature with input_text, output, expected parameters per contracts/scorer-protocol.md
- [X] T005 Add async_score() method signature with identical parameters per contracts/scorer-protocol.md
- [X] T006 Add comprehensive Google-style docstrings with Examples sections per ADR-010
- [X] T007 Export Scorer from src/gepa_adk/ports/__init__.py

**Checkpoint**: Protocol defined - user story contract tests can now validate it

---

## Phase 3: User Story 1 - Score Agent Output with Custom Logic (Priority: P1) 🎯 MVP

**Goal**: Developers can implement custom scorers by following the protocol

**Independent Test**: Implement a simple FixedScorer that returns a fixed score and verify isinstance(scorer, Scorer) returns True

### Contract Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation is validated**

- [X] T008 [P] [US1] Create test file tests/contracts/test_scorer_protocol.py with pytest imports
- [X] T009 [P] [US1] Add test_scorer_protocol_is_runtime_checkable() to verify @runtime_checkable works
- [X] T010 [P] [US1] Add test_fixed_scorer_satisfies_protocol() with minimal FixedScorer implementation
- [X] T011 [P] [US1] Add test_score_returns_tuple_float_dict() to verify return type contract
- [X] T012 [P] [US1] Add test_score_with_metadata() to verify metadata dict is preserved (FR-007)
- [X] T013 [P] [US1] Add test_boundary_scores() to verify 0.0 and 1.0 are valid (edge case)
- [X] T014 [P] [US1] Add test_metadata_accepts_any_dict() to verify dict with various types is accepted (protocol doesn't enforce serializability)

### Validation for User Story 1

- [X] T015 [US1] Run pytest tests/contracts/test_scorer_protocol.py and verify all US1 tests pass
- [X] T016 [US1] Verify SC-001: FixedScorer implementation works as custom scorer
- [X] T017 [US1] Verify SC-004: isinstance() checks work at runtime

**Checkpoint**: User Story 1 complete - developers can implement custom sync scorers

---

## Phase 4: User Story 2 - Async Scoring for I/O-Bound Operations (Priority: P2)

**Goal**: Developers can use async_score() for LLM/API-based scoring without blocking

**Independent Test**: Implement an AsyncDelayScorer that simulates API call delay and verify concurrent execution

### Contract Tests for User Story 2

- [X] T018 [P] [US2] Add test_async_score_returns_same_format() to verify tuple[float, dict] return
- [X] T019 [P] [US2] Add test_async_score_is_awaitable() to verify method is a coroutine
- [X] T020 [P] [US2] Add test_concurrent_async_scoring() to verify multiple async_score calls can run in parallel
- [X] T021 [P] [US2] Add test_protocol_requires_both_methods() to verify class with only score() does not satisfy Scorer protocol

### Validation for User Story 2

- [X] T022 [US2] Run pytest tests/contracts/test_scorer_protocol.py and verify all US2 tests pass
- [X] T023 [US2] Verify SC-003: Async scoring enables concurrent evaluation without blocking

**Checkpoint**: User Story 2 complete - async scoring works for I/O-bound operations

---

## Phase 5: User Story 3 - Scoring Without Expected Output (Priority: P3)

**Goal**: Developers can score open-ended tasks where expected=None

**Independent Test**: Call score() with expected=None and verify a valid score is returned

### Contract Tests for User Story 3

- [X] T024 [P] [US3] Add test_score_with_none_expected() to verify optional expected handling (FR-005)
- [X] T025 [P] [US3] Add test_async_score_with_none_expected() to verify async method also handles None

### Validation for User Story 3

- [X] T026 [US3] Run pytest tests/contracts/test_scorer_protocol.py and verify all US3 tests pass
- [X] T027 [US3] Verify spec acceptance scenario: scorer returns valid score when expected=None

**Checkpoint**: User Story 3 complete - open-ended scoring scenarios supported

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [X] T028 Run full test suite: pytest tests/contracts/test_scorer_protocol.py -v
- [X] T029 Verify ruff check passes on src/gepa_adk/ports/scorer.py
- [X] T030 Verify all 8 functional requirements (FR-001 through FR-008) are satisfied
- [X] T031 Run quickstart.md examples mentally or in REPL to validate documentation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can proceed sequentially in priority order (P1 → P2 → P3)
  - Tests in each story can run in parallel
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - No dependencies on US1/US2

### Within Each User Story

- Tests written FIRST, then validation
- All tests within a story are parallelizable [P]
- Validation depends on tests passing

### Parallel Opportunities

- All tests within a user story marked [P] can run in parallel
- Different user stories can be worked on in parallel after Foundational phase
- T008-T014 can all run in parallel (US1 tests)
- T018-T021 can all run in parallel (US2 tests)
- T024-T025 can all run in parallel (US3 tests)

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all tests for User Story 1 together:
Task: "Create test file tests/contracts/test_scorer_protocol.py"
Task: "Add test_scorer_protocol_is_runtime_checkable()"
Task: "Add test_fixed_scorer_satisfies_protocol()"
Task: "Add test_score_returns_tuple_float_dict()"
Task: "Add test_score_with_metadata()"
Task: "Add test_boundary_scores()"
Task: "Add test_metadata_accepts_any_dict()"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - creates the protocol)
3. Complete Phase 3: User Story 1 (core scoring capability)
4. **STOP and VALIDATE**: Run contract tests, verify isinstance() works
5. Protocol is usable for basic scoring scenarios

### Incremental Delivery

1. Complete Setup + Foundational → Protocol exists
2. Add User Story 1 → Test independently → Sync scoring works (MVP!)
3. Add User Story 2 → Test independently → Async scoring works
4. Add User Story 3 → Test independently → Open-ended scoring works
5. Each story adds capability without breaking previous stories

---

## Success Criteria Mapping

| Success Criterion | User Story | Verification Task |
|-------------------|------------|-------------------|
| SC-001: Custom scorers work | US1 | T016 |
| SC-002: Scorers are interchangeable | All | T030 (FR check) |
| SC-003: Async concurrent evaluation | US2 | T023 |
| SC-004: Runtime isinstance() checks | US1 | T017 |

---

## Notes

- [P] tasks = different test functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable via its contract tests
- Foundational phase creates the protocol; user stories validate it
- This feature is small (~140 lines total) but follows constitution testing requirements
- Commit after each phase or logical group of tests

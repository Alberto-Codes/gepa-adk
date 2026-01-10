# Tasks: CriticScorer

**Input**: Design documents from `/specs/009-critic-scorer/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included per three-layer testing strategy (ADR-005) - contract, unit, integration tests.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/gepa_adk/`
- **Tests**: `tests/contracts/`, `tests/unit/`, `tests/integration/`

---

## Phase 1: Setup

**Purpose**: Exception hierarchy and Pydantic schema setup

- [ ] T001 Add ScoringError exception hierarchy to src/gepa_adk/domain/exceptions.py
- [ ] T002 [P] Create CriticOutput Pydantic schema in src/gepa_adk/adapters/critic_scorer.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core CriticScorer class structure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Create CriticScorer class skeleton with constructor in src/gepa_adk/adapters/critic_scorer.py
- [ ] T004 Implement `_format_critic_input()` helper method in src/gepa_adk/adapters/critic_scorer.py
- [ ] T005 Implement `_parse_critic_output()` helper method in src/gepa_adk/adapters/critic_scorer.py
- [ ] T006 Add structlog logging setup to CriticScorer in src/gepa_adk/adapters/critic_scorer.py
- [ ] T007 [P] Write contract test for Scorer protocol compliance in tests/contracts/test_critic_scorer_contract.py

**Checkpoint**: Foundation ready - CriticScorer class exists with helpers, user story implementation can begin

---

## Phase 3: User Story 1 - Basic Structured Scoring (Priority: P1) 🎯 MVP

**Goal**: Score agent outputs and receive structured feedback (score + metadata)

**Independent Test**: Create simple critic agent, call scorer, verify numeric score and feedback returned

**Acceptance Criteria** (from spec.md):
- Returns numeric score from structured JSON
- Feedback text included in metadata
- Score is float 0.0-1.0

### Tests for User Story 1

- [ ] T008 [P] [US1] Unit test for `async_score()` with mock agent in tests/unit/test_critic_scorer_unit.py
- [ ] T009 [P] [US1] Unit test for `score()` sync wrapper in tests/unit/test_critic_scorer_unit.py
- [ ] T010 [P] [US1] Unit test for JSON parse error handling in tests/unit/test_critic_scorer_unit.py
- [ ] T011 [P] [US1] Unit test for missing score field error in tests/unit/test_critic_scorer_unit.py

### Implementation for User Story 1

- [ ] T012 [US1] Implement `async_score()` method with Runner execution in src/gepa_adk/adapters/critic_scorer.py
- [ ] T013 [US1] Implement `score()` sync wrapper using asyncio.run() in src/gepa_adk/adapters/critic_scorer.py
- [ ] T014 [US1] Add error handling for CriticOutputParseError in src/gepa_adk/adapters/critic_scorer.py
- [ ] T015 [US1] Add error handling for MissingScoreFieldError in src/gepa_adk/adapters/critic_scorer.py

**Checkpoint**: User Story 1 complete - basic scoring with LlmAgent works independently

---

## Phase 4: User Story 2 - Workflow Critic Support (Priority: P2)

**Goal**: Support SequentialAgent and other workflow agents as critics

**Independent Test**: Create SequentialAgent with validator+scorer, verify final score extracted from last sub-agent

**Acceptance Criteria** (from spec.md):
- SequentialAgent executes full workflow
- Score extracted from final sub-agent output
- Handles validation state appropriately

### Tests for User Story 2

- [ ] T016 [P] [US2] Unit test for SequentialAgent critic in tests/unit/test_critic_scorer_unit.py
- [ ] T017 [P] [US2] Integration test for workflow critic (requires real ADK) in tests/integration/test_critic_scorer_integration.py

### Implementation for User Story 2

- [ ] T018 [US2] Verify async_score() handles SequentialAgent event stream in src/gepa_adk/adapters/critic_scorer.py
- [ ] T019 [US2] Add workflow-specific logging context in src/gepa_adk/adapters/critic_scorer.py

**Checkpoint**: User Stories 1 AND 2 complete - both LlmAgent and SequentialAgent critics work

---

## Phase 5: User Story 3 - Multi-Dimensional Scoring with Guidance (Priority: P3)

**Goal**: Capture dimension_scores and actionable_guidance in metadata

**Independent Test**: Configure critic to return dimension_scores/guidance, verify captured in metadata

**Acceptance Criteria** (from spec.md):
- dimension_scores dict included in metadata
- actionable_guidance string included in metadata
- All structured fields preserved

### Tests for User Story 3

- [ ] T020 [P] [US3] Unit test for dimension_scores extraction in tests/unit/test_critic_scorer_unit.py
- [ ] T021 [P] [US3] Unit test for actionable_guidance extraction in tests/unit/test_critic_scorer_unit.py

### Implementation for User Story 3

- [ ] T022 [US3] Enhance _parse_critic_output() to extract dimension_scores in src/gepa_adk/adapters/critic_scorer.py
- [ ] T023 [US3] Enhance _parse_critic_output() to extract actionable_guidance in src/gepa_adk/adapters/critic_scorer.py
- [ ] T024 [US3] Preserve all additional fields from critic output in metadata in src/gepa_adk/adapters/critic_scorer.py

**Checkpoint**: User Stories 1-3 complete - full metadata extraction works

---

## Phase 6: User Story 4 - Session State Sharing (Priority: P4)

**Goal**: Optionally share session state between main agent and critic

**Independent Test**: Pass existing session_id, verify critic accesses conversation history

**Acceptance Criteria** (from spec.md):
- Existing session_id gives critic access to history
- No session_id creates isolated session

### Tests for User Story 4

- [ ] T025 [P] [US4] Unit test for session_id parameter in tests/unit/test_critic_scorer_unit.py
- [ ] T026 [P] [US4] Unit test for isolated session creation (no session_id) in tests/unit/test_critic_scorer_unit.py
- [ ] T027 [P] [US4] Integration test for session sharing in tests/integration/test_critic_scorer_integration.py

### Implementation for User Story 4

- [ ] T028 [US4] Implement session creation/reuse logic in async_score() in src/gepa_adk/adapters/critic_scorer.py
- [ ] T029 [US4] Add session_id parameter handling with proper user_id generation in src/gepa_adk/adapters/critic_scorer.py

**Checkpoint**: All 4 user stories complete

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [ ] T030 [P] Add module-level docstring to src/gepa_adk/adapters/critic_scorer.py
- [ ] T031 [P] Export CriticScorer from src/gepa_adk/adapters/__init__.py
- [ ] T032 [P] Export scoring exceptions from src/gepa_adk/domain/__init__.py (if exists)
- [ ] T033 Run all tests with `uv run pytest tests/ -v` to verify full coverage
- [ ] T034 Run quickstart.md examples manually to validate documentation
- [ ] T035 Run linting with `uv run ruff check --fix src/gepa_adk/adapters/critic_scorer.py`
- [ ] T036 Run type check with `uv run ty check`

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────────────────┐
                                     ├──► Phase 2: Foundational
Phase 1 completes ───────────────────┘
                                              │
                                              ▼
                              ┌───────────────┴───────────────┐
                              │  All User Stories can start   │
                              │  after Foundational complete  │
                              └───────────────┬───────────────┘
                                              │
                    ┌─────────┬───────────────┼───────────────┬─────────┐
                    ▼         ▼               ▼               ▼         │
                  US1       US2             US3             US4         │
                 (P1)      (P2)            (P3)            (P4)         │
                  MVP                                                   │
                    │         │               │               │         │
                    └─────────┴───────────────┴───────────────┴─────────┤
                                                                        ▼
                                                              Phase 7: Polish
```

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US1 (P1) | Phase 2 Foundational | - |
| US2 (P2) | Phase 2 Foundational | US1 (different test files) |
| US3 (P3) | Phase 2 Foundational | US1, US2 |
| US4 (P4) | Phase 2 Foundational | US1, US2, US3 |

### Within Each User Story

1. Tests written FIRST (TDD)
2. Implementation follows
3. Verify tests pass before moving on

### Parallel Opportunities

**Phase 1**:
- T001 and T002 can run in parallel (different files)

**Phase 2**:
- T007 (contract test) parallel with T003-T006 (implementation)

**Phase 3-6 (User Stories)**:
- All unit tests within a story marked [P] can run in parallel
- User stories can be worked in parallel after Foundational complete

**Phase 7**:
- T030, T031, T032 can run in parallel (different files)

---

## Parallel Example: User Story 1

```bash
# Launch all US1 unit tests together (they test different scenarios):
Task T008: "Unit test for async_score() with mock agent"
Task T009: "Unit test for score() sync wrapper"
Task T010: "Unit test for JSON parse error handling"
Task T011: "Unit test for missing score field error"

# Then implement sequentially:
Task T012: "Implement async_score() method"
Task T013: "Implement score() sync wrapper"
Task T014: "Add error handling for CriticOutputParseError"
Task T015: "Add error handling for MissingScoreFieldError"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T007)
3. Complete Phase 3: User Story 1 (T008-T015)
4. **STOP and VALIDATE**: Run `uv run pytest tests/unit/test_critic_scorer_unit.py -v`
5. MVP ready for demo/feedback

### Incremental Delivery

1. Setup + Foundational → Core class ready
2. Add US1 → Basic scoring works → **MVP Complete**
3. Add US2 → Workflow agents supported
4. Add US3 → Rich metadata extraction
5. Add US4 → Session sharing enabled
6. Polish → Production ready

### File Touch Summary

| File | Tasks |
|------|-------|
| `src/gepa_adk/domain/exceptions.py` | T001 |
| `src/gepa_adk/adapters/critic_scorer.py` | T002-T006, T012-T015, T018-T019, T022-T024, T028-T030 |
| `src/gepa_adk/adapters/__init__.py` | T031 |
| `tests/contracts/test_critic_scorer_contract.py` | T007 |
| `tests/unit/test_critic_scorer_unit.py` | T008-T011, T016, T020-T021, T025-T026 |
| `tests/integration/test_critic_scorer_integration.py` | T017, T027 |

---

## Notes

- [P] tasks = different files or independent test scenarios
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- ADK constraint: LlmAgent with `output_schema` cannot use tools (documented in research.md)

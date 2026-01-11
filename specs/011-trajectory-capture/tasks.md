# Tasks: Trajectory Capture from ADK Sessions

**Input**: Design documents from `/specs/011-trajectory-capture/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: Unit and integration tests included per project conventions (pytest with three-layer testing).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story mapping (US1, US2, US3, US4, US5)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new module structure and configuration dataclass

- [X] T001 Create utils module directory at src/gepa_adk/utils/__init__.py
- [X] T002 [P] Add TrajectoryConfig dataclass to src/gepa_adk/domain/types.py with all configuration fields
- [X] T003 [P] Export TrajectoryConfig from src/gepa_adk/__init__.py

---

## Phase 2: Foundational (Core Utilities)

**Purpose**: Implement redaction and truncation utilities that all extraction features depend on

**⚠️ CRITICAL**: Redaction and truncation are shared utilities used by multiple user stories

- [X] T004 Implement _redact_sensitive helper function in src/gepa_adk/utils/events.py with recursive dict/list traversal
- [X] T005 Implement _truncate_strings helper function in src/gepa_adk/utils/events.py with recursive traversal and marker
- [X] T006 Implement extract_trajectory public function signature in src/gepa_adk/utils/events.py (stub returning empty trajectory)
- [X] T007 [P] Add unit tests for TrajectoryConfig defaults in tests/unit/domain/test_types.py
- [X] T008 [P] Add unit tests for _redact_sensitive in tests/unit/utils/test_events.py
- [X] T009 [P] Add unit tests for _truncate_strings in tests/unit/utils/test_events.py

**Checkpoint**: Core utilities ready - user story implementation can begin

---

## Phase 3: User Story 1 - Capture Tool Call History (Priority: P1) 🎯 MVP

**Goal**: Extract detailed tool call information (name, args, response) from ADK events

**Independent Test**: Run agent with tools, extract trajectory with include_tool_calls=True, verify tool_calls tuple contains ToolCallRecord instances with name, arguments, result fields

### Implementation for User Story 1

- [X] T010 [US1] Implement _extract_tool_calls function in src/gepa_adk/utils/events.py (extract logic from ADKAdapter, ADKAdapter will delegate to this)
- [X] T011 [US1] Wire tool call extraction into extract_trajectory with config.include_tool_calls check in src/gepa_adk/utils/events.py
- [X] T012 [US1] Add unit tests for tool call extraction with include_tool_calls=True in tests/unit/utils/test_events.py
- [X] T013 [US1] Add unit tests for tool call exclusion with include_tool_calls=False in tests/unit/utils/test_events.py
- [X] T014 [US1] Add unit test for multiple tool calls in chronological order in tests/unit/utils/test_events.py

**Checkpoint**: Tool call capture works independently - MVP deliverable

---

## Phase 4: User Story 2 - Capture State Deltas (Priority: P2)

**Goal**: Extract state changes from agent execution for reflection context

**Independent Test**: Run agent that modifies session state, extract trajectory with include_state_deltas=True, verify state_deltas tuple contains delta dictionaries

### Implementation for User Story 2

- [ ] T015 [US2] Implement _extract_state_deltas function in src/gepa_adk/utils/events.py (extract logic from ADKAdapter, ADKAdapter will delegate to this)
- [ ] T016 [US2] Wire state delta extraction into extract_trajectory with config.include_state_deltas check in src/gepa_adk/utils/events.py
- [ ] T017 [US2] Add unit tests for state delta extraction with include_state_deltas=True in tests/unit/utils/test_events.py
- [ ] T018 [US2] Add unit test for state delta exclusion with include_state_deltas=False in tests/unit/utils/test_events.py

**Checkpoint**: State delta capture works independently

---

## Phase 5: User Story 3 - Redact Sensitive Data (Priority: P2)

**Goal**: Automatically redact sensitive fields (password, api_key, token, custom keys) from trajectories

**Independent Test**: Include sensitive keys in tool call args, extract with redact_sensitive=True, verify values replaced with "[REDACTED]"

### Implementation for User Story 3

- [ ] T019 [US3] Apply redaction to tool call arguments in extract_trajectory function in src/gepa_adk/utils/events.py
- [ ] T020 [US3] Apply redaction to tool call results in extract_trajectory function in src/gepa_adk/utils/events.py
- [ ] T021 [US3] Apply redaction to state deltas in extract_trajectory function in src/gepa_adk/utils/events.py
- [ ] T022 [US3] Add unit test for default sensitive_keys redaction in tests/unit/utils/test_events.py
- [ ] T023 [US3] Add unit test for custom sensitive_keys redaction in tests/unit/utils/test_events.py
- [ ] T024 [US3] Add unit test for nested redaction (deep dict/list structures) in tests/unit/utils/test_events.py
- [ ] T025 [US3] Add unit test for redact_sensitive=False bypass in tests/unit/utils/test_events.py

**Checkpoint**: Sensitive data redaction works independently

---

## Phase 6: User Story 4 - Truncate Large Values (Priority: P2)

**Goal**: Truncate large string values (DOM, screenshots, verbose APIs) with marker indicating truncation

**Independent Test**: Create tool call with 100KB result, extract with max_string_length=1000, verify result truncated with "...[truncated N chars]" marker

### Implementation for User Story 4

- [ ] T026 [US4] Apply truncation to tool call results in extract_trajectory function in src/gepa_adk/utils/events.py
- [ ] T027 [US4] Apply truncation to tool call arguments in extract_trajectory function in src/gepa_adk/utils/events.py
- [ ] T028 [US4] Apply truncation to state deltas in extract_trajectory function in src/gepa_adk/utils/events.py
- [ ] T029 [US4] Add unit test for truncation with max_string_length limit in tests/unit/utils/test_events.py
- [ ] T030 [US4] Add unit test for truncation disabled with max_string_length=None in tests/unit/utils/test_events.py
- [ ] T031 [US4] Add unit test for truncation marker format "...[truncated N chars]" in tests/unit/utils/test_events.py
- [ ] T032 [US4] Add unit test for exact length boundary (no off-by-one) in tests/unit/utils/test_events.py
- [ ] T033 [US4] Add unit test for redaction precedence over truncation in tests/unit/utils/test_events.py

**Checkpoint**: Large value truncation works independently

---

## Phase 7: User Story 5 - Capture Token Usage (Priority: P3)

**Goal**: Extract token usage statistics (input_tokens, output_tokens, total_tokens) for cost analysis

**Independent Test**: Run agent, extract trajectory with include_token_usage=True, verify token_usage field contains TokenUsage instance

### Implementation for User Story 5

- [ ] T034 [US5] Implement _extract_token_usage function in src/gepa_adk/utils/events.py (extract logic from ADKAdapter, ADKAdapter will delegate to this)
- [ ] T035 [US5] Wire token usage extraction into extract_trajectory with config.include_token_usage check in src/gepa_adk/utils/events.py
- [ ] T036 [US5] Add unit test for token usage extraction with include_token_usage=True in tests/unit/utils/test_events.py
- [ ] T037 [US5] Add unit test for token usage exclusion with include_token_usage=False in tests/unit/utils/test_events.py

**Checkpoint**: Token usage capture works independently

---

## Phase 8: Integration & ADKAdapter Enhancement

**Purpose**: Integrate extract_trajectory with ADKAdapter and add end-to-end tests

- [ ] T038 Add trajectory_config parameter to ADKAdapter.__init__ in src/gepa_adk/adapters/adk_adapter.py
- [ ] T039 Update ADKAdapter._build_trajectory to use extract_trajectory utility in src/gepa_adk/adapters/adk_adapter.py
- [ ] T040 Export extract_trajectory from src/gepa_adk/utils/__init__.py
- [ ] T041 [P] Add integration test for full trajectory capture with ADKAdapter in tests/integration/test_trajectory_capture.py
- [ ] T042 [P] Add integration test for trajectory with redaction in tests/integration/test_trajectory_capture.py
- [ ] T043 [P] Add integration test for trajectory with truncation in tests/integration/test_trajectory_capture.py

**Checkpoint**: ADKAdapter integration complete

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, documentation, and cleanup

- [ ] T044 [P] Add edge case test for empty events list in tests/unit/utils/test_events.py
- [ ] T045 [P] Add edge case test for missing token usage metadata in tests/unit/utils/test_events.py
- [ ] T046 [P] Add edge case test for None/invalid response handling in tests/unit/utils/test_events.py
- [ ] T047 [P] Add edge case test for graceful degradation with partial/missing event attributes in tests/unit/utils/test_events.py
- [ ] T048 Add structlog debug logging to extract_trajectory for observability in src/gepa_adk/utils/events.py
- [ ] T049 Run quickstart.md validation - verify all code examples work
- [ ] T050 Run full test suite with uv run pytest -n auto

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (utilities + tests)
    ↓
┌───────────────────────────────────────────────────────────────┐
│ Phases 3-7 can proceed in parallel (different user stories)   │
│   Phase 3: US1 Tool Calls (P1) 🎯 MVP                         │
│   Phase 4: US2 State Deltas (P2)                              │
│   Phase 5: US3 Redaction (P2)                                 │
│   Phase 6: US4 Truncation (P2)                                │
│   Phase 7: US5 Token Usage (P3)                               │
└───────────────────────────────────────────────────────────────┘
    ↓
Phase 8: Integration (requires all user stories complete)
    ↓
Phase 9: Polish
```

### User Story Dependencies

- **US1 (Tool Calls)**: Depends on Foundational only - No other story dependencies
- **US2 (State Deltas)**: Depends on Foundational only - No other story dependencies
- **US3 (Redaction)**: Depends on Foundational (_redact_sensitive implemented there)
- **US4 (Truncation)**: Depends on Foundational (_truncate_strings implemented there)
- **US5 (Token Usage)**: Depends on Foundational only - No other story dependencies

### Within Each User Story

- Implementation before tests (tests verify implementation)
- Core function before wiring into extract_trajectory
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
- T002 and T003 can run in parallel

**Phase 2 (Foundational)**:
- T007, T008, T009 can run in parallel (tests for different functions)

**Phases 3-7 (User Stories)**:
- All five user stories can be implemented in parallel by different developers
- Within each story, tests can run in parallel when marked [P]

**Phase 8 (Integration)**:
- T041, T042, T043 can run in parallel (different test scenarios)

**Phase 9 (Polish)**:
- T044, T045, T046, T047 can run in parallel (edge case tests)

---

## Parallel Example: Foundational Tests

```bash
# Launch all foundational tests together:
Task: "Add unit tests for TrajectoryConfig defaults in tests/unit/domain/test_types.py"
Task: "Add unit tests for _redact_sensitive in tests/unit/utils/test_events.py"
Task: "Add unit tests for _truncate_strings in tests/unit/utils/test_events.py"
```

## Parallel Example: User Stories

```bash
# With multiple developers, after Phase 2 completes:
Developer A: Phase 3 (US1 - Tool Calls) - MVP Priority
Developer B: Phase 4 + 5 (US2 - State Deltas, US3 - Redaction)
Developer C: Phase 6 + 7 (US4 - Truncation, US5 - Token Usage)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Tool Call Capture)
4. **STOP and VALIDATE**: Test tool call extraction independently
5. Deploy/demo MVP - agents can now capture tool call context

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy (MVP with tool calls!)
3. Add User Story 2 → Test independently → Deploy (adds state context)
4. Add User Story 3 → Test independently → Deploy (adds security via redaction)
5. Add User Story 4 → Test independently → Deploy (adds memory efficiency via truncation)
6. Add User Story 5 → Test independently → Deploy (adds cost tracking)
7. Complete Integration → Full ADKAdapter support
8. Polish → Production-ready

### Single Developer Strategy

1. Complete Setup (T001-T003)
2. Complete Foundational (T004-T009)
3. Complete US1 MVP (T010-T014) → Validate
4. Complete US3 + US4 together (security & efficiency pair)
5. Complete US2 + US5 (remaining context)
6. Integration + Polish

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story (US1-US5)
- Each user story is independently completable and testable
- Redaction takes precedence over truncation (FR-019)
- Default config is secure: redact_sensitive=True
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently

# Tasks: ADK Session State Management for Reflection Agent

**Input**: Design documents from `/specs/122-adk-session-state/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, architecture.md ✅

**Tests**: Tests are included for this feature per Three-Layer Testing (ADR-005).

**Documentation**: This is an internal refactor - no user-facing docs/ updates required per scope table.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| Internal refactor | Not required | Not required |

This feature is an internal refactor of data flow patterns. No public API changes.

---

## Phase 1: Setup

**Purpose**: Minimal setup - feature uses existing project structure

- [X] T001 Verify branch `122-adk-session-state` is checked out
- [X] T002 Verify ADK version >= 1.22.0 in pyproject.toml

---

## Phase 2: Foundational (Shared Utility)

**Purpose**: Create shared utility that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: User story work depends on this shared utility

### Implementation

- [X] T003 Add `extract_output_from_state()` function to `src/gepa_adk/utils/events.py` per contract in `specs/122-adk-session-state/contracts/extract-output-from-state.md`

### Tests

- [X] T004 [P] Add unit tests for `extract_output_from_state()` in `tests/unit/utils/test_events_state.py`

**Checkpoint**: Shared utility ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Session State Data Flow (Priority: P1) 🎯 MVP

**Goal**: Reflection agent receives input data (component_text, trials) through ADK session state

**Independent Test**: Configure reflection agent with session state, verify data accessible via ADK state templating

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T005 [P] [US1] Unit test for session state injection in `tests/unit/engine/test_adk_reflection_state.py` - verify `component_text` and `trials` injected into session.state
- [X] T006 [P] [US1] Contract test for ReflectionFn signature unchanged in `tests/contracts/test_reflection_fn.py`

### Implementation for User Story 1

- [X] T007 [US1] Verify `src/gepa_adk/engine/adk_reflection.py` creates session with state dict containing `component_text` and `trials` (existing functionality - add test coverage only)
- [X] T008 [US1] Verify instruction templates use `{component_text}` and `{trials}` syntax for state access (existing - add test coverage)

**Checkpoint**: Session state data flow verified and tested

---

## Phase 4: User Story 2 - Automatic Output Storage via output_key (Priority: P2)

**Goal**: Reflection agent stores proposal output automatically in session state using output_key

**Independent Test**: Configure agent with output_key, verify proposal retrievable from session.state[output_key]

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [P] [US2] Unit test for output_key configuration in `tests/unit/engine/test_adk_reflection_state.py` - verify LlmAgent has output_key set
- [X] T010 [P] [US2] Unit test for state-based output extraction in `tests/unit/engine/test_adk_reflection_state.py` - verify output retrieved from session.state
- [X] T011 [P] [US2] Unit test for fallback to event extraction in `tests/unit/engine/test_adk_reflection_state.py` - verify fallback when state missing

### Implementation for User Story 2

- [X] T012 [US2] Add `output_key` parameter to `create_adk_reflection_fn()` in `src/gepa_adk/engine/adk_reflection.py` with default value `"proposed_instruction"`
- [X] T013 [US2] Configure `output_key` on LlmAgent in `src/gepa_adk/engine/adk_reflection.py`
- [X] T014 [US2] Import `extract_output_from_state` from `gepa_adk.utils.events` in `src/gepa_adk/engine/adk_reflection.py`
- [X] T015 [US2] Implement state-based output retrieval after agent execution in `src/gepa_adk/engine/adk_reflection.py`:
  - Get session via `session_service.get_session()`
  - Call `extract_output_from_state(session.state, output_key)`
  - Fallback to `extract_final_output(events)` if None
- [X] T016 [US2] Add structlog debug logging for output retrieval method used

**Checkpoint**: output_key mechanism working with fallback to event extraction

---

## Phase 5: User Story 3 - Multi-Agent Workflow State Integration (Priority: P3)

**Goal**: Refactor multi_agent.py to use shared utility for state extraction

**Independent Test**: Run multi-agent workflow, verify state extraction uses shared utility

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T017 [P] [US3] Unit test for refactored `_extract_primary_output()` in `tests/unit/adapters/test_multi_agent_state_extraction.py` - verify uses shared utility
- [X] T018 [P] [US3] Integration test for multi-agent state flow (covered by unit tests with mocks)

### Implementation for User Story 3

- [X] T019 [US3] Import `extract_output_from_state` from `gepa_adk.utils.events` in `src/gepa_adk/adapters/multi_agent.py`
- [X] T020 [US3] Refactor `_extract_primary_output()` in `src/gepa_adk/adapters/multi_agent.py` to use shared utility:
  ```python
  def _extract_primary_output(
      self, pipeline_output: str, session_state: dict[str, Any], primary_agent: LlmAgent
  ) -> str:
      output_key = getattr(primary_agent, "output_key", None)
      result = extract_output_from_state(session_state, output_key)
      if result is not None:
          return result
      return pipeline_output  # Fallback
  ```
- [X] T021 [US3] Verify existing multi_agent tests still pass after refactor

**Checkpoint**: Multi-agent workflow uses shared utility, DRY principle satisfied

---

## Phase 6: Verification & Cross-Cutting Concerns

**Purpose**: Final verification across all user stories

### Test Verification

- [X] T022 Run `uv run pytest tests/unit/utils/test_events_state.py` - verify shared utility tests pass
- [X] T023 Run `uv run pytest tests/unit/engine/test_adk_reflection_state.py` - verify reflection tests pass
- [X] T024 Run `uv run pytest tests/unit/adapters/test_multi_agent_state_extraction.py` - verify multi-agent tests pass
- [X] T025 Run `uv run pytest tests/contracts/` - verify contract tests pass
- [X] T026 Code quality check passed via `scripts/code_quality_check.sh`

### Cross-Cutting Tasks

- [X] T027 Run full test suite (149 related tests pass) - verify no regressions
- [X] T028 Run `scripts/code_quality_check.sh` - verify linting/typing passes
- [ ] T029 Validate quickstart.md scenarios work with new implementation (manual validation)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (T003)
- **User Story 2 (Phase 4)**: Depends on Foundational (T003)
- **User Story 3 (Phase 5)**: Depends on Foundational (T003)
- **Verification (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - Verifies existing functionality
- **User Story 2 (P2)**: Can start after Foundational - Adds new output_key functionality
- **User Story 3 (P3)**: Can start after Foundational - Refactors existing code to use shared utility

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation before verification
- Story complete before moving to next priority

### Parallel Opportunities

- T005, T006 can run in parallel (different test files)
- T009, T010, T011 can run in parallel (same file but independent test cases)
- T017, T018 can run in parallel (different test files)
- User Stories 1, 2, 3 can start in parallel after Foundational phase (if team capacity allows)

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (shared utility)
3. Complete Phase 3: User Story 1 (verify existing state injection)
4. Complete Phase 4: User Story 2 (add output_key mechanism)
5. **STOP and VALIDATE**: Test reflection agent with output_key
6. Proceed to User Story 3 (refactor multi_agent)

### Key Files Changed

| File | Change Type |
|------|-------------|
| `src/gepa_adk/utils/events.py` | ADD function |
| `src/gepa_adk/engine/adk_reflection.py` | MODIFY - add output_key |
| `src/gepa_adk/adapters/multi_agent.py` | REFACTOR - use shared utility |
| `tests/unit/utils/test_events_state.py` | ADD file |
| `tests/unit/engine/test_adk_reflection_state.py` | ADD file |
| `tests/unit/adapters/test_multi_agent_state.py` | ADD file |
| `tests/contracts/test_reflection_fn.py` | ADD/EXTEND file |
| `tests/integration/test_adk_state_flow.py` | ADD file |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Shared utility in utils/ follows hexagonal architecture (accessible from both adapters/ and engine/)

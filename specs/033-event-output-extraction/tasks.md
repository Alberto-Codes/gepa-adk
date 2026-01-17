# Tasks: Shared ADK Event Output Extraction Utility

**Input**: Design documents from `/specs/033-event-output-extraction/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required per Constitution Principle IV (Three-Layer Testing) - TDD approach

**Documentation**: Bug fix + internal refactor - NO user-facing API changes. Per Constitution VI scope table, docs/guides and examples updates are NOT required.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root

---

## Phase 1: Setup

**Purpose**: Verify environment and understand current implementation

- [ ] T001 Verify branch 033-event-output-extraction is checked out and up to date with develop
- [ ] T002 [P] Review existing `extract_trajectory` function patterns in src/gepa_adk/utils/events.py
- [ ] T003 [P] Review current extraction logic in src/gepa_adk/adapters/adk_adapter.py (lines ~753-760)
- [ ] T004 [P] Review current extraction logic in src/gepa_adk/adapters/multi_agent.py (lines ~747-769, ~847-869)
- [ ] T005 [P] Review current extraction logic in src/gepa_adk/adapters/critic_scorer.py (lines ~542-549)

---

## Phase 2: Foundational (Utility Function Core)

**Purpose**: Create the shared utility function with basic extraction and bug fix

**⚠️ CRITICAL**: Adapter refactoring cannot begin until this phase is complete

### Tests (TDD - Write FIRST, ensure they FAIL)

- [ ] T006 [P] Create contract test file tests/contracts/test_extract_final_output_contract.py with test fixtures
- [ ] T007 [P] Add unit tests for extract_final_output in tests/unit/utils/test_events.py covering TC-001 through TC-010 from contract spec (verifies FR-001, FR-002, FR-003, FR-004, FR-005, FR-012, FR-013)
- [ ] T007a [P] Add integration test in tests/integration/test_extract_final_output.py verifying extraction with real ADK event objects (@pytest.mark.slow)

### Implementation

- [ ] T008 Add `extract_final_output` function signature and docstring to src/gepa_adk/utils/events.py
- [ ] T009 Implement response_content extraction path (FR-003) in src/gepa_adk/utils/events.py
- [ ] T010 Implement content.parts fallback path (FR-004) in src/gepa_adk/utils/events.py
- [ ] T011 Implement part.thought filtering (FR-005, bug fix) in src/gepa_adk/utils/events.py
- [ ] T012 Add graceful error handling for missing attributes (FR-012, FR-013) in src/gepa_adk/utils/events.py
- [ ] T013 Export `extract_final_output` in src/gepa_adk/utils/__init__.py if needed
- [ ] T014 Verify all unit tests pass for basic extraction

**Checkpoint**: Core utility function ready with bug fix. Can now proceed to US3 and US4.

---

## Phase 3: User Story 3 - Streaming JSON Concatenation Support (Priority: P2)

**Goal**: Add `prefer_concatenated` parameter to support CriticScorer streaming scenarios

**Independent Test**: Pass multiple events with partial text, verify concatenation works

### Tests (TDD)

- [ ] T015 [P] [US3] Add unit tests for prefer_concatenated=True behavior in tests/unit/utils/test_events.py
- [ ] T016 [P] [US3] Add unit tests for prefer_concatenated=False (default) behavior confirming single-event extraction

### Implementation

- [ ] T017 [US3] Implement prefer_concatenated=True logic (FR-006, FR-007) in src/gepa_adk/utils/events.py
- [ ] T018 [US3] Verify all concatenation tests pass

**Checkpoint**: Full utility function ready with both extraction modes

---

## Phase 4: User Story 4 - Adapter Consolidation (Priority: P2)

**Goal**: Replace duplicated extraction logic in all 4 adapter locations with shared utility

**Independent Test**: Run existing adapter tests to verify behavior unchanged

### Refactor ADKAdapter

- [ ] T019 [US4] Import extract_final_output in src/gepa_adk/adapters/adk_adapter.py
- [ ] T020 [US4] Replace inline extraction in _run_single_example (~lines 753-760) with extract_final_output call
- [ ] T021 [US4] Run existing ADKAdapter tests to verify no regression

### Refactor MultiAgentAdapter

- [ ] T022 [P] [US4] Import extract_final_output in src/gepa_adk/adapters/multi_agent.py
- [ ] T023 [US4] Replace inline extraction in _run_shared_session (~lines 747-769) with extract_final_output call
- [ ] T024 [US4] Replace inline extraction in _run_isolated_sessions (~lines 847-869) with extract_final_output call
- [ ] T025 [US4] Run existing MultiAgentAdapter tests to verify no regression

### Refactor CriticScorer

- [ ] T026 [P] [US4] Import extract_final_output in src/gepa_adk/adapters/critic_scorer.py
- [ ] T027 [US4] Replace inline extraction in async_score (~lines 542-549) with extract_final_output call (use prefer_concatenated if needed)
- [ ] T028 [US4] Run existing CriticScorer tests to verify no regression

**Checkpoint**: All 4 adapter locations now use shared utility. No duplicated extraction logic remains.

---

## Phase 5: Verification & Cross-Cutting Concerns

**Purpose**: Final verification that all tests pass and code quality is maintained

### Test Suite Verification

- [ ] T029 Run full test suite: `uv run pytest` to verify all tests pass
- [ ] T030 Run contract tests specifically: `uv run pytest tests/contracts/`
- [ ] T031 Run unit tests specifically: `uv run pytest tests/unit/`
- [ ] T031a Run coverage for extract_final_output: `uv run pytest --cov=gepa_adk.utils.events --cov-report=term-missing tests/` and verify 100% coverage for new function (SC-004)

### Code Quality

- [ ] T032 [P] Run linting: `uv run ruff check --fix src/gepa_adk/utils/events.py`
- [ ] T033 [P] Run formatting: `uv run ruff format src/gepa_adk/utils/events.py`
- [ ] T034 [P] Run type checking: `uv run ty check` on modified files
- [ ] T035 Verify docstring coverage with interrogate on src/gepa_adk/utils/events.py

### Final Validation

- [ ] T036 Verify SC-001: No duplicated extraction logic remains in adapters (manual code review)
- [ ] T037 Verify SC-002: Create test event with thought=True parts, confirm filtering works
- [ ] T038 Run quickstart.md validation scenarios manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS US3 and US4
- **US3 (Phase 3)**: Depends on Phase 2 completion (needs basic utility function)
- **US4 (Phase 4)**: Depends on Phase 2 and Phase 3 completion (needs full utility)
- **Verification (Phase 5)**: Depends on all previous phases

### User Story Dependencies

- **US1+US2 (Foundational)**: Combined in Phase 2 as they're inseparable (utility IS the bug fix)
- **US3 (P2)**: Can start after Phase 2 - extends utility with concatenation
- **US4 (P2)**: Can start after Phase 3 - refactors adapters to use complete utility (CriticScorer requires prefer_concatenated flag from US3)

### Within Each Phase

- Tests MUST be written and FAIL before implementation (TDD)
- Implementation follows test coverage
- Each task should be committed

### Parallel Opportunities

**Phase 1 (Setup):**
```bash
# All review tasks can run in parallel:
Task: "T002 Review extract_trajectory patterns"
Task: "T003 Review adk_adapter extraction"
Task: "T004 Review multi_agent extraction"
Task: "T005 Review critic_scorer extraction"
```

**Phase 2 (Foundational):**
```bash
# Tests can run in parallel:
Task: "T006 Contract test file"
Task: "T007 Unit tests"
Task: "T007a Integration test"
```

**Phase 4 (US4 Adapter Consolidation):**
```bash
# Import tasks can run in parallel:
Task: "T022 Import in multi_agent.py"
Task: "T026 Import in critic_scorer.py"
```

**Phase 5 (Verification):**
```bash
# Quality checks can run in parallel:
Task: "T032 Linting"
Task: "T033 Formatting"
Task: "T034 Type checking"
```

---

## Implementation Strategy

### MVP First (Foundational Phase Only)

1. Complete Phase 1: Setup (review existing code)
2. Complete Phase 2: Foundational (utility function with bug fix)
3. **STOP and VALIDATE**: Tests pass, bug fix works
4. Can demo bug fix at this point (utility function usable, but adapters not yet refactored)

### Full Implementation

1. Complete Setup + Foundational → Core utility ready with bug fix
2. Add US3 (concatenation) → Enhanced utility for streaming
3. Add US4 (adapter consolidation) → Full refactoring complete
4. Verification → All tests pass, code quality verified

### Incremental Delivery

Each phase adds value:
- After Phase 2: Bug fix available, utility function usable manually
- After Phase 3: Full utility with concatenation mode
- After Phase 4: All adapters using shared utility, maintenance simplified
- After Phase 5: Verified, polished, ready for merge

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [Story] label maps task to specific user story for traceability
- US1 and US2 are combined in Phase 2 (both P1, inseparable)
- US3 and US4 are both P2 but sequential (US4 needs complete utility)
- Bug fix (part.thought filtering) is critical path - verified in T011 and T037
- Commit after each task or logical group
- Stop at any checkpoint to validate progress

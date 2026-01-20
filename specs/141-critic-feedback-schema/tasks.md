# Tasks: Standardize Critic Feedback Schema

**Input**: Design documents from `/specs/141-critic-feedback-schema/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Three-layer testing required per ADR-005 (contract, unit, integration).

**Documentation**: Per Constitution Principle VI, this feature changes the critic/scorer API and requires documentation updates.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| New public API | Required | Required |
| **This feature** | **Required** (critic-agents.md) | **Recommended** |

---

## Phase 1: Setup

**Purpose**: Verify existing code structure and prepare for implementation

- [X] T001 Review existing `normalize_feedback()` in `src/gepa_adk/adapters/critic_scorer.py` (lines 210-305)
- [X] T002 Review existing `TrialBuilder.build_feedback()` in `src/gepa_adk/adapters/trial_builder.py` (lines 182-203)
- [X] T003 [P] Review existing test files to understand current test patterns in `tests/unit/adapters/test_trial_builder.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core normalization function that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement `normalize_feedback()` function in `src/gepa_adk/adapters/trial_builder.py` per contract spec:
  - Accept `score: float` and `raw_feedback: str | dict[str, Any] | None`
  - Return `dict[str, Any]` with required `score` and `feedback_text` fields
  - Map `dimension_scores` → `dimensions`, `actionable_guidance` → `guidance`
  - Pass through custom fields unchanged
  - Handle edge cases: None, empty string, non-string feedback_text, score key in dict
- [X] T005 Add Google-style docstring to `normalize_feedback()` per ADR-010
- [X] T006 Update `TrialBuilder.build_feedback()` to use new `normalize_feedback()` function

**Checkpoint**: Foundation ready - normalization function implemented and integrated

---

## Phase 3: User Story 1 - Simple Critic Returns Score and String (Priority: P1) 🎯 MVP

**Goal**: Developers can return simple `(score, "feedback string")` tuples that automatically normalize to consistent format

**Independent Test**: Create a scorer returning `(0.45, "Too clinical")` and verify output contains `{"score": 0.45, "feedback_text": "Too clinical"}`

### Tests for User Story 1

- [X] T007 [P] [US1] Add unit test `test_normalize_string_feedback` in `tests/unit/adapters/test_trial_builder.py`:
  - Test `normalize_feedback(0.75, "Good but verbose")` returns `{"score": 0.75, "feedback_text": "Good but verbose"}`
- [X] T008 [P] [US1] Add unit test `test_normalize_empty_string` in `tests/unit/adapters/test_trial_builder.py`:
  - Test `normalize_feedback(0.0, "")` returns `{"score": 0.0, "feedback_text": ""}`
- [X] T009 [P] [US1] Add unit test `test_normalize_none_feedback` in `tests/unit/adapters/test_trial_builder.py`:
  - Test `normalize_feedback(1.0, None)` returns `{"score": 1.0, "feedback_text": ""}`

### Implementation for User Story 1

- [X] T010 [US1] Verify simple string input path works in `normalize_feedback()` implementation (from T004)
- [X] T011 [US1] Run unit tests to confirm US1 acceptance scenarios pass

### Documentation for User Story 1 (per Constitution VI)

- [X] T012 [P] [US1] Update `docs/guides/critic-agents.md` with:
  - Simple feedback format section (return `(score, "feedback string")`)
  - Advanced feedback format section (return `(score, dict)`)
  - Field mapping table (`dimension_scores` → `dimensions`, etc.)
  - Migration notes (backwards compatible - no breaking changes)
- [X] T013 [P] [US1] Add or update example in `examples/` demonstrating both feedback formats

**Checkpoint**: Simple feedback format fully functional, tested, AND documented

---

## Phase 4: User Story 2 - Advanced Critic Returns Score and Dictionary (Priority: P2)

**Goal**: Power users can return `(score, dict)` with detailed feedback including dimensions, guidance, and custom fields

**Independent Test**: Create a scorer returning `(0.45, {"feedback_text": "Too clinical", "dimension_scores": {"voice": 0.2}})` and verify all fields pass through

### Tests for User Story 2

- [X] T014 [P] [US2] Add unit test `test_normalize_advanced_full` in `tests/unit/adapters/test_trial_builder.py`:
  - Test full dict with `feedback_text`, `dimension_scores`, `actionable_guidance` normalizes to `feedback_text`, `dimensions`, `guidance`
- [X] T015 [P] [US2] Add unit test `test_normalize_fallback_feedback_key` in `tests/unit/adapters/test_trial_builder.py`:
  - Test `{"feedback": "Legacy"}` falls back to `feedback_text`
- [X] T016 [P] [US2] Add unit test `test_normalize_custom_fields` in `tests/unit/adapters/test_trial_builder.py`:
  - Test custom fields like `{"feedback_text": "OK", "custom_metric": 42}` pass through unchanged
- [X] T017 [P] [US2] Add unit test `test_normalize_dict_score_ignored` in `tests/unit/adapters/test_trial_builder.py`:
  - Test explicit score parameter takes precedence over `score` key in dict
- [X] T018 [P] [US2] Add unit test `test_normalize_nonstring_feedback` in `tests/unit/adapters/test_trial_builder.py`:
  - Test non-string `feedback_text` (e.g., `123`) converts to string `"123"`
- [X] T019 [P] [US2] Add unit test `test_normalize_empty_dimensions` in `tests/unit/adapters/test_trial_builder.py`:
  - Test empty `dimension_scores: {}` is not included in output

### Implementation for User Story 2

- [X] T020 [US2] Verify dict input path works in `normalize_feedback()` implementation (from T004)
- [X] T021 [US2] Run unit tests to confirm US2 acceptance scenarios pass

**Checkpoint**: Advanced feedback format fully functional and tested

---

## Phase 5: User Story 3 - Reflector Receives Consistent Format (Priority: P1)

**Goal**: Reflection agent always receives consistent `{"score": ..., "feedback_text": ...}` regardless of input format

**Independent Test**: Run both simple and advanced scorers through the system and verify reflector receives identically-structured feedback

### Tests for User Story 3

- [X] T022 [P] [US3] Add contract test in `tests/contracts/test_reflection_example_metadata.py`:
  - Verify normalized feedback always contains `score` and `feedback_text` keys
- [X] T023 [P] [US3] Add integration test in `tests/integration/test_critic_reflection_metadata.py`:
  - End-to-end test with simple scorer verifying feedback structure
- [X] T024 [P] [US3] Add integration test in `tests/integration/test_critic_reflection_metadata.py`:
  - End-to-end test with advanced scorer verifying all fields pass through

### Implementation for User Story 3

- [X] T025 [US3] Verify `TrialBuilder.build_trial()` correctly uses normalized feedback from `build_feedback()`
- [X] T026 [US3] Run integration tests to confirm US3 acceptance scenarios pass

**Checkpoint**: All user stories complete - consistent format guaranteed

---

## Phase 6: Final Verification

**Purpose**: Build verification and final test runs

### Build Verification (REQUIRED)

- [X] T027 Verify `uv run mkdocs build` passes without warnings
- [X] T028 Preview docs with `uv run mkdocs serve` and verify critic-agents.md renders correctly

### Final Verification

- [X] T029 Run full test suite: `uv run pytest tests/unit/adapters/test_trial_builder.py -v`
- [X] T030 Run contract tests: `uv run pytest tests/contracts/test_reflection_example_metadata.py -v`
- [X] T031 Run integration tests: `uv run pytest tests/integration/test_critic_reflection_metadata.py -v`
- [X] T032 Verify `uv run ruff check src/gepa_adk/adapters/trial_builder.py` passes
- [X] T033 Run quickstart.md validation scenarios manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 includes documentation tasks per Constitution VI
  - US1 and US3 are both P1 priority but can be done in parallel
  - US2 (P2) can be done after or in parallel with US1/US3
- **Final Verification (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1/US3
- **User Story 3 (P1)**: Can start after Foundational (Phase 2) - May run after US1/US2 for integration tests

### Within Each User Story

- Tests written FIRST (TDD per ADR-005)
- Implementation verifies tests pass
- Story complete before checkpoint

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T001 ─┬─ T002 ─┬─ T003
      └────────┴────────→ All can run in parallel
```

**Phase 3-5 (User Stories)** - Tests and docs can run in parallel:
```
T007 ─┬─ T008 ─┬─ T009  (US1 tests)
T012 ─┬─ T013              (US1 docs - per Constitution VI)
T014 ─┬─ T015 ─┬─ T016 ─┬─ T017 ─┬─ T018 ─┬─ T019  (US2 tests)
T022 ─┬─ T023 ─┬─ T024  (US3 tests)
```

---

## Parallel Example: All Unit Tests

```bash
# Launch all US1 unit tests together:
Task: "Add unit test test_normalize_string_feedback in tests/unit/adapters/test_trial_builder.py"
Task: "Add unit test test_normalize_empty_string in tests/unit/adapters/test_trial_builder.py"
Task: "Add unit test test_normalize_none_feedback in tests/unit/adapters/test_trial_builder.py"

# Launch US1 documentation tasks together:
Task: "Update docs/guides/critic-agents.md with feedback format documentation"
Task: "Add or update example in examples/ demonstrating both feedback formats"

# Launch all US2 unit tests together:
Task: "Add unit test test_normalize_advanced_full in tests/unit/adapters/test_trial_builder.py"
Task: "Add unit test test_normalize_fallback_feedback_key in tests/unit/adapters/test_trial_builder.py"
Task: "Add unit test test_normalize_custom_fields in tests/unit/adapters/test_trial_builder.py"
Task: "Add unit test test_normalize_dict_score_ignored in tests/unit/adapters/test_trial_builder.py"
Task: "Add unit test test_normalize_nonstring_feedback in tests/unit/adapters/test_trial_builder.py"
Task: "Add unit test test_normalize_empty_dimensions in tests/unit/adapters/test_trial_builder.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (review existing code)
2. Complete Phase 2: Foundational (implement `normalize_feedback()`)
3. Complete Phase 3: User Story 1 (simple format tests + verification)
4. **STOP and VALIDATE**: Test simple format independently
5. Demo: Show `(0.75, "Good feedback")` normalizes correctly

### Incremental Delivery

1. Setup + Foundational → Normalization function ready
2. Add User Story 1 → Simple format works + documented → Demo MVP
3. Add User Story 2 → Advanced format works → Demo
4. Add User Story 3 → Integration verified → Demo
5. Final Verification → All tests pass, docs build clean

### Task Summary

| Phase | Tasks | Parallel Opportunities |
|-------|-------|------------------------|
| Setup | 3 | 3 (all parallelizable) |
| Foundational | 3 | 0 (sequential) |
| US1 (P1) | 7 | 5 (tests + docs) |
| US2 (P2) | 8 | 6 (tests) |
| US3 (P1) | 5 | 3 (tests) |
| Final Verification | 7 | 0 (sequential) |
| **Total** | **33** | **17** |

---

## Notes

- [P] tasks = different files or independent operations
- [Story] label maps task to specific user story for traceability
- Three-layer testing required per ADR-005 (contract, unit, integration)
- Documentation required per Constitution VI (user-facing API change)
- No new dependencies - uses existing google-adk and structlog
- Backwards compatible - existing scorers continue to work
- Run `uv run mkdocs build` before PR to verify docs build cleanly

# Tasks: Pass CriticScorer Metadata to Reflection Agent

**Input**: Design documents from `/specs/019-critic-metadata-passthrough/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are included per constitution requirement (Three-Layer Testing).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/gepa_adk/`, `tests/` at repository root
- Feature uses hexagonal architecture: `ports/`, `adapters/`, `domain/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project setup needed - this feature modifies existing files only

- [X] T001 Verify existing test infrastructure runs with `uv run pytest tests/ -v --collect-only`
- [X] T002 [P] Read current EvaluationBatch implementation in src/gepa_adk/ports/adapter.py
- [X] T003 [P] Read current ADKAdapter._build_reflection_example() in src/gepa_adk/adapters/adk_adapter.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structure change that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Add `metadata: list[dict[str, Any]] | None = None` field to EvaluationBatch dataclass in src/gepa_adk/ports/adapter.py
- [X] T005 Update EvaluationBatch docstring to document metadata field, index alignment, and type in src/gepa_adk/ports/adapter.py
- [X] T006 Modify ADKAdapter._eval_single_with_semaphore() to capture metadata from scorer.async_score() return tuple in src/gepa_adk/adapters/adk_adapter.py
- [X] T007 Modify ADKAdapter.evaluate() to collect metadata list and pass to EvaluationBatch constructor in src/gepa_adk/adapters/adk_adapter.py
- [X] T008 Add optional `metadata: dict[str, Any] | None = None` parameter to ADKAdapter._build_reflection_example() signature in src/gepa_adk/adapters/adk_adapter.py
- [X] T009 Modify ADKAdapter.make_reflective_dataset() to pass metadata[i] to _build_reflection_example() in src/gepa_adk/adapters/adk_adapter.py

**Checkpoint**: Foundation ready - EvaluationBatch has metadata field, ADKAdapter captures and passes metadata

---

## Phase 3: User Story 1 - Rich Feedback in Reflection Context (Priority: P1) 🎯 MVP

**Goal**: Include critic `feedback` and `actionable_guidance` in the reflection example's Feedback string

**Independent Test**: Run evaluation with CriticScorer that returns feedback, verify Feedback string contains the text

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Create contract test for EvaluationBatch metadata field in tests/contracts/test_evaluation_batch_metadata.py (copy from specs/019-critic-metadata-passthrough/contracts/evaluation_batch_contract.py)
- [X] T011 [P] [US1] Create contract test for _build_reflection_example with feedback in tests/contracts/test_reflection_example_metadata.py (copy from specs/019-critic-metadata-passthrough/contracts/reflection_example_contract.py)
- [X] T012 [US1] Run contract tests to verify they FAIL with `uv run pytest tests/contracts/test_*metadata*.py -v`

### Implementation for User Story 1

- [X] T013 [US1] Implement feedback text extraction in _build_reflection_example(): append "Feedback: {text}" when metadata.get("feedback") is non-empty in src/gepa_adk/adapters/adk_adapter.py
- [X] T014 [US1] Implement actionable_guidance extraction in _build_reflection_example(): append "Guidance: {text}" when metadata.get("actionable_guidance") is non-empty in src/gepa_adk/adapters/adk_adapter.py
- [X] T015 [US1] Add structured logging for metadata passthrough using self._logger.debug() in src/gepa_adk/adapters/adk_adapter.py
- [X] T016 [US1] Run contract tests to verify they PASS with `uv run pytest tests/contracts/test_*metadata*.py -v`

**Checkpoint**: User Story 1 complete - feedback and actionable_guidance flow to reflection agent

---

## Phase 4: User Story 2 - Dimension Scores in Reflection (Priority: P2)

**Goal**: Include dimension_scores in the reflection example's Feedback string in readable format

**Independent Test**: Run evaluation with critic returning dimension_scores, verify Feedback string contains formatted dimensions

### Tests for User Story 2

- [X] T017 [US2] Add unit test for dimension_scores formatting in _build_reflection_example() in tests/unit/test_adk_adapter_metadata.py
- [X] T018 [US2] Run unit test to verify it FAILS with `uv run pytest tests/unit/test_adk_adapter_metadata.py -v -k dimension`

### Implementation for User Story 2

- [X] T019 [US2] Implement dimension_scores formatting in _build_reflection_example(): append "Dimensions: key1=val1, key2=val2" when metadata.get("dimension_scores") is non-empty dict in src/gepa_adk/adapters/adk_adapter.py
- [X] T020 [US2] Run unit test to verify it PASSES with `uv run pytest tests/unit/test_adk_adapter_metadata.py -v -k dimension`

**Checkpoint**: User Story 2 complete - dimension scores flow to reflection agent in readable format

---

## Phase 5: User Story 3 - Backward Compatibility (Priority: P3)

**Goal**: System works correctly when metadata is None, empty dict, partial, or malformed

**Independent Test**: Run evaluation with non-critic scorer (no metadata), verify reflection pipeline completes without errors

### Tests for User Story 3

- [X] T021 [US3] Add unit test for None metadata handling in _build_reflection_example() in tests/unit/test_adk_adapter_metadata.py
- [X] T022 [P] [US3] Add unit test for empty dict metadata handling in tests/unit/test_adk_adapter_metadata.py
- [X] T023 [P] [US3] Add unit test for partial metadata (only some fields) handling in tests/unit/test_adk_adapter_metadata.py
- [X] T024 [P] [US3] Add unit test for non-dict metadata type handling (logs warning, falls back to score-only) in tests/unit/test_adk_adapter_metadata.py
- [X] T025 [US3] Run backward compatibility tests to verify they FAIL with `uv run pytest tests/unit/test_adk_adapter_metadata.py -v -k "None or empty or partial or malformed"`

### Implementation for User Story 3

- [X] T026 [US3] Ensure _build_reflection_example() handles metadata=None gracefully (default parameter already handles this) in src/gepa_adk/adapters/adk_adapter.py
- [X] T027 [US3] Ensure _build_reflection_example() handles empty dict {} gracefully (no extra text added) in src/gepa_adk/adapters/adk_adapter.py
- [X] T028 [US3] Ensure _build_reflection_example() handles partial metadata (only feedback, no guidance) gracefully in src/gepa_adk/adapters/adk_adapter.py
- [X] T029 [US3] Implement warning log for malformed metadata using self._logger.warning("adapter.metadata.malformed", ...) in src/gepa_adk/adapters/adk_adapter.py
- [X] T030 [US3] Run backward compatibility tests to verify they PASS with `uv run pytest tests/unit/test_adk_adapter_metadata.py -v -k "None or empty or partial or malformed"`

### Integration Tests for User Story 3

- [X] T031 [US3] Create integration test for end-to-end critic→reflection metadata flow in tests/integration/test_critic_reflection_metadata.py
- [X] T032 [US3] Run integration test with `uv run pytest tests/integration/test_critic_reflection_metadata.py -v --slow`

**Checkpoint**: User Story 3 complete - backward compatibility verified with three-layer testing

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [X] T033 Run full test suite to verify no regressions with `uv run pytest tests/ -v`
- [X] T034 Run type checker to verify type hints with `uv run ty check`
- [X] T035 Run linter to verify code style with `uv run ruff check src/gepa_adk/ports/adapter.py src/gepa_adk/adapters/adk_adapter.py`
- [X] T036 [P] Update docstrings for _build_reflection_example() to document metadata parameter in src/gepa_adk/adapters/adk_adapter.py
- [X] T037 [P] Update docstrings for make_reflective_dataset() to document metadata passthrough in src/gepa_adk/adapters/adk_adapter.py
- [X] T038 Validate quickstart.md example works by running code snippet in specs/019-critic-metadata-passthrough/quickstart.md

**Performance Note**: SC-004 (<5% overhead) is inherently satisfied - metadata is already computed by scorer; this feature only stores and passes it through existing data structures with no additional I/O or computation.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verification only
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion (can run in parallel with US1)
- **User Story 3 (Phase 5)**: Depends on Foundational phase completion (can run in parallel with US1/US2)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of US1/US2

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Implementation tasks in order (extraction → formatting → logging)
3. Tests MUST PASS after implementation
4. Story complete before moving to next priority

### Parallel Opportunities

- T002, T003 can run in parallel (reading different files)
- T010, T011 can run in parallel (contract tests in different files)
- T022, T023, T024 can run in parallel (unit tests for edge cases)
- T036, T037 can run in parallel (docstring updates in different methods)
- All user stories can start in parallel after Foundational phase (if team capacity allows)

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all contract tests for User Story 1 together:
Task: "Create contract test for EvaluationBatch metadata in tests/contracts/test_evaluation_batch_metadata.py"
Task: "Create contract test for _build_reflection_example in tests/contracts/test_reflection_example_metadata.py"
```

## Parallel Example: User Story 3 Edge Case Tests

```bash
# Launch all backward compatibility tests together:
Task: "Add unit test for empty dict metadata handling in tests/unit/test_adk_adapter_metadata.py"
Task: "Add unit test for partial metadata handling in tests/unit/test_adk_adapter_metadata.py"
Task: "Add unit test for non-dict metadata type handling in tests/unit/test_adk_adapter_metadata.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verification)
2. Complete Phase 2: Foundational (EvaluationBatch + ADKAdapter changes)
3. Complete Phase 3: User Story 1 (feedback + actionable_guidance)
4. **STOP and VALIDATE**: Test with CriticScorer that returns feedback
5. Deploy/demo if ready - this delivers the core value

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test → Commit (MVP!)
3. Add User Story 2 → Test → Commit (dimension scores)
4. Add User Story 3 → Test → Commit (backward compat verified)
5. Each story adds value without breaking previous stories

### Single Developer Strategy

With one developer (most likely scenario):

1. Complete Setup + Foundational (T001-T009)
2. User Story 1 tests → implementation → verify (T010-T016)
3. User Story 2 tests → implementation → verify (T017-T020)
4. User Story 3 tests → implementation → verify (T021-T032)
5. Polish (T033-T038)

---

## Notes

- This feature modifies 2 existing files only (no new files except tests)
- Changes are backward compatible (new field has default None)
- Contract tests are copied from specs/019-critic-metadata-passthrough/contracts/
- Total: 38 tasks
- Estimated code changes: ~50-100 lines (small, focused feature)
- Three-layer testing complete: contract (T010-T011), unit (T017-T024), integration (T031-T032)

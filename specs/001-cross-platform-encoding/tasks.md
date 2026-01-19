# Tasks: Cross-Platform Encoding Support for Logging

**Input**: Design documents from `/specs/001-cross-platform-encoding/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included - three-layer testing strategy per ADR-005 (unit + contract tests)

**Documentation**: ADR-011 required per FR-006. No user-facing guides needed (internal infrastructure).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| Internal refactor | Not required | Not required |
| New ADR | Required (ADR only) | Not required |

This feature is internal infrastructure (logging processor) - no user-facing guides needed.

---

## Phase 1: Setup

**Purpose**: Project initialization - no new dependencies, just file structure

- [x] T001 Verify branch `001-cross-platform-encoding` is checked out and up to date with develop

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before user story work

**⚠️ CRITICAL**: The processor implementation is foundational - US1/US2 depend on it

- [x] T002 [P] Create EncodingSafeProcessor class with REPLACEMENTS constant in src/gepa_adk/utils/encoding.py
- [x] T003 [P] Implement `__init__` method with encoding detection in src/gepa_adk/utils/encoding.py
- [x] T004 Implement `_sanitize_string` method with smart replacements in src/gepa_adk/utils/encoding.py
- [x] T005 Implement `_sanitize_value` method for recursive handling in src/gepa_adk/utils/encoding.py
- [x] T006 Implement `_sanitize_dict` method in src/gepa_adk/utils/encoding.py
- [x] T007 Implement `__call__` method (structlog processor protocol) in src/gepa_adk/utils/encoding.py
- [x] T008 Export EncodingSafeProcessor in src/gepa_adk/utils/__init__.py
- [x] T008a Identify logging configuration entry point (api.py or similar) and document in plan.md
- [x] T008b Add EncodingSafeProcessor to structlog processor chain before ConsoleRenderer (documented in ADR-011, user integration)

**Checkpoint**: EncodingSafeProcessor is implemented and integrated - testing can begin

---

## Phase 3: User Story 1 - Windows Developer Running Evolution (Priority: P1) 🎯 MVP

**Goal**: Windows users can run evolution loops without UnicodeEncodeError when LLM outputs contain smart quotes, em dashes, non-breaking hyphens

**Independent Test**: Run processor with cp1252 encoding and strings containing U+2011, U+2018/U+2019, U+2014 - no exceptions raised

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation integration**

- [x] T009 [P] [US1] Create unit test file tests/unit/test_encoding.py with test fixtures
- [x] T010 [P] [US1] Add unit test for smart quote sanitization (\u2018, \u2019, \u201c, \u201d) in tests/unit/test_encoding.py
- [x] T011 [P] [US1] Add unit test for em dash sanitization (\u2014) in tests/unit/test_encoding.py
- [x] T012 [P] [US1] Add unit test for non-breaking hyphen sanitization (\u2011) in tests/unit/test_encoding.py
- [x] T013 [P] [US1] Add unit test for en dash sanitization (\u2013) in tests/unit/test_encoding.py
- [x] T014 [P] [US1] Add unit test for ellipsis sanitization (\u2026) in tests/unit/test_encoding.py
- [x] T015 [P] [US1] Add unit test for non-breaking space sanitization (\u00a0) in tests/unit/test_encoding.py
- [x] T016 [P] [US1] Add unit test for unmapped unencodable character fallback (cp1252 simulation) in tests/unit/test_encoding.py
- [x] T016a [P] [US1] Add unit test for null byte handling in tests/unit/test_encoding.py
- [x] T016b [P] [US1] Add unit test for control character handling in tests/unit/test_encoding.py
- [x] T016c [P] [US1] Add unit test for extremely long string (10KB+) in tests/unit/test_encoding.py
- [x] T016d [P] [US1] Add unit test for encoding detection fallback (sys.stdout.encoding=None) in tests/unit/test_encoding.py
- [x] T017 [P] [US1] Create contract test file tests/contracts/test_encoding_contract.py
- [x] T018 [P] [US1] Add contract test for processor protocol compliance (callable, returns EventDict) in tests/contracts/test_encoding_contract.py
- [x] T019 [P] [US1] Add contract test for idempotence in tests/contracts/test_encoding_contract.py

### Implementation for User Story 1

- [x] T020 [US1] Verify all unit tests pass for character sanitization
- [x] T021 [US1] Verify all contract tests pass for protocol compliance

**Checkpoint**: US1 complete - Windows encoding crashes are prevented by the processor

---

## Phase 4: User Story 2 - Consistent Logging Across Platforms (Priority: P2)

**Goal**: Library behaves consistently on Windows (cp1252), macOS (UTF-8), and Linux (UTF-8) - same inputs produce same sanitized outputs

**Independent Test**: Same processor with different encoding values produces consistent safe output

### Tests for User Story 2

- [x] T022 [P] [US2] Add unit test for nested dict sanitization in tests/unit/test_encoding.py
- [x] T023 [P] [US2] Add unit test for list sanitization in tests/unit/test_encoding.py
- [x] T024 [P] [US2] Add unit test for tuple sanitization in tests/unit/test_encoding.py
- [x] T025 [P] [US2] Add unit test for type preservation (int, float, bool, None) in tests/unit/test_encoding.py
- [x] T026 [P] [US2] Add unit test for empty event dict handling in tests/unit/test_encoding.py
- [x] T027 [P] [US2] Add contract test for structlog pipeline integration in tests/contracts/test_encoding_contract.py
- [x] T027a [US2] Add integration test for real structlog console output in tests/integration/test_encoding_integration.py

### Implementation for User Story 2

- [x] T028 [US2] Verify all nested structure tests pass
- [x] T029 [US2] Verify structlog integration test passes

**Checkpoint**: US2 complete - processor works consistently across all platforms

---

## Phase 5: User Story 3 - Clear Documentation for Encoding Requirements (Priority: P3)

**Goal**: Contributors have clear guidance on encoding-safe logging via ADR-011

**Independent Test**: A developer can find ADR-011 and understand encoding requirements within 5 minutes

### Implementation for User Story 3

- [x] T030 [US3] Create ADR-011-cross-platform-encoding.md in docs/adr/ with decision context
- [x] T031 [US3] Add "Problem Statement" section to ADR-011 documenting Windows cp1252 issues
- [x] T032 [US3] Add "Decision" section to ADR-011 documenting EncodingSafeProcessor approach
- [x] T033 [US3] Add "Consequences" section to ADR-011 with character mapping table
- [x] T034 [US3] Add "Implementation" section to ADR-011 with processor chain position guidance
- [x] T035 [US3] Add cross-reference to ADR-008 (Structured Logging) in ADR-011

**Checkpoint**: US3 complete - encoding requirements are documented for contributors

---

## Phase 6: Verification & Cross-Cutting Concerns

**Purpose**: Final verification and cleanup

### Test Suite Verification

- [x] T036 Run full test suite with `pytest tests/unit/test_encoding.py tests/contracts/test_encoding_contract.py -v`
- [x] T037 Verify no ruff/linting errors with `ruff check src/gepa_adk/utils/encoding.py`

### Documentation Verification

- [x] T038 Verify ADR-011 follows ADR template format (matches existing ADRs)
- [x] T039 Verify `uv run mkdocs build` passes without warnings

### Cross-Cutting Tasks

- [x] T040 Add Google-style docstrings to EncodingSafeProcessor per ADR-010
- [x] T041 Review processor for edge cases (null bytes, extremely long strings, mixed content)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verify branch
- **Foundational (Phase 2)**: Core processor implementation - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - character sanitization tests
- **User Story 2 (Phase 4)**: Depends on Foundational - platform consistency tests
- **User Story 3 (Phase 5)**: No code dependencies - can run in parallel with US1/US2
- **Verification (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - Independent of US1
- **User Story 3 (P3)**: Can start after Foundational - Independent (documentation only)

### Within Each User Story

- Tests written and verified to fail before checking implementation
- Implementation already complete in Foundational phase
- Story "implementation" is verification that tests pass
- Documentation updates complete before story is marked done

### Parallel Opportunities

Within Foundational (Phase 2):
- T002, T003 can run in parallel (class + init)
- T004-T007 are sequential (method dependencies)

Within User Story 1 (Phase 3):
- All test tasks T009-T019 can run in parallel (different test cases)

Within User Story 2 (Phase 4):
- All test tasks T022-T027 can run in parallel (different test cases)

Within User Story 3 (Phase 5):
- T030-T035 are sequential (building ADR sections)

Cross-Story Parallelism:
- US1, US2, US3 can all run in parallel after Foundational completes

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all unit tests for US1 together:
Task: "Add unit test for smart quote sanitization in tests/unit/test_encoding.py"
Task: "Add unit test for em dash sanitization in tests/unit/test_encoding.py"
Task: "Add unit test for non-breaking hyphen sanitization in tests/unit/test_encoding.py"
Task: "Add unit test for en dash sanitization in tests/unit/test_encoding.py"
Task: "Add unit test for ellipsis sanitization in tests/unit/test_encoding.py"
Task: "Add unit test for non-breaking space sanitization in tests/unit/test_encoding.py"

# Launch all contract tests for US1 together:
Task: "Add contract test for processor protocol compliance in tests/contract/test_encoding_contract.py"
Task: "Add contract test for idempotence in tests/contract/test_encoding_contract.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify branch)
2. Complete Phase 2: Foundational (implement EncodingSafeProcessor)
3. Complete Phase 3: User Story 1 (character sanitization tests)
4. **STOP and VALIDATE**: Run tests, verify no UnicodeEncodeError
5. Can merge as MVP if needed

### Incremental Delivery

1. Complete Setup + Foundational → Processor implemented
2. Add User Story 1 → Test character sanitization → MVP ready
3. Add User Story 2 → Test cross-platform consistency → Full coverage
4. Add User Story 3 → ADR documentation → Complete feature
5. Each story adds confidence without breaking previous stories

### Single Developer Strategy

Recommended order for solo implementation:
1. T001 (setup)
2. T002-T008 (foundational - processor implementation)
3. T009-T021 (US1 - core tests)
4. T022-T029 (US2 - consistency tests)
5. T030-T035 (US3 - ADR)
6. T036-T041 (verification)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable
- Processor implementation is in Foundational phase (shared by all stories)
- User story "implementation" is primarily test verification
- Commit after each phase for easy rollback
- Run `pytest -v` after each user story phase
- Run `ruff check` before final verification

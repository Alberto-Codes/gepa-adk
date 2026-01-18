# Tasks: ADK Session State Template Substitution

**Input**: Design documents from `/specs/035-adk-session-template/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, architecture.md

**Tests**: Tests are included per Constitution Principle IV (Three-Layer Testing).

**Contract Test Exemption**: This feature modifies internal implementation without introducing new protocols or changing port interfaces. The `ReflectionFn` protocol signature remains unchanged. Per ADR-005, contract tests verify protocol compliance—since no protocols change, no contract tests are required.

**Documentation**: Per Constitution Principle VI, user-facing features MUST include documentation tasks within each user story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| New config option | Required (guides) | Recommended |

This feature modifies internal behavior but documents new template syntax for users.

---

## Phase 1: Setup

**Purpose**: Verify prerequisites and understand current implementation

- [ ] T001 Review current implementation in src/gepa_adk/engine/adk_reflection.py
- [ ] T002 [P] Verify ADK template syntax works with InMemorySessionService (manual test)
- [ ] T003 [P] Identify existing tests in tests/unit/engine/ that may need updates

---

## Phase 2: Foundational

**Purpose**: Create shared infrastructure needed by all user stories

- [ ] T004 Define REFLECTION_INSTRUCTION constant with `{component_text}` and `{trials}` placeholders in src/gepa_adk/engine/adk_reflection.py
- [ ] T005 Ensure JSON pre-serialization for `trials` session state value in src/gepa_adk/engine/adk_reflection.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Basic Template Substitution (Priority: P1) 🎯 MVP

**Goal**: Replace f-string user message construction with ADK `{key}` template placeholders for single placeholder substitution

**Independent Test**: Create agent with `{component_text}` placeholder, populate session state, verify substitution occurs

### Tests for User Story 1

- [ ] T006 [P] [US1] Unit test for single placeholder substitution in tests/unit/engine/test_adk_reflection_template.py
- [ ] T007 [P] [US1] Unit test for missing state key error handling in tests/unit/engine/test_adk_reflection_template.py

### Implementation for User Story 1

- [ ] T008 [US1] Modify `create_adk_reflection_fn()` to use templated instruction instead of f-string user message in src/gepa_adk/engine/adk_reflection.py
- [ ] T009 [US1] Update user message to simple trigger text (not data carrier) in src/gepa_adk/engine/adk_reflection.py
- [ ] T010 [US1] Add structured logging for template substitution in src/gepa_adk/engine/adk_reflection.py
- [ ] T011 [US1] Update docstrings for `create_adk_reflection_fn()` to document template usage in src/gepa_adk/engine/adk_reflection.py

**Checkpoint**: Single placeholder substitution works - can verify with unit tests

---

## Phase 4: User Story 2 - Multiple Placeholder Substitution (Priority: P1)

**Goal**: Ensure both `{component_text}` and `{trials}` placeholders are substituted correctly

**Independent Test**: Create agent with both placeholders, populate session state with both values, verify both substituted

### Tests for User Story 2

- [ ] T012 [P] [US2] Unit test for multiple placeholder substitution in tests/unit/engine/test_adk_reflection_template.py
- [ ] T013 [P] [US2] Unit test for partial state (one key missing) in tests/unit/engine/test_adk_reflection_template.py
- [ ] T014 [P] [US2] Unit test for non-string value serialization (dict/list to JSON) in tests/unit/engine/test_adk_reflection_template.py

### Implementation for User Story 2

- [ ] T015 [US2] Verify REFLECTION_INSTRUCTION contains both `{component_text}` and `{trials}` placeholders in src/gepa_adk/engine/adk_reflection.py
- [ ] T016 [US2] Ensure session state dict includes both keys in src/gepa_adk/engine/adk_reflection.py
- [ ] T017 [US2] Add error handling for partial state scenarios in src/gepa_adk/engine/adk_reflection.py

**Checkpoint**: Multiple placeholder substitution works - full reflection capability restored

---

## Phase 5: User Story 3 - Documentation (Priority: P2)

**Goal**: Document `{key}` template syntax for developers using reflection agents

**Independent Test**: A developer can follow the documentation to implement template substitution in a new agent

### Documentation for User Story 3

- [ ] T018 [P] [US3] Update docs/guides/reflection-prompts.md with `{key}` template syntax section
- [ ] T019 [P] [US3] Add code examples showing session state setup and placeholder usage in docs/guides/reflection-prompts.md
- [ ] T020 [P] [US3] Document optional `{key?}` syntax for graceful missing key handling in docs/guides/reflection-prompts.md
- [ ] T021 [US3] Add migration notes from f-string workaround to template syntax in docs/guides/reflection-prompts.md

**Checkpoint**: Documentation complete - developers can adopt template syntax

---

## Phase 6: Verification & Cross-Cutting Concerns

**Purpose**: Final verification, integration tests, and cleanup

### Integration Tests

- [ ] T022 [P] Integration test with Gemini model in tests/integration/test_reflection_template.py
- [ ] T023 [P] Integration test with Ollama model in tests/integration/test_reflection_template.py (if available)

### Documentation Build Verification

- [ ] T024 Verify `uv run mkdocs build` passes without warnings
- [ ] T025 Preview docs with `uv run mkdocs serve` and verify reflection-prompts guide renders correctly

### Cross-Cutting Tasks

- [ ] T026 Run full test suite to verify no regressions (`uv run pytest`)
- [ ] T027 Verify output equivalence: template-based vs f-string workaround produce same results
- [ ] T028 Close GitHub Issue #99 with implementation summary

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational; can run in parallel with US1 if needed
- **User Story 3 (Phase 5)**: Can run in parallel with US1/US2 (documentation)
- **Verification (Phase 6)**: Depends on US1 and US2 completion

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories - core implementation
- **User Story 2 (P1)**: Builds on US1 foundation but independently testable
- **User Story 3 (P2)**: No code dependencies - purely documentation

### Within Each User Story

- Tests SHOULD be written first (TDD approach)
- Implementation follows tests
- Documentation updates complete the story

### Parallel Opportunities

**Phase 1 (Setup)**:
- T002 and T003 can run in parallel

**Phase 3 (US1)**:
- T006 and T007 (tests) can run in parallel

**Phase 4 (US2)**:
- T012, T013, T014 (tests) can run in parallel

**Phase 5 (US3)**:
- T018, T019, T020 (docs) can run in parallel

**Phase 6 (Verification)**:
- T022 and T023 (integration tests) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for single placeholder substitution in tests/unit/engine/test_adk_reflection_template.py"
Task: "Unit test for missing state key error handling in tests/unit/engine/test_adk_reflection_template.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (single placeholder)
4. **STOP and VALIDATE**: Run unit tests, verify template substitution works
5. Can deploy/merge if minimal functionality sufficient

### Full Feature Delivery

1. Complete Setup + Foundational → Foundation ready
2. Complete User Story 1 → Single placeholder works (MVP!)
3. Complete User Story 2 → Multiple placeholders work (full functionality)
4. Complete User Story 3 → Documentation complete (adoption ready)
5. Complete Verification → Integration tested, issue closed

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 + User Story 2 (implementation)
   - Developer B: User Story 3 (documentation)
3. All converge for Phase 6 verification

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- This feature has minimal scope: one file modified (`adk_reflection.py`), one guide updated
- Existing functionality preserved via backward compatibility (no template placeholders = no substitution)
- Run `uv run mkdocs build` before PR to verify docs build cleanly

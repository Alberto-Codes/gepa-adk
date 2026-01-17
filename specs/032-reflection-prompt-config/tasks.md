# Tasks: Reflection Prompt Configuration

**Input**: Design documents from `/specs/032-reflection-prompt-config/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md, architecture.md

**Tests**: Tests are included per Constitution Principle IV (Three-Layer Testing) and plan.md requirements.

**Documentation**: This feature adds a new public config option and requires documentation updates per Constitution Principle VI.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| New config option | Required (guides) | Recommended |

**Static pages** (manual updates): `docs/guides/reflection-prompts.md` (new)
**Auto-generated** (no manual updates): `docs/reference/` (from docstrings via mkdocstrings)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No setup needed - this feature modifies existing files only

*No tasks in this phase - all infrastructure already exists*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Export DEFAULT_PROMPT_TEMPLATE for users to extend (FR-005)

**⚠️ CRITICAL**: This export is needed before US1 can be tested (users need to reference default)

- [x] T001 Add `DEFAULT_PROMPT_TEMPLATE` to `__all__` list in src/gepa_adk/engine/proposer.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Custom Reflection Prompt Configuration (Priority: P1) 🎯 MVP

**Goal**: Enable users to configure custom reflection prompts via `EvolutionConfig.reflection_prompt`

**Independent Test**: Create an `EvolutionConfig` with a custom `reflection_prompt` value and verify the proposer uses it during evolution

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T002 [P] [US1] Unit test for `reflection_prompt` field acceptance in tests/unit/test_config.py
- [x] T003 [P] [US1] Integration test for custom prompt usage in tests/integration/test_reflection_prompt.py

### Implementation for User Story 1

- [x] T004 [US1] Add `reflection_prompt: str | None = None` field to `EvolutionConfig` in src/gepa_adk/domain/models.py
- [x] T005 [US1] Add docstring for `reflection_prompt` field explaining placeholders in src/gepa_adk/domain/models.py
- [x] T006 [P] [US1] Add `reflection_prompt` parameter to `ADKAdapter.__init__()` in src/gepa_adk/adapters/adk_adapter.py
- [x] T007 [P] [US1] Add `reflection_prompt` parameter to `MultiAgentAdapter.__init__()` in src/gepa_adk/adapters/multi_agent.py
- [x] T008 [US1] Pass `reflection_prompt` to `AsyncReflectiveMutationProposer` in ADKAdapter in src/gepa_adk/adapters/adk_adapter.py
- [x] T009 [US1] Pass `reflection_prompt` to `AsyncReflectiveMutationProposer` in MultiAgentAdapter in src/gepa_adk/adapters/multi_agent.py
- [x] T010 [US1] Wire `config.reflection_prompt` through `evolve()` to ADKAdapter in src/gepa_adk/api.py
- [x] T011 [US1] Wire `config.reflection_prompt` through `evolve_group()` to MultiAgentAdapter in src/gepa_adk/api.py

**Checkpoint**: User Story 1 complete - custom prompts can be configured and used

---

## Phase 4: User Story 2 - Placeholder Validation Warnings (Priority: P2)

**Goal**: Warn users when custom prompts are missing required placeholders

**Independent Test**: Create config with prompt missing `{current_instruction}` or `{feedback_examples}` and verify warning is logged

### Tests for User Story 2

- [x] T012 [P] [US2] Unit test for missing `{current_instruction}` warning in tests/unit/test_config.py
- [x] T013 [P] [US2] Unit test for missing `{feedback_examples}` warning in tests/unit/test_config.py
- [x] T014 [P] [US2] Unit test for valid prompt (both placeholders) produces no warning in tests/unit/test_config.py
- [x] T015 [P] [US2] Unit test for empty string treated as None in tests/unit/test_config.py

### Implementation for User Story 2

- [x] T016 [US2] Add `__post_init__` validation for `reflection_prompt` placeholders in src/gepa_adk/domain/models.py
- [x] T017 [US2] Add structlog warning when `{current_instruction}` placeholder is missing in src/gepa_adk/domain/models.py
- [x] T018 [US2] Add structlog warning when `{feedback_examples}` placeholder is missing in src/gepa_adk/domain/models.py
- [x] T019 [US2] Add info log and convert empty string to None in `__post_init__` in src/gepa_adk/domain/models.py

**Checkpoint**: User Story 2 complete - validation warnings working

---

## Phase 5: User Story 3 - Prompt Customization Documentation (Priority: P2)

**Goal**: Provide comprehensive documentation for creating effective reflection prompts

**Independent Test**: Review documentation for placeholder docs, prompt guidelines, and example prompts

### Implementation for User Story 3

- [x] T020 [US3] Create docs/guides/reflection-prompts.md with section on available placeholders ({current_instruction}, {feedback_examples})
- [x] T021 [US3] Add prompt design guidelines section to docs/guides/reflection-prompts.md
- [x] T022 [US3] Add example prompts section (JSON output, minimal/fast, chain-of-thought) to docs/guides/reflection-prompts.md
- [x] T023 [US3] Add section on extending DEFAULT_PROMPT_TEMPLATE to docs/guides/reflection-prompts.md
- [x] T024 [P] [US3] Update docs/getting-started.md to reference new reflection-prompts.md guide
- [x] T025 [P] [US3] Add docs/guides/reflection-prompts.md to mkdocs.yml navigation

**Checkpoint**: User Story 3 complete - documentation available

---

## Phase 6: User Story 4 - Model Selection Guidance (Priority: P3)

**Goal**: Help users choose appropriate reflection models

**Independent Test**: Review documentation for token budget, complexity, and cost guidance

### Implementation for User Story 4

- [x] T026 [US4] Add model selection section to docs/guides/reflection-prompts.md with token budget considerations
- [x] T027 [US4] Add complexity guidance (matching model capability to task) to docs/guides/reflection-prompts.md
- [x] T028 [US4] Add cost vs quality tradeoffs section covering local, cloud-cheap, cloud-premium to docs/guides/reflection-prompts.md

**Checkpoint**: User Story 4 complete - model selection guidance available

---

## Phase 7: Verification & Cross-Cutting Concerns

**Purpose**: Final verification and documentation build

### Documentation Build Verification (REQUIRED)

- [x] T029 Verify `uv run mkdocs build` passes without warnings
- [x] T030 Preview docs with `uv run mkdocs serve` and verify reflection-prompts.md renders correctly

### Cross-Cutting Tasks

- [x] T031 Run full test suite with `uv run pytest` to verify no regressions
- [x] T032 Verify quickstart.md examples from specs/032-reflection-prompt-config/quickstart.md work

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks - skipped
- **Foundational (Phase 2)**: Can start immediately - exports DEFAULT_PROMPT_TEMPLATE
- **User Story 1 (Phase 3)**: Depends on Phase 2 - core functionality
- **User Story 2 (Phase 4)**: Depends on Phase 3 (T004) - validation adds to config
- **User Story 3 (Phase 5)**: Can start after Phase 2 - documentation independent
- **User Story 4 (Phase 6)**: Depends on Phase 5 - extends same doc file
- **Verification (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 T004 (reflection_prompt field must exist) - but can run tests in parallel
- **User Story 3 (P2)**: Can start after Foundational - documentation is independent of implementation
- **User Story 4 (P3)**: Depends on US3 (extends same file) - otherwise independent

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Domain model changes before API/adapter wiring
- Core implementation before integration
- Documentation updates complete before story is done

### Parallel Opportunities

**Phase 3 (US1):**
- T002 and T003 (tests) can run in parallel
- T006 and T007 (adapter params) can run in parallel

**Phase 4 (US2):**
- T012, T013, T014, T015 (tests) can all run in parallel

**Phase 5 (US3):**
- T024 and T025 (doc updates) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for reflection_prompt field acceptance in tests/unit/test_config.py"
Task: "Integration test for custom prompt usage in tests/integration/test_reflection_prompt.py"

# Launch adapter param tasks together:
Task: "Add reflection_prompt parameter to ADKAdapter.__init__() in src/gepa_adk/adapters/adk_adapter.py"
Task: "Add reflection_prompt parameter to MultiAgentAdapter.__init__() in src/gepa_adk/adapters/multi_agent.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001)
2. Complete Phase 3: User Story 1 (T002-T011)
3. **STOP and VALIDATE**: Test custom prompt configuration works
4. Users can now configure custom prompts

### Incremental Delivery

1. Phase 2 → Foundation ready (DEFAULT_PROMPT_TEMPLATE exported)
2. Add User Story 1 → Test independently → Core feature works (MVP!)
3. Add User Story 2 → Test independently → Validation warnings work
4. Add User Story 3 → Documentation available
5. Add User Story 4 → Model guidance complete
6. Phase 7 → Final verification

### Parallel Team Strategy

With multiple developers:

1. All: Complete Phase 2 (1 task)
2. Once Foundational is done:
   - Developer A: User Story 1 (implementation)
   - Developer B: User Story 3 (documentation)
3. After US1 complete:
   - Developer A: User Story 2 (validation)
   - Developer B: User Story 4 (extends docs)

---

## Architecture Compliance

Per architecture.md hexagonal view:

| Layer | Files Modified | Tasks |
|-------|---------------|-------|
| domain/ | models.py | T004, T005, T016-T019 |
| api.py | api.py | T010, T011 |
| adapters/ | adk_adapter.py, multi_agent.py | T006-T009 |
| engine/ | proposer.py | T001 |

Config flow respects: domain → api → adapters → engine (no layer violations)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Run `uv run mkdocs build` before PR to verify docs build cleanly
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

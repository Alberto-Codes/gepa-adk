# Tasks: ADK Ollama Reflection

**Input**: Design documents from `/specs/034-adk-ollama-reflection/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Constitution IV requires three-layer testing (contracts, unit, integration). Tests included per user story.

**Documentation**: Per Constitution VI, this feature adds a new config option (`inject_schema_guidance`) which requires guide updates and example updates.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Key Principle: Test First, Minimal Changes

Per research.md decisions:
- Leverage existing `extract_final_output()` (PR #96 already handles ADK thought filtering)
- Test with Ollama first before assuming existing extraction is broken
- Only enhance text-level filtering if testing reveals actual problems

---

## Phase 1: Setup

**Purpose**: Verify existing infrastructure and establish baseline

- [X] T001 Verify branch `034-adk-ollama-reflection` is checked out and up to date with develop
- [X] T002 Run existing test suite to confirm baseline (`uv run pytest -n auto`)
- [X] T003 [P] Review existing `create_adk_reflection_fn()` in src/gepa_adk/engine/proposer.py (lines 107-394)
- [X] T004 [P] Review existing extraction logic in src/gepa_adk/engine/proposer.py (lines 283-382)

---

## Phase 2: Foundational (Shared Infrastructure)

**Purpose**: Add helper functions that all user stories depend on

**⚠️ CRITICAL**: User story implementation requires these helpers

- [X] T005 Add `build_schema_guidance()` helper function in src/gepa_adk/engine/proposer.py
- [X] T006 Add `should_inject_schema_guidance()` helper function in src/gepa_adk/engine/proposer.py
- [X] T007 Add unit tests for helper functions in tests/unit/engine/test_proposer.py

**Checkpoint**: Helper functions ready - user story implementation can begin

---

## Phase 3: User Story 1 - Clean Instruction Extraction (Priority: P1) 🎯 MVP

**Goal**: ADK reflection agents with Ollama models extract clean, usable instructions

**Independent Test**: Configure an ADK LlmAgent with Ollama as reflection_agent, run evolution cycle, verify extracted instruction is clean (not reasoning text)

### Tests for User Story 1

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [X] T008 [P] [US1] Contract test for reflection function behavior in tests/contracts/test_adk_reflection_contract.py
- [X] T009 [P] [US1] Unit test for extraction with mixed reasoning/instruction content in tests/unit/engine/test_proposer.py
- [X] T010 [P] [US1] Integration test with mock Ollama response in tests/integration/engine/test_proposer_integration.py

### Implementation for User Story 1

- [X] T011 [US1] Test existing extraction with Ollama-style responses (manual verification before code changes)
- [X] T012 [US1] Add `inject_schema_guidance` parameter to `create_adk_reflection_fn()` signature in src/gepa_adk/engine/proposer.py
- [X] T013 [US1] Implement schema guidance injection into session state in src/gepa_adk/engine/proposer.py
- [X] T014 [US1] Add structured logging for schema injection in src/gepa_adk/engine/proposer.py
- [X] T015 [US1] Update docstrings for modified functions in src/gepa_adk/engine/proposer.py

### Documentation for User Story 1

- [X] T016 [P] [US1] Update docs/guides/multi-agent.md with reflection_agent configuration for Ollama
- [X] T017 [P] [US1] Update examples/multi_agent.py with Ollama reflection agent example

**Checkpoint**: US1 complete - ADK reflection agents work with Ollama using schema guidance injection

---

## Phase 4: User Story 2 - Schema-in-Prompt Fallback (Priority: P2)

**Goal**: System automatically injects JSON schema guidance for non-compliant models

**Independent Test**: Configure reflection_agent with output_schema on Ollama, verify prompt contains schema guidance

### Tests for User Story 2

- [X] T018 [P] [US2] Unit test for schema detection logic (Ollama vs Gemini) in tests/unit/engine/test_proposer.py
- [X] T019 [P] [US2] Unit test for session state modification in tests/unit/engine/test_proposer.py

### Implementation for User Story 2

- [X] T020 [US2] Implement model detection logic in `should_inject_schema_guidance()` in src/gepa_adk/engine/proposer.py
- [X] T021 [US2] Add JSON extraction attempt before existing text fallbacks (optional - only if T011 testing reveals need) in src/gepa_adk/engine/proposer.py
- [X] T022 [US2] Wire schema guidance through ADKAdapter if needed in src/gepa_adk/adapters/adk_adapter.py

### Documentation for User Story 2

- [X] T023 [P] [US2] Document output_schema behavior with Ollama in docs/guides/multi-agent.md
- [X] T024 [P] [US2] Add troubleshooting section for schema guidance in docs/guides/multi-agent.md

**Checkpoint**: US2 complete - Schema guidance automatically injected for Ollama models

---

## Phase 5: User Story 3 - Consistent ADK Patterns (Priority: P3)

**Goal**: Users can use ADK patterns consistently without falling back to direct LiteLLM

**Independent Test**: Run complete evolution cycle with ADK reflection agent, verify no fallback to LiteLLM path

### Tests for User Story 3

- [X] T025 [P] [US3] Integration test for full evolution cycle with ADK reflection in tests/integration/engine/test_proposer_integration.py
- [X] T026 [P] [US3] Verify ADK-style logging patterns in tests/integration/engine/test_proposer_integration.py

### Implementation for User Story 3

- [X] T027 [US3] Ensure ADK Runner is used consistently (verify no direct LiteLLM fallback) in src/gepa_adk/engine/proposer.py
- [X] T028 [US3] Add observability logging for ADK reflection path in src/gepa_adk/engine/proposer.py

### Documentation for User Story 3

- [X] T029 [P] [US3] Document ADK vs LiteLLM reflection paths in docs/guides/multi-agent.md
- [X] T030 [P] [US3] Add logging interpretation guide for debugging reflection issues

**Checkpoint**: US3 complete - ADK patterns used consistently throughout evolution

---

## Phase 6: Verification & Cross-Cutting Concerns

**Purpose**: Final verification and quality checks

### Documentation Build Verification (REQUIRED)

- [ ] T031 Verify `uv run mkdocs build` passes without warnings
- [ ] T032 Preview docs with `uv run mkdocs serve` and verify changes render correctly

### Cross-Cutting Tasks

- [X] T033 Run full test suite (`uv run pytest -n auto`)
- [X] T034 Run type checking (`uv run ty check`)
- [X] T035 Run linting (`uv run ruff check`)
- [ ] T036 Validate quickstart.md scenarios manually
- [X] T037 Code review for constitution compliance (hexagonal architecture, async-first, observability)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verify baseline
- **Foundational (Phase 2)**: Depends on Setup - adds helper functions
- **User Story 1 (Phase 3)**: Depends on Foundational - MVP delivery
- **User Story 2 (Phase 4)**: Depends on US1 (builds on schema injection)
- **User Story 3 (Phase 5)**: Depends on US1 (verifies consistent patterns)
- **Verification (Phase 6)**: Depends on all desired user stories

### User Story Dependencies

- **User Story 1 (P1)**: Foundation only - Can deliver as MVP
- **User Story 2 (P2)**: Builds on US1's schema injection infrastructure
- **User Story 3 (P3)**: Builds on US1's ADK reflection implementation

### Parallel Opportunities

Within each phase, tasks marked [P] can run in parallel:
- T003, T004 (Setup reviews)
- T008, T009, T010 (US1 tests)
- T016, T017 (US1 docs)
- T018, T019 (US2 tests)
- T023, T024 (US2 docs)
- T025, T026 (US3 tests)
- T029, T030 (US3 docs)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for US1 together:
Task: "Contract test for reflection function behavior in tests/contracts/test_adk_reflection_contract.py"
Task: "Unit test for extraction with mixed reasoning/instruction content in tests/unit/engine/test_proposer.py"
Task: "Integration test with mock Ollama response in tests/integration/engine/test_proposer_integration.py"

# After tests written, launch docs in parallel with implementation:
Task: "Update docs/guides/multi-agent.md with reflection_agent configuration for Ollama"
Task: "Update examples/multi_agent.py with Ollama reflection agent example"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify baseline)
2. Complete Phase 2: Foundational (helper functions)
3. Complete Phase 3: User Story 1 (schema injection + docs)
4. **STOP and VALIDATE**: Test with real Ollama model
5. If working, can deploy/demo as MVP

### Key Decision Points

- **After T011**: If existing extraction works fine with Ollama, skip JSON extraction enhancement (T021)
- **After US1 testing**: If schema guidance solves the problem, US2/US3 may need minimal work
- **Per research.md**: Only add complexity if testing reveals actual problems

### Incremental Delivery

1. Setup + Foundational → Helpers ready
2. Add US1 → Test with Ollama → MVP!
3. Add US2 → Enhanced detection/fallback
4. Add US3 → Consistent patterns verified
5. Each story adds value without breaking previous

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Test first: Write tests, verify they fail, then implement
- Minimal changes: Per research.md, leverage existing infrastructure
- Constitution compliance: Hexagonal architecture, async-first, three-layer testing, observability
- Documentation: Update guides and examples as part of each user story (not deferred)

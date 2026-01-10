# Tasks: AsyncReflectiveMutationProposer

**Input**: Design documents from `/specs/007-async-mutation-proposer/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Three-layer testing required per Constitution (ADR-005)

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US#]**: Which user story this task belongs to
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project structure and module initialization

- [X] T001 Create engine module `__init__.py` export for proposer in `src/gepa_adk/engine/__init__.py`
- [X] T002 [P] Create test directory structure: `tests/unit/engine/`, `tests/contracts/engine/`
- [X] T003 [P] Verify litellm dependency installed via `uv pip list | grep litellm`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Base infrastructure required before any user story implementation

**⚠️ CRITICAL**: User story work cannot begin until this phase is complete

- [X] T004 Create proposer module skeleton in `src/gepa_adk/engine/proposer.py` with class stub and docstring
- [X] T005 Define type aliases (ReflectiveDataset, ProposalResult) in `src/gepa_adk/engine/proposer.py`
- [X] T006 Implement `__init__` with validation (model non-empty, temperature 0.0-2.0, max_tokens > 0) in `src/gepa_adk/engine/proposer.py`
- [X] T007 Define DEFAULT_PROMPT_TEMPLATE constant in `src/gepa_adk/engine/proposer.py`

**Checkpoint**: Class instantiable with valid configuration, validation errors raised for invalid inputs

---

## Phase 3: User Story 1 - Generate Instruction Mutations (Priority: P1) 🎯 MVP

**Goal**: Proposer generates improved instruction text via LLM reflection when given feedback

**Independent Test**: Call `await proposer.propose(...)` with mock feedback → returns mutated instruction dict

### Tests for User Story 1

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [X] T008 [P] [US1] Contract test: propose returns dict with mutated text given valid input in `tests/contracts/engine/test_proposer_contracts.py`
- [X] T009 [P] [US1] Contract test: propose uses configured model for LLM calls in `tests/contracts/engine/test_proposer_contracts.py`
- [X] T010 [P] [US1] Unit test: `_build_messages` creates correct message structure in `tests/unit/engine/test_proposer.py`
- [X] T011 [P] [US1] Unit test: `_format_feedback` formats feedback examples as text in `tests/unit/engine/test_proposer.py`

### Implementation for User Story 1

- [X] T012 [US1] Implement `_format_feedback` method to convert feedback list to formatted string in `src/gepa_adk/engine/proposer.py`
- [X] T013 [US1] Implement `_build_messages` method to create LLM message list in `src/gepa_adk/engine/proposer.py`
- [X] T014 [US1] Implement core `propose` method: iterate components, build messages, call LLM in `src/gepa_adk/engine/proposer.py`
- [X] T015 [US1] Add response extraction: get content from `response.choices[0].message.content` in `src/gepa_adk/engine/proposer.py`
- [X] T016 [US1] Handle custom prompt template substitution with {current_instruction} and {feedback_examples} placeholders
- [X] T016a [US1] Add warning log if custom prompt_template missing required placeholders (use structlog)

**Checkpoint**: User Story 1 complete - proposer generates mutations with mocked LLM responses

---

## Phase 4: User Story 2 - Async LiteLLM Integration (Priority: P2)

**Goal**: Proposer calls `litellm.acompletion()` asynchronously without blocking

**Independent Test**: Mock `litellm.acompletion`, verify it's awaited with correct model/messages/params

### Tests for User Story 2

- [X] T017 [P] [US2] Contract test: propose calls `litellm.acompletion` (not sync completion) in `tests/contracts/engine/test_proposer_contracts.py`
- [X] T018 [P] [US2] Contract test: propose passes model, temperature, max_tokens to acompletion in `tests/contracts/engine/test_proposer_contracts.py`
- [X] T019 [P] [US2] Unit test: concurrent propose calls execute without blocking in `tests/unit/engine/test_proposer.py`

### Implementation for User Story 2

- [X] T020 [US2] Add `from litellm import acompletion` import to proposer module
- [X] T021 [US2] Wire `propose` to call `await acompletion(model=self.model, messages=..., temperature=..., max_tokens=...)` in `src/gepa_adk/engine/proposer.py`
- [X] T022 [US2] Verify async behavior: no sync/async bridging, pure async flow

**Checkpoint**: User Story 2 complete - proposer makes real async LLM calls

---

## Phase 5: User Story 3 - Handle Empty Reflective Dataset (Priority: P3)

**Goal**: Proposer returns `None` immediately when no feedback available (no LLM calls)

**Independent Test**: Call propose with empty dataset → returns None, verify acompletion never called

### Tests for User Story 3

- [X] T023 [P] [US3] Contract test: propose returns None for empty dict `{}` in `tests/contracts/engine/test_proposer_contracts.py`
- [X] T024 [P] [US3] Contract test: propose returns None when component has empty list `[]` in `tests/contracts/engine/test_proposer_contracts.py`
- [X] T025 [P] [US3] Contract test: no LLM calls made when returning None (cost optimization) in `tests/contracts/engine/test_proposer_contracts.py`
- [X] T026 [P] [US3] Unit test: performance - None returned within 10ms for empty dataset in `tests/unit/engine/test_proposer.py`

### Implementation for User Story 3

- [X] T027 [US3] Add early return `None` check at start of `propose` for empty reflective_dataset
- [X] T028 [US3] Add check: skip component if not in reflective_dataset or has empty feedback list
- [X] T029 [US3] Return `None` if no components had valid feedback after iteration

**Checkpoint**: User Story 3 complete - empty datasets handled efficiently without API calls

---

## Phase 6: Edge Cases & Error Handling

**Purpose**: Robustness per spec edge cases and contract guarantees

### Tests for Edge Cases

- [X] T030 [P] Contract test: empty LLM response returns original text in `tests/contracts/engine/test_proposer_contracts.py`
- [X] T031 [P] Contract test: None LLM content returns original text in `tests/contracts/engine/test_proposer_contracts.py`
- [X] T032 [P] Contract test: component not in candidate is skipped silently in `tests/contracts/engine/test_proposer_contracts.py`
- [X] T033 [P] Contract test: LiteLLM exceptions propagate unchanged (fail-fast) in `tests/contracts/engine/test_proposer_contracts.py`

### Implementation for Edge Cases

- [X] T034 Handle empty/whitespace/None LLM response by returning original candidate text
- [X] T035 Skip components_to_update entries that don't exist in candidate dict
- [X] T036 Ensure LiteLLM exceptions (AuthenticationError, RateLimitError, APIError) propagate unchanged

**Checkpoint**: All edge cases handled per contract guarantees

---

## Phase 7: Polish & Documentation

**Purpose**: Final cleanup and validation

- [ ] T037 [P] Add Google-style docstrings to all public methods per ADR-010
- [ ] T038 [P] Update `src/gepa_adk/engine/__init__.py` to export `AsyncReflectiveMutationProposer`
- [ ] T039 Run `uv run ruff check --fix` and `uv run ruff format` on proposer module
- [ ] T040 Run `uv run ty check` to verify type annotations
- [ ] T041 Run full test suite `uv run pytest -n auto` - all tests must pass
- [ ] T042 Validate quickstart.md examples work (manual or scripted check)

---

## Phase 8: Integration Tests (CI-Only) 🐢

**Purpose**: Real LLM calls per Constitution IV (Three-Layer Testing)

**⚠️ NOTE**: These tests make real API calls - run only in CI or manually with `@pytest.mark.slow`

- [ ] T043 [P] Create `tests/integration/engine/test_proposer_integration.py` with `@pytest.mark.slow` markers
- [ ] T044 [P] Integration test: propose returns valid mutation with real Ollama call (`ollama/gpt-oss:20b`)
- [ ] T045 [P] Integration test: propose handles real LLM empty/error responses gracefully
- [ ] T046 Integration test: verify Gemini model works (`gemini/gemini-2.5-flash`) - requires API key

**Checkpoint**: Three-layer testing complete per Constitution IV

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ────────────────► Phase 2: Foundational ────┬──► Phase 3: US1 (P1) MVP
                                         │                 ├──► Phase 4: US2 (P2)
                                         │                 └──► Phase 5: US3 (P3)
                                         │                              │
                                         └──────────────────────────────┴──► Phase 6: Edge Cases
                                                                                      │
                                                                                      ▼
                                                                              Phase 7: Polish
                                                                                      │
                                                                                      ▼
                                                                         Phase 8: Integration (CI)
```

### User Story Independence

| Story | Can Start After | Dependencies |
|-------|-----------------|--------------|
| US1 (P1) | Phase 2 complete | None - core functionality |
| US2 (P2) | Phase 2 complete | Integrates with US1 but testable independently via mocks |
| US3 (P3) | Phase 2 complete | Independent - only checks dataset before calling LLM |

### Parallel Opportunities per Phase

**Phase 1**:
- T002 and T003 can run in parallel

**Phase 3 (US1 Tests)**:
- T008, T009, T010, T011 can all run in parallel (different test functions)

**Phase 4 (US2 Tests)**:
- T017, T018, T019 can all run in parallel

**Phase 5 (US3 Tests)**:
- T023, T024, T025, T026 can all run in parallel

**Phase 6 (Edge Case Tests)**:
- T030, T031, T032, T033 can all run in parallel

**Phase 7**:
- T037 and T038 can run in parallel

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: User Story 1 (T008-T016)
4. **STOP & VALIDATE**: Run `uv run pytest tests/unit/engine/test_proposer.py tests/contracts/engine/test_proposer_contracts.py`
5. MVP ready - proposer generates mutations with mocked LLM

### Incremental Delivery

1. Setup + Foundational → Class structure ready
2. User Story 1 → Mutation generation works (mocked) → **MVP!**
3. User Story 2 → Real async LLM integration
4. User Story 3 → Empty dataset optimization
5. Edge Cases → Robust error handling
6. Polish → Production ready

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 47 |
| **Setup Tasks** | 3 |
| **Foundational Tasks** | 4 |
| **US1 Tasks** | 10 (4 tests + 6 impl) |
| **US2 Tasks** | 6 (3 tests + 3 impl) |
| **US3 Tasks** | 7 (4 tests + 3 impl) |
| **Edge Case Tasks** | 7 (4 tests + 3 impl) |
| **Polish Tasks** | 6 |
| **Integration Tasks** | 4 (CI-only) |
| **Parallel Opportunities** | 25 tasks marked [P] |
| **MVP Scope** | T001-T016a (17 tasks) |

### Files Created/Modified

| File | Action |
|------|--------|
| `src/gepa_adk/engine/proposer.py` | CREATE |
| `src/gepa_adk/engine/__init__.py` | MODIFY (add export) |
| `tests/unit/engine/test_proposer.py` | CREATE |
| `tests/contracts/engine/test_proposer_contracts.py` | CREATE |
| `tests/integration/engine/test_proposer_integration.py` | CREATE (CI-only) |

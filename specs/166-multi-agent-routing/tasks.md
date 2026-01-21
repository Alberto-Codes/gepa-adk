# Tasks: Multi-Agent Component Routing

**Input**: Design documents from `/specs/166-multi-agent-routing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED per constitution (Three-Layer Testing). Use pytest-mock for mocking.

**Documentation**: Per Constitution Principle VI, this is a breaking API change requiring docs/ and examples/ updates.

**Code Style**: Follow `.github/instructions/python.instructions.md` (Google style, TACOS docstrings) and `.github/instructions/pytest.instructions.md`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Documentation Scope (Constitution VI)

| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| Breaking change | Required + migration | Required |

This feature is a **breaking API change** (0.2.x → 0.3.x), requiring:
- Update to `docs/guides/multi-agent.md`
- New example in `examples/multi_agent_component_demo.py`

---

## Phase 1: Setup

**Purpose**: Verify prerequisites and prepare for implementation

- [ ] T001 Verify ComponentSpec and QualifiedComponentName types exist in src/gepa_adk/domain/types.py
- [ ] T002 Verify ComponentHandlerRegistry and get_handler exist in src/gepa_adk/adapters/component_handlers.py
- [ ] T003 [P] Add ComponentsMapping type alias to src/gepa_adk/domain/types.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add RestoreError exception that all user stories depend on

**⚠️ CRITICAL**: User story implementation cannot begin until this phase is complete

- [ ] T004 Add RestoreError exception class to src/gepa_adk/domain/exceptions.py with errors attribute for aggregated failures
- [ ] T005 [P] Add unit test for RestoreError in tests/unit/domain/test_exceptions.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Route Components to Correct Agents (Priority: P1) 🎯 MVP

**Goal**: Enable routing component updates to the correct agent based on qualified component names (dot notation per ADR-012)

**Independent Test**: Provide multi-agent setup with per-agent component mappings, verify candidates are applied to correct agents only

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T006 [P] [US1] Unit test for _apply_candidate routing in tests/unit/adapters/test_multi_agent_routing.py
- [ ] T007 [P] [US1] Unit test for _validate_components in tests/unit/adapters/test_multi_agent_routing.py
- [ ] T008 [P] [US1] Unit test for validation error when unknown agent in components in tests/unit/adapters/test_multi_agent_routing.py
- [ ] T009 [P] [US1] Unit test for validation error when unknown component handler in tests/unit/adapters/test_multi_agent_routing.py
- [ ] T010 [P] [US1] Unit test for validation error when agent missing from components mapping in tests/unit/adapters/test_multi_agent_routing.py
- [ ] T010a [P] [US1] Unit test for empty component list behavior (agent excluded from evolution) in tests/unit/adapters/test_multi_agent_routing.py

### Implementation for User Story 1

- [ ] T011 [US1] Modify MultiAgentAdapter.__init__ to accept agents as dict[str, LlmAgent] and require components parameter in src/gepa_adk/adapters/multi_agent.py
- [ ] T012 [US1] Add _validate_components method to MultiAgentAdapter for fail-fast validation in src/gepa_adk/adapters/multi_agent.py
- [ ] T013 [US1] Add _apply_candidate method to route updates via ComponentSpec.parse and get_handler in src/gepa_adk/adapters/multi_agent.py
- [ ] T014 [US1] Modify _build_seed_candidate to generate qualified names (generator.instruction format) in src/gepa_adk/adapters/multi_agent.py
- [ ] T015 [US1] Modify _build_pipeline to read components using ComponentSpec parsing in src/gepa_adk/adapters/multi_agent.py
- [ ] T016 [US1] Update evolve_group signature to require agents as dict and components parameter in src/gepa_adk/api.py
- [ ] T017 [US1] Add structlog context binding for component routing operations in src/gepa_adk/adapters/multi_agent.py

**Checkpoint**: Component routing works - candidates route to correct agents

---

## Phase 4: User Story 2 - Restore All Agents After Evaluation (Priority: P1)

**Goal**: Ensure all agents are restored to original state after each candidate evaluation, regardless of success or failure

**Independent Test**: Apply candidate to multiple agents, complete evaluation, verify all agents match original values

### Tests for User Story 2

- [ ] T018 [P] [US2] Unit test for _restore_agents successful restoration in tests/unit/adapters/test_multi_agent_routing.py
- [ ] T019 [P] [US2] Unit test for _restore_agents with partial failure aggregation in tests/unit/adapters/test_multi_agent_routing.py
- [ ] T020 [P] [US2] Unit test for restoration after evaluation error in tests/unit/adapters/test_multi_agent_routing.py

### Implementation for User Story 2

- [ ] T021 [US2] Add _restore_agents method with best-effort restoration and error aggregation in src/gepa_adk/adapters/multi_agent.py
- [ ] T022 [US2] Integrate _apply_candidate and _restore_agents into evaluate method with try/finally pattern in src/gepa_adk/adapters/multi_agent.py
- [ ] T023 [US2] Add structlog logging for restoration operations in src/gepa_adk/adapters/multi_agent.py

**Checkpoint**: Agents always restored after evaluation - no state leakage

---

## Phase 5: User Story 3 - Track Originals Per Agent (Priority: P2)

**Goal**: Track original values for each agent-component combination using qualified names as keys

**Independent Test**: Inspect originals dictionary after _apply_candidate to verify agent.component keys with correct original values

### Tests for User Story 3

- [ ] T024 [P] [US3] Unit test for originals dictionary structure after _apply_candidate in tests/unit/adapters/test_multi_agent_routing.py
- [ ] T025 [P] [US3] Unit test for originals tracking with multiple agents and components in tests/unit/adapters/test_multi_agent_routing.py

### Implementation for User Story 3

- [ ] T026 [US3] Ensure _apply_candidate returns originals dict keyed by qualified names in src/gepa_adk/adapters/multi_agent.py
- [ ] T027 [US3] Update MultiAgentEvolutionResult to include evolved_components with qualified names in src/gepa_adk/domain/models.py

**Checkpoint**: Originals tracked correctly for all agent-component pairs

---

## Phase 6: Integration & Documentation

**Purpose**: Integration tests, documentation updates, and example creation

### Integration Tests

- [ ] T028 [P] Integration test for multi-agent evolution with per-agent components in tests/integration/test_multi_agent_components.py
- [ ] T029 [P] Integration test for three agents with different component types in tests/integration/test_multi_agent_components.py

### Documentation Updates (Required - Breaking Change)

- [ ] T030 [P] Update docs/guides/multi-agent.md with per-agent components documentation and migration guide
- [ ] T031 [P] Create examples/multi_agent_component_demo.py demonstrating per-agent component evolution

**Checkpoint**: Feature fully documented and demonstrated

---

## Phase 7: Verification & Quality Assurance

**Purpose**: Final verification, code quality, and documentation build

### Code Quality (REQUIRED)

- [ ] T032 Run `./scripts/code_quality_check.sh --all` and fix all warnings and issues
- [ ] T033 Verify all docstrings follow Google style with TACOS acrostic per python.instructions.md
- [ ] T034 Verify all tests follow pytest.instructions.md patterns (mocker fixture from pytest-mock)

### Documentation Build Verification (REQUIRED)

- [ ] T035 Verify `uv run mkdocs build` passes without warnings
- [ ] T036 Preview docs with `uv run mkdocs serve` and verify multi-agent guide renders correctly

### Final Validation

- [ ] T037 Run full test suite: `uv run pytest tests/`
- [ ] T038 Validate quickstart.md examples work as documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories
- **Phase 3-5 (User Stories)**: All depend on Phase 2 completion
  - US1 and US2 are both P1 priority - US2 depends on US1 (_apply_candidate must exist for _restore_agents)
  - US3 (P2) depends on US1 (_apply_candidate returns originals)
- **Phase 6 (Integration/Docs)**: Depends on all user stories complete
- **Phase 7 (Verification)**: Depends on Phase 6

### User Story Dependencies

- **User Story 1 (P1)**: After Phase 2 - Core routing implementation
- **User Story 2 (P1)**: After US1 - Uses _apply_candidate to test restoration
- **User Story 3 (P2)**: After US1 - Verifies originals tracking from _apply_candidate

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation follows test specifications
- Logging added after core implementation

### Parallel Opportunities

**Phase 1**:
- T003 can run parallel after T001, T002 verified

**Phase 2**:
- T004 and T005 can run in parallel

**Phase 3 (US1) Tests**:
```bash
# All US1 tests can run in parallel:
Task: T006, T007, T008, T009, T010
```

**Phase 4 (US2) Tests**:
```bash
# All US2 tests can run in parallel:
Task: T018, T019, T020
```

**Phase 5 (US3) Tests**:
```bash
# All US3 tests can run in parallel:
Task: T024, T025
```

**Phase 6**:
```bash
# Integration tests and docs can run in parallel:
Task: T028, T029, T030, T031
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Complete Phase 1: Setup (verify prerequisites)
2. Complete Phase 2: Foundational (RestoreError exception)
3. Complete Phase 3: User Story 1 (routing)
4. Complete Phase 4: User Story 2 (restoration)
5. **STOP and VALIDATE**: Test routing and restoration independently
6. Can deploy MVP with routing + restoration working

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (routing) → Test independently → Core functionality works
3. US2 (restoration) → Test independently → Full correctness
4. US3 (tracking) → Test independently → Enhanced observability
5. Integration/Docs → Feature complete for users

### Quality Gates

Before marking complete:
1. All tests pass: `uv run pytest tests/`
2. Code quality clean: `./scripts/code_quality_check.sh --all`
3. Docs build clean: `uv run mkdocs build` (no warnings)
4. Docstrings follow Google style with TACOS acrostic

---

## Summary

| Category | Count |
|----------|-------|
| Total Tasks | 39 |
| User Story 1 (P1 - Routing) | 13 tasks |
| User Story 2 (P1 - Restoration) | 6 tasks |
| User Story 3 (P2 - Tracking) | 4 tasks |
| Setup/Foundational | 5 tasks |
| Integration/Docs | 4 tasks |
| Verification | 7 tasks |
| Parallel Opportunities | 21 tasks marked [P] |

**MVP Scope**: User Stories 1 + 2 (19 tasks) - Core routing and restoration
**Full Scope**: All 38 tasks including US3, integration tests, docs, and verification

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Use pytest-mock's `mocker` fixture for all mocking (per pytest.instructions.md)
- Follow Google docstring style with TACOS acrostic for src/ files (per python.instructions.md)
- Run `./scripts/code_quality_check.sh --all` before final commit
- Run `uv run mkdocs build` to verify docs build without warnings
- Breaking change: Version bump to 0.3.x required

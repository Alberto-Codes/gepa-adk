# Tasks: Multi-Agent Co-Evolution (evolve_group)

**Input**: Design documents from `/specs/014-multi-agent-coevolution/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/evolve_group.md ✅

**Tests**: Three-layer testing per ADR-005 (contracts/, unit/, integration/)

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Domain models and exception hierarchy (no external dependencies)

- [ ] T001 [P] Add `MultiAgentValidationError` exception in `src/gepa_adk/domain/exceptions.py`
- [ ] T002 [P] Add `MultiAgentEvolutionResult` dataclass in `src/gepa_adk/domain/models.py`
- [ ] T003 [P] Add `MultiAgentTrajectory` dataclass in `src/gepa_adk/domain/trajectory.py`
- [ ] T004 [P] Add `MultiAgentCandidate` type alias in `src/gepa_adk/domain/types.py`

**Checkpoint**: Domain models ready for adapter implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core adapter that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Create `MultiAgentAdapter` class scaffold in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T006 Implement `MultiAgentAdapter.__init__()` with validation in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T007 Implement `_build_pipeline()` helper (clones agents, builds SequentialAgent) in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T008 Implement `_extract_primary_output()` helper in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T009 Add adapter exports to `src/gepa_adk/adapters/__init__.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Evolve Multiple Agents Together (Priority: P1) 🎯 MVP

**Goal**: Users can call `evolve_group()` with multiple agents and get all instructions evolved

**Independent Test**: Create 3 simple agents, call `evolve_group()`, verify all 3 instructions returned

### Tests for User Story 1

- [ ] T010 [P] [US1] Contract test for MultiAgentAdapter protocol compliance in `tests/contracts/test_multi_agent_adapter_protocol.py`
- [ ] T011 [P] [US1] Unit test for `MultiAgentAdapter.__init__()` validation in `tests/unit/adapters/test_multi_agent_adapter.py`
- [ ] T012 [P] [US1] Unit test for `_build_pipeline()` agent cloning in `tests/unit/adapters/test_multi_agent_adapter.py`

### Implementation for User Story 1

- [ ] T013 [US1] Implement `MultiAgentAdapter.evaluate()` method with error handling in `src/gepa_adk/adapters/multi_agent.py` (covers FR-012 scoring strategy, EdgeCase-3 agent failure)
- [ ] T014 [US1] Implement `MultiAgentAdapter.make_reflective_dataset()` method in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T015 [US1] Create `evolve_group()` public API function in `src/gepa_adk/api.py`:
  - Validate and pass `trainset` to adapter (FR-003)
  - Pass `config` to AsyncGEPAEngine (FR-006)
  - Build seed candidate: `{agent.name}_instruction` for each agent (FR-007)
- [ ] T016 [US1] Export `evolve_group` and `MultiAgentEvolutionResult` in `src/gepa_adk/__init__.py`
- [ ] T017 [US1] Add structlog logging with evolution_id, agent_name context in `src/gepa_adk/adapters/multi_agent.py`

**Checkpoint**: User Story 1 complete - can evolve multiple agents together

---

## Phase 4: User Story 3 - Retrieve All Evolved Instructions (Priority: P1)

**Goal**: Users can access `result.evolved_instructions` dict keyed by agent name

**Independent Test**: Verify `result.evolved_instructions["generator"]`, `result.evolved_instructions["critic"]` accessible

### Tests for User Story 3

- [ ] T018 [P] [US3] Unit test for `MultiAgentEvolutionResult` computed properties in `tests/unit/domain/test_multi_agent_result.py`
- [ ] T019 [P] [US3] Integration test for end-to-end evolution result in `tests/integration/test_multi_agent_evolution.py`

### Implementation for User Story 3

- [ ] T020 [US3] Implement `improvement` and `improved` computed properties in `src/gepa_adk/domain/models.py`
- [ ] T021 [US3] Implement `agent_names` computed property in `src/gepa_adk/domain/models.py`
- [ ] T022 [US3] Convert engine result to `MultiAgentEvolutionResult` in `src/gepa_adk/api.py`

**Checkpoint**: User Story 3 complete - all evolved instructions retrievable by name

---

## Phase 5: User Story 2 - Share Session State Between Agents (Priority: P2))

**Goal**: Agents share session state when `share_session=True`, isolated when `False`

**Independent Test**: Create 2 agents where second references first's output, verify state sharing works

### Tests for User Story 2

- [ ] T023 [P] [US2] Integration test for session sharing in `tests/integration/test_multi_agent_session.py`
- [ ] T024 [P] [US2] Unit test for `share_session=False` isolation in `tests/unit/adapters/test_multi_agent_adapter.py`

### Implementation for User Story 2

- [ ] T025 [US2] Implement session isolation mode (`share_session=False`) in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T026 [US2] Add `output_key` state propagation handling in `src/gepa_adk/adapters/multi_agent.py`
- [ ] T027 [US2] Document session sharing behavior in docstrings (include EdgeCase-5: incompatible outputs behavior) in `src/gepa_adk/adapters/multi_agent.py`

**Checkpoint**: User Story 2 complete - session sharing works both modes

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and final integration

- [ ] T028 [P] Add comprehensive docstrings to all public APIs per ADR-010 in `src/gepa_adk/api.py`
- [ ] T029 [P] Update API documentation in `docs/` if needed
- [ ] T030 Run `quickstart.md` validation - ensure all examples work
- [ ] T031 Run full test suite: `uv run pytest -n auto`
- [ ] T032 Run linting and type checks: `uv run ruff check --fix && uv run ty check`

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ────────────────┐
                               ├──► Phase 2: Foundational ──┬──► Phase 3: US1 (MVP)
                               │                            ├──► Phase 4: US2
                               │                            └──► Phase 5: US3
                               │                                      │
                               └──────────────────────────────────────┴──► Phase 6: Polish
```

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational completion
  - US1 and US3 are P1 priority - implement first
  - US2 is P2 priority - implement after MVP
- **Polish (Phase 6)**: Depends on all user stories

### User Story Dependencies

| Story | Depends On | Can Parallelize With |
|-------|------------|---------------------|
| US1 (Evolve Agents) - P1 | Phase 2 only | US3 |
| US3 (Retrieve Results) - P1 | Phase 2 only | US1 |
| US2 (Session Sharing) - P2 | Phase 2 only | US1, US3 |

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Core implementation before integration
3. Story complete before moving to next priority

---

## Parallel Execution Examples

### Phase 1: All Setup Tasks

```bash
# All domain model tasks can run in parallel (different files):
T001: MultiAgentValidationError in exceptions.py
T002: MultiAgentEvolutionResult in models.py
T003: MultiAgentTrajectory in trajectory.py
T004: MultiAgentCandidate in types.py
```

### Phase 3: User Story 1 Tests

```bash
# All US1 tests can run in parallel:
T010: Contract test for protocol compliance
T011: Unit test for __init__ validation
T012: Unit test for _build_pipeline
```

### Post-Foundational: User Stories

```bash
# With multiple developers after Phase 2 completes:
Developer A: US1 (T010-T017) - MVP path
Developer B: US3 (T018-T022) - Also P1 priority
Developer C: US2 (T023-T027) - P2 priority
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. ✅ Complete Phase 1: Setup (domain models)
2. ✅ Complete Phase 2: Foundational (MultiAgentAdapter scaffold)
3. ✅ Complete Phase 3: User Story 1 (evolve_group API)
4. **STOP and VALIDATE**: Test with 3 agents end-to-end
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → **MVP Complete!**
3. Add US3 → Test independently → Full result access
4. Add US2 → Test independently → Session isolation option
5. Polish → Production ready

### Task Count Summary

| Phase | Tasks | Parallelizable |
|-------|-------|----------------|
| Phase 1: Setup | 4 | 4 (100%) |
| Phase 2: Foundational | 5 | 0 (sequential) |
| Phase 3: US1 (P1) | 8 | 3 tests |
| Phase 4: US3 (P1) | 5 | 2 tests |
| Phase 5: US2 (P2) | 5 | 2 tests |
| Phase 6: Polish | 5 | 2 |
| **Total** | **32** | **13 (41%)** |

---

## Notes

- **ADK Constraint**: `LlmAgent.output_schema` disables tools - see research.md
- **Agent Cloning**: Use `agent.model_copy(update={"instruction": ...})` - Pydantic pattern
- **GEPA Compatibility**: `MultiAgentCandidate = dict[str, str]` matches GEPA's `Candidate` type
- **Session State**: SequentialAgent passes same `InvocationContext` to all sub-agents
- Tests follow three-layer pattern per ADR-005
- Commit after each task or logical group

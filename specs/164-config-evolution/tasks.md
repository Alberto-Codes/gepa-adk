# Tasks: Generate Content Config Evolution

**Input**: Design documents from `/specs/164-config-evolution/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, architecture.md ✅, quickstart.md ✅

**Tests**: Three-layer testing (contract, unit, integration) as specified in spec.md and ADR-005.

**Documentation**: Per Constitution Principle VI, this feature requires documentation updates (new public config option).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add foundational constant and exception types

- [x] T001 [P] Add `COMPONENT_GENERATE_CONFIG = "generate_content_config"` constant to `src/gepa_adk/domain/types.py`
- [x] T002 [P] Add `ConfigValidationError` exception class to `src/gepa_adk/domain/exceptions.py` (inherits from `EvolutionError`, with `message: str` and `errors: list[str]` attributes)

**Checkpoint**: Foundation constants and exceptions ready

---

## Phase 2: Foundational (Config Utilities)

**Purpose**: Core config serialization/deserialization utilities that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create `src/gepa_adk/utils/config_utils.py` module with:
  - [x] T003a `serialize_generate_config(config: GenerateContentConfig) -> str` - Convert config to YAML with parameter descriptions:
    - Temperature: "Controls randomness (0.0=deterministic, 2.0=creative)"
    - top_p: "Nucleus sampling threshold (0.0-1.0)"
    - top_k: "Top-k sampling (higher=more diverse)"
    - max_output_tokens: "Maximum response length"
    - presence_penalty: "Penalizes repeated topics (-2.0 to 2.0)"
    - frequency_penalty: "Penalizes repeated tokens (-2.0 to 2.0)"
  - [x] T003b `deserialize_generate_config(yaml_text: str, existing: GenerateContentConfig | None = None) -> GenerateContentConfig` - Parse YAML, merge with existing (proposed values override, unspecified values preserved)
  - [x] T003c `validate_generate_config(config_dict: dict[str, Any]) -> list[str]` - Validate parameter constraints (per `contracts/config_utils.md` and `data-model.md`)
- [x] T004 Export config utilities from `src/gepa_adk/utils/__init__.py`

**Checkpoint**: Config utilities ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Evolve LLM Generation Config (Priority: P1) 🎯 MVP

**Goal**: Enable `generate_content_config` as an evolvable component in GEPA evolution configuration

**Independent Test**: Configure evolution with `components=["generate_content_config"]` and verify config parameters change based on reflection agent proposals

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T005 [P] [US1] Contract test for `GenerateContentConfigHandler` protocol compliance in `tests/contracts/test_component_handler_contract.py`:
  - Handler implements `serialize`, `apply`, `restore` methods
  - Handler is registered in `ComponentHandlerRegistry` with `COMPONENT_GENERATE_CONFIG` key
  - Handler passes `isinstance(handler, ComponentHandler)` check
- [x] T006 [P] [US1] Unit tests for `GenerateContentConfigHandler` in `tests/unit/adapters/test_component_handlers.py`:
  - `test_serialize_returns_yaml_string`
  - `test_serialize_none_returns_empty`
  - `test_apply_updates_agent_config`
  - `test_apply_returns_original`
  - `test_apply_invalid_keeps_original`
  - `test_restore_reverts_config`
  - `test_restore_handles_none`
- [x] T007 [P] [US1] Unit tests for config utilities in `tests/unit/utils/test_config_utils.py`:
  - `test_serialize_returns_yaml_string`
  - `test_serialize_includes_descriptions`
  - `test_serialize_roundtrip`
  - `test_deserialize_parses_yaml`
  - `test_deserialize_merges_with_existing`
  - `test_deserialize_empty_returns_default`
  - `test_deserialize_invalid_yaml_raises`
  - `test_validate_empty_dict`
  - `test_validate_valid_config`
  - `test_validate_temperature_out_of_range`
  - `test_validate_negative_top_k`
  - `test_validate_multiple_errors`
  - `test_validate_unknown_param_no_error`

### Implementation for User Story 1

- [x] T008 [US1] Implement `GenerateContentConfigHandler` class in `src/gepa_adk/adapters/component_handlers.py`:
  - `serialize(agent: LlmAgent) -> str` - Delegate to `serialize_generate_config`
  - `apply(agent: LlmAgent, value: str) -> GenerateContentConfig | None` - Parse, validate, update agent, return original
  - `restore(agent: LlmAgent, original: GenerateContentConfig | None) -> None` - Restore original config
  - Include structlog logging for all operations (per ADR-008)
  - Handle errors gracefully (log warning, keep original on failure)
- [x] T009 [US1] Register `GenerateContentConfigHandler` in `ComponentHandlerRegistry` at module load time in `src/gepa_adk/adapters/component_handlers.py`
- [x] T010 [US1] Export `GenerateContentConfigHandler` from `src/gepa_adk/adapters/__init__.py`

### Documentation for User Story 1

- [x] T011 [P] [US1] Update `docs/guides/single-agent.md` to mention config evolution capability
- [x] T012 [P] [US1] Create `examples/config_evolution_demo.py` demonstrating config evolution (per `quickstart.md`)

**Checkpoint**: At this point, User Story 1 should be fully functional - `generate_content_config` is evolvable

---

## Phase 4: User Story 2 & 3 - Serialize & Apply Config (Priority: P2)

**Goal**: Add edge case tests for serialization and apply/restore behavior (core implementation in Phase 2)

**Independent Test**: Call `handler.serialize(agent)` and verify YAML output is readable; call `handler.apply(agent, yaml)` then `handler.restore(agent, original)` and verify round-trip

### Tests for User Stories 2 & 3

> **NOTE: Core implementation in T003a/T003b; add edge case tests here**

- [x] T013 [P] [US2/US3] Add edge case tests to `tests/unit/adapters/test_component_handlers.py`:
  - `test_apply_partial_config_merges` - Partial config preserves existing values
  - `test_apply_malformed_yaml_keeps_original` - Garbage input doesn't crash
  - `test_serialize_excludes_non_evolvable` - Only evolvable params in output
- [x] T014 [P] [US2/US3] Integration test for handler round-trip in `tests/integration/test_component_handler_integration.py`:
  - Create agent with config → serialize → apply modified → evaluate → restore → verify original

**Checkpoint**: Serialization and apply/restore edge cases tested

---

## Phase 5: User Story 4 - Validate Config Before Acceptance (Priority: P3)

**Goal**: Reject invalid parameter values with clear error messages before applying to agent

**Independent Test**: Propose `temperature=3.0` and verify rejection with error message containing constraint info

### Tests for User Story 4

- [x] T017 [P] [US4] Add validation boundary tests to `tests/unit/utils/test_config_utils.py`:
  - `test_validate_temperature_boundary_valid` - 0.0 and 2.0 are valid
  - `test_validate_top_p_boundary_valid` - 0.0 and 1.0 are valid
  - `test_validate_presence_penalty_range` - -2.0 to 2.0 valid, outside rejected
  - `test_validate_frequency_penalty_range` - -2.0 to 2.0 valid, outside rejected
  - `test_validate_max_output_tokens_must_be_positive`
  - `test_validate_top_k_must_be_positive`
- [x] T018 [P] [US4] Contract test for `ConfigValidationError` in `tests/unit/utils/test_config_utils.py`:
  - `ConfigValidationError` is subclass of `EvolutionError`
  - Has `message` and `errors` attributes

### Implementation for User Story 4

- [x] T019 [US4] Implement validation rules in `validate_generate_config` (per `data-model.md`):
  - temperature: 0.0 ≤ x ≤ 2.0
  - top_p: 0.0 ≤ x ≤ 1.0
  - top_k: x > 0
  - max_output_tokens: x > 0
  - presence_penalty: -2.0 ≤ x ≤ 2.0
  - frequency_penalty: -2.0 ≤ x ≤ 2.0
  - Unknown parameters: log warning, do NOT reject
- [x] T020 [US4] Wire validation into `GenerateContentConfigHandler.apply()` - if validation fails, log warning and keep original config

**Checkpoint**: All validation rules enforced

---

## Phase 6: Config Reflection Agent (Optional Enhancement)

**Goal**: Provide specialized reflection agent for config-focused evolution

- [x] T021 [P] Implement `create_config_reflection_agent` factory function in `src/gepa_adk/engine/reflection_agents.py`:
  - Create LlmAgent with config-focused instruction
  - Include parameter descriptions and typical ranges in system prompt
- [x] T022 [P] Register config reflection agent in `ComponentReflectionRegistry` with `COMPONENT_GENERATE_CONFIG` key
- [x] T023 [P] Unit test for config reflection agent factory in `tests/unit/engine/test_reflection_agents.py`

**Checkpoint**: Config reflection agent available (optional - can skip if not needed for MVP)

---

## Phase 7: Integration & End-to-End Testing

**Goal**: Verify config evolution works in full evolution loop

- [x] T024 [P] End-to-end integration test in `tests/integration/test_component_handler_integration.py`:
  - Create agent with initial config
  - Run `evolve(agent, examples, components=["generate_content_config"])`
  - Verify config parameters changed (or stayed same if optimal)
  - Verify no errors in evolution loop
- [x] T025 [P] Integration test: config evolution combined with instruction evolution in `tests/integration/test_component_handler_integration.py`:
  - Run `evolve(agent, examples, components=["instruction", "generate_content_config"])`
  - Verify both components can evolve together

**Checkpoint**: Full integration verified

---

## Phase 8: Documentation & Polish

**Purpose**: Final documentation updates and verification

### Documentation Updates

- [x] T026 [P] Update `docs/guides/workflows.md` to mention config evolution capability

### Documentation Build Verification (REQUIRED)

- [x] T028 Run `uv run mkdocs build` and fix any warnings
- [x] T029 Preview docs with `uv run mkdocs serve` and verify config evolution content renders correctly

**Checkpoint**: Documentation complete and builds cleanly

---

## Phase 9: Final Verification

**Purpose**: Code quality and final checks

- [x] T030 Run `scripts/code_quality_check.sh --all` and fix all issues and warnings:
  - Ruff linting
  - Type checking (mypy/pyright)
  - Test suite
  - Import sorting
  - Code formatting
  - Documentation build
  - Security checks (if any)
- [x] T031 Verify all tests pass: `uv run pytest tests/ -v --tb=short`
- [x] T032 Run quickstart validation: manually execute examples from `quickstart.md`

**Checkpoint**: Feature complete and ready for PR

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories
- **Phase 3 (US1 P1)**: Depends on Phase 2 - Core handler implementation
- **Phase 4 (US2/US3 P2)**: Depends on Phase 3 - Edge case tests for serialization/apply
- **Phase 5 (US4 P3)**: Depends on Phase 2 - Can run parallel to Phase 4
- **Phase 6 (Reflection Agent)**: Optional, can run parallel to Phases 4-5
- **Phase 7 (Integration)**: Depends on Phases 3-5 completion
- **Phase 8 (Docs)**: Can start after Phase 3, finalize after Phase 7
- **Phase 9 (Final)**: Depends on all previous phases

### Parallel Opportunities

```text
Phase 1: T001 || T002 (parallel - different files)

Phase 2: T003 → T004 (sequential - module then export)

Phase 3: T005 || T006 || T007 (parallel - different test files)
         T008 → T009 → T010 (sequential - impl then register then export)
         T011 || T012 (parallel - different doc files)

Phase 4: T013 || T014 (parallel - different test files)

Phase 5: T017 || T018 (parallel - different test files)
         T019 → T020 (sequential - validation then wiring)

Phase 6: T021 || T022 || T023 (parallel - can be done together)

Phase 7: T024 || T025 (parallel - different test scenarios)

Phase 8: T026 → T028 → T029 (sequential - docs then build then preview)

Phase 9: T030 → T031 → T032 (sequential - fix issues first)
```

---

## Implementation Strategy

### MVP First (Phase 1-3)

1. Complete Phase 1: Setup (constants, exceptions)
2. Complete Phase 2: Foundational (config_utils)
3. Complete Phase 3: User Story 1 (handler implementation)
4. **STOP and VALIDATE**: Test `evolve(agent, examples, components=["generate_content_config"])` works
5. Can ship MVP at this point

### Incremental Delivery

1. MVP (Phases 1-3) → Basic config evolution works
2. Add Phases 4-5 → Edge case tests + validation
3. Add Phase 6 → Specialized reflection agent (optional)
4. Add Phases 7-9 → Integration tests + docs + quality checks

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Run `uv run mkdocs build` before PR to verify docs build cleanly
- Final task (T030) runs `scripts/code_quality_check.sh --all` per user request

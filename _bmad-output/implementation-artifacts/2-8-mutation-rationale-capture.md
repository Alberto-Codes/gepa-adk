# Story 2.8: Mutation Rationale Capture

Status: review

## Story

As a developer,
I want to see why the reflection agent proposed each mutation,
so that I can understand the evolutionary reasoning and debug unexpected changes.

## Acceptance Criteria

1. `reflection_reasoning: str | None = None` field added to `IterationRecord`
2. Engine captures the reflection agent's text output (the reasoning explaining the mutation) and stores it in the iteration record
3. `EvolutionResult` exposes `.reflection_reasoning` property returning the last iteration's reasoning (convenience accessor)
4. Reflection reasoning is included in `to_dict()` serialization
5. Existing tests pass with the new optional field defaulting to `None`
6. New test verifies reasoning is captured when reflection agent produces text output

## Tasks / Subtasks

- [x] Task 1: Add `reflection_reasoning` field to `IterationRecord` (AC: 1, 5)
  - [x] 1.1 Add `reflection_reasoning: str | None = None` to `IterationRecord` in `src/gepa_adk/domain/models.py:469-474`
  - [x] 1.2 Update `IterationRecord.to_dict()` to include `reflection_reasoning` (AC: 4)
  - [x] 1.3 Update `IterationRecord.from_dict()` to restore `reflection_reasoning` via `.get()` with `None` default (forward-compatible)
  - [x] 1.4 Update docstring on `IterationRecord` to document the new field

- [x] Task 2: Add `.reflection_reasoning` convenience property to `EvolutionResult` (AC: 3)
  - [x] 2.1 Add `reflection_reasoning` property to `EvolutionResult` that returns `self.iteration_history[-1].reflection_reasoning if self.iteration_history else None`
  - [x] 2.2 Add docstring to the property

- [x] Task 3: Thread reasoning through the reflection pipeline (AC: 2)
  - [x] 3.1 Add `extract_reasoning_from_events()` utility to `src/gepa_adk/utils/events.py` — complementary to `extract_final_output()`. Extracts thought-tagged parts (`part.thought=True`) from captured events; falls back to concatenating all text parts from final response events if no thought parts found; returns `None` if no events or no text
  - [x] 3.2 Update `ReflectionFn` type alias in `src/gepa_adk/engine/proposer.py:77` from `Callable[[str, list[dict[str, Any]], str], Awaitable[str]]` to `Callable[[str, list[dict[str, Any]], str], Awaitable[tuple[str, str | None]]]`
  - [x] 3.3 Modify `create_adk_reflection_fn()` inner `reflect()` in `src/gepa_adk/engine/adk_reflection.py` to return `(proposed_text, reasoning)` tuple. Extract reasoning from `result.captured_events` using `extract_reasoning_from_events()`. Update return type and factory return annotation at line 60
  - [x] 3.4 Modify `AsyncReflectiveMutationProposer.propose()` in `src/gepa_adk/engine/proposer.py` to unpack `(proposed_text, reasoning)` tuple at line 258. Store last non-None reasoning in `self.last_reasoning: str | None`. Reset `self.last_reasoning = None` at the start of each `propose()` call
  - [x] 3.5 Modify `AsyncGEPAEngine._propose_mutation()` in `src/gepa_adk/engine/async_engine.py:615` to read `self._proposer.last_reasoning` after mutation proposal
  - [x] 3.6 Pass reasoning to `_record_iteration()` — add `reflection_reasoning: str | None = None` param
  - [x] 3.7 Update `_record_iteration()` to pass reasoning to `IterationRecord` constructor

- [x] Task 4: Write tests (AC: 5, 6)
  - [x] 4.1 Unit test: `IterationRecord` with `reflection_reasoning=None` (backward compat)
  - [x] 4.2 Unit test: `IterationRecord` with `reflection_reasoning="some reasoning"`
  - [x] 4.3 Unit test: `IterationRecord.to_dict()` includes `reflection_reasoning`
  - [x] 4.4 Unit test: `IterationRecord.from_dict()` round-trip preserves reasoning
  - [x] 4.5 Unit test: `IterationRecord.from_dict()` with missing key defaults to `None`
  - [x] 4.6 Unit test: `EvolutionResult.reflection_reasoning` property returns last iteration's reasoning
  - [x] 4.7 Unit test: `EvolutionResult.reflection_reasoning` returns `None` for empty history
  - [x] 4.8 Unit test: `EvolutionResult.to_dict()` / `from_dict()` round-trip preserves reasoning in iteration records
  - [x] 4.9 Integration test: reflection pipeline captures reasoning from mock agent with thought parts present → reasoning captured
  - [x] 4.10 Integration test: reflection pipeline with no thought parts → reasoning is `None` or falls back to full text
  - [x] 4.11 Integration test: reflection pipeline with empty agent response → reasoning is `None`
  - [x] 4.12 Unit test: `propose()` handles `("", None)` empty-tuple return from reflection function (raises `EvolutionError`)
  - [x] 4.13 Update existing test mocks in `tests/unit/engine/test_proposer.py`: `_create_mock_reflection_fn()` at line 27 must return `tuple[str, str | None]` instead of `str` (e.g., `return_value=("proposed text", None)`)
  - [x] 4.14 Verify existing test suite passes (2051+ tests, 0 regressions)

- [x] Task 5: Update test fixture (AC: 4)
  - [x] 5.1 **Do NOT modify** `tests/fixtures/evolution_result_v1.json` (permanent fixture per convention)
  - [x] 5.2 Verify `from_dict()` loads the v1 fixture correctly with `reflection_reasoning=None` defaults

- [ ] [TEA] Testing maturity: Update `_create_mock_executor()` in `tests/unit/engine/test_proposer.py:205` to include `captured_events=None` matching real `ExecutionResult` dataclass shape (cross-cutting, optional)

## Dev Notes

### Key Design Decisions

**Rationale source**: The reflection agent already produces natural language reasoning as part of its mutation response. Currently `adk_reflection.py:209` extracts only `result.extracted_value` (the proposed text) and discards everything else. The reasoning lives in the agent's `captured_events` — either as thought-tagged parts (`part.thought=True`) produced by models like Gemini, or as the full response text from final response events.

**Capture point**: The `ExecutionResult` from `AgentExecutor.execute_agent()` contains `captured_events` (line 98-99 of `ports/agent_executor.py`). A new utility `extract_reasoning_from_events()` in `utils/events.py` extracts reasoning exclusively from thought-tagged parts (`part.thought=True`) in final response events. Returns `None` if no events, no final responses, or no thought parts found. This approach requires NO changes to reflection agent instructions — the current prompt ("Return ONLY the improved component text") stays unchanged. Provider-dependent behavior is acceptable: models with thinking support (Gemini) produce reasoning; others return `None` — this is intentional to avoid returning proposed text as misleading "reasoning".

**ReflectionFn type alias**: `ReflectionFn` at `proposer.py:77` is an internal engine type (exported from `engine/__init__.py`, NOT from package-level `__init__.py`). Changing its return type from `Awaitable[str]` to `Awaitable[tuple[str, str | None]]` is safe — not a public API break.

**No schema version bump needed**: Adding `reflection_reasoning: str | None = None` is backward-compatible per the established convention (Story 2.2 pattern). `from_dict()` uses `.get("reflection_reasoning")` which returns `None` for old data.

**No Protocol changes needed**: `reflection_reasoning` is on concrete types, not on `EvolutionResultProtocol`. Serialization methods (`to_dict`/`from_dict`) are concrete implementation, not Protocol contract (established in Story 2.2).

### Architecture Compliance

- **Layer boundaries**: Domain model change (`IterationRecord`) in `domain/models.py`. Engine threading in `engine/`. No adapter changes needed.
- **Frozen dataclass pattern**: `IterationRecord` is `frozen=True` — field is set at construction time only
- **Serialization convention**: `to_dict()` includes `None` fields as `null` (JSON-compatible). `from_dict()` uses `.get()` with default for optional fields.
- **Structlog event convention**: Log `reflection.reasoning_captured` at `debug` level with `reasoning_length=len(reasoning)` when reasoning is captured
- **Exception hierarchy**: No new exceptions needed

### Critical Implementation Details

**`utils/events.py` — new utility (Task 3.1)**:
Add `extract_reasoning_from_events(events: list[Any] | None) -> str | None` alongside existing `extract_final_output()`. Strategy: (1) collect text from parts where `thought=True`, (2) if no thought parts found, collect all text from final response events (full agent response), (3) return `None` if empty. Uses same event traversal patterns as `extract_final_output()` but with inverted filtering.

**`adk_reflection.py` change (Task 3.3)**:
The inner `reflect()` function currently returns `str`. It needs to return `tuple[str, str | None]` where:
- First element: proposed component text (same as today — from `result.extracted_value`)
- Second element: reasoning text — call `extract_reasoning_from_events(result.captured_events)`

The `reflect()` function signature change impacts its caller in `proposer.py:258` which does:
```python
proposed_component_text = await self.adk_reflection_fn(component_text, trials, component)
```
This must unpack the tuple: `proposed_component_text, reasoning = await self.adk_reflection_fn(...)`.

**`ReflectionFn` type alias (Task 3.2)**:
Update in three locations:
- `src/gepa_adk/engine/proposer.py:77` — the type alias definition
- `src/gepa_adk/engine/proposer.py:130` — constructor parameter type hint
- `src/gepa_adk/engine/adk_reflection.py:60` — factory return type

**Proposer threading (Task 3.3-3.4)**:
`AsyncReflectiveMutationProposer.propose()` iterates over `components_to_update` and calls the reflection function per component. For multi-component evolution, the last component's reasoning is the most relevant (matches `EvolutionResult.reflection_reasoning` semantics). Store the last non-None reasoning.

**Engine threading (Task 3.5-3.7)**:
`_propose_mutation()` returns `tuple[Candidate, list[str]]`. Adding reasoning requires either:
- (a) Expanding the return type to include reasoning, or
- (b) Using a proposer attribute like `self._proposer.last_reasoning`

Option (b) is simpler and avoids cascading return type changes. The engine reads `self._proposer.last_reasoning` after `_propose_mutation()` and passes it to `_record_iteration()`.

**Multi-agent evolution**: `MultiAgentEvolutionResult` shares `IterationRecord` — reasoning will be captured automatically. No changes needed to `MultiAgentEvolutionResult`.

### File Paths to Touch

| File | Change |
|------|--------|
| `src/gepa_adk/domain/models.py` | Add field to `IterationRecord`, update `to_dict()`/`from_dict()`, add property to `EvolutionResult` |
| `src/gepa_adk/utils/events.py` | Add `extract_reasoning_from_events()` utility (thought parts preferred, full text fallback) |
| `src/gepa_adk/engine/adk_reflection.py` | Change `reflect()` return type to tuple, extract reasoning via new utility, update factory return type at line 60 |
| `src/gepa_adk/engine/proposer.py` | Update `ReflectionFn` type alias at line 77, unpack tuple at line 258, store `last_reasoning` attribute |
| `src/gepa_adk/engine/async_engine.py` | Pass reasoning from proposer to `_record_iteration()` |
| `tests/unit/domain/test_models.py` | Add tests for new field, property, serialization |
| `tests/unit/engine/test_proposer.py` | Update `_create_mock_reflection_fn()` return type to tuple, add reasoning capture tests |
| `tests/integration/engine/` | Integration tests for reasoning pipeline (thought parts, no thought parts, empty) |

### Documentation Impact

- New read-only `reflection_reasoning` property added to `EvolutionResult` (public API surface)
- No ADR needed (extending existing domain model per established pattern)
- Docstring examples in `IterationRecord` should include `reflection_reasoning` usage
- `EvolutionResult` docstring should mention the new property
- No guide/tutorial impact (feature is opt-in observation, not behavioral change)

### Project Structure Notes

- All changes follow hexagonal architecture: domain models in `domain/`, engine logic in `engine/`
- No adapter layer changes — reasoning extraction happens at the engine/reflection boundary
- Test placement follows convention: unit tests in `tests/unit/domain/` and `tests/unit/engine/`, integration in `tests/integration/engine/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Epic 2, Story 2.8]
- [Source: _bmad-output/planning-artifacts/architecture.md - Domain Serialization Convention (lines 467-530)]
- [Source: _bmad-output/planning-artifacts/architecture.md - Internal Data Flow (lines 1202-1231)]
- [Source: src/gepa_adk/domain/models.py:413-515 - IterationRecord definition]
- [Source: src/gepa_adk/engine/adk_reflection.py:142-237 - reflect() function]
- [Source: src/gepa_adk/engine/proposer.py:166-289 - propose() method]
- [Source: src/gepa_adk/engine/async_engine.py:712-744 - _record_iteration()]
- [Source: src/gepa_adk/engine/async_engine.py:1309-1329 - iteration recording call site]
- [Source: src/gepa_adk/ports/agent_executor.py:84-133 - ExecutionResult with captured_events]
- [Source: src/gepa_adk/engine/proposer.py:77 - ReflectionFn type alias (internal, not in package __init__.py)]
- [Source: src/gepa_adk/utils/events.py:375-444 - extract_final_output() pattern for new extract_reasoning utility]
- [Source: tests/unit/utils/test_events.py:757 - MockPart with thought=True support]
- [Source: tests/unit/engine/test_proposer.py:27-29 - _create_mock_reflection_fn() needs tuple return]
- [Source: tests/unit/engine/test_proposer.py:205-215 - _create_mock_executor() missing captured_events]
- [Source: Story 2.2 - Serialization convention: optional fields use .get() with None default]
- [Source: Story 2.7 - Latest test count baseline: 2051 tests]

### Previous Story Intelligence (from Story 2.7)

- **Central pattern, not per-component**: Story 2.7 used a single `random.Random(seed)` passed everywhere. Similarly, reasoning should be a single value per iteration (last component's reasoning), not per-component.
- **Attribute-based side channel**: Story 2.7 stored `rng` as a constructor parameter. For the proposer, using `self.last_reasoning` as an attribute avoids changing return types and Protocol signatures.
- **Optional field backward compat**: `seed: int | None = None` in `EvolutionConfig` worked seamlessly. Same pattern for `reflection_reasoning: str | None = None` in `IterationRecord`.
- **Test file convention**: Story 2.7 created `tests/unit/engine/test_determinism.py`. New tests for this story should go in existing `tests/unit/domain/test_models.py` (for domain model tests) and a new file for engine/pipeline tests.
- **Code review patterns from 2.7**: Reviewers flagged placeholder tests, weak negative assertions, and missing integration coverage. Write concrete assertions from the start.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation with no blocking issues.

### Completion Notes List

- Added `reflection_reasoning: str | None = None` field to `IterationRecord` with full `to_dict()`/`from_dict()` support
- Added `reflection_reasoning` property to `EvolutionResult` returning last iteration's reasoning
- Created `extract_reasoning_from_events()` utility in `utils/events.py` with two-tier strategy: thought parts preferred, full text fallback
- Updated `ReflectionFn` type alias from `Awaitable[str]` to `Awaitable[tuple[str, str | None]]`
- Modified `create_adk_reflection_fn()` to extract reasoning from `captured_events` and return tuple
- Modified `AsyncReflectiveMutationProposer.propose()` to unpack tuple and store `last_reasoning`
- Modified `AsyncGEPAEngine._record_iteration()` to pass reasoning from adapter's proposer to `IterationRecord`
- Engine reads reasoning via `getattr(self.adapter, "_proposer", None)` attribute chain (avoids return type cascading)
- Updated 9 test files with mock reflection functions returning tuples instead of plain strings
- Added 26 new tests (7 unit domain, 4 unit proposer, 7 unit events, 8 integration)
- Full suite: 2077 tests pass, 0 regressions (baseline was 2051)
- v1 fixture loads correctly with `reflection_reasoning=None` defaults

### AC-to-Test Mapping

| AC | Test(s) | Status |
|----|---------|--------|
| AC1: `reflection_reasoning` field on `IterationRecord` | `TestIterationRecordReflectionReasoning::test_reflection_reasoning_defaults_to_none`, `test_reflection_reasoning_stores_string` | PASS |
| AC2: Engine captures reasoning | `TestReasoningPipelineEndToEnd::test_reasoning_stored_in_proposer_last_reasoning`, `TestReasoningCaptureWithThoughtParts::test_thought_parts_captured_as_reasoning` | PASS |
| AC3: `EvolutionResult.reflection_reasoning` property | `TestEvolutionResultReflectionReasoning::test_reflection_reasoning_returns_last_iteration_reasoning`, `test_reflection_reasoning_returns_none_for_empty_history` | PASS |
| AC4: Included in `to_dict()` serialization | `TestIterationRecordReflectionReasoning::test_to_dict_includes_reflection_reasoning`, `test_from_dict_round_trip_preserves_reasoning` | PASS |
| AC5: Existing tests pass with new field defaulting to None | `TestIterationRecordReflectionReasoning::test_from_dict_missing_key_defaults_to_none`, `TestSerializationFixtures::test_load_evolution_result_v1_fixture` | PASS |
| AC6: New test verifies reasoning captured | `TestReasoningCaptureWithThoughtParts::test_thought_parts_captured_as_reasoning`, `TestReasoningCaptureWithoutThoughtParts::test_no_thought_parts_falls_back_to_full_text` | PASS |

### File List

- `src/gepa_adk/domain/models.py` — Added `reflection_reasoning` field to `IterationRecord`, updated `to_dict()`/`from_dict()`, added property to `EvolutionResult`
- `src/gepa_adk/utils/events.py` — Added `extract_reasoning_from_events()` utility, updated `__all__`
- `src/gepa_adk/engine/adk_reflection.py` — Changed `reflect()` return type to tuple, extract reasoning via new utility
- `src/gepa_adk/engine/proposer.py` — Updated `ReflectionFn` type alias, unpack tuple, store `last_reasoning`
- `src/gepa_adk/engine/async_engine.py` — Pass reasoning from adapter proposer to `_record_iteration()`
- `tests/unit/domain/test_models.py` — Updated existing key count assertion, added `TestIterationRecordReflectionReasoning` and `TestEvolutionResultReflectionReasoning` classes
- `tests/unit/engine/test_proposer.py` — Updated `_create_mock_reflection_fn()` to return tuple, added `TestProposeReasoningCapture` class
- `tests/unit/engine/test_adk_reflection.py` — Updated result assertions for tuple return
- `tests/unit/engine/test_adk_reflection_state.py` — Updated result assertions for tuple return
- `tests/unit/engine/test_propose_branching.py` — Updated mock return values to tuples
- `tests/unit/utils/test_events.py` — Added `TestExtractReasoningFromEvents` class
- `tests/unit/adapters/test_adk_adapter.py` — Updated mock reflection fn return type
- `tests/unit/adapters/test_multi_agent_state_extraction.py` — Updated mock return value
- `tests/unit/adapters/test_multi_agent_session.py` — Updated mock return value
- `tests/unit/test_reflection_model_wiring.py` — Updated mock return values
- `tests/contracts/engine/test_proposer_contracts.py` — Updated mock return values
- `tests/contracts/engine/test_reflection_fn_contract.py` — Updated reflect stub and assertions
- `tests/contracts/test_adk_adapter_contracts.py` — Updated `_stub_reflection_fn` return type
- `tests/contracts/test_reflection_fn.py` — Updated mock reflection fns and assertions
- `tests/contracts/test_multi_agent_adapter_protocol.py` — Updated mock return value
- `tests/contracts/test_multi_agent_executor_contract.py` — Updated mock reflection fn
- `tests/integration/engine/test_proposer_integration.py` — Updated fake_reflection functions
- `tests/integration/engine/test_reasoning_capture.py` — **NEW** Integration tests for reasoning pipeline

### Change Log

- 2026-03-05: Implemented mutation rationale capture (Story 2.8) — added `reflection_reasoning` field to `IterationRecord`, convenience property on `EvolutionResult`, reasoning extraction utility, and threaded reasoning through the full reflection pipeline
- 2026-03-05: Code review fixes — removed misleading text fallback in `extract_reasoning_from_events()` (now returns None when no thought parts), added TODO comment for `getattr` chain coupling, added engine-level integration tests for `_proposer.last_reasoning` chain, corrected Documentation Impact and test count in story

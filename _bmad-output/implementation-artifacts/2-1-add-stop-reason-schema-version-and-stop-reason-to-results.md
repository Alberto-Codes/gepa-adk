# Story 2.1: Add StopReason, Schema Version, and Stop Reason to Results

Status: complete
Branch: feat/2-1-stop-reason-schema-version

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to know why my evolution run stopped and have versioned result schemas,
so that I can distinguish between completion modes and safely serialize results across versions.

## Acceptance Criteria

1. **StopReason enum exists in `domain/types.py`** — `StopReason(str, Enum)` with values: `COMPLETED`, `MAX_ITERATIONS`, `STOPPER_TRIGGERED`, `KEYBOARD_INTERRUPT`, `TIMEOUT`, `CANCELLED`. Follows `FrontierType` enum pattern already in that file.
2. **`stop_reason: StopReason` field on `EvolutionResult`** — Defaults to `StopReason.COMPLETED`. Frozen field on the existing `@dataclass(slots=True, frozen=True, kw_only=True)`.
3. **`stop_reason: StopReason` field on `MultiAgentEvolutionResult`** — Same default. Propagated from `EvolutionResult` in `api.py` line 981.
4. **`schema_version: int = 1` frozen field on both result types** — Frozen constant, always `1` in this story. `CURRENT_SCHEMA_VERSION = 1` module-level constant in `domain/models.py`.
5. **`EvolutionResultProtocol` updated** — Add `stop_reason: StopReason` and `schema_version: int` data attributes to the protocol in `ports/evolution_result.py`. Remove all "deferred to Story 2.1" comments from protocol, ADR-013, and module docstring.
6. **Engine sets appropriate `StopReason`** — `AsyncGEPAEngine._should_stop()` (line 725) must communicate WHICH condition triggered, and `_build_result()` (line 887) must receive and set the correct `stop_reason`. The **Stop Reason Mapping** table in Dev Notes is the authoritative reference for which `StopReason` value corresponds to each termination condition.
7. **ADR-015 document written** — `docs/adr/ADR-015-result-schema-versioning.md` documenting the schema versioning decision per the architecture doc's Decision 4.
8. **Existing tests pass** — All ~1856 tests continue to pass. `stop_reason` defaults to `COMPLETED` so no existing result construction breaks.
9. **New tests verify each stop reason** — Unit tests for each `StopReason` value being set correctly by the engine under the corresponding termination condition.
10. **Every test asserting on results includes `result.schema_version == 1`** — Add this assertion to relevant existing test classes to establish the versioning contract.

## Tasks / Subtasks

### Task 1: Add StopReason enum to domain/types.py (AC: 1)

- [x] 1.1 Add `StopReason(str, Enum)` class to `src/gepa_adk/domain/types.py` after the `FrontierType` enum (around line 354). Values: `COMPLETED = "completed"`, `MAX_ITERATIONS = "max_iterations"`, `STOPPER_TRIGGERED = "stopper_triggered"`, `KEYBOARD_INTERRUPT = "keyboard_interrupt"`, `TIMEOUT = "timeout"`, `CANCELLED = "cancelled"`. Follow the `FrontierType` pattern (str, Enum with Google docstring).
- [x] 1.2 Add `"StopReason"` to `__all__` in `domain/types.py` (line 633)
- [x] 1.3 Add `StopReason` to import in `domain/__init__.py` (line 72 `from gepa_adk.domain.types import ...`) and to `__all__` (line 88)
- [x] 1.4 Add `StopReason` to import in `gepa_adk/__init__.py` and to `__all__`

### Task 2: Add schema_version and stop_reason to EvolutionResult (AC: 2, 4)

- [x] 2.1 Add `CURRENT_SCHEMA_VERSION = 1` module-level constant in `src/gepa_adk/domain/models.py` (before the dataclass definitions, near imports)
- [x] 2.2 Add `schema_version: int = CURRENT_SCHEMA_VERSION` field to `EvolutionResult` (line 320 area). Place BEFORE `original_score` so it's the first field — follows architecture Decision 4 pattern.
- [x] 2.3 Add `stop_reason: StopReason = StopReason.COMPLETED` field to `EvolutionResult`. Place after `schema_version`. Import `StopReason` from `domain.types`.
- [x] 2.4 Add `"CURRENT_SCHEMA_VERSION"` to `__all__` in `models.py`
- [x] 2.5 Export `CURRENT_SCHEMA_VERSION` from `domain/__init__.py` and `gepa_adk/__init__.py`

### Task 3: Add schema_version and stop_reason to MultiAgentEvolutionResult (AC: 3, 4)

- [x] 3.1 Add `schema_version: int = CURRENT_SCHEMA_VERSION` field to `MultiAgentEvolutionResult` (line 450 area). Same position as in EvolutionResult.
- [x] 3.2 Add `stop_reason: StopReason = StopReason.COMPLETED` field to `MultiAgentEvolutionResult`
- [x] 3.3 Update `api.py` line 981 `MultiAgentEvolutionResult(...)` construction to propagate `stop_reason=evolution_result.stop_reason` and `schema_version=evolution_result.schema_version`

### Task 4: Update EvolutionResultProtocol (AC: 5)

- [x] 4.1 Add `from gepa_adk.domain.types import StopReason` to `ports/evolution_result.py`
- [x] 4.2 Add `stop_reason: StopReason` and `schema_version: int` data attributes to `EvolutionResultProtocol` class body (after `total_iterations`, before properties)
- [x] 4.3 Update protocol class docstring `Attributes:` section to document `stop_reason` and `schema_version`
- [x] 4.4 Remove "deferred to Epic 2, Story 2.1" comments from: module docstring Note (line 53-57), class docstring Note (line 114-117)
- [x] 4.5 Update module docstring examples to include `schema_version` assertion
- [x] 4.6 Update ADR-013 (`docs/adr/ADR-013-result-type-protocol.md`): remove "Deferred: stop_reason" section (line 27-29), update "Neutral" consequence to note that stop_reason and schema_version have been added

### Task 5: Engine stop reason tracking (AC: 6)

- [x] 5.1 Refactor `_should_stop()` (line 725) to return a `StopReason | None` instead of `bool`. Return `None` when no stop condition met, return the specific `StopReason` when triggered:
  - `self._state.iteration >= self.config.max_iterations` → `StopReason.MAX_ITERATIONS`
  - `self._state.stagnation_counter >= self.config.patience` → `StopReason.MAX_ITERATIONS` (patience is a form of max iteration convergence — architecture says to use `STOPPER_TRIGGERED` only for custom stoppers; use your judgment, but patience-based early stop is a built-in termination, not a custom stopper)
  - Custom stopper returns True → `StopReason.STOPPER_TRIGGERED`
  - NOTE: Architecture specifies `STOPPER_TRIGGERED` for custom stoppers; patience can map to `MAX_ITERATIONS` since it's a built-in convergence criterion, not a custom stopper. Discuss in ADR-015 rationale.
- [x] 5.2 Update the evolution loop in `run()` (line 910+) — change `while not self._should_stop()` to capture the stop reason: `stop_reason = self._should_stop(); while stop_reason is None:` pattern, storing the final `stop_reason` when loop exits
- [x] 5.3 Handle the "completed all iterations" case: when max_iterations reached, `stop_reason = StopReason.MAX_ITERATIONS`; when loop completes without trigger (shouldn't happen since _should_stop checks max_iterations), default to `StopReason.COMPLETED`
- [x] 5.4 Update `_build_result()` to accept `stop_reason: StopReason` parameter and pass it to `EvolutionResult(stop_reason=stop_reason, ...)`
- [x] 5.5 Thread stop_reason through the `run()` → `_build_result()` call site

### Task 6: Write ADR-015 (AC: 7)

- [x] 6.1 Create `docs/adr/ADR-015-result-schema-versioning.md` following ADR-013 format (Status: Accepted, Date, Deciders)
- [x] 6.2 Document: Context (need for versioned serialization for cross-session comparison), Decision (frozen `schema_version: int = 1` on result types, `CURRENT_SCHEMA_VERSION` constant, domain-layer serialization), Design rules from architecture Decision 4 (`to_dict()` outputs version, `from_dict()` validates version), Rationale (stdlib only, hexagonal boundaries, frozen record), Consequences, Alternatives (Pydantic model versioning — rejected for external dep in domain layer; unversioned serialization — rejected for forward compat)
- [x] 6.3 Update `docs/adr/index.md` to include ADR-015 entry
- [x] 6.4 Note: `to_dict()`/`from_dict()` are NOT implemented in this story — that's Story 2.2. ADR-015 documents the decision; Story 2.2 implements serialization.

### Task 7: Update existing tests with schema_version assertions (AC: 10)

- [x] 7.0 **Discovery first:** Grep for `EvolutionResult(` and `MultiAgentEvolutionResult(` across ALL test files (`tests/`) to find every construction point. Do NOT rely solely on the named files below — the grep results are authoritative for finding all sites that need `schema_version == 1` assertions.
- [x] 7.1 In `tests/unit/domain/test_models.py`: Add `assert result.schema_version == 1` to `TestEvolutionResultFieldAccess`, `TestEvolutionResultComputedProperties`, `TestMultiAgentEvolutionResultComputedProperties`
- [x] 7.2 In `tests/contracts/test_evolution_result_protocol.py`: Add `schema_version` and `stop_reason` to protocol compliance tests. Add `assert isinstance(result, EvolutionResultProtocol)` tests that include the new fields.
- [x] 7.3 In `tests/contracts/test_objective_scores_models.py`: Add `schema_version == 1` assertions to backward compatibility tests
- [x] 7.4 In any integration tests or other test files discovered in 7.0 that assert on result fields: add `schema_version == 1` assertion

### Task 8: New tests for StopReason (AC: 9)

- [x] 8.1 Create test class `TestStopReasonEnum` in `tests/unit/domain/test_models.py` (or a new `test_stop_reason.py` — prefer existing file per project convention):
  - Test all 6 enum values exist and have correct string values
  - Test `StopReason` is a `str` subclass (enables JSON serialization)
  - Test enum membership: `StopReason("completed") == StopReason.COMPLETED`
- [x] 8.2 Create test class `TestEvolutionResultStopReason` in `tests/unit/domain/test_models.py`:
  - Test default `stop_reason` is `StopReason.COMPLETED`
  - Test explicit `stop_reason=StopReason.MAX_ITERATIONS` construction
  - Test `stop_reason` is accessible on frozen instance
  - Test `stop_reason` on `MultiAgentEvolutionResult` with same patterns
- [x] 8.3 Create test class `TestEngineStopReason` in `tests/unit/engine/` (new file `test_stop_reason.py` or in existing engine test file):
  - Test max_iterations triggers `StopReason.MAX_ITERATIONS`
  - Test patience exhaustion triggers appropriate stop reason
  - Test custom stopper triggers `StopReason.STOPPER_TRIGGERED`
  - Test baseline-only (max_iterations=0) case
  - Use `create_mock_adapter` from `tests/fixtures/adapters.py` for mock setup
  - Use existing conftest fixtures (`sample_config`, `sample_candidate`, `sample_batch`)
- [x] 8.4 Contract test: verify both result types with `stop_reason` still satisfy `EvolutionResultProtocol`

### Task 9: Validation and cleanup (AC: 8)

- [x] 9.1 Run full test suite: `pytest` — all tests pass, coverage >= 85%
- [x] 9.2 Run `ruff format` + `ruff check --fix`
- [x] 9.3 Run `docvet check` on all modified files
- [x] 9.4 Run `ty check src tests`
- [x] 9.5 Verify `__all__` updated in every modified module

- [ ] [TEA] Testing maturity: Add boundary test for StopReason enum exhaustiveness — verify that every StopReason value has at least one engine test covering it, preventing future enum additions without test coverage (cross-cutting, optional). **Partial: covers all 3 active values (COMPLETED, MAX_ITERATIONS, STOPPER_TRIGGERED); remaining 3 deferred to Story 2.4 when the engine sets them.**

## Dev Notes

### Architecture Compliance

This story implements **Architecture Decision 4** (Result Schema Versioning) and resolves **Gap 1** (Graceful termination with StopReason) from the architecture document. The architecture specifies:

- `StopReason(str, Enum)` with exactly 6 values — follow this precisely
- `schema_version: int = 1` as a frozen field — `CURRENT_SCHEMA_VERSION` constant
- Domain-layer placement (no external deps) — `StopReason` in `domain/types.py`, `schema_version` in `domain/models.py`
- Protocol update includes both fields per architecture impact analysis

The architecture doc (`_bmad-output/planning-artifacts/architecture.md`) lines 1375-1395 contain the complete specification including the enum definition, field additions, and protocol impact. **Read this section before implementing.**

### Critical Implementation Patterns

**Frozen dataclass field ordering:** New fields with defaults (`schema_version`, `stop_reason`) can go before fields without defaults in `kw_only=True` dataclasses. Place them first per architecture pattern:
```python
CURRENT_SCHEMA_VERSION = 1

@dataclass(slots=True, frozen=True, kw_only=True)
class EvolutionResult:
    schema_version: int = CURRENT_SCHEMA_VERSION
    stop_reason: StopReason = StopReason.COMPLETED
    original_score: float
    ...
```

**Engine `_should_stop` refactor:** The return type changes from `bool` to `StopReason | None`. This is the most invasive change. The evolution loop in `run()` must be updated from:
```python
while not self._should_stop():
    ...
```
to:
```python
stop_reason = self._should_stop()
while stop_reason is None:
    ...
    stop_reason = self._should_stop()
```

**MultiAgentEvolutionResult propagation in `api.py`:** Line 981 constructs `MultiAgentEvolutionResult` from `EvolutionResult` fields. Add `stop_reason=evolution_result.stop_reason` and `schema_version=evolution_result.schema_version` to the construction kwargs.

**Exception hierarchy:** If adding `ConfigurationError` raises for invalid schema versions (not in this story but ADR-015 mentions it), follow the `cause=e` + `from e` pattern from project-context.md.

### Stop Reason Mapping

| Termination Condition | Location | StopReason Value |
|---|---|---|
| `iteration >= max_iterations` | `_should_stop()` line 741 | `MAX_ITERATIONS` |
| `stagnation_counter >= patience` | `_should_stop()` line 746 | `MAX_ITERATIONS` |
| Custom stopper returns True | `_should_stop()` line 756 | `STOPPER_TRIGGERED` |
| Normal loop completion (all iterations run) | `run()` after loop | `COMPLETED` |
| Baseline-only (`max_iterations=0`) | `_should_stop()` first check | `MAX_ITERATIONS` |

**Note on patience mapping:** Patience-based early stopping maps to `MAX_ITERATIONS` (not `STOPPER_TRIGGERED`) because it's a built-in convergence criterion, not a user-provided custom stopper. The custom stopper path (`StopReason.STOPPER_TRIGGERED`) is reserved for objects implementing `StopperProtocol` passed via `stop_callbacks`. Document this rationale in ADR-015.

**Note on KEYBOARD_INTERRUPT, TIMEOUT, CANCELLED:** These are NOT set in this story. They're defined in the enum for Story 2.4 (Graceful Interrupt) and for future use. This story only uses `COMPLETED`, `MAX_ITERATIONS`, and `STOPPER_TRIGGERED`.

### Source Tree Components to Touch

**Domain layer (no external deps):**
- `src/gepa_adk/domain/types.py` — add `StopReason` enum + export
- `src/gepa_adk/domain/models.py` — add `CURRENT_SCHEMA_VERSION`, `schema_version`, `stop_reason` fields to both result types + export
- `src/gepa_adk/domain/__init__.py` — re-export `StopReason`, `CURRENT_SCHEMA_VERSION`

**Ports layer:**
- `src/gepa_adk/ports/evolution_result.py` — add `stop_reason`, `schema_version` to protocol

**Engine layer:**
- `src/gepa_adk/engine/async_engine.py` — refactor `_should_stop()` return type, update `_build_result()`, thread stop_reason through `run()`

**API layer:**
- `src/gepa_adk/api.py` — propagate `stop_reason` + `schema_version` in `MultiAgentEvolutionResult` construction (line 981)

**Package exports:**
- `src/gepa_adk/__init__.py` — export `StopReason`, `CURRENT_SCHEMA_VERSION`

**Documentation:**
- `docs/adr/ADR-015-result-schema-versioning.md` — new ADR
- `docs/adr/ADR-013-result-type-protocol.md` — remove deferral notes
- `docs/adr/index.md` — add ADR-015 entry

**Tests:**
- `tests/unit/domain/test_models.py` — new test classes + updated assertions
- `tests/unit/engine/test_stop_reason.py` — new engine stop reason tests (or add to existing engine test file)
- `tests/contracts/test_evolution_result_protocol.py` — updated protocol compliance
- `tests/contracts/test_objective_scores_models.py` — updated assertions

### Testing Standards Summary

- `pytestmark = pytest.mark.unit` at module top for unit tests, `pytest.mark.contract` for contract tests
- Tests grouped in classes: `TestStopReasonEnum`, `TestEvolutionResultStopReason`, `TestEngineStopReason`
- Use `create_mock_adapter` factory from `tests/fixtures/adapters.py` for engine tests
- `asyncio_mode = "auto"` — do NOT add `@pytest.mark.asyncio`
- Coverage must stay >= 85%
- `filterwarnings = ["error"]` — new warnings break CI
- Run `docvet check` on all modified source files

### Documentation Impact

- `docs/adr/ADR-015-result-schema-versioning.md` — NEW: documents schema versioning decision. Note: ADR-015 documents the full schema versioning decision for both this story and Story 2.2. Only `schema_version` and `StopReason` fields are implemented here; `to_dict()`/`from_dict()` are implemented in Story 2.2.
- `docs/adr/ADR-013-result-type-protocol.md` — UPDATE: remove deferral notes for stop_reason
- `docs/adr/index.md` — UPDATE: add ADR-015 entry
- No user-facing guide changes needed in THIS story — StopReason and schema_version are API-level additions. **Forward reference:** Story 2.2 (serialization) and Story 2.3 (display enhancements) will add user-facing documentation for these fields. Do NOT write user guides or getting-started updates here.
- CHANGELOG entry will be auto-generated by release-please from `feat` commit type

### Project Structure Notes

- `StopReason` belongs in `domain/types.py` alongside `FrontierType` — both are enums used across layers
- `CURRENT_SCHEMA_VERSION` belongs in `domain/models.py` alongside the result types it governs
- ADR-015 follows existing ADR numbering (last is ADR-014)
- All new exports must be added to `__all__` at file bottom per project convention
- Import boundaries: `domain/types.py` uses only stdlib (`enum`); `ports/evolution_result.py` imports from domain (allowed)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1] — Acceptance criteria with BDD format
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 4] — Result Schema Versioning design rules (lines 400-415)
- [Source: _bmad-output/planning-artifacts/architecture.md#Gap 1 resolved] — StopReason enum specification (lines 1375-1395)
- [Source: _bmad-output/planning-artifacts/architecture.md#Pattern 5] — Result Schema Versioning code pattern (lines 711-752)
- [Source: _bmad-output/project-context.md] — Coding standards, testing rules, import boundaries
- [Source: src/gepa_adk/domain/types.py#FrontierType] — Enum pattern to follow (str, Enum)
- [Source: src/gepa_adk/domain/models.py#EvolutionResult] — Line 320, frozen dataclass to modify
- [Source: src/gepa_adk/domain/models.py#MultiAgentEvolutionResult] — Line 450, frozen dataclass to modify
- [Source: src/gepa_adk/ports/evolution_result.py#EvolutionResultProtocol] — Line 67, protocol to update
- [Source: src/gepa_adk/engine/async_engine.py#_should_stop] — Line 725, termination logic to refactor
- [Source: src/gepa_adk/engine/async_engine.py#_build_result] — Line 887, result construction to update
- [Source: src/gepa_adk/api.py#line 981] — MultiAgentEvolutionResult construction to update
- [Source: docs/adr/ADR-013-result-type-protocol.md] — ADR to update (remove deferral notes)
- [Source: tests/unit/domain/test_models.py] — Existing result tests to augment
- [Source: tests/contracts/test_evolution_result_protocol.py] — Protocol compliance tests to update
- [Source: tests/fixtures/adapters.py] — Mock adapter factory for engine tests

### Git Intelligence

Recent commits on `main`:
```
0ae5c67 chore(bmad): epic 1A+1B retrospective and workflow improvements (#276)
486798b chore(main): release 1.0.1 (#275)
05b1e54 refactor(engine): eliminate all 7 ty type-narrowing workarounds (#274)
646a3bf chore(main): release 1.0.0 (#273)
f4cf65b fix(ci): add explicit target-branch and full bootstrap-sha
```

Epic 1A and 1B are fully complete. This is the first feature story (Epic 2). The codebase is at version 1.0.1 with 1856+ tests and 89%+ coverage. All CI pipelines trigger on `main`. Branch naming convention: `feat/2-1-add-stop-reason-schema-version`.

### Previous Story Intelligence (from Story 1B.6)

Key learnings from the last completed story:
1. **Line numbers are advisory** — Prior stories shifted code. Use grep patterns, not hardcoded line numbers.
2. **Documentation subtasks are mandatory** — docstrings and ADRs must be completed as part of AC.
3. **Clean sweep at the end** — Run a grep sweep for any stale references.
4. **No story refs in production code** — Don't reference "Story 2.1" in src/ files.
5. **Pre-commit hooks are strict** — Run full quality pipeline before committing.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

### Completion Notes List

### File List

- `src/gepa_adk/domain/types.py` — Added StopReason enum
- `src/gepa_adk/domain/models.py` — Added CURRENT_SCHEMA_VERSION, schema_version, stop_reason fields
- `src/gepa_adk/domain/__init__.py` — Re-exported StopReason, CURRENT_SCHEMA_VERSION
- `src/gepa_adk/__init__.py` — Re-exported StopReason, CURRENT_SCHEMA_VERSION
- `src/gepa_adk/ports/evolution_result.py` — Updated EvolutionResultProtocol
- `src/gepa_adk/engine/async_engine.py` — Refactored _should_stop(), _build_result(), run()
- `src/gepa_adk/api.py` — Propagated schema_version/stop_reason to MultiAgentEvolutionResult
- `docs/adr/ADR-015-result-schema-versioning.md` — NEW: schema versioning ADR
- `docs/adr/ADR-013-result-type-protocol.md` — Updated neutral consequence
- `docs/adr/index.md` — Added ADR-015 entry
- `tests/unit/domain/test_models.py` — Added TestStopReasonEnum, TestEvolutionResultStopReason, schema_version assertions
- `tests/unit/engine/test_stop_reason.py` — NEW: TestEngineStopReason (5 tests)
- `tests/contracts/test_evolution_result_protocol.py` — Added schema_version/stop_reason assertions
- `tests/contracts/test_objective_scores_models.py` — Added schema_version assertion
- `tests/contracts/test_protocol_method_signatures.py` — Updated EXPECTED_ATTRIBUTES

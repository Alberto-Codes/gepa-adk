# Story 2.4: Graceful Interrupt with Partial Results

Status: done
Branch: feat/2-4-graceful-interrupt-with-partial-results

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want Ctrl+C during evolution to return my best results so far,
so that long-running evolution runs don't lose progress when interrupted.

## Acceptance Criteria

1. **Engine catches `KeyboardInterrupt` and `asyncio.CancelledError`** — The `AsyncGEPAEngine.run()` method wraps the evolution loop in a `try/except` that catches both `KeyboardInterrupt` and `asyncio.CancelledError`. These are `BaseException` subclasses (Python 3.12+) and will not be caught by the existing fail-fast `except Exception` behavior for adapter errors.
2. **Partial `EvolutionResult` with `StopReason.KEYBOARD_INTERRUPT`** — On interrupt, a partial `EvolutionResult` is constructed via `_build_result(stop_reason=StopReason.KEYBOARD_INTERRUPT)`. For `asyncio.CancelledError`, use `StopReason.CANCELLED`. Note: catching `CancelledError` without re-raising means an `asyncio.Task` wrapping the engine will be marked as **completed** (not cancelled) — the caller receives a result instead of `CancelledError` propagation. This is intentional: partial results are more valuable than a cancellation exception.
3. **Best-so-far components preserved** — The partial result contains `evolved_components` from `_state.best_candidate.components` (the best candidate found before interruption).
4. **Completed iteration records preserved** — The partial result contains `iteration_history` with all fully completed iteration records (iterations that finished scoring and recording before the interrupt).
5. **Serialization works on partial results** — The partial result serializes correctly via `to_dict()` and deserializes via `from_dict()` with the interrupt `stop_reason` preserved.
6. **Stateless retry** — Re-running evolution after interrupt requires no cleanup. Engine instances are disposable; no global state is mutated by interrupt handling.
7. **Integration test with simulated interrupt** — Integration test uses a mock adapter that raises `KeyboardInterrupt` after N successful iterations. Test verifies: N iteration records in `iteration_history`, `stop_reason == StopReason.KEYBOARD_INTERRUPT`, `evolved_components` populated, `total_iterations == N`. Test is marked `pytest.mark.integration`.
8. **Works alongside `SignalStopper`** — The engine `try/except` handles immediate mid-operation interrupts (during an `await` call inside the loop body). `SignalStopper` continues to handle graceful inter-iteration stops (checked by `_should_stop()` between iterations). Both paths are complementary; neither interferes with the other.
9. **`asyncio.CancelledError` test** — Separate integration test verifies `asyncio.CancelledError` produces `stop_reason=StopReason.CANCELLED` with same partial result guarantees.
10. **Stopper cleanup guaranteed** — The existing `finally` block in `run()` ensures `_cleanup_stoppers()` runs even on interrupt. No changes needed to cleanup flow.
11. **Existing tests pass** — All ~1948+ tests continue to pass. No regressions.
12. **Docstring updated** — `run()` method docstring updated to document interrupt handling behavior, removing the "Fail-fast behavior: adapter exceptions are not caught" note for `BaseException` subclasses, and adding a note about partial results on interrupt.

## Tasks / Subtasks

### Task 1: Add interrupt handling to `AsyncGEPAEngine.run()` (AC: 1, 2, 10)

- [x] 1.1 Add `import asyncio` to the imports section of `async_engine.py` (after `import time`, before `from dataclasses`). Only `asyncio.CancelledError` is used from the module.
- [x] 1.2 Modify the `run()` method (currently lines 919-971) to catch `KeyboardInterrupt` and `asyncio.CancelledError` around the `_run_evolution_loop()` call. The catch block must be inside the existing `try/finally` so stopper cleanup still runs. Structure:
  ```python
  try:
      return await self._run_evolution_loop()
  except KeyboardInterrupt:
      logger.info("evolution.interrupted", iteration=self._state.iteration if self._state else 0)
      if self._state is None:
          raise
      return self._build_result(stop_reason=StopReason.KEYBOARD_INTERRUPT)
  except asyncio.CancelledError:
      logger.info("evolution.cancelled", iteration=self._state.iteration if self._state else 0)
      if self._state is None:
          raise
      return self._build_result(stop_reason=StopReason.CANCELLED)
  finally:
      self._cleanup_stoppers(setup_stoppers)
  ```
- [x] 1.3 **Edge case: interrupt before baseline** — If `_state is None` (interrupt happens during `_initialize_baseline()` before any iteration), re-raise the exception since there's no meaningful partial result to construct. The guard `if self._state is None: raise` handles this. Verified: `_state` is assigned atomically at `async_engine.py` line 465, AFTER both baseline `evaluate()` calls complete — so if interrupt hits during either baseline eval, `_state` is still `None`.
- [x] 1.4 **Edge case: interrupt during first iteration** — If `_state.iteration == 0` and `_state.iteration_history` is empty but baseline was scored, construct result with `total_iterations=0`, empty `iteration_history`, and baseline-only evolved_components. `_build_result()` handles this correctly already since `_state.best_candidate` defaults to the initial candidate.

### Task 2: Update `run()` docstring (AC: 12)

- [x] 2.1 Update the `run()` method docstring to document interrupt behavior:
  - In the description, add a bullet: "4. On `KeyboardInterrupt` or `asyncio.CancelledError`, return partial result"
  - Update `Returns:` to mention partial results on interrupt
  - Update `Raises:` to clarify that `KeyboardInterrupt` and `asyncio.CancelledError` are caught (not propagated) when engine state exists, but re-raised if interrupt occurs before baseline evaluation
  - Update `Note:` to replace "Fail-fast behavior: adapter exceptions are not caught" with "Fail-fast behavior: adapter `Exception` subclasses propagate unchanged. `KeyboardInterrupt` and `asyncio.CancelledError` (`BaseException` subclasses) are caught and converted to partial results with appropriate `StopReason`."

### Task 3: Integration test — `KeyboardInterrupt` partial result (AC: 3, 4, 7)

- [x] 3.1 Create a new test file `tests/integration/engine/test_engine_interrupt.py` with `pytestmark = pytest.mark.integration` at module top. This keeps interrupt tests separate from failure tests (different concern: interrupt ≠ failure).
- [x] 3.2 Create a helper adapter class `InterruptingAdapter` that:
  - Extends or mimics the mock adapter pattern from `test_async_engine_failure.py`
  - Must implement the full `AsyncGEPAAdapter` protocol surface: `evaluate()`, `make_reflective_dataset()`, and `propose_new_texts()` — the engine calls all three during the evolution loop
  - Accepts `interrupt_after: int` (number of successful evaluations before raising)
  - Counts evaluations and raises `KeyboardInterrupt` on the (N+1)th `evaluate()` call
  - Returns predictable increasing scores for successful evaluations (e.g., `0.5 + 0.05 * call_count`)
  - `propose_new_texts()` returns modified component text (e.g., `f"Evolved iteration {call_count}"`)
  - Also accepts `interrupt_type: type = KeyboardInterrupt` to reuse for `CancelledError` tests
- [x] 3.3 Create test class `TestKeyboardInterruptPartialResult`:
  - `test_interrupt_returns_partial_result` — Interrupt after 3 successful iterations. Verify `isinstance(result, EvolutionResult)`, `result.stop_reason == StopReason.KEYBOARD_INTERRUPT`, `len(result.iteration_history) >= 1` (at least 1 completed iteration before interrupt).
  - `test_interrupt_preserves_best_components` — Verify `result.evolved_components` is populated and contains the component keys from the initial candidate.
  - `test_interrupt_preserves_iteration_history` — Verify each `IterationRecord` in the history has valid `score`, `accepted`, and `evolved_components` fields.
  - `test_interrupt_total_iterations_matches_history` — Verify `result.total_iterations` is consistent (equals the iteration count at interruption).
  - `test_interrupt_serialization_round_trip` — Call `result.to_dict()`, verify `stop_reason` is `"keyboard_interrupt"` in dict, then `EvolutionResult.from_dict(d)` and verify all fields match.
  - `test_interrupt_scores_consistent` — Verify `result.original_score` is the baseline and `result.final_score` is the best score seen (>= original if any iteration was accepted).

### Task 4: Integration test — `asyncio.CancelledError` partial result (AC: 9)

- [x] 4.1 Create test class `TestCancelledErrorPartialResult` in same file:
  - `test_cancelled_returns_partial_result` — Same pattern as KeyboardInterrupt test but adapter raises `asyncio.CancelledError`. Verify `result.stop_reason == StopReason.CANCELLED`.
  - `test_cancelled_serialization_round_trip` — Verify serialization preserves `"cancelled"` stop_reason.

### Task 5: Integration test — Edge cases and mid-iteration interrupt (AC: 1, 6, 8)

- [x] 5.1 Create test class `TestInterruptEdgeCases` in same file:
  - `test_interrupt_before_baseline_raises` — Adapter raises `KeyboardInterrupt` on the very first `evaluate()` call (baseline). Since `_state` hasn't been fully initialized (`_state` is assigned atomically at line 465 of `async_engine.py`, AFTER both baseline evaluations complete), the engine should re-raise `KeyboardInterrupt` (no partial result possible). Verify `pytest.raises(KeyboardInterrupt)`.
  - `test_interrupt_mid_iteration_excludes_incomplete` — Adapter succeeds for N complete iterations, then raises `KeyboardInterrupt` during the (N+1)th iteration's evaluation call (before `_record_iteration()` is called for that iteration). Verify result has exactly N iteration records — the incomplete iteration is NOT included. This is the highest-risk real-world scenario (90% of Ctrl+C hits land during long-running LLM evaluation awaits).
  - `test_stateless_retry_after_interrupt` — After receiving a partial result from an interrupted run, create a new `AsyncGEPAEngine` instance and run again successfully. Verify the second run completes normally with `stop_reason != StopReason.KEYBOARD_INTERRUPT`.
  - `test_stopper_cleanup_on_interrupt` — Use a mock stopper that tracks `setup()`/`teardown()` calls. Verify `teardown()` is called even when `KeyboardInterrupt` occurs mid-evolution. (This tests the existing `finally` block works with interrupt handling.)

### Task 6: Validation and cleanup (AC: 11)

- [x] 6.1 Run full test suite: `pytest` — all tests pass (1964 passed)
- [x] 6.2 Run `ruff format` + `ruff check --fix`
- [x] 6.3 Run `docvet check` on `src/gepa_adk/engine/async_engine.py`
- [x] 6.4 Run `ty check src tests`
- [x] 6.5 Verify no new public symbols need `__all__` updates (no new classes/functions exported)

- [ ] [TEA] Testing maturity: Add unit test for `_build_result()` called with each `StopReason` variant — verify all 6 enum values produce valid `EvolutionResult` objects with correct `stop_reason` field. Currently `_build_result()` is only tested indirectly through `run()`. (cross-cutting, optional)

## Dev Notes

### Architecture Compliance

This story adds interrupt handling to the engine layer. Key architectural constraints:

- **Engine layer imports**: `asyncio` is stdlib — safe for engine layer. No new external dependencies.
- **Domain layer unchanged**: No changes to `EvolutionResult`, `StopReason`, or any domain models. All required types already exist.
- **Fail-fast preserved for adapter errors**: Only `KeyboardInterrupt` and `asyncio.CancelledError` (`BaseException` subclasses) are caught. Regular `Exception` subclasses from adapters still propagate unchanged. This maintains the existing fail-fast contract.
- **No Protocol changes**: Interrupt handling is an engine implementation detail, not a port/adapter contract.
- **No `__all__` changes**: No new public symbols.
- **No schema version bump**: No domain model changes.

### Key Design Decisions

1. **Catch in `run()`, not `_run_evolution_loop()`**: The `run()` method already has the `try/finally` for stopper cleanup. Adding the `except` clauses here keeps all lifecycle management in one place and ensures cleanup runs for all exit paths (normal, exception, interrupt).

2. **Separate `StopReason` for `KeyboardInterrupt` vs `CancelledError`**: `KEYBOARD_INTERRUPT` for user-initiated Ctrl+C, `CANCELLED` for programmatic task cancellation (e.g., `asyncio.Task.cancel()`). These are semantically different: one is user intent, the other is framework/orchestration intent. **`CancelledError` suppression note**: Catching `CancelledError` without re-raising means an `asyncio.Task` wrapping the engine will be marked as completed (not cancelled). The caller receives a partial `EvolutionResult` instead of a `CancelledError`. This is intentional — if someone wraps the engine in `asyncio.wait_for()`, the timeout will succeed with a partial result rather than raising `asyncio.TimeoutError`.

3. **`TIMEOUT` is NOT handled here**: `StopReason.TIMEOUT` is the domain of the existing `TimeoutStopper` (checked between iterations via `_should_stop()`). This story does NOT catch `asyncio.TimeoutError`. If a future story needs timeout-based partial results from `asyncio.wait_for()`, it would be handled separately.

4. **Re-raise if `_state is None`**: If the interrupt happens before `_initialize_baseline()` completes, there's no baseline score, no candidate, and no meaningful result to return. Re-raising is the correct behavior — the caller never got a chance to start evolution. Verified: `_state` is assigned atomically after both baseline evals complete.

5. **Integration tests, not unit tests**: The interrupt behavior involves async execution, adapter interaction, and result construction across multiple methods. Integration tests with mock adapters are the right abstraction level. Unit-testing `_build_result()` in isolation is covered by the TEA optional task.

6. **New test file**: `test_engine_interrupt.py` is separate from `test_async_engine_failure.py` because interrupt handling and failure handling are orthogonal concerns. Interrupts return results; failures propagate exceptions.

### Critical Implementation Patterns

**Engine `run()` structure after change:**
```python
async def run(self) -> EvolutionResult:
    self._start_time = time.monotonic()
    self._total_evaluations = 0
    setup_stoppers = self._setup_stoppers()

    try:
        return await self._run_evolution_loop()
    except KeyboardInterrupt:
        logger.info("evolution.interrupted",
                     iteration=self._state.iteration if self._state else 0)
        if self._state is None:
            raise
        return self._build_result(stop_reason=StopReason.KEYBOARD_INTERRUPT)
    except asyncio.CancelledError:
        logger.info("evolution.cancelled",
                     iteration=self._state.iteration if self._state else 0)
        if self._state is None:
            raise
        return self._build_result(stop_reason=StopReason.CANCELLED)
    finally:
        self._cleanup_stoppers(setup_stoppers)
```

**InterruptingAdapter test helper pattern:**
```python
class InterruptingAdapter:
    def __init__(self, interrupt_after: int, interrupt_type: type = KeyboardInterrupt):
        self._interrupt_after = interrupt_after
        self._interrupt_type = interrupt_type
        self._call_count = 0

    async def evaluate(self, batch, candidate, capture_traces=False):
        self._call_count += 1
        if self._call_count > self._interrupt_after:
            raise self._interrupt_type()
        score = 0.5 + 0.05 * self._call_count
        return EvaluationBatch(
            outputs=[None] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
        )

    async def propose_new_texts(self, *args, **kwargs):
        return {"instruction": f"Evolved iteration {self._call_count}"}
```

**Python 3.12+ `asyncio.CancelledError` semantics:**
- `asyncio.CancelledError` is a `BaseException` (not `Exception`) since Python 3.9
- A bare `except Exception:` will NOT catch it — our handler must explicitly name it
- It is safe to catch and suppress (return a result instead of re-raising) — the task is already being cancelled, and returning a value from the coroutine is valid
- If the engine is running inside an `asyncio.Task`, catching `CancelledError` prevents the task from being marked as cancelled — it will be marked as completed with the returned result

**Interaction with SignalStopper:**
```
Ctrl+C pressed during evolution:

Case A — Between iterations (engine idle, checking _should_stop):
  1. SignalStopper._handle_signal() sets _stop_requested = True
  2. _should_stop() returns StopReason.STOPPER_TRIGGERED
  3. Loop exits normally, _build_result(STOPPER_TRIGGERED) called
  4. No exception involved

Case B — During await (LLM call, scoring, etc.):
  1. KeyboardInterrupt raised at the await point
  2. Engine's except KeyboardInterrupt catches it
  3. _build_result(KEYBOARD_INTERRUPT) called
  4. Partial result returned

Both paths return EvolutionResult — caller sees no difference in result type.
```

### Source Tree Components to Touch

**Engine layer:**
- `src/gepa_adk/engine/async_engine.py` — Add `import asyncio`, modify `run()` method to catch `KeyboardInterrupt` and `asyncio.CancelledError`, update `run()` docstring.

**Tests:**
- `tests/integration/engine/test_engine_interrupt.py` (NEW) — `InterruptingAdapter` helper, `TestKeyboardInterruptPartialResult`, `TestCancelledErrorPartialResult`, `TestInterruptEdgeCases` test classes.

### Documentation Impact

- No documentation impact (confirmed). Interrupt handling is an engine implementation detail.
- `run()` docstring update is covered in Task 2.
- No ADR needed — this implements an already-planned feature described in the architecture doc (Gap 1 resolution for 99%+ completion NFR).
- CHANGELOG entry will be auto-generated by release-please from `feat` commit type.

### Project Structure Notes

- **One new file**: `tests/integration/engine/test_engine_interrupt.py` — follows existing test structure pattern (see `test_async_engine_failure.py` for reference).
- **One modified file**: `src/gepa_adk/engine/async_engine.py` — minimal change (~15 lines added to `run()`).
- No new dependencies in `pyproject.toml`.
- No `__init__.py` updates needed.
- Import boundaries respected: engine imports only `asyncio` (stdlib).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4] — Acceptance criteria with BDD format
- [Source: _bmad-output/planning-artifacts/architecture.md#Gap 1 resolution] — StopReason enum + partial result on interrupt design
- [Source: _bmad-output/project-context.md] — Coding standards, testing rules, import boundaries
- [Source: src/gepa_adk/engine/async_engine.py#run() (line 919)] — Method to modify with interrupt handling
- [Source: src/gepa_adk/engine/async_engine.py#_build_result() (line 888)] — Already accepts stop_reason parameter
- [Source: src/gepa_adk/engine/async_engine.py#_run_evolution_loop() (line 973)] — Evolution loop to wrap
- [Source: src/gepa_adk/domain/types.py#StopReason (line 358)] — KEYBOARD_INTERRUPT and CANCELLED already defined
- [Source: src/gepa_adk/adapters/stoppers/signal.py] — SignalStopper for inter-iteration graceful stops
- [Source: tests/integration/engine/test_async_engine_failure.py] — Existing test patterns for engine failure scenarios
- [Source: _bmad-output/implementation-artifacts/2-3-evolution-result-display-enhancements.md] — Previous story patterns and learnings

### Git Intelligence

Recent commits on `main`:
```
66cc7a4 feat(domain): add display methods and original_components to evolution results (#297)
6589a0b feat(domain): add result serialization with to_dict/from_dict
536073a feat(domain): add StopReason enum and schema versioning to evolution results
```

Stories 2.1, 2.2, and 2.3 are complete and merged. `StopReason` enum (including `KEYBOARD_INTERRUPT` and `CANCELLED`), `to_dict()`/`from_dict()`, `_build_result(stop_reason=...)`, `original_components`, and display methods all exist. This story adds the engine-level interrupt handling that these types were designed for.

Branch naming convention: `feat/2-4-graceful-interrupt-with-partial-results`

### Previous Story Intelligence (from Story 2.3)

Key learnings:
1. **Line numbers are advisory** — Prior stories shifted code. Use grep patterns, not hardcoded line numbers.
2. **Documentation subtasks are mandatory** — docstrings must be completed as part of AC.
3. **Pre-commit hooks are strict** — Run full quality pipeline before committing.
4. **Discovery first** — Grep across ALL test files before deciding where to add tests.
5. **Test count**: 1948 tests currently passing (as of Story 2.3). Interrupt tests should not break any.
6. **`asyncio` is NOT imported in `async_engine.py`** — Must add `import asyncio` explicitly.
7. **Engine has no existing `except` blocks in `run()`** — The only control flow is `try/finally` for stopper cleanup.
8. **`_state` can be `None`** — `_state` is set during `_initialize_baseline()` inside `_run_evolution_loop()`. If interrupt occurs before baseline completes, `_state` is `None`.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation with no debugging needed.

### Completion Notes List

- Added `import asyncio` to `async_engine.py` (Task 1.1)
- Added `except KeyboardInterrupt` and `except asyncio.CancelledError` blocks to `run()` inside the existing `try/finally` (Task 1.2-1.4). Both catch blocks log the event, re-raise if `_state is None` (pre-baseline interrupt), and otherwise return partial `EvolutionResult` via `_build_result()`.
- Updated `run()` docstring: added step 4 for interrupt handling, updated Returns/Raises/Note sections (Task 2.1).
- Created `tests/integration/engine/test_engine_interrupt.py` with `InterruptingAdapter` helper and 12 integration tests across 3 test classes (Tasks 3-5).
- All 1964 tests pass with 0 regressions. Ruff, docvet, and ty checks pass cleanly.

### AC-to-Test Mapping

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 (catches KeyboardInterrupt + CancelledError) | `test_interrupt_returns_partial_result`, `test_cancelled_returns_partial_result`, `test_interrupt_before_baseline_raises` | PASS |
| AC2 (partial result with StopReason) | `test_interrupt_returns_partial_result`, `test_cancelled_returns_partial_result` | PASS |
| AC3 (best-so-far components) | `test_interrupt_preserves_best_components` | PASS |
| AC4 (completed iteration records) | `test_interrupt_preserves_iteration_history`, `test_interrupt_total_iterations_matches_history` | PASS |
| AC5 (serialization) | `test_interrupt_serialization_round_trip`, `test_cancelled_serialization_round_trip` | PASS |
| AC6 (stateless retry) | `test_stateless_retry_after_interrupt` | PASS |
| AC7 (integration test) | `TestKeyboardInterruptPartialResult` (6 tests) | PASS |
| AC8 (works alongside SignalStopper) | `test_stopper_cleanup_on_interrupt` | PASS |
| AC9 (CancelledError test) | `TestCancelledErrorPartialResult` (2 tests) | PASS |
| AC10 (stopper cleanup) | `test_stopper_cleanup_on_interrupt` | PASS |
| AC11 (existing tests pass) | Full suite: 1964 passed | PASS |
| AC12 (docstring updated) | Manual verification + docvet check | PASS |

### File List

- `src/gepa_adk/engine/async_engine.py` — Modified: added `import asyncio`, interrupt handling in `run()`, updated docstring
- `tests/integration/engine/test_engine_interrupt.py` — New: 12 integration tests for interrupt handling
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Modified: status updated to in-progress

## Change Log

- 2026-03-04: Implemented graceful interrupt handling for `AsyncGEPAEngine.run()`. Added `KeyboardInterrupt` and `asyncio.CancelledError` exception handlers that return partial `EvolutionResult` with appropriate `StopReason`. Created 12 integration tests covering normal interrupts, edge cases, serialization, and stopper cleanup. All 1964 tests pass.
- 2026-03-04: **Code review completed.** Fixed 3 issues: (1) Added missing `assert len(iteration_history) == 2` count assertion in `test_interrupt_mid_iteration_excludes_incomplete`; (2) Extracted `_run_interrupted_engine()` helper to eliminate test setup duplication across 6 tests; (3) Changed weak negative assertion to positive `assert result2.stop_reason == StopReason.MAX_ITERATIONS` in retry test. Fixed story doc typo (`cleanup()` → `make_reflective_dataset()`). Status → done.

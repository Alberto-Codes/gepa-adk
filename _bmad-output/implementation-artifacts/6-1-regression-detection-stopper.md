# Story 6.1: Regression Detection Stopper

Branch: feat/stoppers-6-1-regression-detection-stopper
Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want evolution to stop automatically if scores consistently decline,
so that I don't waste compute on evolution runs that are degrading.

## Acceptance Criteria

1. `adapters/stoppers/regression.py` exists and contains `RegressionStopper` implementing `StopperProtocol` via structural subtyping (no inheritance)
2. The stopper detects score decline: when `best_score` at iteration N is lower than `best_score` at iteration N-K (configurable lookback `window`, default `window=3`)
3. When regression is detected, `__call__` returns `True`, which causes the engine to set `stop_reason = StopReason.STOPPER_TRIGGERED` (engine handles this automatically — stopper just returns `True`)
4. `RegressionStopper` can be composed with existing stoppers via `CompositeStopper`
5. `RegressionStopper` is added to `tests/contracts/test_stopper_protocol.py` `TestStopperProtocolRuntimeCheckable` class (convention: one contract file per Protocol, not per implementation)
6. Unit tests at `tests/unit/adapters/stoppers/test_regression.py` cover: regression with default window, custom window, no regression with improving scores, edge case with insufficient history
7. `RegressionStopper` is exported from `gepa_adk.adapters.stoppers` and from `gepa_adk` top-level

## Tasks / Subtasks

- [x] Task 1: Implement `RegressionStopper` (AC: 1, 2, 3, 4)
  - [x] 1.1 Create `src/gepa_adk/adapters/stoppers/regression.py`
  - [x] 1.2 Implement as a **plain class** (NOT dataclass — all other stoppers use plain classes):
    ```python
    class RegressionStopper:
        def __init__(self, *, window: int = 3) -> None:
            if window < 1:
                raise ConfigurationError(...)
            self.window = window
            self._score_history: list[float] = []
    ```
  - [x] 1.3 Validate `window >= 1` in `__init__` — raise `ConfigurationError` with `field="window"`, `value=window`, `constraint="Must be >= 1"`
  - [x] 1.4 Implement `__call__(self, state: StopperState) -> bool`:
    - Append `state.best_score` to `_score_history`
    - If `len(_score_history) <= window`, return `False` (insufficient history)
    - Return `_score_history[-1] < _score_history[-(window + 1)]`
  - [x] 1.5 Implement `setup(self) -> None` that clears `self._score_history = []` — engine calls this at the start of each run, making the stopper safe to reuse across multiple evolution runs
  - [x] 1.6 Add module-level docstring and `__all__ = ["RegressionStopper"]` at file BOTTOM
  - [x] 1.7 Add structlog event on detection: `logger.info("stopper.regression.triggered", window=self.window, current_score=..., baseline_score=...)`

- [x] Task 2: Wire exports (AC: 7)
  - [x] 2.1 Add `from gepa_adk.adapters.stoppers.regression import RegressionStopper` to `adapters/stoppers/__init__.py` and include in its `__all__`
  - [x] 2.2 Add `RegressionStopper` to `adapters/__init__.py` re-exports and `__all__`
  - [x] 2.3 Add `RegressionStopper` to `gepa_adk/__init__.py` imports and `__all__`
  - [x] 2.4 Update `docs/guides/stoppers.md` — add `RegressionStopper` to the Available Stoppers table: `| \`RegressionStopper(window)\` | Stop when score declines over N iterations | Detecting degrading runs |`

- [x] Task 3: Contract test (AC: 5)
  - [x] 3.1 Add `RegressionStopper` to `tests/contracts/test_stopper_protocol.py` → `TestStopperProtocolRuntimeCheckable` class: add `test_regression_stopper_satisfies_protocol` asserting `isinstance(RegressionStopper(), StopperProtocol)`
  - [x] 3.2 Do NOT create a new `test_regression_stopper_contract.py` — convention is one contract file per Protocol (Story 3.2 standard). Behavioral tests for `RegressionStopper` belong in unit tests (Task 4)

- [x] Task 4: Unit tests (AC: 6)
  - [x] 4.1 Create `tests/unit/adapters/stoppers/test_regression.py`
  - [x] 4.2 Set `pytestmark = pytest.mark.unit` at module level
  - [x] 4.3 Create `make_state(best_score, iteration=0)` helper fixture or factory
  - [x] 4.4 `TestRegressionStopperInitialization` — valid init, `window=1`, `window=3` (default), `window=0` raises `ConfigurationError`, `window=-1` raises `ConfigurationError`
  - [x] 4.5 `TestRegressionStopperBehavior` — core scenarios:
    - Insufficient history returns False (< window+1 calls)
    - Exactly at window+1 calls: regression detected returns True
    - Exactly at window+1 calls: no regression returns False
    - Improving scores: never returns True
    - Custom window (window=5): needs 6 calls before detection
  - [x] 4.6 `TestRegressionStopperEdgeCases` — boundary and corner cases:
    - `window=1`: detects single-step regression immediately (after 2 calls)
    - Scores flat (plateau): `0.8, 0.8, 0.8, 0.8` — equal is NOT a regression (not `<`)
    - Same stopper instance called N >> window times: history grows but detection still uses last vs. N-K, does not reset
    - Scores recover then decline: `[0.5, 0.6, 0.7, 0.4]` with window=3 — 0.4 < 0.5 → True
  - [x] 4.7 `TestRegressionStopperComposition` — compose with `CompositeStopper`:
    - `CompositeStopper([RegressionStopper(window=3), ScoreThresholdStopper(0.99)], mode="any")` — returns `isinstance(..., StopperProtocol)` and works correctly
  - [x] 4.8 `TestRegressionStopperProtocolCompliance` — `isinstance(RegressionStopper(), StopperProtocol)` is True; `__call__` returns `bool`
- [x] Task 5: Final verification (AC: 1–7)
  - [x] 5.1 Run `uv run pytest tests/contracts/ -x` — all green, count >= 453 (454 passed)
  - [x] 5.2 Run `uv run pytest tests/unit/adapters/stoppers/ -x` — all green
  - [x] 5.3 Run `uv run pytest` — zero regressions from full suite (2147 passed, 1 skipped)
  - [x] 5.4 Verify `from gepa_adk import RegressionStopper` works in a Python REPL
  - [x] 5.5 Run `uv run ty check src` — exits 0
  - [x] 5.6 Run `python scripts/check_protocol_coverage.py` — still 12/12 (RegressionStopper is an implementation, not a new Protocol — no new contract test file mapping needed for the coverage script)

- [x] Task 6: Instance reuse safety test (AC: implied by setup() lifecycle)
  - [x] 6.1 In `TestRegressionStopperEdgeCases`, add `test_setup_clears_history`: call stopper 4 times (trigger regression), call `stopper.setup()`, then call again — verify history is cleared and stopper no longer fires immediately
  - [x] 6.2 Verify engine calls `setup()` at start of each run (read `async_engine.py` `_setup_stoppers()` — already calls `setup()` if present via `getattr`)

- [ ] [TEA] Testing maturity: add a test verifying that `CompositeStopper` correctly propagates `setup()` calls to all child stoppers including `RegressionStopper` (engine only calls `setup()` on top-level stoppers, not nested ones — verify this is handled or document the limitation). (cross-cutting, optional)

## Dev Notes

### Critical Architecture Insight: StopperState Has No Score History

`StopperState` (in `src/gepa_adk/domain/stopper.py`) contains:
```python
@dataclass(frozen=True, slots=True)
class StopperState:
    iteration: int
    best_score: float          # ← only the current best
    stagnation_counter: int
    total_evaluations: int
    candidates_count: int
    elapsed_seconds: float
```

There is NO score history in `StopperState`. `RegressionStopper` MUST track `best_score` across calls internally. This is the same stateful pattern as `SignalStopper` (which tracks `_stop_requested` across calls).

### Implementation Pattern

**Use a plain class — NOT a dataclass.** All existing stoppers (`ScoreThresholdStopper`, `TimeoutStopper`, `SignalStopper`, etc.) use plain classes with `__init__`. Do not deviate from this pattern.

```python
class RegressionStopper:
    """Stops evolution when best score declines over a lookback window.

    Detects regression by comparing the current best score to the best score
    from ``window`` iterations ago. Returns ``True`` (stop) when the current
    score is strictly lower than the score ``window`` steps prior.

    Requires at least ``window + 1`` calls before any regression can be detected.
    Call ``setup()`` (or let the engine call it) to reset history between runs.

    Args:
        window: Number of iterations to look back for comparison. Must be >= 1.
            Default is 3.
    """

    def __init__(self, *, window: int = 3) -> None:
        if window < 1:
            raise ConfigurationError(
                f"RegressionStopper window must be >= 1, got {window}",
                field="window",
                value=window,
                constraint="Must be >= 1",
            )
        self.window = window
        self._score_history: list[float] = []

    def setup(self) -> None:
        """Reset score history. Called by engine at start of each run."""
        self._score_history = []

    def __call__(self, state: StopperState) -> bool:
        self._score_history.append(state.best_score)
        if len(self._score_history) <= self.window:
            return False
        current = self._score_history[-1]
        baseline = self._score_history[-(self.window + 1)]
        if current < baseline:
            logger.info(
                "stopper.regression.triggered",
                window=self.window,
                current_score=current,
                baseline_score=baseline,
            )
            return True
        return False


__all__ = ["RegressionStopper"]
```

### Regression Logic Verification

Window=3 example with history `[0.5, 0.6, 0.7, 0.4]` (4 calls):
- After call 1: history=[0.5], len=1 ≤ 3 → False (cold start)
- After call 2: history=[0.5, 0.6], len=2 ≤ 3 → False
- After call 3: history=[0.5, 0.6, 0.7], len=3 ≤ 3 → False
- After call 4: history=[0.5, 0.6, 0.7, 0.4], len=4 > 3 → compare history[-1]=0.4 vs history[-4]=0.5 → 0.4 < 0.5 → **True** ✅

Equal scores (plateau `[0.8, 0.8, 0.8, 0.8]`):
- After call 4: history[-1]=0.8, history[-4]=0.8 → 0.8 < 0.8 → **False** (equal is NOT regression) ✅

### How Engine Handles stop_reason

The engine automatically sets `StopReason.STOPPER_TRIGGERED` when ANY stopper in `config.stop_callbacks` returns `True`. The `RegressionStopper` just needs to return `True` — no additional code needed to set stop reason. See `src/gepa_adk/engine/async_engine.py` → `_should_stop()`.

### Lifecycle: setup() Required for Instance Reuse Safety

`RegressionStopper` implements `setup()` to clear `_score_history`. The engine calls `setup()` at the start of each run (via `getattr` check in `_setup_stoppers()`). This makes the stopper safe to reuse across multiple `evolve()` calls with the same instance. Without `setup()`, history from run N would bleed into run N+1.

### Exception Pattern (for __init__ validation)

```python
from gepa_adk.domain.exceptions import ConfigurationError

raise ConfigurationError(
    f"RegressionStopper window must be >= 1, got {self.window}",
    field="window",
    value=self.window,
    constraint="Must be >= 1",
)
```

No `cause=e` or `from e` needed — this is a direct raise, not wrapping another exception.

### Export Chain

```
adapters/stoppers/regression.py
  └─ adapters/stoppers/__init__.py  (add RegressionStopper)
       └─ adapters/__init__.py       (add RegressionStopper)
            └─ gepa_adk/__init__.py  (add RegressionStopper)
```

Verify all four `__all__` lists are updated. Check `test_adapter_reexports.py` for the existing reexport test pattern.

### Contract Test Convention (Overrides Epic AC)

The epics AC specified `tests/contracts/test_regression_stopper_contract.py` but this was written before Story 3.2 established the **one-file-per-Protocol** standard. `RegressionStopper` is an *implementation*, not a new Protocol. Convention takes precedence:
- Add `RegressionStopper` isinstance check to **existing** `test_stopper_protocol.py` → `TestStopperProtocolRuntimeCheckable`
- All behavioral tests go in unit tests (`tests/unit/adapters/stoppers/test_regression.py`)
- Do NOT create a new contract file for this implementation

### Structlog Usage

```python
import structlog

logger = structlog.get_logger(__name__)
```

Event name: `stopper.regression.triggered` (dot-notation per python.md conventions).

### Documentation Impact

`RegressionStopper` is a new public API symbol exported from `gepa_adk`. Impact:
- **API docs**: mkdocstrings auto-generates from docstring — no manual docs work needed. Ensure the class docstring is complete (Args, Returns via `__call__` docstring).
- **Changelog**: `feat(stoppers):` commit type will trigger a changelog entry in v2.2.0 — no extra work.
- **CONTRIBUTING/guides**: `docs/guides/stoppers.md` has an Available Stoppers table — add `RegressionStopper(window)` | Stop when score declines over N iterations | Detecting degrading runs. **This is required, not optional.**
- No ADR required (fits existing Decision 6: keep direct instantiation, no factory).

### Previous Story Learnings (from Epic 3)

**Story 3.1 (Critic Preset Factory):**
- Export chain must update ALL four `__all__` lists — checked via `test_adapter_reexports.py`
- `ConfigurationError` fields: `field`, `value`, `constraint` (no `suggestion` field)
- Model handling with conditional kwargs — not relevant here but pattern useful

**Story 3.2 (Contract Test Gaps):**
- Three-class template: `TestXxxRuntimeCheckable`, `TestXxxBehavior`, `TestXxxNonCompliance`
- `pytestmark = pytest.mark.contract` at module level
- Import Protocol from `gepa_adk.ports`, not internal module
- Document `runtime_checkable` limitation: only checks method existence, not signature

**Story 3.3 (Extension Point Docs):**
- Public API imports: `from gepa_adk import RegressionStopper` (NOT `from gepa_adk.adapters.stoppers import ...`) in examples

### Project Structure Notes

**New files:**
- `src/gepa_adk/adapters/stoppers/regression.py` — new stopper implementation
- `tests/unit/adapters/stoppers/test_regression.py` — unit tests

**Modified files:**
- `src/gepa_adk/adapters/stoppers/__init__.py` — add `RegressionStopper` export
- `src/gepa_adk/adapters/__init__.py` — add `RegressionStopper` re-export
- `src/gepa_adk/__init__.py` — add `RegressionStopper` re-export
- `tests/contracts/test_stopper_protocol.py` — add `RegressionStopper` to `TestStopperProtocolRuntimeCheckable`
- `tests/unit/adapters/test_adapter_reexports.py` — add `RegressionStopper` re-export test
- `docs/guides/stoppers.md` — add `RegressionStopper` to Available Stoppers table
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — status update
- `_bmad-output/implementation-artifacts/6-1-regression-detection-stopper.md` — task tracking

### References

- [Source: src/gepa_adk/ports/stopper.py — StopperProtocol definition]
- [Source: src/gepa_adk/domain/stopper.py — StopperState dataclass (no score history)]
- [Source: src/gepa_adk/adapters/stoppers/signal.py — stateful stopper pattern with internal `_stop_requested`]
- [Source: src/gepa_adk/adapters/stoppers/threshold.py — plain class stopper pattern, ConfigurationError usage]
- [Source: src/gepa_adk/adapters/stoppers/composite.py — CompositeStopper for AC4]
- [Source: src/gepa_adk/adapters/stoppers/__init__.py — export pattern to follow]
- [Source: src/gepa_adk/engine/async_engine.py — how _should_stop() handles STOPPER_TRIGGERED]
- [Source: src/gepa_adk/domain/types.py — StopReason enum values]
- [Source: src/gepa_adk/domain/exceptions.py — ConfigurationError (field, value, constraint only)]
- [Source: tests/contracts/test_stopper_protocol.py — three-class template exemplar]
- [Source: tests/unit/adapters/stoppers/test_threshold.py — unit test pattern]
- [Source: tests/unit/adapters/test_adapter_reexports.py — reexport test pattern]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 6 — stopper registration]
- [Source: _bmad-output/project-context.md — arch rules, exception patterns, structlog usage]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

### Completion Notes List

- Implemented `RegressionStopper` as a plain class (matching pattern of all existing stoppers) with `window` parameter (default 3), stateful `_score_history`, and strict less-than comparison for regression detection.
- Export chain updated across all four `__all__` lists: `regression.py` → `stoppers/__init__.py` → `adapters/__init__.py` → `gepa_adk/__init__.py`.
- Contract test added to existing `test_stopper_protocol.py` (one-file-per-Protocol convention from Story 3.2).
- 21 unit tests covering initialization, core behavior, edge cases (plateau, recovery/decline, long history), composition, instance reuse via `setup()`, and protocol compliance.
- `docs/guides/stoppers.md` Available Stoppers table updated with `RegressionStopper(window)`.
- `test_adapter_reexports.py` updated with `RegressionStopper` re-export identity test.
- All tests green: 2147 passed, 454 contract tests, ty check clean, 12/12 protocol coverage.
- Pre-review party-mode research identified `CompositeStopper` missing `setup()` propagation — fixed with 15-line addition to `composite.py` and a multi-run reuse test. Final suite: 2148 passed.

### File List

- `src/gepa_adk/adapters/stoppers/regression.py` (new)
- `src/gepa_adk/adapters/stoppers/composite.py` (modified — added setup() propagation to children)
- `src/gepa_adk/adapters/stoppers/__init__.py` (modified)
- `src/gepa_adk/adapters/__init__.py` (modified)
- `src/gepa_adk/__init__.py` (modified)
- `tests/unit/adapters/stoppers/test_regression.py` (new)
- `tests/contracts/test_stopper_protocol.py` (modified)
- `tests/unit/adapters/test_adapter_reexports.py` (modified)
- `docs/guides/stoppers.md` (modified)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified)
- `_bmad-output/implementation-artifacts/6-1-regression-detection-stopper.md` (modified)

## Change Log

- 2026-03-11: Code review applied 3 fixes: (1) Added `test_composite_all_short_circuit_skips_regression_history` test documenting that `mode="all"` short-circuit prevents `RegressionStopper` history accumulation when listed second; (2) Added stateful stopper ordering caveat to `CompositeStopper.__call__` docstring; (3) Added dedicated `RegressionStopper` section to `docs/guides/stoppers.md` covering cold-start, plateau, instance reuse, and composition ordering. Fixed misleading "unchanged" comment in `adapters/__init__.py`. Suite: 2149 passed, 1 skipped.
- 2026-03-11: Implemented `RegressionStopper` — new stopper that detects score regression over a configurable lookback window. Added full export chain, contract test (to existing file), 21 unit tests, docs update, and re-export identity test. All 2147 tests pass, zero regressions.

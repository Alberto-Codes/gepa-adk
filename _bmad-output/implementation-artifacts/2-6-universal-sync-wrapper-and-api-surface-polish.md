# Story 2.6: Universal Sync Wrapper and API Surface Polish

Status: done
Branch: feat/2-6-universal-sync-wrapper-and-api-surface-polish

## Story

As a developer working in scripts or REPLs,
I want a single sync wrapper for any async evolution call,
so that I don't need to manage asyncio boilerplate.

## Acceptance Criteria

1. **Given** `evolve_sync()` currently exists wrapping only `evolve()`, **when** the universal sync wrapper is implemented, **then** `run_sync(coroutine)` wraps any async `evolve_*()` call using `asyncio.run()` with `nest_asyncio` fallback.

2. **Given** backward compatibility matters, **when** `run_sync` is available, **then** `evolve_sync()` is retained as a deprecated alias pointing to `run_sync(evolve(...))` and emits a `DeprecationWarning`.

3. **Given** public API discoverability, **when** `run_sync` is implemented, **then** `run_sync` is exported in `gepa_adk.__init__.py.__all__`.

4. **Given** Jupyter has a running event loop, **when** `run_sync()` documentation is written, **then** the Jupyter incompatibility is documented (use `await evolve(...)` directly in Jupyter instead).

5. **Given** API consistency goals, **when** the `evolve()` signature is updated, **then** a `*` keyword-only separator is placed after `trainset` for optional parameters (breaking change).

6. **Given** API consistency, **when** `evolve_group()` and `evolve_workflow()` signatures are updated, **then** they similarly use `*` keyword-only separator after their last required positional parameter.

## Tasks / Subtasks

- [x] Task 1: Implement `run_sync()` universal wrapper (AC: 1, 4)
  - [x] 1.1: Create `run_sync(coro: Coroutine[Any, Any, T]) -> T` function in `api.py` that accepts any coroutine and returns its result
  - [x] 1.2: Primary path: `asyncio.run(coro)` (standard case, no running event loop)
  - [x] 1.3: Fallback: catch `RuntimeError("cannot be called from a running event loop")` and apply `nest_asyncio.apply()` + create a new event loop via `loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)` then `loop.run_until_complete(coro)`. Do NOT use deprecated `asyncio.get_event_loop()` (deprecated since Python 3.10; triggers warning under `filterwarnings = ["error"]`)
  - [x] 1.4: If `nest_asyncio` not installed, raise `RuntimeError` with installation instructions (same as current behavior)
  - [x] 1.5: Add Google-style docstring with `Note:` section documenting Jupyter incompatibility: use `await evolve(...)` directly in notebooks instead of `run_sync(evolve(...))`
  - [x] 1.6: Type the return value as generic `T` using `TypeVar` so IDE autocompletion works: `run_sync(evolve(...))` returns `EvolutionResult`, `run_sync(evolve_group(...))` returns `MultiAgentEvolutionResult`
  - [x] 1.7: Parameter type MUST be `Coroutine[Any, Any, T]` — not `Awaitable[T]`. `asyncio.run()` requires a coroutine specifically. If a non-coroutine is passed, Python's type checker catches it statically, but add a runtime `if not asyncio.iscoroutine(coro)` guard raising `TypeError` with a clear message for untyped callers

- [x] Task 2: Deprecate `evolve_sync()` (AC: 2)
  - [x] 2.1: Rewrite `evolve_sync()` body to emit `warnings.warn("evolve_sync() is deprecated, use run_sync(evolve(...)) instead", DeprecationWarning, stacklevel=2)` then delegate to `run_sync(evolve(agent, trainset, **kwargs))`
  - [x] 2.2: Update `evolve_sync()` docstring: add `.. deprecated::` note pointing to `run_sync()`
  - [x] 2.3: Keep `evolve_sync` in `__all__` of both `api.py` and `__init__.py` (removing it would break imports)
  - [x] 2.4: Add `"ignore::DeprecationWarning"` filter to `pyproject.toml` `[tool.pytest.ini_options] filterwarnings` for the specific `evolve_sync` message so that the existing `filterwarnings = ["error"]` doesn't break tests that still use `evolve_sync()`

- [x] Task 3: Add keyword-only separator to `evolve()` (AC: 5)
  - [x] 3.1: Change `evolve()` signature from `async def evolve(agent, trainset, valset=None, ...)` to `async def evolve(agent, trainset, *, valset=None, ...)`
  - [x] 3.2: Update `evolve()` docstring to note keyword-only requirement for optional params
  - [x] 3.3: Search tests for any positional calls to `evolve()` beyond the first two args and convert to keyword syntax — grep for `evolve(` across `tests/` (all calls already used keyword args)

- [x] Task 4: Add keyword-only separator to `evolve_group()` (AC: 6)
  - [x] 4.1: Change `evolve_group()` signature from `async def evolve_group(agents, primary, trainset, components=None, ...)` to `async def evolve_group(agents, primary, trainset, *, components=None, ...)`
  - [x] 4.2: Update docstring similarly
  - [x] 4.3: Fix any positional calls in tests (all calls already used keyword args)

- [x] Task 5: Add keyword-only separator to `evolve_workflow()` (AC: 6)
  - [x] 5.1: Change `evolve_workflow()` signature from `async def evolve_workflow(workflow, trainset, critic=None, ...)` to `async def evolve_workflow(workflow, trainset, *, critic=None, ...)`
  - [x] 5.2: Update docstring similarly
  - [x] 5.3: Fix any positional calls in tests (all calls already used keyword args)

- [x] Task 6: Update exports (AC: 3)
  - [x] 6.1: Add `run_sync` to `__all__` in `api.py` (api.py has no `__all__` — not applicable)
  - [x] 6.2: Add `from gepa_adk.api import run_sync` and `"run_sync"` to `__all__` in `gepa_adk/__init__.py`
  - [x] 6.3: Verify `evolve_sync` remains in both `__all__` lists

- [x] Task 7: Write tests (AC: 1-6)
  - [x] 7.1: Create `tests/unit/test_run_sync.py` with class `TestRunSync` — test the wrapper mechanics with mock coroutines, NOT the full evolution pipeline. Create a simple `async def dummy() -> str: return "ok"` helper and verify `run_sync(dummy())` returns `"ok"`. This keeps tests fast and unit-scoped.
    - `test_run_sync_returns_coroutine_result()` — verify return value from a mock async function
    - `test_run_sync_with_typed_return()` — verify generic `T` return type works (returns exact type)
  - [x] 7.2: Class `TestEvolveSyncDeprecation`:
    - `test_evolve_sync_emits_deprecation_warning()` — `pytest.warns(DeprecationWarning, match="run_sync")`
  - [x] 7.3: Class `TestKeywordOnlySeparator` — use `inspect.signature()` for robust verification:
    - `test_evolve_optional_params_are_keyword_only()` — verify via `sig.parameters[name].kind == Parameter.KEYWORD_ONLY` for all optional params
    - `test_evolve_group_optional_params_are_keyword_only()` — same for evolve_group
    - `test_evolve_workflow_optional_params_are_keyword_only()` — same for evolve_workflow
  - [x] 7.4: Class `TestRunSyncErrorHandling`:
    - `test_run_sync_without_nest_asyncio_raises_informative_error()` — mock import failure, verify error message contains "nest-asyncio"
    - `test_run_sync_propagates_non_event_loop_runtime_errors()` — non-event-loop RuntimeErrors propagate unchanged
    - `test_run_sync_rejects_non_coroutine()` — `run_sync(42)` raises `TypeError` with clear message
    - `test_run_sync_rejects_function_not_call()` — `run_sync(some_func)` raises `TypeError`
  - [x] 7.5: Class `TestRunSyncNestedLoop` (REQUIRED, not optional):
    - `test_run_sync_fallback_with_running_event_loop()` — mock a running event loop scenario, verify `nest_asyncio` fallback path executes and returns correct result
  - [x] 7.6: Verify all existing tests still pass after signature changes (1907 passed, no regressions)

- [x] Task 8: Run quality pipeline (AC: all)
  - [x] 8.1: `ruff format && ruff check --fix`
  - [x] 8.2: `docvet check` — 0 findings, 100% coverage on api.py and __init__.py
  - [x] 8.3: `ty check src tests` — all checks passed
  - [x] 8.4: `pytest` — 1907 passed (1888 baseline + 12 new + 7 pre-existing)
  - [x] 8.5: Verify `__all__` updated in all modified modules

- [x] [TEA] Testing maturity: Existing `evolve_sync` tests (3 in test_api.py) pass through deprecated path. Updated test_evolve_sync_nested_event_loop_handling to match new `asyncio.new_event_loop()` pattern. (cross-cutting, optional)

## Dev Notes

### Architecture Compliance

- **Layer placement**: `run_sync()` belongs in `api.py` — the ONLY file that may contain sync wrappers (ADR-001, project-context.md line 70-71). Do NOT create sync wrappers anywhere else.
- **Import boundaries**: `run_sync` imports only stdlib (`asyncio`, `warnings`, `typing`). The `nest_asyncio` import is lazy (inside the except block), matching the current `evolve_sync` pattern.
- **Exception pattern**: If `nest_asyncio` is missing, raise `RuntimeError` (not `ConfigurationError`) — this is an environment setup issue, not an evolution config issue.
- **No new dependencies**: `nest_asyncio >= 1.6.0` is already in `pyproject.toml`.
- **Async guarantee preserved**: `run_sync` is `def` (sync). All evolution functions remain `async def`. ADR-001 is maintained.
- **Generic typing**: Use `TypeVar("T")` for return type so `run_sync(evolve(...))` correctly narrows to `EvolutionResult` in IDE.

### Key Design Decisions

1. **Universal `run_sync` over per-function wrappers**: Instead of `evolve_sync`, `evolve_group_sync`, `evolve_workflow_sync` (3 functions to maintain), one `run_sync(coro)` wraps any coroutine. This follows the UX spec's design and reduces API surface.

2. **DeprecationWarning for `evolve_sync`**: Use `warnings.warn()` with `stacklevel=2` so the warning points to the caller's code, not to the `evolve_sync` function itself. The `DeprecationWarning` category is correct (not `FutureWarning`) since this is a developer-facing API.

3. **Keyword-only separator is a breaking change on a 1.x release**: Any caller passing optional args positionally (e.g., `evolve(agent, trainset, valset)`) will get `TypeError`. This is intentional per the epic spec. Grep tests thoroughly — all three functions need fixing. **Semver impact**: Since the project is on 1.0.1, this is a breaking change requiring a MAJOR version bump. Use `feat(api)!:` (with `!`) in the commit message so release-please creates a 2.0.0 release. The PR description must explicitly note the breaking change under a `BREAKING CHANGE:` footer.

4. **pyproject.toml filterwarnings update**: Since `filterwarnings = ["error"]` is set, the new `DeprecationWarning` from `evolve_sync` will fail any test that calls `evolve_sync`. Add a specific ignore filter: `"ignore:evolve_sync\\(\\) is deprecated:DeprecationWarning"`. This lets the deprecation tests use `pytest.warns()` while not breaking other tests.

5. **Coroutine parameter, not function+args**: `run_sync` takes a coroutine object (`run_sync(evolve(agent, trainset))`) not a callable+args (`run_sync(evolve, agent, trainset)`). This is simpler and matches Python conventions (`asyncio.run()` also takes a coroutine).

6. **No Jupyter special-casing in `run_sync`**: The `nest_asyncio` fallback handles the nested event loop case. Document that `await evolve(...)` is preferred in Jupyter. Do NOT try to auto-detect Jupyter.

### Previous Story Intelligence (from Story 2.5)

- **Test count baseline**: 1888 tests passing (1838 unit+contract + 50 new from Story 2.5). Story 2.6 must not regress this.
- **Pre-flight validation**: All three entry points now have `_pre_flight_validate_*()` functions. These are synchronous `def` functions called before the async work. The keyword-only separator change does NOT affect pre-flight validation — it only changes the caller's interface.
- **Quality pipeline**: `ruff format`, `ruff check --fix`, `docvet check`, `ty check src tests` before committing.
- **Branch convention**: `feat/2-6-universal-sync-wrapper-and-api-surface-polish`
- **Commit convention**: `feat(api)!: add universal sync wrapper and keyword-only signatures` — the `!` is REQUIRED because the keyword-only separator is a breaking change on a 1.x release. This triggers a MAJOR version bump (1.0.1 -> 2.0.0) via release-please. Include a `BREAKING CHANGE:` footer in the commit body listing: keyword-only optional params for `evolve()`, `evolve_group()`, `evolve_workflow()`.
- **ConfigurationError pattern**: keyword-only `__init__` with `field`, `value`, `constraint`. Not used in this story (RuntimeError for env issues instead).
- **`evolve_sync` current implementation** (lines 1947-2051 of `api.py`): Uses `asyncio.run()` primary + `nest_asyncio.apply()` fallback. Extract this logic into `run_sync()` and have `evolve_sync` delegate.

### Git Intelligence (from recent commits)

- `b019f7a feat(api): add pre-flight validation enhancements` — latest commit, modified `api.py` and `domain/models.py`
- `e892fc0 feat(engine): add graceful interrupt handling` — modified engine, added interrupt handling
- `66cc7a4 feat(domain): add display methods and original_components` — modified domain models
- `6589a0b feat(domain): add result serialization with to_dict/from_dict` — serialization support
- `536073a feat(domain): add StopReason enum and schema versioning` — schema versioning
- Pattern: Each story has been a clean, focused PR. Follow this pattern.

### Current `evolve_sync` Implementation Reference

The current `evolve_sync()` (lines 1947-2051 in `api.py`) does:
1. Takes `agent`, `trainset`, `**kwargs`
2. Tries `asyncio.run(evolve(agent, trainset, **kwargs))`
3. On `RuntimeError` (running event loop): tries `import nest_asyncio; nest_asyncio.apply(); loop.run_until_complete(evolve(...))`
4. If `nest_asyncio` not available: raises `RuntimeError` with install instructions

Extract this logic into `run_sync(coro)` with one fix: replace `asyncio.get_event_loop()` (deprecated since Python 3.10) with `asyncio.new_event_loop()` + `asyncio.set_event_loop(loop)` in the fallback path. The deprecated call triggers `DeprecationWarning` which fails under our `filterwarnings = ["error"]` config. Then have `evolve_sync` call `run_sync(evolve(agent, trainset, **kwargs))` with a deprecation warning.

### Current Signatures (for reference)

```python
# api.py line 1500
async def evolve(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    valset: list[dict[str, Any]] | None = None,   # <-- add * before this
    critic: LlmAgent | None = None,
    ...
) -> EvolutionResult:

# api.py line 833
async def evolve_group(
    agents: dict[str, LlmAgent],
    primary: str,
    trainset: list[dict[str, Any]],
    components: dict[str, list[str]] | None = None,  # <-- add * before this
    ...
) -> MultiAgentEvolutionResult:

# api.py line 1235
async def evolve_workflow(
    workflow: SequentialAgent | LoopAgent | ParallelAgent,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,  # <-- add * before this
    ...
) -> MultiAgentEvolutionResult:

# api.py line 1947
def evolve_sync(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    **kwargs: Any,
) -> EvolutionResult:
```

### Documentation Impact

- **Docstring updates**: `evolve()`, `evolve_group()`, `evolve_workflow()` — note keyword-only requirement in `Args:` section
- **`run_sync` docstring**: Full Google-style docstring with `Note:` for Jupyter incompatibility
- **`evolve_sync` docstring**: Add `.. deprecated::` note
- **No external docs impact**: `run_sync` is a simple utility; getting-started guide can be updated separately (Story 8.2)
- **No ADR needed**: This implements existing ADR-001 (async-first) and ADR-015 (keyword-only separator) decisions
- **CHANGELOG**: `feat(api)!: add universal sync wrapper and keyword-only signatures` will trigger a MAJOR version changelog entry (2.0.0) due to the `!` breaking change indicator. The `BREAKING CHANGE:` footer lists: optional params for `evolve()`, `evolve_group()`, `evolve_workflow()` are now keyword-only after positional required args.

### Project Structure Notes

- All changes in existing files — no new source files
- New test file: `tests/unit/test_run_sync.py`
- `pyproject.toml` update: add deprecation warning filter
- `src/gepa_adk/api.py` — add `run_sync()`, modify `evolve_sync()`, add `*` to three signatures
- `src/gepa_adk/__init__.py` — add `run_sync` to imports and `__all__`
- No `domain/`, `ports/`, `adapters/`, `engine/` changes expected

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2, Story 2.6]
- [Source: _bmad-output/planning-artifacts/architecture.md#ADR-001 Async-First]
- [Source: _bmad-output/planning-artifacts/architecture.md#Pattern 6: Public API Extension Recipe]
- [Source: _bmad-output/planning-artifacts/architecture.md#Cross-Cutting Concerns - Async propagation]
- [Source: _bmad-output/project-context.md#Async rules (line 70-71)]
- [Source: src/gepa_adk/api.py#evolve_sync() (lines 1947-2051)]
- [Source: src/gepa_adk/api.py#evolve() (line 1500), evolve_group() (line 833), evolve_workflow() (line 1235)]
- [Source: _bmad-output/implementation-artifacts/2-5-pre-flight-validation-enhancements.md#Dev Notes]

## AC-to-Test Mapping

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 - run_sync wraps any async evolve call | TestRunSync (test_run_sync_returns_coroutine_result, test_run_sync_with_typed_return), TestRunSyncNestedLoop (test_run_sync_fallback_with_running_event_loop) | PASS |
| AC2 - evolve_sync deprecated alias | TestEvolveSyncDeprecation (test_evolve_sync_emits_deprecation_warning) | PASS |
| AC3 - run_sync exported in __all__ | Verified via `from gepa_adk import run_sync` in test imports | PASS |
| AC4 - Jupyter incompatibility documented | run_sync docstring Note: section documents Jupyter limitation | PASS (documentation) |
| AC5 - evolve() keyword-only separator | TestKeywordOnlySeparator (test_evolve_optional_params_are_keyword_only) | PASS |
| AC6 - evolve_group/workflow keyword-only | TestKeywordOnlySeparator (test_evolve_group_optional_params_are_keyword_only, test_evolve_workflow_optional_params_are_keyword_only) | PASS |

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No debug issues encountered.

### Completion Notes List

- Created `run_sync()` universal wrapper in `api.py` with `asyncio.run()` primary path and `nest_asyncio` fallback using `asyncio.new_event_loop()` (not deprecated `get_event_loop()`)
- Added runtime `asyncio.iscoroutine()` guard for non-coroutine arguments with clear TypeError message
- Deprecated `evolve_sync()` with `DeprecationWarning` (stacklevel=2) delegating to `run_sync(evolve(...))`
- Added `Warns:` section to `evolve_sync()` docstring for docvet compliance
- Added `*` keyword-only separator to `evolve()`, `evolve_group()`, `evolve_workflow()` after required positional params
- Split docstrings into `Args:` (positional) and `Keyword Args:` (keyword-only) sections for all three functions
- Exported `run_sync` in `gepa_adk/__init__.py` imports and `__all__`
- Updated `api.py` module docstring to reference `run_sync()` instead of `evolve_sync()`
- Updated `__init__.py` module docstring to note `evolve_sync` deprecation and `run_sync` addition
- Added deprecation warning filter to `pyproject.toml` so existing `evolve_sync` tests don't break
- Updated existing `test_evolve_sync_nested_event_loop_handling` test to match new `asyncio.new_event_loop()` pattern
- 12 new tests in `tests/unit/test_run_sync.py`; 1907 total tests pass (no regressions)
- Quality pipeline clean: ruff format/check, docvet check (0 findings), ty check (all passed)

### Change Log

- 2026-03-05: Implemented universal sync wrapper and API surface polish (Story 2.6) — run_sync(), evolve_sync() deprecation, keyword-only signatures for all three entry points

### File List

- src/gepa_adk/api.py (modified) — added run_sync(), rewrote evolve_sync() with deprecation, added * keyword-only separator to evolve/evolve_group/evolve_workflow, updated docstrings with Keyword Args sections
- src/gepa_adk/__init__.py (modified) — added run_sync import and __all__ entry, updated module docstring
- pyproject.toml (modified) — added evolve_sync deprecation warning filter
- tests/unit/test_run_sync.py (new) — 12 unit tests for run_sync, deprecation, keyword-only signatures, error handling
- tests/unit/test_api.py (modified) — updated test_evolve_sync_nested_event_loop_handling for new_event_loop pattern

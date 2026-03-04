# Story 1B.5: Eliminate ty Type-Narrowing Workarounds

Status: done
Branch: refactor/1b-5-eliminate-ty-type-narrowing-workarounds

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a contributor,
I want the evaluation pipeline's return types to be fully ty-resolvable without inline suppressions,
So that ty provides complete type safety across the codebase and new regressions are caught at the type level.

## Acceptance Criteria

1. **Runtime arity dispatch eliminated in `engine/proposer.py`** — The `inspect.signature()` dispatch between 2-param and 3-param reflection function calls is removed. The `ReflectionFn` type alias is redefined to 3-param: `Callable[[str, list[dict[str, Any]], str], Awaitable[str]]`. All 3 `ty: ignore` comments in `proposer.py` (lines 282, 283, 289) are removed. `ReflectionFn` is engine-internal (not part of public API surface) — use `refactor(engine):` commit type, NOT `BREAKING CHANGE:` footer, to avoid unnecessary major version bump.
2. **Union return unpacking resolved in `adapters/evolution/multi_agent.py`** — The `_run_single_example()` union return type `tuple[str, list, dict] | tuple[str, dict]` is replaced with `@overload` declarations using `Literal[True]`/`Literal[False]` on `capture_events` that ty can narrow. Both `ty: ignore[invalid-assignment]` comments (lines 880, 895) are removed.
3. **Dead `event.session` code removed from `multi_agent.py`** — The `hasattr(event, "session")` guard blocks (lines 1102-1105, 1235-1238) are confirmed dead code (ADK `Event` class has no `session` attribute, confirmed via `extra='forbid'` on the Pydantic model) and deleted entirely. Both `ty: ignore[no-matching-overload]` comments are removed with the code. Session state extraction, if needed, follows the `AgentExecutor` pattern of re-fetching via session service.
4. **Zero `ty: ignore` comments in src/** — `grep -rn "ty: ignore" src/gepa_adk/ --include="*.py"` returns zero hits. The docstring reference on `proposer.py:214` is also updated to reflect the new approach.
5. **`uv run ty check src` exits 0** — No new ignores or suppressions introduced.
6. **`uv run ty check src tests` exits 0** — Tests also pass type checking.
7. **All existing tests pass with no behavior changes** — Full test suite green, coverage >= 85%.
8. **Dead parameter cleanup (Tech Debt td-001, td-002)** — Remove dead `session_service` parameter and dead `output_field` parameter from `create_adk_reflection_fn()` in `engine/adk_reflection.py`. Update all callers (~42+ call sites across 13 test files, 2 source files) and docstrings.
9. **Nullable trajectories explicitly OUT OF SCOPE** — The epics BDD mentioned changing `list | None` to always-initialized `list` and adding a `Result` dataclass. These patterns do NOT produce `ty: ignore` comments (the `assert` narrowing satisfies ty). Deferred to a dedicated cleanup story to minimize blast radius.

## Tasks / Subtasks

**Execution order:** Task 1 (dead params) -> Tasks 2-3 (ReflectionFn, **atomic — single commit**) -> Task 4 (dead event.session code) -> Task 5 (@overload) -> Tasks 6-7 (docs + validate). Run tests after each task.

- [x] Task 1: Clean up dead parameters in `create_adk_reflection_fn()` (AC: 8)
  - [x] 1.1 Remove `session_service` parameter from `create_adk_reflection_fn()` in `engine/adk_reflection.py`
  - [x] 1.2 Remove `output_field` parameter
  - [x] 1.3 Update `api.py` callers — remove `session_service` kwarg from `create_adk_reflection_fn()` calls
  - [x] 1.4 Update ALL test callers passing `session_service=...` (~42 call sites across 13 test files)
  - [x] 1.5 Update docstring in `create_adk_reflection_fn()` — remove Args entries for `session_service` and `output_field`
  - [x] 1.6 Update docstring examples that show `session_service` parameter
  - [x] 1.7 Run `uv run docvet check src/gepa_adk/engine/adk_reflection.py` — no findings
  - [x] 1.8 Run `uv run pytest` — all 1855 tests pass

- [x] Task 2: Redefine `ReflectionFn` to 3-param in `engine/proposer.py` (AC: 1, 4)
  - [x] 2.1 Redefine `ReflectionFn` type alias to `Callable[[str, list[dict[str, Any]], str], Awaitable[str]]`
  - [x] 2.2 Remove `inspect.signature()` dispatch block, replace with direct 3-param call
  - [x] 2.3 Remove `import inspect` from `proposer.py`
  - [x] 2.4 Update `ReflectionFn` docstring — always 3 parameters
  - [x] 2.5 `__all__` — no changes needed (name unchanged)
  - [x] 2.6 `engine/__init__.py` — no changes needed (name unchanged)
  - [x] 2.7 Update 2-param mock in `test_multi_agent_executor_contract.py`
  - [x] 2.8 Update all other 2-param reflection mocks in tests
  - [x] 2.9 `uv run ty check src` — exits 0
  - [x] 2.10 `uv run pytest` — all tests pass

- [x] Task 3: Update reflection function factory to return 3-param signature (AC: 1)
  - [x] 3.1 Change inner `reflect()` signature from `component_name: str | None = None` to `component_name: str = ""`
  - [x] 3.2 Return type annotation references `ReflectionFn` (now 3-param) — verified match
  - [x] 3.3 Update docstrings to reflect 3-param signature
  - [x] 3.4 `uv run ty check src && uv run pytest` — green

- [x] Task 4: Delete dead `event.session` extraction code in `multi_agent.py` (AC: 3, 4)
  - [x] 4.1 Verified `Event` has no `session` attribute (Pydantic `extra='forbid'`)
  - [x] 4.2 Deleted `hasattr(event, "session")` block from `_run_shared_session()`
  - [x] 4.3 Deleted identical block from `_run_isolated_sessions()`
  - [x] 4.4 Verified downstream callers — session state obtained via AgentExecutor (Path A)
  - [x] 4.5 Verified `test_multi_agent_state_extraction.py` passes (7 tests, executor path)
  - [x] 4.6 `uv run ty check src && uv run pytest` — green

- [x] Task 5: Resolve union return unpacking in `multi_agent.py` with `@overload` (AC: 2, 4)
  - [x] 5.1 Added `Literal, overload` to `typing` import
  - [x] 5.2 Verified RUF038 not active (requires ruff preview mode, not enabled)
  - [x] 5.3 Added `@overload` declarations on `_run_single_example()`
  - [x] 5.4 Added `@overload` declarations on `_run_shared_session()` and `_run_isolated_sessions()`
  - [x] 5.5 Removed both `ty: ignore[invalid-assignment]` comments
  - [x] 5.6 Call sites use literal `True`/`False` — ty narrows correctly
  - [x] 5.7 `uv run ty check src` — zero diagnostics
  - [x] 5.8 `uv run pytest` — all tests pass

- [x] Task 6: Update docstrings and documentation (AC: 4)
  - [x] 6.1 Updated `propose()` docstring Note section — direct 3-param call description
  - [x] 6.2 Updated second Note section — removed `inspect.signature` dispatch description
  - [x] 6.3 Reviewed `docs/guides/reflection-prompts.md` — no changes needed
  - [x] 6.4 `uv run docvet check` — zero findings on all modified source files

- [x] Task 7: Validate and finalize (AC: 4, 5, 6, 7)
  - [x] 7.1 `grep -rn "ty: ignore" src/gepa_adk/` — zero hits
  - [x] 7.2 `uv run ty check src` — exits 0
  - [x] 7.3 `uv run ty check src tests` — exits 0
  - [x] 7.4 `uv run pytest --cov=src --cov-fail-under=85` — 1855 passed, 89.34% coverage
  - [x] 7.5 `uv run ruff check . && uv run ruff format --check .` — clean
  - [x] 7.6 `uv run docvet check` — zero findings
  - [x] 7.7 `pre-commit run --all-files` — all 9 hooks green
  - [x] 7.8 Removed tech_debt td-001 and td-002 from `sprint-status.yaml`
  - [x] 7.9 Using `refactor(engine):` commit type

## Dev Notes

### ty: ignore Inventory (7 comments, 3 patterns)

| # | File | Line | Suppress Rule | Pattern | Fix Strategy |
|---|------|------|---------------|---------|--------------|
| 1 | `engine/proposer.py` | 282 | `invalid-argument-type` | Runtime arity dispatch | Redefine ReflectionFn to 3-param, direct call |
| 2 | `engine/proposer.py` | 283 | `too-many-positional-arguments` | Runtime arity dispatch | Same — remove inspect.signature block |
| 3 | `engine/proposer.py` | 289 | `invalid-argument-type` | Runtime arity dispatch | Same — remove 2-param branch entirely |
| 4 | `multi_agent.py` | 880 | `invalid-assignment` | Union return unpacking | @overload with Literal[True]/Literal[False] |
| 5 | `multi_agent.py` | 895 | `invalid-assignment` | Union return unpacking | Same — ty narrows overload return type |
| 6 | `multi_agent.py` | 1105 | `no-matching-overload` | Dead event.session code | Delete dead hasattr block (Event has no session) |
| 7 | `multi_agent.py` | 1238 | `no-matching-overload` | Dead event.session code | Delete dead hasattr block |

### Party Mode Consensus Decisions (Full Panel — 2026-03-04)

**Panel: BMad Master, Winston (Architect), Amelia (Developer), Bob (SM), John (PM), Quinn (QA), Murat (Test Architect), Paige (Tech Writer), Mary (Analyst), Sally (UX), Barry (Quick Flow)**

**Decision 1: Redefine `ReflectionFn` (unanimous)**
Redefine existing `ReflectionFn` type alias from 2-param to 3-param. Do NOT create a second type `ReflectionFnWithComponent`. Rationale: The inner `reflect()` closure already accepts 3 params. The 2-param alias was always inaccurate. Only 1 explicit 2-param mock exists in tests. Clean break, not dual types.

**Decision 2: Delete dead `event.session` code (unanimous with verification condition)**
ADK `Event` class has NO `session` attribute (`extra='forbid'` Pydantic model). The `hasattr(event, "session")` blocks in `_run_shared_session` and `_run_isolated_sessions` never execute at runtime. Delete the code entirely instead of casting/wrapping. Add a verification test confirming `Event` lacks `session` across ADK version matrix. If session state is needed, use the AgentExecutor pattern (re-fetch session from session service).

**Decision 3: Nullable trajectories OUT OF SCOPE (unanimous)**
The epics BDD mentioned changing `list | None` to always-initialized `list` and adding a `Result` dataclass to `domain/types.py`. These patterns do NOT produce `ty: ignore` comments — the `assert trajectories is not None` pattern satisfies ty. Deferred to a dedicated cleanup story to minimize blast radius (both adapters, EvaluationBatch, dozens of tests).

**Decision 4: Dead params in this story, single PR (majority)**
Story 1B.4 explicitly deferred td-001/td-002 to "Story 1B.5 or a dedicated tech-debt pass." Keep in scope. Single PR — the 42+ test kwarg removals are mechanical find-and-replace.

**Decision 5: Task execution order (adopted per Murat)**
Task 1 (dead params, highest churn, independent) -> Tasks 2-3 (ReflectionFn type + factory) -> Task 4 (dead code deletion with verification) -> Task 5 (@overload, most complex type change) -> Tasks 6-7 (docs + validation). Run tests after each task for incremental confidence.

**Additional items surfaced (Round 1):**
- Paige: Add subtask to review `docs/guides/reflection-prompts.md` after signature changes
- Murat: Add verification test for `Event` having no `session` attribute before deletion
- Murat: Check `RUF038` ruff rule status — it simplifies `Literal[True, False]` to `bool` which breaks @overload narrowing
- Paige: ~~`BREAKING CHANGE:` footer needed in commit~~ (reversed in Round 2)

### Second Round Review Refinements (Full Panel — 2026-03-04)

**Refinement 1: Do NOT use `BREAKING CHANGE:` footer (unanimous)**
`ReflectionFn` is engine-internal, not part of the public API surface. Using `BREAKING CHANGE:` or `feat!` would trigger release-please to bump 1.0.0 → 2.0.0 unnecessarily. Use `refactor(engine):` commit type instead. Reverses Paige's Round 1 suggestion after deeper analysis.

**Refinement 2: Add dev note about two-path session state structure (unanimous)**
Task 4 context must explain: Path A (executor, works — re-fetches session from service) vs Path B (legacy event iteration, dead — `hasattr(event, "session")` never executes). Deleting Path B is safe because `session_state_legacy` is already always `{}` and downstream `_extract_primary_output()` gets session state via Path A.

**Refinement 3: Tasks 2-3 must be atomic (unanimous)**
Redefining `ReflectionFn` (Task 2) and updating the factory return type (Task 3) must be a single commit. Splitting them creates an intermediate state where the type alias doesn't match the factory, which could break `ty check`.

**Refinement 4: Verify `test_multi_agent_state_extraction.py` after Task 4 (adopted per Murat)**
Add explicit subtask to confirm state extraction tests exercise the executor path (Path A), not the dead event path (Path B). If any test relied on `event.session` being populated, it was testing dead code.

**Refinement 5: No new issues found (unanimous)**
Story is comprehensive and implementation-ready. All research findings incorporated. No additional scope changes needed.

### Research Findings (Web + Codebase Analysis)

**ty @overload support (confirmed working):**
- `@overload` with `Literal[True]`/`Literal[False]` IS supported by ty
- Union argument expansion for overloads was fixed (astral-sh/ty Issue #468, resolved via ruff#18382)
- Ruff `RUF038` rule may simplify `Literal[True, False]` to `bool` in implementation signatures — must suppress if enabled
- Fallback if @overload doesn't narrow: separate methods (`_run_with_events` / `_run_without_events`)

**ADK Event.session analysis (critical finding):**
- `Event` extends `LlmResponse` (Pydantic BaseModel) with `extra='forbid'`
- `Event` fields: `invocation_id`, `author`, `actions`, `branch`, `id`, `timestamp`, `long_running_tool_ids`
- `Event` does NOT have a `session` field — `hasattr(event, "session")` returns `False` at runtime
- `Session.state` IS typed as `dict[str, Any]` in ADK — no MappingProxyType issue
- The `no-matching-overload` error is because `event.session` resolves to unknown/error type
- `AgentExecutor` pattern: re-fetch session from session service, access `refreshed_session.state`

**gepa sync (0.1.0) reference patterns:**
- Uses strict Protocol-based callable types with fixed param counts (no 2/3-param variation)
- Uses `inspect.signature()` only for evaluator wrapper parameter filtering, not arity dispatch
- Trajectories also `list | None` with nullable pattern (same as gepa-adk)
- No asyncio.gather (synchronous codebase)

**Blast radius (measured):**

| Change | Source Files | Test Files | Total Call Sites |
|--------|-------------|------------|-----------------|
| Remove `session_service` param | 2 (api.py, adk_reflection.py) | 13 | ~42+ |
| Remove `output_field` param | 1 (adk_reflection.py) | 0 | 0 |
| Redefine `ReflectionFn` 3-param | 3 (proposer, adk_reflection, __init__) | 6 | ~10 |
| Delete event.session blocks | 1 (multi_agent.py) | 0 | 0 |
| @overload on _run_single_example | 1 (multi_agent.py) | 1 (5 calls) | 5 |

### Previous Story Learnings (from Story 1B.4)

1. **Pre-commit hooks are strict** — yamllint, ruff, ty, pytest, docvet all enforced. Run `pre-commit run --all-files` before committing.
2. **docvet catches stale-body findings** — When changing function signatures, verify docvet still passes. Docstring content must match the function body.
3. **`create_mock_adapter()` factory** — Use this for all test mock adapter creation, not direct `MockAdapter()`.
4. **Line numbers are advisory** — Prior stories may have shifted line numbers. Dev agent must grep for actual patterns rather than trusting hardcoded line references.
5. **`__all__` at file BOTTOM** — When adding new type aliases, update `__all__`.
6. **Dead parameters identified during 1B.4 review** — td-001 (`session_service`) and td-002 (`output_field`) were explicitly deferred to this story.
7. **Test files that need `session_service` removed** — 13 files, ~42 call sites. Use `grep -rn "session_service" tests/` to find all, then mechanical removal.

### Project Structure Notes

```
# Files to MODIFY (source — 5 files)
src/gepa_adk/engine/proposer.py              - Redefine ReflectionFn to 3-param, remove inspect.signature dispatch
src/gepa_adk/engine/adk_reflection.py        - Remove session_service + output_field params, update reflect() signature
src/gepa_adk/engine/__init__.py              - No changes needed (ReflectionFn name unchanged)
src/gepa_adk/adapters/evolution/multi_agent.py - @overload on 3 methods, delete event.session dead code
src/gepa_adk/api.py                           - Remove session_service kwarg from create_adk_reflection_fn() calls

# Test files to UPDATE (~14 files)
tests/contracts/test_reflection_fn.py                    - Remove session_service kwarg
tests/contracts/engine/test_reflection_fn_contract.py    - Remove session_service kwarg
tests/contracts/test_multi_agent_executor_contract.py    - Remove session_service kwarg + update 2-param mock
tests/integration/test_schema_reflection.py              - Remove session_service kwarg
tests/integration/test_reflection_template.py            - Remove session_service kwarg
tests/integration/engine/test_adk_reflection.py          - Remove session_service kwarg
tests/integration/engine/test_context_integration.py     - Remove session_service kwarg
tests/unit/engine/test_adk_reflection.py                 - Remove session_service kwarg
tests/unit/engine/test_adk_reflection_state.py           - Remove session_service kwarg
tests/unit/engine/test_adk_reflection_template.py        - Remove session_service kwarg
tests/unit/engine/test_context_passing.py                - Remove session_service kwarg
tests/unit/engine/test_proposer.py                       - Verify ReflectionFn usage
tests/unit/test_api_session_service.py                   - Remove session_service kwarg (mocked)
tests/unit/test_api_app_runner.py                        - Remove session_service kwarg (mocked)

# Files NOT needing changes (verified)
src/gepa_adk/adapters/evolution/adk_adapter.py - No ty:ignore, different return pattern
src/gepa_adk/domain/types.py                   - No Result dataclass needed (out of scope)
src/gepa_adk/ports/adapter.py                  - EvaluationBatch stays list | None (out of scope)

# Documentation to review
docs/guides/reflection-prompts.md              - Verify accuracy after signature changes
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1B.5] — Acceptance criteria with BDD format
- [Source: _bmad-output/implementation-artifacts/1b-4-fix-pre-existing-boundary-violations.md] — Previous story with td-001/td-002 tech debt, panel consensus, blast radius analysis
- [Source: _bmad-output/implementation-artifacts/1b-3-clean-up-ty-type-check-diagnostics.md] — Story that reduced ty ignores to ~5
- [Source: _bmad-output/project-context.md#Import Layer Boundaries] — 5-layer import rules
- [Source: _bmad-output/project-context.md#Type Checking (ty)] — ty conventions (`# ty: ignore[rule]` syntax)
- [Source: docs/adr/ADR-000-hexagonal-architecture.md] — Layer boundary rules
- [Source: docs/adr/ADR-002-protocol-for-interfaces.md] — Protocol-based interfaces (structural subtyping)
- [Source: src/gepa_adk/engine/proposer.py:78] — ReflectionFn type alias (currently 2-param, redefined to 3-param)
- [Source: src/gepa_adk/engine/proposer.py:274-295] — inspect.signature dispatch block to remove
- [Source: src/gepa_adk/engine/adk_reflection.py:63-68] — create_adk_reflection_fn signature with dead params
- [Source: src/gepa_adk/adapters/evolution/multi_agent.py:880,895] — Union return unpacking with ty:ignore
- [Source: src/gepa_adk/adapters/evolution/multi_agent.py:1102-1105,1235-1238] — Dead event.session hasattr blocks
- [Source: src/gepa_adk/adapters/execution/agent_executor.py:497-507] — Correct session state pattern (re-fetch)
- [Source: .venv/.../google/adk/events/event.py] — Event class has no `session` field, `extra='forbid'`
- [Source: .venv/.../google/adk/sessions/session.py:44] — Session.state is `dict[str, Any]`
- [Source: .venv/.../gepa/proposer/reflective_mutation/base.py] — gepa sync: strict Protocol callable types
- [Research: github.com/astral-sh/ty#468] — ty @overload union argument expansion (fixed)
- [Research: github.com/astral-sh/ruff#16129] — RUF038 Literal simplification risk with @overload

### Git Intelligence

Recent commits on `main`:
```
646a3bf chore(main): release 1.0.0 (#273)
f4cf65b fix(ci): add explicit target-branch and full bootstrap-sha
b6bf54d chore(release): bootstrap release-please for 1.0.0
b3c5e32 chore(repo): migrate branch references from develop to main (#271)
1e430ba refactor(arch): fix all 7 pre-existing hexagonal boundary violations
```

v1.0.0 released (`646a3bf`). Story 1B.4 (`1e430ba`) merged all boundary fixes. Story 1B.6 completed trunk-based migration. Current version: 1.0.0. Test count: ~1856, coverage: ~85%.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes List

- All 7 `ty: ignore` comments eliminated from `src/gepa_adk/`
- Tech debt td-001 (dead `session_service` param) and td-002 (dead `output_field` param) resolved
- `ReflectionFn` type alias redefined from 2-param to 3-param — single type, single truth
- Dead `event.session` code deleted from `multi_agent.py` (ADK `Event` has no `session` field)
- Union return unpacking resolved with `@overload` + `Literal[True]`/`Literal[False]`
- Fixed `Mapping` vs `dict` type variance with dict comprehension in proposer
- ~50+ test call sites updated to 3-param reflection function signature
- All 1855 tests pass, 89.34% coverage, all pre-commit hooks green

### File List

**Source files modified (4):**
- `src/gepa_adk/engine/adk_reflection.py` — Removed dead `session_service` + `output_field` params, updated `reflect()` to `component_name: str = ""`
- `src/gepa_adk/engine/proposer.py` — Redefined `ReflectionFn` to 3-param, removed `inspect.signature()` dispatch, fixed Mapping→dict conversion
- `src/gepa_adk/adapters/evolution/multi_agent.py` — Added `@overload` declarations on 3 methods, deleted dead `event.session` blocks
- `src/gepa_adk/api.py` — Removed `session_service` kwarg from 2 `create_adk_reflection_fn()` calls

**Test files modified (16):**
- `tests/contracts/test_reflection_fn.py`
- `tests/contracts/engine/test_reflection_fn_contract.py`
- `tests/contracts/test_multi_agent_executor_contract.py`
- `tests/contracts/test_adk_adapter_contracts.py`
- `tests/integration/test_schema_reflection.py`
- `tests/integration/test_reflection_template.py`
- `tests/integration/engine/test_adk_reflection.py`
- `tests/integration/engine/test_context_integration.py`
- `tests/unit/engine/test_adk_reflection.py`
- `tests/unit/engine/test_adk_reflection_state.py`
- `tests/unit/engine/test_adk_reflection_template.py`
- `tests/unit/engine/test_context_passing.py`
- `tests/unit/engine/test_proposer.py`
- `tests/unit/test_api_session_service.py`
- `tests/unit/adapters/test_adk_adapter.py`
- `tests/integration/engine/test_proposer_integration.py`

**BMAD artifacts modified (2):**
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/1b-5-eliminate-ty-type-narrowing-workarounds.md`

### Change Log

| Task | Change | Files | Tests After |
|------|--------|-------|-------------|
| 1 | Removed dead `session_service` + `output_field` params from `create_adk_reflection_fn()`, updated 42+ test call sites | adk_reflection.py, api.py, 13 test files | 1855 pass |
| 2-3 | Redefined `ReflectionFn` to 3-param, removed `inspect.signature()` dispatch, updated factory inner `reflect()` signature | proposer.py, adk_reflection.py, 6 test files | 1855 pass |
| 4 | Deleted dead `hasattr(event, "session")` blocks from `_run_shared_session()` and `_run_isolated_sessions()` | multi_agent.py | 1855 pass |
| 5 | Added `@overload` declarations with `Literal[True]`/`Literal[False]` on 3 methods, removed 2 `ty: ignore` comments | multi_agent.py | 1855 pass |
| 6 | Updated docstrings in proposer.py, reviewed reflection-prompts.md | proposer.py | 1855 pass |
| 7 | Final validation, fixed 50+ test calls to 3-param, removed tech debt entries | 16 test files, sprint-status.yaml | 1855 pass, 89.34% cov |

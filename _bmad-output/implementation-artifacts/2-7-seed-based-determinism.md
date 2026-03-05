# Story 2.7: Seed-Based Determinism

Status: done
Branch: feat/2-7-seed-based-determinism

## Story

As a developer debugging evolutionary optimization,
I want to set a seed for deterministic engine decisions,
so that I can reproduce identical evolutionary trajectories for debugging and testing.

## Acceptance Criteria

1. **Given** `EvolutionConfig` has no `seed` parameter, **when** the seed field is added, **then** `seed: int | None = None` is available on `EvolutionConfig` with `None` preserving current random behavior.

2. **Given** a seed is provided, **when** the engine initializes, **then** a central `random.Random(seed)` is created and passed to all stochastic components: candidate selector and merge proposer.

3. **Given** `seed=None` (default), **when** the engine runs, **then** behavior is identical to current implementation (backward compatible, unseeded `random.Random()` instances).

4. **Given** a seed is provided and the user passes `candidate_selector` as a string, **when** `create_candidate_selector()` is called, **then** the seed-derived RNG is passed via the existing `rng` parameter.

5. **Given** `config.use_merge=True` and no `merge_proposer` is provided by the user, **when** the engine initializes with a seed, **then** a `MergeProposer(rng=seeded_rng)` is auto-created. Without seed, `MergeProposer(rng=random.Random())` is auto-created.

6. **Given** seed is always logged in results metadata, **when** an evolution run completes, **then** `result.config.seed` reflects the configured seed (automatic — `EvolutionConfig` is already stored in results).

7. **Given** identical seed, agents, scorer, and fitness scores, **when** the engine runs twice, **then** evolutionary decisions (candidate selection order, component selection, Pareto state updates) are identical.

8. **Given** determinism scope, **when** documenting the seed feature, **then** it is explicit that determinism covers engine decisions ONLY — LLM inference is inherently stochastic and NOT covered.

## Tasks / Subtasks

- [x] Task 1: Add `seed` field to `EvolutionConfig` (AC: 1)
  - [x] 1.1: Add `seed: int | None = None` field to `EvolutionConfig` in `domain/models.py` — place after `stop_callbacks` field (last current field)
  - [x] 1.2: Add docstring entry for `seed` in the class docstring's `Attributes:` section
  - [x] 1.3: No `__post_init__` validation needed — `int | None` is always valid, no cross-field constraints
  - [x] 1.4: Verify `to_dict()` / `from_dict()` serialization handles the new field automatically (dataclass fields are included by default in `dataclasses.asdict`)

- [x] Task 2: Wire seed-derived RNG through API layer (AC: 2, 4, 5)
  - [x] 2.1: In `api.py`'s `evolve()` function, after config resolution (`config = config or EvolutionConfig()`), create `rng = random.Random(config.seed) if config.seed is not None else None`. This is the SINGLE RNG creation point — the same `rng` instance is shared with both the candidate selector and the engine (via a new `rng` parameter on the engine constructor). Do NOT create a second `Random(seed)` in the engine.
  - [x] 2.2: Pass `rng` to `create_candidate_selector(candidate_selector, rng=rng)` when `candidate_selector` is a string — update line ~1868 to include `rng=rng`
  - [x] 2.3: When `candidate_selector` is a `CandidateSelectorProtocol` instance (user-provided), do NOT override its RNG — the user controls it
  - [x] 2.4: Pass the `rng` instance to the engine constructor: `AsyncGEPAEngine(..., rng=rng)` — the engine uses this for default selector creation and MergeProposer auto-creation (see Task 3)
  - [x] 2.5: Apply the same RNG wiring to `evolve_group()` and `evolve_workflow()` — they also resolve `candidate_selector` strings via `create_candidate_selector()` and create engine instances
  - [x] 2.6: Add `import random` to `api.py` imports (stdlib, no new dependency)
  - [x] 2.7: Add a `Note:` to `evolve()`, `evolve_group()`, `evolve_workflow()` docstrings with a concrete example: ``For reproducible evolution, pass a seeded config: config=EvolutionConfig(seed=42)``

- [x] Task 3: Wire RNG in engine constructor (AC: 2, 5)
  - [x] 3.1: Add `rng: random.Random | None = None` parameter to `AsyncGEPAEngine.__init__()`. Store as `self._rng = rng`. The engine does NOT create its own RNG from config.seed — it receives the RNG from the API layer (single instance, shared).
  - [x] 3.2: Kept `self._candidate_selector = candidate_selector` unchanged — the engine correctly uses `None` to mean "no Pareto tracking". Changing to a default selector would alter behavior beyond seed scope.
  - [x] 3.3: Auto-create `MergeProposer` when `config.use_merge=True` and `merge_proposer is None`: `MergeProposer(rng=rng or random.Random())` — fixes the silent no-op gap.
  - [x] 3.4: Add `import random` to `async_engine.py` imports
  - [x] 3.5: Log seed value at engine start: `logger.info("engine.start", seed=config.seed)`

- [x] Task 4: Update docstrings (AC: 8)
  - [x] 4.1: Add `Note:` section to `EvolutionConfig` docstring: "Determinism applies to engine decisions only (candidate selection, component selection, merge proposals). LLM inference is inherently stochastic and not covered by the seed guarantee."
  - [x] 4.2: Update `AsyncGEPAEngine` docstring to mention seed-based RNG propagation
  - [x] 4.3: Run `docvet check` — 0 findings on modified files

- [x] Task 5: Write tests (AC: 1-8)
  - [x] 5.1: Create `tests/unit/engine/test_determinism.py` with `pytestmark = pytest.mark.unit`
  - [x] 5.2: Class `TestEvolutionConfigSeed` — 3 tests (default_is_none, accepts_integer, accepts_zero)
  - [x] 5.3: Class `TestSeedRngWiring` — 6 tests (stores_rng, rng_none, merge_auto_seed, merge_auto_unseed, merge_false, user_proposer)
  - [x] 5.4: Class `TestDeterministicDecisions` — 3 tests (same_seed, different_seed, engine_run_determinism)
  - [x] 5.5: Class `TestApiSeedWiring` — 4 tests (selector_receives_rng, no_rng_no_seed, evolve_rng_to_engine, evolve_group_rng_to_engine)
  - [x] 5.6: Run full suite: `uv run pytest` — 2051 passed, 0 regressions

- [x] Task 6: Run quality pipeline (AC: all)
  - [x] 6.1: `ruff format && ruff check --fix` — clean
  - [x] 6.2: `docvet check` — 0 findings on modified files
  - [x] 6.3: `ty check src` — all checks passed
  - [x] 6.4: `pytest` — 2051 passed (baseline 2034 + 17 new)
  - [x] 6.5: Verify `__all__` unchanged (no new public exports — seed is a field, not a function)

- [ ] [TEA] Testing maturity: Create shared domain object test fixtures (GH #292) (cross-cutting, optional)
  - [x] Create `tests/unit/domain/conftest.py` with factory fixtures: `make_iteration_record(**overrides)`, `make_evolution_result(**overrides)`, `make_multiagent_result(**overrides)` — return valid instances with sensible defaults, accept `**overrides` for customization
  - [ ] Use the factories in this story's new `test_determinism.py` tests instead of inline construction
  - [ ] Migrate at least 5 existing tests in `tests/unit/domain/test_models.py` to use the factories
  - [ ] All existing tests pass (`uv run pytest`)

## Dev Notes

### Architecture Compliance

- **Layer placement**: `seed` field belongs in `EvolutionConfig` (domain layer). RNG creation belongs in `api.py` (API layer) — single creation point. Engine receives the RNG via constructor injection. No adapter changes needed.
- **Import boundaries**: `random` is stdlib — allowed in all layers per ADR-000.
- **No new dependencies**: Uses only `random.Random` from stdlib.
- **Backward compatibility**: `seed=None` is default, preserving current unseeded behavior everywhere.
- **Dependency injection preserved**: Engine receives components via constructor. Seed just influences how default components are created.

### Key Design Decisions

1. **Central RNG, not per-component seeds**: Create ONE `random.Random(seed)` and pass it to all stochastic components. This ensures cross-component determinism (e.g., candidate selection and merge proposal are correlated the same way each run). Do NOT create separate `Random(seed)` per component — that would give each component the same sequence independently, which is different from sharing one stream.

2. **Single RNG instance, created in API**: The API layer creates ONE `random.Random(seed)` instance and passes it to both `create_candidate_selector(rng=rng)` (for string selectors) AND the engine constructor via a new `rng` parameter. The engine stores this RNG and uses it for default `ParetoCandidateSelector` and auto-created `MergeProposer`. This ensures all stochastic components share the same RNG stream. The engine does NOT create its own RNG from config.seed.

3. **MergeProposer auto-creation**: Currently, `use_merge=True` without a user-provided `MergeProposer` silently does nothing (engine checks both flags). This story fixes that gap by auto-creating a `MergeProposer` when `use_merge=True` and no proposer is provided. This is a behavior improvement, not a breaking change (previously it was a no-op).

4. **User-provided components are respected**: If the user passes a pre-built `CandidateSelectorProtocol` instance or `MergeProposer`, their RNG is not overridden. The seed only affects auto-created defaults.

5. **No `seed` parameter on `evolve()` signature**: The seed flows through `config=EvolutionConfig(seed=42)`. Adding a redundant `seed` parameter on `evolve()` would create two conflicting sources of truth. Keep the API surface minimal.

### Previous Story Intelligence (from Story 2.6)

- **Test count baseline**: 2034 tests passing (after review fixes). Story 2.7 must not regress.
- **Keyword-only params**: `evolve()`, `evolve_group()`, `evolve_workflow()` now use `*` separator — all optional params are keyword-only. No signature changes needed for seed (it's on config, not the function).
- **Quality pipeline**: `ruff format`, `ruff check --fix`, `docvet check`, `ty check src tests` before committing.
- **Branch convention**: `feat/2-7-seed-based-determinism`
- **Commit convention**: `feat(engine): add seed-based determinism for reproducible evolution` — NOT a breaking change (additive field with None default).
- **`EvolutionConfig` pattern**: `@dataclass(slots=True, kw_only=True)` with `__post_init__` validation raising `ConfigurationError(field=..., value=..., constraint=...)`.
- **Serialization**: `to_dict()` / `from_dict()` use `dataclasses.asdict` / manual construction. New fields are auto-included.

### Git Intelligence (from recent commits)

- `0befe0a feat(api)!: add universal sync wrapper and keyword-only signatures` — latest on main
- `b019f7a feat(api): add pre-flight validation enhancements` — added pre-flight validators
- `e892fc0 feat(engine): add graceful interrupt handling` — modified engine, added interrupt handling
- Pattern: Each story is a clean, focused commit. Follow with `feat(engine): ...` scope.

### Current Stochastic Component Inventory

| Component | File | RNG Param | Notes |
|-----------|------|-----------|-------|
| `ParetoCandidateSelector` | `adapters/selection/candidate_selector.py:39` | `rng: random.Random \| None = None` | Defaults to `Random()` when None |
| `EpsilonGreedyCandidateSelector` | `adapters/selection/candidate_selector.py:140` | `rng: random.Random \| None = None` | Defaults to `Random()` when None |
| `MergeProposer` | `engine/merge_proposer.py:47` | `rng: random.Random` (required) | No default — must be provided |
| `CurrentBestCandidateSelector` | `adapters/selection/candidate_selector.py:113` | None | Deterministic — no RNG |
| `RoundRobinComponentSelector` | `adapters/selection/component_selector.py:44` | None | Deterministic — no RNG |
| `AllComponentSelector` | `adapters/selection/component_selector.py:110` | None | Deterministic — no RNG |

### Current API Wiring Gaps (to fix)

1. `api.py:1868`: `create_candidate_selector(candidate_selector)` called WITHOUT `rng=` — needs `rng=rng`
2. Engine default selector (`async_engine.py:257`): `ParetoCandidateSelector()` created WITHOUT RNG — needs `ParetoCandidateSelector(rng=self._rng)`
3. No auto-creation of `MergeProposer` when `use_merge=True` — engine silently skips merge

### Documentation Impact

- **Docstring updates**: `EvolutionConfig`, `AsyncGEPAEngine.__init__`, `evolve()` (note seed flows through config)
- **No external docs changes**: Seed is a simple config field; getting-started guide updated in Story 8.2
- **No ADR needed**: Seed-based determinism is a standard pattern, not an architectural decision
- **CHANGELOG**: `feat(engine): add seed-based determinism` will create a minor version changelog entry

### Project Structure Notes

- Modified files: `domain/models.py`, `engine/async_engine.py`, `api.py`
- New test file: `tests/unit/engine/test_determinism.py`
- No new source files, no new dependencies, no adapter changes

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2, Story 2.7 (lines 653-669)]
- [Source: src/gepa_adk/domain/models.py#EvolutionConfig (lines 162-340)]
- [Source: src/gepa_adk/engine/async_engine.py#AsyncGEPAEngine.__init__ (lines 145-276)]
- [Source: src/gepa_adk/adapters/selection/candidate_selector.py#create_candidate_selector (lines 199-236)]
- [Source: src/gepa_adk/engine/merge_proposer.py#MergeProposer (line 47)]
- [Source: src/gepa_adk/api.py#evolve() candidate_selector resolution (lines 1865-1870)]
- [Source: _bmad-output/implementation-artifacts/2-6-universal-sync-wrapper-and-api-surface-polish.md#Dev Notes]
- [Source: _bmad-output/project-context.md#Dataclass patterns, Exception handling]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None required — clean implementation.

### Completion Notes List

- Task 3.2 deviation: Did NOT change `self._candidate_selector = candidate_selector` to default to `ParetoCandidateSelector`. The engine uses `None` to mean "no Pareto tracking" — changing this would alter behavior beyond seed scope. The RNG flows through the API layer's `create_candidate_selector(rng=rng)` call instead.
- `EvolutionConfig` does not have `to_dict`/`from_dict` — serialization of the seed field is automatic via `dataclasses.asdict` when needed externally. `EvolutionResult.to_dict()` does not include config.
- `evolve_workflow()` delegates to `evolve_group()`, so RNG wiring only needed in `evolve()` and `evolve_group()`.
- `evolve_group()` does not accept `candidate_selector` parameter, so only `rng` is passed to the engine constructor.

### Change Log

- `src/gepa_adk/domain/models.py`: Added `seed: int | None = None` field and docstring
- `src/gepa_adk/engine/async_engine.py`: Added `rng` param, `import random`, MergeProposer auto-creation, seed logging
- `src/gepa_adk/api.py`: Added `import random`, RNG creation in `evolve()` and `evolve_group()`, passed to selectors and engine
- `tests/unit/engine/test_determinism.py`: New — 17 tests across 4 test classes
- `tests/unit/domain/conftest.py`: New — factory fixtures for domain model test objects (TEA cross-cutting)

### Review: Code Review Fixes (2026-03-05)

- Rewrote `test_evolve_passes_seeded_rng_to_engine` — was a guaranteed-pass placeholder; now mocks API internals and verifies engine receives `rng` kwarg
- Added `test_evolve_group_passes_seeded_rng_to_engine` — new test covering `evolve_group()` RNG wiring gap
- Replaced `test_seed_zero_creates_rng_not_none` (tested stdlib) with `test_seed_zero_creates_rng_in_engine` (tests actual engine with `seed=0`)
- Updated test counts, File List, and TEA subtask status

### File List

- `src/gepa_adk/domain/models.py` (modified)
- `src/gepa_adk/engine/async_engine.py` (modified)
- `src/gepa_adk/api.py` (modified)
- `tests/unit/engine/test_determinism.py` (new)
- `tests/unit/domain/conftest.py` (new)

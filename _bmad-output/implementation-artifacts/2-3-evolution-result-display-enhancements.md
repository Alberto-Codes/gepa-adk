# Story 2.3: Evolution Result Display Enhancements

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a readable, informative result representation,
so that I can quickly understand what happened during evolution without parsing raw data.

## Acceptance Criteria

1. **`original_components` field on `EvolutionResult`** — new optional field `original_components: dict[str, str] | None = None` storing the pre-evolution component values. Backward-compatible: no schema version bump needed (optional field with `None` default). `to_dict()` includes it. `from_dict()` uses `.get("original_components")` (returns `None` for old dicts). Existing v1 test fixture loads without changes.
2. **`original_components` field on `MultiAgentEvolutionResult`** — same pattern: optional `dict[str, str] | None = None` field.
3. **`__repr__()` on `EvolutionResult`** — overrides the auto-generated dataclass repr with narrative format: improvement percentage first (e.g., `+41.7%`), then iterations/stop reason, then evolved component names, then acceptance rate. No box-drawing characters. Every line greppable (no multi-line values that break `grep`). 2-space indent for nested lines. No separate `__str__` override — `repr()` IS the human-readable form (pandas/sklearn convention). `to_dict()` covers raw field access.
4. **`__repr__()` on `MultiAgentEvolutionResult`** — same narrative format adapted for multi-agent: shows improvement, iterations/stop reason, primary agent, agent names, acceptance rate. Same formatting rules.
5. **`show_diff()` on `EvolutionResult`** — signature: `show_diff(self, original_components: dict[str, str] | None = None) -> str`. If `original_components` param is `None`, falls back to `self.original_components`. If both are `None`, raises `ValueError`. Produces unified-diff-style output (`---`/`+++`/`@@`) for each component that changed, using `difflib.unified_diff()`. Components with no changes are skipped. Returns the combined diff as a single string. If no components changed, returns `"No changes detected."`.
6. **`show_diff()` on `MultiAgentEvolutionResult`** — same pattern and signature. Diff sections labeled with agent names.
7. **`_repr_html_()` on `EvolutionResult`** — returns an HTML string suitable for Jupyter rendering. Contains a summary `<table>` (improvement, scores, iterations, stop reason) and a components `<table>` (component name, truncated evolved value). Iteration history wrapped in `<details>`/`<summary>` for collapsible display. Uses inline CSS only (no external stylesheets, no `<style>` tags). No JavaScript. HTML-escapes all values via `html.escape()`.
8. **`_repr_html_()` on `MultiAgentEvolutionResult`** — similar HTML table with primary agent and agent-specific columns. Same `<details>`/`<summary>` for history.
9. **Regex-based structural tests** — tests verify format elements are present (improvement line, iterations line, component names, greppable output) using regex patterns. NO brittle snapshot tests that break when formatting changes. Tests cover: positive improvement, zero improvement, negative improvement, multiple components, single component.
10. **Edge case coverage** — tests for: empty `iteration_history`, very long component values (truncation), multi-line component values (truncation), `show_diff()` with identical components ("No changes"), `show_diff()` with missing original component key, `show_diff()` zero-arg with stored originals, `show_diff()` with no originals raises `ValueError`, Unicode component values, empty string components, component text containing diff markers (`---`/`+++`/`@@`).
11. **stdlib only** — all display methods use only stdlib (`difflib`, `html`, string formatting). No external rendering libraries. Domain layer import boundary respected.
12. **Existing tests pass** — all ~1894+ tests continue to pass. No regressions.
13. **`__all__` unchanged** — no new public symbols added to module exports (methods are on existing classes).

## Tasks / Subtasks

### Task 1: Add `original_components` field to result types (AC: 1, 2)

- [x] 1.1 Add `original_components: dict[str, str] | None = None` field to `EvolutionResult` in `src/gepa_adk/domain/models.py` (after `objective_scores`, before methods). Optional with `None` default — backward-compatible, no schema version bump.
- [x]1.2 Add same field to `MultiAgentEvolutionResult` (after `total_iterations`, before methods).
- [x]1.3 Update `EvolutionResult.to_dict()` — add `"original_components": self.original_components` to output dict.
- [x]1.4 Update `EvolutionResult.from_dict()` — add `original_components=migrated.get("original_components")` to constructor call.
- [x]1.5 Update `MultiAgentEvolutionResult.to_dict()` and `from_dict()` — same pattern.
- [x]1.6 Update class docstrings to document the new field in `Attributes:` section.
- [x]1.7 Verify existing test fixture `evolution_result_v1.json` loads without error (no `original_components` key → `None`).

### Task 2: Wire `original_components` into engine result construction (AC: 1, 2)

- [x]2.1 Find where `EvolutionResult` is constructed in the engine layer (grep for `EvolutionResult(` in `src/gepa_adk/engine/`).
- [x]2.2 Pass the original candidate components as `original_components=` when constructing `EvolutionResult`. The engine already has these values (the initial candidate components before evolution).
- [x]2.3 Same for `MultiAgentEvolutionResult` construction — pass original components.
- [x]2.4 Verify existing engine tests still pass after wiring.

### Task 3: Add `__repr__()` to `EvolutionResult` (AC: 3, 11)

- [x]3.1 Add `__repr__(self) -> str` method to `EvolutionResult` (after `improved` property, before `Candidate` class). Overrides the auto-generated dataclass repr. Format:
  ```
  EvolutionResult: +41.7% improvement (0.60 → 0.85)
    iterations: 10, stop_reason: completed
    components: instruction
    acceptance_rate: 7/10
  ```
  - Improvement line: `+XX.X%` for positive, `-XX.X%` for negative, `0.0%` for no change. Show `(original → final)` scores.
  - Stop reason: use `self.stop_reason.value` (the string value).
  - Components: comma-separated list of `self.evolved_components` keys.
  - Acceptance rate: count accepted iterations / `self.total_iterations`. Skip line if `total_iterations == 0`.
  - No box-drawing characters (U+2500-U+257F). Every line greppable. 2-space indent.
- [x]3.2 Add a module-level helper `_truncate(text: str, max_len: int = 80) -> str` that collapses multi-line text to single line and truncates with `...`. Place before `EvolutionResult` class (private, not in `__all__`).
- [x]3.3 Add Google-style docstring with `Returns:` section.

### Task 4: Add `__repr__()` to `MultiAgentEvolutionResult` (AC: 4, 11)

- [x]4.1 Add `__repr__(self) -> str` method to `MultiAgentEvolutionResult` (after `agent_names` property). Format:
  ```
  MultiAgentEvolutionResult: +41.7% improvement (0.60 → 0.85)
    iterations: 10, stop_reason: completed
    primary_agent: generator
    agents: critic, generator
    acceptance_rate: 7/10
  ```
- [x]4.2 Add Google-style docstring with `Returns:` section.

### Task 5: Add `show_diff()` to `EvolutionResult` (AC: 5, 11)

- [x]5.1 Add `import difflib` to the imports section of `models.py` (stdlib, domain-layer safe).
- [x]5.2 Add `show_diff(self, original_components: dict[str, str] | None = None) -> str` method to `EvolutionResult` (after `__repr__`).
  - If `original_components` param is `None`, fall back to `self.original_components`.
  - If both are `None`, raise `ValueError("No original components available. Pass original_components or use a result that stores them.")`.
  - For each key in `self.evolved_components`: generate unified diff via `difflib.unified_diff()` with `fromfile=f"{key} (original)"`, `tofile=f"{key} (evolved)"`. Use `splitlines(keepends=True)` on input, `lineterm=""` on output.
  - Skip components with identical values. If key not in originals, show as entirely new (`+` lines only).
  - Join diffs with blank line separator. If no diffs, return `"No changes detected."`.
- [x]5.3 Add Google-style docstring with `Args:`, `Returns:`, `Raises:` sections.

### Task 6: Add `show_diff()` to `MultiAgentEvolutionResult` (AC: 6, 11)

- [x]6.1 Add `show_diff(self, original_components: dict[str, str] | None = None) -> str` method to `MultiAgentEvolutionResult` (after `__repr__`). Same logic as `EvolutionResult.show_diff()`.
- [x]6.2 Add Google-style docstring with `Args:`, `Returns:`, `Raises:` sections.

### Task 7: Add `_repr_html_()` to `EvolutionResult` (AC: 7, 11)

- [x]7.1 Add `import html` to the imports section of `models.py` (stdlib, domain-layer safe).
- [x]7.2 Add `_repr_html_(self) -> str` method to `EvolutionResult` (after `show_diff`). Return an HTML string containing:
  - Summary `<table>` with inline CSS: rows for improvement (%), original score, final score, total iterations, stop reason. Subtle borders, padding, monospace font for values.
  - Components `<table>`: columns "Component" and "Evolved Value" (truncated to 200 chars).
  - Iteration history in `<details>`/`<summary>` (HTML5 collapsible — no JS, no CSS hacks, degrades gracefully).
  - All values escaped via `html.escape()`. No `<style>` tags, no CSS classes — inline styles only for max portability (JupyterLab, Colab, VS Code).
- [x]7.3 Add Google-style docstring with `Returns:` section.

### Task 8: Add `_repr_html_()` to `MultiAgentEvolutionResult` (AC: 8, 11)

- [x]8.1 Add `_repr_html_(self) -> str` method to `MultiAgentEvolutionResult` (after `show_diff`). Same HTML pattern with primary agent row and agent-specific component labeling. Same `<details>`/`<summary>` for history.
- [x]8.2 HTML-escape all values.
- [x]8.3 Add Google-style docstring with `Returns:` section.

### Task 9: Unit tests for `original_components` field (AC: 1, 2, 10, 12)

- [x]9.1 Add tests to existing `TestEvolutionResultSerialization` class:
  - `test_to_dict_includes_original_components` — non-None originals appear in dict
  - `test_to_dict_original_components_none` — None originals appear as `null`
  - `test_from_dict_round_trip_with_original_components` — round-trip preserves originals
  - `test_from_dict_without_original_components_key` — old dict without key → `None` (backward compat)
- [x]9.2 Add same tests to `TestMultiAgentEvolutionResultSerialization`.
- [x]9.3 Verify existing fixture test (`test_load_evolution_result_v1_fixture`) still passes — v1 fixture has no `original_components` key.

### Task 10: Unit tests for `__repr__()` (AC: 9, 10, 12)

- [x]10.1 Create test class `TestEvolutionResultRepr` in `tests/unit/domain/test_models.py`:
  - `test_repr_contains_improvement_percentage` — regex match for `[+-]?\d+\.\d+%`
  - `test_repr_contains_scores` — regex match for original and final scores
  - `test_repr_contains_iterations_and_stop_reason` — regex match for `iterations: \d+, stop_reason: \w+`
  - `test_repr_contains_component_names` — verify component key names appear
  - `test_repr_every_line_greppable` — split on `\n`, verify no empty interior lines
  - `test_repr_no_box_drawing` — verify no Unicode box-drawing characters (U+2500-U+257F range)
  - `test_repr_uses_two_space_indent` — indented lines start with exactly `  ` (two spaces)
  - `test_repr_positive_improvement` — positive case
  - `test_repr_negative_improvement` — regression case
  - `test_repr_zero_improvement` — no change case
  - `test_repr_empty_history` — handles empty `iteration_history` (no acceptance_rate line)
  - `test_repr_multiple_components` — multiple evolved components shown
  - `test_repr_unicode_component_values` — emoji and CJK characters in component text
- [x]10.2 Create test class `TestMultiAgentEvolutionResultRepr`:
  - `test_repr_contains_improvement_percentage`
  - `test_repr_contains_primary_agent`
  - `test_repr_contains_agent_names`
  - `test_repr_uses_two_space_indent`

### Task 11: Unit tests for `show_diff()` (AC: 9, 10, 12)

- [x]11.1 Create test class `TestEvolutionResultShowDiff`:
  - `test_show_diff_contains_diff_markers` — regex match for `---`, `+++`, `@@`
  - `test_show_diff_shows_changed_component` — verify changed text appears in diff
  - `test_show_diff_identical_returns_no_changes` — identical components → "No changes detected."
  - `test_show_diff_multiple_components` — diffs for each changed component
  - `test_show_diff_missing_original_key` — new component (no original) shows as additions
  - `test_show_diff_multiline_values` — multi-line component text diffs correctly
  - `test_show_diff_zero_arg_with_stored_originals` — uses `self.original_components` when no param
  - `test_show_diff_param_overrides_stored` — explicit param takes priority over stored originals
  - `test_show_diff_no_originals_raises_valueerror` — both param and field are `None` → `ValueError`
  - `test_show_diff_component_with_diff_markers_in_text` — component text containing `---`/`+++`/`@@` chars
  - `test_show_diff_empty_string_components` — original or evolved is empty string
- [x]11.2 Create test class `TestMultiAgentEvolutionResultShowDiff`:
  - `test_show_diff_contains_diff_markers`
  - `test_show_diff_identical_returns_no_changes`
  - `test_show_diff_zero_arg_with_stored_originals`
  - `test_show_diff_no_originals_raises_valueerror`

### Task 12: Unit tests for `_repr_html_()` (AC: 9, 10, 12)

- [x]12.1 Create test class `TestEvolutionResultReprHtml`:
  - `test_repr_html_returns_string` — verify return type is `str`
  - `test_repr_html_contains_table_tags` — regex match for `<table` and `</table>`
  - `test_repr_html_contains_improvement` — improvement percentage in HTML
  - `test_repr_html_contains_scores` — original and final scores in HTML
  - `test_repr_html_escapes_values` — inject `<script>alert('xss')</script>` in component text, verify `&lt;script&gt;` in output
  - `test_repr_html_contains_component_names` — component keys in HTML
  - `test_repr_html_contains_details_summary` — verify `<details>` and `<summary>` tags present
- [x]12.2 Create test class `TestMultiAgentEvolutionResultReprHtml`:
  - `test_repr_html_returns_string`
  - `test_repr_html_contains_table_tags`
  - `test_repr_html_contains_primary_agent`

### Task 13: Update docstrings (AC: 12)

- [x]13.1 Update `EvolutionResult` class docstring `Attributes:` to document `original_components`. Update `Examples:` section to include `repr()` and `show_diff()` usage examples showing both zero-arg and parameterized `show_diff()`.
- [x]13.2 Update `MultiAgentEvolutionResult` class docstring similarly.
- [x]13.3 Update the module-level docstring `Examples:` section in `models.py` to mention display methods and `original_components`.

### Task 14: Validation and cleanup (AC: 12)

- [x]14.1 Run full test suite: `pytest` — all tests pass
- [x]14.2 Run `ruff format` + `ruff check --fix`
- [x]14.3 Run `docvet check` on `src/gepa_adk/domain/models.py`
- [x]14.4 Run `ty check src tests`
- [x]14.5 Verify `__all__` in `models.py` does NOT need updates (no new public symbols)

- [ ] [TEA] Testing maturity: Add adversarial input tests for `show_diff()` — extremely long single-line components (10,000 chars), components with only whitespace differences, components with embedded null bytes or control characters (cross-cutting, optional)

## Dev Notes

### Architecture Compliance

This story adds an optional field and display methods to the domain model layer. Key architectural constraints:

- **Domain layer = stdlib only** (exception: structlog). `difflib`, `html` are both stdlib — safe for domain layer.
- **Frozen dataclass methods**: `__repr__()`, `show_diff()`, `_repr_html_()` are all read-only methods. Safe on frozen dataclasses — no mutation required.
- **No Protocol changes**: Display methods and `original_components` are NOT part of `EvolutionResultProtocol`. These are presentation concerns and optional enrichment on concrete types. Do NOT add them to the Protocol (same reasoning as `to_dict()`/`from_dict()` — see Story 2.2 notes).
- **No `__all__` changes**: Methods on existing classes and new optional fields don't need export updates.
- **No schema version bump**: Adding `original_components: dict[str, str] | None = None` is backward-compatible — optional field with `None` default. `from_dict()` uses `.get()` which returns `None` for old dicts missing the key. Existing v1 fixtures remain valid.

### Key Design Decisions (Party Mode Consensus)

These decisions were made via full-team review with research backing:

1. **Override `__repr__`, not `__str__`**: pandas and sklearn both override `__repr__` with summary formats. The "eval-reconstructable repr" convention is widely abandoned for complex objects. `to_dict()` covers raw field access. No separate `__str__` needed.

2. **Store `original_components` on result types**: sklearn GridSearchCV, Optuna Trial, and Ray Tune all store the configuration that produced results inside the result object. This makes `show_diff()` usable zero-arg without requiring the caller to have saved originals. Backward-compatible (optional `None` default, no schema bump).

3. **`show_diff()` dual-mode signature**: `show_diff(self, original_components: dict[str, str] | None = None)`. Uses param if provided (explicit override), falls back to `self.original_components`, raises `ValueError` if both are `None`. This supports both engine-caller and standalone-result use cases.

4. **`_repr_html_()` uses `<details>`/`<summary>`**: HTML5 native collapsible elements — no CSS hacks (xarray checkbox pattern), no JavaScript. Degrades gracefully (content shows expanded in unsupported environments). Inline styles only for max portability across JupyterLab, Colab, VS Code. No `<style>` tags.

5. **No HTML diff in `_repr_html_()`**: Rich color-coded diff in HTML is deferred to a future story. Keep domain models as data presentation, not design systems. Rich rendering belongs in an adapter-level `ResultRenderer` if needed.

### Critical Implementation Patterns

**`__repr__()` format rules:**
- Improvement percentage FIRST — primary information
- No box-drawing characters (U+2500-U+257F range) — plain ASCII only
- Every line greppable — no multi-line values that span line breaks
- 2-space indent for sub-lines — not tabs, not 4-space

**Example `__repr__()` output (positive improvement):**
```
EvolutionResult: +41.7% improvement (0.60 → 0.85)
  iterations: 10, stop_reason: completed
  components: instruction
  acceptance_rate: 7/10
```

**Example `__repr__()` output (no improvement):**
```
EvolutionResult: 0.0% improvement (0.60 → 0.60)
  iterations: 5, stop_reason: max_iterations
  components: instruction, output_schema
  acceptance_rate: 0/5
```

**`show_diff()` dual-mode pattern:**
```python
def show_diff(self, original_components: dict[str, str] | None = None) -> str:
    originals = original_components or self.original_components
    if originals is None:
        raise ValueError(
            "No original components available. "
            "Pass original_components or use a result that stores them."
        )
    # ... generate diffs ...
```

**`difflib.unified_diff()` gotchas:**
- Returns an **iterator** — must materialize to list before joining
- Input must be `splitlines(keepends=True)` — NOT `split("\n")`
- Use `lineterm=""` to avoid double newlines when input lines already have endings
- Handles content containing `---`/`+++`/`@@` correctly (markers are positional, not content-based)

**`_repr_html_()` minimal safe pattern (cross-platform):**
```python
def _repr_html_(self) -> str:
    # Inline styles only — no <style> tags, no CSS classes
    # <details>/<summary> for collapsible sections
    # html.escape() all user-provided values
    return (
        '<div style="font-family: monospace;">'
        '<table style="border-collapse: collapse; ...">'
        # ... summary rows ...
        '</table>'
        '<details><summary>Iteration History</summary>'
        # ... history table ...
        '</details>'
        '</div>'
    )
```

**Component value truncation (module-level helper):**
```python
def _truncate(text: str, max_len: int = 80) -> str:
    single_line = text.replace("\n", " ")
    if len(single_line) <= max_len:
        return single_line
    return single_line[:max_len - 3] + "..."
```

**Imports needed (all stdlib):**
- `import difflib` — for `show_diff()` unified diff generation
- `import html` — for `_repr_html_()` value escaping

### Source Tree Components to Touch

**Domain layer (no external deps):**
- `src/gepa_adk/domain/models.py` — add `original_components` field, `__repr__()`, `show_diff()`, `_repr_html_()` methods, `_truncate()` helper. Add `import difflib` and `import html`. Update docstrings.

**Engine layer:**
- `src/gepa_adk/engine/` — wire `original_components=` when constructing `EvolutionResult` and `MultiAgentEvolutionResult`. One-line change per construction site.

**Tests:**
- `tests/unit/domain/test_models.py` — add serialization tests for `original_components`, plus 6 new test classes for display methods.

### Testing Standards Summary

- `pytestmark = pytest.mark.unit` already at module top in `test_models.py`
- Tests grouped in classes per method: `TestEvolutionResultRepr`, `TestEvolutionResultShowDiff`, etc.
- Use regex (`re.search()`) for structural verification — NOT snapshot comparison
- Coverage must stay >= 85%
- `filterwarnings = ["error"]` — new warnings break CI
- Run `docvet check` on all modified source files
- Async not needed — all display methods are synchronous

### Documentation Impact

- `src/gepa_adk/domain/models.py` — UPDATE: class docstring Attributes and Examples sections
- No ADR changes needed — display methods are not an architectural decision
- No user-facing guide changes in this story (future DX/docs epic 8 will cover user guides)
- CHANGELOG entry will be auto-generated by release-please from `feat` commit type

### Project Structure Notes

- No new files in `src/` — all changes are additions to existing `models.py`
- No new files in `tests/` — all test classes go in existing `test_models.py`
- `__all__` in `models.py` is UNCHANGED — methods and optional fields don't need export updates
- Import boundaries respected: `models.py` only adds stdlib imports (`difflib`, `html`)
- Engine layer gets minimal one-line wiring changes
- No new dependencies in `pyproject.toml`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3 (line 587)] — Acceptance criteria with BDD format
- [Source: _bmad-output/project-context.md] — Coding standards, testing rules, import boundaries
- [Source: src/gepa_adk/domain/models.py#EvolutionResult (line 432)] — Frozen dataclass to add field + methods to
- [Source: src/gepa_adk/domain/models.py#MultiAgentEvolutionResult (line 654)] — Frozen dataclass to add field + methods to
- [Source: src/gepa_adk/domain/models.py#IterationRecord (line 326)] — Has `accepted` field for acceptance rate
- [Source: src/gepa_adk/domain/types.py#StopReason (line 358)] — str enum, `.value` gives display string
- [Source: src/gepa_adk/domain/models.py#__all__ (line 831)] — No changes needed
- [Source: src/gepa_adk/domain/models.py#imports (line 61-67)] — Add `difflib` and `html` here
- [Source: src/gepa_adk/domain/models.py#to_dict (line 505)] — Update to include original_components
- [Source: src/gepa_adk/domain/models.py#from_dict (line 527)] — Update to extract original_components
- [Source: src/gepa_adk/engine/] — Find EvolutionResult construction sites for wiring
- [Source: _bmad-output/implementation-artifacts/2-2-result-serialization.md] — Previous story patterns and learnings
- [Research: pandas __repr__ convention] — pandas uses same impl for __repr__ and __str__
- [Research: sklearn _repr_html_ pattern] — Uses CSS class prefixing and dark mode detection
- [Research: Optuna/sklearn store inputs in results] — Config stored alongside scores
- [Research: difflib.unified_diff gotchas] — Iterator return, splitlines(keepends=True), lineterm=""

### Git Intelligence

Recent commits on `main`:
```
6589a0b feat(domain): add result serialization with to_dict/from_dict
536073a feat(domain): add StopReason enum and schema versioning to evolution results
0ae5c67 chore(bmad): epic 1A+1B retrospective and workflow improvements (#276)
486798b chore(main): release 1.0.1 (#275)
```

Stories 2.1 and 2.2 are complete and merged. `schema_version`, `stop_reason`, `to_dict()`, `from_dict()` all exist. This story builds on those foundations by adding `original_components` storage and human-readable display methods.

Branch naming convention: `feat/2-3-evolution-result-display-enhancements`

### Previous Story Intelligence (from Story 2.2)

Key learnings:
1. **Line numbers are advisory** — Prior stories shifted code. Use grep patterns, not hardcoded line numbers.
2. **Documentation subtasks are mandatory** — docstrings and examples must be completed as part of AC.
3. **Clean sweep at the end** — Run a grep sweep for stale references.
4. **No story refs in production code** — Don't reference "Story 2.3" in src/ files.
5. **Pre-commit hooks are strict** — Run full quality pipeline before committing.
6. **Discovery first** — Grep across ALL test files before deciding where to add tests.
7. **`ConfigurationError` is already imported** — in `models.py` line 66. No new exception imports needed.
8. **`Any` is already imported** from `typing` line 62. No new type imports needed.
9. **Test count**: 1894 tests currently passing (as of Story 2.2). Display tests should not break any.
10. **Optional fields don't need schema bump** — adding `field: T | None = None` is backward-compatible. `from_dict()` uses `.get()` which returns `None` for missing keys.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### AC-to-Test Mapping

| AC | Test Class(es) | Status |
|----|---------------|--------|
| AC1 | TestEvolutionResultOriginalComponents (4 tests) | PASS |
| AC2 | TestMultiAgentOriginalComponents (5 tests) | PASS |
| AC3 | TestEvolutionResultRepr (13 tests) | PASS |
| AC4 | TestMultiAgentEvolutionResultRepr (4 tests) | PASS |
| AC5 | TestEvolutionResultShowDiff (11 tests) | PASS |
| AC6 | TestMultiAgentEvolutionResultShowDiff (4 tests) | PASS |
| AC7 | TestEvolutionResultReprHtml (7 tests) | PASS |
| AC8 | TestMultiAgentEvolutionResultReprHtml (3 tests) | PASS |
| AC9 | Regex-based assertions in all Repr/ShowDiff/Html test classes | PASS |
| AC10 | Edge case tests across Repr/ShowDiff/Html classes | PASS |
| AC11 | Only stdlib imports (difflib, html) verified | PASS |
| AC12 | 1948 tests pass, 0 regressions (up from 1897) | PASS |
| AC13 | __all__ unchanged, verified at models.py:1156 | PASS |

### Completion Notes List

- All 14 tasks completed
- `original_components` field added to both `EvolutionResult` and `MultiAgentEvolutionResult`
- Engine wired to pass `original_components` in `async_engine.py` and `api.py`
- `__repr__()`, `show_diff()`, `_repr_html_()` added to both result types
- Module-level helpers `_truncate()` and `_build_diff()` shared by both result types
- 51 new tests across 8 test classes (Tasks 9-12)
- 1948 tests pass (up from 1897), 0 regressions
- ruff, ty, docvet all clean
- `__all__` unchanged, no schema version bump needed

### File List

- `src/gepa_adk/domain/models.py` — Added `original_components` field, `__repr__()`, `show_diff()`, `_repr_html_()`, `_truncate()`, `_build_diff()`
- `src/gepa_adk/engine/async_engine.py` — Wired `original_components=` in `_build_result()`
- `src/gepa_adk/api.py` — Pass `original_components` through to `MultiAgentEvolutionResult`
- `tests/unit/domain/test_models.py` — 8 new test classes, updated 2 existing key-set assertions

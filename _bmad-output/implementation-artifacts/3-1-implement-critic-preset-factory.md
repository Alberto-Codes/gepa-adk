# Story 3.1: Implement Critic Preset Factory

Status: review

## Story

As a developer,
I want to use pre-built critic agents by name,
so that I can add structured evaluation without defining custom critic agents.

## Acceptance Criteria

1. `create_critic(name, *, model=None)` exists in `adapters/scoring/critic_scorer.py` and returns a configured `LlmAgent`
2. Three MVP presets available: `"structured_output"`, `"accuracy"`, `"relevance"`
3. Invalid preset names raise `ConfigurationError` with message listing valid presets (using existing `constraint` field for structured context)
4. `create_critic` is re-exported via `gepa_adk.__init__` (added to `__all__`)
5. `gepa_adk.critic_presets` dict maps preset name to human-readable description, also re-exported
6. Four deterministic unit tests: one per preset (3) + invalid-name error test (1)

## Tasks / Subtasks

- [x] Task 1: Implement `create_critic()` factory and `critic_presets` dict (AC: 1, 2, 5)
  - [x] 1.1 Add `critic_presets` dict with ASI-aware descriptions:
    - `"structured_output": "Scores output format/schema compliance with per-dimension diagnostics"`
    - `"accuracy": "Scores factual correctness with error diagnosis and improvement guidance"`
    - `"relevance": "Scores topical relevance with coverage analysis and focus guidance"`
  - [x] 1.2 Add three new instruction constants (see Dev Notes for full text):
    - `STRUCTURED_OUTPUT_CRITIC_INSTRUCTION`
    - `ACCURACY_CRITIC_INSTRUCTION`
    - `RELEVANCE_CRITIC_INSTRUCTION`
  - [x] 1.3 Add `create_critic(name: str, *, model: str | None = None) -> LlmAgent` function
  - [x] 1.4 All three presets use `CriticOutput` schema (maximizes ASI for reflector — see GEPA Context)
  - [x] 1.5 Each preset returns `LlmAgent(name=f"{name}_critic", instruction=..., output_schema=CriticOutput, **model_kwargs)`
  - [x] 1.6 Model handling: use conditional kwargs — `model_kwargs = {"model": model} if model is not None else {}` (mirrors reflection agent precedent; lets ADK use its default when None)
  - [x] 1.7 Add `__all__` at file BOTTOM (file currently has none) — include `create_critic`, `critic_presets`, and the three new instruction constants alongside existing exports
- [x] Task 2: Wire exports (AC: 4, 5)
  - [x] 2.1 Re-export `create_critic`, `critic_presets`, and new instruction constants from `adapters/scoring/__init__.py`
  - [x] 2.2 Re-export from `adapters/__init__.py`
  - [x] 2.3 Re-export from `gepa_adk/__init__.py` and add to its `__all__`
- [x] Task 3: Error handling (AC: 3)
  - [x] 3.1 Invalid name raises `ConfigurationError` — use existing fields only (no `suggestion` field exists):
    ```python
    raise ConfigurationError(
        f"Unknown critic preset '{name}'. Valid presets: {', '.join(critic_presets)}",
        constraint=f"Must be one of: {', '.join(critic_presets)}",
        value=name,
        field="name",
    )
    ```
  - [x] 3.2 Use `from gepa_adk.domain.exceptions import ConfigurationError`
- [x] Task 4: Unit tests (AC: 6)
  - [x] 4.1 Create `tests/unit/adapters/scoring/` directory with `__init__.py` (does not exist yet)
  - [x] 4.2 Create `tests/unit/adapters/scoring/test_critic_preset_factory.py`
  - [x] 4.3 Set `pytestmark = pytest.mark.unit` at module level
  - [x] 4.4 `test_create_critic_structured_output_returns_llm_agent` — verify: `isinstance(agent, LlmAgent)`, `agent.name == "structured_output_critic"`, `agent.output_schema == CriticOutput`, `"dimension_scores" in agent.instruction.lower()`, `"actionable_guidance" in agent.instruction.lower()`
  - [x] 4.5 `test_create_critic_accuracy_returns_llm_agent` — same pattern; also assert `"factual" in agent.instruction.lower()`
  - [x] 4.6 `test_create_critic_relevance_returns_llm_agent` — same pattern; also assert `"relevant" in agent.instruction.lower()`
  - [x] 4.7 `test_create_critic_invalid_name_raises_configuration_error` — verify `ConfigurationError` raised, check `exc.constraint` contains valid preset names
  - [x] 4.8 `test_create_critic_reexported_from_package` — `from gepa_adk import create_critic, critic_presets; assert callable(create_critic); assert isinstance(critic_presets, dict)` (covers AC 4+5)
- [x] [TEA] Testing maturity: add model-override test verifying `create_critic("accuracy", model="some/model")` passes model through to `LlmAgent` (cross-cutting, optional)

## Dev Notes

### GEPA Context: Why Critic Presets Are ASI Generators

The GEPA paper (arXiv:2507.19457, ICLR 2026 Oral) defines **Actionable Side Information (ASI)** as "the text-optimization analogue of a gradient." The reflector LLM reads ASI to diagnose *why* a candidate failed and proposes *targeted* fixes. Without rich ASI, GEPA degrades to blind mutation.

Our `Scorer` protocol returns `tuple[float, dict[str, Any]]` — this IS the GEPA `(scalar, ASI)` primitive. The `CriticOutput` schema maps directly:
- `score` -> scalar fitness metric
- `feedback` -> text ASI (diagnostic explanation)
- `dimension_scores` -> multi-objective ASI (enables Pareto frontier selection)
- `actionable_guidance` -> structured ASI (concrete fix suggestions for the reflector)

**All presets use `CriticOutput`** (not `SimpleCriticOutput`) to maximize ASI quality. This overrides Architecture Decision 3 which originally specified `SimpleCriticOutput` for `"structured_output"` — the ASI quality benefit outweighs the minimal schema overhead. Users who want minimal feedback can still construct their own `LlmAgent` with `SimpleCriticOutput` directly.

### Architecture Compliance

- **Layer**: `adapters/` (uses external lib `google.adk.agents.LlmAgent`)
- **Pattern**: Factory function, NOT registry (MVP). Follow existing `create_component_selector()` pattern in `adapters/selection/component_selector.py`
- **Structural subtyping**: `create_critic` returns `LlmAgent` directly — no Protocol needed for the factory itself. The returned agent is consumed by `CriticScorer` which already satisfies `Scorer` Protocol
- **Boundary enforcement**: Only `adapters/` may import `google.adk` — this is already in `adapters/scoring/`

### Existing Code to Reuse (DO NOT REINVENT)

- `CriticOutput` schema — already in `critic_scorer.py` (score, feedback, dimension_scores, actionable_guidance)
- `SIMPLE_CRITIC_INSTRUCTION` and `ADVANCED_CRITIC_INSTRUCTION` — remain untouched for custom critic users
- `ConfigurationError` — already in `domain/exceptions.py`, accepts keyword-only: `field`, `value`, `constraint` (NO `suggestion` field)
- `LlmAgent` import — already used in `critic_scorer.py`: `from google.adk.agents import LlmAgent`
- `normalize_feedback()` — already handles `CriticOutput` fields and passes them as trial metadata (the ASI pipeline)

### Implementation Reference

Model handling — use conditional kwargs (mirrors reflection agent pattern where `model: str` is required positional):
```python
def create_critic(name: str, *, model: str | None = None) -> LlmAgent:
    model_kwargs: dict[str, Any] = {}
    if model is not None:
        model_kwargs["model"] = model

    presets: dict[str, Callable[[], LlmAgent]] = {
        "structured_output": lambda: LlmAgent(
            name="structured_output_critic",
            instruction=STRUCTURED_OUTPUT_CRITIC_INSTRUCTION,
            output_schema=CriticOutput,
            **model_kwargs,
        ),
        # ... accuracy, relevance follow same pattern
    }

    if name not in presets:
        raise ConfigurationError(...)
    return presets[name]()
```

Naming convention: `{preset_name}_critic` (follows `{purpose}_{role}` pattern from reflection agents: `text_reflector`, `schema_reflector`).

### Preset Instruction Constants

Three NEW constants to add (existing `SIMPLE_CRITIC_INSTRUCTION` and `ADVANCED_CRITIC_INSTRUCTION` remain untouched):

**`STRUCTURED_OUTPUT_CRITIC_INSTRUCTION`**:
```
Evaluate whether the output follows the expected structure and format.

Score from 0.0 (completely malformed) to 1.0 (perfectly structured).

In your feedback, diagnose specific structural issues: missing fields,
wrong types, malformed JSON, schema violations. Quote the problematic
sections and explain what the correct structure should be.

Provide dimension_scores for: schema_compliance, field_completeness,
type_correctness, format_consistency.

In actionable_guidance, give concrete instructions for fixing each
structural issue found. The guidance should be specific enough that
a prompt editor can adjust the system prompt to prevent these issues.
```

**`ACCURACY_CRITIC_INSTRUCTION`**:
```
Evaluate the factual accuracy and correctness of the output relative
to the input and any expected answer.

Score from 0.0 (completely wrong) to 1.0 (perfectly accurate).

In your feedback, identify specific factual errors, logical flaws,
or reasoning mistakes. Quote incorrect passages and explain what
the correct answer or reasoning should be.

Provide dimension_scores for: factual_correctness, reasoning_quality,
completeness, consistency.

In actionable_guidance, explain what knowledge or reasoning patterns
the system prompt should emphasize to prevent these accuracy issues.
```

**`RELEVANCE_CRITIC_INSTRUCTION`**:
```
Evaluate whether the output is relevant to the input query and
addresses what was actually asked.

Score from 0.0 (completely off-topic) to 1.0 (perfectly relevant).

In your feedback, identify which aspects of the query were addressed,
which were missed, and any tangential content that dilutes relevance.
Quote specific passages that are on-topic or off-topic.

Provide dimension_scores for: query_alignment, topic_coverage,
completeness, focus.

In actionable_guidance, explain how the system prompt should be
adjusted to improve topical focus and query coverage.
```

### Exception Pattern

```python
raise ConfigurationError(
    f"Unknown critic preset '{name}'. Valid presets: {', '.join(critic_presets)}",
    constraint=f"Must be one of: {', '.join(critic_presets)}",
    value=name,
    field="name",
)
```
No `cause=` or `from e` needed here — this is a direct raise, not wrapping another exception.

### Growth Phase Vision (Out of Scope — Documented for Future Stories)

The MVP delivers three **content-focused** presets that evaluate agent *output quality*. The factory API (`create_critic()`) is designed to grow with trajectory-dependent presets that evaluate agent *behavior*:

- **`"tool_use"`** — Grades tool selection, argument quality, call sequencing, efficiency. Enables evolving instructions for agents using MCP servers (Playwright, search APIs, databases). Dimensions: `tool_selection_accuracy`, `argument_quality`, `call_sequencing`, `efficiency`, `error_handling`.
- **`"safety"`** — Grades policy compliance, content safety, data leakage, boundary adherence. Content evaluation works now; action-level safety needs trajectory.
- **`"efficiency"`** — Grades step count, token cost, redundancy, directness. Requires trajectory metadata.

**Pipeline change required**: `CriticScorer._format_critic_input()` must accept optional trajectory data for action-focused presets. Same factory API surface — `create_critic("tool_use")` — no breaking changes.

**Innovation context**: gepa-adk is the only GEPA implementation providing structured ASI schemas and preset critics. GEPA-AI and DSPy both use unstructured feedback. Our `CriticOutput` schema formalizes the "gradient" that GEPA conceptualized but never structured.

Candidate stories documented in `epics.md` (Stories 3.4, 3.5, 3.6) and architecture rationale in `architecture.md` Decision 3 Growth phase.

### Documentation Impact

- No documentation impact (confirmed). This is a new function added to the public API — the v2.0.0 docs were just released and this will be documented in a future Epic 8 story (8-2-documentation-updates).

### Project Structure Notes

- Implementation file: `src/gepa_adk/adapters/scoring/critic_scorer.py` (add to existing file)
- Test file: `tests/unit/adapters/scoring/test_critic_preset_factory.py` (new file, new directory)
- Export chain: `critic_scorer.py` -> `scoring/__init__.py` -> `adapters/__init__.py` -> `gepa_adk/__init__.py`
- `tests/unit/adapters/scoring/` does NOT exist yet — create it with `__init__.py`
- `critic_scorer.py` currently has NO `__all__` — add one at file BOTTOM

### References

- [Source: GEPA paper arXiv:2507.19457 — ASI concept, feedback primitives, Pareto frontier]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3, Story 3.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 3 - Critic Presets (overridden: all presets use CriticOutput)]
- [Source: src/gepa_adk/adapters/scoring/critic_scorer.py — CriticScorer, CriticOutput schema, instructions, normalize_feedback]
- [Source: src/gepa_adk/adapters/selection/component_selector.py — factory pattern reference]
- [Source: src/gepa_adk/adapters/agents/reflection_agents.py — LlmAgent factory and model-handling precedent]
- [Source: src/gepa_adk/domain/exceptions.py — ConfigurationError (field, value, constraint only)]
- [Source: _bmad-output/project-context.md — architecture rules, exception patterns]

## AC-to-Test Mapping

| AC | Test | Status |
|----|------|--------|
| AC1: `create_critic()` exists and returns `LlmAgent` | `test_create_critic_structured_output_returns_llm_agent` | PASS |
| AC2: Three MVP presets available | `test_critic_presets_is_dict_with_three_entries` | PASS |
| AC3: Invalid preset raises `ConfigurationError` | `test_create_critic_invalid_name_raises_configuration_error` | PASS |
| AC4: Re-exported via `gepa_adk.__init__` | `test_create_critic_reexported_from_package` | PASS |
| AC5: `critic_presets` dict re-exported | `test_create_critic_reexported_from_package` | PASS |
| AC6: Four+ deterministic unit tests | All 7 tests in `test_critic_preset_factory.py` | PASS |

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
None — clean implementation, no debugging needed.

### Completion Notes List
- Implemented `create_critic()` factory function and `critic_presets` dict in `critic_scorer.py`
- Added 3 preset instruction constants: `STRUCTURED_OUTPUT_CRITIC_INSTRUCTION`, `ACCURACY_CRITIC_INSTRUCTION`, `RELEVANCE_CRITIC_INSTRUCTION`
- All presets use `CriticOutput` schema (maximizing ASI quality for reflector)
- Model passthrough uses conditional kwargs pattern (mirrors reflection agent precedent)
- Invalid preset raises `ConfigurationError` with `constraint` field listing valid presets
- Added `__all__` at file bottom with all exports
- Wired exports through full chain: `critic_scorer.py` -> `scoring/__init__.py` -> `adapters/__init__.py` -> `gepa_adk/__init__.py`
- Updated existing `test_adapter_reexports.py` to include 5 new symbols
- Created 7 unit tests (3 per-preset + invalid name + model override + presets dict + re-export)
- Full suite: 2101 passed, 0 failures

### File List
- `src/gepa_adk/adapters/scoring/critic_scorer.py` (modified — factory, presets, instructions, `__all__`)
- `src/gepa_adk/adapters/scoring/__init__.py` (modified — new re-exports)
- `src/gepa_adk/adapters/__init__.py` (modified — new re-exports)
- `src/gepa_adk/__init__.py` (modified — new re-exports and `__all__` entries)
- `tests/unit/adapters/scoring/__init__.py` (new)
- `tests/unit/adapters/scoring/test_critic_preset_factory.py` (new — 7 tests)
- `tests/unit/adapters/test_adapter_reexports.py` (modified — 5 new re-export cases)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — status update)
- `_bmad-output/implementation-artifacts/3-1-implement-critic-preset-factory.md` (modified — task tracking)

## Change Log
- 2026-03-07: Implemented critic preset factory with 3 presets, full export chain, and 7 unit tests

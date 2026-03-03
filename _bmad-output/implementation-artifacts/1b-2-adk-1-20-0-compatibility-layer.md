# Story 1B.2: ADK 1.20.0 Compatibility Layer

Status: review
Branch: feat/1b-2-adk-compatibility-layer

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer using an enterprise-deployed ADK version,
I want gepa-adk to work with google-adk 1.20.0 through latest,
So that I can adopt the library without upgrading my ADK version.

## Acceptance Criteria

1. **Discovery-first approach** — Given the current dependency floor is google-adk>=1.22.0 with no compatibility shims, When the compatibility work is performed, Then discovery is done first: install adk==1.20.0 in isolation, run full test suite, categorize failures as import errors, API signature changes, or behavioral changes
2. **Adapters-and-api-only shims** — Compatibility shims are implemented in the adapters layer and/or the `api.py` composition root — no version-conditional code in domain/ports/engine
3. **Dependency floor lowered** — `pyproject.toml` dependency is updated from `google-adk>=1.22.0` to the lowest working version (target: `google-adk>=1.20.0`; may be `>=1.21.0` if 1.20.0 proves incompatible via discovery)
4. **CI version matrix** — The existing `tests.yml` CI workflow is updated with an ADK version matrix testing against adk==1.20.0 and adk-latest
5. **Behavior-only assertions** — No test uses version-conditional assertions — tests assert behavior, not version
6. **API differences documented** — API differences are documented in a compatibility section in the ADK adapter module docstring

## Tasks / Subtasks

- [x] Task 1: Discovery — Install adk==1.20.0 and categorize failures (AC: 1)
  - [x] 1.1 Create a fresh venv: `uv venv .venv-compat --python 3.12 && uv pip install --python .venv-compat/bin/python -e ".[dev]"` then override: `uv pip install --python .venv-compat/bin/python google-adk==1.20.0`. Alternative: `uv run --with google-adk==1.20.0 pytest` (verify this downgrades correctly)
  - [x] 1.2 Categorize each failure into one of four types: (a) import error, (b) API signature change, (c) behavioral change, (d) deprecation warning elevated to error by `filterwarnings = ["error"]` config
  - [x] 1.3 Document findings in Completion Notes of this story file — include failure count, category breakdown, and affected files
  - [x] 1.4 Run `pip show google-genai` (or `uv pip show`) in the 1.20.0 venv to get the resolved google-genai version. Compare with current locked version (1.57.0). If different, verify `from google.genai.types import Content, Part` still works
  - [x] 1.5 If `engine/reflection_agents.py` crashes on ADK 1.20.0 (pre-existing boundary violation from Story 1B.4), use `pytest --ignore=tests/` selectively or `-k "not reflection"` to complete discovery for the rest of the codebase. Document reflection failures as a 1B.4 dependency
  - **DECISION GATE:** Zero failures, zero warnings → **SKIP Task 2, proceed to Tasks 3–7**
- [x] Task 2: SKIPPED — Discovery gate passed clean, no shims needed (AC: 2)
  - [x] 2.1–2.5: All skipped — adk 1.20.0 is fully API-compatible with 1.22.0 for gepa-adk usage
- [x] Task 3: Update dependency floor in pyproject.toml (AC: 3)
  - [x] 3.1 Change `google-adk>=1.22.0` to `google-adk>=1.20.0`
  - [x] 3.2 Run `uv lock` to regenerate the lockfile
  - [x] 3.3 Run full test suite with adk==1.20.0 and adk-latest to verify both work
- [x] Task 4: Add ADK version matrix to CI (AC: 4)
  - [x] 4.1 Update `.github/workflows/tests.yml` to add a strategy matrix with `adk-version: ["1.20.0", ""]`
  - [x] 4.2 Add a step that overrides the locked google-adk version: `uv pip install google-adk==${{ matrix.adk-version }}` (for pinned) or skip override for latest
  - [x] 4.3 Both matrix entries use same pytest command with 85% coverage floor (verified locally in Task 3.3)
  - [x] 4.4 type-check, lint jobs unaffected (run once, not per-version); codecov only uploads from latest entry
- [x] Task 5: Verify all tests are behavior-only + add compatibility contract test (AC: 5)
  - [x] 5.1 Grep for any version-conditional test assertions — none found
  - [x] 5.2 N/A — no version-conditional assertions exist
  - [x] 5.3 Created `tests/contracts/test_adk_compatibility.py` — 16 import smoke tests covering LlmAgent, BaseAgent, SequentialAgent, LoopAgent, ParallelAgent, Runner, BaseSessionService, InMemorySessionService, Session, Content, Part, GenerateContentConfig, BaseLlm, LiteLlm, FunctionTool, App
  - [x] 5.4 All 16 contract tests pass on both adk==1.20.0 and adk-latest
- [x] Task 6: Document API differences (AC: 6)
  - [x] 6.1 Added `Compatibility:` section to `adapters/__init__.py` module docstring — documents ADK 1.20.0–latest compatibility
  - [x] 6.2 N/A — no shim files created (zero API differences found)
  - [x] 6.3 docvet passes on updated docstring
- [x] Task 7: Validate (AC: all)
  - [x] 7.1 ruff check + format: all passed
  - [x] 7.2 ty check src tests: all passed
  - [x] 7.3 pytest --cov --cov-fail-under=85: 1820 passed, 88% coverage
  - [x] 7.4 check_boundaries.sh: 7 pre-existing violations (tracked by Story 1B.4, CI gate is soft) — zero new violations introduced
  - [x] 7.5 check_protocol_coverage.py: 1 pre-existing gap (EvaluationPolicyProtocol) — not introduced by this story
  - [x] 7.6 pre-commit run --all-files: all 9 hooks passed

## Dev Notes

### Discovery-First Approach

This story requires a **phased approach**: discovery before implementation. The developer MUST NOT jump straight to writing shims — the first task is to install adk==1.20.0, run the test suite, and understand what actually breaks. The scope of shim work depends entirely on what fails.

**Expected outcome of discovery:** Based on analysis of ADK release notes (v1.20.0 through v1.22.0), the core APIs used by gepa-adk (agents, sessions, runners) appear stable across these versions. The main risk areas are:
- **Transitive google-genai version:** adk==1.20.0 may pin a different google-genai version, which could break `Content`/`Part`/`types` imports
- **App class import path:** `google.adk.apps.app.App` — verify this existed in 1.20.0
- **LiteLlm model class:** `google.adk.models.lite_llm.LiteLlm` was added IN 1.20.0 — should be available
- **BaseLlm class:** `google.adk.models.base_llm.BaseLlm` — verify available in 1.20.0
- **FunctionTool:** `google.adk.tools.FunctionTool` — verify available in 1.20.0

If discovery reveals that adk==1.20.0 is API-compatible with 1.22.0 for gepa-adk's usage, the shim layer may be minimal or unnecessary — just the dependency floor change and CI matrix addition.

**Decision gate after Task 1:** If zero failures and zero warnings, skip Task 2 entirely and proceed to Tasks 3–7. If discovery reveals irreconcilable transitive dependency conflicts, the story outcome becomes "documented infeasibility" with a recommendation for the lowest working version floor.

**Infeasibility exit condition:** If adk==1.20.0 requires a google-genai version that breaks `Content`/`Part`/`types` imports and no shim can resolve the conflict, accept a higher floor (e.g., `>=1.21.0`). Document WHY the original 1.20.0 target was infeasible so the PM can reassess FR13.

### ADK Release Notes Summary (v1.20.0 → v1.22.0)

**v1.20.0 (2025-12-01):**
- Multi-provider support added (Claude, LiteLLM) — `LiteLlm` model class was introduced here
- Enum constraint added to `transfer_to_agent` tool (not used by gepa-adk)
- Sub-agent name uniqueness validation added
- LiteLLM system instruction role changed from "developer" to "system"
- No breaking changes to core agent/session/runner APIs

**v1.21.0 (2025-12-11):**
- Interactions API support added (`use_interactions_api` parameter)
- `Gemma3Ollama` model added (not used by gepa-adk)
- `add_session_to_memory` methods added to contexts
- No breaking changes to core APIs

**v1.22.0 (2026-01-08):**
- **Breaking:** OpenTelemetry for BigQuery plugin tracing (not used by gepa-adk)
- `thinking_config` now allowed in `generate_content_config`
- Credential manager accepts `tool_context` instead of `callback_context`
- Auto-session creation support added

**Key insight:** No breaking changes to the core APIs (LlmAgent, Runner, Session, etc.) that gepa-adk depends on. The compatibility layer may be trivially small.

### Current ADK Import Surface (8 Files)

All ADK imports are in `adapters/` layer (except one boundary violation in `engine/reflection_agents.py` tracked by Story 1B.4):

| File | Imports |
|------|---------|
| `api.py` | LlmAgent, LoopAgent, ParallelAgent, SequentialAgent, App, BaseLlm, LiteLlm, Runner, BaseSessionService, InMemorySessionService |
| `adapters/evolution/adk_adapter.py` | LlmAgent, BaseSessionService, InMemorySessionService, Content, Part |
| `adapters/evolution/multi_agent.py` | LlmAgent, SequentialAgent, Runner, BaseSessionService, InMemorySessionService |
| `adapters/execution/agent_executor.py` | Runner, BaseSessionService, InMemorySessionService, Session, google.genai.types |
| `adapters/scoring/critic_scorer.py` | BaseAgent, BaseSessionService, InMemorySessionService |
| `adapters/workflow/workflow.py` | LlmAgent, LoopAgent, ParallelAgent, SequentialAgent |
| `adapters/media/video_blob_service.py` | Part (from google.genai.types) |
| `engine/reflection_agents.py` | LlmAgent, FunctionTool (**boundary violation** — tracked by Story 1B.4) |

### Compatibility Shim Pattern

If shims are needed, they MUST follow this pattern:

```python
# adapters/{concern}/adk_compat.py
"""ADK version compatibility shims.

Abstracts API differences between google-adk 1.20.0 and latest.
All version-conditional logic is isolated here.

Compatibility:
    - google-adk 1.20.0: [describe differences]
    - google-adk 1.22.0+: [describe current behavior]
"""

try:
    from google.adk.some_new_module import NewThing
except ImportError:
    # Fallback for adk < 1.22.0
    from google.adk.old_module import OldThing as NewThing
```

**CRITICAL RULE:** Shims live ONLY in `adapters/` and `api.py` (composition root) — never in domain, ports, engine, or utils. The `api.py` file is the outermost boundary / composition root (per ADR-000) and is allowed to know about concrete ADK types. It is intentionally excluded from `check_boundaries.sh` scanning.

### CI Matrix Design

The `tests.yml` workflow update should follow this pattern:

```yaml
strategy:
  matrix:
    adk-version: ["1.20.0", ""]  # "" means use locked/latest
  fail-fast: false

steps:
  - name: Override ADK version (if pinned)
    if: matrix.adk-version != ''
    run: uv pip install google-adk==${{ matrix.adk-version }}
```

**Important:** Only the `test` job needs the matrix. Lint and type-check jobs should run once (not per-version).

### Hexagonal Boundary Rules (ADR-000)

| Layer | Can Import From | Cannot Import From |
|-------|-----------------|-------------------|
| `domain/` | stdlib only (exception: `structlog`) | `ports/`, `adapters/`, external libs |
| `ports/` | `domain/` + stdlib | `adapters/`, external libs |
| `adapters/` | `ports/` + `domain/` + external libs (ADK, LiteLLM) | — |
| `engine/` | `ports/` + `domain/` + `structlog` | `adapters/` (receives via injection) |
| `utils/` | stdlib + `structlog` | — |

### engine/reflection_agents.py Boundary Violation (Story 1B.4)

The file `engine/reflection_agents.py` imports `LlmAgent` and `FunctionTool` from `google.adk` — a pre-existing boundary violation tracked by Story 1B.4. If these imports fail on ADK 1.20.0:

- **Do NOT fix them in this story** — that's Story 1B.4's scope
- Use `pytest --ignore=tests/unit/engine/test_reflection_agents.py` or `pytest -k "not reflection"` to get discovery results for the rest of the codebase
- Document reflection-specific failures as a 1B.4 dependency in Completion Notes
- If reflection failures prevent the 85% coverage floor from being met on the 1.20.0 matrix entry, note this in the CI workflow (may need a temporary coverage exception for the 1.20.0 matrix entry, or the story may need to wait for 1B.4)

### CI Coverage Floor Interaction

The 85% coverage floor is enforced per-run. If adk==1.20.0 causes import-time failures that prevent modules from loading, coverage will drop below 85% and fail for coverage reasons rather than test failure reasons. This cascading failure mode means a single import error can mask the real problem. During discovery, run pytest with `--no-cov` first to see actual test failures, then re-run with coverage to check the floor.

### ADK Compatibility Contract Test

Create `tests/contracts/test_adk_compatibility.py` to serve as a regression detector for ADK import path stability. Shape:

```python
"""ADK import compatibility contract tests.

Verifies that all google-adk and google-genai import paths used by
gepa-adk are available in the installed ADK version. Catches import-path
renames and removals across ADK versions immediately on CI.

Attributes:
    pytestmark: Contract-level test marker.
"""

import pytest

pytestmark = pytest.mark.contract


class TestADKAgentImports:
    """Verify all ADK agent types used by gepa-adk are importable."""

    def test_llm_agent_importable(self):
        from google.adk.agents import LlmAgent  # noqa: F401

    def test_base_agent_importable(self):
        from google.adk.agents import BaseAgent  # noqa: F401

    def test_workflow_agents_importable(self):
        from google.adk.agents import SequentialAgent, LoopAgent, ParallelAgent  # noqa: F401


class TestADKSessionImports:
    """Verify all ADK session types used by gepa-adk are importable."""

    def test_session_service_importable(self):
        from google.adk.sessions import BaseSessionService, InMemorySessionService  # noqa: F401

    def test_session_importable(self):
        from google.adk.sessions import Session  # noqa: F401


class TestADKRunnerImports:
    """Verify ADK Runner is importable."""

    def test_runner_importable(self):
        from google.adk.runners import Runner  # noqa: F401


class TestGenAITypeImports:
    """Verify google-genai types used by gepa-adk are importable."""

    def test_content_part_importable(self):
        from google.genai.types import Content, Part  # noqa: F401
```

This test costs near-zero runtime and catches version-breaking renames across every CI run. Error messages from import failures are self-explanatory.

### Testing Standards

- `pytestmark = pytest.mark.contract` for the compatibility test (not unit)
- `pytestmark = pytest.mark.unit` at module top
- Tests grouped in classes: `TestConstructor`, `TestCompatibility`
- Use `create_mock_adapter` factory for adapter tests
- 85% coverage floor enforced in CI
- `asyncio_mode = "auto"` — do NOT add `@pytest.mark.asyncio`
- `filterwarnings = ["error"]` — new imports causing warnings will break CI

### Previous Story Learnings (from Story 1B.1)

1. **Pre-commit hooks are strict** — yamllint, ruff, ty, pytest, docvet all enforced. Run them before committing.
2. **docvet catches missing docstring sections** — Module docstrings need `Attributes:`, `Examples:`, `See Also:` sections.
3. **`__all__` at file BOTTOM** — Update when adding new public names.
4. **Piggybacked improvements must be documented** — If you find issues while building shims, document but don't fix them unless trivially scoped.
5. **Pre-existing boundary violations exist** — 7 violations found by Story 1B.1. Do NOT fix them here (that's Story 1B.4).
6. **boundaries.yml uses `continue-on-error: true`** — The CI gate is soft until Story 1B.4 resolves violations.

### Project Structure Notes

```
src/gepa_adk/
├── api.py                              # MAYBE MODIFY — composition root, may need shims
├── domain/                             # NO ADK imports allowed
├── ports/                              # NO ADK imports allowed
├── engine/                             # NO ADK imports allowed (1 violation tracked)
├── utils/                              # NO ADK imports allowed
└── adapters/                           # ALL ADK imports live here
    ├── __init__.py                     # Re-exports — add Compatibility docstring section
    ├── evolution/
    │   ├── adk_adapter.py              # Heavy ADK usage (agents, sessions, types)
    │   └── multi_agent.py              # ADK agents, runners, sessions
    ├── execution/
    │   ├── agent_executor.py           # ADK runner, sessions, genai types
    │   └── trial_builder.py
    ├── scoring/
    │   └── critic_scorer.py            # ADK BaseAgent, sessions
    ├── workflow/
    │   └── workflow.py                 # ADK agent types (Llm, Sequential, etc.)
    ├── media/
    │   └── video_blob_service.py       # google.genai.types.Part
    ├── components/
    ├── selection/
    └── stoppers/

.github/workflows/
├── tests.yml                           # MODIFY — add ADK version matrix
├── boundaries.yml                      # EXISTING — verify still passes
└── ...                                 # Other workflows unaffected

pyproject.toml                          # MODIFY — lower google-adk floor to >=1.20.0

tests/contracts/
├── test_adk_compatibility.py           # NEW — import smoke tests for all ADK types
└── ...                                 # Existing contract tests unaffected
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1B.2] — Acceptance criteria with BDD format
- [Source: _bmad-output/planning-artifacts/architecture.md#Version Pinning Strategy] — ADK version matrix CI approach
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] — Adapter sub-package organization
- [Source: _bmad-output/planning-artifacts/architecture.md#Growth-Phase Readiness] — ADK compatibility gap identified
- [Source: _bmad-output/project-context.md] — 95 implementation rules (import boundaries lines 58-68)
- [Source: docs/adr/ADR-000-hexagonal-architecture.md] — Layer boundary rules
- [Source: docs/adr/ADR-006-external-library-integration.md] — External deps isolated in adapters/
- [Source: .github/workflows/tests.yml] — Current CI workflow to extend with version matrix
- [Source: pyproject.toml] — Current dependency: `google-adk>=1.22.0`
- [Source: _bmad-output/implementation-artifacts/1b-1-architectural-boundary-enforcement-scripts.md] — Previous story learnings, boundary violations
- [Source: https://github.com/google/adk-python/releases] — ADK release notes v1.20.0–v1.22.0

### Git Intelligence

Recent commits on `develop`:
```
22eb124 chore(docvet): enforce presence check with 100% threshold (#263)
4522479 chore(docs): standardize badges and replace TestPyPI with local smoke test (#262)
c0130cb feat(ci): add hexagonal boundary enforcement scripts and CI workflow (#261)
1df6a5e test(contracts): add Protocol method signature drift guard (#260)
ff343ac feat(ports): define EvolutionResultProtocol for unified result types (#259)
```

All Epic 1A stories merged. Story 1B.1 merged. Codebase stable.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

**Task 1 — Discovery (2026-03-03):**
- Method: `uv run --with google-adk==1.20.0 pytest --no-cov -q`
- Result: 1804 passed, 1 skipped, 67 deselected (api-marked), 0 failures, 0 warnings
- Failure breakdown: (a) import errors: 0, (b) API signature changes: 0, (c) behavioral changes: 0, (d) deprecation warnings: 0
- google-genai version on adk 1.20.0: 1.57.0 (same as current locked version — no transitive conflict)
- Content/Part imports verified OK on 1.20.0
- engine/reflection_agents.py: No crashes on 1.20.0 (boundary violation still exists but doesn't affect compatibility)
- **Decision gate outcome:** Zero failures → Task 2 (shims) SKIPPED entirely. ADK 1.20.0 is fully compatible.

**Tasks 3–7 — Implementation and Validation (2026-03-03):**
- Lowered dependency floor from google-adk>=1.22.0 to google-adk>=1.20.0
- Added CI version matrix (adk 1.20.0 + latest) to tests.yml
- Created 16 ADK import compatibility contract tests
- Added Compatibility section to adapters/__init__.py docstring
- All pre-commit hooks (9/9), ruff, ty, pytest (1820 passed, 88% coverage), docvet pass
- No shims needed — ADK 1.20.0 API surface is identical to 1.22.0 for gepa-adk usage

### File List

- `pyproject.toml` — Modified: google-adk floor lowered from >=1.22.0 to >=1.20.0
- `uv.lock` — Modified: regenerated lockfile
- `.github/workflows/tests.yml` — Modified: added ADK version matrix (1.20.0 + latest) to test job
- `src/gepa_adk/adapters/__init__.py` — Modified: added Compatibility section to module docstring
- `tests/contracts/test_adk_compatibility.py` — New: 16 import smoke tests for all ADK/genai types
- `_bmad-output/implementation-artifacts/1b-2-adk-1-20-0-compatibility-layer.md` — Modified: story tracking
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Modified: status updates

### Change Log

- 2026-03-03: Story 1B.2 implemented — ADK 1.20.0 compatibility confirmed via discovery (zero failures), dependency floor lowered, CI version matrix added, contract tests created, API compatibility documented

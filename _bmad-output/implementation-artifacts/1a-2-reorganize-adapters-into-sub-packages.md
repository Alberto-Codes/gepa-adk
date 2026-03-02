# Story 1A.2: Reorganize Adapters into Sub-Packages

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a contributor,
I want adapters organized by concern in sub-packages with backward-compatible re-exports,
So that I can navigate and extend the adapter layer without cognitive overload.

## Acceptance Criteria

1. **7 new sub-packages exist** under `src/gepa_adk/adapters/`: `execution/`, `scoring/`, `evolution/`, `selection/`, `components/`, `workflow/`, `media/`
2. **Existing `stoppers/` sub-package remains untouched** — no file moves, no new `__init__.py`, no modifications
3. **Each sub-package has an `__init__.py`** that exports its public symbols with `__all__`
4. **Single-module packages** include a docstring in `__init__.py` explaining the package's purpose and anticipated growth
5. **`adapters/__init__.py` re-exports every previously-importable symbol** to its new sub-package location (all 40 symbols in current `__all__`)
6. **Deprecation tests** systematically verify every previously-importable symbol: `assert adapters.X is adapters.subpkg.X`
7. **Full `pytest` run passes** with zero failures, zero import warnings, and no coverage drop below current level
8. **ADR-014 document** is written at `docs/adr/ADR-014-adapter-reorganization.md`

## Tasks / Subtasks

- [x] Task 1: Create sub-package directories with `__init__.py` files (AC: 1, 3, 4)
  - [x]1.1 Create `adapters/execution/__init__.py`
  - [x]1.2 Create `adapters/scoring/__init__.py`
  - [x]1.3 Create `adapters/evolution/__init__.py`
  - [x]1.4 Create `adapters/selection/__init__.py`
  - [x]1.5 Create `adapters/components/__init__.py`
  - [x]1.6 Create `adapters/workflow/__init__.py`
  - [x]1.7 Create `adapters/media/__init__.py`
- [x]Task 2: Move adapter modules into sub-packages (AC: 1, 2)
  - [x]2.1 Move `agent_executor.py` + `trial_builder.py` → `execution/`
  - [x]2.2 Move `critic_scorer.py` → `scoring/`
  - [x]2.3 Move `adk_adapter.py` + `multi_agent.py` → `evolution/`
  - [x]2.4 Move `candidate_selector.py` + `component_selector.py` + `evaluation_policy.py` → `selection/`
  - [x]2.5 Move `component_handlers.py` → `components/`
  - [x]2.6 Move `workflow.py` → `workflow/`
  - [x]2.7 Move `video_blob_service.py` → `media/`
  - [x]2.8 Verify `stoppers/` is completely untouched (no file moves, no changes)
- [x]Task 3: Fix internal cross-adapter imports after moves (AC: 7)
  - [x]3.1 Update imports in `adk_adapter.py` (references `component_handlers`, `trial_builder`, `video_blob_service`)
  - [x]3.2 Update imports in `multi_agent.py` (references `component_handlers`, `trial_builder`, `workflow`, `agent_executor`)
  - [x]3.3 Update any other internal adapter-to-adapter imports
- [x]Task 4: Update `adapters/__init__.py` re-exports (AC: 5)
  - [x]4.1 Change all import paths to new sub-package locations
  - [x]4.2 Maintain identical `__all__` list — same 40 symbols
  - [x]4.3 Update module docstring to note sub-package structure
- [x]Task 5: Update external import sites (AC: 7)
  - [x]5.1 Update `src/gepa_adk/api.py` imports
  - [x]5.2 Update `src/gepa_adk/__init__.py` if needed
  - [x]5.3 Update `src/gepa_adk/engine/async_engine.py` imports (uses `RoundRobinComponentSelector`, `FullEvaluationPolicy`)
  - [x]5.4 Grep for any remaining `from gepa_adk.adapters.<old_module>` and update
- [x]Task 6: Update test imports (AC: 7)
  - [x]6.1 Update `tests/unit/adapters/` test files — import from new sub-package paths
  - [x]6.2 Update `tests/integration/adapters/` test files
  - [x]6.3 Update `tests/contracts/` test files
  - [x]6.4 Update conftest files that reference adapter imports
- [x]Task 7: Write deprecation tests (AC: 6)
  - [x]7.1 Create `tests/unit/adapters/test_adapter_reexports.py`
  - [x]7.2 One `assert adapters.X is adapters.subpkg.X` test per re-exported symbol (40 assertions)
  - [x]7.3 Verify import from both old path (`gepa_adk.adapters.X`) and new path (`gepa_adk.adapters.subpkg.module.X`) resolve to same object
- [x]Task 8: Write ADR-014 (AC: 8)
  - [x]8.1 Create `docs/adr/ADR-014-adapter-reorganization.md`
  - [x]8.2 Follow existing ADR format (see `docs/adr/ADR-000-hexagonal-architecture.md` for template)
  - [x]8.3 Document: context, decision, rationale, consequences, migration safety
- [x]Task 9: Validate (AC: 7)
  - [x]9.1 Run `ruff format` + `ruff check --fix` on all modified files
  - [x]9.2 Run `ty check src tests`
  - [x]9.3 Run full `pytest` — zero failures
  - [x]9.4 Run `docvet check` on new/modified docstrings
  - [x]9.5 Run pre-commit hooks (`pre-commit run --all-files`)
  - [x]9.6 Verify coverage has not dropped below current level

## Dev Notes

### Architecture-Mandated Target Structure

From [Source: _bmad-output/planning-artifacts/architecture.md, Decision 5 + Target Directory Tree]:

```
adapters/
├── __init__.py          # Re-exports preserving old import paths
├── execution/           # Agent execution infrastructure
│   ├── __init__.py
│   ├── agent_executor.py    # AgentExecutor, SessionNotFoundError
│   └── trial_builder.py     # TrialBuilder
├── scoring/             # Scoring infrastructure
│   ├── __init__.py
│   └── critic_scorer.py     # CriticScorer, SimpleCriticOutput, CriticOutput, constants, normalize_feedback
├── evolution/           # Core adapter implementations
│   ├── __init__.py
│   ├── adk_adapter.py       # ADKAdapter (single-agent)
│   └── multi_agent.py       # MultiAgentAdapter (multi-agent/workflow)
├── selection/           # Selection strategies
│   ├── __init__.py
│   ├── candidate_selector.py  # Pareto, CurrentBest, EpsilonGreedy + create_candidate_selector()
│   ├── component_selector.py  # RoundRobin, All + create_component_selector()
│   └── evaluation_policy.py   # Full, Subset policies
├── components/          # Evolvable surface handlers
│   ├── __init__.py
│   └── component_handlers.py  # ComponentHandlerRegistry + 3 built-in handlers + get_handler + register_handler
├── stoppers/            # EXISTING — DO NOT TOUCH
│   └── (unchanged)
├── workflow/            # Workflow utilities
│   ├── __init__.py
│   └── workflow.py          # is_workflow_agent, find_llm_agents, WorkflowAgentType, clone_workflow_with_overrides
└── media/               # Multimodal adapters
    ├── __init__.py
    └── video_blob_service.py  # VideoBlobService, MAX_VIDEO_SIZE_BYTES
```

### Complete Symbol Re-Export Map (40 symbols)

Current `adapters/__init__.py` exports exactly these symbols — all must remain importable from `gepa_adk.adapters`:

| Symbol | Current Module | Target Sub-Package |
|--------|---------------|-------------------|
| `ADKAdapter` | `adk_adapter` | `evolution.adk_adapter` |
| `AgentExecutor` | `agent_executor` | `execution.agent_executor` |
| `SessionNotFoundError` | `agent_executor` | `execution.agent_executor` |
| `ParetoCandidateSelector` | `candidate_selector` | `selection.candidate_selector` |
| `CurrentBestCandidateSelector` | `candidate_selector` | `selection.candidate_selector` |
| `EpsilonGreedyCandidateSelector` | `candidate_selector` | `selection.candidate_selector` |
| `create_candidate_selector` | `candidate_selector` | `selection.candidate_selector` |
| `ComponentHandlerRegistry` | `component_handlers` | `components.component_handlers` |
| `GenerateContentConfigHandler` | `component_handlers` | `components.component_handlers` |
| `InstructionHandler` | `component_handlers` | `components.component_handlers` |
| `OutputSchemaHandler` | `component_handlers` | `components.component_handlers` |
| `component_handlers` | `component_handlers` | `components.component_handlers` |
| `get_handler` | `component_handlers` | `components.component_handlers` |
| `register_handler` | `component_handlers` | `components.component_handlers` |
| `RoundRobinComponentSelector` | `component_selector` | `selection.component_selector` |
| `AllComponentSelector` | `component_selector` | `selection.component_selector` |
| `create_component_selector` | `component_selector` | `selection.component_selector` |
| `CriticScorer` | `critic_scorer` | `scoring.critic_scorer` |
| `SimpleCriticOutput` | `critic_scorer` | `scoring.critic_scorer` |
| `CriticOutput` | `critic_scorer` | `scoring.critic_scorer` |
| `SIMPLE_CRITIC_INSTRUCTION` | `critic_scorer` | `scoring.critic_scorer` |
| `ADVANCED_CRITIC_INSTRUCTION` | `critic_scorer` | `scoring.critic_scorer` |
| `normalize_feedback` | `critic_scorer` | `scoring.critic_scorer` |
| `FullEvaluationPolicy` | `evaluation_policy` | `selection.evaluation_policy` |
| `SubsetEvaluationPolicy` | `evaluation_policy` | `selection.evaluation_policy` |
| `MultiAgentAdapter` | `multi_agent` | `evolution.multi_agent` |
| `is_workflow_agent` | `workflow` | `workflow.workflow` |
| `find_llm_agents` | `workflow` | `workflow.workflow` |
| `WorkflowAgentType` | `workflow` | `workflow.workflow` |
| `TimeoutStopper` | `stoppers` | `stoppers` (unchanged) |
| `TrialBuilder` | `trial_builder` | `execution.trial_builder` |
| `VideoBlobService` | `video_blob_service` | `media.video_blob_service` |
| `MAX_VIDEO_SIZE_BYTES` | `video_blob_service` | `media.video_blob_service` |

**Note:** The `stoppers` re-export does NOT change — `TimeoutStopper` stays imported from `gepa_adk.adapters.stoppers`.

### Critical Internal Cross-Adapter Imports

These files import from other adapter modules — their internal imports MUST be updated after the move:

1. **`adk_adapter.py`** (→ `evolution/adk_adapter.py`):
   - `from gepa_adk.adapters.component_handlers import ...` → `from gepa_adk.adapters.components.component_handlers import ...`
   - `from gepa_adk.adapters.trial_builder import ...` → `from gepa_adk.adapters.execution.trial_builder import ...`
   - `from gepa_adk.adapters.video_blob_service import ...` → `from gepa_adk.adapters.media.video_blob_service import ...`

2. **`multi_agent.py`** (→ `evolution/multi_agent.py`):
   - `from gepa_adk.adapters.component_handlers import ...` → `from gepa_adk.adapters.components.component_handlers import ...`
   - `from gepa_adk.adapters.trial_builder import ...` → `from gepa_adk.adapters.execution.trial_builder import ...`
   - `from gepa_adk.adapters.workflow import ...` → `from gepa_adk.adapters.workflow.workflow import ...`
   - `from gepa_adk.adapters.agent_executor import ...` → `from gepa_adk.adapters.execution.agent_executor import ...`

### External Import Sites to Update

These files outside `adapters/` import adapter modules directly:

1. **`src/gepa_adk/api.py`**: Imports `ADKAdapter`, `AgentExecutor`, candidate/component selectors, `CriticScorer`, `MultiAgentAdapter`, workflow utils — update to sub-package paths
2. **`src/gepa_adk/__init__.py`**: Re-exports from `api.py` — likely no change needed (imports via `api`)
3. **`src/gepa_adk/engine/async_engine.py`**: Imports `RoundRobinComponentSelector` and `FullEvaluationPolicy` — update to `selection` sub-package paths

### Re-Export Template

From [Source: architecture.md, "Adapter Re-Export Template"]:

```python
# adapters/__init__.py
"""Adapter layer re-exports for backward compatibility.

All public symbols are re-exported from their sub-package locations.
New code should import from sub-packages directly.
"""

# Evolution adapters
from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter
from gepa_adk.adapters.evolution.multi_agent import MultiAgentAdapter

# Execution
from gepa_adk.adapters.execution.agent_executor import AgentExecutor, SessionNotFoundError
from gepa_adk.adapters.execution.trial_builder import TrialBuilder

# Scoring
from gepa_adk.adapters.scoring.critic_scorer import (
    ADVANCED_CRITIC_INSTRUCTION,
    SIMPLE_CRITIC_INSTRUCTION,
    CriticOutput,
    CriticScorer,
    SimpleCriticOutput,
    normalize_feedback,
)

# Selection
from gepa_adk.adapters.selection.candidate_selector import (
    CurrentBestCandidateSelector,
    EpsilonGreedyCandidateSelector,
    ParetoCandidateSelector,
    create_candidate_selector,
)
from gepa_adk.adapters.selection.component_selector import (
    AllComponentSelector,
    RoundRobinComponentSelector,
    create_component_selector,
)
from gepa_adk.adapters.selection.evaluation_policy import (
    FullEvaluationPolicy,
    SubsetEvaluationPolicy,
)

# Components
from gepa_adk.adapters.components.component_handlers import (
    ComponentHandlerRegistry,
    GenerateContentConfigHandler,
    InstructionHandler,
    OutputSchemaHandler,
    component_handlers,
    get_handler,
    register_handler,
)

# Workflow
from gepa_adk.adapters.workflow.workflow import (
    WorkflowAgentType,
    find_llm_agents,
    is_workflow_agent,
)

# Stoppers (unchanged — already a sub-package)
from gepa_adk.adapters.stoppers import TimeoutStopper

# Media
from gepa_adk.adapters.media.video_blob_service import MAX_VIDEO_SIZE_BYTES, VideoBlobService

__all__ = [
    # (same 40-symbol list as current)
]
```

### Deprecation Test Pattern

From [Source: architecture.md, "Migration safety"]:

```python
# tests/unit/adapters/test_adapter_reexports.py
"""Verify backward-compatible re-exports from adapters/__init__.py."""

import pytest

from gepa_adk import adapters

pytestmark = pytest.mark.unit


class TestAdapterReExports:
    """Each old import path resolves to the same object as the new sub-package path."""

    def test_adk_adapter_reexport(self):
        from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter as Direct
        assert adapters.ADKAdapter is Direct

    def test_critic_scorer_reexport(self):
        from gepa_adk.adapters.scoring.critic_scorer import CriticScorer as Direct
        assert adapters.CriticScorer is Direct

    # ... one test per symbol (40 total), or parametrize
```

### Sub-Package `__init__.py` Docstring Requirements

Single-module packages MUST include a docstring explaining purpose and anticipated growth:

```python
# adapters/scoring/__init__.py
"""Scoring infrastructure for evolution evaluation.

Currently contains CriticScorer for LLM-based evaluation.
Anticipated growth: create_critic() factory (Decision 3), preset-based scorer construction.

Attributes:
    CriticScorer: LLM-based scorer using critic agents.
    ...
"""
```

### Project Structure Notes

- This is a **mechanical refactoring** — no logic changes, only file moves + import path updates
- The architecture mandates this structure (Decision 5, ADR-014) as a prerequisite for all feature work
- `stoppers/` is the only existing sub-package and must NOT be modified
- After this story, Pattern 1 (New Adapter Recipe) in the architecture targets `adapters/{concern}/` paths
- The `clone_workflow_with_overrides` function in `workflow.py` is NOT currently exported in `adapters/__init__.py` — do not add it

### Testing Standards

- Use `pytestmark = pytest.mark.unit` at module level for deprecation tests
- Tests must be inside classes (e.g., `TestAdapterReExports`) — no flat functions
- Parametrize the 40-symbol re-export assertions if preferred over 40 individual test methods
- Coverage must not drop — moving files should preserve existing coverage if test imports are updated correctly

### ADR-014 Structure

Follow existing ADR format in `docs/adr/`. Minimum sections:
- **Status**: Accepted
- **Context**: Flat adapter directory with 11 modules causes cognitive overload
- **Decision**: Reorganize into 7 concern-based sub-packages with re-exports
- **Consequences**: Cleaner navigation, clear placement for new adapters, one-time import migration
- **Migration**: Backward-compatible re-exports in `adapters/__init__.py`, enforced by deprecation tests

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5] — Adapter Organization rationale and target structure
- [Source: _bmad-output/planning-artifacts/architecture.md#Adapter Re-Export Template] — Re-export `__init__.py` template
- [Source: _bmad-output/planning-artifacts/architecture.md#Target Directory Tree] — Complete file-level mapping
- [Source: _bmad-output/planning-artifacts/architecture.md#Pattern 1] — New Adapter Implementation Recipe (references new sub-package paths)
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1A, Story 1A.2] — Acceptance criteria
- [Source: _bmad-output/project-context.md] — 95 implementation rules (import boundaries, testing, naming)
- [Source: src/gepa_adk/adapters/__init__.py] — Current 40-symbol export list
- [Source: docs/adr/ADR-000-hexagonal-architecture.md] — Hexagonal architecture foundation
- [Source: docs/adr/ADR-002-protocol-for-interfaces.md] — Protocol-based interfaces

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes List

- All 9 tasks completed successfully
- 7 sub-packages created: execution, scoring, evolution, selection, components, workflow, media
- 11 adapter modules moved via `git mv` preserving git history
- stoppers/ sub-package left completely untouched
- Internal cross-adapter imports updated in adk_adapter.py and multi_agent.py
- adapters/__init__.py re-exports all 33 unique symbols from new sub-package paths
- 35 deprecation tests verify re-export identity (33 parametrized + 2 coverage tests)
- ADR-014 written documenting the reorganization decision
- All pre-commit hooks pass: yamllint, ruff, ty, pytest (1769 passed), docvet (0 findings)
- Fixed pre-existing ty unused type:ignore comments in 5 test files
- Fixed pre-existing yamllint trailing whitespace in mkdocs.yml
- Fixed 51 docvet findings across all staged files (missing examples, cross-references, typed attributes, stale-body, doctest-to-fenced conversion)
- Diagnosed docvet Note: section boundary issue (Note: not in _SECTION_PATTERN) and reordered docstrings accordingly

### File List

**New files (10):**
- `src/gepa_adk/adapters/components/__init__.py`
- `src/gepa_adk/adapters/evolution/__init__.py`
- `src/gepa_adk/adapters/execution/__init__.py`
- `src/gepa_adk/adapters/media/__init__.py`
- `src/gepa_adk/adapters/scoring/__init__.py`
- `src/gepa_adk/adapters/selection/__init__.py`
- `src/gepa_adk/adapters/workflow/__init__.py`
- `tests/unit/adapters/test_adapter_reexports.py`
- `docs/adr/ADR-014-adapter-reorganization.md`
- `_bmad-output/implementation-artifacts/1a-2-reorganize-adapters-into-sub-packages.md`

**Moved files (11):**
- `adapters/agent_executor.py` -> `adapters/execution/agent_executor.py`
- `adapters/trial_builder.py` -> `adapters/execution/trial_builder.py`
- `adapters/critic_scorer.py` -> `adapters/scoring/critic_scorer.py`
- `adapters/adk_adapter.py` -> `adapters/evolution/adk_adapter.py`
- `adapters/multi_agent.py` -> `adapters/evolution/multi_agent.py`
- `adapters/candidate_selector.py` -> `adapters/selection/candidate_selector.py`
- `adapters/component_selector.py` -> `adapters/selection/component_selector.py`
- `adapters/evaluation_policy.py` -> `adapters/selection/evaluation_policy.py`
- `adapters/component_handlers.py` -> `adapters/components/component_handlers.py`
- `adapters/workflow.py` -> `adapters/workflow/workflow.py`
- `adapters/video_blob_service.py` -> `adapters/media/video_blob_service.py`

**Modified source files (9):**
- `src/gepa_adk/__init__.py` (import paths + docstring updates)
- `src/gepa_adk/adapters/__init__.py` (re-exports from new sub-package paths)
- `src/gepa_adk/api.py` (import paths + docstring updates)
- `src/gepa_adk/engine/async_engine.py` (import paths + docstring updates)
- `src/gepa_adk/engine/adk_reflection.py` (docstring import path)
- `src/gepa_adk/engine/proposer.py` (type ignore + docstring updates)
- `src/gepa_adk/ports/agent_executor.py` (docstring cross-reference path fix)
- `src/gepa_adk/ports/component_handler.py` (docstring cross-reference path fixes)
- `mkdocs.yml` (trailing whitespace fix)

**Modified planning artifacts (1):**
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Modified test files (~50):**
- All test files under tests/ that imported from old adapter paths updated to sub-package paths
- String-based patch targets updated in test_adk_adapter.py, test_agent_executor.py, test_unified_execution.py, test_reflection_model_wiring.py, test_encoding_contract.py
- Removed unused type:ignore comments in 4 test files

### Change Log

| Change | Reason |
|--------|--------|
| Created 7 sub-package `__init__.py` files | AC 1, 3, 4 |
| Moved 11 adapter modules via `git mv` | AC 1 |
| Updated internal cross-adapter imports | AC 7 |
| Updated `adapters/__init__.py` re-exports | AC 5 |
| Updated external import sites (api.py, __init__.py, engine) | AC 7 |
| Updated ~50 test file imports | AC 7 |
| Created 35 deprecation tests | AC 6 |
| Created ADR-014 | AC 8 |
| Fixed all pre-commit hook findings | AC 7 |
| Fixed 10 stale docstring cross-references in 4 files | Code review H1 |
| Fixed ADR-014 symbol count (40 -> 33) | Code review M1 |
| Removed dangling section comment in adapters/__init__.py | Code review M2 |
| Updated File List with sprint-status.yaml and ports/ files | Code review L1 |

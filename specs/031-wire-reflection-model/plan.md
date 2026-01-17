# Implementation Plan: Wire Reflection Model Config to Proposer

**Branch**: `031-wire-reflection-model` | **Date**: 2026-01-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/031-wire-reflection-model/spec.md`

## Summary

Wire `EvolutionConfig.reflection_model` through the adapter chain (`ADKAdapter`, `MultiAgentAdapter`) to `AsyncReflectiveMutationProposer` so users can configure which LLM model is used for reflection/mutation operations. This is a configuration passthrough change with no new functionality—the proposer already supports the `model` parameter.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0 (existing - no new deps)
**Storage**: N/A (in-memory configuration passthrough)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Linux/macOS (CLI library)
**Project Type**: Single project (Python library)
**Performance Goals**: N/A (configuration wiring - no runtime performance impact)
**Constraints**: Must maintain backward compatibility with existing API signatures
**Scale/Scope**: 4 files modified, ~20 lines changed

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | PASS | Changes in `adapters/` layer only; domain models unchanged; no new external imports |
| **II. Async-First Design** | PASS | No new I/O; configuration passthrough only |
| **III. Protocol-Based Interfaces** | PASS | No protocol changes; proposer already accepts `model` parameter |
| **IV. Three-Layer Testing** | REQUIRED | Must add unit tests for config flow; contract tests not needed (no protocol changes) |
| **V. Observability** | REQUIRED | Must add INFO-level log when proposer initializes with model (per FR-003) |

**Gate Result**: PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/031-wire-reflection-model/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal - no new entities)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (empty - no new contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── api.py                    # evolve(), evolve_group(), evolve_workflow() - MODIFY
├── adapters/
│   ├── adk_adapter.py        # ADKAdapter.__init__() - MODIFY
│   └── multi_agent.py        # MultiAgentAdapter.__init__() - MODIFY
├── domain/
│   └── models.py             # EvolutionConfig (reflection_model already exists)
├── engine/
│   └── proposer.py           # AsyncReflectiveMutationProposer (model param exists)
└── ports/
    └── (no changes)

tests/
├── unit/
│   └── test_reflection_model_wiring.py  # NEW - config flow verification
└── integration/
    └── (existing tests should pass)
```

**Structure Decision**: Single project structure. Changes are confined to the `adapters/` layer with API surface changes in `api.py`. No new modules or packages required.

## Complexity Tracking

> No Constitution violations detected. No complexity justifications needed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |

## Configuration Flow Design

### Current State (Broken)

```
EvolutionConfig.reflection_model = "gemini-2.0-flash"
    ↓
    NOT PASSED ANYWHERE
    ↓
ADKAdapter / MultiAgentAdapter
    ↓
AsyncReflectiveMutationProposer(model="ollama/gpt-oss:20b")  # HARDCODED
```

### Target State (Wired)

```
EvolutionConfig.reflection_model = "gemini-2.0-flash"  (or user-provided)
    ↓
api.evolve(config=config)
    ↓
ADKAdapter(reflection_model=config.reflection_model)
    ↓
AsyncReflectiveMutationProposer(model=reflection_model)
    ↓
LiteLLM calls use configured model
```

## Files to Modify

| File | Function/Class | Change Description |
|------|----------------|-------------------|
| `src/gepa_adk/api.py` | `evolve()` | Pass `config.reflection_model` to `ADKAdapter` |
| `src/gepa_adk/api.py` | `evolve_group()` | Pass `config.reflection_model` to `MultiAgentAdapter` |
| `src/gepa_adk/adapters/adk_adapter.py` | `ADKAdapter.__init__()` | Add `reflection_model: str` parameter; use when creating proposer |
| `src/gepa_adk/adapters/multi_agent.py` | `MultiAgentAdapter.__init__()` | Add `reflection_model: str` parameter; use when creating proposer |

## Decision: Default Value Alignment

**Issue**: Config default (`"gemini-2.0-flash"`) differs from proposer default (`"ollama/gpt-oss:20b"`)

**Decision**: Keep `EvolutionConfig` default as `"gemini-2.0-flash"` (the documented production-ready model). The proposer's hardcoded default was a development artifact. Once wiring is complete, the config default becomes authoritative.

**Rationale**:
- `gemini-2.0-flash` is a widely available, production-ready model
- Users who want Ollama can explicitly set `reflection_model="ollama_chat/..."`
- This aligns config documentation with runtime behavior

---

## Constitution Check (Post-Design)

*Re-evaluation after Phase 1 design completion.*

| Principle | Status | Verification |
|-----------|--------|--------------|
| **I. Hexagonal Architecture** | PASS | Changes confined to `adapters/` and `api.py`; no domain changes; no new imports |
| **II. Async-First Design** | PASS | No new I/O added; sync configuration passthrough only |
| **III. Protocol-Based Interfaces** | PASS | `ProposerProtocol` unchanged; existing `model` param used |
| **IV. Three-Layer Testing** | PLANNED | Unit tests specified in `tests/unit/test_reflection_model_wiring.py` |
| **V. Observability** | PLANNED | INFO log `proposer_initialized` with `reflection_model` context |

**Post-Design Gate Result**: PASS - Ready for `/speckit.tasks`

## Generated Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| research.md | `specs/031-wire-reflection-model/research.md` | Research findings and decisions |
| data-model.md | `specs/031-wire-reflection-model/data-model.md` | Entity documentation (no new entities) |
| quickstart.md | `specs/031-wire-reflection-model/quickstart.md` | Usage examples |
| contracts/ | `specs/031-wire-reflection-model/contracts/` | N/A - no new API contracts |

## Next Steps

Run `/speckit.tasks` to generate the implementation task list.

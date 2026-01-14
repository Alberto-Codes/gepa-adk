# Implementation Plan: Wire ADK Reflection Agent into evolve() API

**Branch**: `021-adk-reflection-evolve` | **Date**: 2026-01-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/021-adk-reflection-evolve/spec.md`

## Summary

Wire the existing ADK reflection infrastructure into the public `evolve()` API to enable users to pass custom ADK LlmAgent instances for reflection. The infrastructure (`create_adk_reflection_fn()`, `AsyncReflectiveMutationProposer` with `adk_reflection_fn` support) already exists - this feature connects the missing link between the API parameter and the proposer.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0
**Storage**: N/A (in-memory session state via ADK's InMemorySessionService)
**Testing**: pytest with three-layer testing (contract, unit, integration)
**Target Platform**: Python library (cross-platform)
**Project Type**: Single project (Python library)
**Performance Goals**: No performance degradation vs current implementation
**Constraints**: Maintain backward compatibility with existing evolve() calls
**Scale/Scope**: Library feature - minimal code changes (~50 lines across 2-3 files)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | PASS | Changes are in api.py (public API) and adapters/adk_adapter.py (adapter layer). No domain/port layer changes needed. Import rules maintained. |
| **II. Async-First Design** | PASS | `evolve()` is already async. `create_adk_reflection_fn()` returns async callable. No sync/async bridging needed. |
| **III. Protocol-Based Interfaces** | PASS | No new protocols needed. Using existing `ReflectionFn` type alias. |
| **IV. Three-Layer Testing** | PASS | Will add unit tests (mocked reflection agent) and integration tests (real ADK agent). Contract tests already exist for proposer. |
| **V. Observability & Documentation** | PASS | Will use structlog for logging. Google-style docstrings required. Exceptions use existing hierarchy. |

**Gate Result**: All principles satisfied. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/021-adk-reflection-evolve/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (from /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── api.py                    # MODIFY: Pass reflection_agent to adapter
├── adapters/
│   └── adk_adapter.py       # MODIFY: Accept reflection_agent, create adk_reflection_fn
├── engine/
│   └── proposer.py          # NO CHANGE: Already supports adk_reflection_fn
├── domain/                   # NO CHANGE
├── ports/                    # NO CHANGE
└── utils/                    # NO CHANGE

tests/
├── unit/
│   └── test_api.py          # ADD: Tests for reflection_agent parameter
├── integration/
│   └── test_adk_reflection.py  # ADD: Integration tests with real ADK agent
└── contracts/                # NO CHANGE: Existing proposer contracts cover this
```

**Structure Decision**: Single project structure (Python library). Changes touch 2 source files and add 2 test files.

## Complexity Tracking

> No complexity violations. This feature is a simple wiring task connecting existing infrastructure.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

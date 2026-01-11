# Implementation Plan: ADK-First Reflection Agent Support

**Branch**: `010-adk-reflection-agent` | **Date**: 2026-01-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-adk-reflection-agent/spec.md`

## Summary

Enable gepa-adk users to configure ADK agents for reflection in the mutation proposer, providing configurable prompts and full ADK observability. The implementation adds a factory function `create_adk_reflection_fn()` and extends `AsyncReflectiveMutationProposer` with an optional `adk_reflection_fn` parameter, falling back to LiteLLM when not configured.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0
**Storage**: N/A (in-memory session state via ADK's InMemorySessionService)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Linux/Windows server, Python asyncio runtime
**Project Type**: Single library package
**Performance Goals**: Match existing LiteLLM latency (no additional overhead from ADK wrapper)
**Constraints**: Must maintain backwards compatibility with existing proposer API
**Scale/Scope**: Single feature addition to existing engine module

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | PASS | Factory function goes in `engine/proposer.py`, ADK imports only in that module (engine orchestrates, receives adapters via injection) |
| II. Async-First Design | PASS | `create_adk_reflection_fn` returns async callable, `Runner.run_async()` used throughout |
| III. Protocol-Based Interfaces | PASS | Reflection function is a `Callable[[str, list[dict]], Awaitable[str]]` - structural typing, no new Protocol needed |
| IV. Three-Layer Testing | PASS | Will include contract tests (callable signature), unit tests (mock ADK), integration tests (@pytest.mark.slow with real ADK) |
| V. Observability & Documentation | PASS | structlog logging, Google-style docstrings, context binding for reflection operations |

**Gate Result**: PASS - No violations, proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/010-adk-reflection-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── __init__.py
├── adapters/
│   └── adk_adapter.py       # Existing - no changes needed
├── domain/
│   └── trajectory.py        # Existing - no changes needed
├── engine/
│   ├── __init__.py
│   ├── gepa_engine.py       # Existing async engine
│   └── proposer.py          # MODIFY: Add create_adk_reflection_fn, extend AsyncReflectiveMutationProposer
├── ports/
│   ├── adapter.py           # Existing port
│   └── scorer.py            # Existing port
└── utils/

tests/
├── contracts/
│   └── test_reflection_fn_contract.py   # NEW: Callable signature verification
├── integration/
│   └── test_adk_reflection.py           # NEW: Real ADK agent reflection tests
└── unit/
    └── test_proposer.py                 # MODIFY: Add ADK reflection path tests
```

**Structure Decision**: Single project structure following existing hexagonal layout. The reflection factory function lives in `engine/proposer.py` since it orchestrates ADK components and is part of the proposer's responsibility.

## Complexity Tracking

> No violations - this section is not needed.

## Post-Design Constitution Re-Check

*Verified after Phase 1 design artifacts generated.*

| Principle | Status | Verification |
|-----------|--------|--------------|
| I. Hexagonal Architecture | PASS | Factory in `engine/`, ADK imports isolated there, no ports layer changes |
| II. Async-First Design | PASS | All new code is async (`async def reflect`, `Runner.run_async`) |
| III. Protocol-Based Interfaces | PASS | `ReflectionFn` type alias uses structural typing via `Callable` |
| IV. Three-Layer Testing | PASS | Contract, unit, and integration test files defined in structure |
| V. Observability & Documentation | PASS | Google-style docstrings in contracts, quickstart examples included |

**Final Gate Result**: PASS - Ready for Phase 2 task generation.

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Research | `specs/010-adk-reflection-agent/research.md` | Complete |
| Data Model | `specs/010-adk-reflection-agent/data-model.md` | Complete |
| Contracts | `specs/010-adk-reflection-agent/contracts/` | Complete |
| Quickstart | `specs/010-adk-reflection-agent/quickstart.md` | Complete |
| Tasks | `specs/010-adk-reflection-agent/tasks.md` | Pending (`/speckit.tasks`) |

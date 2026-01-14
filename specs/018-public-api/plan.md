# Implementation Plan: Public API (evolve, evolve_sync)

**Branch**: `018-public-api` | **Date**: 2026-01-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/018-public-api/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement the primary user-facing API functions `evolve()` and `evolve_sync()` that allow single-agent ADK instruction evolution with progressive configuration disclosure. The async `evolve()` function is the core entry point, while `evolve_sync()` provides a sync wrapper for scripts/notebooks. These functions complement the existing `evolve_group()` and `evolve_workflow()` functions already in `api.py`.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: google-adk, structlog, asyncio (stdlib)  
**Storage**: N/A  
**Testing**: pytest with three-layer strategy (contract, unit, integration)  
**Target Platform**: Linux/macOS/Windows (Python runtime)  
**Project Type**: Single project (hexagonal architecture)  
**Performance Goals**: N/A (evolution runs depend on LLM API latency)  
**Constraints**: Async-first design, sync wrapper must handle nested event loops  
**Scale/Scope**: Single-agent evolution API

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | ✅ PASS | `api.py` orchestrates through ports; no external imports in domain/ports |
| II. Async-First Design | ✅ PASS | `evolve()` is async; `evolve_sync()` is top-level wrapper only |
| III. Protocol-Based Interfaces | ✅ PASS | Uses existing `AsyncGEPAAdapter` protocol |
| IV. Three-Layer Testing | ✅ REQUIRED | Must add contract, unit, and integration tests |
| V. Observability & Documentation | ✅ REQUIRED | Must add structlog events, Google docstrings |

**ADRs Referenced**:
- ADR-000: Hexagonal Architecture (layer rules)
- ADR-001: Async-First Architecture (sync wrapper at top-level only)
- ADR-002: Protocol for Interfaces (existing adapter protocol)
- ADR-005: Three-Layer Testing (test requirements)

## Project Structure

### Documentation (this feature)

```text
specs/018-public-api/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── __init__.py          # MODIFY: Export evolve, evolve_sync
├── api.py               # MODIFY: Add evolve(), evolve_sync()
├── adapters/
│   ├── adk_adapter.py   # EXISTING: ADKAdapter for single-agent
│   └── critic_scorer.py # EXISTING: CriticScorer
├── domain/
│   ├── models.py        # EXISTING: EvolutionConfig, EvolutionResult
│   └── types.py         # EXISTING: TrajectoryConfig
├── engine/
│   └── async_engine.py  # EXISTING: AsyncGEPAEngine
├── ports/
│   ├── adapter.py       # EXISTING: AsyncGEPAAdapter protocol
│   └── scorer.py        # EXISTING: Scorer protocol
└── utils/
    └── state_guard.py   # MAY EXIST: StateGuard utility

tests/
├── contracts/
│   └── test_api_contract.py    # NEW: API contract tests
├── unit/
│   └── test_api.py             # NEW: Unit tests with mocks
└── integration/
    └── test_api_integration.py # NEW: Real ADK integration tests
```

**Structure Decision**: Single project following existing hexagonal architecture. No new directories needed; new functions added to existing `api.py` module.

## Complexity Tracking

> No Constitution violations - all constraints satisfied within existing architecture.

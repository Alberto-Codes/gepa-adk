# Implementation Plan: AsyncGEPAEngine

**Branch**: `006-async-gepa-engine` | **Date**: 2026-01-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-async-gepa-engine/spec.md`

## Summary

Implement an async-first evolution engine (`AsyncGEPAEngine`) that orchestrates the core evolution loop for gepa-adk. The engine iterates until max_iterations or convergence, accepts improved candidates based on configurable thresholds, and supports early stopping via patience. Inspired by GEPA's `GEPAEngine` patterns but reimplemented as async-native for ADK integration.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: None (stdlib only for engine layer per ADR-000)
**Storage**: N/A (in-memory state during run; no persistence in v1)
**Testing**: pytest with async support (pytest-asyncio)
**Target Platform**: Linux/macOS/Windows (cross-platform Python)
**Project Type**: Single package (library)
**Performance Goals**: Async-native for concurrent evaluation (3-5x speedup via semaphore)
**Constraints**: Engine layer cannot import adapters directly (dependency injection per hexagonal architecture)
**Scale/Scope**: Single evolution runs; no multi-run orchestration in v1

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Hexagonal Architecture (Ports & Adapters)

| Requirement | Status | Notes |
|-------------|--------|-------|
| Engine in `engine/` layer | ✅ PASS | `src/gepa_adk/engine/async_engine.py` |
| Imports only from `ports/`, `domain/` | ✅ PASS | Uses `AsyncGEPAAdapter` protocol, domain models |
| Receives adapters via injection | ✅ PASS | Adapter passed to constructor, not imported |
| No external libs in engine | ✅ PASS | Only stdlib (asyncio) |

### II. Async-First Design

| Requirement | Status | Notes |
|-------------|--------|-------|
| Core APIs are async | ✅ PASS | `async def run()` main entry point |
| No internal sync/async bridging | ✅ PASS | Async all the way down |
| Protocol methods are coroutines | ✅ PASS | `AsyncGEPAAdapter` methods are async |

### III. Protocol-Based Interfaces

| Requirement | Status | Notes |
|-------------|--------|-------|
| Uses `typing.Protocol` | ✅ PASS | `AsyncGEPAAdapter` is a Protocol |
| `@runtime_checkable` where needed | ✅ PASS | Already defined in ports/adapter.py |
| No ABC inheritance | ✅ PASS | Pure Protocol |

### IV. Three-Layer Testing

| Requirement | Status | Notes |
|-------------|--------|-------|
| Contract tests in `tests/contracts/` | ✅ PLANNED | Engine interaction with mock adapter |
| Unit tests in `tests/unit/` | ✅ PLANNED | Core loop logic, convergence, acceptance |
| Integration tests marked `@pytest.mark.slow` | ✅ PLANNED | Real ADK adapter tests (future) |
| Tests written before implementation | ✅ REQUIRED | TDD approach |

### V. Observability & Documentation Standards

| Requirement | Status | Notes |
|-------------|--------|-------|
| Google-style docstrings | ✅ REQUIRED | All public methods documented |
| 95%+ coverage (interrogate) | ✅ REQUIRED | |
| Exceptions inherit from `EvolutionError` | ✅ PASS | Will use existing hierarchy |

**Gate Status**: ✅ PASS - No violations. Ready for Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/006-async-gepa-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   ├── __init__.py
│   ├── models.py         # EvolutionConfig, EvolutionResult, IterationRecord, Candidate (existing)
│   ├── exceptions.py     # EvolutionError, ConfigurationError (existing)
│   └── types.py          # Score, ComponentName, ModelName (existing)
├── ports/
│   ├── __init__.py
│   └── adapter.py        # AsyncGEPAAdapter, EvaluationBatch (existing)
├── engine/               # NEW - This feature
│   ├── __init__.py
│   └── async_engine.py   # AsyncGEPAEngine class
└── __init__.py

tests/
├── contracts/
│   └── test_async_engine_contracts.py  # Protocol compliance
├── unit/
│   └── engine/
│       └── test_async_engine.py        # Core logic tests
└── integration/
    └── engine/
        └── test_async_engine_integration.py  # Future: real adapter
```

**Structure Decision**: Single project structure. Engine layer added under `src/gepa_adk/engine/` following hexagonal architecture. Tests organized by layer (contracts, unit, integration).

## Complexity Tracking

> No violations to justify. Design follows constitution principles.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | — | — |

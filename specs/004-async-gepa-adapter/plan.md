# Implementation Plan: AsyncGEPAAdapter Protocol

**Branch**: `004-async-gepa-adapter` | **Date**: 2026-01-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-async-gepa-adapter/spec.md`

## Summary

Define the `AsyncGEPAAdapter` protocol - an async-first adaptation of GEPA's `GEPAAdapter` protocol for integration with Google ADK. The protocol specifies three async methods (`evaluate`, `make_reflective_dataset`, `propose_new_texts`) that adapters must implement. Uses `typing.Protocol` with `@runtime_checkable` decorator for structural subtyping with runtime verification support.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: None (stdlib only for ports layer per ADR-000)
**Storage**: N/A
**Testing**: pytest with pytest-asyncio
**Target Platform**: Linux/macOS/Windows (library)
**Project Type**: Single library project
**Performance Goals**: Protocol isinstance() checks should be minimized; prefer static type checking
**Constraints**: No external imports in ports layer; async-first design
**Scale/Scope**: Single protocol definition with 3 methods, plus supporting EvaluationBatch dataclass

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Hexagonal Architecture | ✅ PASS | Protocol goes in `ports/` layer with no external imports |
| II. Async-First Design | ✅ PASS | All 3 protocol methods are async coroutines |
| III. Protocol-Based Interfaces | ✅ PASS | Uses `typing.Protocol` with `@runtime_checkable` per ADR-002 |
| IV. Three-Layer Testing | ✅ PASS | Will include contract tests in `tests/contracts/` |
| V. Observability & Documentation | ✅ PASS | Google-style docstrings, exception hierarchy used |

**ADR Alignment**:
- ADR-000: Protocol in ports/, no external deps ✅
- ADR-001: Async methods throughout ✅
- ADR-002: Protocol-based, @runtime_checkable ✅
- ADR-005: Contract tests planned ✅

## Project Structure

### Documentation (this feature)

```text
specs/004-async-gepa-adapter/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (not created by /speckit.plan)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/              # Existing: models.py, types.py, exceptions.py
│   ├── __init__.py
│   ├── models.py        # Candidate, EvolutionConfig (already implemented)
│   ├── types.py         # Score, ComponentName, ModelName
│   └── exceptions.py    # EvolutionError hierarchy
├── ports/               # NEW: Protocol definitions
│   ├── __init__.py
│   └── adapter.py       # AsyncGEPAAdapter protocol + EvaluationBatch
└── __init__.py

tests/
├── contracts/           # NEW: Protocol compliance tests
│   ├── __init__.py
│   └── test_adapter_protocol.py
├── unit/
└── integration/
```

**Structure Decision**: Follows existing hexagonal structure. New `ports/` directory for protocol definitions, new `tests/contracts/` for protocol compliance tests.

## Complexity Tracking

No constitution violations to justify.

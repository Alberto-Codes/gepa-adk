# Implementation Plan: StateGuard for State Key Preservation

**Branch**: `013-state-guard` | **Date**: January 11, 2026 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/013-state-guard/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

StateGuard is a validation utility that ensures ADK state injection tokens are preserved during instruction evolution. It detects missing required tokens and re-appends them, while escaping any unauthorized new tokens introduced by reflection. This prevents runtime failures when evolved instructions break the `{token}` placeholder format that ADK uses for state injection.

**Technical Approach**: Pure Python utility class using regex pattern matching to identify tokens. No external dependencies required. Placed in `utils/` layer per hexagonal architecture.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: None (stdlib `re` module only)  
**Storage**: N/A (stateless validation)  
**Testing**: pytest with unit tests (no I/O, no async = unit-only)  
**Target Platform**: Linux server (cross-platform compatible)  
**Project Type**: Single project (existing gepa-adk structure)  
**Performance Goals**: <1ms validation for instructions up to 10KB  
**Constraints**: Pure Python, no external imports per utils/ layer rules  
**Scale/Scope**: Single-file utility, ~50-100 LOC

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Hexagonal Architecture ✅

| Criterion | Status | Notes |
|-----------|--------|-------|
| Layer placement | ✅ PASS | `utils/` layer - shared utilities with minimal deps |
| Import rules | ✅ PASS | Only stdlib `re` module - compliant with utils/ rules |
| No external deps | ✅ PASS | No ADK, LiteLLM, or other external imports |

### II. Async-First Design ✅

| Criterion | Status | Notes |
|-----------|--------|-------|
| I/O operations | ✅ N/A | No I/O - pure string manipulation |
| Async methods | ✅ N/A | Sync-only is appropriate for CPU-bound string ops |

### III. Protocol-Based Interfaces ✅

| Criterion | Status | Notes |
|-----------|--------|-------|
| Port definition | ✅ N/A | No port needed - utility function, not integration point |
| Protocol usage | ✅ N/A | Direct class usage, no polymorphism required |

### IV. Three-Layer Testing ✅

| Criterion | Status | Notes |
|-----------|--------|-------|
| Contract tests | ✅ N/A | No protocol = no contract tests needed |
| Unit tests | ✅ REQUIRED | Pure functions → unit tests only |
| Integration tests | ✅ N/A | No external dependencies to integrate |
| TDD approach | ✅ REQUIRED | Tests must be written before implementation |

### V. Observability & Documentation ✅

| Criterion | Status | Notes |
|-----------|--------|-------|
| Structured logging | ⚪ OPTIONAL | May add debug logging for repairs |
| Docstrings | ✅ REQUIRED | Google-style, 95%+ coverage |
| Exception handling | ✅ N/A | No exceptions expected - graceful validation |

**Gate Status**: ✅ PASS - No violations, proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/013-state-guard/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── utils/
│   ├── __init__.py      # Export StateGuard
│   ├── events.py        # Existing trajectory utilities
│   └── state_guard.py   # NEW: StateGuard class

tests/
├── unit/
│   └── utils/
│       ├── test_events.py      # Existing
│       └── test_state_guard.py # NEW: Unit tests for StateGuard
```

**Structure Decision**: Single project structure (existing). StateGuard is placed in `utils/` layer alongside existing utility modules like `events.py`. No new packages or layers required.

## Complexity Tracking

> No violations to justify - feature is simple and aligns with all constitution principles.

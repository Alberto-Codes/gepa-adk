# Implementation Plan: API StateGuard Validation

**Branch**: `020-api-stateguard-validation` | **Date**: January 13, 2026 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/020-api-stateguard-validation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Wire the existing `StateGuard` utility into the public API `evolve()`, `evolve_sync()`, `evolve_group()`, and `evolve_workflow()` functions to validate and repair state injection tokens in evolved instructions. The `state_guard` parameter already exists in function signatures with a TODO placeholder - this feature implements the actual validation logic.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: google-adk, structlog (existing), gepa_adk.utils.StateGuard (existing)  
**Storage**: N/A  
**Testing**: pytest with three-layer strategy (contract/unit/integration)  
**Target Platform**: Python async runtime  
**Project Type**: Single package  
**Performance Goals**: Sub-millisecond overhead (StateGuard operates on final instruction strings only)  
**Constraints**: Must not break existing API behavior when state_guard=None (backward compatible)  
**Scale/Scope**: ~50 lines of new code, wiring existing StateGuard into 4 API functions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | ✅ PASS | StateGuard is in `utils/` layer (allowed). API is top-level public surface. No layer violations. |
| II. Async-First Design | ✅ PASS | StateGuard.validate() is synchronous but operates only on final strings (no I/O). Called after async evolution completes. |
| III. Protocol-Based Interfaces | ✅ N/A | No new protocols needed - using existing StateGuard class |
| IV. Three-Layer Testing | ✅ REQUIRED | Must add unit tests for StateGuard integration in API |
| V. Observability & Documentation | ✅ REQUIRED | Must add structured logging when StateGuard validation is applied |

**Gate Result**: ✅ PASS - No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/020-api-stateguard-validation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── api.py               # MODIFY: evolve(), evolve_sync(), evolve_group(), evolve_workflow()
├── utils/
│   └── state_guard.py   # EXISTING: StateGuard class (no changes needed)
└── domain/
    └── models.py        # EXISTING: EvolutionResult (no changes needed)

tests/
├── unit/
│   └── test_api_state_guard.py  # NEW: Unit tests for StateGuard integration
└── integration/
    └── test_api_state_guard_integration.py  # NEW: Integration tests (optional)
```

**Structure Decision**: Single package structure. Modifications are limited to `api.py` for wiring and new test files. No architectural changes needed.

## Complexity Tracking

> No violations - section not applicable.

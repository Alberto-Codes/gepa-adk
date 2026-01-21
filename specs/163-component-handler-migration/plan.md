# Implementation Plan: Component Handler Migration

**Branch**: `163-component-handler-migration` | **Date**: 2026-01-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/163-component-handler-migration/spec.md`

## Summary

Migrate ADKAdapter's `_apply_candidate()` and `_restore_agent()` methods from hardcoded if/elif component handling to registry-based dispatch using the ComponentHandler pattern established in #162. The handlers (InstructionHandler, OutputSchemaHandler) and registry already exist—this feature rewires the adapter to use them.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0, structlog >= 25.5.0 (existing - no new deps)
**Storage**: N/A (in-memory component handling)
**Testing**: pytest with three-layer strategy (unit/contract/integration)
**Target Platform**: Linux/macOS/Windows (cross-platform library)
**Project Type**: Single Python package (hexagonal architecture)
**Performance Goals**: No performance regression in evaluation throughput
**Constraints**: Backward compatibility with existing evolution workflows
**Scale/Scope**: Single adapter class refactor (~50 lines of code changes)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicable | Status | Notes |
|-----------|------------|--------|-------|
| I. Hexagonal Architecture | ✅ Yes | ✅ Compliant | Handler protocol in `ports/`, implementations in `adapters/` |
| II. Async-First Design | ⬜ N/A | — | Handler methods are sync (no I/O) |
| III. Protocol-Based Interfaces | ✅ Yes | ✅ Compliant | Uses existing ComponentHandler protocol |
| IV. Three-Layer Testing | ✅ Yes | ✅ Required | Unit + contract + integration tests |
| V. Observability & Code Documentation | ✅ Yes | ✅ Required | structlog logging, Google-style docstrings |
| VI. Documentation Synchronization | ⬜ N/A | — | Internal refactor, no user-facing API changes |

**ADRs Referenced**:
- ADR-000 (Hexagonal): Layer boundaries preserved
- ADR-002 (Protocols): ComponentHandler protocol already defined
- ADR-005 (Testing): Three layers required

**Gate Passed**: ✅ No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/163-component-handler-migration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── architecture.md      # Phase 2 output (conditional)
└── tasks.md             # Phase 3 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/              # No changes
├── ports/
│   └── component_handler.py  # Existing (from #162)
├── adapters/
│   ├── adk_adapter.py        # MODIFY: Use registry dispatch
│   └── component_handlers.py # Existing (from #162) - handlers already registered
├── engine/              # No changes
└── utils/               # No changes

tests/
├── unit/
│   └── adapters/
│       ├── test_adk_adapter.py          # MODIFY: Add registry dispatch tests
│       └── test_component_handlers.py   # Existing (from #162)
├── contracts/
│   └── test_adk_adapter_contracts.py    # Existing (verify unchanged)
└── integration/
    └── adapters/
        └── test_adk_adapter_integration.py  # Existing (verify unchanged)
```

**Structure Decision**: Single package, modifying `adapters/adk_adapter.py` to use existing `adapters/component_handlers.py` infrastructure.

## Complexity Tracking

> No violations requiring justification. This is a straightforward refactor.

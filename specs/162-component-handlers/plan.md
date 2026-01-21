# Implementation Plan: ComponentHandler Protocol and Registry

**Branch**: `162-component-handlers` | **Date**: 2026-01-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/162-component-handlers/spec.md`

## Summary

Create a ComponentHandler protocol that abstracts component serialization/application, replacing hardcoded if/elif branches in `ADKAdapter._apply_candidate()` with a registry-based handler pattern. This enables adding new component types without modifying core adapter code, following the Open/Closed principle and aligning with existing patterns like ComponentSelectorProtocol.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0, structlog >= 25.5.0 (existing - no new deps)
**Storage**: N/A (in-memory registry)
**Testing**: pytest with three-layer strategy (contracts/, unit/, integration/)
**Target Platform**: Linux/macOS/Windows (Python runtime)
**Project Type**: Single project with hexagonal architecture
**Performance Goals**: O(1) handler lookup via dict-based registry
**Constraints**: Must maintain backward compatibility with existing component handling
**Scale/Scope**: Initially 2 handlers (instruction, output_schema), extensible to N

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies | Status | Notes |
|-----------|---------|--------|-------|
| I. Hexagonal Architecture | YES | PASS | Protocol in ports/, implementations in adapters/ |
| II. Async-First Design | NO | N/A | No I/O operations; handlers are sync component manipulation |
| III. Protocol-Based Interfaces | YES | PASS | ComponentHandler uses `typing.Protocol` with `@runtime_checkable` |
| IV. Three-Layer Testing | YES | PASS | Contract, unit, integration tests planned |
| V. Observability & Documentation | YES | PASS | Google-style docstrings, structlog for errors |
| VI. Documentation Synchronization | NO | N/A | Internal refactor, no user-facing API changes |

**ADRs Referenced**:
- ADR-000: Hexagonal Architecture (port/adapter separation)
- ADR-002: Protocol for Interfaces (runtime_checkable protocol pattern)
- ADR-005: Three-Layer Testing (test structure)

**Gate Result**: PASS - No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/162-component-handlers/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── architecture.md      # Phase 2 output (conditional)
└── tasks.md             # Phase 3 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── ports/
│   ├── component_handler.py     # NEW: ComponentHandler protocol
│   └── __init__.py              # UPDATE: export protocol
├── adapters/
│   ├── component_handlers.py    # NEW: Registry + handler implementations
│   └── __init__.py              # UPDATE: export handlers/registry
└── domain/
    └── types.py                 # EXISTING: component name constants

tests/
├── contracts/
│   └── test_component_handler_protocol.py    # NEW: Protocol compliance
├── unit/
│   ├── ports/
│   │   └── test_component_handler.py         # NEW: Protocol unit tests
│   └── adapters/
│       └── test_component_handlers.py        # NEW: Registry/handler tests
└── integration/
    └── test_component_handler_integration.py # NEW: End-to-end tests
```

**Structure Decision**: Single project following existing hexagonal architecture. Protocol goes in ports/ (no external deps), implementations in adapters/ (may use google.adk types for LlmAgent).

## Complexity Tracking

> No violations to justify. Design follows established patterns.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

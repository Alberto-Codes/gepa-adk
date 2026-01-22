# Implementation Plan: Required Field Preservation for Output Schema Evolution

**Branch**: `198-schema-field-preservation` | **Date**: 2026-01-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/198-schema-field-preservation/spec.md`

## Summary

Add constraint-based validation to output schema evolution that preserves required fields and their types. When the reflection agent proposes a schema mutation, the `OutputSchemaHandler` validates the mutation against user-specified constraints before applying it. Invalid mutations are rejected with a warning, preserving the original schema.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0, pydantic >= 2.0, structlog >= 25.5.0
**Storage**: N/A (in-memory validation during evolution)
**Testing**: pytest + pytest-asyncio (contract, unit, integration layers)
**Target Platform**: Linux/macOS/Windows (cross-platform library)
**Project Type**: single (Python library)
**Performance Goals**: Validation adds < 1ms per mutation (negligible overhead)
**Constraints**: Must be backward compatible (no constraints = current behavior)
**Scale/Scope**: Supports any Pydantic schema size; constraints dictionary scales O(n) with fields

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies | Status | Notes |
|-----------|---------|--------|-------|
| I. Hexagonal Architecture | Yes | PASS | `SchemaConstraints` goes in domain/, validation logic in adapters/ |
| II. Async-First Design | No | N/A | Schema validation is synchronous (no I/O) |
| III. Protocol-Based Interfaces | Yes | PASS | Existing `ComponentHandler` protocol unchanged; validation is internal |
| IV. Three-Layer Testing | Yes | PASS | Contract tests for validation protocol, unit for logic, integration for end-to-end |
| V. Observability & Documentation | Yes | PASS | Structured logging for rejected mutations; docstrings required |
| VI. Documentation Synchronization | Yes | PASS | Update guides/single-agent.md and examples |

**Gate Decision**: PASS - No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/198-schema-field-preservation/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── architecture.md      # Phase 2 output (if needed)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   └── types.py                    # Add SchemaConstraints dataclass
├── adapters/
│   └── component_handlers.py       # Add validation to OutputSchemaHandler.apply()
├── utils/
│   └── schema_utils.py             # Add validate_schema_against_constraints() helper
└── api.py                          # Add schema_constraints parameter to evolve()

tests/
├── contracts/
│   └── test_schema_constraints_contract.py    # Protocol compliance
├── unit/
│   ├── domain/
│   │   └── test_schema_constraints.py         # SchemaConstraints dataclass
│   ├── utils/
│   │   └── test_schema_constraint_validation.py  # Validation logic
│   └── adapters/
│       └── test_output_schema_handler_constraints.py  # Handler integration
└── integration/
    └── test_schema_constrained_evolution.py   # End-to-end with real ADK
```

**Structure Decision**: Single Python library with hexagonal architecture. Domain model (`SchemaConstraints`) in domain/, validation logic in adapters/, helper utilities in utils/.

## Complexity Tracking

> No violations to justify. Design follows existing patterns.

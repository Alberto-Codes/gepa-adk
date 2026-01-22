# Implementation Plan: Optional Stoppers (MaxEvaluations and File-based)

**Branch**: `197-optional-stoppers` | **Date**: 2026-01-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/197-optional-stoppers/spec.md`

## Summary

Implement two additional stopper types for the gepa-adk evolution framework:
1. **MaxEvaluationsStopper**: Stops evolution after a configurable number of total evaluations, enabling API cost control
2. **FileStopper**: Stops evolution when a specified file exists, enabling external orchestration integration

Both stoppers conform to the existing `StopperProtocol` and integrate seamlessly with the `CompositeStopper` for combining stop conditions.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: structlog>=25.5.0 (existing - no new deps), pathlib (stdlib)
**Storage**: N/A (in-memory stopper state)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Linux/macOS/Windows (cross-platform)
**Project Type**: Single library (src/gepa_adk)
**Performance Goals**: Stopper checks must complete in <1ms per iteration
**Constraints**: Zero external dependencies beyond structlog; stdlib only for file operations
**Scale/Scope**: Simple adapter implementations (~40 lines each + ~60 lines tests each)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies | Compliant | Notes |
|-----------|---------|-----------|-------|
| I. Hexagonal Architecture | Yes | ✅ | Stoppers in `adapters/stoppers/`, use domain `StopperState`, conform to `StopperProtocol` port |
| II. Async-First Design | No | N/A | Stoppers are synchronous by design (protocol is sync `__call__`) |
| III. Protocol-Based Interfaces | Yes | ✅ | Both implement `StopperProtocol` via duck typing |
| IV. Three-Layer Testing | Yes | ✅ | Contract tests for protocol compliance, unit tests for logic, integration with engine |
| V. Observability & Code Documentation | Yes | ✅ | Google-style docstrings, structlog for logging |
| VI. Documentation Synchronization | Yes | ⚠️ | Optional stoppers - guides may need update if user-facing |

**ADRs Referenced**:
- ADR-000: Hexagonal Architecture - adapters layer for external integrations
- ADR-002: Protocol for Interfaces - StopperProtocol compliance
- ADR-005: Three-Layer Testing - test strategy
- ADR-008: Structured Logging - structlog usage

**Documentation Scope Assessment**:
| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| New public API (stoppers) | Recommended (guides) | Recommended |

These are "nice-to-have" convenience stoppers (priority: low), so documentation is recommended but not strictly required. The existing stopper documentation should be sufficient for users to understand the pattern.

## Project Structure

### Documentation (this feature)

```text
specs/197-optional-stoppers/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 3 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   └── stopper.py              # StopperState (existing - no changes)
├── ports/
│   └── stopper.py              # StopperProtocol (existing - no changes)
└── adapters/
    └── stoppers/
        ├── __init__.py         # Export new stoppers (modify)
        ├── evaluations.py      # NEW: MaxEvaluationsStopper
        └── file.py             # NEW: FileStopper

tests/
├── contracts/
│   └── test_stopper_protocol.py    # Add contract tests for new stoppers
└── unit/
    └── adapters/
        └── stoppers/
            ├── test_evaluations.py  # NEW: MaxEvaluationsStopper tests
            └── test_file.py         # NEW: FileStopper tests
```

**Structure Decision**: Single project structure following existing stopper adapter pattern. New stoppers go in `adapters/stoppers/` alongside existing `timeout.py`, `threshold.py`, `signal.py`, and `composite.py`.

## Complexity Tracking

No constitution violations detected. Implementation follows established patterns:
- Simple adapter classes (~20-30 lines each)
- No new dependencies
- No architectural changes

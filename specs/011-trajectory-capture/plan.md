# Implementation Plan: Trajectory Capture from ADK Sessions

**Branch**: `011-trajectory-capture` | **Date**: 2026-01-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-trajectory-capture/spec.md`

## Summary

Implement configurable trajectory capture from ADK sessions with support for tool calls, state deltas, token usage, and sensitive data redaction. The technical approach uses a `TrajectoryConfig` dataclass in the domain layer and an `extract_trajectory` utility function, integrating with the existing `ADKTrajectory` model and `ADKAdapter`.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: google-adk (1.22.0), pydantic (2.12.5), structlog (25.5.0)  
**Storage**: N/A (in-memory trajectory extraction)  
**Testing**: pytest with pytest-asyncio, pytest-mock  
**Target Platform**: Linux server (cross-platform Python)  
**Project Type**: Single project (hexagonal architecture)  
**Performance Goals**: Trajectory extraction < 10ms for typical event streams  
**Constraints**: No mutations to original ADK events; immutable trajectory output  
**Scale/Scope**: Handles batches of up to 1000 evaluation examples

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | ✅ PASS | `TrajectoryConfig` in domain/, `extract_trajectory` in utils/, no external deps in domain |
| **II. Async-First Design** | ✅ PASS | Extraction is CPU-bound (no I/O), sync is appropriate; async ADKAdapter integration remains |
| **III. Protocol-Based Interfaces** | ✅ PASS | No new protocols needed; uses existing domain models |
| **IV. Three-Layer Testing** | ✅ PASS | Unit tests for utils, integration tests for ADKAdapter flow |
| **V. Observability & Documentation** | ✅ PASS | Google-style docstrings, structlog for debug logging |

**ADR Alignment**:
- ADR-000: Domain types remain pure (no external imports)
- ADR-005: Tests across unit/ and integration/ layers
- ADR-010: All public functions require docstrings with examples

## Project Structure

### Documentation (this feature)

```text
specs/011-trajectory-capture/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - no new protocols)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   ├── types.py         # ADD: TrajectoryConfig dataclass
│   └── trajectory.py    # EXISTING: ADKTrajectory, ToolCallRecord, TokenUsage
├── utils/               # NEW DIRECTORY
│   ├── __init__.py
│   └── events.py        # ADD: extract_trajectory, _redact_sensitive
├── adapters/
│   └── adk_adapter.py   # MODIFY: Add trajectory_config parameter
└── __init__.py          # MODIFY: Export new types

tests/
├── unit/
│   ├── domain/
│   │   └── test_types.py    # ADD: TrajectoryConfig tests
│   └── utils/               # NEW DIRECTORY
│       ├── __init__.py
│       └── test_events.py   # ADD: extraction & redaction tests
└── integration/
    └── test_trajectory_capture.py  # ADD: end-to-end tests
```

**Structure Decision**: Single project structure with hexagonal layers. New `utils/` module for extraction utilities (infrastructure concern, not domain logic).

## Complexity Tracking

> No Constitution violations. Feature uses existing patterns.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | — | — |

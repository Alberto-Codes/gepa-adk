# Implementation Plan: Shared ADK Event Output Extraction Utility

**Branch**: `033-event-output-extraction` | **Date**: 2026-01-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/033-event-output-extraction/spec.md`

## Summary

Extract duplicated ADK event output extraction logic from 4 adapter locations into a shared `extract_final_output` utility in `gepa_adk.utils.events`. The utility fixes the critical bug of missing `part.thought` filtering that causes parse failures with models emitting reasoning content (72 observed parse errors, 0.0 scores). This refactoring eliminates ~80 lines of duplicated code and provides a single maintenance point for ADK event structure changes.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, structlog>=25.5.0 (existing - no new deps)
**Storage**: N/A (in-memory event processing)
**Testing**: pytest with contract/unit/integration layers
**Target Platform**: Linux/macOS/Windows (Python interpreter)
**Project Type**: Single project (library)
**Performance Goals**: No measurable latency impact (current inline extraction is already sub-millisecond)
**Constraints**: Must maintain backward compatibility with existing adapter behavior
**Scale/Scope**: 4 adapter locations, 1 utility function, ~80 lines of duplicated code to consolidate

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Status | Notes |
|-----------|----------|--------|-------|
| I. Hexagonal Architecture | Yes | PASS | Utility goes in `utils/` layer; no external imports needed (uses stdlib only) |
| II. Async-First Design | No | N/A | Function is synchronous (processes in-memory event list, no I/O) |
| III. Protocol-Based Interfaces | No | N/A | This is a utility function, not a port interface |
| IV. Three-Layer Testing | Yes | PASS | Will add contract tests for function behavior, unit tests with mock events, integration tests via existing adapter tests |
| V. Observability & Code Documentation | Yes | PASS | Will include Google-style docstrings with Args, Returns, Examples sections |
| VI. Documentation Synchronization | Partial | PASS | Bug fix + internal refactor - no user-facing API changes. No docs/guides updates required per Constitution scope table. |

**ADRs Referenced**:
- ADR-000: Hexagonal Architecture - `utils/` layer is appropriate for shared utilities
- ADR-005: Three-Layer Testing - Tests required at all three layers

## Project Structure

### Documentation (this feature)

```text
specs/033-event-output-extraction/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── architecture.md      # Phase 2 output (SKIPPED - see reasoning below)
└── tasks.md             # Phase 3 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── utils/
│   └── events.py        # Add extract_final_output function here
├── adapters/
│   ├── adk_adapter.py   # Refactor _run_single_example to use shared utility
│   ├── multi_agent.py   # Refactor _run_shared_session and _run_isolated_sessions
│   └── critic_scorer.py # Refactor async_score to use shared utility

tests/
├── contracts/
│   └── test_extract_final_output_contract.py  # Protocol compliance tests
├── unit/
│   └── utils/
│       └── test_events.py  # Add unit tests for extract_final_output
└── integration/
    └── test_trajectory_capture.py  # Verify adapters still work (existing tests)
```

**Structure Decision**: Single project structure. The utility function is added to existing `utils/events.py` alongside `extract_trajectory`. Test files extend existing test modules.

## Complexity Tracking

No violations. This is a straightforward refactoring that consolidates existing code without introducing new patterns or architectural complexity.

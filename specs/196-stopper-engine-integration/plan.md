# Implementation Plan: Wire stop_callbacks into AsyncGEPAEngine

**Branch**: `196-stopper-engine-integration` | **Date**: 2026-01-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/196-stopper-engine-integration/spec.md`
**Parent Issue**: #51 - Pluggable stop conditions

## Summary

Integrate the existing stopper callback system into AsyncGEPAEngine. The engine must track additional state (elapsed_seconds, total_evaluations), build StopperState snapshots, check stop_callbacks in `_should_stop()`, and handle SignalStopper lifecycle (setup/cleanup). All stopper implementations (TimeoutStopper, ScoreThresholdStopper, SignalStopper, CompositeStopper) are already complete - this is the final wiring step.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0, structlog >= 25.5.0 (existing - no new deps)
**Storage**: N/A (in-memory evolution state)
**Testing**: pytest with three-layer strategy (unit, contracts, integration)
**Target Platform**: Linux/macOS/Windows (Python-based CLI/library)
**Project Type**: Single project with hexagonal architecture
**Performance Goals**: Stoppers must execute in sub-millisecond time; no meaningful overhead to evolution loop
**Constraints**: Backward compatible - empty stop_callbacks list must have zero behavior change
**Scale/Scope**: Modifies ~50 lines in async_engine.py + ~100 lines integration tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | PASS | Engine layer (async_engine.py) depends only on ports (StopperProtocol) and domain (StopperState). No adapter imports in engine. |
| **II. Async-First Design** | PASS | Engine is already async. Stoppers are synchronous callables (pure functions) - no async bridging needed. |
| **III. Protocol-Based Interfaces** | PASS | Uses existing StopperProtocol from ports/stopper.py. No new protocols required. |
| **IV. Three-Layer Testing** | REQUIRED | Must add: (1) Contract tests for stopper invocation, (2) Unit tests with mock stoppers, (3) Integration tests with real stoppers. |
| **V. Observability** | REQUIRED | Must log stopper triggering with structlog. Include stopper class name and iteration in log events. |
| **VI. Documentation Sync** | N/A | Internal engine change - no user-facing API changes requiring guide updates. Existing stopper docs cover usage. |

**ADRs Applicable**:
- ADR-000: Hexagonal Architecture - Engine receives stoppers via config injection
- ADR-001: Async-First - Stoppers are sync callables (pure functions), no async needed
- ADR-002: Protocol for Interfaces - Uses StopperProtocol
- ADR-005: Three-Layer Testing - Integration tests required
- ADR-008: Structured Logging - Log stopper triggers

**Gate Status**: PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/196-stopper-engine-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── architecture.md      # Phase 2 output (conditional)
└── tasks.md             # Phase 3 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   ├── stopper.py           # StopperState (existing)
│   └── models.py            # EvolutionConfig with stop_callbacks (existing)
├── ports/
│   └── stopper.py           # StopperProtocol (existing)
├── adapters/
│   └── stoppers/            # Stopper implementations (existing)
│       ├── timeout.py
│       ├── threshold.py
│       ├── signal.py
│       └── composite.py
└── engine/
    └── async_engine.py      # MODIFY: Add stopper integration

tests/
├── contracts/
│   └── test_stopper_protocol.py  # Existing protocol tests
├── unit/
│   ├── domain/
│   │   └── test_stopper.py       # Existing StopperState tests
│   └── engine/
│       └── test_stopper_integration.py  # NEW: Unit tests with mocks
└── integration/
    └── test_stopper_integration.py      # NEW: Integration tests
```

**Structure Decision**: Single hexagonal project. Modifications confined to engine layer (async_engine.py) with new tests in unit/engine and integration directories.

## Complexity Tracking

> No constitution violations - section not applicable.

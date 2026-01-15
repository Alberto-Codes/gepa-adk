# Implementation Plan: Objective Scores Passthrough

**Branch**: `026-objective-scores` | **Date**: 2026-01-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/026-objective-scores/spec.md`

## Summary

Pass through optional `objective_scores` from adapter evaluation results to engine state, iteration history, and evolution results. This enables multi-objective metric tracking and analysis without transforming the data structure. The implementation extends existing data models with optional fields that default to None, ensuring backward compatibility with adapters that don't provide objective scores.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, structlog>=25.5.0 (existing - no new deps)
**Storage**: N/A (in-memory evolution state)
**Testing**: pytest with three-layer testing (contract, unit, integration)
**Target Platform**: Linux/macOS Python runtime
**Project Type**: Single project (hexagonal architecture)
**Performance Goals**: No performance impact (simple field passthrough)
**Constraints**: Backward compatible - existing adapters must work unchanged
**Scale/Scope**: Minimal scope - optional field additions only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | PASS | Changes confined to domain/models.py and engine/async_engine.py - no layer violations |
| II. Async-First Design | PASS | No new I/O operations - passthrough only |
| III. Protocol-Based Interfaces | PASS | EvaluationBatch already has objective_scores field in ports/adapter.py |
| IV. Three-Layer Testing | PASS | Will add contract tests (protocol compliance), unit tests (engine state), integration tests (end-to-end) |
| V. Observability & Documentation | PASS | Google-style docstrings required for new/modified code |

**Gate Status**: PASS - No violations. Proceed with Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/026-objective-scores/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   ├── models.py           # MODIFY: Add objective_scores to IterationRecord, EvolutionResult
│   ├── types.py            # NO CHANGE - using inline type list[dict[str, float]] | None
│   └── exceptions.py       # NO CHANGE
├── ports/
│   └── adapter.py          # READ: EvaluationBatch already has objective_scores
├── engine/
│   └── async_engine.py     # MODIFY: Extract and pass through objective_scores
└── adapters/               # NO CHANGE - passthrough only

tests/
├── contracts/
│   └── test_objective_scores_models.py      # NEW: Model contract tests
├── unit/
│   └── engine/
│       └── test_objective_scores_engine.py  # NEW: Engine state tests
└── integration/
    └── test_objective_scores_e2e.py         # NEW: End-to-end tests
```

**Structure Decision**: Single project with hexagonal architecture. Changes affect domain layer (models.py) and engine layer (async_engine.py) only. Port layer already supports objective_scores via EvaluationBatch.

## Complexity Tracking

> No violations requiring justification. Feature is a minimal optional field passthrough.

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design completion.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | PASS | Data model changes in domain/, engine changes in engine/ - layers respected |
| II. Async-First Design | PASS | No sync/async bridging - purely data passthrough |
| III. Protocol-Based Interfaces | PASS | No protocol changes needed - EvaluationBatch already supports objective_scores |
| IV. Three-Layer Testing | PASS | Contract tests (data model invariants), unit tests (engine passthrough), integration tests (end-to-end) planned |
| V. Observability & Documentation | PASS | Docstrings defined in data-model.md, contracts specify behavior |

**Post-Design Status**: PASS - Ready for Phase 2 task generation.

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Implementation Plan | plan.md | Complete |
| Research | research.md | Complete |
| Data Model | data-model.md | Complete |
| Contracts | contracts/objective-scores-contract.md | Complete |
| Quickstart | quickstart.md | Complete |
| Agent Context | CLAUDE.md | Updated |

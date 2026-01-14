# Implementation Plan: Pass CriticScorer Metadata to Reflection Agent

**Branch**: `019-critic-metadata-passthrough` | **Date**: 2026-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/019-critic-metadata-passthrough/spec.md`

## Summary

This feature fixes a data flow gap where CriticScorer extracts rich metadata (feedback, actionable_guidance, dimension_scores) but the metadata is discarded before reaching the reflection agent. The implementation adds a `metadata` field to `EvaluationBatch`, captures scorer metadata in `ADKAdapter.evaluate()`, and enriches `_build_reflection_example()` to include critic feedback in the reflection context.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, structlog>=25.5.0, dataclasses (stdlib)
**Storage**: N/A (in-memory data flow)
**Testing**: pytest with three-layer testing (contract, unit, integration)
**Target Platform**: Linux server (ADK/LLM evaluation workloads)
**Project Type**: Single project (hexagonal architecture)
**Performance Goals**: <5% overhead on evaluation time (SC-004)
**Constraints**: Backward compatible with existing scorers (FR-006)
**Scale/Scope**: Internal data structure change affecting 3 files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Check (Phase 0)

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | PASS | Changes in `ports/adapter.py` (EvaluationBatch), `adapters/adk_adapter.py` (implementation). No layer violations. |
| **II. Async-First Design** | PASS | No new async methods. Existing async methods remain unchanged. |
| **III. Protocol-Based Interfaces** | PASS | EvaluationBatch is a dataclass, not a protocol. No protocol changes needed. |
| **IV. Three-Layer Testing** | REQUIRED | Contract tests for EvaluationBatch metadata field. Unit tests for _build_reflection_example with metadata. Integration tests for end-to-end critic->reflection flow. |
| **V. Observability & Documentation** | REQUIRED | Structured logging for metadata passthrough. Google-style docstrings for updated methods. |

**Gate Status**: PASS - All constitution principles satisfied or have clear implementation path.

### Post-Design Check (Phase 1)

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | PASS | Data model confirms changes isolated to `ports/adapter.py` (data structure) and `adapters/adk_adapter.py` (implementation). No cross-layer imports. |
| **II. Async-First Design** | PASS | No new I/O operations. Metadata is passed alongside existing data structures in the async flow. |
| **III. Protocol-Based Interfaces** | PASS | EvaluationBatch remains a dataclass. Adding `metadata` field maintains structural compatibility. |
| **IV. Three-Layer Testing** | READY | Contract tests defined in `contracts/evaluation_batch_contract.py` and `contracts/reflection_example_contract.py`. Unit and integration test locations identified. |
| **V. Observability & Documentation** | READY | Quickstart.md documents usage. Docstrings will be added during implementation. |

**Post-Design Gate Status**: PASS - Design phase complete. Ready for `/speckit.tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/019-critic-metadata-passthrough/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── evaluation-batch.py  # Updated EvaluationBatch contract
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── ports/
│   └── adapter.py           # EvaluationBatch (add metadata field)
├── adapters/
│   └── adk_adapter.py       # ADKAdapter (capture & pass metadata)
└── domain/
    └── (no changes)

tests/
├── contracts/
│   └── test_evaluation_batch.py  # EvaluationBatch metadata contract
├── unit/
│   └── test_adk_adapter.py       # _build_reflection_example tests
└── integration/
    └── test_critic_reflection.py # End-to-end metadata flow
```

**Structure Decision**: Single project with hexagonal architecture. Changes touch `ports/` (EvaluationBatch dataclass) and `adapters/` (ADKAdapter implementation). No new files required - only modifications to existing structures.

## Complexity Tracking

> No violations. Implementation is minimal and focused.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

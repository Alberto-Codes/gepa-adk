# Implementation Plan: Execute Workflows As-Is (Preserve Structure)

**Branch**: `215-workflow-structure` | **Date**: 2026-01-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/215-workflow-structure/spec.md`
**GitHub Issue**: #215

## Summary

Refactor `_build_pipeline()` in `MultiAgentAdapter` to preserve workflow structure (LoopAgent iterations, ParallelAgent concurrency, nested workflows) instead of flattening all agents into a single SequentialAgent. The implementation uses recursive cloning with instruction overrides applied only at LlmAgent leaf nodes.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0 (SequentialAgent, LoopAgent, ParallelAgent, LlmAgent)
**Storage**: N/A (in-memory workflow cloning)
**Testing**: pytest with three-layer strategy (contract/unit/integration)
**Target Platform**: Linux/macOS/Windows (Python package)
**Project Type**: Single library package (hexagonal architecture)
**Performance Goals**: No performance regression; maintain current evaluation throughput
**Constraints**: Must be backward compatible with existing evolve_workflow() API
**Scale/Scope**: Supports workflows with arbitrary nesting depth (default max_depth=5)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies | Status | Notes |
|-----------|---------|--------|-------|
| I. Hexagonal Architecture | Yes | PASS | Changes in adapters/ layer only; domain models unchanged |
| II. Async-First Design | Yes | PASS | No new I/O; uses existing async evaluate() flow |
| III. Protocol-Based Interfaces | No | N/A | No new protocols needed; extends existing adapter |
| IV. Three-Layer Testing | Yes | REQUIRED | Unit tests for cloning, integration tests for ADK execution |
| V. Observability & Documentation | Yes | REQUIRED | Update docs/guides/workflows.md |
| VI. Documentation Synchronization | Yes | REQUIRED | Update workflows guide and examples |

**ADR References**:
- ADR-000: Hexagonal Architecture - Changes isolated to adapters layer
- ADR-005: Three-Layer Testing - New tests required in all layers
- ADR-006: External Library Integration - ADK agent types handled in adapters

## Project Structure

### Documentation (this feature)

```text
specs/215-workflow-structure/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - no new protocols)
└── architecture.md      # Phase 2 output (conditional)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── adapters/
│   ├── multi_agent.py      # PRIMARY: Refactor _build_pipeline()
│   └── workflow.py         # Add clone_workflow_with_overrides()
├── domain/
│   └── (no changes)
├── ports/
│   └── (no changes)
└── api.py                  # (no changes - API preserved)

tests/
├── unit/
│   ├── test_workflow.py           # Add cloning tests
│   └── test_multi_agent.py        # Update pipeline tests
└── integration/
    └── test_workflow_integration.py  # Add ADK execution tests

docs/
└── guides/
    └── workflows.md        # Update with preserved structure behavior
```

**Structure Decision**: Single project with hexagonal architecture. Changes isolated to adapters layer per ADR-000.

## Complexity Tracking

> No complexity violations. Implementation follows existing patterns.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | — | — |

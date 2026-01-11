# Implementation Plan: Concurrent Batch Evaluation

**Branch**: `012-concurrent-batch` | **Date**: 2026-01-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-concurrent-batch/spec.md`

## Summary

Add semaphore-controlled concurrent batch evaluation to the ADKAdapter, enabling parallel execution of batch evaluations with configurable concurrency limits. This feature transforms the current sequential evaluation loop in `ADKAdapter.evaluate()` into a parallel implementation using `asyncio.Semaphore` and `asyncio.gather()`, achieving 3-5x performance improvement while maintaining result ordering and graceful error handling.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0, asyncio (stdlib)
**Storage**: N/A (in-memory session state via ADK's InMemorySessionService)
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux server, cross-platform Python
**Project Type**: Single Python package (hexagonal architecture)
**Performance Goals**: 3-5x speedup over sequential evaluation, linear scaling with concurrency
**Constraints**: Memory-bounded per evaluation, configurable concurrency 1-20
**Scale/Scope**: Batches of 100+ examples, concurrency up to 20

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | PASS | Changes confined to `adapters/adk_adapter.py`; no port changes needed. Uses existing `EvolutionConfig.max_concurrent_evals` from `domain/models.py`. |
| II. Async-First Design | PASS | Feature directly implements async concurrency via `asyncio.Semaphore` and `asyncio.gather()`. All existing methods are already async. |
| III. Protocol-Based Interfaces | PASS | `AsyncGEPAAdapter` protocol unchanged; `EvaluationBatch` return type unchanged. Implementation is internal to adapter. |
| IV. Three-Layer Testing | PASS | Will add: contract tests (protocol compliance), unit tests (semaphore behavior, error handling), integration tests (real ADK execution). |
| V. Observability & Documentation | PASS | Will add structured logging for concurrency metrics. Google-style docstrings for new/modified methods. |

**Gate Result**: PASS - All principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/012-concurrent-batch/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   ├── models.py        # EvolutionConfig (already has max_concurrent_evals)
│   ├── types.py         # Type aliases
│   ├── exceptions.py    # Error types
│   └── trajectory.py    # ADKTrajectory
├── ports/
│   ├── adapter.py       # AsyncGEPAAdapter protocol, EvaluationBatch
│   └── scorer.py        # Scorer protocol
├── adapters/
│   └── adk_adapter.py   # ADKAdapter - PRIMARY MODIFICATION TARGET
├── engine/
│   └── async_engine.py  # Evolution engine (uses adapter)
└── utils/
    └── events.py        # Trajectory extraction

tests/
├── contracts/           # Protocol compliance tests
├── integration/         # Real ADK tests (@pytest.mark.slow)
└── unit/                # Mock-based unit tests
```

**Structure Decision**: Single Python package following hexagonal architecture. Primary changes in `adapters/adk_adapter.py` with corresponding tests in all three test layers.

## Complexity Tracking

> No violations requiring justification. Implementation follows established patterns.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

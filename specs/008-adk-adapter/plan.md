# Implementation Plan: ADKAdapter (AsyncGEPAAdapter for ADK)

**Branch**: `008-adk-adapter` | **Date**: 2026-01-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-adk-adapter/spec.md`

## Summary

Implement `ADKAdapter`, a concrete adapter class that bridges GEPA's evaluation patterns to Google ADK's agent/runner architecture. The adapter implements the `AsyncGEPAAdapter` protocol, enabling evolutionary optimization of ADK agents by overriding instructions, capturing execution traces, scoring outputs, and building reflective datasets.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: 
- `google-adk>=1.22.0` (LlmAgent, Runner, InMemorySessionService, Event)
- `gepa_adk.ports.adapter` (AsyncGEPAAdapter, EvaluationBatch)
- `gepa_adk.ports.scorer` (Scorer)
- `gepa_adk.domain.models` (Candidate)
- `structlog` (logging)

**Storage**: In-memory sessions (InMemorySessionService by default)  
**Testing**: pytest with pytest-asyncio, three-layer testing (contracts, unit, integration)  
**Target Platform**: Linux server, Python async runtime  
**Project Type**: Single package (src/gepa_adk/adapters/)  
**Performance Goals**: Evaluation latency bounded by underlying LLM latency  
**Constraints**: Session isolation between batch examples, async-first  
**Scale/Scope**: Single-agent evaluation, sequential batch processing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | ✅ PASS | ADKAdapter goes in `adapters/` layer, implements protocol from `ports/`, imports Google ADK externally |
| **II. Async-First Design** | ✅ PASS | All protocol methods are async coroutines, uses `async for event in runner.run_async()` |
| **III. Protocol-Based Interfaces** | ✅ PASS | Implements `AsyncGEPAAdapter` protocol, uses `Scorer` protocol for scoring |
| **IV. Three-Layer Testing** | ✅ PASS | Will include contracts, unit (with mock ADK), and integration tests |
| **V. Observability & Documentation** | ✅ PASS | Structured logging with structlog, Google-style docstrings |

**Gate Status**: ✅ PASSED - Ready for Phase 0 research

## Project Structure

### Documentation (this feature)

```text
specs/008-adk-adapter/
├── plan.md              # This file
├── research.md          # Phase 0 output - ADK API research
├── data-model.md        # Phase 1 output - entity definitions  
├── quickstart.md        # Phase 1 output - usage examples
├── contracts/           # Phase 1 output - API contracts
│   └── adapter.yaml     # ADKAdapter interface contract
└── tasks.md             # Phase 2 output (speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── adapters/                    # NEW: External library integrations
│   ├── __init__.py             
│   └── adk_adapter.py          # ADKAdapter implementation
├── domain/
│   ├── models.py               # Candidate (existing)
│   ├── types.py                # Score, ComponentName (existing)
│   └── exceptions.py           # AdapterError (may extend)
├── ports/
│   ├── adapter.py              # AsyncGEPAAdapter, EvaluationBatch (existing)
│   └── scorer.py               # Scorer protocol (existing)
└── engine/                     # (future: AsyncGEPAEngine will use adapter)

tests/
├── contracts/
│   └── test_adk_adapter_contracts.py    # Protocol compliance
├── unit/
│   └── adapters/
│       └── test_adk_adapter.py          # Business logic with mocks
└── integration/
    └── test_adk_adapter_integration.py  # Real ADK calls (@pytest.mark.slow)
```

**Structure Decision**: Following existing hexagonal architecture pattern. ADKAdapter is placed in `adapters/` layer where external library integrations belong. This aligns with Constitution Principle I and ADR-006.

## Complexity Tracking

> No violations - design follows established patterns.

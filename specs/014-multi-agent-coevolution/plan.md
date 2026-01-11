# Implementation Plan: Multi-Agent Co-Evolution (evolve_group)

**Branch**: `014-multi-agent-coevolution` | **Date**: January 11, 2026 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-multi-agent-coevolution/spec.md`

## Summary

Implement multi-agent co-evolution via `evolve_group()` API function that enables evolving multiple ADK agents together. The approach uses ADK's `SequentialAgent` for session state sharing between agents during evaluation, with a `MultiAgentAdapter` that orchestrates multi-agent pipeline execution and scoring. All agent instructions are optimized together while targeting the primary agent's score for fitness evaluation.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: google-adk>=1.22.0, structlog>=25.5.0  
**Storage**: N/A (in-memory evolution state)  
**Testing**: pytest, pytest-asyncio (three-layer: contracts, unit, integration)  
**Target Platform**: Linux/macOS/Windows (cross-platform Python)  
**Project Type**: Single Python package (hexagonal architecture)  
**Performance Goals**: Linear scaling with agent count (N agents = ~N× single-agent time)  
**Constraints**: Must maintain async-first design, no blocking I/O in evolution loop  
**Scale/Scope**: 2-10 agents per group typical, max_iterations up to 100

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Hexagonal Architecture** | ✅ PASS | MultiAgentAdapter in `adapters/`, uses `ports/adapter.py` protocol |
| **II. Async-First Design** | ✅ PASS | `evolve_group()` is async, all I/O through async adapter methods |
| **III. Protocol-Based Interfaces** | ✅ PASS | Uses existing `AsyncGEPAAdapter` protocol, no new ABCs |
| **IV. Three-Layer Testing** | ✅ PASS | Contract tests for MultiAgentAdapter, unit tests with fakes, integration with real ADK |
| **V. Observability & Documentation** | ✅ PASS | structlog with context, Google-style docstrings, domain exceptions |

**ADR Compliance**:
- ADR-000: MultiAgentAdapter isolated in adapters/, depends on ports/ protocols
- ADR-001: All methods async, uses existing async engine
- ADR-002: No new protocols needed; reuses AsyncGEPAAdapter
- ADR-005: Tests in contracts/, unit/, integration/
- ADR-006: ADK imports only in adapters/multi_agent.py
- ADR-008: structlog with evolution_id, agent_name context
- ADR-009: Extends existing exception hierarchy
- ADR-010: Google docstrings with examples

## Project Structure

### Documentation (this feature)

```text
specs/014-multi-agent-coevolution/
├── plan.md              # This file
├── research.md          # Phase 0 output - ADK multi-agent patterns
├── data-model.md        # Phase 1 output - Entity definitions
├── quickstart.md        # Phase 1 output - Usage examples
├── contracts/           # Phase 1 output - API contracts
│   └── evolve_group.md  # Public API contract
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── __init__.py          # Add evolve_group to public API
├── api.py               # NEW: evolve_group() function
├── domain/
│   ├── models.py        # UPDATE: Add MultiAgentEvolutionResult
│   └── exceptions.py    # UPDATE: Add MultiAgentValidationError
├── adapters/
│   ├── multi_agent.py   # NEW: MultiAgentAdapter implementation
│   └── adk_adapter.py   # Existing (reference implementation)
└── ports/
    └── adapter.py       # Existing AsyncGEPAAdapter protocol (no changes)

tests/
├── contracts/
│   └── test_multi_agent_adapter_protocol.py  # NEW: Protocol compliance
├── unit/
│   └── test_multi_agent_adapter.py           # NEW: Unit tests with fakes
└── integration/
    └── test_multi_agent_evolution.py         # NEW: Real ADK tests
```

**Structure Decision**: Follows existing hexagonal architecture pattern. New `MultiAgentAdapter` in adapters layer implements existing `AsyncGEPAAdapter` protocol. Public API exposed via new `api.py` module at package root.

## Complexity Tracking

> No constitution violations - design follows all established patterns.

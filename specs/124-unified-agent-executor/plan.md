# Implementation Plan: Unified Agent Executor

**Branch**: `124-unified-agent-executor` | **Date**: 2026-01-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/124-unified-agent-executor/spec.md`
**Related Issue**: [#135](https://github.com/Alberto-Codes/gepa-adk/issues/135)

## Summary

Implement a unified agent execution interface that provides feature parity across all agent types (generator, critic, reflection). Currently, ~18-19% of code is duplicated across three separate execution paths. The AgentExecutor consolidates this into a single protocol-based interface with consistent session management, event capture, and result handling.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0 (Runner, Session, Event), structlog >= 25.5.0
**Storage**: N/A (in-memory session state via ADK's InMemorySessionService)
**Testing**: pytest with contract/unit/integration layers per ADR-005
**Target Platform**: Linux/Windows/macOS (library, not service)
**Project Type**: Single Python package (hexagonal architecture)
**Performance Goals**: No regression from current execution paths
**Constraints**: Must maintain backward compatibility with existing evolve() API
**Scale/Scope**: Internal refactoring, ~400 lines of code affected

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | ✅ Pass | Protocol in ports/, adapter in adapters/, no domain changes |
| II. Async-First Design | ✅ Pass | execute_agent() is async, no sync bridges internally |
| III. Protocol-Based Interfaces | ✅ Pass | AgentExecutorProtocol with @runtime_checkable |
| IV. Three-Layer Testing | ✅ Pass | Contract tests for protocol, unit for adapter, integration for feature parity |
| V. Observability & Documentation | ✅ Pass | Google-style docstrings, structlog logging |
| VI. Documentation Synchronization | ⚠️ N/A | Internal refactor, no user-facing API changes |

**Post-Phase 1 Re-check**: All principles satisfied. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/124-unified-agent-executor/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # ADK API + codebase analysis
├── data-model.md        # ExecutionResult, protocol definition
├── quickstart.md        # Usage examples
├── contracts/           # Protocol contracts
│   └── agent_executor_protocol.py
├── architecture.md      # System architecture (Phase 2)
└── tasks.md             # Implementation tasks (Phase 3)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   ├── models.py           # (no changes)
│   ├── types.py            # (no changes)
│   └── exceptions.py       # (no changes)
├── ports/
│   ├── protocols.py        # (existing protocols)
│   └── agent_executor.py   # NEW: AgentExecutorProtocol, ExecutionResult, ExecutionStatus
├── adapters/
│   ├── adk_adapter.py      # MODIFY: Use AgentExecutor
│   ├── critic_scorer.py    # MODIFY: Use AgentExecutor
│   └── agent_executor.py   # NEW: AgentExecutor implementation
├── engine/
│   ├── adk_reflection.py   # MODIFY: Use AgentExecutor
│   └── proposer.py         # (no changes)
└── utils/
    └── events.py           # MODIFY: Consolidate extraction utilities

tests/
├── contracts/
│   └── test_agent_executor_protocol.py   # NEW: Protocol compliance
├── unit/
│   ├── ports/
│   │   └── test_agent_executor_types.py  # NEW: Enum/dataclass tests
│   └── adapters/
│       └── test_agent_executor.py        # NEW: Adapter unit tests
└── integration/
    └── test_unified_execution.py         # NEW: Feature parity tests
```

**Structure Decision**: Single Python package with hexagonal layers. No structural changes, only new files within existing directories following ADR-000.

## Complexity Tracking

> **No violations to justify** - All principles satisfied.

## Phase Artifacts

| Phase | Artifact | Status |
|-------|----------|--------|
| 0 | research.md | ✅ Complete |
| 1 | data-model.md | ✅ Complete |
| 1 | contracts/ | ✅ Complete |
| 1 | quickstart.md | ✅ Complete |
| 2 | architecture.md | Pending |

## Key Design Decisions

### Decision 1: Protocol in Ports Layer

**Choice**: Define AgentExecutorProtocol in `src/gepa_adk/ports/agent_executor.py`

**Rationale**: Follows hexagonal architecture - ports contain interfaces, adapters contain implementations. Enables mocking for unit tests.

### Decision 2: Timeout as Status, Not Exception

**Choice**: Return `ExecutionStatus.TIMEOUT` instead of raising TimeoutError

**Rationale**: Allows graceful handling, events are still captured and accessible even on timeout.

### Decision 3: Any Type for Agent Parameter

**Choice**: Use `Any` for agent parameter in protocol, not LlmAgent

**Rationale**: Avoid coupling ports layer to ADK types. Validation happens in adapter.

### Decision 4: Session Reuse via Parameter

**Choice**: Add `existing_session_id` parameter instead of separate method

**Rationale**: Simpler API, single method handles both new and existing sessions.

## References

- [ADR-000: Hexagonal Architecture](../../docs/adr/ADR-000-hexagonal-architecture.md)
- [ADR-002: Protocol for Interfaces](../../docs/adr/ADR-002-protocol-for-interfaces.md)
- [ADR-005: Three-Layer Testing](../../docs/adr/ADR-005-three-layer-testing.md)
- [Research: ADK Runner API](research.md)
- [GitHub Issue #135](https://github.com/Alberto-Codes/gepa-adk/issues/135)

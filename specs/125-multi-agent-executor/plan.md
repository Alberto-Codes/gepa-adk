# Implementation Plan: Multi-Agent Unified Executor

**Branch**: `125-multi-agent-executor` | **Date**: 2026-01-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/125-multi-agent-executor/spec.md`

## Summary

Extend `MultiAgentAdapter` and `evolve_group()` to use the unified `AgentExecutor` from PR #138, ensuring all agent types (generator, critic, reflection) share consistent session management and feature parity with single-agent evolution. The implementation adds an optional `executor` parameter to `MultiAgentAdapter`, creates an executor in `evolve_group()` when one is not provided, and passes it through to `CriticScorer` and reflection functions.

## Technical Context

**Language/Version**: Python 3.12 + google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0
**Primary Dependencies**: google-adk (LlmAgent, BaseAgent, Runner, Session), structlog (logging)
**Storage**: N/A (in-memory session state via ADK's InMemorySessionService)
**Testing**: pytest + pytest-asyncio, contract/unit/integration layers
**Target Platform**: Linux/macOS/Windows (cross-platform Python)
**Project Type**: Single project (Python library)
**Performance Goals**: No regression in multi-agent evaluation throughput
**Constraints**: Backward compatibility with existing `evolve_group()` and `MultiAgentAdapter` callers
**Scale/Scope**: ~200-300 LOC changes across 3-4 files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | ✅ Pass | Protocol in ports/, implementation in adapters/ |
| II. Async-First Design | ✅ Pass | All execution methods are async |
| III. Protocol-Based Interfaces | ✅ Pass | Uses existing AgentExecutorProtocol |
| IV. Three-Layer Testing | ✅ Pass | Contract, unit, integration tests planned |
| V. Observability & Code Documentation | ✅ Pass | Structured logging with `uses_executor=True` |
| VI. Documentation Synchronization | ✅ Pass | Will update multi-agent guide and examples |

## Project Structure

### Documentation (this feature)

```text
specs/125-multi-agent-executor/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 3 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── ports/
│   └── agent_executor.py      # AgentExecutorProtocol (existing, no changes)
├── adapters/
│   ├── agent_executor.py      # AgentExecutor implementation (existing, no changes)
│   ├── multi_agent.py         # MultiAgentAdapter (ADD executor parameter)
│   └── critic_scorer.py       # CriticScorer (already has executor parameter)
├── engine/
│   └── reflection.py          # ADK reflection functions (ADD executor parameter)
└── api.py                     # evolve_group() (ADD executor creation and passing)

tests/
├── contracts/
│   └── test_multi_agent_executor_contract.py  # New contract tests
├── unit/
│   └── adapters/
│       └── test_multi_agent.py                # Extend existing tests
└── integration/
    └── test_multi_agent_executor_integration.py  # New integration tests
```

**Structure Decision**: Single project structure. Changes are localized to existing modules in the adapters and api layers. No new files needed except for tests.

## Complexity Tracking

> **No violations. Implementation follows existing patterns.**

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Executor passing | Parameter injection | Follows existing CriticScorer pattern |
| Backward compatibility | Optional parameter with None default | Existing callers continue working |
| Session sharing | Via shared executor instance | Consistent with single-agent evolution |

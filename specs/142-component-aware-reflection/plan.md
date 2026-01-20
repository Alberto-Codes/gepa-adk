# Implementation Plan: Component-Aware Reflection Agents

**Branch**: `142-component-aware-reflection` | **Date**: 2026-01-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/142-component-aware-reflection/spec.md`
**Research**: [research.md](research.md)

## Summary

Add component-aware reflection agents with validation tools for the `output_schema` component type. The system provides pre-built reflection agent factories that create ADK LlmAgents with appropriate instructions and validation tools. When evolving `output_schema` components, the reflection agent can validate proposed Pydantic schemas before returning them, reducing wasted iterations on invalid proposals.

**Key Technical Approach** (from research):
- Use ADK's `FunctionTool` to wrap existing `validate_schema_text()` function
- Factory pattern creates configured `LlmAgent` instances per component type
- Registry maps component names to factories for auto-selection
- Explicit instruction guides LLM to use validation tool before returning

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0, pydantic >= 2.0, structlog >= 25.5.0
**Storage**: N/A (in-memory evolution state)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Cross-platform Python library
**Project Type**: Single project (Python library)
**Performance Goals**: N/A (validation adds minimal overhead)
**Constraints**: Must not break existing reflection behavior (backward compatibility)
**Scale/Scope**: MVP covers `output_schema` only; registry extensible for future validators

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | ✅ PASS | New code in `engine/` (reflection_agents.py), `utils/` (schema_tools.py). No adapter imports in engine - uses ADK via executor injection. |
| **II. Async-First Design** | ✅ PASS | Reflection functions already async. Tool validation is sync but called within async flow. |
| **III. Protocol-Based Interfaces** | ✅ PASS | Uses existing `AgentExecutorProtocol`. No new protocols needed. |
| **IV. Three-Layer Testing** | ✅ PASS | Will add: unit tests for factories, integration tests for tool validation flow. |
| **V. Observability & Code Documentation** | ✅ PASS | Will use structlog for validation events. Google-style docstrings required. |
| **VI. Documentation Synchronization** | ✅ PASS | User-facing feature - requires guide updates and example. |

**ADRs Applicable**:
- ADR-000: Hexagonal Architecture - validation tool in utils/, factory in engine/
- ADR-002: Protocol for Interfaces - no new protocols needed
- ADR-005: Three-Layer Testing - contract + unit + integration tests
- ADR-006: External Library Integration - ADK FunctionTool used in adapters layer conceptually

## Project Structure

### Documentation (this feature)

```text
specs/142-component-aware-reflection/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 quickstart guide
├── contracts/           # Phase 1 API contracts
├── architecture.md      # Phase 2 architecture (if needed)
└── tasks.md             # Phase 3 tasks (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── engine/
│   ├── adk_reflection.py       # MODIFY: Accept component_name, auto-select agent
│   ├── proposer.py             # MODIFY: Pass component_name to reflection
│   └── reflection_agents.py    # CREATE: Factory functions + registry
├── utils/
│   └── schema_tools.py         # CREATE: validate_output_schema tool function
└── domain/
    └── types.py                # MODIFY: Add component name constants (optional)

tests/
├── unit/
│   └── engine/
│       └── test_reflection_agents.py    # CREATE: Unit tests for factories
└── integration/
    └── test_schema_reflection.py        # CREATE: Integration test with validation

docs/
└── guides/
    └── single-agent.md         # UPDATE: Document schema evolution with validation

examples/
└── schema_evolution_validated.py  # CREATE: Example showing validated schema evolution
```

**Structure Decision**: Follows existing hexagonal architecture. New factory module in `engine/` (orchestration), new tool wrapper in `utils/` (shared utilities). No changes to `adapters/` - ADK FunctionTool is created in utils and passed to agents.

## Complexity Tracking

> No constitution violations. All changes fit within existing architecture.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| New module `reflection_agents.py` | In `engine/` not `adapters/` | Factory creates agents but doesn't perform I/O; engine orchestrates |
| Tool wrapper in `utils/` | Not in `adapters/` | Pure function wrapping existing validation; no ADK imports |

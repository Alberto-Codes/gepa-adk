# Implementation Plan: AgentProvider Protocol

**Branch**: `029-agent-provider-protocol` | **Date**: 2026-01-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/029-agent-provider-protocol/spec.md`

## Summary

Define an `AgentProvider` protocol for optional agent loading and persistence, enabling gepa-adk integrators to implement custom storage backends for agent configurations. The protocol supports loading agents by name, persisting evolved instructions, and listing available agents. Google ADK's `from_config()` YAML loading pattern will be referenced but the protocol remains storage-agnostic.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, structlog>=25.5.0, typing (stdlib)
**Storage**: N/A (protocol definition only - implementations choose storage)
**Testing**: pytest with contract tests
**Target Platform**: Linux (Python package)
**Project Type**: Single project (library)
**Performance Goals**: N/A (protocol definition - no runtime overhead)
**Constraints**: No external imports in ports/ layer per ADR-000
**Scale/Scope**: Single protocol with 3 methods

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | PASS | Protocol goes in `ports/`, no external imports |
| II. Async-First Design | EXCEPTION | Protocol methods are sync (see rationale below) |
| III. Protocol-Based Interfaces | PASS | Using `typing.Protocol` with `@runtime_checkable` |
| IV. Three-Layer Testing | PASS | Contract tests in `tests/contracts/` |
| V. Observability & Documentation | PASS | Google-style docstrings, structlog for implementations |

**Exception Rationale for Principle II (Async-First)**:

While ADR-001 requires async for I/O-bound operations, the AgentProvider protocol uses sync methods for the following reasons:

1. **Protocol Abstraction**: The protocol itself does not perform I/O; implementations handle storage operations
2. **Simplicity**: Many implementations (in-memory, simple file-based) don't require async
3. **Flexibility**: Implementations can use async internally and block in sync methods, or provide async wrappers
4. **Caller Control**: Callers needing async can wrap with `asyncio.to_thread()` or similar patterns

This exception is documented in research.md Section 4 and aligns with the protocol's role as a configuration abstraction layer rather than an I/O layer.

**ADRs Applicable**:
- ADR-000: Hexagonal Architecture - Protocol in ports/ layer
- ADR-002: Protocol for Interfaces - Use typing.Protocol, @runtime_checkable
- ADR-005: Three-Layer Testing - Contract tests required

## Project Structure

### Documentation (this feature)

```text
specs/029-agent-provider-protocol/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI/Protocol specs)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── ports/
│   ├── __init__.py           # Export AgentProvider
│   └── agent_provider.py     # NEW: AgentProvider protocol definition
└── domain/
    └── exceptions.py         # (No new exceptions - implementations define their own)

tests/
├── contracts/
│   └── test_agent_provider_protocol.py  # NEW: Protocol compliance tests
└── unit/
    └── test_agent_provider_unit.py      # NEW: Unit tests for mock provider
```

**Structure Decision**: Single project structure following existing hexagonal architecture. Protocol definition in `ports/` layer, contract tests in `tests/contracts/`.

## Complexity Tracking

> No complexity violations. Feature is a straightforward protocol definition.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

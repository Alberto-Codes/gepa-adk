# Architecture Decision Records

Architecture Decision Records (ADRs) capture the key technical decisions made during the development of GEPA-ADK. Each ADR explains the context, decision, and consequences of a particular architectural choice.

## Purpose

ADRs serve as living documentation that:

- **Explains why** design decisions were made
- **Provides context** for future developers
- **Evolves** as the project grows
- **Guides** implementation of new features

## How to Use ADRs

When implementing a feature:

1. Check which ADRs apply to your work
2. Follow the patterns and principles documented
3. If a new decision is needed, create a new ADR

## ADR Index

| ADR | Title | Status | Summary |
|-----|-------|--------|---------|
| [ADR-000](ADR-000-hexagonal-architecture.md) | Hexagonal Architecture | Accepted | Ports & adapters pattern for dependency isolation |
| [ADR-001](ADR-001-async-first-architecture.md) | Async-First Architecture | Accepted | All I/O operations use async/await |
| [ADR-002](ADR-002-protocol-for-interfaces.md) | Protocol-Based Interfaces | Accepted | Use `typing.Protocol` for structural subtyping |
| [ADR-005](ADR-005-three-layer-testing.md) | Three-Layer Testing | Accepted | Contract, unit, and integration test layers |
| [ADR-006](ADR-006-external-library-integration.md) | External Library Integration | Accepted | Isolate external dependencies in adapters |
| [ADR-008](ADR-008-structured-logging.md) | Structured Logging | Accepted | Use structlog for observable logging |
| [ADR-009](ADR-009-exception-hierarchy.md) | Exception Hierarchy | Accepted | All exceptions inherit from EvolutionError |
| [ADR-010](ADR-010-docstring-quality.md) | Docstring Quality | Accepted | Google-style docstrings with 95%+ coverage |
| [ADR-011](ADR-011-cross-platform-encoding.md) | Cross-Platform Encoding | Accepted | Encoding-safe logging for Windows cp1252 consoles |
| [ADR-012](ADR-012-multi-agent-component-addressing.md) | Multi-Agent Component Addressing | Accepted | Dot-separated qualified names for multi-agent evolution |
| [ADR-013](ADR-013-result-type-protocol.md) | Result Type Unification | Accepted | Shared protocol for evolution result types via structural subtyping |
| [ADR-014](ADR-014-adapter-reorganization.md) | Adapter Layer Reorganization | Accepted | Concern-based sub-packages with backward-compatible re-exports |
| [ADR-015](ADR-015-result-schema-versioning.md) | Result Schema Versioning | Accepted | Domain-layer schema versioning and stop reason tracking for evolution results |

## Core Principles

The ADRs establish five core principles that guide all development:

1. **Hexagonal Architecture** (ADR-000): Strict layer boundaries between domain, ports, adapters, and engine
2. **Async-First Design** (ADR-001): All I/O-bound operations must be async
3. **Protocol-Based Interfaces** (ADR-002): Use protocols for flexibility without inheritance
4. **Three-Layer Testing** (ADR-005): Contract, unit, and integration tests for every feature
5. **Observability & Documentation** (ADR-008, 009, 010): Structured logging, exception handling, and docstring quality

## Related Documentation

- [Docstring Templates](../contributing/docstring-templates.md) - How to write docstrings
- [API Reference](../reference/index.md) - Generated API documentation

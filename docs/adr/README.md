# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the gepa-adk project.

ADRs document significant architectural decisions made during the development of gepa-adk, providing context, rationale, and consequences for future contributors.

## ADR Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-000](ADR-000-hexagonal-architecture.md) | Hexagonal Architecture | Accepted |
| [ADR-001](ADR-001-async-first-architecture.md) | Async-First Architecture | Accepted |
| [ADR-002](ADR-002-protocol-for-interfaces.md) | Protocol for Interfaces | Accepted |
| [ADR-005](ADR-005-three-layer-testing.md) | Three-Layer Testing Strategy | Accepted |
| [ADR-006](ADR-006-external-library-integration.md) | External Library Integration | Accepted |
| [ADR-008](ADR-008-structured-logging.md) | Structured Logging Pattern | Accepted |
| [ADR-009](ADR-009-exception-hierarchy.md) | Exception Hierarchy | Accepted |
| [ADR-010](ADR-010-docstring-quality.md) | Docstring Quality Standards | Accepted |

## ADR Template

When creating a new ADR, use the following template:

```markdown
# ADR-XXX: Title

> **Status**: Proposed | Accepted | Deprecated | Superseded
> **Date**: YYYY-MM-DD
> **Deciders**: [list of people involved]

## Context

[Describe the context and problem statement]

## Decision

[Describe the decision that was made]

## Consequences

### Positive
- [List positive consequences]

### Negative
- [List negative consequences]

### Neutral
- [List neutral consequences]

## Alternatives Considered

[List alternatives that were considered and why they were rejected]
```

## References

- [ADR GitHub Organization](https://adr.github.io/)
- [Michael Nygard's ADR article](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)

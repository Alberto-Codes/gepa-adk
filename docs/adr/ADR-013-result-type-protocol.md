# ADR-013: Result Type Unification via Shared Protocol

> **Status**: Accepted
> **Date**: 2026-03-02
> **Deciders**: gepa-adk maintainers

## Context

Two frozen result dataclasses — `EvolutionResult` (single-agent) and `MultiAgentEvolutionResult` (multi-agent) — share 5 data fields and 2 computed properties. Engine and utility code that accepts either type must currently use `EvolutionResult | MultiAgentEvolutionResult` type unions. As `WorkflowEvolutionResult` is added in the future, every union must be extended, creating a maintenance burden and scattered type definitions.

Both types are frozen `@dataclass(slots=True, frozen=True, kw_only=True)` instances that cannot be modified after creation. Their shared surface consists of:

- `original_score: float`
- `final_score: float`
- `evolved_components: dict[str, str]`
- `iteration_history: list[IterationRecord]`
- `total_iterations: int`
- `improvement` computed property (float)
- `improved` computed property (bool)

## Decision

Define a minimal `EvolutionResultProtocol` in `ports/evolution_result.py` that both result types satisfy via structural subtyping (ADR-002). The protocol declares the 5 shared data fields as data attribute annotations and the 2 computed properties as `@property` stubs.

This is the project's **first data-attribute protocol**. All 11 existing protocols in `ports/` use method stubs only. Data annotations were chosen here because the shared surface consists of frozen dataclass fields, not methods — data annotations match the structural reality exactly. `@property` stubs were considered for all 7 members but rejected as unnecessary indirection for the 5 plain fields.

### Deferred: `stop_reason`

The `stop_reason` field is intentionally excluded from this initial protocol definition. It will be added to both result types and to this protocol in Epic 2, Story 2.1, when `StopReason` enum and the corresponding field are introduced.

## Rationale

- **ADR-002 alignment**: Protocol at the boundary, implementations stay independent via structural subtyping — no inheritance required
- **Zero code change**: Both `EvolutionResult` and `MultiAgentEvolutionResult` already satisfy the protocol structurally without any modifications
- **Scalable**: Future result types (e.g., `WorkflowEvolutionResult`) need only satisfy the protocol shape — no type union updates needed
- **Mode-specific preservation**: Fields like `valset_score` (single-agent) and `primary_agent` (multi-agent) remain on their concrete types; consumers needing those fields use the concrete type directly

## Consequences

### Positive

- **Type-safe polymorphism**: Engine code can accept `EvolutionResultProtocol` instead of unions
- **Contract enforcement**: The contract test catches future field renames or removals that would break the shared interface
- **Future-proof**: New result types automatically work with protocol-typed consumers

### Negative

- **Novel pattern**: First data-attribute protocol in the project — contributors must understand it differs from existing method-only protocols
- **Runtime limitation**: `isinstance()` checks attribute presence, not types — a class with `original_score: str` would still pass

### Neutral

- **Protocol growth**: As `stop_reason` and `schema_version` are added (Epic 2), the protocol expands but remains minimal

## Alternatives Considered

### 1. ABC Base Class

Use `abc.ABC` as a shared base for both result types. Rejected because it violates ADR-002 (structural subtyping over inheritance) and would require modifying the existing frozen dataclasses to inherit from a base class.

### 2. Type Union Everywhere

Continue using `EvolutionResult | MultiAgentEvolutionResult` at every call site. Rejected because it doesn't scale — each new result type requires updating every union, and the pattern provides no contract enforcement.

## References

- [ADR-002: Protocol-Based Interfaces](ADR-002-protocol-for-interfaces.md)
- [ADR-000: Hexagonal Architecture](ADR-000-hexagonal-architecture.md)

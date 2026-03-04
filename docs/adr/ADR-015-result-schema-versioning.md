# ADR-015: Result Schema Versioning — Domain-Layer Serialization

> **Status**: Accepted
> **Date**: 2026-03-04
> **Deciders**: gepa-adk maintainers

## Context

Evolution results (`EvolutionResult`, `MultiAgentEvolutionResult`) are frozen dataclasses that capture the outcome of an evolution run. As GEPA-ADK moves toward cross-session result comparison and experiment tracking, serialized results loaded from previous sessions require a forward-compatible schema — a plain JSON round-trip is not sufficient.

Additionally, the engine terminates evolution runs for several reasons (max iterations reached, patience exhausted, custom stopper triggered), but this information was lost — the caller could only see the final score, not *why* the run stopped.

## Decision

### Schema Versioning

Add a frozen `schema_version: int = CURRENT_SCHEMA_VERSION` field to both result types, where `CURRENT_SCHEMA_VERSION = 1` is a module-level constant in `domain/models.py`.

Design rules:
- `to_dict()` outputs `{"schema_version": N, ...}` — version is always included
- `from_dict()` accepts `schema_version <= CURRENT_VERSION` — explicit migration per version step
- `from_dict()` always returns the current-version type — missing fields get `None` defaults
- Output `schema_version` is always `CURRENT_VERSION` regardless of input version
- Unknown `schema_version > CURRENT_VERSION` raises `ConfigurationError` with migration guidance

**Note:** `to_dict()` and `from_dict()` are not implemented in this ADR's initial story (Story 2.1). They are implemented in Story 2.2. This ADR documents the full decision; implementation is phased.

### Stop Reason Tracking

Add `StopReason(str, Enum)` to `domain/types.py` with six values:

| Value | Meaning |
|-------|---------|
| `COMPLETED` | Default — normal completion |
| `MAX_ITERATIONS` | Reached max iterations or patience exhausted |
| `STOPPER_TRIGGERED` | Custom stopper (via `StopperProtocol`) returned True |
| `KEYBOARD_INTERRUPT` | User interrupted (future: Story 2.4) |
| `TIMEOUT` | Time limit exceeded (future) |
| `CANCELLED` | Programmatic cancellation (future) |

Add a frozen `stop_reason: StopReason = StopReason.COMPLETED` field to both result types.

### Stop Reason Mapping

| Termination Condition | StopReason Value |
|---|---|
| `iteration >= max_iterations` | `MAX_ITERATIONS` |
| `stagnation_counter >= patience` | `MAX_ITERATIONS` |
| Custom stopper returns True | `STOPPER_TRIGGERED` |
| Normal loop completion | `COMPLETED` (default) |
| `max_iterations=0` (baseline-only) | `MAX_ITERATIONS` |

**Patience maps to `MAX_ITERATIONS`**, not `STOPPER_TRIGGERED`, because patience-based early stopping is a built-in convergence criterion, not a user-provided custom stopper. `STOPPER_TRIGGERED` is reserved exclusively for objects implementing `StopperProtocol` passed via `stop_callbacks`.

## Rationale

- **Stdlib only**: All serialization logic stays in the domain layer with no external dependencies (respects ADR-000 hexagonal boundaries)
- **Frozen record**: Version is part of the immutable result — cannot be accidentally modified after creation
- **Forward compatible**: Explicit per-version migration ensures old results can always be loaded by newer code
- **`str` enum**: `StopReason(str, Enum)` enables direct JSON serialization (`json.dumps` works without custom encoder)
- **Protocol alignment**: Both new fields are added to `EvolutionResultProtocol` (ADR-013), maintaining the shared interface via structural subtyping

## Consequences

### Positive

- **Cross-session comparison**: Serialized results carry their schema version, enabling safe deserialization across GEPA-ADK versions
- **Diagnostic clarity**: Callers can inspect `result.stop_reason` to understand why evolution terminated, enabling better experiment analysis
- **Test strategy**: Migration test fixtures per schema version (`tests/fixtures/evolution_result_v1.json`) ensure backward compatibility as the schema evolves

### Negative

- **Field overhead**: Two additional fields on every result instance (minimal memory impact for frozen dataclasses)
- **Phased implementation**: `to_dict()`/`from_dict()` are deferred to Story 2.2, so schema_version is present but not yet used for serialization

### Neutral

- **Default values**: Both fields have defaults (`schema_version=1`, `stop_reason=COMPLETED`), so existing code that constructs result types without these fields continues to work unchanged

## Alternatives Considered

### 1. Pydantic Model Versioning

Use Pydantic's model validators for schema migration. Rejected because it introduces an external dependency in the domain layer, violating ADR-000 (hexagonal architecture — domain uses stdlib only).

### 2. Unversioned Serialization

Serialize results as plain dicts without version metadata. Rejected because it provides no forward-compatibility guarantee — adding or renaming a field in a future version would silently break deserialization of old results.

### 3. Separate Metadata Wrapper

Wrap results in a `ResultEnvelope(version=1, data=result)` container. Rejected because it adds indirection — the version belongs to the result itself (frozen record), not an external wrapper.

## References

- [ADR-000: Hexagonal Architecture](ADR-000-hexagonal-architecture.md)
- [ADR-002: Protocol-Based Interfaces](ADR-002-protocol-for-interfaces.md)
- [ADR-013: Result Type Unification](ADR-013-result-type-protocol.md)

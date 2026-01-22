# Research: Required Field Preservation for Output Schema Evolution

**Date**: 2026-01-22
**Feature**: 198-schema-field-preservation

## Research Questions

1. How should SchemaConstraints be structured as a domain model?
2. Where should constraint validation logic live (utils vs adapters)?
3. How to integrate with the existing OutputSchemaHandler.apply() pattern?
4. How to thread schema_constraints through the evolve() API to the handler?

---

## Decision 1: SchemaConstraints Domain Model Structure

**Decision**: Use a frozen dataclass in `domain/types.py` with optional fields for each constraint type.

**Rationale**:
- Follows existing patterns (`TrajectoryConfig`, `ComponentSpec`, `ProposalResult`) in `domain/types.py`
- Frozen dataclass ensures immutability during evolution
- Optional fields allow incremental adoption (start with `required_fields`, add `preserve_types` later)
- Domain layer has no external dependencies (stdlib only per ADR-000)

**Alternatives Considered**:

| Alternative | Rejected Because |
|-------------|------------------|
| Pydantic BaseModel | Domain layer cannot import pydantic (ADR-000) |
| TypedDict | No runtime validation, harder to extend |
| Plain dict | No type safety, error-prone |

**Structure**:
```python
@dataclass(frozen=True, slots=True)
class SchemaConstraints:
    """Constraints for output schema evolution."""
    required_fields: tuple[str, ...] = ()
    preserve_types: dict[str, type | tuple[type, ...]] = field(default_factory=dict)
```

---

## Decision 2: Validation Logic Location

**Decision**: Add validation function in `utils/schema_utils.py`, invoke from `OutputSchemaHandler.apply()`.

**Rationale**:
- `schema_utils.py` already contains schema serialization/deserialization
- Validation is a utility concern, not core domain logic
- `OutputSchemaHandler` in adapters/ orchestrates but delegates to utils
- Keeps handler simple (serialize → validate → apply or reject)

**Alternatives Considered**:

| Alternative | Rejected Because |
|-------------|------------------|
| Validation in domain/ | Domain has no external deps; validation needs Pydantic introspection |
| Validation in adapters/component_handlers.py | Would bloat handler; schema logic belongs in schema_utils |
| Separate validator class | Over-engineering; simple function suffices |

**Interface**:
```python
def validate_schema_against_constraints(
    proposed_schema: type[BaseModel],
    original_schema: type[BaseModel],
    constraints: SchemaConstraints,
) -> tuple[bool, list[str]]:
    """Validate proposed schema against constraints.

    Returns:
        (is_valid, list_of_violation_messages)
    """
```

---

## Decision 3: Handler Integration Pattern

**Decision**: Add optional `constraints` parameter to `OutputSchemaHandler`, set via a new `set_constraints()` method or constructor.

**Rationale**:
- `ComponentHandler` protocol doesn't change (backward compatible)
- Handler stores constraints as instance state
- `apply()` checks constraints before modifying agent
- Follows existing pattern where handlers are configured at registration

**Alternatives Considered**:

| Alternative | Rejected Because |
|-------------|------------------|
| Pass constraints through apply() | Protocol change; breaks existing implementations |
| Global registry of constraints | Implicit; hard to track per-evolution |
| Context parameter in serialize/apply/restore | Protocol change needed |

**Pattern**:
```python
class OutputSchemaHandler:
    def __init__(self):
        self._constraints: SchemaConstraints | None = None

    def set_constraints(self, constraints: SchemaConstraints | None) -> None:
        self._constraints = constraints

    def apply(self, agent, value) -> Any:
        original = getattr(agent, "output_schema", None)
        new_schema = deserialize_schema(value)

        if self._constraints and original:
            is_valid, violations = validate_schema_against_constraints(
                new_schema, original, self._constraints
            )
            if not is_valid:
                logger.warning("output_schema.constraint_violation", violations=violations)
                return original  # Reject mutation

        agent.output_schema = new_schema
        return original
```

---

## Decision 4: API Threading Pattern

**Decision**: Add `schema_constraints` parameter to `evolve()`, configure handler before evolution starts.

**Rationale**:
- Clean API: constraints are evolution-run scoped
- Handler configuration happens once at setup
- No changes to engine or proposer (validation is transparent)
- Constraints reset between runs (no leakage)

**Threading Path**:
```
evolve(schema_constraints=...)
  → if schema_constraints:
      handler = get_handler("output_schema")
      handler.set_constraints(schema_constraints)
  → ADKAdapter uses handler via get_handler()
  → OutputSchemaHandler.apply() validates against constraints
  → After evolution, handler.set_constraints(None) to reset
```

**Alternatives Considered**:

| Alternative | Rejected Because |
|-------------|------------------|
| Thread through EvolutionConfig | Config is for iteration/scoring params, not component-specific |
| Pass to ADKAdapter constructor | Adapter doesn't know about specific components |
| New evolved() function variant | API proliferation |

---

## Decision 5: Type Compatibility Rules

**Decision**: Support exact match or tuple of allowed types with explicit compatibility.

**Rationale**:
- `int` should satisfy `float` constraint (common numeric widening)
- User specifies `(float, int)` for numeric flexibility
- No implicit widening without explicit specification

**Rules**:
```python
preserve_types={"score": float}           # Only float allowed
preserve_types={"score": (float, int)}    # float or int allowed
preserve_types={"id": str}                # Only str allowed
```

**Type Checking**:
```python
def _is_type_compatible(actual: type, allowed: type | tuple[type, ...]) -> bool:
    if isinstance(allowed, tuple):
        return actual in allowed
    return actual == allowed
```

---

## Open Questions Resolved

| Question | Resolution |
|----------|------------|
| Validate at configuration time? | Yes - fail fast if constraints reference non-existent fields |
| What if original schema is None? | Skip validation (can't constrain nothing) |
| Log level for rejections? | WARNING (not ERROR - graceful degradation) |
| P3 bounds preservation? | Defer to future iteration (not in P1/P2 scope) |

---

## Implementation Order

1. **Domain**: Add `SchemaConstraints` dataclass to `domain/types.py`
2. **Utils**: Add `validate_schema_against_constraints()` to `utils/schema_utils.py`
3. **Adapters**: Modify `OutputSchemaHandler` to support constraints
4. **API**: Add `schema_constraints` parameter to `evolve()` and thread to handler
5. **Tests**: Contract → Unit → Integration (per ADR-005)
6. **Docs**: Update single-agent guide with constraints example

# Research: ComponentHandler Protocol and Registry

**Feature**: 162-component-handlers
**Date**: 2026-01-20
**Status**: Complete

## Research Tasks

### 1. Protocol Design Pattern (from established codebase patterns)

**Task**: Analyze existing protocol patterns in gepa-adk for consistency.

**Decision**: Use `@runtime_checkable` Protocol with structural subtyping.

**Rationale**:
- Established pattern in `ports/selector.py` with `CandidateSelectorProtocol`, `ComponentSelectorProtocol`, etc.
- Enables isinstance() checks for validation without inheritance
- Follows ADR-002: Protocol for Interfaces
- Google-style docstrings with Examples section per codebase convention

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| ABC inheritance | More boilerplate, less flexible, violates ADR-002 |
| Duck typing only | No runtime validation capability |
| dataclass-based | Not suitable for behavior-only contracts |

**Evidence**: `src/gepa_adk/ports/selector.py` lines 15-52 (CandidateSelectorProtocol pattern)

---

### 2. Registry Pattern Selection

**Task**: Determine optimal registry implementation for handler lookup.

**Decision**: Simple dict-based registry with module-level default instance.

**Rationale**:
- O(1) lookup via `dict[str, ComponentHandler]`
- Follows existing pattern in `adapters/component_selector.py` with factory function
- Module-level default allows convenience functions while supporting injection
- No external dependencies needed

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Class-based singleton | Over-engineered for simple use case |
| Plugin discovery (entry_points) | Overkill for internal handlers |
| Dependency injection framework | Adds unnecessary complexity |

**Evidence**: `src/gepa_adk/adapters/component_selector.py` lines 160-195 (factory pattern)

---

### 3. Handler Method Signatures

**Task**: Define optimal method signatures for serialize/apply/restore.

**Decision**: Sync methods with explicit typing and Any return for originals.

**Rationale**:
- Component manipulation is CPU-bound, not I/O-bound (no async needed)
- Current `_apply_candidate()` returns `tuple[str, Any]` - preserve flexibility
- `serialize(agent) -> str` for evolution text representation
- `apply(agent, value) -> Any` returns original for later restore
- `restore(agent, original) -> None` reinstates original state

**Method Signatures**:
```python
def serialize(self, agent: LlmAgent) -> str:
    """Extract component value from agent as string for evolution."""

def apply(self, agent: LlmAgent, value: str) -> Any:
    """Apply evolved value to agent, return original for restore."""

def restore(self, agent: LlmAgent, original: Any) -> None:
    """Restore original value after evaluation."""
```

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Async methods | No I/O involved; adds unnecessary complexity |
| Generic typing for original | Any provides needed flexibility, matches current code |
| Combined apply/restore context manager | Harder to integrate with existing try/finally pattern |

**Evidence**: `src/gepa_adk/adapters/adk_adapter.py` lines 422-490 (current implementation)

---

### 4. Handler Implementation Strategy

**Task**: Plan concrete handler implementations for instruction and output_schema.

**Decision**: Two initial handlers with distinct serialization strategies.

**InstructionHandler**:
- `serialize`: Return `str(agent.instruction)`
- `apply`: Set `agent.instruction = value`, return original
- `restore`: Set `agent.instruction = original`

**OutputSchemaHandler**:
- `serialize`: Use existing `serialize_schema()` utility
- `apply`: Use `deserialize_schema()`, set `agent.output_schema`, return original
- `restore`: Set `agent.output_schema = original`
- Handle `SchemaValidationError` gracefully (keep original on failure)

**Rationale**:
- Mirrors exact behavior in current `_apply_candidate()` method
- Reuses existing `serialize_schema`/`deserialize_schema` utilities
- Error handling preserves current fail-safe behavior

**Evidence**:
- `src/gepa_adk/adapters/adk_adapter.py` lines 438-466 (current apply logic)
- `src/gepa_adk/utils/schema_tools.py` (serialization utilities)

---

### 5. Error Handling Strategy

**Task**: Define error behavior for registry operations and handler methods.

**Decision**: Explicit exceptions with informative messages.

**Registry Errors**:
| Scenario | Exception | Message |
|----------|-----------|---------|
| Get non-existent handler | `KeyError` | `"No handler registered for component: {name}"` |
| Empty/None component name | `ValueError` | `"Component name must be a non-empty string"` |
| Non-protocol-compliant handler | `TypeError` | `"Handler does not implement ComponentHandler protocol"` |

**Handler Errors**:
- `serialize` with unset component: Return empty string (graceful default)
- `apply` with invalid value: Log warning, keep original (fail-safe)
- `restore` with None original: Reset to component's default state

**Rationale**:
- KeyError for missing items is Pythonic dict behavior
- ValueError/TypeError for invalid inputs follows stdlib conventions
- Graceful degradation matches current adapter behavior

**Evidence**: `src/gepa_adk/adapters/adk_adapter.py` lines 459-465 (current error handling)

---

### 6. Export and API Surface

**Task**: Determine public API exports.

**Decision**: Export protocol from ports/, implementations from adapters/.

**From `ports/__init__.py`**:
```python
from gepa_adk.ports.component_handler import ComponentHandler
```

**From `adapters/__init__.py`**:
```python
from gepa_adk.adapters.component_handlers import (
    ComponentHandlerRegistry,
    InstructionHandler,
    OutputSchemaHandler,
    component_handlers,  # default registry instance
    get_handler,
    register_handler,
)
```

**Rationale**:
- Follows hexagonal architecture: protocol in ports, implementations in adapters
- Convenience functions (`get_handler`, `register_handler`) for simple use cases
- Registry class exposed for advanced usage (custom registries)

**Evidence**: `src/gepa_adk/adapters/__init__.py` (existing export pattern)

---

## Summary

All research tasks complete. No NEEDS CLARIFICATION items remain.

**Key Decisions**:
1. `@runtime_checkable` Protocol with sync methods
2. Dict-based registry with module-level default instance
3. Three methods: serialize, apply, restore
4. Two initial handlers: InstructionHandler, OutputSchemaHandler
5. Explicit exceptions with informative messages
6. Exports split between ports/ (protocol) and adapters/ (implementations)

**Ready for Phase 1**: Data model and contract design.

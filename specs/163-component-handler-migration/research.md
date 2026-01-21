# Research: Component Handler Migration

**Feature**: 163-component-handler-migration
**Date**: 2026-01-20

## Overview

This research validates the feasibility of migrating ADKAdapter's hardcoded if/elif component handling to registry-based dispatch. Issue #162 has already established the ComponentHandler protocol and implementations—this feature rewires the adapter to use them.

## Research Tasks

### 1. ComponentHandler Protocol Review

**Task**: Verify the ComponentHandler protocol from #162 meets requirements.

**Decision**: The existing protocol is complete and suitable.

**Rationale**:
- Protocol defined in `ports/component_handler.py` with three methods:
  - `serialize(agent: LlmAgent) -> str`
  - `apply(agent: LlmAgent, value: str) -> Any`
  - `restore(agent: LlmAgent, original: Any) -> None`
- Uses `@runtime_checkable` for isinstance() validation
- Follows hexagonal architecture (protocol in ports/, implementations in adapters/)
- Documented with Google-style docstrings and examples

**Alternatives Considered**:
- None needed—protocol is already defined and tested

### 2. Handler Implementations Review

**Task**: Verify InstructionHandler and OutputSchemaHandler implementations.

**Decision**: Both handlers are implemented and registered in the default registry.

**Rationale**:
- `InstructionHandler` (lines 222-306 in component_handlers.py):
  - Serializes `agent.instruction` to string
  - Handles None instruction gracefully (returns empty string)
  - Returns original value for restoration
- `OutputSchemaHandler` (lines 308-419 in component_handlers.py):
  - Uses existing `serialize_pydantic_schema()` and `deserialize_schema()` utilities
  - Graceful degradation on deserialization failure (logs warning, keeps original)
  - Proper error handling via SchemaValidationError
- Both are registered at module load:
  ```python
  component_handlers.register(COMPONENT_INSTRUCTION, InstructionHandler())
  component_handlers.register(COMPONENT_OUTPUT_SCHEMA, OutputSchemaHandler())
  ```

**Alternatives Considered**:
- None needed—implementations are complete and tested in #162

### 3. Registry Access Pattern

**Task**: Determine best pattern for ADKAdapter to access handlers.

**Decision**: Import `get_handler` function from `component_handlers` module.

**Rationale**:
- `get_handler(name: str)` provides O(1) lookup from default registry
- Raises `KeyError` for unknown components (fail-fast behavior)
- Already exported in `__all__` of component_handlers.py
- Pattern matches existing codebase conventions

**Implementation**:
```python
from gepa_adk.adapters.component_handlers import get_handler

def _apply_candidate(self, candidate: dict[str, str]) -> dict[str, Any]:
    originals = {}
    for component_name, value in candidate.items():
        handler = get_handler(component_name)
        originals[component_name] = handler.apply(self.agent, value)
    return originals
```

**Alternatives Considered**:
1. Direct registry access (`component_handlers.get()`) - More verbose, no benefit
2. Injecting registry via constructor - Over-engineering for single adapter use case
3. Using `has()` check before `get()` - Unnecessary, fail-fast is appropriate

### 4. Return Type Changes

**Task**: Determine if `_apply_candidate` return type should change.

**Decision**: Change from `tuple[str, Any]` to `dict[str, Any]` for flexibility.

**Rationale**:
- Current signature: `tuple[str, Any]` (instruction, output_schema) - tightly coupled
- New signature: `dict[str, Any]` - component name → original value mapping
- Enables future component types without signature changes
- Matches the candidate input format (dict[str, str])
- `_restore_agent` receives same dict format for symmetric dispatch

**Migration**:
```python
# Before (coupled to specific components):
original_instruction, original_output_schema = self._apply_candidate(candidate)
self._restore_agent(original_instruction, original_output_schema)

# After (generic dispatch):
originals = self._apply_candidate(candidate)
self._restore_agent(originals)
```

**Alternatives Considered**:
1. Keep tuple, add elements as components grow - Breaks backward compat each time
2. NamedTuple with optional fields - Still coupled to component knowledge

### 5. Error Handling Strategy

**Task**: Determine error handling for unknown component names.

**Decision**: Let KeyError propagate for unknown components.

**Rationale**:
- Unknown component in candidate dict indicates programmer error (misconfiguration)
- Fail-fast behavior is appropriate for development/testing
- Handler's `apply()` already handles data errors gracefully (invalid schema text)
- Consistent with registry's documented behavior

**Alternatives Considered**:
1. Skip unknown components with warning - Masks errors, harder to debug
2. Catch KeyError and re-raise as custom exception - Adds complexity without benefit

### 6. Backward Compatibility Analysis

**Task**: Verify refactor maintains identical external behavior.

**Decision**: Refactor is fully backward compatible.

**Rationale**:
- `_apply_candidate` and `_restore_agent` are internal methods (underscore prefix)
- Public API (`evaluate()`, `make_reflective_dataset()`, `propose_new_texts()`) unchanged
- Candidate format (dict[str, str]) unchanged
- EvaluationBatch return format unchanged
- Handler behavior matches existing inline code:
  - InstructionHandler.apply() matches current instruction assignment
  - OutputSchemaHandler.apply() matches current schema deserialization + warning on failure

**Verification Plan**:
- All existing unit tests must pass without modification
- All existing contract tests must pass without modification
- All existing integration tests must pass without modification

**Alternatives Considered**:
- None—backward compatibility is non-negotiable per spec

## Summary

| Question | Decision | Confidence |
|----------|----------|------------|
| Protocol suitable? | Yes, use as-is | High |
| Handlers ready? | Yes, already registered | High |
| Registry access? | Use `get_handler()` | High |
| Return type? | Change to `dict[str, Any]` | High |
| Error handling? | Fail-fast on unknown components | High |
| Backward compat? | Full compatibility maintained | High |

## Implementation Approach

1. **Modify `_apply_candidate`**:
   - Change return type to `dict[str, Any]`
   - Loop over candidate items
   - Use `get_handler(component_name).apply()` for each
   - Collect originals in dict

2. **Modify `_restore_agent`**:
   - Change signature to accept `dict[str, Any]`
   - Loop over originals items
   - Use `get_handler(component_name).restore()` for each

3. **Update call sites in `evaluate()`**:
   - Adjust for new return type (dict instead of tuple)

4. **Add/update tests**:
   - Unit tests for registry dispatch
   - Verify existing tests still pass

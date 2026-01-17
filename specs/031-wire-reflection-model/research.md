# Research: Wire Reflection Model Config to Proposer

**Feature**: 031-wire-reflection-model
**Date**: 2026-01-17

## Research Tasks

This feature is a configuration wiring change with no unknowns in the Technical Context. Research focused on verifying existing code patterns and best practices.

### 1. Existing Parameter Passing Patterns

**Task**: How are other config parameters currently passed through the adapter chain?

**Findings**:
- `EvolutionConfig` is passed to `evolve()` and `evolve_group()` as a parameter
- Config values are extracted in the API functions and passed individually to adapters
- Example: `config.max_concurrent_evals` is passed to `ADKAdapter` constructor
- Pattern: API layer extracts config → passes named parameters → adapters receive as constructor args

**Decision**: Follow the same pattern for `reflection_model`

**Code Reference**:
```python
# api.py:evolve() - existing pattern
adapter = ADKAdapter(
    agent=agent,
    scorer=scorer,
    max_concurrent_evals=config.max_concurrent_evals,  # Config value passed through
    ...
)
```

### 2. AsyncReflectiveMutationProposer Model Parameter

**Task**: Verify the proposer already supports the `model` parameter

**Findings**:
- `AsyncReflectiveMutationProposer.__init__()` accepts `model: str = "ollama/gpt-oss:20b"` (line 400)
- Parameter is validated (non-empty check)
- Stored as `self.model` and used in `_call_litellm()` method
- No changes needed to proposer

**Decision**: Use existing `model` parameter - no proposer modifications required

**Code Reference**:
```python
# engine/proposer.py:398-400
def __init__(
    self,
    model: str = "ollama/gpt-oss:20b",
    ...
)
```

### 3. Logging Best Practices (per FR-003)

**Task**: How should the reflection model be logged at INFO level?

**Findings**:
- Project uses `structlog` for all logging (Constitution V. Observability)
- Existing pattern: `log = structlog.get_logger(__name__)` at module level
- INFO logs use `log.info("message", key=value, ...)` format
- Context binding is used for evolution context

**Decision**: Add INFO log in proposer `__init__` after model assignment:
```python
log.info("proposer_initialized", reflection_model=self.model)
```

**Rationale**: Logging in proposer (not adapter) because:
1. Single point of truth - proposer is where model is actually used
2. Works regardless of which adapter creates the proposer
3. Follows existing logging patterns in the codebase

### 4. ADKAdapter Three-Path Logic

**Task**: Understand the three paths for proposer creation in ADKAdapter

**Findings** (from `adk_adapter.py` lines 194-212):
1. **External proposer provided**: `if proposer is not None` → use it directly
2. **ADK reflection_agent provided**: `elif reflection_agent is not None` → create ADK-based proposer
3. **Default case**: `else` → create LiteLLM-based proposer (THIS is where `reflection_model` applies)

**Decision**: Only path 3 needs `reflection_model` because:
- Path 1: External proposer already configured by caller
- Path 2: ADK agent handles its own model internally
- Path 3: LiteLLM proposer needs the model string

**Code Change Pattern**:
```python
# Only in the default case:
else:
    self._proposer = AsyncReflectiveMutationProposer(model=reflection_model)
```

### 5. Backward Compatibility

**Task**: Ensure API changes don't break existing callers

**Findings**:
- Adapter constructors currently don't have `reflection_model` parameter
- Adding it with a default value maintains backward compatibility
- Recommend: `reflection_model: str = "gemini-2.0-flash"` (matching config default)

**Decision**: Add parameter with default value to maintain backward compatibility:
```python
def __init__(
    self,
    agent: LlmAgent,
    scorer: Scorer,
    ...,
    reflection_model: str = "gemini-2.0-flash",  # NEW - with default
):
```

**Rationale**: Existing code that doesn't pass `reflection_model` will get the config default, which is the expected behavior.

## Summary

| Research Area | Decision | Rationale |
|---------------|----------|-----------|
| Parameter passing | Follow existing config extraction pattern | Consistency with codebase |
| Proposer changes | None needed | Already supports `model` parameter |
| Logging | Add INFO log in proposer `__init__` | Single point of truth |
| ADKAdapter paths | Only modify default path (path 3) | Other paths don't use LiteLLM model |
| Backward compatibility | Default parameter value | Maintains existing API signatures |

## Alternatives Considered

### Alternative 1: Pass entire EvolutionConfig to adapters

**Rejected because**:
- Violates current pattern of extracting individual values
- Would increase adapter coupling to config structure
- Unnecessary for a single parameter

### Alternative 2: Add logging in API layer instead of proposer

**Rejected because**:
- Would require logging in multiple places (evolve, evolve_group)
- Proposer is the authoritative location where model is used
- Proposer already has structlog setup

### Alternative 3: Change EvolutionConfig default to match proposer default

**Accepted** (supersedes initial recommendation):
- Initial research recommended keeping `"gemini-2.0-flash"` as the documented, production-ready default
- Implementation updated `EvolutionConfig` to use `"ollama_chat/gpt-oss:20b"` as the default
- This change improves local and offline usability for open-source users
- `"gemini/gemini-2.5-flash"` remains the documented production recommendation for users with API access

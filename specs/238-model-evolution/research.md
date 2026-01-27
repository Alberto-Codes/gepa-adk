# Research: Model Evolution Support

**Feature**: 238-model-evolution
**Date**: 2026-01-27

## Research Questions Resolved

### 1. ADK Model Type Structure

**Question**: How does LlmAgent store its model reference?

**Decision**: `LlmAgent.model: Union[str, BaseLlm]` - a mutable Pydantic field

**Findings**:
- `LlmAgent` (Pydantic model) has `model: Union[str, BaseLlm] = ''` at line 192
- For string models: direct replacement works
- For `BaseLlm` subclasses: all have `model: str` attribute (line 41 of base_llm.py)
- `LiteLlm` extends `BaseLlm`, stores `**kwargs` in `_additional_args` (preserved on `.model` mutation)

**Source**: `.venv/Lib/site-packages/google/adk/agents/llm_agent.py`, `.venv/Lib/site-packages/google/adk/models/base_llm.py`

### 2. Wrapper Preservation Strategy

**Question**: How to change model name without losing custom wrapper configuration?

**Decision**: Duck-type on `.model` attribute and mutate in-place

**Rationale**:
- `BaseLlm` and all subclasses have `model: str` attribute
- Custom wrappers that extend `BaseLlm` also have this attribute
- Mutating `obj.model = "new-name"` preserves all other object state
- Both are Pydantic models without `frozen=True`, so mutation is allowed

**Alternatives Considered**:
1. ❌ Create new wrapper instance: Would lose `_additional_args` and custom config
2. ❌ Type-check for specific classes: Fragile, doesn't handle custom wrappers
3. ✅ Duck-type on `.model` attribute: Flexible, preserves all wrapper state

### 3. Component Handler Pattern

**Question**: How do existing component handlers work?

**Decision**: Follow `OutputSchemaHandler` pattern with constraints

**Findings**:
- `ComponentHandler` protocol: `serialize()`, `apply()`, `restore()` methods
- `OutputSchemaHandler` has `set_constraints()` for `SchemaConstraints`
- `ComponentHandlerRegistry` manages handler lookup by component name
- `apply()` should log warnings and keep original on validation failure (graceful degradation)

**Source**: `src/gepa_adk/ports/component_handler.py`, `src/gepa_adk/adapters/component_handlers.py`

### 4. Reflection Agent Registration

**Question**: How to pass `allowed_models` to reflection agent factory?

**Decision**: Use `functools.partial` to bake allowed_models into factory

**Rationale**:
- Factory signature is `(model: str) -> LlmAgent`
- `ComponentReflectionRegistry.register()` expects this signature
- `partial(create_model_reflection_agent, allowed_models=[...])` creates compatible factory

**Source**: `src/gepa_adk/engine/reflection_agents.py` - `ComponentReflectionRegistry` class

### 5. Model Resolution Flow

**Question**: How does ADK resolve model strings vs wrapped models?

**Decision**: Keep model evolution at string level, let existing `_resolve_model_for_agent()` handle wrapping

**Findings**:
- `_resolve_model_for_agent(model_string)` in `api.py` (lines 79-113)
- Native ADK patterns (gemini-*) → return string
- Other patterns → wrap with `LiteLlm(model=model_string)`
- Model evolution should evolve the string, not the wrapped object

**Implication**: ModelHandler serializes to string, applies string, and the resolution happens at execution time

## Technology Best Practices

### Pydantic Model Mutation

- Pydantic v2 models without `frozen=True` allow attribute mutation
- Use direct assignment: `obj.model = "new-value"`
- Both `LlmAgent` and `BaseLlm` allow mutation

### ComponentHandler Error Handling

Per ADR-008 and existing patterns:
- Log warnings with structlog on validation failure
- Keep original value (graceful degradation)
- Never raise exceptions from `apply()` - return original instead

### Constraint Validation Pattern

Following `SchemaConstraints` pattern:
- Frozen dataclass for immutability
- `tuple[str, ...]` for allowed values (immutable collection)
- Validation in handler's `apply()` method

## Resolved Clarifications

| Item | Resolution |
|------|------------|
| Opt-in behavior | `model_choices=None` means no model evolution |
| Empty list handling | Treat as opt-out (no model evolution) |
| Single model in list | Skip model evolution (no alternatives) |
| Current model inclusion | Auto-add to allowed_models if not present |
| Wrapper without `.model` | Log warning, skip model evolution |

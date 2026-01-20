# Research: Component-Aware Reflection Agents

**Feature**: 142-component-aware-reflection
**Date**: 2026-01-20

## Research Tasks

### 1. How does Google ADK handle output_schema validation?

**Decision**: ADK uses Pydantic's `model_validate_json()` at runtime when the agent produces output, and provides a `SetModelResponseTool` workaround when tools are present.

**Findings**:

1. **Runtime Validation** (llm_agent.py:830-838):
   ```python
   if self.output_schema:
       result = self.output_schema.model_validate_json(result).model_dump(
           exclude_none=True
       )
   ```
   ADK validates the LLM's JSON output against the Pydantic schema at runtime. If invalid, Pydantic raises a `ValidationError`.

2. **SetModelResponseTool Pattern** (set_model_response_tool.py):
   - When `output_schema` + `tools` are both present, ADK injects a `SetModelResponseTool`
   - This tool's signature is dynamically generated from the output_schema's fields
   - The tool validates input via `self.output_schema.model_validate(args)` (line 109)
   - **Key insight**: ADK uses a **tool** to enforce structured output when other tools are present

3. **Instruction Injection** (_output_schema_processor.py:57-64):
   ```python
   instruction = (
       'IMPORTANT: You have access to other tools, but you must provide '
       'your final response using the set_model_response tool with the '
       'required structured format...'
   )
   llm_request.append_instructions([instruction])
   ```
   ADK adds explicit instructions guiding the LLM to use the validation tool.

**Rationale**: This pattern is directly applicable to our use case. We can create a validation tool that wraps `validate_schema_text()` and let the reflection agent self-validate.

**Alternatives Considered**:
- Post-hoc validation only (current approach) - rejected because it wastes iterations on invalid proposals
- Pre-validation before LLM call - not applicable (can't validate before proposal exists)

---

### 2. How should we create the validation tool for reflection?

**Decision**: Use ADK's `FunctionTool` pattern - wrap `validate_schema_text()` in a simple function and let ADK handle the rest.

**Findings**:

1. **FunctionTool Pattern** (function_tool.py):
   - ADK's `FunctionTool` wraps any Python callable
   - Extracts function name, docstring, and signature for LLM
   - Handles both sync and async functions
   - Returns structured dicts including `{'error': ...}` for failures

2. **Tool Return Pattern**:
   ```python
   # From function_tool.py - error handling pattern
   return {'error': error_str}  # LLM sees this and can retry
   ```

3. **Our Implementation Approach**:
   ```python
   def validate_output_schema(schema_text: str) -> dict[str, Any]:
       """Validate a Pydantic schema definition.

       Args:
           schema_text: Python code defining a Pydantic BaseModel class.

       Returns:
           dict with 'valid' (bool) and 'errors' (list) or 'class_name' if valid.
       """
       try:
           result = validate_schema_text(schema_text)
           return {
               'valid': True,
               'class_name': result.class_name,
               'field_count': result.field_count,
               'field_names': list(result.field_names),
           }
       except SchemaValidationError as e:
           return {
               'valid': False,
               'errors': [str(e)],
               'stage': e.validation_stage,
               'line_number': e.line_number,
           }
   ```

**Rationale**: Using `FunctionTool` means we don't need to implement tool infrastructure - ADK handles function declaration generation, argument parsing, and invocation.

---

### 3. How should the reflection agent factory work?

**Decision**: Create factory functions that return fully-configured `LlmAgent` instances with appropriate tools and instructions.

**Findings**:

1. **Existing Reflection Pattern** (adk_reflection.py):
   - `create_adk_reflection_fn()` takes an agent and creates a reflection callable
   - The agent's instruction uses `{component_text}` and `{trials}` template placeholders
   - Output is extracted via `output_key` or event parsing

2. **Factory Pattern for Component-Aware Agents**:
   ```python
   def create_schema_reflection_agent(model: str) -> LlmAgent:
       """Create a reflection agent for output_schema components."""
       return LlmAgent(
           name="schema_reflector",
           model=model,
           instruction=SCHEMA_REFLECTION_INSTRUCTION,
           tools=[FunctionTool(validate_output_schema)],
           output_key="proposed_component_text",
       )

   def create_text_reflection_agent(model: str) -> LlmAgent:
       """Create a reflection agent for text components (no tools)."""
       return LlmAgent(
           name="text_reflector",
           model=model,
           instruction=REFLECTION_INSTRUCTION,
           output_key="proposed_component_text",
       )
   ```

3. **Registry Pattern**:
   ```python
   COMPONENT_REFLECTION_FACTORIES: dict[str, Callable[[str], LlmAgent]] = {
       "output_schema": create_schema_reflection_agent,
       # Future: "tools": create_tools_reflection_agent,
       # Future: "input_schema": create_input_schema_reflection_agent,
   }

   def get_reflection_agent(component_name: str, model: str) -> LlmAgent:
       """Get appropriate reflection agent for component type."""
       factory = COMPONENT_REFLECTION_FACTORIES.get(
           component_name,
           create_text_reflection_agent  # default
       )
       return factory(model)
   ```

**Rationale**: Factory pattern keeps agent creation separate from usage, enables easy testing, and allows future extension without modifying core code.

---

### 4. What instruction should guide schema validation tool usage?

**Decision**: Create `SCHEMA_REFLECTION_INSTRUCTION` that explicitly instructs the agent to validate before returning.

**Findings**:

ADK's instruction pattern (_output_schema_processor.py):
```python
'IMPORTANT: You have access to other tools, but you must provide '
'your final response using the set_model_response tool...'
```

**Our SCHEMA_REFLECTION_INSTRUCTION**:
```python
SCHEMA_REFLECTION_INSTRUCTION = '''## Component Text to Improve
{component_text}

## Trials
{trials}

## Instructions
Propose an improved version of the Pydantic schema based on the trials above.

IMPORTANT: Before returning your final answer, you MUST use the validate_output_schema
tool to verify your proposed schema is syntactically valid. If validation fails, fix
the errors and validate again until the schema is valid.

Return ONLY the improved Pydantic class definition (starting with "class"), nothing else.
Do not wrap in markdown code fences.'''
```

**Rationale**: Explicit instruction ensures the LLM uses the validation tool. ADK's own pattern demonstrates this approach works.

---

### 5. How to integrate with existing reflection flow?

**Decision**: Modify `create_adk_reflection_fn()` to accept an optional `component_name` parameter, and auto-select the appropriate reflection agent internally.

**Findings**:

1. **Current Signature**:
   ```python
   def create_adk_reflection_fn(
       reflection_agent: Any,
       executor: AgentExecutorProtocol,
       session_service: Any | None = None,
       output_key: str = "proposed_component_text",
       output_field: str | None = None,
   ) -> ReflectionFn
   ```

2. **Proposed Signature**:
   ```python
   def create_adk_reflection_fn(
       reflection_agent: Any | None = None,  # Optional - auto-select if None
       executor: AgentExecutorProtocol,
       session_service: Any | None = None,
       output_key: str = "proposed_component_text",
       output_field: str | None = None,
       model: str = "gemini-2.0-flash",  # For auto-creation
   ) -> ReflectionFn
   ```

3. **Integration Point**:
   The `ReflectionFn` signature needs to include `component_name`:
   ```python
   # Current
   ReflectionFn = Callable[[str, list[dict]], Awaitable[str]]

   # New (backward compatible)
   ReflectionFn = Callable[[str, list[dict], str], Awaitable[str]]
   #                        ^text  ^trials   ^component_name
   ```

4. **Proposer Change** (proposer.py:246-248):
   ```python
   # Current
   proposed_component_text = await self.adk_reflection_fn(component_text, trials)

   # New - pass component name
   proposed_component_text = await self.adk_reflection_fn(
       component_text, trials, component
   )
   ```

**Rationale**: Minimal API surface change while enabling component-aware behavior. Backward compatible since existing code can ignore the new parameter.

---

## Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Validation approach | ADK FunctionTool wrapping validate_schema_text() | Reuses existing validation, ADK handles tool mechanics |
| Agent creation | Factory functions returning configured LlmAgent | Separation of concerns, testable, extensible |
| Registry pattern | Dict mapping component names to factories | Simple, explicit, easy to extend |
| Instruction pattern | Explicit "MUST use validate tool" instruction | Matches ADK's own approach for output_schema + tools |
| Integration | Add component_name to ReflectionFn signature | Minimal change, backward compatible |

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/gepa_adk/engine/reflection_agents.py` | Create | Factory functions + registry |
| `src/gepa_adk/utils/schema_tools.py` | Create | validate_output_schema tool function |
| `src/gepa_adk/engine/proposer.py` | Modify | Pass component_name to reflection |
| `src/gepa_adk/engine/adk_reflection.py` | Modify | Accept component_name, auto-select agent |
| `tests/unit/engine/test_reflection_agents.py` | Create | Unit tests for factories |
| `tests/integration/test_schema_reflection.py` | Create | Integration test with real validation |

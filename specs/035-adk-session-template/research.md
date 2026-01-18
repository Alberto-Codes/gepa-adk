# Research: ADK Session State Template Substitution

**Date**: 2026-01-18
**Branch**: `035-adk-session-template`
**Objective**: Determine correct ADK template syntax for session state injection in agent instructions

## Research Summary

### Problem

The current reflection agent implementation in `adk_reflection.py` passes data via manual f-string construction in user messages. This works but bypasses ADK's native template substitution capability. GitHub Issue #99 requested exploration of ADK's session state templating.

### Key Finding

**The correct ADK template syntax is `{key}` (NOT `{state.key}` as assumed in the original spec).**

ADK automatically processes `{key}` placeholders in agent instructions against `session.state[key]` values.

## Research Task 1: Template Syntax Discovery

### Question
What is the correct template syntax for session state in ADK agent instructions?

### Source Code Evidence

**From `google.adk.utils.instructions_utils` (in .venv):**

```python
async def _replace_match(match) -> str:
    var_name = match.group().lstrip('{').rstrip('}').strip()
    optional = False
    if var_name.endswith('?'):
        optional = True
        var_name = var_name.removesuffix('?')
    if var_name.startswith('artifact.'):
        # artifact handling...
    else:
        if not _is_valid_state_name(var_name):
            return match.group()
        if var_name in invocation_context.session.state:
            value = invocation_context.session.state[var_name]
            if value is None:
                return ''
            return str(value)
        else:
            if optional:
                return ''
            else:
                raise KeyError(f'Context variable not found: `{var_name}`.')
```

The regex pattern used is `r'{+[^{}]*}+'` which matches `{variable_name}`.

### Decision

**Use `{key}` syntax for session state values.**

| Syntax | Valid | Example | Notes |
|--------|-------|---------|-------|
| `{key}` | Yes | `{component_text}` | Standard syntax |
| `{key?}` | Yes | `{component_text?}` | Optional - returns empty string if missing |
| `{state.key}` | No | N/A | Not supported |
| `{session.key}` | No | N/A | Not supported |

### Rationale
- ADK's `inject_session_state()` function expects simple `{key}` placeholders
- The `state.` prefix is implicit - ADK automatically looks up `session.state[key]`
- Optional syntax (`{key?}`) prevents KeyError when state key is missing

---

## Research Task 2: Template Injection Flow

### Question
How does ADK process template placeholders in agent instructions?

### Source Code Evidence

**From `google.adk.flows.llm_flows.instructions` (in .venv):**

```python
async def _process_agent_instruction(
    self, agent, invocation_context: InvocationContext
) -> str:
    """Process agent instruction with state injection."""
    raw_si, bypass_state_injection = await agent.canonical_instruction(
        ReadonlyContext(invocation_context)
    )
    si = raw_si
    if not bypass_state_injection:
        si = await instructions_utils.inject_session_state(
            raw_si, ReadonlyContext(invocation_context)
        )
    return si
```

### Decision

**Template injection is automatic.** No additional code needed beyond:
1. Define agent instruction with `{key}` placeholders
2. Populate session state with corresponding keys before running agent
3. ADK automatically injects values during instruction processing

### Flow Diagram

```text
1. Session created with state:
   session_service.create_session(state={"component_text": "...", "trials": "..."})

2. Agent instruction defined:
   instruction = "Improve: {component_text}\nTrials: {trials}"

3. Runner.run_async() called
   └── _process_agent_instruction()
       └── inject_session_state(instruction, context)
           └── For each {key} placeholder:
               └── Replace with session.state[key]

4. LLM receives processed instruction:
   "Improve: <actual component text>\nTrials: <actual trials JSON>"
```

---

## Research Task 3: State Prefixes and Advanced Features

### Question
What additional template features does ADK support?

### Source Code Evidence

**From `google.adk.sessions.state` (in .venv):**

```python
class State:
  """A state dict that maintains the current value and the pending-commit delta."""

  APP_PREFIX = "app:"
  USER_PREFIX = "user:"
  TEMP_PREFIX = "temp:"
```

**From `instructions_utils._is_valid_state_name()`:**

```python
def _is_valid_state_name(var_name):
    parts = var_name.split(':')
    if len(parts) == 1:
        return var_name.isidentifier()
    if len(parts) == 2:
        prefixes = [State.APP_PREFIX, State.USER_PREFIX, State.TEMP_PREFIX]
        if (parts[0] + ':') in prefixes:
            return parts[1].isidentifier()
    return False
```

### Decision

**Supported template features:**

| Feature | Syntax | Description |
|---------|--------|-------------|
| Simple key | `{key}` | Looks up `session.state[key]` |
| Optional key | `{key?}` | Returns empty string if missing |
| App-scoped | `{app:key}` | Application-level state |
| User-scoped | `{user:key}` | User-level state |
| Temp-scoped | `{temp:key}` | Temporary session state |
| Artifact | `{artifact.filename}` | Load artifact content |

**For this feature**: Use simple `{key}` and `{key?}` syntax. Prefixed state keys are for advanced multi-session scenarios not needed for reflection agents.

---

## Research Task 4: Type Handling

### Question
How does ADK handle non-string session state values?

### Source Code Evidence

From `_replace_match()`:
```python
value = invocation_context.session.state[var_name]
if value is None:
    return ''
return str(value)
```

### Decision

**All values are converted to strings via `str(value)`.**

| State Value Type | Template Result |
|------------------|-----------------|
| `str` | Value as-is |
| `None` | Empty string `""` |
| `dict` | Python dict repr (NOT JSON) |
| `list` | Python list repr |
| `int`, `float` | String conversion |

**Important**: For complex types like `trials` (dict/list), pre-serialize to JSON string before setting session state:
```python
session_state = {
    "component_text": component_text,
    "trials": json.dumps(trials, indent=2),  # Pre-serialize
}
```

---

## Research Task 5: Error Handling

### Question
How does ADK handle missing or invalid template keys?

### Source Code Evidence

From `_replace_match()`:
```python
if var_name in invocation_context.session.state:
    value = invocation_context.session.state[var_name]
    # ... return value
else:
    if optional:
        logger.debug(
            'Context variable %s not found, replacing with empty string',
            var_name,
        )
        return ''
    else:
        raise KeyError(f'Context variable not found: `{var_name}`.')
```

### Decision

**Error handling strategy:**

| Scenario | `{key}` Behavior | `{key?}` Behavior |
|----------|------------------|-------------------|
| Key exists | Substitute value | Substitute value |
| Key missing | Raise `KeyError` | Return empty string |
| Invalid key name | Leave placeholder unchanged | Leave placeholder unchanged |

**For reflection agents**: Use required syntax `{key}` since both `component_text` and `trials` are always provided. The KeyError serves as a fail-fast mechanism if session state is incorrectly configured.

---

## Implementation Recommendation

### Current Implementation (workaround)

```python
# From adk_reflection.py lines 205-214
user_message = f"""## Component Text to Improve
{component_text}

## Trials
{json.dumps(trials, indent=2)}

Propose an improved version of the component text based on the trials above.
Return ONLY the improved component text, nothing else."""
```

### Proposed Implementation (using templates)

```python
# Agent instruction with templates
REFLECTION_INSTRUCTION = """## Component Text to Improve
{component_text}

## Trials
{trials}

Propose an improved version of the component text based on the trials above.
Return ONLY the improved component text, nothing else."""

# Create agent with templated instruction
reflection_agent = LlmAgent(
    name="Reflector",
    model=model,
    instruction=REFLECTION_INSTRUCTION,
)

# Session state (pre-serialize complex types)
session_state = {
    "component_text": component_text,
    "trials": json.dumps(trials, indent=2),
}

# Run with minimal user message
async for event in runner.run_async(
    user_id="reflection",
    session_id=session_id,
    new_message=Content(
        role="user",
        parts=[Part(text="Please improve the component text.")],
    ),
):
    events.append(event)
```

### Benefits

1. **Cleaner separation**: Data in session state, task in user message
2. **ADK-native**: Uses documented ADK patterns
3. **Testable**: Session state can be inspected/mocked independently
4. **Consistent**: Aligns with other ADK agents using template substitution

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Template syntax undocumented | Verified in ADK source code; tested locally |
| Model provider differences | Integration tests across Gemini, Ollama, OpenAI |
| Breaking existing behavior | Feature flag or gradual rollout option |

---

## Spec Update Required

The original spec assumed `{state.key}` syntax. Update to:
- **FR-001**: Change `{state.key}` to `{key}` in all references
- **User Stories**: Update placeholder examples to `{component_text}` not `{state.component_text}`

## References

### ADK Source Files (in .venv)

- `google/adk/utils/instructions_utils.py` - Template injection implementation
- `google/adk/flows/llm_flows/instructions.py` - Template integration in flow
- `google/adk/sessions/state.py` - State prefix definitions

### Project Files

- `src/gepa_adk/engine/adk_reflection.py` - Current implementation
- `specs/034-adk-ollama-reflection/research.md` - Previous research on data passing

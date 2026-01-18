# Research: ADK Session State Management

**Feature**: 122-adk-session-state
**Date**: 2026-01-18
**Status**: Complete

## 1. ADK output_key Mechanism

### Decision
Use ADK's native `output_key` parameter on `LlmAgent` for automatic output storage in session state.

### Rationale
- **Built-in feature**: `output_key` is a first-class citizen in ADK's `LlmAgent` (google-adk 1.22.0+)
- **Automatic storage**: ADK automatically stores agent output to `session.state[output_key]` on final response
- **Thought filtering**: ADK excludes thought/reasoning parts (`part.thought=True`) from stored output
- **Schema support**: Works with `output_schema` for structured JSON output validation

### ADK Implementation Details

From `.venv/lib/python3.12/site-packages/google/adk/agents/llm_agent.py`:

```python
# Line 326-332
output_key: Optional[str] = None
"""The key in session state to store the output of the agent.

Typically use cases:
- Extracts agent reply for later use, such as in tools, callbacks, etc.
- Connects agents to coordinate with each other.
"""

# Lines 818-839: How output is stored
if (
    self.output_key
    and event.is_final_response()
    and event.content
    and event.content.parts
):
    result = ''.join(
        part.text
        for part in event.content.parts
        if part.text and not part.thought  # Filters out reasoning
    )
    if self.output_schema:
        result = self.output_schema.model_validate_json(result).model_dump(
            exclude_none=True
        )
    event.actions.state_delta[self.output_key] = result
```

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Manual extraction from events | Duplicates ADK functionality; error-prone |
| Custom callback to capture output | Unnecessary complexity; output_key does this |
| Parse final message content | Already done by ADK's output_key mechanism |

---

## 2. ADK State Templating

### Decision
Use ADK's `inject_session_state()` for instruction template substitution with `{key}` syntax.

### Rationale
- **Native feature**: ADK provides `inject_session_state()` in `google.adk.utils.instructions_utils`
- **Automatic invocation**: ADK calls this during instruction processing for LlmAgent
- **Flexible syntax**: Supports `{key}`, `{key?}` (optional), and `{artifact.filename}`
- **State prefixes**: Supports `app:`, `user:`, `temp:` prefixes for scoped state

### ADK Implementation Details

From `.venv/lib/python3.12/site-packages/google/adk/utils/instructions_utils.py`:

```python
async def inject_session_state(
    template: str,
    readonly_context: ReadonlyContext,
) -> str:
    """Populates values in the instruction template, e.g. state, artifact, etc.

    e.g. 'You can inject a state variable like {var_name} or an artifact
    {artifact.file_name} into the instruction template.'
    """
    # Key behavior (lines 106-122):
    if var_name in invocation_context.session.state:
        value = invocation_context.session.state[var_name]
        if value is None:
            return ''
        return str(value)
    else:
        if optional:  # {var_name?} syntax
            return ''  # Silent empty string
        else:
            raise KeyError(f'Context variable not found: `{var_name}`.')
```

### Template Syntax

| Syntax | Behavior |
|--------|----------|
| `{key}` | Required - raises `KeyError` if missing |
| `{key?}` | Optional - returns empty string if missing |
| `{artifact.name}` | Load from artifact service |
| `{app:key}` | App-scoped state |
| `{user:key}` | User-scoped state |
| `{temp:key}` | Temp-scoped state |

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Python f-string formatting | Requires runtime string manipulation; not ADK-native |
| Jinja2 templates | External dependency; ADK already provides templating |
| Manual instruction construction | Defeats purpose of ADK state management |

---

## 3. Session State Lifecycle

### Decision
Use `InMemorySessionService` with unique session IDs per reflection operation.

### Rationale
- **Isolation**: Each reflection gets isolated state (no cross-contamination)
- **Simplicity**: No persistence needed for reflection operations
- **Existing pattern**: Already used in `adk_reflection.py` and `multi_agent.py`

### Session Creation Pattern

```python
# From adk_reflection.py (lines 250-261)
session_state: dict[str, Any] = {
    "component_text": component_text,
    "trials": json.dumps(trials),
}

await session_service.create_session(
    app_name="gepa_reflection",
    user_id="reflection",
    session_id=session_id,  # Unique per operation
    state=session_state,    # Pre-populated
)
```

### State Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Create Session with Initial State                        │
│    session.state = {component_text, trials}                 │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. ADK Template Substitution (automatic)                    │
│    instruction = "Improve {component_text}..."              │
│    → resolved from session.state["component_text"]          │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Agent Execution                                          │
│    - Processes input                                        │
│    - Generates response                                     │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. ADK Stores Output (automatic if output_key set)          │
│    event.actions.state_delta[output_key] = response         │
│    → session.state[output_key] updated                      │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Retrieve Output from State                               │
│    if output_key in session.state:                          │
│        return session.state[output_key]                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Existing Implementation Analysis

### Current State in gepa-adk

| File | Current State | Changes Needed |
|------|--------------|----------------|
| `engine/adk_reflection.py` | ✅ Uses session state for input injection | Add output_key config, use shared extractor |
| `engine/proposer.py` | ✅ Accepts adk_reflection_fn | No changes - interface unchanged |
| `adapters/multi_agent.py` | ✅ Has output_key extraction (inline) | Refactor to use shared extractor |
| `utils/events.py` | ✅ extract_final_output exists | Add extract_output_from_state() |

### Existing output_key Pattern (from multi_agent.py)

```python
# Lines 356-360 - CURRENT inline implementation
def _extract_primary_output(
    self, pipeline_output: str, session_state: dict[str, Any], primary_agent: LlmAgent
) -> str:
    if hasattr(primary_agent, "output_key") and primary_agent.output_key:
        output_key = primary_agent.output_key
        if output_key in session_state:
            return str(session_state[output_key])
    return pipeline_output  # Fallback
```

---

## 4.1 Shared Utility Decision

### Problem

Both `engine/adk_reflection.py` and `adapters/multi_agent.py` need output_key extraction logic.

### Constraint

Per Constitution §I (Hexagonal Architecture) and ADR-000:
- **engine/** layer CANNOT import from **adapters/** layer
- Import rules: `engine/ → ports/, domain/` only (receives adapters via injection)

Importing extraction logic from `multi_agent.py` into `adk_reflection.py` would **violate hexagonal architecture**.

### Decision

Extract shared logic to `utils/events.py`:

```python
# NEW function in utils/events.py
def extract_output_from_state(
    session_state: dict[str, Any],
    output_key: str | None,
    fallback: str = "",
) -> str | None:
    """Extract output from session state using output_key.

    Args:
        session_state: ADK session state dictionary.
        output_key: Key where agent stored its output, or None.
        fallback: Default value if extraction fails.

    Returns:
        Output string if found in state, None otherwise (caller should fallback).
    """
    if not output_key:
        return None
    if output_key in session_state:
        value = session_state[output_key]
        if value is not None:
            return str(value)
    return None
```

### Rationale

| Principle | How This Complies |
|-----------|-------------------|
| **DRY** | Single implementation, no duplication |
| **Hexagonal** | `utils/` accessible from both adapters/ and engine/ |
| **Separation of Concerns** | Extraction logic separate from business logic |
| **Cohesion** | Complements existing `extract_final_output()` in same module |

### Impact

| File | Change |
|------|--------|
| `utils/events.py` | ADD `extract_output_from_state()` |
| `adapters/multi_agent.py` | REFACTOR `_extract_primary_output()` to use shared utility |
| `engine/adk_reflection.py` | USE shared utility for state extraction |

---

## 5. Implementation Approach

### Phase 1: Add Shared Utility

**File**: `src/gepa_adk/utils/events.py`

Add `extract_output_from_state()` alongside existing `extract_final_output()`:

```python
def extract_output_from_state(
    session_state: dict[str, Any],
    output_key: str | None,
) -> str | None:
    """Extract output from session state using output_key.

    Returns None if extraction fails (caller should fallback).
    """
    if not output_key:
        return None
    if output_key in session_state:
        value = session_state[output_key]
        if value is not None:
            return str(value)
    return None
```

### Phase 2: Configure output_key on Reflection Agent

**File**: `src/gepa_adk/engine/adk_reflection.py`

1. Add `output_key` parameter to `create_adk_reflection_fn()` factory
2. Default to `"proposed_component_text"` for consistent state key
3. Use shared `extract_output_from_state()` for retrieval

```python
from gepa_adk.utils.events import extract_final_output, extract_output_from_state

def create_adk_reflection_fn(
    reflection_agent: Any,
    session_service: Any | None = None,
    output_key: str = "proposed_component_text",  # NEW parameter
) -> ReflectionFn:
    # Ensure agent has output_key configured
    if not hasattr(reflection_agent, 'output_key') or not reflection_agent.output_key:
        reflection_agent.output_key = output_key
```

### Phase 3: State-Based Output Retrieval

**File**: `src/gepa_adk/engine/adk_reflection.py`

```python
# After runner.run_async completes
session = await session_service.get_session(
    app_name="gepa_reflection",
    user_id="reflection",
    session_id=session_id,
)

# Use shared utility with fallback
proposed_component_text = None
if session:
    proposed_component_text = extract_output_from_state(session.state, output_key)

if proposed_component_text is None:
    # Fallback to existing extract_final_output
    proposed_component_text = extract_final_output(events)
```

### Phase 4: Refactor multi_agent.py

**File**: `src/gepa_adk/adapters/multi_agent.py`

Refactor `_extract_primary_output()` to use shared utility:

```python
from gepa_adk.utils.events import extract_output_from_state

def _extract_primary_output(
    self, pipeline_output: str, session_state: dict[str, Any], primary_agent: LlmAgent
) -> str:
    # Use shared utility
    output_key = getattr(primary_agent, "output_key", None)
    result = extract_output_from_state(session_state, output_key)
    if result is not None:
        return result
    return pipeline_output  # Fallback
```

---

## 6. Edge Cases and Error Handling

| Scenario | Handling |
|----------|----------|
| output_key not set on agent | Fallback to event-based extraction |
| output_key not in session state | Fallback to event-based extraction |
| Session retrieval fails | Fallback to event-based extraction |
| Empty output in state | Return empty string (existing behavior) |
| Agent fails mid-execution | Propagate exception (existing behavior) |

---

## 7. Testing Strategy

### Unit Tests
- Mock session service and verify output_key storage
- Test fallback when output_key missing
- Test template substitution with session state

### Integration Tests
- Real ADK agent with output_key configured
- Verify end-to-end state flow
- Multi-agent workflow with shared state

### Contract Tests
- ReflectionFn protocol compliance unchanged
- Backward compatibility with existing callers

---

## 8. References

- ADK Source: `.venv/lib/python3.12/site-packages/google/adk/agents/llm_agent.py` (lines 326-332, 818-839)
- ADK Templating: `.venv/lib/python3.12/site-packages/google/adk/utils/instructions_utils.py`
- Existing pattern: `src/gepa_adk/adapters/multi_agent.py` (lines 356-360)
- Current implementation: `src/gepa_adk/engine/adk_reflection.py`

# Research: Wire ADK Reflection Agent into evolve() API

**Feature Branch**: `021-adk-reflection-evolve`
**Date**: 2026-01-14

## Executive Summary

This feature has minimal unknowns because the core infrastructure already exists and is fully implemented. The research confirms that wiring is straightforward with no architectural decisions required.

## Research Questions

### Q1: How does create_adk_reflection_fn() integrate with AsyncReflectiveMutationProposer?

**Decision**: Use existing integration pattern - proposer already accepts `adk_reflection_fn` parameter.

**Rationale**: The `AsyncReflectiveMutationProposer.__init__()` already accepts `adk_reflection_fn: ReflectionFn | None = None` (proposer.py:302). The `propose()` method checks if `adk_reflection_fn` is provided and uses it for reflection (proposer.py:420-423), otherwise falls back to LiteLLM.

**Alternatives Considered**:
- Creating a new proposer class - rejected as unnecessary; existing class already supports both modes
- Modifying the Proposer protocol - rejected; no protocol change needed

### Q2: Where should the ADK reflection function be created in the call chain?

**Decision**: Create `adk_reflection_fn` in ADKAdapter when `reflection_agent` is provided.

**Rationale**: ADKAdapter is the integration point between the public API and the engine components. It already creates the default proposer (adk_adapter.py:171). Adding reflection agent support here follows the existing pattern and keeps the API layer clean.

**Flow**:
```
evolve(reflection_agent=my_agent)
    ↓
ADKAdapter(reflection_agent=reflection_agent)
    ↓
adk_reflection_fn = create_adk_reflection_fn(reflection_agent)
    ↓
AsyncReflectiveMutationProposer(adk_reflection_fn=adk_reflection_fn)
```

**Alternatives Considered**:
- Create in api.py and pass callable to adapter - rejected; creates tight coupling between API and engine
- Create in engine layer - rejected; ADKAdapter already handles proposer creation

### Q3: How should errors from invalid reflection_agent be handled?

**Decision**: Validate in ADKAdapter.__init__() using existing TypeError pattern.

**Rationale**: ADKAdapter already validates `agent` with TypeError if not LlmAgent (adk_adapter.py:148-149). Same pattern applies to `reflection_agent`.

**Error Messages**:
- Invalid type: `TypeError: reflection_agent must be LlmAgent, got {type}`
- Note: `create_adk_reflection_fn()` also validates type (proposer.py:98-99)

**Alternatives Considered**:
- Validate in api.py - rejected; adapter is responsible for integration validation
- Silent fallback to LiteLLM on error - rejected; hides configuration mistakes

### Q4: How is session state managed for the reflection agent?

**Decision**: Use existing session state management in `create_adk_reflection_fn()`.

**Rationale**: The factory function already handles session creation, state initialization, and cleanup (proposer.py:136-262). Session state includes:
- `current_instruction` (str): The instruction being improved
- `execution_feedback` (JSON-serialized list): Evaluation results

No changes needed - existing implementation is complete.

### Q5: What logging changes are needed?

**Decision**: Remove warning, add success logging.

**Rationale**: Current code logs warning "not yet implemented" (api.py:842-846). Replace with:
1. Remove warning in api.py
2. Add debug log when reflection_agent is provided: `"evolve.reflection_agent.configured"`
3. Proposer already logs reflection operations (proposer.py logs)

## Dependencies Verified

| Dependency | Status | Location |
|------------|--------|----------|
| `create_adk_reflection_fn()` | Implemented | src/gepa_adk/engine/proposer.py:74 |
| `AsyncReflectiveMutationProposer` with `adk_reflection_fn` | Implemented | src/gepa_adk/engine/proposer.py:265 |
| `ReflectionFn` type alias | Defined | src/gepa_adk/engine/proposer.py:39 |
| ADK Runner integration | Implemented | src/gepa_adk/engine/proposer.py:142 |
| Session state management | Implemented | src/gepa_adk/engine/proposer.py:44-52 |

## Implementation Summary

### Files to Modify

1. **src/gepa_adk/api.py**
   - Remove warning log (lines 840-846)
   - Pass `reflection_agent` to ADKAdapter constructor
   - Add debug log for reflection_agent configuration

2. **src/gepa_adk/adapters/adk_adapter.py**
   - Add `reflection_agent: LlmAgent | None = None` parameter to `__init__`
   - Validate reflection_agent type if provided
   - Call `create_adk_reflection_fn(reflection_agent)` if provided
   - Pass `adk_reflection_fn` to proposer constructor

### Files to Add

1. **tests/unit/test_api_reflection.py** (or extend test_api.py)
   - Test evolve() with reflection_agent parameter
   - Test default behavior without reflection_agent
   - Test invalid reflection_agent raises TypeError

2. **tests/integration/test_adk_reflection_integration.py**
   - Integration test with real ADK LlmAgent for reflection
   - Mark with `@pytest.mark.slow` per constitution

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing behavior | Low | High | Test default path (no reflection_agent) explicitly |
| Session state issues | Low | Medium | Existing tests cover create_adk_reflection_fn() |
| Import cycles | Low | Low | create_adk_reflection_fn is in engine layer, accessible from adapters |

## Reference Implementations

### GEPA (Dev Dependency - Inspiration)

**Location**: `.venv/lib/python3.12/site-packages/gepa/`

GEPA's `ReflectiveMutationProposer` provides the pattern our implementation follows:

**LanguageModel Protocol** (`gepa/proposer/reflective_mutation/base.py:27-28`):
```python
class LanguageModel(Protocol):
    def __call__(self, prompt: str) -> str: ...
```

This is analogous to our `ReflectionFn` type alias. GEPA uses a simple callable protocol.

**ReflectiveMutationProposer** (`gepa/proposer/reflective_mutation/reflective_mutation.py:32-44`):
```python
def __init__(
    self,
    ...
    reflection_lm: LanguageModel | None = None,
    reflection_prompt_template: str | None = None,
):
```

Key pattern: The proposer accepts an optional `reflection_lm` parameter. If not provided, it expects the adapter to handle proposal generation (line 66-67):
```python
if self.adapter.propose_new_texts is not None:
    return self.adapter.propose_new_texts(candidate, reflective_dataset, components_to_update)
```

**Relevance**: Our `AsyncReflectiveMutationProposer` follows the same pattern with `adk_reflection_fn`. GEPA validates our architectural approach.

### ADK Runner (Source Dependency)

**Location**: `.venv/lib/python3.12/site-packages/google/adk/runners.py`

The ADK `Runner` class manages agent execution with session management:

**Runner Class** (`runners.py:100-196`):
```python
class Runner:
    """The Runner class is used to run agents."""

    def __init__(
        self,
        *,
        agent: Optional[BaseAgent] = None,
        session_service: BaseSessionService,
        ...
    ):
```

**run_async Method** (`runners.py:407`): The async entry point for running agents.

**Relevance**: Our `create_adk_reflection_fn()` uses `Runner.run_async()` (proposer.py:142) to execute the reflection agent. This confirms correct ADK integration pattern.

### Key Insights from Dependencies

| Pattern | GEPA | gepa-adk | Notes |
|---------|------|----------|-------|
| Reflection callable | `LanguageModel` protocol | `ReflectionFn` type alias | Both use simple callable signatures |
| Optional reflection | `reflection_lm: LanguageModel \| None` | `adk_reflection_fn: ReflectionFn \| None` | Same optional pattern |
| Fallback behavior | Delegate to adapter or raise | Fall back to LiteLLM | gepa-adk has built-in fallback |
| Session management | Not applicable (sync) | ADK InMemorySessionService | gepa-adk uses ADK's session model |

## Conclusion

All research questions resolved. No blockers identified. Implementation is straightforward wiring of existing components.

The GEPA dependency validates our architectural approach - the reflection callable pattern is proven. The ADK Runner pattern is correctly used in our existing `create_adk_reflection_fn()` implementation.

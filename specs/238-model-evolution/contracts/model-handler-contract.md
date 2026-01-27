# Contract: ModelHandler

**Protocol**: `ComponentHandler` (from `gepa_adk.ports.component_handler`)
**Implementation**: `ModelHandler` (in `gepa_adk.adapters.component_handlers`)

## Protocol Requirements

```python
@runtime_checkable
class ComponentHandler(Protocol):
    def serialize(self, agent: LlmAgent) -> str: ...
    def apply(self, agent: LlmAgent, value: str) -> Any: ...
    def restore(self, agent: LlmAgent, original: Any) -> None: ...
```

## Contract Tests

### CT-001: Protocol Compliance

**Precondition**: ModelHandler instance created
**Action**: `isinstance(handler, ComponentHandler)`
**Expected**: `True`

### CT-002: Serialize String Model

**Precondition**: Agent with `model="gemini-2.5-flash"` (string)
**Action**: `handler.serialize(agent)`
**Expected**: `"gemini-2.5-flash"`

### CT-003: Serialize Wrapped Model

**Precondition**: Agent with `model=LiteLlm(model="ollama_chat/llama3")`
**Action**: `handler.serialize(agent)`
**Expected**: `"ollama_chat/llama3"`

### CT-004: Apply Valid Model (String)

**Precondition**:
- Agent with `model="model-a"` (string)
- Handler constraints: `allowed_models=("model-a", "model-b")`
**Action**: `handler.apply(agent, "model-b")`
**Expected**:
- Returns `("string", "model-a")`
- `agent.model == "model-b"`

### CT-005: Apply Valid Model (Wrapper)

**Precondition**:
- Agent with `model=LiteLlm(model="model-a", custom_arg="preserved")`
- Handler constraints: `allowed_models=("model-a", "model-b")`
**Action**: `handler.apply(agent, "model-b")`
**Expected**:
- Returns `("wrapper", "model-a")`
- `agent.model.model == "model-b"`
- `agent.model._additional_args["custom_arg"] == "preserved"` (wrapper preserved)

### CT-006: Apply Invalid Model (Constraint Violation)

**Precondition**:
- Agent with `model="model-a"`
- Handler constraints: `allowed_models=("model-a", "model-b")`
**Action**: `handler.apply(agent, "model-c")`
**Expected**:
- Returns `None`
- `agent.model == "model-a"` (unchanged)
- Warning logged

### CT-007: Restore String Model

**Precondition**:
- Agent with `model="model-b"` (after apply)
- Original from apply: `("string", "model-a")`
**Action**: `handler.restore(agent, ("string", "model-a"))`
**Expected**: `agent.model == "model-a"`

### CT-008: Restore Wrapper Model

**Precondition**:
- Agent with wrapped model (model attribute = "model-b")
- Original from apply: `("wrapper", "model-a")`
**Action**: `handler.restore(agent, ("wrapper", "model-a"))`
**Expected**: `agent.model.model == "model-a"`

### CT-009: Restore After Constraint Violation

**Precondition**: Original from apply was `None`
**Action**: `handler.restore(agent, None)`
**Expected**: No-op, no exception

### CT-010: No Constraints Set (Accept All)

**Precondition**:
- Agent with `model="model-a"`
- Handler constraints: `None` (not set)
**Action**: `handler.apply(agent, "any-model")`
**Expected**:
- Returns restore info (not `None`)
- Model changed to "any-model"

## Invariants

1. **Roundtrip**: `serialize()` → `apply()` → `restore()` returns agent to original state
2. **Wrapper Preservation**: After `apply()`, wrapper object identity unchanged (same object)
3. **Graceful Degradation**: `apply()` never raises exceptions, returns `None` on failure
4. **Constraint Enforcement**: Invalid models rejected when constraints set

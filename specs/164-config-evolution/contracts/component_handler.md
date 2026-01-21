# Contract: GenerateContentConfigHandler

**Protocol**: `ComponentHandler` (ports/component_handler.py)
**Implementation**: `GenerateContentConfigHandler` (adapters/component_handlers.py)

## Protocol Compliance

The handler MUST implement all three protocol methods:

### serialize(agent: LlmAgent) -> str

**Preconditions**:
- `agent` is a valid LlmAgent instance

**Postconditions**:
- Returns YAML string representation of config
- Returns empty string if `agent.generate_content_config` is None
- Never raises exceptions (logs warnings on serialization failure)

**Contract Tests**:
```python
def test_serialize_returns_string():
    handler = GenerateContentConfigHandler()
    result = handler.serialize(agent)
    assert isinstance(result, str)

def test_serialize_none_returns_empty():
    handler = GenerateContentConfigHandler()
    agent.generate_content_config = None
    assert handler.serialize(agent) == ""

def test_serialize_produces_valid_yaml():
    handler = GenerateContentConfigHandler()
    result = handler.serialize(agent)
    if result:
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)
```

---

### apply(agent: LlmAgent, value: str) -> Any

**Preconditions**:
- `agent` is a valid LlmAgent instance
- `value` is a string (may be empty or invalid YAML)

**Postconditions**:
- Returns original `generate_content_config` (or None)
- On valid input: `agent.generate_content_config` is updated
- On invalid input: `agent.generate_content_config` unchanged, warning logged
- Never raises exceptions

**Contract Tests**:
```python
def test_apply_returns_original():
    handler = GenerateContentConfigHandler()
    original = agent.generate_content_config
    result = handler.apply(agent, valid_yaml)
    assert result is original or result == original

def test_apply_updates_agent():
    handler = GenerateContentConfigHandler()
    handler.apply(agent, "temperature: 0.5")
    assert agent.generate_content_config.temperature == 0.5

def test_apply_invalid_keeps_original():
    handler = GenerateContentConfigHandler()
    original = agent.generate_content_config
    handler.apply(agent, "temperature: 999")  # Out of range
    assert agent.generate_content_config == original

def test_apply_never_raises():
    handler = GenerateContentConfigHandler()
    # Should not raise even with garbage input
    handler.apply(agent, "{{{{invalid yaml")
    handler.apply(agent, None)  # Edge case
```

---

### restore(agent: LlmAgent, original: Any) -> None

**Preconditions**:
- `agent` is a valid LlmAgent instance
- `original` is the value returned from a previous `apply()` call

**Postconditions**:
- `agent.generate_content_config` equals `original`
- Never raises exceptions
- Returns None

**Contract Tests**:
```python
def test_restore_returns_none():
    handler = GenerateContentConfigHandler()
    result = handler.restore(agent, original)
    assert result is None

def test_restore_reverts_config():
    handler = GenerateContentConfigHandler()
    original = handler.apply(agent, "temperature: 0.5")
    handler.restore(agent, original)
    # Config should match original state

def test_restore_handles_none():
    handler = GenerateContentConfigHandler()
    handler.restore(agent, None)
    assert agent.generate_content_config is None
```

---

## Registry Contract

### Registration

```python
# MUST be registered at module load time
assert component_handlers.has(COMPONENT_GENERATE_CONFIG)

# MUST return handler via get_handler
handler = get_handler(COMPONENT_GENERATE_CONFIG)
assert isinstance(handler, ComponentHandler)
```

### Protocol Check

```python
# Handler MUST pass runtime protocol check
from gepa_adk.ports.component_handler import ComponentHandler

handler = GenerateContentConfigHandler()
assert isinstance(handler, ComponentHandler)
```

---

## Invariants

1. **Stateless**: Handler maintains no instance state
2. **Idempotent restore**: `restore(agent, x)` followed by `restore(agent, x)` has same effect as single call
3. **Round-trip**: `restore(agent, apply(agent, serialize(agent)))` leaves agent unchanged
4. **Thread-safe**: All methods are thread-safe (no shared mutable state)

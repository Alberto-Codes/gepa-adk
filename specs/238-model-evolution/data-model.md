# Data Model: Model Evolution Support

**Feature**: 238-model-evolution
**Date**: 2026-01-27

## Entities

### ModelConstraints

**Location**: `src/gepa_adk/domain/types.py`

**Purpose**: Immutable configuration defining which model names are allowed during evolution.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `allowed_models` | `tuple[str, ...]` | Model name strings permitted during evolution | Non-empty after auto-include |

**Design Notes**:
- Frozen dataclass (`frozen=True, slots=True`) for immutability
- Uses `tuple` not `list` for hashability and immutability
- No external dependencies (pure Python stdlib)

```python
@dataclass(frozen=True, slots=True)
class ModelConstraints:
    """Constraints for model evolution.

    Defines which model names are permitted during evolution.
    The handler validates proposed models against this list.

    Attributes:
        allowed_models: Model name strings that may be selected.
            Must contain at least one model after processing.
    """
    allowed_models: tuple[str, ...] = ()
```

### ModelHandler

**Location**: `src/gepa_adk/adapters/component_handlers.py`

**Purpose**: Implements `ComponentHandler` protocol for model serialization, application, and restoration.

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `serialize` | `LlmAgent` | `str` | Extract model name from agent |
| `apply` | `LlmAgent`, `str` | `Any` | Apply new model, return original for restore |
| `restore` | `LlmAgent`, `Any` | `None` | Restore original model |
| `set_constraints` | `ModelConstraints \| None` | `None` | Configure allowed models |

**State Tracking**:
The `apply()` method returns a tuple indicating how to restore:
- `("string", original_name)` - agent.model was a string
- `("wrapper", original_name)` - agent.model was a wrapper object
- `None` - validation failed, no change made

**Design Notes**:
- Duck-types on `.model` attribute for wrapper detection
- Mutates wrapper in-place to preserve configuration
- Logs warning and keeps original on constraint violation

### Model Reflection Agent

**Location**: `src/gepa_adk/engine/reflection_agents.py`

**Purpose**: Factory function creating LlmAgent for proposing model changes.

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | `str` | Model to use for reflection agent itself |
| `allowed_models` | `list[str]` | Models the agent can propose |

**Output**: `LlmAgent` with instruction containing allowed models list

**Design Notes**:
- Instruction bakes in allowed models as explicit list
- Uses `functools.partial` for registry compatibility
- Output key: `proposed_component_text`

## Relationships

```
evolve() API
    │
    ├─[model_choices provided]─► ModelConstraints
    │                              │
    │                              ▼
    │                         ModelHandler
    │                              │
    │                              ├─ serialize() ─► model name string
    │                              ├─ apply() ◄─── constraint validation
    │                              └─ restore() ─► original state
    │
    └─[reflection needed]─────► create_model_reflection_agent()
                                   │
                                   ▼
                              LlmAgent (proposes from allowed list)
```

## State Transitions

### Model During Evolution

```
Initial State
    │
    ▼
serialize() ─► "current-model-name"
    │
    ▼
Reflection Agent proposes "new-model-name"
    │
    ▼
apply() validates against constraints
    │
    ├─[valid]───► agent.model = "new-model-name"
    │             (or wrapper.model = "new-model-name")
    │             return restore_info
    │
    └─[invalid]─► log warning
                  return None (keep original)
    │
    ▼
Evaluation runs with new model
    │
    ▼
restore() ─► return to original model state
```

## Component Name

The model component will use the name `"model"` for registration:

```python
COMPONENT_MODEL = "model"
```

This follows the existing pattern:
- `COMPONENT_INSTRUCTION = "instruction"`
- `COMPONENT_OUTPUT_SCHEMA = "output_schema"`
- `COMPONENT_GENERATE_CONFIG = "generate_content_config"`

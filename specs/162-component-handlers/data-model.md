# Data Model: ComponentHandler Protocol and Registry

**Feature**: 162-component-handlers
**Date**: 2026-01-20
**Status**: Complete

## Entities

### ComponentHandler (Protocol)

A protocol defining the contract for component serialization, application, and restoration.

| Attribute | Type | Description |
|-----------|------|-------------|
| N/A | N/A | Protocol defines methods only, no data attributes |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `serialize` | `(agent: LlmAgent) -> str` | Extract component value from agent as string |
| `apply` | `(agent: LlmAgent, value: str) -> Any` | Apply evolved value, return original |
| `restore` | `(agent: LlmAgent, original: Any) -> None` | Restore original value |

**Constraints**:
- Must be runtime-checkable via `@runtime_checkable` decorator
- All methods are synchronous (no I/O operations)
- `serialize` must return valid string representation for evolution
- `apply` must return value suitable for `restore` to use
- `restore` must handle `None` original gracefully

---

### ComponentHandlerRegistry

A container that maps component names to their handlers.

| Attribute | Type | Description |
|-----------|------|-------------|
| `_handlers` | `dict[str, ComponentHandler]` | Internal mapping of names to handlers |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `register` | `(name: str, handler: ComponentHandler) -> None` | Add/replace handler for name |
| `get` | `(name: str) -> ComponentHandler` | Retrieve handler by name |
| `has` | `(name: str) -> bool` | Check if handler exists |

**Validation Rules**:
- `name` must be non-empty string (raises `ValueError`)
- `handler` must implement `ComponentHandler` protocol (raises `TypeError`)
- `get` raises `KeyError` for unregistered names

---

### InstructionHandler

Concrete handler for the "instruction" component.

| Attribute | Type | Description |
|-----------|------|-------------|
| N/A | N/A | Stateless handler, no attributes |

**Behavior**:
- `serialize`: Returns `str(agent.instruction)`, empty string if None
- `apply`: Sets `agent.instruction = value`, returns original instruction
- `restore`: Sets `agent.instruction = original`

**State Transitions**:
```
Agent State: instruction="original text"
    ↓ apply("new text")
Agent State: instruction="new text"
    Returns: "original text"
    ↓ restore("original text")
Agent State: instruction="original text"
```

---

### OutputSchemaHandler

Concrete handler for the "output_schema" component.

| Attribute | Type | Description |
|-----------|------|-------------|
| N/A | N/A | Stateless handler, no attributes |

**Behavior**:
- `serialize`: Uses `serialize_schema(agent.output_schema)`, empty string if None
- `apply`: Deserializes value, sets schema, returns original; keeps original on error
- `restore`: Sets `agent.output_schema = original`

**State Transitions**:
```
Agent State: output_schema=MySchema
    ↓ apply("class NewSchema: ...")
Agent State: output_schema=NewSchema
    Returns: MySchema
    ↓ restore(MySchema)
Agent State: output_schema=MySchema
```

**Error Handling**:
- `SchemaValidationError` during apply: Log warning, keep original schema

---

## Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                    ComponentHandler                         │
│                      (Protocol)                             │
│  + serialize(agent) -> str                                  │
│  + apply(agent, value) -> Any                               │
│  + restore(agent, original) -> None                         │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │ implements
            ┌──────────────┼──────────────┐
            │              │              │
┌───────────┴───────┐ ┌────┴────────┐ ┌───┴────────────┐
│ InstructionHandler│ │OutputSchema │ │ CustomHandler  │
│                   │ │   Handler   │ │   (future)     │
└───────────────────┘ └─────────────┘ └────────────────┘
            │              │              │
            └──────────────┼──────────────┘
                           │ registered in
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              ComponentHandlerRegistry                        │
│  - _handlers: dict[str, ComponentHandler]                    │
│  + register(name, handler) -> None                          │
│  + get(name) -> ComponentHandler                            │
│  + has(name) -> bool                                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ default instance
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              component_handlers (module var)                 │
│              get_handler(name) -> ComponentHandler           │
│              register_handler(name, handler) -> None         │
└─────────────────────────────────────────────────────────────┘
```

## Type Aliases

From `domain/types.py` (existing):
- `ComponentName: TypeAlias = str`
- `COMPONENT_INSTRUCTION: ComponentName = "instruction"`
- `COMPONENT_OUTPUT_SCHEMA: ComponentName = "output_schema"`

## Module Dependencies

```
ports/component_handler.py
    imports: typing (Protocol, Any, runtime_checkable)
    no external deps (per hexagonal architecture)

adapters/component_handlers.py
    imports: ports/component_handler (ComponentHandler)
    imports: domain/types (COMPONENT_INSTRUCTION, COMPONENT_OUTPUT_SCHEMA)
    imports: utils/schema_tools (serialize_schema, deserialize_schema)
    imports: google.adk.agents (LlmAgent) - adapters layer allowed
    imports: structlog (logging)
```

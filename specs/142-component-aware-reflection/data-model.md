# Data Model: Component-Aware Reflection Agents

**Feature**: 142-component-aware-reflection
**Date**: 2026-01-20

## Entities

### 1. ReflectionAgentFactory

A callable type that creates configured ADK LlmAgent instances for specific component types.

| Field | Type | Description |
|-------|------|-------------|
| (callable) | `Callable[[str], LlmAgent]` | Takes model name, returns configured agent |

**Validation Rules**:
- Must return a valid `LlmAgent` instance
- Returned agent must have `output_key` set

**Notes**: This is a type alias, not a class. Factory functions implement this signature.

---

### 2. ComponentReflectionRegistry

Maps component names to their reflection agent factories.

| Field | Type | Description |
|-------|------|-------------|
| _factories | `dict[str, ReflectionAgentFactory]` | Component name → factory mapping |
| _default_factory | `ReflectionAgentFactory` | Fallback for unregistered components |

**Operations**:
- `register(component_name, factory)` - Add/update a mapping
- `get_factory(component_name)` - Get factory or default
- `get_agent(component_name, model)` - Create agent for component

**Validation Rules**:
- Component names are case-sensitive strings
- Exact match only (no pattern matching for MVP)

---

### 3. SchemaValidationToolResult

Structured result from the schema validation tool.

| Field | Type | Description |
|-------|------|-------------|
| valid | `bool` | Whether schema is syntactically valid |
| class_name | `str \| None` | Name of the class if valid |
| field_count | `int \| None` | Number of fields if valid |
| field_names | `list[str] \| None` | Field names if valid |
| errors | `list[str] \| None` | Error messages if invalid |
| stage | `str \| None` | Validation stage where failure occurred |
| line_number | `int \| None` | Line number of error if applicable |

**Validation Rules**:
- If `valid=True`: `class_name`, `field_count`, `field_names` must be set
- If `valid=False`: `errors` must be non-empty

---

### 4. ReflectionFn (Extended)

The reflection function signature, extended to include component name.

| Parameter | Type | Description |
|-----------|------|-------------|
| component_text | `str` | Current text of the component being evolved |
| trials | `list[dict[str, Any]]` | Performance trials with feedback |
| component_name | `str` | Name of the component (e.g., "output_schema") |

**Returns**: `str` - Proposed improved component text

**Notes**: Third parameter is new; backward compatible by making it have a default or by handling arity.

---

## Type Aliases

```python
# From spec FR-001, FR-002
ReflectionAgentFactory = Callable[[str], LlmAgent]
"""Factory that takes model name and returns configured reflection agent."""

# Existing, extended with component_name
ReflectionFn = Callable[[str, list[dict[str, Any]], str], Awaitable[str]]
"""Async callable: (component_text, trials, component_name) -> proposed_text."""

# Component name constants
COMPONENT_OUTPUT_SCHEMA = "output_schema"
COMPONENT_INSTRUCTION = "instruction"
```

---

## Relationships

```
ComponentReflectionRegistry
        │
        │ contains
        ▼
ReflectionAgentFactory ─────creates────▶ LlmAgent
        │                                    │
        │                                    │ has tools
        │                                    ▼
        │                              validate_output_schema
        │                                    │
        │                                    │ returns
        │                                    ▼
        │                         SchemaValidationToolResult
        │
        │ used by
        ▼
create_adk_reflection_fn() ────produces────▶ ReflectionFn
```

---

## State Transitions

### Reflection Agent Selection

```
┌─────────────────────┐
│  component_name     │
│  provided           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐    found     ┌─────────────────────┐
│  Lookup in registry │──────────────▶│  Use registered     │
│                     │              │  factory             │
└──────────┬──────────┘              └─────────────────────┘
           │
           │ not found
           ▼
┌─────────────────────┐
│  Use default        │
│  (text reflection)  │
└─────────────────────┘
```

### Schema Validation Flow

```
┌─────────────────────┐
│  LLM proposes       │
│  schema text        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Call validate_     │
│  output_schema tool │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌─────────┐  ┌─────────┐
│ valid   │  │ invalid │
│ =True   │  │ =False  │
└────┬────┘  └────┬────┘
     │            │
     ▼            ▼
┌─────────┐  ┌─────────────┐
│ Return  │  │ Fix errors  │
│ schema  │  │ and retry   │
└─────────┘  └─────────────┘
```

---

## Existing Entities (Modified)

### AsyncReflectiveMutationProposer

**Change**: Pass `component` name when calling `adk_reflection_fn`.

```python
# Before (proposer.py:246-247)
proposed_component_text = await self.adk_reflection_fn(
    component_text, trials
)

# After
proposed_component_text = await self.adk_reflection_fn(
    component_text, trials, component
)
```

### create_adk_reflection_fn

**Change**: Accept optional parameters for auto-selection.

| New Parameter | Type | Default | Description |
|---------------|------|---------|-------------|
| model | `str` | `"gemini-2.0-flash"` | Model for auto-created agents |

**Behavior**: If `reflection_agent` is `None`, auto-select based on component name.

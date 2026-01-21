# Data Model: Component Handler Migration

**Feature**: 163-component-handler-migration
**Date**: 2026-01-20

## Overview

This feature is a refactoring that changes internal method signatures. No new domain entities are introduced. The changes affect internal data flow between ADKAdapter methods.

## Existing Entities (No Changes)

The following entities from #162 are used without modification:

### ComponentHandler Protocol

```python
@runtime_checkable
class ComponentHandler(Protocol):
    def serialize(self, agent: LlmAgent) -> str: ...
    def apply(self, agent: LlmAgent, value: str) -> Any: ...
    def restore(self, agent: LlmAgent, original: Any) -> None: ...
```

### ComponentHandlerRegistry

```python
class ComponentHandlerRegistry:
    def register(self, name: str, handler: ComponentHandler) -> None
    def get(self, name: str) -> ComponentHandler
    def has(self, name: str) -> bool
```

### InstructionHandler

```python
class InstructionHandler:
    def serialize(self, agent: LlmAgent) -> str
    def apply(self, agent: LlmAgent, value: str) -> str
    def restore(self, agent: LlmAgent, original: str) -> None
```

### OutputSchemaHandler

```python
class OutputSchemaHandler:
    def serialize(self, agent: LlmAgent) -> str
    def apply(self, agent: LlmAgent, value: str) -> Any
    def restore(self, agent: LlmAgent, original: Any) -> None
```

## Internal Signature Changes

### Before (Tuple-based)

```python
def _apply_candidate(self, candidate: dict[str, str]) -> tuple[str, Any]:
    """Returns (original_instruction, original_output_schema)"""
    ...

def _restore_agent(
    self, original_instruction: str, original_output_schema: Any
) -> None:
    """Positional args for each component type"""
    ...
```

### After (Dict-based)

```python
def _apply_candidate(self, candidate: dict[str, str]) -> dict[str, Any]:
    """Returns {component_name: original_value} mapping"""
    ...

def _restore_agent(self, originals: dict[str, Any]) -> None:
    """Generic dict of component originals"""
    ...
```

## Data Flow

```
candidate: dict[str, str]
    ↓ _apply_candidate
    ↓ for each (component_name, value):
    ↓     handler = get_handler(component_name)
    ↓     originals[component_name] = handler.apply(agent, value)
    ↓
originals: dict[str, Any]
    ↓ (stored during evaluate())
    ↓ _restore_agent
    ↓ for each (component_name, original):
    ↓     handler = get_handler(component_name)
    ↓     handler.restore(agent, original)
    ↓
agent restored to original state
```

## State Transitions

No new state or persistence. Agent state is transiently modified during evaluation and restored immediately after.

| Phase | Agent State | Originals Dict |
|-------|-------------|----------------|
| Before apply | Original | Empty |
| After apply | Modified | Filled |
| During evaluate | Modified | Filled |
| After restore | Original | Filled (unused) |

## Validation Rules

1. **Candidate keys**: Must be registered component names (KeyError on unknown)
2. **Candidate values**: Strings (handler responsible for parsing)
3. **Original values**: Type varies by handler (str for instruction, class for schema)

## Relationships

```
ADKAdapter "1" --> "1" LlmAgent : modifies during evaluate
ADKAdapter "1" --> "*" ComponentHandler : dispatches via registry
ComponentHandler "1" --> "1" component : manages one component type
```

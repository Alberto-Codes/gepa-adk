# Data Model: AgentProvider Protocol

**Date**: 2026-01-15
**Feature**: 029-agent-provider-protocol

## Overview

This document defines the data model for the AgentProvider protocol, including entities, relationships, and validation rules.

## Entities

### AgentProvider (Protocol)

The core protocol interface for agent loading and persistence.

| Attribute | Type | Description |
|-----------|------|-------------|
| N/A | N/A | Protocol defines methods only, no attributes |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_agent` | `(name: str) -> LlmAgent` | Retrieve agent by unique name |
| `save_instruction` | `(name: str, instruction: str) -> None` | Persist evolved instruction |
| `list_agents` | `() -> list[str]` | List all available agent names |

**Validation Rules**:
- `name` must be a non-empty string
- `instruction` can be empty but must be a string
- All methods raise appropriate errors for invalid inputs

### LlmAgent (External - from google.adk)

The ADK agent type returned by `get_agent()`.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Unique agent identifier |
| `instruction` | `str \| InstructionProvider` | Dynamic instruction text (evolable) |
| `model` | `str \| BaseLlm` | LLM model identifier |
| `tools` | `list[ToolUnion]` | Available tools |
| `description` | `str` | Optional agent description |

**Note**: This is an external type from Google ADK. We reference it but don't define it.

### Agent Configuration (Conceptual)

The data needed to construct an agent. Not a formal type in the protocol.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Unique identifier |
| `instruction` | `str` | Yes | System instruction |
| `model` | `str` | No | Model name (inherits if not set) |
| `description` | `str` | No | Agent description |

## Relationships

```
┌─────────────────────┐
│   AgentProvider     │
│     (Protocol)      │
└──────────┬──────────┘
           │ returns
           ▼
┌─────────────────────┐
│      LlmAgent       │
│  (google.adk type)  │
└──────────┬──────────┘
           │ has
           ▼
┌─────────────────────┐
│    instruction      │
│      (str)          │
└─────────────────────┘
```

## State Transitions

The protocol itself is stateless. State management is the responsibility of implementations.

**Agent Lifecycle** (implementation-defined):

```
[Not Loaded] → get_agent(name) → [Loaded]
                                    │
                                    ▼
               [Used in Evolution] ← evolve
                                    │
                                    ▼
               save_instruction() → [Persisted]
```

## Type Definitions

```python
from typing import Protocol, runtime_checkable
from google.adk.agents import LlmAgent


@runtime_checkable
class AgentProvider(Protocol):
    """Protocol for loading and persisting agents."""

    def get_agent(self, name: str) -> LlmAgent:
        """Load an agent by name."""
        ...

    def save_instruction(self, name: str, instruction: str) -> None:
        """Persist an evolved instruction."""
        ...

    def list_agents(self) -> list[str]:
        """List available agent names."""
        ...
```

## Error Conditions

| Condition | Expected Behavior |
|-----------|-------------------|
| Agent not found | Raise appropriate error (implementation-defined) |
| Invalid name (empty) | Raise ValueError |
| Storage failure | Raise appropriate error (implementation-defined) |
| Invalid instruction | Implementation decides (may accept empty strings) |

## Constraints

1. **No External Imports in Protocol**: The protocol file in `ports/` must not import external libraries directly. It can import `LlmAgent` type for annotation purposes only using `TYPE_CHECKING`.

2. **Immutability**: Returned `LlmAgent` instances should be treated as snapshots. Modifications require explicit `save_instruction()` calls.

3. **Thread Safety**: Not guaranteed by the protocol. Implementations must handle concurrency.

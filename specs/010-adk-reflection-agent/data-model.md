# Data Model: ADK-First Reflection Agent Support

**Feature**: 010-adk-reflection-agent
**Date**: 2026-01-10

## Overview

This feature does not introduce new persistent data models. Instead, it defines runtime data structures (function signatures and session state schemas) for the ADK reflection integration.

## Runtime Data Structures

### 1. Reflection Function Callable

**Type Alias**: `ReflectionFn`

```python
from collections.abc import Awaitable, Callable

ReflectionFn = Callable[[str, list[dict]], Awaitable[str]]
```

**Signature**:
- **Input 1** (`current_instruction: str`): The current instruction text to improve
- **Input 2** (`feedback: list[dict]`): List of feedback dictionaries from evaluation
- **Output** (`str`): Improved instruction text

**Usage Context**: Passed to `AsyncReflectiveMutationProposer` as `adk_reflection_fn` parameter.

---

### 2. Session State Schema

**Purpose**: Context data passed to ADK reflection agent via session initialization.

| Key | Type | Description |
|-----|------|-------------|
| `current_instruction` | `str` | The instruction text being evolved |
| `execution_feedback` | `str` | JSON-serialized list of feedback dictionaries |

**Example**:
```python
session_state = {
    "current_instruction": "Be helpful and concise",
    "execution_feedback": '[{"score": 0.8, "output": "...", "feedback": "..."}]'
}
```

**Validation Rules**:
- `current_instruction` must be non-empty string
- `execution_feedback` must be valid JSON (serialized list)

---

### 3. Feedback Item Schema

**Purpose**: Individual feedback entry in the reflective dataset.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Inputs` | `dict[str, str]` | Yes | Component name → value mapping |
| `Generated Outputs` | `str` | Yes | Agent output text |
| `Feedback` | `str` | Yes | Structured feedback string |

**Example**:
```python
{
    "Inputs": {"instruction": "Be helpful"},
    "Generated Outputs": "Hello, how can I help?",
    "Feedback": "score: 0.750, tool_calls: 0, tokens: 42"
}
```

**Note**: This schema is already defined by `ADKAdapter._build_reflection_example()` and remains unchanged.

---

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AsyncReflectiveMutationProposer                  │
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────────────────────────┐  │
│  │ model: str       │    │ adk_reflection_fn: ReflectionFn|None │  │
│  │ prompt_template  │    │                                      │  │
│  │ temperature      │    │  Called when not None:               │  │
│  │ max_tokens       │    │  - Passes current_instruction        │  │
│  └──────────────────┘    │  - Passes feedback list              │  │
│                          │  - Receives improved instruction     │  │
│                          └──────────────────────────────────────┘  │
│                                        │                            │
│                                        │ if None                    │
│                                        ▼                            │
│                          ┌──────────────────────────────────────┐  │
│                          │ litellm.acompletion() (fallback)     │  │
│                          └──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    create_adk_reflection_fn()                       │
│                                                                     │
│  Inputs:                           Creates:                         │
│  ┌────────────────────────┐       ┌────────────────────────────┐   │
│  │ reflection_agent:      │       │ async def reflect(         │   │
│  │   LlmAgent             │──────▶│   current_instruction,     │   │
│  │ session_service:       │       │   feedback                 │   │
│  │   BaseSessionService   │       │ ) -> str                   │   │
│  └────────────────────────┘       └────────────────────────────┘   │
│                                              │                      │
│                                              ▼                      │
│                                   ┌─────────────────────┐          │
│                                   │ Session State       │          │
│                                   │ ├ current_instruction│          │
│                                   │ └ execution_feedback │          │
│                                   └─────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

## State Transitions

This feature has no persistent state transitions. The reflection function is stateless - each invocation creates a fresh ADK session, processes reflection, and returns results.

## Validation Rules Summary

| Entity | Rule | Error Handling |
|--------|------|----------------|
| `adk_reflection_fn` | Must be async callable or None | TypeError at proposer init |
| `current_instruction` | Non-empty string | Return None (skip component) |
| `feedback` | List of dicts | Empty list → early return None |
| ADK response | Non-empty string | Fallback to original text |

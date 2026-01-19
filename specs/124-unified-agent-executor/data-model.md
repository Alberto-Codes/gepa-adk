# Data Model: Unified Agent Executor

**Feature**: 124-unified-agent-executor
**Date**: 2026-01-19

## Overview

This document defines the data structures for the Unified Agent Executor feature. These models live in the domain and ports layers, following hexagonal architecture principles.

---

## 1. Core Entities

### 1.1 ExecutionStatus (Enum)

**Purpose**: Represents the outcome status of an agent execution.

**Location**: `src/gepa_adk/ports/agent_executor.py`

```
ExecutionStatus
├── SUCCESS  - Agent completed execution normally
├── FAILED   - Agent encountered an error during execution
└── TIMEOUT  - Agent execution exceeded configured timeout
```

**Validation Rules**:
- Status MUST be one of the three defined values
- Status is determined by execution outcome, not output quality

**Relationships**:
- Used by ExecutionResult.status

---

### 1.2 ExecutionResult (Dataclass)

**Purpose**: Captures the complete result of an agent execution, providing consistent return type across all agent types.

**Location**: `src/gepa_adk/ports/agent_executor.py`

```
ExecutionResult
├── status: ExecutionStatus          [Required] Outcome status
├── session_id: str                  [Required] ADK session identifier
├── extracted_value: str | None      [Optional] Output text from agent
├── error_message: str | None        [Optional] Error details if failed/timeout
├── execution_time_seconds: float    [Optional] Execution duration (default: 0.0)
└── captured_events: list[Any] | None [Optional] ADK events for debugging
```

**Validation Rules**:
- status is required and must be a valid ExecutionStatus
- session_id is required and must be non-empty string
- If status is FAILED, error_message SHOULD be populated
- If status is SUCCESS, extracted_value SHOULD be populated
- execution_time_seconds must be >= 0.0

**State Transitions**:
```
                ┌─────────────┐
                │   RUNNING   │
                └──────┬──────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   SUCCESS   │ │   FAILED    │ │   TIMEOUT   │
└─────────────┘ └─────────────┘ └─────────────┘
```

**Relationships**:
- Created by AgentExecutor.execute_agent()
- Consumed by ADKAdapter, CriticScorer, reflection function

---

### 1.3 AgentExecutorProtocol (Protocol)

**Purpose**: Defines the interface for unified agent execution, enabling dependency injection and testing.

**Location**: `src/gepa_adk/ports/agent_executor.py`

```
AgentExecutorProtocol
└── execute_agent(
        agent: Any,                              [Required] ADK LlmAgent
        input_text: str,                         [Required] User message
        *,
        instruction_override: str | None,        [Optional] Override agent instruction
        output_schema_override: dict | None,     [Optional] Override output schema
        session_state: dict | None,              [Optional] Initial session state
        existing_session_id: str | None,         [Optional] Reuse existing session
        timeout_seconds: int,                    [Optional] Execution timeout (default: 300)
    ) -> ExecutionResult
```

**Validation Rules**:
- agent must be a valid ADK LlmAgent (not enforced at protocol level)
- input_text must be non-empty string
- If instruction_override provided, it replaces agent's instruction for this execution only
- If existing_session_id provided, session must exist (error if not found)
- timeout_seconds must be > 0

**Relationships**:
- Implemented by AgentExecutor adapter
- Used by ADKAdapter, CriticScorer, reflection function

---

## 2. Supporting Types

### 2.1 Type Aliases

**Location**: `src/gepa_adk/domain/types.py` (existing file)

```python
# No new type aliases needed - using Any for ADK types to avoid coupling
```

---

## 3. Entity Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                        Evolution Engine                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  ADKAdapter  │    │ CriticScorer │    │  Reflection  │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │               │
│         └───────────────────┴───────────────────┘               │
│                             │                                    │
│                    ┌────────▼────────┐                          │
│                    │ AgentExecutor   │                          │
│                    │   Protocol      │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  AgentExecutor    │
                    │    Adapter        │
                    └─────────┬─────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
      ┌──────────────┐              ┌──────────────┐
      │  ADK Runner  │              │ADK Session   │
      │              │              │  Service     │
      └──────────────┘              └──────────────┘
```

---

## 4. Data Flow

### 4.1 Execution Flow

```
Input                Processing              Output
─────                ──────────              ──────

LlmAgent       ─┐
input_text      │    ┌────────────────┐
instruction_    │───▶│ AgentExecutor  │───▶ ExecutionResult
  override      │    │                │      ├── status
session_state   │    │ 1. Validate    │      ├── session_id
existing_       │    │ 2. Setup       │      ├── extracted_value
  session_id   ─┘    │ 3. Execute     │      ├── error_message
                     │ 4. Capture     │      ├── execution_time
                     │ 5. Extract     │      └── captured_events
                     └────────────────┘
```

### 4.2 Session State Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Session Lifecycle                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Option A: New Session                                          │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐        │
│  │ session_    │───▶│ Create       │───▶│ Execute     │        │
│  │ state       │    │ Session      │    │ Agent       │        │
│  └─────────────┘    └──────────────┘    └─────────────┘        │
│                                                                  │
│  Option B: Reuse Session                                        │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐        │
│  │ existing_   │───▶│ Get          │───▶│ Execute     │        │
│  │ session_id  │    │ Session      │    │ Agent       │        │
│  └─────────────┘    └──────────────┘    └─────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Validation Summary

| Entity | Field | Rule |
|--------|-------|------|
| ExecutionResult | status | Required, valid ExecutionStatus |
| ExecutionResult | session_id | Required, non-empty string |
| ExecutionResult | execution_time_seconds | >= 0.0 |
| AgentExecutorProtocol | input_text | Required, non-empty |
| AgentExecutorProtocol | timeout_seconds | > 0 |
| AgentExecutorProtocol | existing_session_id | Session must exist if provided |

---

## 5.1 Exceptions

### SessionNotFoundError

**Purpose**: Raised when `existing_session_id` is provided but the session does not exist in the session service.

**Location**: `src/gepa_adk/domain/exceptions.py`

```python
class SessionNotFoundError(EvolutionError):
    """Raised when a requested session does not exist.

    Attributes:
        session_id: The session ID that was not found.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")
```

**Relationships**:
- Raised by AgentExecutor when existing_session_id is invalid
- Inherits from EvolutionError per ADR-009

---

## 6. Migration Notes

### Existing Types Affected

| Type | Change |
|------|--------|
| ADKAdapter | Now delegates to AgentExecutor |
| CriticScorer | Now delegates to AgentExecutor |
| ReflectionFn | Return type unchanged, internal delegation |

### Backward Compatibility

- No changes to public API (`evolve()`, `evolve_sync()`)
- No changes to EvolutionResult, EvolutionConfig
- Internal implementation detail only

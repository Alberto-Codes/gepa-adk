# Architecture: Unified Agent Executor

**Branch**: `124-unified-agent-executor` | **Date**: 2026-01-19 | **Status**: draft
**Spec**: [./spec.md](spec.md) | **Plan**: [./plan.md](plan.md) | **Tasks**: [./tasks.md](tasks.md)

## 0. Links & References

- Feature Spec: `./spec.md`
- Implementation Plan: `./plan.md`
- Tasks: `./tasks.md` (to be generated)
- Related ADRs:
  - [ADR-000: Hexagonal Architecture](../../docs/adr/ADR-000-hexagonal-architecture.md)
  - [ADR-002: Protocol for Interfaces](../../docs/adr/ADR-002-protocol-for-interfaces.md)
  - [ADR-005: Three-Layer Testing](../../docs/adr/ADR-005-three-layer-testing.md)
- GitHub Issue: [#135](https://github.com/Alberto-Codes/gepa-adk/issues/135)

## 1. Purpose & Scope

### Goal

Provide a unified execution interface for all ADK agent types (generator, critic, reflection) with consistent session management, event capture, and result handling. This eliminates ~18-19% code duplication and enables feature parity across agent types.

### Non-Goals

- Workflow agent support (SequentialAgent, ParallelAgent, LoopAgent)
- Database persistence of execution results
- OpenTelemetry tracing integration
- Provider-specific error enhancement
- Tool validation callbacks (deferred to #133)
- Lifecycle callbacks (deferred to #134)

### Scope Boundaries

- **In-scope**: AgentExecutorProtocol, AgentExecutor adapter, migration of ADKAdapter/CriticScorer/reflection, backward compatibility
- **Out-of-scope**: Public API changes, new user-facing features, workflow support

### Constraints

- **Technical**: Must use existing google-adk >= 1.22.0, no new dependencies
- **Organizational**: Must follow hexagonal architecture (ADR-000), protocols (ADR-002)
- **Conventions**: Backward compatible - existing evolve() API unchanged

## 2. Architecture at a Glance

- **Single AgentExecutor** replaces three separate Runner instantiation patterns
- **Protocol-based interface** in ports layer enables dependency injection and testing
- **ExecutionResult dataclass** provides consistent return type with status, output, events
- **Session management** unified: create new or reuse existing via parameter
- **Timeout handling** returns status (not exception) for graceful recovery
- **Event capture** always available for debugging and trajectory analysis

## 3. Context Diagram (C4 Level 1)

> Shows how the Unified Agent Executor fits into the broader system.

```mermaid
flowchart TB
    subgraph Legend[" "]
        direction LR
        l1["👤 Actor"]
        l2["🔷 System"]
        l3["📦 External"]
        l4["🔶 Modified"]
    end

    subgraph Actors[" "]
        user["👤 GEPA Developer<br/><i>Uses evolution API</i>"]
    end

    subgraph System[" "]
        gepa["🔷 GEPA-ADK<br/><i>Evolution engine with<br/>Unified Agent Executor</i>"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>Runner, Session,<br/>Event types</i>"]
        llm["📦 LLM Provider<br/><i>Ollama, Gemini</i>"]
    end

    user -->|"evolve(agent, trainset)"| gepa
    gepa -->|"Runner.run_async()"| adk
    gepa -->|"LLM calls<br/>(reflection)"| llm

    style l1 fill:#1168BD,color:#E0E0E0
    style l2 fill:#438DD5,color:#E0E0E0
    style l3 fill:#666666,color:#E0E0E0
    style l4 fill:#D4740C,color:#E0E0E0
    style gepa fill:#438DD5,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style user fill:#1168BD,color:#E0E0E0
```

## 4. Container Diagram (C4 Level 2)

> Shows the major containers within GEPA-ADK and how AgentExecutor fits.

```mermaid
flowchart TB
    subgraph GEPA["GEPA-ADK"]
        api["🔷 Public API<br/><i>Python</i><br/>evolve(), evolve_sync()"]
        engine["🔷 Evolution Engine<br/><i>Python</i><br/>AsyncGEPAEngine"]

        subgraph Adapters["Adapters Layer"]
            executor["🔶 AgentExecutor<br/><i>NEW</i><br/>Unified execution"]
            adk_adapter["🔶 ADKAdapter<br/><i>MODIFIED</i><br/>Uses AgentExecutor"]
            critic["🔶 CriticScorer<br/><i>MODIFIED</i><br/>Uses AgentExecutor"]
        end

        subgraph Engine2["Engine Layer"]
            reflection["🔶 adk_reflection<br/><i>MODIFIED</i><br/>Uses AgentExecutor"]
            proposer["🔷 Proposer<br/><i>Python</i><br/>Mutation generation"]
        end
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>Runner, Session</i>"]
    end

    api --> engine
    engine --> adk_adapter
    engine --> proposer
    adk_adapter --> executor
    critic --> executor
    reflection --> executor
    executor --> adk

    style api fill:#438DD5,color:#E0E0E0
    style engine fill:#438DD5,color:#E0E0E0
    style proposer fill:#438DD5,color:#E0E0E0
    style executor fill:#D4740C,color:#E0E0E0
    style adk_adapter fill:#D4740C,color:#E0E0E0
    style critic fill:#D4740C,color:#E0E0E0
    style reflection fill:#D4740C,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
```

## 5. Component Diagram (C4 Level 3)

> Shows the internal structure of the AgentExecutor and its relationships.

```mermaid
flowchart TB
    subgraph Ports["ports/ (Interfaces)"]
        protocol["📦 AgentExecutorProtocol<br/><i>Protocol</i><br/>execute_agent() contract"]
        status["📦 ExecutionStatus<br/><i>Enum</i><br/>SUCCESS/FAILED/TIMEOUT"]
        result["📦 ExecutionResult<br/><i>Dataclass</i><br/>Unified return type"]
    end

    subgraph Adapters["adapters/ (Implementation)"]
        executor["🔶 AgentExecutor<br/><i>Class</i><br/>Implements protocol"]
    end

    subgraph Consumers["Consumers (Modified)"]
        adk_adapter["🔶 ADKAdapter<br/><i>Class</i><br/>Generator evaluation"]
        critic["🔶 CriticScorer<br/><i>Class</i><br/>Critic evaluation"]
        reflection["🔶 create_adk_reflection_fn<br/><i>Function</i><br/>Reflection execution"]
    end

    subgraph ADK["Google ADK"]
        runner["📦 Runner<br/><i>Class</i><br/>Agent runtime"]
        session["📦 SessionService<br/><i>Protocol</i><br/>State management"]
    end

    executor -->|"implements"| protocol
    executor -->|"returns"| result
    result -->|"uses"| status

    adk_adapter -->|"uses"| executor
    critic -->|"uses"| executor
    reflection -->|"uses"| executor

    executor -->|"delegates to"| runner
    executor -->|"manages"| session

    style protocol fill:#5B9BD5,color:#E0E0E0
    style status fill:#5B9BD5,color:#E0E0E0
    style result fill:#5B9BD5,color:#E0E0E0
    style executor fill:#D4740C,color:#E0E0E0
    style adk_adapter fill:#D4740C,color:#E0E0E0
    style critic fill:#D4740C,color:#E0E0E0
    style reflection fill:#D4740C,color:#E0E0E0
    style runner fill:#666666,color:#E0E0E0
    style session fill:#666666,color:#E0E0E0
```

## 6. Code Diagram (C4 Level 4)

> Shows class relationships for the new and modified components.

```mermaid
classDiagram
    class ExecutionStatus {
        <<enumeration>>
        SUCCESS
        FAILED
        TIMEOUT
    }

    class ExecutionResult {
        +ExecutionStatus status
        +str session_id
        +str|None extracted_value
        +str|None error_message
        +float execution_time_seconds
        +list|None captured_events
    }

    class AgentExecutorProtocol {
        <<protocol>>
        +execute_agent(agent, input_text, **kwargs) ExecutionResult
    }

    class AgentExecutor {
        -BaseSessionService _session_service
        -str _app_name
        +execute_agent(agent, input_text, **kwargs) ExecutionResult
        -_create_or_get_session(session_id, state) Session
        -_execute_with_timeout(runner, session, input, timeout) tuple
        -_extract_output(session, events) str|None
    }

    class ADKAdapter {
        -AgentExecutorProtocol _executor
        +evaluate(batch, candidate) EvaluationBatch
        -_run_single_example(input) tuple
    }

    class CriticScorer {
        -AgentExecutorProtocol _executor
        +async_score(input, output, expected) Score
    }

    ExecutionResult --> ExecutionStatus : uses
    AgentExecutor ..|> AgentExecutorProtocol : implements
    AgentExecutor --> ExecutionResult : returns
    ADKAdapter --> AgentExecutorProtocol : uses
    CriticScorer --> AgentExecutorProtocol : uses
```

## 7. Hexagonal Architecture View

> Shows how the feature aligns with the hexagonal (ports & adapters) architecture.

```mermaid
flowchart TB
    subgraph External["External Systems"]
        ADK["Google ADK<br/>Runner, Session, Events"]
    end

    subgraph Adapters["adapters/ (External Integration)"]
        executor["🔶 AgentExecutor<br/>(NEW)"]
        adk_adapter["🔶 ADKAdapter<br/>(MODIFIED)"]
        critic["🔶 CriticScorer<br/>(MODIFIED)"]
    end

    subgraph Ports["ports/ (Interfaces)"]
        exec_protocol["🔶 AgentExecutorProtocol<br/>(NEW)"]
        exec_result["🔶 ExecutionResult<br/>(NEW)"]
        exec_status["🔶 ExecutionStatus<br/>(NEW)"]
        adapter_protocol["AsyncGEPAAdapter"]
        scorer_protocol["Scorer"]
    end

    subgraph Engine["engine/ (Orchestration)"]
        gepa_engine["AsyncGEPAEngine"]
        reflection["🔶 adk_reflection<br/>(MODIFIED)"]
        proposer["AsyncReflectiveMutationProposer"]
    end

    subgraph Domain["domain/ (Pure Python)"]
        models["EvolutionConfig, Candidate"]
        types["TrajectoryConfig, etc."]
    end

    subgraph API["api.py (Public Interface)"]
        evolve["evolve(), evolve_sync()"]
    end

    API --> Engine
    Engine --> Ports
    Ports --> Adapters
    Adapters --> External
    Engine --> Domain

    adk_adapter --> exec_protocol
    critic --> exec_protocol
    reflection --> exec_protocol
    executor .-> exec_protocol

    style executor fill:#D4740C,color:#E0E0E0
    style adk_adapter fill:#D4740C,color:#E0E0E0
    style critic fill:#D4740C,color:#E0E0E0
    style reflection fill:#D4740C,color:#E0E0E0
    style exec_protocol fill:#D4740C,color:#E0E0E0
    style exec_result fill:#D4740C,color:#E0E0E0
    style exec_status fill:#D4740C,color:#E0E0E0
```

## 8. Runtime Behavior (Sequence Diagrams)

### 8.1 Happy Path: Agent Execution via AgentExecutor

```mermaid
sequenceDiagram
    autonumber
    participant C as Consumer<br/>(ADKAdapter/Critic/Reflection)
    participant E as AgentExecutor
    participant S as SessionService
    participant R as ADK Runner
    participant A as Agent

    C->>E: execute_agent(agent, input, ...)

    alt existing_session_id provided
        E->>S: get_session(session_id)
        S-->>E: existing session
    else new session
        E->>S: create_session(state)
        S-->>E: new session
    end

    E->>R: Runner(agent, session_service)
    E->>R: run_async(user_id, session_id, message)

    loop Event stream
        R->>A: execute
        A-->>R: event
        R-->>E: event
        E->>E: capture event
    end

    E->>E: extract_output(session, events)
    E-->>C: ExecutionResult(SUCCESS, output, events)
```

### 8.2 Error Case: Timeout During Execution

```mermaid
sequenceDiagram
    autonumber
    participant C as Consumer
    participant E as AgentExecutor
    participant R as ADK Runner

    C->>E: execute_agent(agent, input, timeout=60)
    E->>R: run_async(...)

    loop Event stream
        R-->>E: event (captured)
        Note over E: Time passes...
    end

    Note over E: Timeout reached
    E->>E: Stop iteration
    E->>E: Status = TIMEOUT
    E-->>C: ExecutionResult(TIMEOUT, partial_events)

    Note over C: Caller can inspect<br/>captured_events for debugging
```

### 8.3 Session Sharing: Critic Accesses Generator State

```mermaid
sequenceDiagram
    autonumber
    participant A as ADKAdapter
    participant E as AgentExecutor
    participant S as SessionService
    participant CS as CriticScorer

    A->>E: execute_agent(generator, input)
    E->>S: create_session()
    S-->>E: session_id="sess_123"
    E-->>A: ExecutionResult(session_id="sess_123")

    Note over A: Generator sets session state<br/>during execution

    A->>CS: async_score(input, output, session_id="sess_123")
    CS->>E: execute_agent(critic, input, existing_session_id="sess_123")
    E->>S: get_session("sess_123")
    S-->>E: existing session with state

    Note over E: Critic can access<br/>generator's state

    E-->>CS: ExecutionResult
```

## 9. Data Model & Contracts

### 9.1 Data Changes (ERD)

> New types introduced in ports layer.

```mermaid
erDiagram
    EXECUTION_STATUS {
        enum value "SUCCESS|FAILED|TIMEOUT"
    }
    EXECUTION_RESULT {
        ExecutionStatus status
        string session_id
        string extracted_value "nullable"
        string error_message "nullable"
        float execution_time_seconds
        list captured_events "nullable"
    }
    EXECUTION_RESULT ||--|| EXECUTION_STATUS : "has"
```

### 9.2 API Contracts

**Public API Changes**: None - internal refactoring only

**New Protocol** (ports layer):
```python
@runtime_checkable
class AgentExecutorProtocol(Protocol):
    async def execute_agent(
        self,
        agent: Any,
        input_text: str,
        *,
        instruction_override: str | None = None,
        output_schema_override: dict[str, Any] | None = None,
        session_state: dict[str, Any] | None = None,
        existing_session_id: str | None = None,
        timeout_seconds: int = 300,
    ) -> ExecutionResult: ...
```

**Internal Changes**:
- `ADKAdapter.__init__()` accepts optional `executor: AgentExecutorProtocol`
- `CriticScorer.__init__()` accepts optional `executor: AgentExecutorProtocol`
- `create_adk_reflection_fn()` accepts optional `executor: AgentExecutorProtocol`

## 10. Quality Attributes (NFRs)

| Attribute | Requirement | Verification |
|-----------|-------------|--------------|
| **Performance** | No regression from current execution paths | Integration timing tests |
| **Reliability** | TIMEOUT status instead of exception | Unit tests for timeout handling |
| **Maintainability** | Single execution path for all agent types | Code coverage, no duplication |
| **Testability** | Protocol enables mocking | Contract tests |
| **Backward Compatibility** | evolve() API unchanged | Existing tests pass |

## 11. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Contract** | `tests/contracts/test_agent_executor_protocol.py` | AgentExecutor implements protocol | `@pytest.mark.contract` |
| **Unit** | `tests/unit/adapters/test_agent_executor.py` | Session management, timeout, extraction | `@pytest.mark.unit` |
| **Integration** | `tests/integration/test_unified_execution.py` | Feature parity across agent types | `@pytest.mark.integration` |

**Key Test Scenarios**:
1. Execute agent and extract output successfully
2. Execute with instruction override - original unchanged
3. Execute with session reuse - state accessible
4. Timeout returns TIMEOUT status with partial events
5. Feature parity: generator, critic, reflection all work identically

## 12. Risks & Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Output extraction differences between agent types | Incorrect results | Test all three paths thoroughly |
| Session state isolation regression | Data leakage | Verify session isolation in tests |
| Performance regression | Slower evolution | Benchmark before/after |

### Open Questions

- [x] Should timeout raise or return status? **Decision: Return status**
- [x] Use Any or LlmAgent for agent parameter? **Decision: Any (avoid coupling)**

### TODOs

- [x] Consolidate duplicate extraction utilities in ADKAdapter to utils/events.py → **Covered by T061**
- [x] Document migration path for custom adapters → **Out of scope (no custom adapters exist)**

## 13. Decisions (ADR References)

| ADR | Title | Relevance to This Feature |
|-----|-------|---------------------------|
| ADR-000 | Hexagonal Architecture | Protocol in ports, implementation in adapters |
| ADR-002 | Protocol Interfaces | AgentExecutorProtocol with @runtime_checkable |
| ADR-005 | Three-Layer Testing | Contract/unit/integration test coverage |

**New ADRs Needed**: None - all decisions align with existing ADRs.

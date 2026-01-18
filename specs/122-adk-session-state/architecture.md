# Architecture: ADK Session State Management

**Branch**: `122-adk-session-state` | **Date**: 2026-01-18 | **Status**: draft
**Spec**: [./spec.md] | **Plan**: [./plan.md] | **Tasks**: [./tasks.md]

## 0. Links & References

- Feature Spec: `./spec.md`
- Implementation Plan: `./plan.md`
- Research: `./research.md`
- Related ADRs:
  - ADR-000: Hexagonal Architecture
  - ADR-001: Async-First Architecture
  - ADR-002: Protocol for Interfaces
  - ADR-005: Three-Layer Testing

## 1. Purpose & Scope

### Goal

Enable the reflection agent to fully leverage ADK's native session state management, eliminating manual message construction and enabling state-based data flow between agents.

### Non-Goals

- Persistent session storage (remains in-memory)
- Changes to domain models or port protocols
- Multi-agent workflow implementation (future work)

### Scope Boundaries

- **In-scope**: output_key configuration, state-based output retrieval, backward compatibility
- **Out-of-scope**: New domain models, protocol changes, documentation updates

### Constraints

- **Technical**: Must use existing ADK session state APIs (InMemorySessionService)
- **Organizational**: Must follow hexagonal architecture (changes in adapters/engine only)
- **Conventions**: Existing ReflectionFn interface must remain unchanged

## 2. Architecture at a Glance

- **State injection** (existing): Input data flows via session.state and template substitution
- **Output storage** (new): Configure `output_key` on LlmAgent for automatic state storage
- **Output retrieval** (new): Extract output from session.state instead of parsing events
- **Shared utility** (new): `extract_output_from_state()` in `utils/events.py` (DRY, hexagonal-compliant)
- **Fallback strategy**: Event-based extraction when state retrieval fails
- **Layer impact**: 3 layers - utils (new function), engine (modify), adapters (refactor to use shared utility)

## 3. Context Diagram (C4 Level 1)

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
        developer["👤 GEPA Developer<br/><i>Uses reflection agent<br/>for instruction evolution</i>"]
    end

    subgraph System[" "]
        gepa["🔷 GEPA-ADK<br/><i>Evolutionary optimization<br/>for ADK agents</i>"]
        reflection["🔶 Reflection Agent<br/><i>Modified to use<br/>output_key for state</i>"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>Agent runtime with<br/>session state mgmt</i>"]
        llm["📦 LLM Provider<br/><i>Gemini/Ollama<br/>for reflection</i>"]
    end

    developer -->|"Configures evolution"| gepa
    gepa -->|"Creates reflection agent"| reflection
    reflection -->|"Runs via ADK Runner<br/>with session state"| adk
    reflection -->|"Generates proposals"| llm

    style l1 fill:#1168BD,color:#E0E0E0
    style l2 fill:#438DD5,color:#E0E0E0
    style l3 fill:#666666,color:#E0E0E0
    style l4 fill:#D4740C,color:#E0E0E0
    style gepa fill:#438DD5,color:#E0E0E0
    style reflection fill:#D4740C,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style developer fill:#1168BD,color:#E0E0E0
```

## 4. Component Diagram (C4 Level 3)

```mermaid
flowchart TB
    subgraph engine["engine/ Layer"]
        adk_reflection["🔶 adk_reflection.py<br/><i>Module</i><br/>create_adk_reflection_fn()"]
        proposer["📦 proposer.py<br/><i>Class</i><br/>AsyncReflectiveMutationProposer"]
    end

    subgraph utils["utils/ Layer (Shared)"]
        events["🔶 events.py<br/><i>Module</i><br/>+ extract_output_from_state()"]
    end

    subgraph adapters["adapters/ Layer"]
        multi_agent["🔶 multi_agent.py<br/><i>Class</i><br/>REFACTOR to use shared utility"]
    end

    subgraph adk["Google ADK"]
        llm_agent["📦 LlmAgent<br/><i>Class</i><br/>output_key field"]
        session_service["📦 InMemorySessionService<br/><i>Class</i><br/>Session state storage"]
        inject_state["📦 inject_session_state()<br/><i>Function</i><br/>Template substitution"]
    end

    proposer -->|"Uses"| adk_reflection
    adk_reflection -->|"Uses"| events
    multi_agent -->|"Uses"| events
    adk_reflection -->|"Creates"| llm_agent
    adk_reflection -->|"Uses"| session_service
    llm_agent -->|"Instruction processed by"| inject_state

    style adk_reflection fill:#D4740C,color:#E0E0E0
    style events fill:#D4740C,color:#E0E0E0
    style multi_agent fill:#D4740C,color:#E0E0E0
    style proposer fill:#5B9BD5,color:#E0E0E0
    style llm_agent fill:#666666,color:#E0E0E0
    style session_service fill:#666666,color:#E0E0E0
    style inject_state fill:#666666,color:#E0E0E0
```

## 5. Hexagonal Architecture View

```mermaid
flowchart TB
    subgraph External["External Systems"]
        ADK["Google ADK<br/>(Session State)"]
        LLM["LLM Provider"]
    end

    subgraph Adapters["adapters/ (Refactored)"]
        MultiAgent["🔶 multi_agent.py<br/>REFACTOR: use shared utility"]
    end

    subgraph Utils["utils/ (Shared)"]
        Events["🔶 events.py<br/>+ extract_output_from_state()"]
    end

    subgraph Engine["engine/ (Modified)"]
        ADKReflection["🔶 adk_reflection.py<br/>+ output_key config<br/>+ use shared utility"]
        Proposer["proposer.py<br/>(unchanged)"]
    end

    subgraph Ports["ports/ (Unchanged)"]
        ProposerProtocol["MutationProposer Protocol"]
    end

    subgraph Domain["domain/ (Unchanged)"]
        Models["EvolutionConfig, etc."]
    end

    Engine --> Ports
    Engine --> Utils
    Adapters --> Utils
    Adapters --> External
    Engine --> External
    Engine --> Domain

    style ADKReflection fill:#D4740C,color:#E0E0E0
    style Events fill:#D4740C,color:#E0E0E0
    style MultiAgent fill:#D4740C,color:#E0E0E0
    style Proposer fill:#5B9BD5,color:#E0E0E0
    style ProposerProtocol fill:#5B9BD5,color:#E0E0E0
    style Models fill:#5B9BD5,color:#E0E0E0
```

## 6. Runtime Behavior (Sequence Diagrams)

### 6.1 Happy Path: Reflection with output_key

```mermaid
sequenceDiagram
    autonumber
    participant P as Proposer
    participant R as adk_reflection
    participant U as utils/events
    participant SS as SessionService
    participant ADK as ADK Runner
    participant LLM as LLM

    P->>R: reflect(component_text, trials)
    R->>SS: create_session(state={component_text, trials})
    SS-->>R: session

    R->>ADK: run_async(agent, message)
    Note over ADK: inject_session_state()<br/>substitutes {component_text}, {trials}
    ADK->>LLM: Generate improved text
    LLM-->>ADK: Response
    Note over ADK: output_key configured<br/>→ state_delta[output_key] = response
    ADK-->>R: events

    R->>SS: get_session(session_id)
    SS-->>R: session with updated state
    R->>U: extract_output_from_state(state, output_key)
    U-->>R: output string (or None)
    R-->>P: proposed_component_text
```

### 6.2 Fallback: State Retrieval Fails

```mermaid
sequenceDiagram
    autonumber
    participant P as Proposer
    participant R as adk_reflection
    participant SS as SessionService
    participant ADK as ADK Runner
    participant Extract as extract_final_output

    P->>R: reflect(component_text, trials)
    R->>SS: create_session(state={...})
    R->>ADK: run_async(agent, message)
    ADK-->>R: events

    R->>SS: get_session(session_id)
    SS-->>R: session (output_key not in state)

    Note over R: Fallback to event extraction
    R->>Extract: extract_final_output(events)
    Extract-->>R: output from events
    R-->>P: proposed_component_text
```

## 7. State Flow Architecture

```mermaid
flowchart LR
    subgraph Input["Input Phase"]
        CT["component_text"]
        TR["trials (JSON)"]
    end

    subgraph Session["Session State"]
        State["session.state<br/>{component_text, trials}"]
    end

    subgraph Agent["Agent Execution"]
        Instruction["Instruction with<br/>{component_text}, {trials}"]
        LLM["LLM generates<br/>improved text"]
    end

    subgraph Output["Output Phase"]
        OutputKey["session.state[output_key]"]
        Result["proposed_component_text"]
    end

    CT --> State
    TR --> State
    State -->|"inject_session_state()"| Instruction
    Instruction --> LLM
    LLM -->|"output_key auto-storage"| OutputKey
    OutputKey -->|"get_session()"| Result

    style State fill:#438DD5,color:#E0E0E0
    style OutputKey fill:#D4740C,color:#E0E0E0
```

## 8. Quality Attributes (NFRs)

| Attribute | Requirement | Verification |
|-----------|-------------|--------------|
| **Performance** | No regression from current reflection | Benchmark tests |
| **Reliability** | Fallback to event extraction on failure | Unit tests with mock failures |
| **Maintainability** | Follows existing patterns from multi_agent.py | Code review |
| **Backward Compatibility** | ReflectionFn interface unchanged | Contract tests |

## 9. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Contract** | `tests/contracts/` | ReflectionFn signature unchanged | `@pytest.mark.contract` |
| **Unit** | `tests/unit/engine/` | output_key config, state retrieval, fallback | - |
| **Integration** | `tests/integration/` | Real ADK with output_key | `@pytest.mark.external` |

**Key Test Scenarios**:
1. Output retrieved from session.state[output_key]
2. Fallback to extract_final_output when state missing
3. Template substitution with valid session state
4. Backward compatibility with existing callers

## 10. Risks & Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| ADK output_key behavior changes | Breaking change | Pin ADK version, test with CI |
| State retrieval timing issues | Empty output | Fallback to event extraction |

### Open Questions

- [x] How does ADK store output with output_key? → Researched in research.md
- [x] Does output_key work with InMemorySessionService? → Yes, confirmed in codebase

## 11. Decisions (ADR References)

| ADR | Title | Relevance to This Feature |
|-----|-------|---------------------------|
| ADR-000 | Hexagonal Architecture | Changes in engine/ only, ports unchanged |
| ADR-001 | Async-First | All operations remain async |
| ADR-002 | Protocol Interfaces | ReflectionFn signature unchanged |
| ADR-005 | Three-Layer Testing | Unit + integration + contract tests |

**New ADRs Needed**: None - follows existing patterns

# Architecture: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Status**: draft | review | approved
**Spec**: [./spec.md] | **Plan**: [./plan.md] | **Tasks**: [./tasks.md]

**Note**: This template is filled in by the `/speckit.architecture` command. It generates Mermaid-first architecture documentation from spec.md and plan.md.

## 0. Links & References

- Feature Spec: `./spec.md`
- Implementation Plan: `./plan.md`
- Tasks: `./tasks.md`
- Related ADRs: [list ADRs from plan.md Constitution Check]
- PRs: [link when available]

## 1. Purpose & Scope

### Goal

[Extract from spec.md: what this feature enables, primary value proposition]

### Non-Goals

[Explicitly out of scope - from spec.md or plan.md]

### Scope Boundaries

- **In-scope**: [concrete deliverables]
- **Out-of-scope**: [explicitly excluded items]

## 2. Architecture at a Glance

[3-7 bullet summary of the architecture - plain English, no diagrams]

- [Key architectural decision 1]
- [Key component/layer affected]
- [Integration points]
- [Data flow summary]
- [Non-functional considerations]

## 3. Context Diagram (C4 Level 1)

> Shows how this feature fits into the broader system and external dependencies.
>
> **Note**: C4 diagrams require Mermaid 9.3+. If diagrams don't render, validate at [mermaid.live](https://mermaid.live).

```mermaid
C4Context
title [Feature] - System Context

Person(user, "User", "Primary actor interacting with the system")
System(gepa, "GEPA-ADK", "Evolutionary optimization for ADK agents")

System_Ext(adk, "Google ADK", "Agent Development Kit - agent runtime")
System_Ext(llm, "LLM Provider", "LiteLLM-compatible model (Ollama, Gemini, etc.)")
System_Ext(storage, "Session Storage", "InMemory or persistent session service")

Rel(user, gepa, "Configures and runs evolution")
Rel(gepa, adk, "Executes agents", "async")
Rel(gepa, llm, "Reflection/mutation", "LiteLLM")
Rel(gepa, storage, "Session state", "ADK sessions")
```

## 4. Container Diagram (C4 Level 2)

> Shows the major containers (deployable units) within the system boundary.

```mermaid
C4Container
title [Feature] - Container View

Person(user, "User", "Developer using GEPA-ADK")

System_Boundary(gepa, "GEPA-ADK") {
  Container(api, "Public API", "Python", "evolve(), evolve_multi_agent()")
  Container(engine, "Evolution Engine", "Python", "AsyncGEPAEngine orchestration")
  Container(adapters, "Adapters", "Python", "ADKAdapter, MultiAgentAdapter")
  Container(proposer, "Mutation Proposer", "Python", "LLM-based instruction mutation")
}

System_Ext(adk, "Google ADK", "Agent runtime")
System_Ext(llm, "LLM Provider", "Reflection model")

Rel(user, api, "Calls", "async Python")
Rel(api, engine, "Delegates")
Rel(engine, adapters, "Evaluates via")
Rel(adapters, adk, "Runs agents", "ADK Runner")
Rel(engine, proposer, "Mutates via")
Rel(proposer, llm, "Generates", "LiteLLM")
```

## 5. Component Diagram (C4 Level 3)

> Shows the internal components of a container - use only when Container view is too coarse.

```mermaid
C4Component
title [Feature] - Component View (Adapters Container)

Container_Boundary(adapters, "Adapters Layer") {
  Component(adk_adapter, "ADKAdapter", "Class", "Single-agent evaluation")
  Component(multi_adapter, "MultiAgentAdapter", "Class", "Multi-agent pipeline evaluation")
  Component(scorer, "Scorer", "Protocol", "Output scoring interface")
}

Container_Boundary(ports, "Ports Layer") {
  Component(gepa_protocol, "AsyncGEPAAdapter", "Protocol", "Adapter interface contract")
  Component(scorer_protocol, "Scorer", "Protocol", "Scoring interface contract")
}

Rel(adk_adapter, gepa_protocol, "Implements")
Rel(multi_adapter, gepa_protocol, "Implements")
Rel(adk_adapter, scorer, "Uses")
Rel(multi_adapter, scorer, "Uses")
```

## 6. Hexagonal Architecture View

> Project-specific: Shows how this feature aligns with the hexagonal (ports & adapters) architecture.

```mermaid
flowchart TB
    subgraph External["External Systems"]
        ADK["Google ADK"]
        LLM["LLM Provider"]
        Storage["Session Storage"]
    end

    subgraph Adapters["adapters/ (External Integration)"]
        ADKAdapter["ADKAdapter"]
        MultiAgent["MultiAgentAdapter"]
        Proposer["AsyncReflectiveMutationProposer"]
    end

    subgraph Ports["ports/ (Interfaces)"]
        AdapterPort["AsyncGEPAAdapter Protocol"]
        ScorerPort["Scorer Protocol"]
        ProposerPort["MutationProposer Protocol"]
    end

    subgraph Engine["engine/ (Orchestration)"]
        GEPAEngine["AsyncGEPAEngine"]
    end

    subgraph Domain["domain/ (Pure Python)"]
        Models["EvolutionConfig, Candidate"]
        Types["TrajectoryConfig, etc."]
        Exceptions["EvolutionError hierarchy"]
    end

    subgraph API["api.py (Public Interface)"]
        Evolve["evolve()"]
        EvolveGroup["evolve_multi_agent()"]
    end

    API --> Engine
    Engine --> Ports
    Ports --> Adapters
    Adapters --> External
    Engine --> Domain
```

## 7. Runtime Behavior (Sequence Diagrams)

### 7.1 Happy Path: [Primary Flow Name]

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant API as api.py
    participant E as Engine
    participant A as Adapter
    participant P as Proposer
    participant ADK as Google ADK
    participant LLM as LLM Provider

    U->>API: evolve(agent, trainset, config)
    API->>E: run evolution loop
    loop Each iteration
        E->>A: evaluate(batch, candidate)
        A->>ADK: run_async(agent, input)
        ADK-->>A: events/output
        A->>A: score outputs
        A-->>E: EvaluationBatch

        E->>A: make_reflective_dataset()
        A-->>E: feedback dataset

        E->>P: propose(candidate, dataset)
        P->>LLM: acompletion(prompt)
        LLM-->>P: improved instruction
        P-->>E: mutated candidate
    end
    E-->>API: best candidate
    API-->>U: EvolutionResult
```

### 7.2 Error/Edge Case: [Failure Scenario Name]

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant A as Adapter
    participant ADK as Google ADK

    U->>A: evaluate(batch, candidate)
    A->>ADK: run_async(agent, input)
    ADK-->>A: error/timeout

    Note over A: Capture error in trajectory
    A->>A: score = 0.0, output = ""
    A-->>U: EvaluationBatch with error trajectory
```

## 8. Data Model & Contracts

### 8.1 Data Changes (ERD)

> Include only if this feature adds/modifies persistent data structures.

```mermaid
erDiagram
    EVOLUTION_CONFIG {
        string reflection_model
        int max_iterations
        int population_size
    }
    CANDIDATE {
        dict components
        float score
    }
    TRAJECTORY {
        string input
        string output
        list tool_calls
        string error
    }
    EVOLUTION_CONFIG ||--o{ CANDIDATE : "produces"
    CANDIDATE ||--o{ TRAJECTORY : "has"
```

### 8.2 API Contracts

**Public API Changes**:
- `evolve()` — [describe parameter/return changes]
- `EvolutionConfig` — [describe new fields]

**Internal Protocol Changes**:
- `AsyncGEPAAdapter` — [describe method signature changes]

## 9. Deployment / Infrastructure View

> Include only if infrastructure or deployment is relevant to this feature.

```mermaid
flowchart LR
    subgraph Local["Local Development"]
        CLI[CLI]
        Ollama[Ollama LLM]
    end
    subgraph Cloud["Production"]
        API[GEPA-ADK API]
        Gemini[Gemini API]
    end

    CLI --> Ollama
    API --> Gemini
```

## 10. Quality Attributes (NFRs)

| Attribute | Requirement | Verification |
|-----------|-------------|--------------|
| **Performance** | [e.g., <100ms per evaluation] | Integration tests with timing |
| **Reliability** | [e.g., Graceful degradation on LLM failure] | Error handling tests |
| **Security** | [e.g., No secrets in logs] | Code review, TrajectoryConfig |
| **Maintainability** | [e.g., Hexagonal architecture compliance] | Layer import rules |
| **Observability** | [e.g., Structured logging with context] | Log format verification |

## 11. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Contract** | `tests/contracts/` | Protocol compliance | `@pytest.mark.contract` |
| **Unit** | `tests/unit/` | Business logic with mocks | `@pytest.mark.unit` |
| **Integration** | `tests/integration/` | Real ADK/LLM calls | `@pytest.mark.integration` |

**Key Test Scenarios**:
1. [Happy path test description]
2. [Error handling test description]
3. [Edge case test description]

## 12. Risks & Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk 1] | [Impact description] | [Mitigation strategy] |

### Open Questions

- [ ] [Question 1 - needs resolution before implementation]
- [ ] [Question 2 - can be resolved during implementation]

### TODOs

- [ ] [Follow-up item tracked in tasks.md]

## 13. Decisions (ADR References)

| ADR | Title | Relevance to This Feature |
|-----|-------|---------------------------|
| ADR-000 | Hexagonal Architecture | [How this feature complies] |
| ADR-001 | Async-First | [Async patterns used] |
| ADR-002 | Protocol Interfaces | [Protocols affected] |
| ADR-005 | Three-Layer Testing | [Test strategy alignment] |

**New ADRs Needed**:
- [ ] ADR-XXX: [Title] — [Brief rationale if new decision required]

---

## Diagram Standards Reference

This document uses the following diagram types:

| Diagram Type | Purpose | When to Use |
|--------------|---------|-------------|
| **C4 Context** | System boundaries & external actors | Always |
| **C4 Container** | Deployable units within system | Always |
| **C4 Component** | Internal structure of a container | When container is complex |
| **Hexagonal** | Ports & adapters architecture view | Project-specific (always for this project) |
| **Sequence** | Runtime interactions | 1-2 key flows (happy path + error) |
| **ERD** | Data model changes | When persistence is involved |
| **Architecture-beta** | Deployment/infrastructure | When infra matters |

**Mermaid Resources**:
- [Mermaid Live Editor](https://mermaid.live/) — Validate diagrams
- [C4 Diagrams in Mermaid](https://mermaid.js.org/syntax/c4.html)
- [Sequence Diagrams](https://mermaid.js.org/syntax/sequenceDiagram.html)
- [ER Diagrams](https://mermaid.js.org/syntax/entityRelationshipDiagram.html)

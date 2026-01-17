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

### Constraints

> Technical or organizational constraints affecting this feature (from arc42 best practices)

- **Technical**: [e.g., Must use existing database, Python 3.12+, no new dependencies]
- **Organizational**: [e.g., Must follow hexagonal architecture, ADR compliance required]
- **Conventions**: [e.g., Naming conventions, API patterns to follow]

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
> **Note**: Uses flowchart TB for better layout control. Validate at [mermaid.live](https://mermaid.live).

```mermaid
flowchart TB
    subgraph Legend[" "]
        direction LR
        l1["👤 Actor"]
        l2["🔷 System"]
        l3["📦 External"]
    end

    subgraph Actors[" "]
        user["👤 User<br/><i>Primary actor interacting<br/>with the system</i>"]
    end

    subgraph System[" "]
        gepa["🔷 GEPA-ADK<br/><i>Evolutionary optimization<br/>for ADK agents</i>"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>Agent Development Kit -<br/>agent runtime</i>"]
        llm["📦 LLM Provider<br/><i>LiteLLM-compatible model<br/>(Ollama, Gemini, etc.)</i>"]
        storage["📦 Session Storage<br/><i>InMemory or persistent<br/>session service</i>"]
    end

    user -->|"Configures and<br/>runs evolution"| gepa
    gepa -->|"Executes agents<br/>(async)"| adk
    gepa -->|"Reflection/mutation<br/>(LiteLLM)"| llm
    gepa -->|"Session state<br/>(ADK sessions)"| storage

    style l1 fill:#1168BD,color:#E0E0E0
    style l2 fill:#438DD5,color:#E0E0E0
    style l3 fill:#666666,color:#E0E0E0
    style gepa fill:#438DD5,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style storage fill:#666666,color:#E0E0E0
    style user fill:#1168BD,color:#E0E0E0
```

## 4. Container Diagram (C4 Level 2)

> Shows the major containers (deployable units) within the system boundary.

```mermaid
flowchart TB
    subgraph Actors[" "]
        user["👤 User<br/><i>Developer using GEPA-ADK</i>"]
    end

    subgraph GEPA["GEPA-ADK"]
        api["🔷 Public API<br/><i>Python</i><br/>evolve(), evolve_multi_agent()"]
        engine["🔷 Evolution Engine<br/><i>Python</i><br/>AsyncGEPAEngine orchestration"]
        adapters["🔷 Adapters<br/><i>Python</i><br/>ADKAdapter, MultiAgentAdapter"]
        proposer["🔷 Mutation Proposer<br/><i>Python</i><br/>LLM-based instruction mutation"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>Agent runtime</i>"]
        llm["📦 LLM Provider<br/><i>Reflection model</i>"]
    end

    user -->|"Calls<br/>(async Python)"| api
    api -->|"Delegates"| engine
    engine -->|"Evaluates via"| adapters
    adapters -->|"Runs agents<br/>(ADK Runner)"| adk
    engine -->|"Mutates via"| proposer
    proposer -->|"Generates<br/>(LiteLLM)"| llm

    style api fill:#438DD5,color:#E0E0E0
    style engine fill:#438DD5,color:#E0E0E0
    style adapters fill:#438DD5,color:#E0E0E0
    style proposer fill:#438DD5,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style user fill:#1168BD,color:#E0E0E0
```

## 5. Component Diagram (C4 Level 3)

> Shows the internal components of a container - use only when Container view is too coarse.

```mermaid
flowchart TB
    subgraph adapters["Adapters Layer"]
        adk_adapter["📦 ADKAdapter<br/><i>Class</i><br/>Single-agent evaluation"]
        multi_adapter["📦 MultiAgentAdapter<br/><i>Class</i><br/>Multi-agent pipeline evaluation"]
        scorer["📦 Scorer<br/><i>Protocol</i><br/>Output scoring interface"]
    end

    subgraph ports["Ports Layer"]
        gepa_protocol["📦 AsyncGEPAAdapter<br/><i>Protocol</i><br/>Adapter interface contract"]
        scorer_protocol["📦 Scorer<br/><i>Protocol</i><br/>Scoring interface contract"]
    end

    adk_adapter -->|"Implements"| gepa_protocol
    multi_adapter -->|"Implements"| gepa_protocol
    adk_adapter -->|"Uses"| scorer
    multi_adapter -->|"Uses"| scorer

    style adk_adapter fill:#5B9BD5,color:#E0E0E0
    style multi_adapter fill:#5B9BD5,color:#E0E0E0
    style scorer fill:#5B9BD5,color:#E0E0E0
    style gepa_protocol fill:#5B9BD5,color:#E0E0E0
    style scorer_protocol fill:#5B9BD5,color:#E0E0E0
```

## 6. Code Diagram (C4 Level 4)

> Shows class/module relationships - use only when class structure clarifies the design. Optional for simple features.

```mermaid
classDiagram
    class EvolutionConfig {
        +str reflection_model
        +int max_iterations
        +int max_concurrent_evals
        +__post_init__()
    }

    class ADKAdapter {
        -_proposer: ProposerProtocol
        -_session_service: SessionService
        +evaluate(batch, candidate) EvaluationBatch
        +make_reflective_dataset() ReflectiveDataset
    }

    class AsyncReflectiveMutationProposer {
        -model: str
        -prompt_template: str
        +propose(candidate, dataset) Candidate
    }

    class ProposerProtocol {
        <<protocol>>
        +propose(candidate, dataset) Candidate
    }

    EvolutionConfig --> ADKAdapter : configures
    ADKAdapter --> AsyncReflectiveMutationProposer : creates
    AsyncReflectiveMutationProposer ..|> ProposerProtocol : implements
```

## 7. Hexagonal Architecture View

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

## 8. Runtime Behavior (Sequence Diagrams)

### 8.1 Happy Path: [Primary Flow Name]

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

### 8.2 Error/Edge Case: [Failure Scenario Name]

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

## 9. Data Model & Contracts

### 9.1 Data Changes (ERD)

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

### 9.2 API Contracts

**Public API Changes**:
- `evolve()` — [describe parameter/return changes]
- `EvolutionConfig` — [describe new fields]

**Internal Protocol Changes**:
- `AsyncGEPAAdapter` — [describe method signature changes]

## 10. Deployment / Infrastructure View

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

## 11. Quality Attributes (NFRs)

| Attribute | Requirement | Verification |
|-----------|-------------|--------------|
| **Performance** | [e.g., <100ms per evaluation] | Integration tests with timing |
| **Reliability** | [e.g., Graceful degradation on LLM failure] | Error handling tests |
| **Security** | [e.g., No secrets in logs] | Code review, TrajectoryConfig |
| **Maintainability** | [e.g., Hexagonal architecture compliance] | Layer import rules |
| **Observability** | [e.g., Structured logging with context] | Log format verification |

## 12. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Contract** | `tests/contracts/` | Protocol compliance | `@pytest.mark.contract` |
| **Unit** | `tests/unit/` | Business logic with mocks | `@pytest.mark.unit` |
| **Integration** | `tests/integration/` | Real ADK/LLM calls | `@pytest.mark.integration` |

**Key Test Scenarios**:
1. [Happy path test description]
2. [Error handling test description]
3. [Edge case test description]

## 13. Risks & Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk 1] | [Impact description] | [Mitigation strategy] |

### Open Questions

- [ ] [Question 1 - needs resolution before implementation]
- [ ] [Question 2 - can be resolved during implementation]

### TODOs

- [ ] [Follow-up item tracked in tasks.md]

## 14. Decisions (ADR References)

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
| **Flowchart** | Deployment/infrastructure | When infra matters |

### Why flowchart TB instead of native C4?

We use `flowchart TB` instead of Mermaid's native C4 syntax because:
- **Stability**: Mermaid C4 is [experimental and may change](https://mermaid.js.org/syntax/c4.html)
- **Layout control**: flowchart allows TB (top-to-bottom) orientation
- **Styling flexibility**: Full control over colors and text

### C4 Color Scheme (Accessibility-First)

**Design Principles** (based on [WCAG 2.1 AA](https://www.w3.org/WAI/WCAG21/quickref/)):
- **4.5:1 contrast ratio** minimum for text
- **Blue/Gray palette** is colorblind-safe (avoids red/green)
- **Soft white text** (`#E0E0E0`) reduces eye strain on dark backgrounds
- **Icons + labels** ensure meaning isn't conveyed by color alone

| Element Type | Icon | Fill Color | Text | Contrast | Usage |
|--------------|------|------------|------|----------|-------|
| Person/Actor | 👤 | `#1168BD` | `#E0E0E0` | 7.2:1 | Users, developers, external actors |
| System (main) | 🔷 | `#438DD5` | `#E0E0E0` | 4.6:1 | Primary system being documented |
| Container | 🔷 | `#438DD5` | `#E0E0E0` | 4.6:1 | Deployable units within system |
| Component | 📦 | `#5B9BD5` | `#E0E0E0` | 4.5:1 | Internal classes, modules, protocols |
| External | 📦 | `#666666` | `#E0E0E0` | 5.7:1 | Third-party systems, external services |
| **Modified** | 🔶 | `#D4740C` | `#E0E0E0` | 4.5:1 | Highlight changed components (orange) |

**Best Practices** (from [C4 Model](https://c4model.com/)):
- Every element needs: **name, type, technology, description**
- Include a **legend** on every diagram
- Don't show internal details of external systems
- Keep diagrams **focused** - multiple small > one large

**Pattern for C4 nodes**:
```
node_id["ICON Title<br/><i>Technology/Type</i><br/>Brief description"]
```

**Example with Legend**:
```mermaid
flowchart TB
    subgraph Legend[" "]
        direction LR
        l1["👤 Actor"]
        l2["🔷 System"]
        l3["📦 External"]
    end

    user["👤 Developer<br/><i>Primary actor</i>"]
    system["🔷 My System<br/><i>Python</i><br/>Does something useful"]
    external["📦 External API<br/><i>Third-party service</i>"]

    user --> system --> external

    style l1 fill:#1168BD,color:#E0E0E0
    style l2 fill:#438DD5,color:#E0E0E0
    style l3 fill:#666666,color:#E0E0E0
    style user fill:#1168BD,color:#E0E0E0
    style system fill:#438DD5,color:#E0E0E0
    style external fill:#666666,color:#E0E0E0
```

**Resources**:
- [Mermaid Live Editor](https://mermaid.live/) — Validate diagrams
- [C4 Model](https://c4model.com/) — Official C4 documentation
- [Colorblind Safe Palettes](https://davidmathlogic.com/colorblind/) — Verify accessibility
- [WCAG Contrast Checker](https://webaim.org/resources/contrastchecker/) — Test ratios

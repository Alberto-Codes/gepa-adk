# Architecture: Pareto Frontier Tracking and Candidate Selection

**Feature**: 022-pareto-frontier
**Date**: 2026-01-14

## Overview

This document describes the architectural design for integrating Pareto frontier tracking and candidate selection strategies into gepa-adk's evolution engine.

---

## System Context

The Pareto frontier system integrates into gepa-adk's existing hexagonal architecture, adding new domain models, a port protocol, and strategy implementations.

```mermaid
flowchart TB
    subgraph External["External Systems"]
        ADK[Google ADK]
        LLM[LLM Provider]
    end

    subgraph PublicAPI["Public API Layer"]
        API[api.py<br/>evolve/evolve_sync]
    end

    subgraph Engine["Engine Layer"]
        AE[AsyncGEPAEngine]
    end

    subgraph Ports["Ports Layer"]
        AP[AsyncGEPAAdapter<br/>Protocol]
        CSP[CandidateSelectorProtocol<br/>NEW]
    end

    subgraph Domain["Domain Layer"]
        PS[ParetoState<br/>NEW]
        PF[ParetoFrontier<br/>NEW]
        C[Candidate]
        EC[EvolutionConfig]
    end

    subgraph Strategies["Strategies Layer"]
        PCS[ParetoCandidateSelector<br/>NEW]
        CBCS[CurrentBestCandidateSelector<br/>NEW]
        EGCS[EpsilonGreedyCandidateSelector<br/>NEW]
    end

    subgraph Adapters["Adapters Layer"]
        AA[ADKAdapter]
    end

    API --> AE
    AE --> AP
    AE --> CSP
    AE --> PS
    PS --> PF
    PS --> C
    CSP -.->|implements| PCS
    CSP -.->|implements| CBCS
    CSP -.->|implements| EGCS
    AP -.->|implements| AA
    AA --> ADK
    AA --> LLM
```

---

## Layer Responsibilities

### Domain Layer (No External Dependencies)

```mermaid
classDiagram
    class ParetoState {
        +list~Candidate~ candidates
        +dict~int, dict~int, float~~ candidate_scores
        +ParetoFrontier frontier
        +FrontierType frontier_type
        +int iteration
        +int best_average_idx
        +int stagnation_counter
        +float original_score
        +add_candidate(candidate, scores) int
        +get_average_score(candidate_idx) float
        +update_best_average() void
    }

    class ParetoFrontier {
        +dict~int, set~int~~ example_leaders
        +dict~int, float~ best_scores
        +update(candidate_idx, scores) void
        +get_non_dominated() set~int~
        +get_selection_weights() dict~int, int~
    }

    class Candidate {
        +dict~str, str~ components
        +int generation
        +str parent_id
        +dict~str, Any~ metadata
    }

    class FrontierType {
        <<enumeration>>
        INSTANCE
        OBJECTIVE
        HYBRID
        CARTESIAN
    }

    ParetoState "1" *-- "1" ParetoFrontier : contains
    ParetoState "1" *-- "*" Candidate : tracks
    ParetoState --> FrontierType : uses
```

### Ports Layer (Protocol Definitions)

```mermaid
classDiagram
    class CandidateSelectorProtocol {
        <<protocol>>
        +select(state: ParetoState) int
    }

    class AsyncGEPAAdapter {
        <<protocol>>
        +evaluate(batch, candidate, capture_traces) EvaluationBatch
        +make_reflective_dataset(candidate, eval_batch, components) Mapping
        +propose_new_texts(candidate, dataset, components) dict
    }

    note for CandidateSelectorProtocol "NEW: Enables pluggable selection strategies"
```

### Strategies Layer (Algorithm Implementations)

```mermaid
classDiagram
    class CandidateSelectorProtocol {
        <<protocol>>
        +select(state: ParetoState) int
    }

    class ParetoCandidateSelector {
        -Random rng
        +__init__(rng: Random)
        +select(state: ParetoState) int
    }

    class CurrentBestCandidateSelector {
        +select(state: ParetoState) int
    }

    class EpsilonGreedyCandidateSelector {
        -float epsilon
        -Random rng
        +__init__(epsilon: float, rng: Random)
        +select(state: ParetoState) int
    }

    CandidateSelectorProtocol <|.. ParetoCandidateSelector : implements
    CandidateSelectorProtocol <|.. CurrentBestCandidateSelector : implements
    CandidateSelectorProtocol <|.. EpsilonGreedyCandidateSelector : implements
```

---

## Data Flow

### Evolution Loop with Pareto Selection

```mermaid
sequenceDiagram
    autonumber
    participant API as Public API
    participant Engine as AsyncGEPAEngine
    participant Selector as CandidateSelector
    participant State as ParetoState
    participant Adapter as ADKAdapter

    API->>Engine: run()

    rect rgb(240, 248, 255)
        Note over Engine,State: Initialization Phase
        Engine->>Adapter: evaluate(batch, initial_candidate)
        Adapter-->>Engine: EvaluationBatch (per-example scores)
        Engine->>State: add_candidate(initial, scores)
        State->>State: update frontier
    end

    loop Evolution Iterations
        rect rgb(255, 250, 240)
            Note over Engine,Selector: Selection Phase
            Engine->>Selector: select(state)
            Selector->>State: get frontier weights
            State-->>Selector: selection weights
            Selector-->>Engine: parent_candidate_idx
        end

        rect rgb(240, 255, 240)
            Note over Engine,Adapter: Mutation Phase
            Engine->>Adapter: make_reflective_dataset(parent)
            Adapter-->>Engine: reflective_dataset
            Engine->>Adapter: propose_new_texts(parent, dataset)
            Adapter-->>Engine: proposed_candidate
        end

        rect rgb(255, 240, 245)
            Note over Engine,State: Evaluation Phase
            Engine->>Adapter: evaluate(batch, proposal)
            Adapter-->>Engine: EvaluationBatch
            Engine->>State: add_candidate(proposal, scores)
            State->>State: update frontier
            State->>State: update best_average_idx
        end
    end

    Engine-->>API: EvolutionResult
```

### Pareto Frontier Update

```mermaid
flowchart TD
    subgraph Input
        NC[New Candidate]
        SC[Scores per Example]
    end

    subgraph UpdateProcess["Frontier Update Process"]
        A["For each example_idx in scores"]
        B{"score > best_scores(example_idx)?"}
        C["Replace leader set with new_candidate"]
        D{"score == best_scores(example_idx)?"}
        E["Add new_candidate to leader set"]
        F["No change to frontier"]
        G["Update best_scores(example_idx)"]
    end

    subgraph Output
        UF[Updated Frontier]
    end

    NC --> A
    SC --> A
    A --> B
    B -->|Yes| C
    B -->|No| D
    C --> G
    D -->|Yes| E
    D -->|No| F
    E --> G
    G --> UF
    F --> UF
```

---

## State Transitions

### ParetoState Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Empty: Create ParetoState()

    Empty --> Initialized: add_candidate(initial, scores)
    note right of Initialized: frontier has 1 candidate<br/>best_average_idx = 0

    Initialized --> Evolving: add_candidate(proposal, scores)
    note right of Evolving: frontier updated<br/>best may change

    Evolving --> Evolving: add_candidate(proposal, scores)

    Evolving --> Converged: max_iterations or patience exhausted

    Converged --> [*]: return EvolutionResult
```

### Candidate Selection Decision

```mermaid
flowchart TD
    Start{Which Selector?}

    Start -->|Pareto| P1[Get non-dominated candidates]
    P1 --> P2[Calculate selection weights]
    P2 --> P3[Sample proportional to weights]
    P3 --> Return[Return candidate_idx]

    Start -->|Greedy| G1[Return state.best_average_idx]
    G1 --> Return

    Start -->|Epsilon-Greedy| E1{random < epsilon?}
    E1 -->|Yes| E2[Return random candidate_idx]
    E1 -->|No| E3[Return state.best_average_idx]
    E2 --> Return
    E3 --> Return
```

---

## Pareto Selection Algorithm

### Non-Dominated Candidate Identification

```mermaid
flowchart LR
    subgraph Candidates["Candidate Scores"]
        C0["C0: [0.9, 0.5]"]
        C1["C1: [0.5, 0.9]"]
        C2["C2: [0.6, 0.6]"]
    end

    subgraph Frontier["Pareto Frontier"]
        E0["Example 0<br/>Leader: C0 (0.9)"]
        E1["Example 1<br/>Leader: C1 (0.9)"]
    end

    subgraph NonDom["Non-Dominated Set"]
        ND["{C0, C1}"]
    end

    C0 --> E0
    C1 --> E1
    E0 --> ND
    E1 --> ND

    note["C2 is dominated:<br/>neither best on any example"]
```

### Selection Weight Calculation

```mermaid
flowchart TD
    subgraph ExampleLeaders["example_leaders"]
        EL0["Example 0: {C0}"]
        EL1["Example 1: {C1, C3}"]
        EL2["Example 2: {C0, C1}"]
    end

    subgraph Frequency["Count Appearances"]
        F0["C0: 2 (Ex 0, Ex 2)"]
        F1["C1: 2 (Ex 1, Ex 2)"]
        F3["C3: 1 (Ex 1)"]
    end

    subgraph Sampling["Sampling List"]
        SL["[C0, C0, C1, C1, C3]"]
    end

    subgraph Result["Random Selection"]
        R["C0: 40%, C1: 40%, C3: 20%"]
    end

    EL0 --> Frequency
    EL1 --> Frequency
    EL2 --> Frequency
    Frequency --> SL
    SL --> R
```

---

## Integration Points

### Engine Modification

```mermaid
flowchart TB
    subgraph Before["Current AsyncGEPAEngine"]
        B1[_EngineState]
        B2[Always selects best_candidate]
        B3[Single best tracking]
    end

    subgraph After["Modified AsyncGEPAEngine"]
        A1[ParetoState<br/>when selector provided]
        A2[CandidateSelectorProtocol.select]
        A3[Per-example score tracking]
        A4[Frontier-based exploration]
    end

    Before -->|"Add optional<br/>candidate_selector"| After
```

### Public API Change

```mermaid
flowchart LR
    subgraph CurrentAPI["Current API"]
        C1["evolve(agent, trainset,<br/>config=None)"]
    end

    subgraph NewAPI["New API"]
        N1["evolve(agent, trainset,<br/>config=None,<br/>candidate_selector=None)"]
    end

    CurrentAPI -->|"Add optional parameter"| NewAPI

    subgraph Behavior
        B1{candidate_selector<br/>provided?}
        B2[Use ParetoState<br/>+ selector]
        B3[Use _EngineState<br/>+ greedy]
    end

    N1 --> B1
    B1 -->|Yes| B2
    B1 -->|No| B3
```

---

## File Structure

```mermaid
flowchart TB
    subgraph src/gepa_adk
        subgraph domain
            D1[models.py<br/>Existing]
            D2[state.py<br/>NEW: ParetoState, ParetoFrontier]
            D3[types.py<br/>MOD: +FrontierType]
        end

        subgraph ports
            P1[adapter.py<br/>Existing]
            P2[selector.py<br/>NEW: CandidateSelectorProtocol]
        end

        subgraph strategies
            S1[candidate_selector.py<br/>NEW: All 3 selectors]
        end

        subgraph engine
            E1[async_engine.py<br/>MOD: +selector integration]
        end

        API1[api.py<br/>MOD: +candidate_selector param]
    end

    subgraph tests
        T1[contracts/test_candidate_selector_protocol.py]
        T2[unit/test_pareto_state.py]
        T3[unit/test_candidate_selectors.py]
        T4[integration/test_pareto_evolution.py]
    end

    D2 --> P2
    P2 --> S1
    S1 --> E1
    E1 --> API1
```

---

## Summary

The Pareto frontier architecture:

1. **Preserves hexagonal boundaries**: Domain models have no external deps
2. **Uses protocol-based injection**: Engine receives selector via constructor
3. **Maintains backward compatibility**: Default behavior unchanged without selector
4. **Enables extensibility**: New selectors can be added by implementing the protocol
5. **Supports testing at all layers**: Contract, unit, and integration tests

Key design decisions:
- Selectors are stateless algorithms (except RNG state)
- Frontier updates are incremental (O(m) per candidate, where m = examples)
- Selection is lazy (dominance removal only at selection time)

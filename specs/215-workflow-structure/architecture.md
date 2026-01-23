# Architecture: Execute Workflows As-Is (Preserve Structure)

**Feature**: 215-workflow-structure
**Date**: 2026-01-22

> **Scope**: This is a focused refactor within the adapters layer. Full C4 diagrams are not warranted; this document captures the key architectural change.

## 1. Purpose

Replace the flattening behavior in `_build_pipeline()` with structure-preserving recursive cloning to enable proper execution of LoopAgent, ParallelAgent, and nested workflows.

## 2. Affected Components

```mermaid
graph TD
    subgraph "Public API (No Change)"
        A[evolve_workflow]
    end

    subgraph "Adapters Layer (Changes)"
        B[MultiAgentAdapter]
        C[workflow.py]
    end

    subgraph "ADK (External)"
        D[SequentialAgent]
        E[LoopAgent]
        F[ParallelAgent]
        G[LlmAgent]
    end

    A --> B
    B --> C
    C --> D
    C --> E
    C --> F
    C --> G

    style C fill:#90EE90
    style B fill:#FFE4B5
```

**Legend**:
- Green: New function added
- Orange: Existing code modified

## 3. Key Change: Cloning Flow

### Before (Flattening)

```mermaid
sequenceDiagram
    participant MA as MultiAgentAdapter
    participant BP as _build_pipeline()
    participant SA as SequentialAgent

    MA->>BP: candidate dict
    BP->>BP: Clone each LlmAgent
    BP->>SA: Create wrapper
    SA-->>MA: Flat SequentialAgent

    Note over MA,SA: LoopAgent.max_iterations LOST
    Note over MA,SA: ParallelAgent becomes sequential
```

### After (Structure Preservation)

```mermaid
sequenceDiagram
    participant MA as MultiAgentAdapter
    participant CW as clone_workflow_with_overrides()
    participant WF as Original Workflow
    participant CL as Cloned Workflow

    MA->>CW: workflow, candidate
    CW->>WF: Read structure
    CW->>CW: Recursive clone
    CW->>CL: Construct with clones
    CL-->>MA: Same type as original

    Note over MA,CL: LoopAgent.max_iterations PRESERVED
    Note over MA,CL: ParallelAgent stays parallel
```

## 4. Recursive Cloning Algorithm

```mermaid
flowchart TD
    A[clone_workflow_with_overrides] --> B{Agent Type?}

    B -->|LlmAgent| C[Get instruction override]
    C --> D[model_copy with override]
    D --> E[Return cloned LlmAgent]

    B -->|SequentialAgent| F[Clone each sub_agent]
    F --> G[Construct new SequentialAgent]
    G --> H[Return cloned Sequential]

    B -->|LoopAgent| I[Clone each sub_agent]
    I --> J[Construct new LoopAgent]
    J --> K[Copy max_iterations]
    K --> L[Return cloned Loop]

    B -->|ParallelAgent| M[Clone each sub_agent]
    M --> N[Construct new ParallelAgent]
    N --> O[Return cloned Parallel]

    style K fill:#FFD700
```

**Note**: Yellow highlights the critical preservation of `max_iterations`.

## 5. Integration Points

| Component | File | Change Type |
|-----------|------|-------------|
| `clone_workflow_with_overrides()` | `adapters/workflow.py` | New function |
| `MultiAgentAdapter.__init__` | `adapters/multi_agent.py` | Store original workflow |
| `MultiAgentAdapter._build_pipeline` | `adapters/multi_agent.py` | Call cloning function |
| `MultiAgentAdapter._extract_primary_output` | `adapters/multi_agent.py` | Handle loop outputs |

## 6. Testing Strategy

```mermaid
graph LR
    subgraph "Unit Tests"
        U1[test_clone_llm_agent]
        U2[test_clone_sequential]
        U3[test_clone_loop_preserves_iterations]
        U4[test_clone_parallel]
        U5[test_clone_nested]
    end

    subgraph "Integration Tests"
        I1[test_loop_executes_n_times]
        I2[test_parallel_concurrent]
        I3[test_nested_workflow_e2e]
    end

    U1 --> I1
    U3 --> I1
    U4 --> I2
    U5 --> I3
```

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing tests | Medium | Run full test suite, update assertions |
| Performance regression | Low | Recursive cloning is O(n) where n = agents |
| ADK compatibility | Low | Using standard model_copy() pattern |
| Deep nesting stack overflow | Very Low | Respect existing max_depth limit |

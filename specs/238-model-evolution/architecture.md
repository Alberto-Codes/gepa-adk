# Architecture: Model Evolution Support

**Branch**: `238-model-evolution` | **Date**: 2026-01-27 | **Status**: draft
**Spec**: [./spec.md](./spec.md) | **Plan**: [./plan.md](./plan.md) | **Tasks**: [./tasks.md](./tasks.md)

## 0. Links & References

- Feature Spec: `./spec.md`
- Implementation Plan: `./plan.md`
- Tasks: `./tasks.md` (pending)
- Related ADRs:
  - ADR-000: Hexagonal Architecture
  - ADR-002: Protocol for Interfaces
  - ADR-005: Three-Layer Testing
  - ADR-008: Structured Logging
- GitHub Issue: [#238](https://github.com/Alberto-Codes/gepa-adk/issues/238)

## 1. Purpose & Scope

### Goal

Enable evolutionary optimization of the model used by ADK agents, allowing users to discover the best-performing model from a set of allowed choices through the same process used for instruction, schema, and config evolution.

### Non-Goals

- Model performance benchmarking (separate from evolution)
- Automatic model discovery (user must provide explicit choices)
- Model cost optimization (user responsibility)
- Validation of model accessibility at configuration time

### Scope Boundaries

- **In-scope**:
  - `ModelConstraints` dataclass for allowed model choices
  - `ModelHandler` implementing `ComponentHandler` protocol
  - `create_model_reflection_agent()` factory function
  - `model_choices` parameter for `evolve()` API
  - Wrapper preservation during model mutation

- **Out-of-scope**:
  - Model cost tracking
  - Model capability analysis
  - Automatic model selection heuristics

### Constraints

- **Technical**: Python 3.12+, no new dependencies, ADK >= 1.22.0
- **Organizational**: Hexagonal architecture compliance, three-layer testing
- **Conventions**: Follow existing `SchemaConstraints` and `OutputSchemaHandler` patterns

## 2. Architecture at a Glance

- **New component type**: "model" joins existing instruction, output_schema, generate_content_config
- **Opt-in design**: Model evolution requires explicit `model_choices` parameter
- **Wrapper preservation**: Duck-typing on `.model` attribute enables in-place mutation
- **Existing integration**: Extends ComponentHandler protocol, no new protocols needed
- **Four layers touched**: domain (types), adapters (handlers), engine (reflection), api

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
        user["👤 Developer<br/><i>Uses gepa-adk to<br/>evolve agents</i>"]
    end

    subgraph System[" "]
        gepa["🔶 GEPA-ADK<br/><i>Now with model<br/>evolution support</i>"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>LlmAgent, BaseLlm,<br/>LiteLlm types</i>"]
        llm["📦 LLM Providers<br/><i>Multiple models<br/>to choose from</i>"]
    end

    user -->|"Provides model_choices<br/>for evolution"| gepa
    gepa -->|"Mutates agent.model<br/>during evaluation"| adk
    gepa -->|"Tests each model<br/>candidate"| llm

    style l1 fill:#1168BD,color:#E0E0E0
    style l2 fill:#438DD5,color:#E0E0E0
    style l3 fill:#666666,color:#E0E0E0
    style l4 fill:#D4740C,color:#E0E0E0
    style gepa fill:#D4740C,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style user fill:#1168BD,color:#E0E0E0
```

## 4. Container Diagram (C4 Level 2)

```mermaid
flowchart TB
    subgraph Actors[" "]
        user["👤 Developer"]
    end

    subgraph GEPA["GEPA-ADK"]
        api["🔶 Public API<br/><i>Python</i><br/>evolve(model_choices=...)"]
        engine["🔷 Evolution Engine<br/><i>Python</i><br/>Orchestrates evolution"]
        adapters["🔶 Adapters<br/><i>Python</i><br/>ModelHandler + existing"]
        reflection["🔶 Reflection Agents<br/><i>Python</i><br/>create_model_reflection_agent"]
    end

    subgraph External[" "]
        adk["📦 Google ADK"]
        llm["📦 LLM Provider"]
    end

    user -->|"evolve(model_choices=...)"| api
    api -->|"Configures"| engine
    engine -->|"Uses"| adapters
    engine -->|"Creates"| reflection
    adapters -->|"Mutates model"| adk
    reflection -->|"Proposes models"| llm

    style api fill:#D4740C,color:#E0E0E0
    style engine fill:#438DD5,color:#E0E0E0
    style adapters fill:#D4740C,color:#E0E0E0
    style reflection fill:#D4740C,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style user fill:#1168BD,color:#E0E0E0
```

## 5. Component Diagram (C4 Level 3)

```mermaid
flowchart TB
    subgraph domain["domain/ (Pure Python)"]
        constraints["🔶 ModelConstraints<br/><i>dataclass</i><br/>allowed_models tuple"]
        schema_constraints["📦 SchemaConstraints<br/><i>dataclass</i><br/>Existing pattern"]
    end

    subgraph ports["ports/ (Interfaces)"]
        handler_protocol["📦 ComponentHandler<br/><i>Protocol</i><br/>serialize/apply/restore"]
    end

    subgraph adapters["adapters/ (Implementations)"]
        model_handler["🔶 ModelHandler<br/><i>Class</i><br/>Implements protocol"]
        schema_handler["📦 OutputSchemaHandler<br/><i>Class</i><br/>Existing pattern"]
        registry["📦 ComponentHandlerRegistry<br/><i>Class</i><br/>Handler lookup"]
    end

    subgraph engine["engine/ (Orchestration)"]
        model_reflection["🔶 create_model_reflection_agent<br/><i>Function</i><br/>Factory with allowed_models"]
        reflection_registry["📦 ComponentReflectionRegistry<br/><i>Class</i><br/>Agent factory lookup"]
    end

    model_handler -->|"implements"| handler_protocol
    model_handler -->|"uses"| constraints
    schema_handler -->|"implements"| handler_protocol
    schema_handler -->|"uses"| schema_constraints
    registry -->|"stores"| model_handler
    reflection_registry -->|"stores"| model_reflection

    style constraints fill:#D4740C,color:#E0E0E0
    style model_handler fill:#D4740C,color:#E0E0E0
    style model_reflection fill:#D4740C,color:#E0E0E0
    style handler_protocol fill:#5B9BD5,color:#E0E0E0
    style schema_constraints fill:#5B9BD5,color:#E0E0E0
    style schema_handler fill:#5B9BD5,color:#E0E0E0
    style registry fill:#5B9BD5,color:#E0E0E0
    style reflection_registry fill:#5B9BD5,color:#E0E0E0
```

## 6. Code Diagram (C4 Level 4)

```mermaid
classDiagram
    class ModelConstraints {
        +tuple~str~ allowed_models
    }
    <<dataclass>> ModelConstraints

    class ComponentHandler {
        <<protocol>>
        +serialize(agent) str
        +apply(agent, value) Any
        +restore(agent, original) None
    }

    class ModelHandler {
        -_constraints: ModelConstraints|None
        +set_constraints(constraints)
        +serialize(agent) str
        +apply(agent, value) tuple|None
        +restore(agent, original) None
    }

    class LlmAgent {
        +model: str|BaseLlm
        +instruction: str
    }

    class BaseLlm {
        +model: str
    }

    class LiteLlm {
        +model: str
        -_additional_args: dict
    }

    ModelHandler ..|> ComponentHandler : implements
    ModelHandler --> ModelConstraints : uses
    ModelHandler --> LlmAgent : operates on
    LlmAgent --> BaseLlm : contains
    LiteLlm --|> BaseLlm : extends
```

## 7. Hexagonal Architecture View

```mermaid
flowchart TB
    subgraph External["External Systems"]
        ADK["Google ADK<br/>(LlmAgent, BaseLlm)"]
        LLM["LLM Providers<br/>(Multiple models)"]
    end

    subgraph Adapters["adapters/ (External Integration)"]
        ModelHandler["🔶 ModelHandler"]
        InstructionHandler["InstructionHandler"]
        SchemaHandler["OutputSchemaHandler"]
        ConfigHandler["GenerateContentConfigHandler"]
    end

    subgraph Ports["ports/ (Interfaces)"]
        HandlerProtocol["ComponentHandler Protocol"]
    end

    subgraph Engine["engine/ (Orchestration)"]
        ModelReflection["🔶 create_model_reflection_agent"]
        TextReflection["create_text_reflection_agent"]
        SchemaReflection["create_schema_reflection_agent"]
    end

    subgraph Domain["domain/ (Pure Python)"]
        ModelConstraints["🔶 ModelConstraints"]
        SchemaConstraints["SchemaConstraints"]
        Types["ComponentSpec, etc."]
    end

    subgraph API["api.py (Public Interface)"]
        Evolve["🔶 evolve(model_choices=...)"]
    end

    API --> Engine
    Engine --> Ports
    Ports --> Adapters
    Adapters --> External
    Engine --> Domain
    ModelHandler --> ModelConstraints

    style ModelHandler fill:#D4740C,color:#E0E0E0
    style ModelReflection fill:#D4740C,color:#E0E0E0
    style ModelConstraints fill:#D4740C,color:#E0E0E0
    style Evolve fill:#D4740C,color:#E0E0E0
```

## 8. Runtime Behavior (Sequence Diagrams)

### 8.1 Happy Path: Model Evolution

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant API as api.evolve()
    participant H as ModelHandler
    participant R as ModelReflectionAgent
    participant E as Engine
    participant LLM as LLM Provider

    U->>API: evolve(agent, trainset, model_choices=[A,B,C])
    API->>API: Auto-include current model
    API->>H: set_constraints(ModelConstraints)
    API->>E: Start evolution

    loop Each iteration
        E->>H: serialize(agent)
        H-->>E: "current-model"

        E->>LLM: Evaluate with current model
        LLM-->>E: Results

        E->>R: propose(current, trials)
        R->>LLM: "Select best model from [A,B,C]"
        LLM-->>R: "model-B"
        R-->>E: proposed="model-B"

        E->>H: apply(agent, "model-B")
        H->>H: Validate against constraints
        H-->>E: ("wrapper"|"string", original)

        E->>LLM: Evaluate with model-B
        LLM-->>E: Results

        E->>H: restore(agent, original)
    end

    E-->>API: Best candidate
    API-->>U: EvolutionResult
```

### 8.2 Error Case: Invalid Model Rejected

```mermaid
sequenceDiagram
    autonumber
    participant R as ReflectionAgent
    participant H as ModelHandler
    participant E as Engine

    R-->>E: proposed="model-Z" (not in allowed list)
    E->>H: apply(agent, "model-Z")
    H->>H: Check constraints
    Note over H: "model-Z" not in allowed_models
    H->>H: Log warning
    H-->>E: None (no change)
    Note over E: Keep original model,<br/>try next iteration
```

## 9. Data Model & Contracts

### 9.1 New Data Structure

```mermaid
erDiagram
    MODEL_CONSTRAINTS {
        tuple allowed_models "Immutable list of model names"
    }

    MODEL_HANDLER {
        ModelConstraints _constraints "Optional validation"
    }

    EVOLUTION_RESULT {
        dict evolved_components "May include 'model' key"
    }

    MODEL_HANDLER ||--o| MODEL_CONSTRAINTS : "validated by"
    EVOLUTION_RESULT ||--o| MODEL_HANDLER : "produced by"
```

### 9.2 API Contracts

**Public API Changes**:
- `evolve()` — New parameter: `model_choices: Sequence[str] | None = None`
- `EvolutionResult.evolved_components` — May contain `"model"` key when evolved

**Internal Protocol**: No changes to `ComponentHandler` protocol

## 10. Quality Attributes (NFRs)

| Attribute | Requirement | Verification |
|-----------|-------------|--------------|
| **Performance** | No degradation from existing evolution | Benchmark tests |
| **Reliability** | Graceful rejection of invalid models | Unit tests for constraint validation |
| **Maintainability** | Follows existing handler pattern | Code review against OutputSchemaHandler |
| **Observability** | Log model changes with structlog | Log format verification |

## 11. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Contract** | `tests/contracts/` | ModelHandler implements ComponentHandler | `@pytest.mark.contract` |
| **Unit** | `tests/unit/adapters/` | Handler serialize/apply/restore logic | `@pytest.mark.unit` |
| **Unit** | `tests/unit/domain/` | ModelConstraints validation | `@pytest.mark.unit` |
| **Integration** | `tests/integration/` | End-to-end model evolution | `@pytest.mark.integration` |

**Key Test Scenarios**:
1. String model serialization and mutation
2. Wrapper model mutation with preservation
3. Constraint validation (accept/reject)
4. Opt-in behavior (no model_choices = no evolution)
5. Auto-include current model

## 12. Risks & Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Wrapper mutation breaks custom subclasses | High | Duck-type on `.model` attribute, not specific types |
| Model names invalid at runtime | Medium | User responsibility; clear error messages |

### Open Questions

None - all clarified during research phase.

## 13. Decisions (ADR References)

| ADR | Title | Relevance to This Feature |
|-----|-------|---------------------------|
| ADR-000 | Hexagonal Architecture | ModelConstraints in domain, ModelHandler in adapters |
| ADR-002 | Protocol Interfaces | ModelHandler implements ComponentHandler |
| ADR-005 | Three-Layer Testing | Contract + unit + integration tests required |
| ADR-008 | Structured Logging | Log model evolution events |

**New ADRs Needed**: None - follows existing patterns.

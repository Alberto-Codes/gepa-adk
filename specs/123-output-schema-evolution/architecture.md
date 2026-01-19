# Architecture: Output Schema Evolution

**Branch**: `123-output-schema-evolution` | **Date**: 2026-01-18 | **Status**: draft
**Spec**: [./spec.md](./spec.md) | **Plan**: [./plan.md](./plan.md) | **Tasks**: [./tasks.md](./tasks.md)

## 0. Links & References

- Feature Spec: `./spec.md`
- Implementation Plan: `./plan.md`
- Research: `./research.md`
- Data Model: `./data-model.md`
- Related ADRs: ADR-000 (Hexagonal Architecture), ADR-005 (Three-Layer Testing)

## 1. Purpose & Scope

### Goal

Enable evolution of Pydantic output schemas as components, allowing developers to optimize structured output definitions alongside agent instructions using the gepa-adk evolution engine.

### Non-Goals

- Evolving complex nested schemas with external imports
- Supporting JSON Schema format (Python source code only)
- Custom Pydantic validators (`@validator` decorators)
- Real-time schema validation during agent execution

### Scope Boundaries

- **In-scope**: Schema serialization, validation, deserialization utilities
- **Out-of-scope**: Modifications to the evolution engine core, new protocols

### Constraints

- **Technical**: Python 3.12+, stdlib only for utils layer (per ADR-000), Pydantic dependency
- **Organizational**: Must follow hexagonal architecture, no engine modifications
- **Conventions**: Self-contained schemas only (no imports allowed)

## 2. Architecture at a Glance

- **No new layers**: Adds utilities to existing `utils/` layer
- **No engine changes**: Existing component system already generic
- **Three utilities**: serialize, validate, deserialize Pydantic schemas
- **Security**: AST validation before exec() for deserialization
- **Integration**: Hooks into acceptance flow for validation

## 3. Component Diagram (Feature Focus)

> Shows the new schema_utils module and its integration with existing components.

```mermaid
flowchart TB
    subgraph Legend[" "]
        direction LR
        l1["📦 Existing"]
        l2["🔶 New/Modified"]
    end

    subgraph Utils["utils/ Layer"]
        schema_utils["🔶 schema_utils.py<br/><i>New Module</i><br/>serialize, validate, deserialize"]
        events["📦 events.py<br/><i>Existing</i><br/>Event extraction"]
    end

    subgraph Engine["engine/ Layer"]
        async_engine["📦 AsyncGEPAEngine<br/><i>Existing</i><br/>Orchestration (calls validation)"]
        proposer["📦 Proposer<br/><i>Existing</i><br/>Mutation proposals"]
    end

    subgraph Domain["domain/ Layer"]
        models["📦 models.py<br/><i>Existing</i><br/>Candidate, EvolutionResult"]
        exceptions["🔶 exceptions.py<br/><i>Extended</i><br/>SchemaValidationError fields"]
    end

    async_engine -->|"validate before accept"| schema_utils
    schema_utils -->|"raises on error"| exceptions
    models -->|"components dict"| async_engine
    proposer -->|"mutated schema text"| async_engine

    style schema_utils fill:#D4740C,color:#E0E0E0
    style exceptions fill:#D4740C,color:#E0E0E0
    style events fill:#5B9BD5,color:#E0E0E0
    style async_engine fill:#5B9BD5,color:#E0E0E0
    style proposer fill:#5B9BD5,color:#E0E0E0
    style models fill:#5B9BD5,color:#E0E0E0
    style l1 fill:#5B9BD5,color:#E0E0E0
    style l2 fill:#D4740C,color:#E0E0E0
```

## 4. Hexagonal Architecture View

> Shows how schema utilities fit within the hexagonal architecture.

```mermaid
flowchart TB
    subgraph External["External Systems"]
        ADK["Google ADK"]
        LLM["LLM Provider"]
    end

    subgraph Adapters["adapters/ (External Integration)"]
        ADKAdapter["ADKAdapter"]
        Proposer["Proposer"]
    end

    subgraph Ports["ports/ (Interfaces)"]
        AdapterPort["AsyncGEPAAdapter"]
        ScorerPort["Scorer"]
    end

    subgraph Engine["engine/ (Orchestration)"]
        GEPAEngine["AsyncGEPAEngine"]
    end

    subgraph Utils["utils/ (Shared Utilities)"]
        direction TB
        schema_utils["🔶 schema_utils.py"]
        events["events.py"]
        encoding["encoding.py"]
    end

    subgraph Domain["domain/ (Pure Python)"]
        Models["Candidate, EvolutionResult"]
        Exceptions["🔶 SchemaValidationError"]
    end

    Engine -->|"validates schemas"| schema_utils
    Engine --> Domain
    schema_utils --> Exceptions

    style schema_utils fill:#D4740C,color:#E0E0E0
    style Exceptions fill:#D4740C,color:#E0E0E0
```

## 5. Runtime Behavior (Sequence Diagrams)

### 5.1 Happy Path: Schema Evolution

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant API as api.py
    participant SU as schema_utils
    participant E as Engine
    participant P as Proposer
    participant LLM as LLM

    U->>API: evolve(agent, components=["output_schema"])
    API->>SU: serialize_pydantic_schema(agent.output_schema)
    SU-->>API: schema_text (Python source)
    API->>E: run evolution(candidate with schema_text)

    loop Each iteration
        E->>P: propose(candidate, reflective_dataset)
        P->>LLM: "Improve this schema..."
        LLM-->>P: proposed_schema_text
        P-->>E: mutated candidate

        E->>SU: validate_schema_text(proposed_schema_text)
        alt Valid Schema
            SU-->>E: SchemaValidationResult
            E->>E: accept proposal
        else Invalid Schema
            SU-->>E: SchemaValidationError
            E->>E: reject proposal
        end
    end

    E-->>API: EvolutionResult(evolved_component_text)
    API-->>U: result with evolved schema text
```

### 5.2 Error Path: Invalid Schema Rejected

```mermaid
sequenceDiagram
    autonumber
    participant E as Engine
    participant SU as schema_utils
    participant P as Proposer

    P->>E: proposed candidate with invalid schema
    E->>SU: validate_schema_text(schema_text)

    Note over SU: ast.parse() fails OR<br/>no BaseModel found OR<br/>exec() fails

    SU-->>E: raise SchemaValidationError
    E->>E: log warning, reject proposal
    E->>E: continue with previous best
```

### 5.3 Post-Evolution: Deserialize for Use

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant API as api.py
    participant SU as schema_utils
    participant Agent as Agent

    U->>API: result = await evolve(...)
    API-->>U: EvolutionResult

    U->>SU: deserialize_schema(result.evolved_component_text)
    SU->>SU: validate_schema_text() (includes exec)
    SU-->>U: EvolvedSchemaClass

    U->>Agent: agent.output_schema = EvolvedSchemaClass
    Note over Agent: Now uses evolved schema
```

## 6. Data Flow

```
┌─────────────────┐     serialize_pydantic_schema()     ┌─────────────────┐
│ Pydantic Model  │ ──────────────────────────────────▶ │   Schema Text   │
│     Class       │                                     │  (Python src)   │
│ (MyOutput)      │                                     │  in Candidate   │
└─────────────────┘                                     └────────┬────────┘
                                                                 │
                                                                 ▼
                                                        ┌─────────────────┐
                                                        │  Evolution Loop │
                                                        │  (LLM mutation) │
                                                        └────────┬────────┘
                                                                 │
                        validate_schema_text()                   ▼
┌─────────────────┐ ◀────────────────────────────────── ┌─────────────────┐
│ Accept/Reject   │                                     │ Proposed Schema │
│   Decision      │                                     │      Text       │
└────────┬────────┘                                     └─────────────────┘
         │ (if accepted)
         ▼
┌─────────────────┐     deserialize_schema()            ┌─────────────────┐
│ Evolved Schema  │ ◀────────────────────────────────── │  Final Result   │
│     Class       │                                     │ evolved_text    │
│ (EvolvedOutput) │                                     └─────────────────┘
└─────────────────┘
```

## 7. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Contract** | `tests/contracts/` | Round-trip serialization, validation rules | `@pytest.mark.contract` |
| **Unit** | `tests/unit/utils/` | serialize, validate, deserialize functions | `@pytest.mark.unit` |
| **Integration** | `tests/integration/` | End-to-end schema evolution | `@pytest.mark.integration` |

**Key Test Scenarios**:
1. Round-trip: serialize → evolve → deserialize preserves field types
2. Validation rejects syntax errors, missing BaseModel, imports
3. Security: exec() with controlled namespace only

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Code execution via exec() | Security | AST validation + controlled namespace whitelist |
| LLM proposes invalid schemas | Evolution fails | Validation rejects; engine continues with previous best |
| inspect.getsource() fails | Serialization fails | Only support classes defined in .py files |
| Schema name collisions | Namespace pollution | Unique namespace per validation call |

## 9. Decisions (ADR References)

| ADR | Title | Relevance to This Feature |
|-----|-------|---------------------------|
| ADR-000 | Hexagonal Architecture | Utils layer for schema_utils; no domain changes |
| ADR-005 | Three-Layer Testing | Contract + Unit + Integration tests required |
| ADR-009 | Exception Hierarchy | SchemaValidationError extends existing hierarchy |

**New ADRs Needed**: None - feature fits within existing architecture.

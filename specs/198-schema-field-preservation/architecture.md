# Architecture: Required Field Preservation for Output Schema Evolution

**Branch**: `198-schema-field-preservation` | **Date**: 2026-01-22 | **Status**: draft
**Spec**: [./spec.md](./spec.md) | **Plan**: [./plan.md](./plan.md) | **Tasks**: ./tasks.md (pending)

## 0. Links & References

- Feature Spec: `./spec.md`
- Implementation Plan: `./plan.md`
- Tasks: `./tasks.md` (to be generated with `/speckit.tasks`)
- Related ADRs: ADR-000 (Hexagonal Architecture), ADR-002 (Protocol Interfaces), ADR-005 (Three-Layer Testing)
- PRs: [link when available]

## 1. Purpose & Scope

### Goal

Enable users to protect critical fields in `output_schema` during evolution. When the reflection agent proposes schema mutations, the system validates against user-specified constraints and rejects invalid mutations, preserving schema integrity.

### Non-Goals

- Automatic detection of critical fields (user must explicitly specify)
- Persisting constraint configurations across runs
- Modifying reflection agent prompts to be aware of constraints
- GUI or interactive constraint configuration

### Scope Boundaries

- **In-scope**: Required field validation, type preservation, configuration-time validation, backward compatibility
- **Out-of-scope**: Field bounds/constraints preservation (P3 - future), constraint-aware reflection prompts

### Constraints

- **Technical**: Python 3.12+, no new dependencies, validation < 1ms
- **Organizational**: Must follow hexagonal architecture (ADR-000), protocol-based interfaces (ADR-002)
- **Conventions**: Frozen dataclasses for domain types, structured logging for rejections

## 2. Architecture at a Glance

- **New domain type**: `SchemaConstraints` dataclass in `domain/types.py` for constraint configuration
- **Validation utility**: `validate_schema_against_constraints()` in `utils/schema_utils.py`
- **Handler enhancement**: `OutputSchemaHandler` gains constraint checking in `apply()`
- **API threading**: `evolve()` accepts `schema_constraints` parameter, configures handler before evolution
- **Backward compatible**: No constraints = current behavior unchanged

## 3. Context Diagram (C4 Level 1)

> Shows how schema constraints fit into the broader evolution system.

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
        user["👤 Developer<br/><i>Configures constraints<br/>and runs evolution</i>"]
    end

    subgraph System[" "]
        gepa["🔶 GEPA-ADK<br/><i>Evolutionary optimization<br/>with constraint validation</i>"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>Agent runtime</i>"]
        llm["📦 LLM Provider<br/><i>Reflection model</i>"]
    end

    user -->|"evolve(schema_constraints=...)"| gepa
    gepa -->|"Proposes schema<br/>mutations"| llm
    gepa -->|"Executes agents"| adk

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

> Shows the containers affected by this feature.

```mermaid
flowchart TB
    subgraph Actors[" "]
        user["👤 Developer"]
    end

    subgraph GEPA["GEPA-ADK"]
        api["🔶 Public API<br/><i>api.py</i><br/>+schema_constraints param"]
        engine["🔷 Evolution Engine<br/><i>engine/</i><br/>Orchestration (unchanged)"]
        adapters["🔶 Adapters<br/><i>adapters/</i><br/>OutputSchemaHandler validation"]
        utils["🔶 Utils<br/><i>utils/</i><br/>validate_schema_against_constraints()"]
        domain["🔶 Domain<br/><i>domain/</i><br/>SchemaConstraints type"]
    end

    subgraph External[" "]
        llm["📦 LLM Provider<br/><i>Reflection model</i>"]
    end

    user -->|"evolve(...)"| api
    api -->|"Configures"| adapters
    adapters -->|"Validates with"| utils
    utils -->|"Uses"| domain
    engine -->|"Proposes via"| llm

    style api fill:#D4740C,color:#E0E0E0
    style engine fill:#438DD5,color:#E0E0E0
    style adapters fill:#D4740C,color:#E0E0E0
    style utils fill:#D4740C,color:#E0E0E0
    style domain fill:#D4740C,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style user fill:#1168BD,color:#E0E0E0
```

## 5. Component Diagram (C4 Level 3)

> Shows the internal components affected by this feature.

```mermaid
flowchart TB
    subgraph domain["domain/ (Pure Python)"]
        types["🔶 types.py<br/><i>+SchemaConstraints dataclass</i>"]
    end

    subgraph utils["utils/"]
        schema_utils["🔶 schema_utils.py<br/><i>+validate_schema_against_constraints()</i>"]
    end

    subgraph adapters["adapters/"]
        handler["🔶 OutputSchemaHandler<br/><i>+_constraints: SchemaConstraints</i><br/>+set_constraints()"]
        registry["📦 ComponentHandlerRegistry<br/><i>Unchanged</i>"]
    end

    subgraph api["api.py"]
        evolve["🔶 evolve()<br/><i>+schema_constraints param</i>"]
    end

    evolve -->|"Creates & configures"| handler
    handler -->|"Calls"| schema_utils
    schema_utils -->|"Uses"| types
    registry -->|"Contains"| handler

    style types fill:#D4740C,color:#E0E0E0
    style schema_utils fill:#D4740C,color:#E0E0E0
    style handler fill:#D4740C,color:#E0E0E0
    style registry fill:#5B9BD5,color:#E0E0E0
    style evolve fill:#D4740C,color:#E0E0E0
```

## 6. Code Diagram (C4 Level 4)

> Shows the class structure for constraint validation.

```mermaid
classDiagram
    class SchemaConstraints {
        <<frozen dataclass>>
        +tuple~str~ required_fields
        +dict~str, type~ preserve_types
    }

    class OutputSchemaHandler {
        -SchemaConstraints _constraints
        +set_constraints(constraints)
        +serialize(agent) str
        +apply(agent, value) Any
        +restore(agent, original)
    }

    class validate_schema_against_constraints {
        <<function>>
        +__call__(proposed, original, constraints) tuple~bool, list~str~~
    }

    class SchemaValidationResult {
        <<frozen dataclass>>
        +type~BaseModel~ schema_class
        +str class_name
        +int field_count
        +tuple~str~ field_names
    }

    OutputSchemaHandler --> SchemaConstraints : stores
    OutputSchemaHandler --> validate_schema_against_constraints : calls
    validate_schema_against_constraints --> SchemaValidationResult : uses
```

## 7. Hexagonal Architecture View

> Shows how this feature aligns with the hexagonal architecture.

```mermaid
flowchart TB
    subgraph External["External Systems"]
        LLM["LLM Provider"]
        ADK["Google ADK"]
    end

    subgraph Adapters["adapters/ (External Integration)"]
        Handler["🔶 OutputSchemaHandler<br/>+constraint validation"]
        ADKAdapter["ADKAdapter"]
        Proposer["MutationProposer"]
    end

    subgraph Utils["utils/ (Shared Utilities)"]
        SchemaUtils["🔶 schema_utils.py<br/>+validate_schema_against_constraints()"]
    end

    subgraph Ports["ports/ (Interfaces)"]
        ComponentPort["ComponentHandler Protocol<br/>(unchanged)"]
    end

    subgraph Engine["engine/ (Orchestration)"]
        GEPAEngine["AsyncGEPAEngine<br/>(unchanged)"]
    end

    subgraph Domain["domain/ (Pure Python)"]
        Types["🔶 types.py<br/>+SchemaConstraints"]
        Models["models.py"]
    end

    subgraph API["api.py (Public Interface)"]
        Evolve["🔶 evolve()<br/>+schema_constraints param"]
    end

    API --> Engine
    API --> Adapters
    Engine --> Ports
    Adapters --> Utils
    Utils --> Domain
    Adapters --> External
    Handler -.->|implements| ComponentPort

    style Handler fill:#D4740C,color:#E0E0E0
    style SchemaUtils fill:#D4740C,color:#E0E0E0
    style Types fill:#D4740C,color:#E0E0E0
    style Evolve fill:#D4740C,color:#E0E0E0
```

## 8. Runtime Behavior (Sequence Diagrams)

### 8.1 Happy Path: Valid Mutation Accepted

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant API as evolve()
    participant H as OutputSchemaHandler
    participant V as validate_schema_against_constraints()
    participant A as Agent

    U->>API: evolve(agent, schema_constraints=...)
    API->>H: set_constraints(constraints)

    Note over API,A: Evolution loop starts...

    API->>H: apply(agent, proposed_schema_text)
    H->>H: deserialize_schema(text)
    H->>V: validate(proposed, original, constraints)
    V-->>H: (True, [])

    H->>A: agent.output_schema = proposed
    H-->>API: original_schema

    Note over API,A: Evolution continues...
```

### 8.2 Error Path: Invalid Mutation Rejected

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant API as evolve()
    participant H as OutputSchemaHandler
    participant V as validate_schema_against_constraints()
    participant L as structlog
    participant A as Agent

    U->>API: evolve(agent, schema_constraints=...)
    API->>H: set_constraints(constraints)

    Note over API,A: Evolution loop starts...

    API->>H: apply(agent, proposed_schema_text)
    H->>H: deserialize_schema(text)
    H->>V: validate(proposed, original, constraints)
    V-->>H: (False, ["Required field 'score' missing"])

    H->>L: warning("output_schema.constraint_violation", ...)
    Note over H,A: Agent NOT modified
    H-->>API: original_schema (unchanged)

    Note over API,A: Evolution continues with original schema...
```

### 8.3 Configuration Validation: Fail Fast

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant API as evolve()
    participant A as Agent

    U->>API: evolve(agent, schema_constraints=SchemaConstraints(required_fields=("nonexistent",)))
    API->>A: Get agent.output_schema.model_fields
    A-->>API: {"score": ..., "feedback": ...}
    API->>API: Check "nonexistent" in fields

    Note over API: Field not found!
    API--xU: ConfigurationError("Field 'nonexistent' not found in original schema")
```

## 9. Data Model & Contracts

### 9.1 Data Changes

```mermaid
erDiagram
    SCHEMA_CONSTRAINTS {
        tuple required_fields "Field names that must exist"
        dict preserve_types "Field name to allowed types"
    }

    OUTPUT_SCHEMA_HANDLER {
        SchemaConstraints _constraints "Optional constraint config"
    }

    EVOLVE_API {
        SchemaConstraints schema_constraints "New parameter"
    }

    EVOLVE_API ||--o| SCHEMA_CONSTRAINTS : "accepts"
    OUTPUT_SCHEMA_HANDLER ||--o| SCHEMA_CONSTRAINTS : "stores"
```

### 9.2 API Contracts

**Public API Changes**:
- `evolve(schema_constraints: SchemaConstraints | None = None)` — New optional parameter

**Internal Changes**:
- `OutputSchemaHandler.set_constraints(constraints: SchemaConstraints | None)` — New method
- `validate_schema_against_constraints(proposed, original, constraints)` — New utility function

## 10. Quality Attributes (NFRs)

| Attribute | Requirement | Verification |
|-----------|-------------|--------------|
| **Performance** | Validation < 1ms per mutation | Unit test with timing assertions |
| **Reliability** | Graceful rejection (never crash) | Unit tests for all edge cases |
| **Maintainability** | Hexagonal architecture compliance | Layer import rules enforced |
| **Observability** | Structured logging for rejections | Log format verification |
| **Backward Compat** | No constraints = unchanged behavior | Integration tests |

## 11. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Contract** | `tests/contracts/test_schema_constraints_contract.py` | SchemaConstraints immutability, validation protocol | `@pytest.mark.contract` |
| **Unit** | `tests/unit/domain/test_schema_constraints.py` | Dataclass behavior | `@pytest.mark.unit` |
| **Unit** | `tests/unit/utils/test_schema_constraint_validation.py` | Validation logic | `@pytest.mark.unit` |
| **Unit** | `tests/unit/adapters/test_output_schema_handler_constraints.py` | Handler integration | `@pytest.mark.unit` |
| **Integration** | `tests/integration/test_schema_constrained_evolution.py` | End-to-end with real ADK | `@pytest.mark.integration` |

**Key Test Scenarios**:
1. Required field present → mutation accepted
2. Required field missing → mutation rejected, original preserved
3. Type matches → mutation accepted
4. Type mismatch → mutation rejected
5. No constraints → all mutations accepted (backward compat)
6. Invalid constraint config → fail fast with ConfigurationError

## 12. Risks & Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Handler state leaks between runs | Constraints from one run affect next | Reset constraints after evolution completes |
| Type extraction fails for complex types | Validation incorrectly rejects | Test with Optional, Union, List types |

### Open Questions

- [x] Where to validate constraints at config time? → In `evolve()` before handler setup
- [x] Log level for rejections? → WARNING (not ERROR)

## 13. Decisions (ADR References)

| ADR | Title | Relevance to This Feature |
|-----|-------|---------------------------|
| ADR-000 | Hexagonal Architecture | SchemaConstraints in domain/, validation in utils/, handler in adapters/ |
| ADR-002 | Protocol Interfaces | ComponentHandler protocol unchanged; validation is internal |
| ADR-005 | Three-Layer Testing | Contract + Unit + Integration tests required |

**New ADRs Needed**: None - this feature follows existing patterns.

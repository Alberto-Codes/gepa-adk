# Architecture: Component-Aware Reflection Agents

**Branch**: `142-component-aware-reflection` | **Date**: 2026-01-20 | **Status**: draft
**Spec**: [./spec.md](spec.md) | **Plan**: [./plan.md](plan.md)

## 0. Links & References

- Feature Spec: `./spec.md`
- Implementation Plan: `./plan.md`
- Research: `./research.md`
- Related ADRs: ADR-000 (Hexagonal), ADR-002 (Protocols), ADR-005 (Testing), ADR-006 (External Libraries)

## 1. Purpose & Scope

### Goal

Enable reflection agents to validate `output_schema` proposals before returning, reducing wasted evolution iterations on invalid Pydantic schemas.

### Non-Goals

- Validating other structured ADK attributes (deferred)
- Modifying how ADK executes agents
- Changing the core evolution loop

### Scope Boundaries

- **In-scope**: `output_schema` validation tool, reflection agent factories, component registry
- **Out-of-scope**: `tools`, `input_schema`, `generate_content_config` validation (future)

### Constraints

- **Technical**: Must use ADK's FunctionTool pattern for validation tool
- **Organizational**: Follow hexagonal architecture - tools in utils/, factories in engine/
- **Conventions**: Backward compatible - existing code must continue to work

## 2. Architecture at a Glance

- **Factory pattern** creates component-specific reflection agents (schema vs text)
- **Registry** maps component names to factories for auto-selection
- **Validation tool** wraps existing `validate_schema_text()` as ADK FunctionTool
- **Reflection instruction** explicitly guides LLM to use validation before returning
- **Proposer passes component_name** to reflection, enabling dynamic agent selection
- **Backward compatible** - existing code works unchanged

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
        user["👤 Developer<br/><i>Evolves agent components</i>"]
    end

    subgraph System[" "]
        gepa["🔷 GEPA-ADK<br/><i>Evolution system with<br/>component-aware reflection</i>"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>Agent runtime with<br/>FunctionTool support</i>"]
        llm["📦 LLM Provider<br/><i>Reflection model<br/>(Gemini, etc.)</i>"]
    end

    user -->|"Evolves output_schema<br/>component"| gepa
    gepa -->|"Executes reflection<br/>agent with tools"| adk
    adk -->|"LLM calls with<br/>tool invocation"| llm

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

```mermaid
flowchart TB
    subgraph GEPA["GEPA-ADK"]
        api["🔷 Public API<br/><i>api.py</i><br/>evolve(), evolve_sync()"]
        engine["🔷 Evolution Engine<br/><i>engine/</i><br/>AsyncGEPAEngine"]
        proposer["🔶 Mutation Proposer<br/><i>engine/proposer.py</i><br/>Passes component_name"]
        reflection["🔶 Reflection Module<br/><i>engine/adk_reflection.py</i><br/>Auto-selects agent"]
        factories["🔶 Reflection Factories<br/><i>engine/reflection_agents.py</i><br/>NEW: Creates agents"]
        utils["🔶 Schema Tools<br/><i>utils/schema_tools.py</i><br/>NEW: Validation tool"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>FunctionTool, LlmAgent</i>"]
    end

    api --> engine
    engine --> proposer
    proposer --> reflection
    reflection --> factories
    factories --> utils
    factories --> adk

    style api fill:#438DD5,color:#E0E0E0
    style engine fill:#438DD5,color:#E0E0E0
    style proposer fill:#D4740C,color:#E0E0E0
    style reflection fill:#D4740C,color:#E0E0E0
    style factories fill:#D4740C,color:#E0E0E0
    style utils fill:#D4740C,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
```

## 5. Component Diagram (C4 Level 3)

```mermaid
flowchart TB
    subgraph engine["engine/ (Orchestration)"]
        proposer["📦 AsyncReflectiveMutationProposer<br/><i>Class</i><br/>Calls reflection with component_name"]
        adk_reflection["📦 create_adk_reflection_fn<br/><i>Function</i><br/>Creates ReflectionFn"]
        reflection_agents["📦 reflection_agents.py<br/><i>Module - NEW</i><br/>Factories + Registry"]
    end

    subgraph utils["utils/ (Shared Utilities)"]
        schema_tools["📦 schema_tools.py<br/><i>Module - NEW</i><br/>validate_output_schema()"]
        schema_utils["📦 schema_utils.py<br/><i>Existing</i><br/>validate_schema_text()"]
    end

    proposer -->|"calls with<br/>component_name"| adk_reflection
    adk_reflection -->|"gets agent from"| reflection_agents
    reflection_agents -->|"creates tool from"| schema_tools
    schema_tools -->|"wraps"| schema_utils

    style proposer fill:#D4740C,color:#E0E0E0
    style adk_reflection fill:#D4740C,color:#E0E0E0
    style reflection_agents fill:#D4740C,color:#E0E0E0
    style schema_tools fill:#D4740C,color:#E0E0E0
    style schema_utils fill:#5B9BD5,color:#E0E0E0
```

## 6. Code Diagram (C4 Level 4)

```mermaid
classDiagram
    class ComponentReflectionRegistry {
        -_factories: dict~str, ReflectionAgentFactory~
        -_default_factory: ReflectionAgentFactory
        +register(component_name, factory)
        +get_factory(component_name) ReflectionAgentFactory
        +get_agent(component_name, model) LlmAgent
    }

    class ReflectionAgentFactory {
        <<type alias>>
        Callable[[str], LlmAgent]
    }

    class SchemaValidationToolResult {
        +valid: bool
        +class_name: str | None
        +field_count: int | None
        +field_names: list | None
        +errors: list | None
        +stage: str | None
    }

    class validate_output_schema {
        <<function>>
        +schema_text: str
        returns dict
    }

    class create_schema_reflection_agent {
        <<function>>
        +model: str
        returns LlmAgent
    }

    class create_text_reflection_agent {
        <<function>>
        +model: str
        returns LlmAgent
    }

    ComponentReflectionRegistry --> ReflectionAgentFactory : contains
    create_schema_reflection_agent ..|> ReflectionAgentFactory : implements
    create_text_reflection_agent ..|> ReflectionAgentFactory : implements
    create_schema_reflection_agent --> validate_output_schema : uses as tool
    validate_output_schema --> SchemaValidationToolResult : returns
```

## 7. Hexagonal Architecture View

```mermaid
flowchart TB
    subgraph External["External Systems"]
        ADK["Google ADK<br/>(FunctionTool, LlmAgent)"]
        LLM["LLM Provider"]
    end

    subgraph Adapters["adapters/"]
        ADKAdapter["ADKAdapter"]
        AgentExecutor["AgentExecutor"]
    end

    subgraph Engine["engine/ (MODIFIED)"]
        GEPAEngine["AsyncGEPAEngine"]
        Proposer["🔶 Proposer<br/>passes component_name"]
        ADKReflection["🔶 adk_reflection<br/>auto-selects agent"]
        ReflectionAgents["🔶 reflection_agents.py<br/>NEW: factories + registry"]
    end

    subgraph Utils["utils/ (MODIFIED)"]
        SchemaUtils["schema_utils.py<br/>(existing validation)"]
        SchemaTools["🔶 schema_tools.py<br/>NEW: tool wrapper"]
    end

    subgraph Domain["domain/"]
        Types["types.py"]
    end

    GEPAEngine --> Proposer
    Proposer --> ADKReflection
    ADKReflection --> ReflectionAgents
    ReflectionAgents --> SchemaTools
    SchemaTools --> SchemaUtils
    ReflectionAgents -.-> ADK
    ADKAdapter --> AgentExecutor
    AgentExecutor --> ADK

    style Proposer fill:#D4740C,color:#E0E0E0
    style ADKReflection fill:#D4740C,color:#E0E0E0
    style ReflectionAgents fill:#D4740C,color:#E0E0E0
    style SchemaTools fill:#D4740C,color:#E0E0E0
```

## 8. Runtime Behavior (Sequence Diagrams)

### 8.1 Happy Path: Schema Reflection with Validation

```mermaid
sequenceDiagram
    autonumber
    participant P as Proposer
    participant R as adk_reflection
    participant F as reflection_agents
    participant A as LlmAgent
    participant T as validate_output_schema
    participant S as schema_utils

    P->>R: reflect(text, trials, "output_schema")
    R->>F: get_agent("output_schema", model)
    F-->>R: schema_reflection_agent (with tool)

    R->>A: execute reflection

    loop LLM self-validates
        A->>A: propose schema text
        A->>T: validate_output_schema(proposed)
        T->>S: validate_schema_text(proposed)
        alt Valid
            S-->>T: SchemaValidationResult
            T-->>A: {"valid": true, ...}
        else Invalid
            S-->>T: SchemaValidationError
            T-->>A: {"valid": false, "errors": [...]}
            A->>A: fix and retry
        end
    end

    A-->>R: valid proposed schema
    R-->>P: proposed_component_text
```

### 8.2 Fallback: Unknown Component Uses Default

```mermaid
sequenceDiagram
    autonumber
    participant P as Proposer
    participant R as adk_reflection
    participant F as reflection_agents
    participant A as LlmAgent

    P->>R: reflect(text, trials, "custom_component")
    R->>F: get_agent("custom_component", model)
    Note over F: Not in registry
    F-->>R: text_reflection_agent (no tools)

    R->>A: execute reflection
    A-->>R: proposed text (no validation)
    R-->>P: proposed_component_text
```

## 9. Data Model & Contracts

### 9.1 API Contracts

**Extended ReflectionFn signature**:
```python
# Before
ReflectionFn = Callable[[str, list[dict]], Awaitable[str]]

# After (backward compatible)
ReflectionFn = Callable[[str, list[dict], str], Awaitable[str]]
#                        ^text  ^trials   ^component_name
```

**New factory functions**:
- `create_text_reflection_agent(model: str) -> LlmAgent`
- `create_schema_reflection_agent(model: str) -> LlmAgent`
- `get_reflection_agent(component_name: str, model: str) -> LlmAgent`

**New validation tool**:
- `validate_output_schema(schema_text: str) -> dict`

## 10. Quality Attributes (NFRs)

| Attribute | Requirement | Verification |
|-----------|-------------|--------------|
| **Backward Compatibility** | Existing code works unchanged | Unit tests with old API |
| **Extensibility** | New validators without core changes | Registry pattern |
| **Reliability** | Invalid schemas don't crash | Tool returns error dict |
| **Observability** | Validation events logged | structlog with context |

## 11. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Unit** | `tests/unit/engine/test_reflection_agents.py` | Factory functions, registry | - |
| **Unit** | `tests/unit/utils/test_schema_tools.py` | Tool wrapper function | - |
| **Integration** | `tests/integration/test_schema_reflection.py` | Full validation flow | `@pytest.mark.slow` |

**Key Test Scenarios**:
1. Schema reflection agent validates and returns valid schema
2. Schema reflection agent retries on invalid schema (mock LLM)
3. Unknown component falls back to text reflection
4. Registry extension works without core changes
5. Backward compatibility - existing code unchanged

## 12. Risks & Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM ignores validation tool | Wasted iterations | Strong instruction, fallback to downstream validation |
| Tool adds latency | Slower reflection | Validation is fast (<10ms), benefit outweighs cost |

### Open Questions

- [x] How does ADK handle output_schema validation? → Researched: uses `model_validate_json()` and `SetModelResponseTool`
- [x] Can we use ADK's existing patterns? → Yes: FunctionTool + instruction injection

## 13. Decisions (ADR References)

| ADR | Title | Relevance to This Feature |
|-----|-------|---------------------------|
| ADR-000 | Hexagonal Architecture | Tools in utils/, factories in engine/ |
| ADR-002 | Protocol Interfaces | No new protocols needed |
| ADR-005 | Three-Layer Testing | Unit + integration tests |
| ADR-006 | External Library Integration | ADK FunctionTool used via injection |

**New ADRs Needed**: None

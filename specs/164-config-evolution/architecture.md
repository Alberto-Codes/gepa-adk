# Architecture: Generate Content Config Evolution

**Branch**: `164-config-evolution` | **Date**: 2026-01-20 | **Status**: draft
**Spec**: [./spec.md] | **Plan**: [./plan.md] | **Tasks**: [./tasks.md]

## 0. Links & References

- Feature Spec: `./spec.md`
- Implementation Plan: `./plan.md`
- Tasks: `./tasks.md`
- Related ADRs: ADR-000 (Hexagonal), ADR-002 (Protocols), ADR-005 (Testing), ADR-006 (External Libs), ADR-008 (Logging)
- PRs: [link when available]

## 1. Purpose & Scope

### Goal

Enable automatic optimization of LLM generation parameters (temperature, top_p, top_k, max_output_tokens) alongside other agent components during GEPA evolution. This extends the ComponentHandler pattern to support `generate_content_config` as an evolvable component.

### Non-Goals

- Evolving `safety_settings` as a separate component
- Model-specific parameter validation
- Automatic parameter constraint discovery
- UI/visualization for config evolution

### Scope Boundaries

- **In-scope**:
  - GenerateContentConfigHandler implementation
  - Config serialization/deserialization utilities
  - Validation for known parameter constraints
  - Config reflection agent factory
  - Three-layer tests
- **Out-of-scope**:
  - Changes to core evolution loop
  - New dependencies (uses existing PyYAML, structlog)

### Constraints

- **Technical**: Must follow ComponentHandler protocol exactly; YAML serialization for LLM readability
- **Organizational**: Must comply with hexagonal architecture (handler in adapters/, utilities in utils/)
- **Conventions**: Follow existing InstructionHandler/OutputSchemaHandler patterns

## 2. Architecture at a Glance

- **Handler Pattern**: `GenerateContentConfigHandler` implements the `ComponentHandler` protocol with serialize/apply/restore methods
- **Layers Affected**: domain/ (constant), utils/ (new config_utils), adapters/ (handler), engine/ (reflection agent)
- **Integration**: Registered in `ComponentHandlerRegistry` at module load; automatic dispatch via `_apply_candidate()`
- **Data Flow**: Config → YAML serialize → reflection agent → proposed YAML → validate → apply to agent
- **Error Handling**: Graceful degradation - invalid configs keep original, warning logged

## 3. Context Diagram (C4 Level 1)

> Shows how config evolution fits into the broader GEPA system.

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
        dev["👤 GEPA Developer<br/><i>Configures evolution with<br/>generate_content_config component</i>"]
    end

    subgraph System[" "]
        gepa["🔷 GEPA-ADK<br/><i>Evolutionary optimization<br/>for ADK agents</i>"]
        config_handler["🔶 Config Evolution<br/><i>NEW: GenerateContentConfig<br/>as evolvable component</i>"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>GenerateContentConfig<br/>from google.genai.types</i>"]
        llm["📦 Reflection LLM<br/><i>Proposes config<br/>improvements</i>"]
    end

    dev -->|"components=[<br/>'generate_content_config']"| gepa
    gepa -->|"serialize/apply<br/>config"| config_handler
    config_handler -->|"Uses GenerateContentConfig<br/>from"| adk
    gepa -->|"Reflection<br/>proposals"| llm

    style l1 fill:#1168BD,color:#E0E0E0
    style l2 fill:#438DD5,color:#E0E0E0
    style l3 fill:#666666,color:#E0E0E0
    style l4 fill:#D4740C,color:#E0E0E0
    style gepa fill:#438DD5,color:#E0E0E0
    style config_handler fill:#D4740C,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style dev fill:#1168BD,color:#E0E0E0
```

## 4. Container Diagram (C4 Level 2)

> Shows the containers involved in config evolution.

```mermaid
flowchart TB
    subgraph GEPA["GEPA-ADK"]
        api["🔷 Public API<br/><i>Python</i><br/>evolve() with components"]
        engine["🔷 Evolution Engine<br/><i>Python</i><br/>AsyncGEPAEngine"]
        adapters["🔷 Adapters<br/><i>Python</i><br/>ADKAdapter + ComponentHandlers"]
        config_handler["🔶 Config Handler<br/><i>Python</i><br/>GenerateContentConfigHandler"]
        config_utils["🔶 Config Utils<br/><i>Python</i><br/>serialize/deserialize/validate"]
        reflection["🔶 Config Reflector<br/><i>Python</i><br/>Config reflection agent factory"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>GenerateContentConfig</i>"]
        llm["📦 LLM Provider<br/><i>Config improvement</i>"]
    end

    api -->|"components list"| engine
    engine -->|"get_handler"| adapters
    adapters -->|"dispatch"| config_handler
    config_handler -->|"uses"| config_utils
    engine -->|"get_reflection_agent"| reflection
    reflection -->|"proposals"| llm
    config_handler -->|"GenerateContentConfig"| adk

    style api fill:#438DD5,color:#E0E0E0
    style engine fill:#438DD5,color:#E0E0E0
    style adapters fill:#438DD5,color:#E0E0E0
    style config_handler fill:#D4740C,color:#E0E0E0
    style config_utils fill:#D4740C,color:#E0E0E0
    style reflection fill:#D4740C,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
```

## 5. Component Diagram (C4 Level 3)

> Shows the internal components for config evolution.

```mermaid
flowchart TB
    subgraph adapters["adapters/ Layer"]
        registry["📦 ComponentHandlerRegistry<br/><i>Class</i><br/>Handler lookup by name"]
        config_handler["🔶 GenerateContentConfigHandler<br/><i>Class</i><br/>serialize/apply/restore"]
        instruction_handler["📦 InstructionHandler<br/><i>Existing</i><br/>Instruction evolution"]
        schema_handler["📦 OutputSchemaHandler<br/><i>Existing</i><br/>Schema evolution"]
    end

    subgraph utils["utils/ Layer"]
        config_utils["🔶 config_utils<br/><i>Module</i><br/>serialize/deserialize/validate"]
    end

    subgraph ports["ports/ Layer"]
        handler_protocol["📦 ComponentHandler<br/><i>Protocol</i><br/>serialize/apply/restore"]
    end

    subgraph domain["domain/ Layer"]
        types["📦 types.py<br/><i>Module</i><br/>COMPONENT_GENERATE_CONFIG"]
        exceptions["📦 exceptions.py<br/><i>Module</i><br/>ConfigValidationError"]
    end

    subgraph engine["engine/ Layer"]
        reflection_registry["📦 ComponentReflectionRegistry<br/><i>Class</i><br/>Agent factory lookup"]
        config_reflector["🔶 create_config_reflection_agent<br/><i>Function</i><br/>Config-focused agent"]
    end

    registry -->|"stores"| config_handler
    config_handler .->|"implements"| handler_protocol
    config_handler -->|"delegates to"| config_utils
    config_handler -->|"uses constant"| types
    config_utils -->|"raises"| exceptions
    reflection_registry -->|"maps to"| config_reflector

    style registry fill:#5B9BD5,color:#E0E0E0
    style config_handler fill:#D4740C,color:#E0E0E0
    style instruction_handler fill:#5B9BD5,color:#E0E0E0
    style schema_handler fill:#5B9BD5,color:#E0E0E0
    style config_utils fill:#D4740C,color:#E0E0E0
    style handler_protocol fill:#5B9BD5,color:#E0E0E0
    style types fill:#5B9BD5,color:#E0E0E0
    style exceptions fill:#5B9BD5,color:#E0E0E0
    style reflection_registry fill:#5B9BD5,color:#E0E0E0
    style config_reflector fill:#D4740C,color:#E0E0E0
```

## 6. Code Diagram (C4 Level 4)

> Class relationships for the config handler implementation.

```mermaid
classDiagram
    class ComponentHandler {
        <<protocol>>
        +serialize(agent: LlmAgent) str
        +apply(agent: LlmAgent, value: str) Any
        +restore(agent: LlmAgent, original: Any) None
    }

    class GenerateContentConfigHandler {
        +serialize(agent: LlmAgent) str
        +apply(agent: LlmAgent, value: str) GenerateContentConfig
        +restore(agent: LlmAgent, original: GenerateContentConfig) None
    }

    class ConfigUtils {
        <<module>>
        +serialize_generate_config(config) str
        +deserialize_generate_config(yaml_text, existing) GenerateContentConfig
        +validate_generate_config(config_dict) list~str~
    }

    class ConfigValidationError {
        +message: str
        +errors: list~str~
    }

    class EvolutionError {
        <<base>>
    }

    GenerateContentConfigHandler ..|> ComponentHandler : implements
    GenerateContentConfigHandler --> ConfigUtils : uses
    ConfigUtils --> ConfigValidationError : raises
    ConfigValidationError --|> EvolutionError : inherits
```

## 7. Hexagonal Architecture View

> Shows how config evolution aligns with the hexagonal architecture.

```mermaid
flowchart TB
    subgraph External["External Systems"]
        ADK["Google ADK<br/>(GenerateContentConfig)"]
        LLM["LLM Provider<br/>(Reflection)"]
    end

    subgraph Adapters["adapters/ (External Integration)"]
        ConfigHandler["🔶 GenerateContentConfigHandler"]
        Registry["ComponentHandlerRegistry"]
    end

    subgraph Utils["utils/ (Shared Utilities)"]
        ConfigUtils["🔶 config_utils.py"]
    end

    subgraph Ports["ports/ (Interfaces)"]
        HandlerProtocol["ComponentHandler Protocol"]
    end

    subgraph Engine["engine/ (Orchestration)"]
        ReflectionRegistry["ComponentReflectionRegistry"]
        ConfigReflector["🔶 create_config_reflection_agent"]
    end

    subgraph Domain["domain/ (Pure Python)"]
        Types["🔶 COMPONENT_GENERATE_CONFIG"]
        Exceptions["ConfigValidationError"]
    end

    subgraph API["api.py (Public Interface)"]
        Evolve["evolve(components=[...])"]
    end

    API --> Engine
    Engine --> Ports
    Ports --> Adapters
    Adapters --> External
    Adapters --> Utils
    Engine --> Domain
    Utils --> Domain

    style ConfigHandler fill:#D4740C,color:#E0E0E0
    style ConfigUtils fill:#D4740C,color:#E0E0E0
    style Types fill:#D4740C,color:#E0E0E0
    style ConfigReflector fill:#D4740C,color:#E0E0E0
```

## 8. Runtime Behavior (Sequence Diagrams)

### 8.1 Happy Path: Config Evolution Cycle

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant E as Engine
    participant R as Registry
    participant H as ConfigHandler
    participant CU as config_utils
    participant A as Agent
    participant RF as Reflector

    U->>E: evolve(components=["generate_content_config"])
    E->>R: get_handler("generate_content_config")
    R-->>E: GenerateContentConfigHandler

    E->>H: serialize(agent)
    H->>A: agent.generate_content_config
    A-->>H: GenerateContentConfig
    H->>CU: serialize_generate_config(config)
    CU-->>H: YAML text
    H-->>E: YAML text

    E->>RF: propose(yaml_text, trials)
    RF-->>E: proposed YAML

    E->>H: apply(agent, proposed_yaml)
    H->>CU: deserialize_generate_config(yaml)
    CU->>CU: validate_generate_config(dict)
    CU-->>H: new GenerateContentConfig
    H->>A: agent.generate_content_config = new
    H-->>E: original config

    Note over E: Evaluate with new config...

    E->>H: restore(agent, original)
    H->>A: agent.generate_content_config = original
```

### 8.2 Error Case: Invalid Config Rejected

```mermaid
sequenceDiagram
    autonumber
    participant E as Engine
    participant H as ConfigHandler
    participant CU as config_utils
    participant A as Agent
    participant L as Logger

    E->>H: apply(agent, "temperature: 999")
    H->>CU: deserialize_generate_config(yaml)
    CU->>CU: validate_generate_config({temperature: 999})
    CU-->>H: errors=["temperature must be 0.0-2.0"]
    H->>L: warning("config_handler.apply.failed", errors)
    Note over H: Keep original config unchanged
    H-->>E: original config (unchanged)
```

## 9. Data Model & Contracts

### 9.1 Data Changes

> No persistent data changes - config is in-memory on LlmAgent.

```mermaid
erDiagram
    LLMAGENT {
        str name
        str model
        str instruction
        type output_schema
        GenerateContentConfig generate_content_config
    }
    GENERATE_CONTENT_CONFIG {
        float temperature "0.0-2.0"
        float top_p "0.0-1.0"
        float top_k "positive"
        int max_output_tokens "positive"
        float presence_penalty "-2.0-2.0"
        float frequency_penalty "-2.0-2.0"
    }
    LLMAGENT ||--o| GENERATE_CONTENT_CONFIG : "has"
```

### 9.2 API Contracts

**No Public API Changes** - Uses existing `evolve()` with components parameter.

**New Internal Components**:
- `COMPONENT_GENERATE_CONFIG = "generate_content_config"` in domain/types.py
- `GenerateContentConfigHandler` class in adapters/component_handlers.py
- `config_utils` module in utils/

## 10. Deployment / Infrastructure View

> No infrastructure changes - this is a library feature.

## 11. Quality Attributes (NFRs)

| Attribute | Requirement | Verification |
|-----------|-------------|--------------|
| **Performance** | <1ms for serialize/apply/restore | Unit tests with timing |
| **Reliability** | Graceful degradation on invalid input | Error handling tests |
| **Security** | No secrets in serialized config | Code review |
| **Maintainability** | Hexagonal architecture compliance | Layer import checks |
| **Observability** | Structured logging with context | Log format verification |

## 12. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Contract** | `tests/contracts/` | Handler protocol compliance | `@pytest.mark.contract` |
| **Unit** | `tests/unit/adapters/` | Handler serialize/apply/restore | `@pytest.mark.unit` |
| **Unit** | `tests/unit/utils/` | Config utils functions | `@pytest.mark.unit` |
| **Integration** | `tests/integration/` | Full evolution with config component | `@pytest.mark.integration` |

**Key Test Scenarios**:
1. Handler serialize/apply/restore round-trip
2. Validation rejects out-of-range parameters
3. Partial config merges with existing
4. None/empty config handling
5. Full evolution loop with config component

## 13. Risks & Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| ADK GenerateContentConfig changes | Handler breaks | Pin ADK version, test in CI |
| YAML parsing edge cases | Invalid proposals | Comprehensive validation tests |

### Open Questions

- [x] YAML vs JSON format → YAML chosen for LLM readability
- [x] Which params to evolve → Core generation params only

### TODOs

- [x] Implementation in tasks.md
- [ ] Example script `config_evolution_demo.py`
- [ ] Update docs/guides

## 14. Decisions (ADR References)

| ADR | Title | Relevance to This Feature |
|-----|-------|---------------------------|
| ADR-000 | Hexagonal Architecture | Handler in adapters/, utils in utils/, constant in domain/ |
| ADR-002 | Protocol Interfaces | Implements ComponentHandler protocol |
| ADR-005 | Three-Layer Testing | Contract + unit + integration tests required |
| ADR-006 | External Library Integration | ADK types imported only in adapters/ |
| ADR-008 | Structured Logging | All handler operations logged with structlog |

**New ADRs Needed**: None - follows existing patterns.

# Architecture: Reflection Prompt Configuration

**Branch**: `032-reflection-prompt-config` | **Date**: 2026-01-17 | **Status**: draft
**Spec**: [./spec.md](./spec.md) | **Plan**: [./plan.md](./plan.md) | **Tasks**: [./tasks.md](./tasks.md)

## 0. Links & References

- Feature Spec: `./spec.md`
- Implementation Plan: `./plan.md`
- Tasks: `./tasks.md` (pending generation)
- Related ADRs: ADR-000 (Hexagonal Architecture), ADR-008 (Structured Logging)
- PRs: [link when available]

## 1. Purpose & Scope

### Goal

Enable users to customize the reflection/mutation prompt template via `EvolutionConfig.reflection_prompt`, allowing them to tailor prompt behavior to specific use cases, model capabilities, and output format requirements.

### Non-Goals

- Creating new proposer types or mechanisms
- Changing the core evolution algorithm
- Adding new external dependencies
- Modifying the ADK reflection agent path (only LiteLLM path affected)

### Scope Boundaries

- **In-scope**:
  - New `reflection_prompt` field in `EvolutionConfig`
  - Config wiring through api → adapter → proposer
  - Placeholder validation warnings
  - Documentation for prompt customization
  - Export of `DEFAULT_PROMPT_TEMPLATE`
- **Out-of-scope**:
  - New prompt templates or variations (user responsibility)
  - Changes to ADK reflection agent behavior
  - Persistent prompt storage

### Constraints

- **Technical**: Python 3.12+, no new dependencies, must work with existing proposer infrastructure
- **Organizational**: Must follow hexagonal architecture (config in domain/, wiring through layers)
- **Conventions**: Use structlog for warnings, follow existing `reflection_model` wiring pattern

## 2. Architecture at a Glance

- **Configuration-only feature**: No new runtime logic, purely config passthrough
- **Affects domain layer**: New optional field in `EvolutionConfig` dataclass
- **Wires through 4 layers**: domain → api → adapters → engine/proposer
- **Reuses existing infrastructure**: `AsyncReflectiveMutationProposer` already supports `prompt_template` parameter
- **Validation at config creation**: Warns on missing placeholders via structlog
- **Backward compatible**: `reflection_prompt` defaults to `None` (use existing default)

## 3. Context Diagram (C4 Level 1)

> Shows how this feature fits into the broader system. The reflection prompt configuration affects the LLM Provider interaction.

```mermaid
flowchart TB
    subgraph Legend[" "]
        direction LR
        l1["👤 Actor"]
        l2["🔷 System"]
        l3["📦 External"]
    end

    subgraph Actors[" "]
        user["👤 Developer<br/><i>Configures evolution with<br/>custom reflection prompt</i>"]
    end

    subgraph System[" "]
        gepa["🔷 GEPA-ADK<br/><i>Evolutionary optimization<br/>for ADK agents</i>"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>Agent runtime -<br/>not affected by this feature</i>"]
        llm["📦 LLM Provider<br/><i>Receives customized<br/>reflection prompts</i>"]
    end

    user -->|"Configures<br/>EvolutionConfig.reflection_prompt"| gepa
    gepa -->|"Sends custom prompt<br/>template (LiteLLM)"| llm
    gepa -->|"Executes agents<br/>(unchanged)"| adk

    style l1 fill:#1168BD,color:#E0E0E0
    style l2 fill:#438DD5,color:#E0E0E0
    style l3 fill:#666666,color:#E0E0E0
    style gepa fill:#438DD5,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style user fill:#1168BD,color:#E0E0E0
```

## 4. Container Diagram (C4 Level 2)

> Shows the config flow through major containers.

```mermaid
flowchart TB
    subgraph Actors[" "]
        user["👤 Developer<br/><i>Sets reflection_prompt in config</i>"]
    end

    subgraph GEPA["GEPA-ADK"]
        domain["🔷 Domain<br/><i>domain/models.py</i><br/>EvolutionConfig with new field"]
        api["🔷 Public API<br/><i>api.py</i><br/>evolve() extracts config.reflection_prompt"]
        adapters["🔷 Adapters<br/><i>adapters/</i><br/>ADKAdapter accepts reflection_prompt param"]
        proposer["🔷 Proposer<br/><i>engine/proposer.py</i><br/>Uses prompt_template for LLM calls"]
    end

    subgraph External[" "]
        llm["📦 LLM Provider<br/><i>Receives formatted prompt</i>"]
    end

    user -->|"Creates config"| domain
    user -->|"Calls evolve(config=...)"| api
    api -->|"Passes reflection_prompt"| adapters
    adapters -->|"Passes prompt_template"| proposer
    proposer -->|"Formats & sends<br/>prompt (LiteLLM)"| llm

    style domain fill:#438DD5,color:#E0E0E0
    style api fill:#438DD5,color:#E0E0E0
    style adapters fill:#438DD5,color:#E0E0E0
    style proposer fill:#438DD5,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style user fill:#1168BD,color:#E0E0E0
```

## 5. Component Diagram (C4 Level 3)

> Shows internal components affected by this feature.

```mermaid
flowchart TB
    subgraph domain["domain/"]
        config["📦 EvolutionConfig<br/><i>dataclass</i><br/>NEW: reflection_prompt field"]
    end

    subgraph api_layer["api.py"]
        evolve["📦 evolve()<br/><i>function</i><br/>Extracts config.reflection_prompt"]
        evolve_group["📦 evolve_group()<br/><i>function</i><br/>Extracts config.reflection_prompt"]
    end

    subgraph adapters["adapters/"]
        adk_adapter["📦 ADKAdapter<br/><i>class</i><br/>NEW: reflection_prompt param"]
        multi_adapter["📦 MultiAgentAdapter<br/><i>class</i><br/>NEW: reflection_prompt param"]
    end

    subgraph engine["engine/"]
        proposer["📦 AsyncReflectiveMutationProposer<br/><i>class</i><br/>EXISTING: prompt_template param"]
        default_prompt["📦 DEFAULT_PROMPT_TEMPLATE<br/><i>constant</i><br/>NEW: exported in __all__"]
    end

    evolve -->|"Reads"| config
    evolve -->|"Passes reflection_prompt"| adk_adapter
    evolve_group -->|"Passes reflection_prompt"| multi_adapter
    adk_adapter -->|"Passes prompt_template"| proposer
    multi_adapter -->|"Passes prompt_template"| proposer

    style config fill:#5B9BD5,color:#E0E0E0
    style evolve fill:#5B9BD5,color:#E0E0E0
    style evolve_group fill:#5B9BD5,color:#E0E0E0
    style adk_adapter fill:#5B9BD5,color:#E0E0E0
    style multi_adapter fill:#5B9BD5,color:#E0E0E0
    style proposer fill:#5B9BD5,color:#E0E0E0
    style default_prompt fill:#5B9BD5,color:#E0E0E0
```

## 6. Code Diagram (C4 Level 4)

> Shows class relationships for the reflection_prompt config wiring.

```mermaid
classDiagram
    class EvolutionConfig {
        +str reflection_model
        +str|None reflection_prompt
        +int max_iterations
        +int max_concurrent_evals
        +__post_init__() validates placeholders
    }

    class ADKAdapter {
        -str|None _reflection_prompt
        -ProposerProtocol _proposer
        +__init__(reflection_prompt)
        +evaluate(batch, candidate) EvaluationBatch
    }

    class MultiAgentAdapter {
        -str|None _reflection_prompt
        -ProposerProtocol _proposer
        +__init__(reflection_prompt)
        +evaluate(batch, candidate) EvaluationBatch
    }

    class AsyncReflectiveMutationProposer {
        -str model
        -str prompt_template
        +__init__(prompt_template)
        +propose(candidate, dataset) Candidate
        -_build_messages() list
    }

    class DEFAULT_PROMPT_TEMPLATE {
        <<constant>>
        +str value
    }

    EvolutionConfig --> ADKAdapter : reflection_prompt
    EvolutionConfig --> MultiAgentAdapter : reflection_prompt
    ADKAdapter --> AsyncReflectiveMutationProposer : prompt_template
    MultiAgentAdapter --> AsyncReflectiveMutationProposer : prompt_template
    AsyncReflectiveMutationProposer --> DEFAULT_PROMPT_TEMPLATE : fallback if None
```

## 7. Hexagonal Architecture View

> Shows how this feature aligns with hexagonal architecture layers.

```mermaid
flowchart TB
    subgraph External["External Systems"]
        LLM["LLM Provider<br/>(receives custom prompt)"]
    end

    subgraph Adapters["adapters/ (External Integration)"]
        ADKAdapter["ADKAdapter<br/>+ reflection_prompt param"]
        MultiAgent["MultiAgentAdapter<br/>+ reflection_prompt param"]
    end

    subgraph Engine["engine/ (Orchestration)"]
        Proposer["AsyncReflectiveMutationProposer<br/>(existing prompt_template)"]
        DefaultPrompt["DEFAULT_PROMPT_TEMPLATE<br/>(newly exported)"]
    end

    subgraph Domain["domain/ (Pure Python)"]
        Config["EvolutionConfig<br/>+ reflection_prompt: str | None"]
        Validation["__post_init__<br/>(placeholder warnings)"]
    end

    subgraph API["api.py (Public Interface)"]
        Evolve["evolve()<br/>(wires config)"]
        EvolveGroup["evolve_group()<br/>(wires config)"]
    end

    API --> Adapters
    Adapters --> Engine
    Engine --> External
    Domain --> API

    style Config fill:#D4740C,color:#E0E0E0
    style ADKAdapter fill:#D4740C,color:#E0E0E0
    style MultiAgent fill:#D4740C,color:#E0E0E0
    style DefaultPrompt fill:#D4740C,color:#E0E0E0
```

**Legend**: 🔶 Orange = Modified components (colorblind-safe highlight)

## 8. Runtime Behavior (Sequence Diagrams)

### 8.1 Happy Path: Custom Prompt Configuration

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant D as domain/models.py
    participant API as api.py
    participant A as ADKAdapter
    participant P as Proposer
    participant LLM as LLM Provider

    U->>D: EvolutionConfig(reflection_prompt="...")
    D->>D: __post_init__ validates placeholders
    Note over D: Warns if {current_instruction}<br/>or {feedback_examples} missing

    U->>API: evolve(agent, scorer, config=config)
    API->>API: resolved_config = config or EvolutionConfig()
    API->>A: ADKAdapter(..., reflection_prompt=config.reflection_prompt)
    A->>P: AsyncReflectiveMutationProposer(prompt_template=reflection_prompt)

    Note over P: Evolution loop runs...

    P->>P: _build_messages(current_text, feedback)
    P->>P: prompt_template.format(<br/>current_instruction=...,<br/>feedback_examples=...)
    P->>LLM: acompletion(messages=[{role: "user", content: formatted_prompt}])
    LLM-->>P: improved_instruction
    P-->>API: mutated candidate
```

### 8.2 Edge Case: Missing Placeholder Warning

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant D as domain/models.py
    participant Log as structlog

    U->>D: EvolutionConfig(reflection_prompt="Improve: {current_instruction}")
    D->>D: __post_init__ validates
    D->>Log: warning("reflection_prompt missing {feedback_examples}")
    Note over D: Config creation succeeds<br/>(warning, not error)
    D-->>U: EvolutionConfig instance
```

### 8.3 Edge Case: Empty String Fallback

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant D as domain/models.py
    participant Log as structlog
    participant P as Proposer

    U->>D: EvolutionConfig(reflection_prompt="")
    D->>D: __post_init__ detects empty string
    D->>Log: info("Empty reflection_prompt, using default")
    Note over D: Internally set to None

    Note over P: Later, in proposer...
    P->>P: prompt_template = reflection_prompt or DEFAULT_PROMPT_TEMPLATE
    Note over P: Uses DEFAULT_PROMPT_TEMPLATE
```

## 9. Data Model & Contracts

### 9.1 Data Changes (Config Schema)

> No persistent data changes. Config is in-memory only.

```mermaid
erDiagram
    EVOLUTION_CONFIG {
        string reflection_model "Existing field"
        string reflection_prompt "NEW: Optional custom template"
        int max_iterations "Existing field"
        int max_concurrent_evals "Existing field"
        float min_improvement_threshold "Existing field"
        int patience "Existing field"
    }

    PROMPT_TEMPLATE {
        string current_instruction "Required placeholder"
        string feedback_examples "Required placeholder"
    }

    EVOLUTION_CONFIG ||--o| PROMPT_TEMPLATE : "contains placeholders"
```

### 9.2 API Contracts

**Public API Changes**:

| Component | Change | Backward Compatible |
|-----------|--------|---------------------|
| `EvolutionConfig.reflection_prompt` | NEW field: `str \| None = None` | Yes (defaults to None) |
| `DEFAULT_PROMPT_TEMPLATE` | NEW export from `engine.proposer` | Yes (additive) |

**Internal Changes**:

| Component | Change |
|-----------|--------|
| `api.evolve()` | Passes `config.reflection_prompt` to ADKAdapter |
| `api.evolve_group()` | Passes `config.reflection_prompt` to MultiAgentAdapter |
| `ADKAdapter.__init__()` | NEW param: `reflection_prompt: str \| None = None` |
| `MultiAgentAdapter.__init__()` | NEW param: `reflection_prompt: str \| None = None` |

## 10. Deployment / Infrastructure View

> Not applicable - this is a configuration-only feature with no infrastructure changes.

## 11. Quality Attributes (NFRs)

| Attribute | Requirement | Verification |
|-----------|-------------|--------------|
| **Performance** | No runtime overhead (config passthrough only) | N/A |
| **Reliability** | Graceful fallback on empty/invalid prompt | Unit test for empty string handling |
| **Maintainability** | Follows existing config wiring pattern | Code review |
| **Observability** | Structured logging for validation warnings | Log format verification |
| **Backward Compatibility** | Existing code works without changes | Integration test without reflection_prompt |

## 12. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Contract** | N/A | No new protocols - config dataclass only | — |
| **Unit** | `tests/unit/test_config.py` | Config validation, placeholder warnings | `@pytest.mark.unit` |
| **Integration** | `tests/integration/test_reflection_prompt.py` | Custom prompt actually used | `@pytest.mark.integration` |

**Key Test Scenarios**:

1. **Valid custom prompt**: Create config with both placeholders, verify no warnings
2. **Missing placeholder warning**: Create config missing `{feedback_examples}`, verify warning logged
3. **Empty string fallback**: Create config with `reflection_prompt=""`, verify default used
4. **End-to-end**: Run evolution with custom prompt, verify LLM receives formatted prompt
5. **Default behavior**: Run evolution without reflection_prompt, verify DEFAULT_PROMPT_TEMPLATE used

## 13. Risks & Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users create invalid prompts | LLM returns poor responses | Validation warnings + documentation |
| Prompt injection concerns | Unlikely (user controls their own config) | Document that prompt content is user responsibility |

### Open Questions

- [x] Should validation be warning or error? **Decision: Warning** (per research.md)
- [x] How to handle empty string? **Decision: Treat as None + info log**

### TODOs

- [ ] Create comprehensive prompt documentation at `docs/guides/reflection-prompts.md`

## 14. Decisions (ADR References)

| ADR | Title | Relevance to This Feature |
|-----|-------|---------------------------|
| ADR-000 | Hexagonal Architecture | Config in domain/, wiring through layers follows pattern |
| ADR-008 | Structured Logging | Validation warnings use structlog |

**New ADRs Needed**:
- None - feature follows existing patterns

---

## Diagram Standards Reference

Diagrams used in this document:

| Diagram Type | Purpose | Sections |
|--------------|---------|----------|
| **C4 Context** | System boundaries | Section 3 |
| **C4 Container** | Config flow through containers | Section 4 |
| **C4 Component** | Affected components | Section 5 |
| **Hexagonal** | Layer compliance | Section 6 |
| **Sequence** | Config wiring at runtime | Section 7 (3 diagrams) |
| **ERD** | Config schema | Section 8 |

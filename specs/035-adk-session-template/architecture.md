# Architecture: ADK Session State Template Substitution

**Branch**: `035-adk-session-template` | **Date**: 2026-01-18 | **Status**: draft
**Spec**: [./spec.md](./spec.md) | **Plan**: [./plan.md](./plan.md) | **Tasks**: [./tasks.md](./tasks.md)

## 0. Links & References

- Feature Spec: `./spec.md`
- Implementation Plan: `./plan.md`
- Tasks: `./tasks.md`
- Related ADRs: ADR-000 (Hexagonal), ADR-001 (Async-First), ADR-005 (Three-Layer Testing)
- GitHub Issue: #99

## 1. Purpose & Scope

### Goal

Enable ADK's native template substitution syntax (`{key}`) in reflection agent instructions, replacing the current workaround of manually embedding data in user messages via Python f-strings.

### Non-Goals

- Custom template syntax beyond ADK's native support
- Template substitution in tool descriptions or other agent properties
- Dynamic session state updates during agent execution

### Scope Boundaries

- **In-scope**: Modify `adk_reflection.py` to use `{key}` placeholders, add tests, update docs
- **Out-of-scope**: Changes to other adapters, new public APIs, persistence layer changes

### Constraints

- **Technical**: Must work across all LLM providers (Gemini, Ollama, OpenAI); no new dependencies
- **Organizational**: Must follow hexagonal architecture; changes only in `engine/` layer
- **Conventions**: Use ADK's `{key}` syntax (not `{state.key}`); pre-serialize complex types to JSON

## 2. Architecture at a Glance

- **ADK provides native template substitution** via `inject_session_state()` in `google.adk.utils.instructions_utils`
- **Syntax is `{key}`** which maps to `session.state[key]`; optional variant `{key?}` returns empty string if missing
- **Template processing occurs automatically** during `Runner.run_async()` before sending to LLM
- **Current workaround** embeds data in user messages via f-strings, bypassing ADK's template system
- **Proposed change** moves data to session state and uses `{key}` placeholders in agent instruction
- **No protocol changes** — `ReflectionFn` signature remains unchanged; internal implementation detail only

## 3. Context Diagram (C4 Level 1)

> Shows how template substitution fits into the broader system and external dependencies.

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
        dev["👤 Developer<br/><i>Configures evolution<br/>with reflection agent</i>"]
    end

    subgraph System[" "]
        gepa["🔷 GEPA-ADK<br/><i>Evolutionary optimization<br/>for ADK agents</i>"]
        reflection["🔶 Reflection Function<br/><i>Uses ADK templates<br/>for data injection</i>"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>inject_session_state()<br/>template processing</i>"]
        llm["📦 LLM Provider<br/><i>Receives processed<br/>instruction</i>"]
        session["📦 InMemorySessionService<br/><i>Stores state for<br/>template substitution</i>"]
    end

    dev -->|"Calls evolve()<br/>with LlmAgent"| gepa
    gepa -->|"Creates"| reflection
    reflection -->|"Populates<br/>session.state"| session
    reflection -->|"Runner.run_async()<br/>triggers template"| adk
    adk -->|"Substitutes {key}<br/>from session.state"| session
    adk -->|"Sends processed<br/>instruction"| llm

    style l1 fill:#1168BD,color:#E0E0E0
    style l2 fill:#438DD5,color:#E0E0E0
    style l3 fill:#666666,color:#E0E0E0
    style l4 fill:#D4740C,color:#E0E0E0
    style dev fill:#1168BD,color:#E0E0E0
    style gepa fill:#438DD5,color:#E0E0E0
    style reflection fill:#D4740C,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style session fill:#666666,color:#E0E0E0
```

## 4. Container Diagram (C4 Level 2)

> Shows the containers involved in template substitution flow.

```mermaid
flowchart TB
    subgraph GEPA["GEPA-ADK"]
        api["🔷 Public API<br/><i>Python</i><br/>evolve(), evolve_sync()"]
        engine["🔷 AsyncGEPAEngine<br/><i>Python</i><br/>Evolution orchestration"]
        reflection["🔶 adk_reflection.py<br/><i>Python</i><br/>Template-based reflection"]
    end

    subgraph ADK["Google ADK"]
        runner["📦 Runner<br/><i>Agent execution</i>"]
        instructions["📦 instructions_utils<br/><i>inject_session_state()</i>"]
        session_svc["📦 InMemorySessionService<br/><i>Session state storage</i>"]
    end

    subgraph LLM["LLM Provider"]
        model["📦 LLM Model<br/><i>Gemini/Ollama/OpenAI</i>"]
    end

    api -->|"Calls"| engine
    engine -->|"Uses"| reflection
    reflection -->|"1. create_session(state)"| session_svc
    reflection -->|"2. run_async()"| runner
    runner -->|"3. _process_agent_instruction()"| instructions
    instructions -->|"4. Read state[key]"| session_svc
    instructions -->|"5. Send processed instruction"| model

    style api fill:#438DD5,color:#E0E0E0
    style engine fill:#438DD5,color:#E0E0E0
    style reflection fill:#D4740C,color:#E0E0E0
    style runner fill:#666666,color:#E0E0E0
    style instructions fill:#666666,color:#E0E0E0
    style session_svc fill:#666666,color:#E0E0E0
    style model fill:#666666,color:#E0E0E0
```

## 5. ADK Template Substitution Internals

> Shows how ADK processes `{key}` placeholders internally.

```mermaid
flowchart LR
    subgraph Input["Agent Definition"]
        instruction["instruction:<br/>'Improve: {component_text}<br/>Trials: {trials}'"]
    end

    subgraph SessionState["Session State"]
        state["state = {<br/>  'component_text': '...',<br/>  'trials': '{...}'<br/>}"]
    end

    subgraph Processing["ADK Processing"]
        regex["1. Match regex<br/>r'{+[^{}]*}+'"]
        validate["2. Validate key name<br/>_is_valid_state_name()"]
        lookup["3. Lookup in state<br/>session.state[key]"]
        convert["4. Convert to string<br/>str(value)"]
    end

    subgraph Output["Processed Instruction"]
        result["'Improve: You are...<br/>Trials: [{score:0.5}]'"]
    end

    instruction --> regex
    regex --> validate
    validate --> lookup
    state --> lookup
    lookup --> convert
    convert --> result

    style instruction fill:#438DD5,color:#E0E0E0
    style state fill:#438DD5,color:#E0E0E0
    style regex fill:#5B9BD5,color:#E0E0E0
    style validate fill:#5B9BD5,color:#E0E0E0
    style lookup fill:#5B9BD5,color:#E0E0E0
    style convert fill:#5B9BD5,color:#E0E0E0
    style result fill:#438DD5,color:#E0E0E0
```

## 6. Hexagonal Architecture View

> Shows how this feature aligns with the hexagonal (ports & adapters) architecture.

```mermaid
flowchart TB
    subgraph External["External Systems"]
        ADK["📦 Google ADK<br/><i>inject_session_state()</i>"]
        LLM["📦 LLM Provider"]
        Session["📦 InMemorySessionService"]
    end

    subgraph Adapters["adapters/ (NO CHANGES)"]
        ADKAdapter["ADKAdapter"]
        MultiAgent["MultiAgentAdapter"]
    end

    subgraph Ports["ports/ (NO CHANGES)"]
        AdapterPort["AsyncGEPAAdapter Protocol"]
        ScorerPort["Scorer Protocol"]
    end

    subgraph Engine["engine/ (MODIFIED)"]
        GEPAEngine["AsyncGEPAEngine"]
        Reflection["🔶 adk_reflection.py<br/><i>Uses {key} templates</i>"]
    end

    subgraph Domain["domain/ (NO CHANGES)"]
        Models["EvolutionConfig, Candidate"]
    end

    Engine --> Ports
    Ports --> Adapters
    Adapters --> External
    Engine --> Domain
    Reflection --> ADK
    Reflection --> Session

    style ADK fill:#666666,color:#E0E0E0
    style LLM fill:#666666,color:#E0E0E0
    style Session fill:#666666,color:#E0E0E0
    style Reflection fill:#D4740C,color:#E0E0E0
```

**Layer Impact**: Only `engine/adk_reflection.py` is modified. No changes to ports, adapters, or domain layers.

## 7. Runtime Behavior (Sequence Diagrams)

### 7.1 Happy Path: Template Substitution During Reflection

```mermaid
sequenceDiagram
    autonumber
    participant E as Engine
    participant R as adk_reflection.py
    participant SS as InMemorySessionService
    participant Runner as ADK Runner
    participant IU as instructions_utils
    participant LLM as LLM Provider

    E->>R: reflection_fn(component_text, trials)

    Note over R: Prepare session state
    R->>R: state = {component_text, trials_json}
    R->>SS: create_session(state)
    SS-->>R: session_id

    Note over R: Execute with templated instruction
    R->>Runner: run_async(session_id, trigger_message)

    Note over Runner: ADK processes instruction
    Runner->>IU: inject_session_state(instruction, context)
    IU->>SS: read state["component_text"]
    SS-->>IU: "You are a helpful..."
    IU->>SS: read state["trials"]
    SS-->>IU: "[{score: 0.5}]"
    IU-->>Runner: processed instruction

    Runner->>LLM: send(processed_instruction + trigger)
    LLM-->>Runner: improved component text
    Runner-->>R: events
    R->>R: extract_final_output(events)
    R-->>E: improved_component_text
```

### 7.2 Error Path: Missing Session State Key

```mermaid
sequenceDiagram
    autonumber
    participant R as adk_reflection.py
    participant SS as InMemorySessionService
    participant Runner as ADK Runner
    participant IU as instructions_utils

    R->>SS: create_session(state={trials: "..."})
    Note over SS: Missing "component_text" key!
    SS-->>R: session_id

    R->>Runner: run_async(session_id, message)
    Runner->>IU: inject_session_state(instruction, context)

    IU->>SS: read state["component_text"]
    SS-->>IU: KeyError!

    Note over IU: Required key missing
    IU-->>Runner: raise KeyError("Context variable not found: `component_text`")
    Runner-->>R: Exception propagates

    Note over R: Handle error gracefully
    R-->>R: Log warning, return fallback
```

## 8. Data Model

> No new data structures. Session state format unchanged.

### Session State Structure

```python
session_state: dict[str, Any] = {
    "component_text": str,   # Plain text - agent instruction to improve
    "trials": str,           # JSON string - serialized trial results
}
```

### Template Syntax Reference

| Syntax | Behavior | Use Case |
|--------|----------|----------|
| `{key}` | Substitute or raise KeyError | Required data |
| `{key?}` | Substitute or return "" | Optional data |
| `{app:key}` | App-scoped state | Shared config |
| `{user:key}` | User-scoped state | User preferences |
| `{temp:key}` | Temporary state | Scratch data |

## 9. Before/After Comparison

### Current Implementation (Workaround)

```mermaid
flowchart LR
    subgraph Current["CURRENT: f-string in user message"]
        data1["component_text<br/>trials"]
        fstring["Python f-string<br/>interpolation"]
        message["user_message =<br/>'## Component...<br/>{component_text}'"]
        agent1["LlmAgent<br/>instruction: static"]
    end

    data1 --> fstring --> message
    message --> agent1

    style fstring fill:#666666,color:#E0E0E0
    style message fill:#666666,color:#E0E0E0
```

### Proposed Implementation (ADK Templates)

```mermaid
flowchart LR
    subgraph Proposed["PROPOSED: ADK template substitution"]
        data2["component_text<br/>trials"]
        state["session.state = {<br/>component_text,<br/>trials}"]
        adk["ADK<br/>inject_session_state()"]
        agent2["LlmAgent<br/>instruction:<br/>'{component_text}'"]
    end

    data2 --> state
    state --> adk
    adk --> agent2

    style state fill:#D4740C,color:#E0E0E0
    style adk fill:#D4740C,color:#E0E0E0
```

## 10. Quality Attributes (NFRs)

| Attribute | Requirement | Verification |
|-----------|-------------|--------------|
| **Performance** | No increase in execution time vs workaround | Benchmark comparison test |
| **Reliability** | KeyError on missing required keys (fail-fast) | Unit test for error cases |
| **Compatibility** | Works with Gemini, Ollama, OpenAI | Multi-provider integration tests |
| **Maintainability** | Uses ADK-native patterns | Code review |
| **Observability** | Structured logging preserved | Log format verification |

## 11. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Unit** | `tests/unit/engine/test_adk_reflection.py` | Template placeholder detection, JSON serialization, error handling | `@pytest.mark.unit` |
| **Integration** | `tests/integration/test_reflection_template.py` | End-to-end with real LLM, multi-provider | `@pytest.mark.slow` |

**Key Test Scenarios**:
1. Single placeholder substitution with valid state
2. Multiple placeholder substitution
3. Missing required key raises KeyError
4. Optional placeholder returns empty string when missing
5. Non-string values converted via str()
6. Output equivalence with current workaround

## 12. Risks & Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Template syntax undocumented | May change in future ADK versions | Pin ADK version; verified in source |
| Model provider differences | Some models may handle instruction differently | Multi-provider integration tests |
| Breaking existing behavior | Users depending on current message format | Feature flag for rollback |

### Open Questions

- [x] What is the correct template syntax? → **Resolved: `{key}` not `{state.key}`**
- [x] How are complex types handled? → **Resolved: Use `json.dumps()` pre-serialization**
- [ ] Should we support optional placeholders `{key?}` for future flexibility?

## 13. Decisions (ADR References)

| ADR | Title | Relevance to This Feature |
|-----|-------|---------------------------|
| ADR-000 | Hexagonal Architecture | Changes only in engine/ layer; no adapter changes |
| ADR-001 | Async-First | Existing async flow unchanged |
| ADR-005 | Three-Layer Testing | Unit + integration tests for template behavior |

**New ADRs Needed**: None — this feature uses existing patterns.

---

## Appendix: ADK Source Code References

| Component | Location (in .venv) | Purpose |
|-----------|---------------------|---------|
| `inject_session_state()` | `google/adk/utils/instructions_utils.py` | Main template processing |
| `_replace_match()` | `google/adk/utils/instructions_utils.py` | Individual placeholder handling |
| `_is_valid_state_name()` | `google/adk/utils/instructions_utils.py` | Key name validation |
| `State` prefixes | `google/adk/sessions/state.py` | APP, USER, TEMP prefix constants |
| `_process_agent_instruction()` | `google/adk/flows/llm_flows/instructions.py` | Template integration in flow |

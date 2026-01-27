# Architecture: Multimodal Input Support

**Branch**: `235-multimodal-input` | **Date**: 2026-01-27 | **Status**: draft
**Spec**: [./spec.md](./spec.md) | **Plan**: [./plan.md](./plan.md) | **Tasks**: [./tasks.md](./tasks.md)

## 0. Links & References

- Feature Spec: `./spec.md`
- Implementation Plan: `./plan.md`
- Tasks: `./tasks.md`
- Related ADRs:
  - ADR-000: Hexagonal Architecture
  - ADR-001: Async-First Architecture
  - ADR-002: Protocol for Interfaces
  - ADR-005: Three-Layer Testing
  - ADR-006: External Library Integration
  - ADR-008: Structured Logging
  - ADR-009: Exception Hierarchy
- PRs: [link when available]

## 1. Purpose & Scope

### Goal

Enable trainset/valset examples to include video files alongside text prompts, allowing GEPA to evolve multimodal agents (e.g., video transcription, visual analysis) without text-only workarounds.

### Non-Goals

- Image file support (future iteration)
- Audio-only file support (future iteration)
- Video streaming or URL-based inputs
- Video preprocessing (resizing, compression)
- Remote storage integration (S3, GCS)
- Video caching optimization

### Scope Boundaries

- **In-scope**: Video file loading, validation, blob conversion, Content assembly, backward compatibility
- **Out-of-scope**: Non-video media types, cloud storage, preprocessing

### Constraints

- **Technical**: 2GB max file size (Gemini API limit), video/* MIME types only, local filesystem paths
- **Organizational**: Must follow hexagonal architecture, ADK types only in adapters layer
- **Conventions**: Protocol-based interfaces, async methods for I/O, structlog for observability

## 2. Architecture at a Glance

- **New port interface**: `VideoBlobServiceProtocol` defines video loading contract
- **New adapter**: `VideoBlobService` implements file I/O and Part creation
- **Extended executor**: `AgentExecutor.execute_agent()` accepts optional `Content` input
- **Extended adapter**: `ADKAdapter._run_single_example()` assembles multimodal Content
- **Extended validation**: `_validate_dataset()` allows `videos` field alternative to `input`
- **New exception**: `VideoValidationError` for file validation failures
- **Preserved compatibility**: Text-only trainsets work unchanged

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
        user["👤 ML Engineer<br/><i>Evolving multimodal agents</i>"]
    end

    subgraph System[" "]
        gepa["🔶 GEPA-ADK<br/><i>Evolutionary optimization<br/>with multimodal support</i>"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>Agent runtime with<br/>multimodal Content</i>"]
        llm["📦 Gemini API<br/><i>Multimodal-capable<br/>LLM provider</i>"]
        files["📦 Filesystem<br/><i>Local video files<br/>(MP4, MOV, etc.)</i>"]
    end

    user -->|"trainset with<br/>video paths"| gepa
    gepa -->|"Content(text+video)"| adk
    gepa -->|"Reflection<br/>(LiteLLM)"| llm
    gepa -->|"Read video<br/>bytes"| files

    style l1 fill:#1168BD,color:#E0E0E0
    style l2 fill:#438DD5,color:#E0E0E0
    style l3 fill:#666666,color:#E0E0E0
    style l4 fill:#D4740C,color:#E0E0E0
    style gepa fill:#D4740C,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style llm fill:#666666,color:#E0E0E0
    style files fill:#666666,color:#E0E0E0
    style user fill:#1168BD,color:#E0E0E0
```

## 4. Container Diagram (C4 Level 2)

```mermaid
flowchart TB
    subgraph Actors[" "]
        user["👤 ML Engineer<br/><i>Uses evolve() API</i>"]
    end

    subgraph GEPA["GEPA-ADK"]
        api["🔶 Public API<br/><i>Python</i><br/>evolve() with videos field"]
        engine["🔷 Evolution Engine<br/><i>Python</i><br/>AsyncGEPAEngine"]
        adapters["🔶 Adapters<br/><i>Python</i><br/>ADKAdapter, VideoBlobService"]
        executor["🔶 Agent Executor<br/><i>Python</i><br/>Multimodal Content support"]
    end

    subgraph External[" "]
        adk["📦 Google ADK<br/><i>Part, Content types</i>"]
        files["📦 Filesystem<br/><i>Video files</i>"]
    end

    user -->|"trainset[{videos}]"| api
    api -->|"Validates dataset"| engine
    engine -->|"evaluate()"| adapters
    adapters -->|"load video bytes"| files
    adapters -->|"Content(parts)"| executor
    executor -->|"run_async()"| adk

    style api fill:#D4740C,color:#E0E0E0
    style engine fill:#438DD5,color:#E0E0E0
    style adapters fill:#D4740C,color:#E0E0E0
    style executor fill:#D4740C,color:#E0E0E0
    style adk fill:#666666,color:#E0E0E0
    style files fill:#666666,color:#E0E0E0
    style user fill:#1168BD,color:#E0E0E0
```

## 5. Component Diagram (C4 Level 3)

```mermaid
flowchart TB
    subgraph adapters["adapters/ (Modified)"]
        video_service["🔶 VideoBlobService<br/><i>NEW</i><br/>Video file I/O"]
        adk_adapter["🔶 ADKAdapter<br/><i>MODIFIED</i><br/>Content assembly"]
        agent_executor["🔶 AgentExecutor<br/><i>MODIFIED</i><br/>Multimodal input"]
        critic["📦 CriticScorer<br/><i>Unchanged</i>"]
    end

    subgraph ports["ports/ (Modified)"]
        video_protocol["🔶 VideoBlobServiceProtocol<br/><i>NEW</i><br/>Video loading contract"]
        adapter_protocol["📦 AsyncGEPAAdapter<br/><i>Unchanged</i>"]
        executor_protocol["📦 AgentExecutorProtocol<br/><i>Unchanged signature</i>"]
    end

    subgraph domain["domain/ (Modified)"]
        exceptions["🔶 VideoValidationError<br/><i>NEW</i><br/>File validation errors"]
        models["📦 Models<br/><i>Unchanged</i>"]
    end

    video_service -->|"Implements"| video_protocol
    adk_adapter -->|"Uses"| video_service
    adk_adapter -->|"Uses"| agent_executor
    adk_adapter -->|"Implements"| adapter_protocol
    video_service -->|"Raises"| exceptions

    style video_service fill:#D4740C,color:#E0E0E0
    style adk_adapter fill:#D4740C,color:#E0E0E0
    style agent_executor fill:#D4740C,color:#E0E0E0
    style video_protocol fill:#D4740C,color:#E0E0E0
    style exceptions fill:#D4740C,color:#E0E0E0
    style critic fill:#5B9BD5,color:#E0E0E0
    style adapter_protocol fill:#5B9BD5,color:#E0E0E0
    style executor_protocol fill:#5B9BD5,color:#E0E0E0
    style models fill:#5B9BD5,color:#E0E0E0
```

## 6. Code Diagram (C4 Level 4)

```mermaid
classDiagram
    class VideoBlobServiceProtocol {
        <<protocol>>
        +prepare_video_parts(video_paths) list~Part~
        +validate_video_file(video_path) VideoFileInfo
    }

    class VideoBlobService {
        +prepare_video_parts(video_paths) list~Part~
        +validate_video_file(video_path) VideoFileInfo
        -_detect_mime_type(path) str
        -MAX_VIDEO_SIZE_BYTES: int
    }

    class VideoFileInfo {
        +path: str
        +size_bytes: int
        +mime_type: str
    }

    class VideoValidationError {
        +video_path: str
        +field: str
        +constraint: str
    }

    class ConfigurationError {
        +field: str
        +value: object
        +constraint: str
    }

    class ADKAdapter {
        -_executor: AgentExecutor
        -_video_service: VideoBlobServiceProtocol
        +_run_single_example(example) str
        -_prepare_multimodal_content(example) Content
    }

    class AgentExecutor {
        +execute_agent(agent, input_text, input_content) ExecutionResult
        -_build_content(input_text, input_content) Content
    }

    VideoBlobService ..|> VideoBlobServiceProtocol : implements
    VideoBlobService --> VideoFileInfo : returns
    VideoBlobService --> VideoValidationError : raises
    VideoValidationError --|> ConfigurationError : extends
    ADKAdapter --> VideoBlobServiceProtocol : uses
    ADKAdapter --> AgentExecutor : uses
```

## 7. Hexagonal Architecture View

```mermaid
flowchart TB
    subgraph External["External Systems"]
        ADK["Google ADK<br/>(Part, Content, Runner)"]
        LLM["LLM Provider"]
        FS["Filesystem<br/>(Video Files)"]
    end

    subgraph Adapters["adapters/ (External Integration)"]
        direction TB
        VBS["🔶 VideoBlobService<br/>NEW: Video file I/O"]
        ADKA["🔶 ADKAdapter<br/>MOD: Content assembly"]
        AE["🔶 AgentExecutor<br/>MOD: Multimodal input"]
        Proposer["AsyncReflectiveMutationProposer"]
    end

    subgraph Ports["ports/ (Interfaces)"]
        VBP["🔶 VideoBlobServiceProtocol<br/>NEW"]
        AdapterPort["AsyncGEPAAdapter Protocol"]
        ScorerPort["Scorer Protocol"]
    end

    subgraph Engine["engine/ (Orchestration)"]
        GEPAEngine["AsyncGEPAEngine"]
    end

    subgraph Domain["domain/ (Pure Python)"]
        Exceptions["🔶 VideoValidationError<br/>NEW"]
        Models["EvolutionConfig, Candidate"]
    end

    subgraph API["api.py (Public Interface)"]
        Evolve["🔶 evolve()<br/>MOD: videos validation"]
    end

    API --> Engine
    Engine --> Ports
    Ports --> Adapters
    VBS --> FS
    AE --> ADK
    Proposer --> LLM
    VBS --> Domain
    ADKA --> VBS
    ADKA --> AE

    style VBS fill:#D4740C,color:#E0E0E0
    style ADKA fill:#D4740C,color:#E0E0E0
    style AE fill:#D4740C,color:#E0E0E0
    style VBP fill:#D4740C,color:#E0E0E0
    style Exceptions fill:#D4740C,color:#E0E0E0
    style Evolve fill:#D4740C,color:#E0E0E0
```

## 8. Runtime Behavior (Sequence Diagrams)

### 8.1 Happy Path: Multimodal Evolution

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant API as api.py
    participant VAL as _validate_dataset
    participant E as Engine
    participant A as ADKAdapter
    participant VBS as VideoBlobService
    participant FS as Filesystem
    participant AE as AgentExecutor
    participant ADK as Google ADK

    U->>API: evolve(agent, trainset=[{input, videos}])
    API->>VAL: _validate_dataset(trainset)
    VAL-->>API: OK (input or videos present)
    API->>E: run evolution

    loop Each iteration
        E->>A: evaluate(batch, candidate)

        loop Each example
            A->>VBS: prepare_video_parts(videos)
            VBS->>FS: read video bytes
            FS-->>VBS: bytes
            VBS-->>A: list[Part]

            A->>A: _prepare_multimodal_content()
            Note over A: Content(parts=[Part(text), Part(video)])

            A->>AE: execute_agent(agent, input_content=content)
            AE->>ADK: run_async(content)
            ADK-->>AE: events/output
            AE-->>A: ExecutionResult
        end

        A-->>E: EvaluationBatch
    end

    E-->>API: best candidate
    API-->>U: EvolutionResult
```

### 8.2 Error Case: Video Validation Failure

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant A as ADKAdapter
    participant VBS as VideoBlobService
    participant FS as Filesystem

    U->>A: _run_single_example({videos: ["/bad/path.mp4"]})
    A->>VBS: prepare_video_parts(["/bad/path.mp4"])
    VBS->>VBS: validate_video_file("/bad/path.mp4")
    VBS->>FS: check exists
    FS-->>VBS: FileNotFoundError

    Note over VBS: Wrap in VideoValidationError
    VBS-->>A: VideoValidationError("not found")
    A-->>U: Propagate error with context
```

## 9. Data Model & Contracts

### 9.1 Data Changes (No Persistence)

This feature does not add persistent data. Video files are read on-demand and converted to in-memory Part objects.

```mermaid
erDiagram
    TRAINSET_EXAMPLE {
        string input "Optional if videos present"
        list videos "Optional: list of file paths"
        string expected "Optional: reference output"
    }
    VIDEO_FILE_INFO {
        string path "Absolute file path"
        int size_bytes "File size"
        string mime_type "video/* MIME type"
    }
    TRAINSET_EXAMPLE ||--o{ VIDEO_FILE_INFO : "validates to"
```

### 9.2 API Contracts

**Public API Changes**:
- `evolve()` — Trainset examples now accept optional `videos` field
- `_validate_dataset()` — Validates `input` OR `videos` present (not both required)

**New Protocol**:
- `VideoBlobServiceProtocol` — Contract for video loading (see contracts/video-blob-service.md)

**Extended Signature**:
- `AgentExecutor.execute_agent()` — New optional `input_content: Content` parameter

## 10. Deployment / Infrastructure View

No infrastructure changes. Video files are read from local filesystem during execution.

## 11. Quality Attributes (NFRs)

| Attribute | Requirement | Verification |
|-----------|-------------|--------------|
| **Performance** | Video loading adds <1s overhead per file | Unit tests with timing |
| **Reliability** | Clear errors for missing/invalid files | Error handling tests |
| **Memory** | No memory leaks for large videos | Integration tests with monitoring |
| **Maintainability** | Hexagonal architecture compliance | Layer import rules |
| **Observability** | Structured logging for video ops | Log format verification |
| **Compatibility** | 100% backward compatible | Existing test suite passes |

## 12. Testing Strategy

| Layer | Location | What to Test | Markers |
|-------|----------|--------------|---------|
| **Contract** | `tests/contracts/test_video_blob_contract.py` | Protocol compliance | `@pytest.mark.contract` |
| **Unit** | `tests/unit/adapters/test_video_blob_service.py` | Service logic with mocks | `@pytest.mark.unit` |
| **Unit** | `tests/unit/adapters/test_adk_adapter_multimodal.py` | Content assembly | `@pytest.mark.unit` |
| **Integration** | `tests/integration/test_multimodal_evolution.py` | End-to-end with real files | `@pytest.mark.integration` |

**Key Test Scenarios**:
1. Happy path: Video + text evolution with critic scoring
2. Backward compatibility: Text-only trainsets unchanged
3. Error handling: Missing file, oversized file, invalid MIME type
4. Edge cases: Multiple videos, video-only input, empty paths

## 13. Risks & Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Memory pressure with large videos | OOM errors during evolution | Document size limits, test with large files |
| Model provider video support varies | Some models may fail | Document supported models, graceful errors |
| File locking on Windows | Cannot read open videos | Document behavior, use read-only mode |

### Open Questions

- [x] Should videos be cached? → No, defer to future optimization
- [x] Handle duplicate video paths? → Process each reference

### TODOs

- [ ] Add performance benchmarks for video loading
- [ ] Document supported video formats per provider

## 14. Decisions (ADR References)

| ADR | Title | Relevance to This Feature |
|-----|-------|---------------------------|
| ADR-000 | Hexagonal Architecture | VideoBlobService in adapters/, protocol in ports/ |
| ADR-001 | Async-First | async prepare_video_parts() |
| ADR-002 | Protocol Interfaces | VideoBlobServiceProtocol with @runtime_checkable |
| ADR-005 | Three-Layer Testing | Contract, unit, integration tests |
| ADR-006 | External Library Integration | google.genai.types only in adapters/ |
| ADR-008 | Structured Logging | Video loading events logged |
| ADR-009 | Exception Hierarchy | VideoValidationError extends ConfigurationError |

**New ADRs Needed**: None

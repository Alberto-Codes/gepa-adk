# Tasks: Multimodal Input Support

**Feature**: 235-multimodal-input
**Date**: 2026-01-27
**Spec**: [./spec.md](./spec.md) | **Plan**: [./plan.md](./plan.md) | **Architecture**: [./architecture.md](./architecture.md)

---

## Phase 1: Setup

### Task 1.1: Create Feature Branch
- **Priority**: P0
- **Estimate**: XS
- **Dependencies**: None

**Description**:
Create and checkout the feature branch `235-multimodal-input` from develop.

**Acceptance Criteria**:
- [ ] Branch `235-multimodal-input` exists
- [ ] Branch is based on latest develop

**Implementation Notes**:
```bash
git checkout develop
git pull origin develop
git checkout -b 235-multimodal-input
```

---

## Phase 2: Foundation (Domain & Ports)

### Task 2.1: Add VideoValidationError Exception
- **Priority**: P1
- **Estimate**: S
- **Dependencies**: None
- **Story**: Supports US1, US3, US4

**Description**:
Create `VideoValidationError` exception class in the domain layer that extends `ConfigurationError`. This exception will be raised for video file validation failures.

**Acceptance Criteria**:
- [ ] `VideoValidationError` class exists in `src/gepa_adk/domain/exceptions.py`
- [ ] Extends `ConfigurationError`
- [ ] Has `video_path`, `field`, and `constraint` attributes
- [ ] Follows ADR-009 exception hierarchy pattern

**Test Criteria**:
- [ ] Unit test: Exception instantiation with all attributes
- [ ] Unit test: Exception inheritance chain
- [ ] Unit test: String representation includes video_path

**Implementation Notes**:
```python
class VideoValidationError(ConfigurationError):
    """Raised when video file validation fails."""

    def __init__(
        self,
        message: str,
        *,
        video_path: str,
        field: str = "video",
        constraint: str,
    ) -> None:
        super().__init__(message, field=field, value=video_path, constraint=constraint)
        self.video_path = video_path
```

---

### Task 2.2: Add VideoFileInfo Data Class
- **Priority**: P1
- **Estimate**: XS
- **Dependencies**: None
- **Story**: Supports US1, US3, US4

**Description**:
Create `VideoFileInfo` dataclass in the domain layer to hold validated video file metadata.

**Acceptance Criteria**:
- [ ] `VideoFileInfo` dataclass exists in `src/gepa_adk/domain/models.py`
- [ ] Has `path: str`, `size_bytes: int`, `mime_type: str` fields
- [ ] Frozen dataclass (immutable)

**Test Criteria**:
- [ ] Unit test: Dataclass instantiation
- [ ] Unit test: Immutability (frozen)

**Implementation Notes**:
```python
@dataclass(frozen=True)
class VideoFileInfo:
    """Metadata for a validated video file."""
    path: str
    size_bytes: int
    mime_type: str
```

---

### Task 2.3: Create VideoBlobServiceProtocol
- **Priority**: P1
- **Estimate**: S
- **Dependencies**: Task 2.1, Task 2.2
- **Story**: Supports US1, US3, US4

**Description**:
Define the `VideoBlobServiceProtocol` in the ports layer following ADR-002 (Protocol Interfaces).

**Acceptance Criteria**:
- [ ] Protocol exists in `src/gepa_adk/ports/video_blob_service.py`
- [ ] Has `@runtime_checkable` decorator
- [ ] Defines `async prepare_video_parts(video_paths: list[str]) -> list[Any]`
- [ ] Defines `validate_video_file(video_path: str) -> VideoFileInfo`
- [ ] Uses `list[Any]` return type (ADK types only in adapters)
- [ ] Proper docstrings per contract spec

**Test Criteria**:
- [ ] Contract test: Protocol is runtime checkable
- [ ] Contract test: Method signatures match contract

**Implementation Notes**:
```python
from typing import Protocol, Any, runtime_checkable
from gepa_adk.domain.models import VideoFileInfo

@runtime_checkable
class VideoBlobServiceProtocol(Protocol):
    """Protocol for loading video files as multimodal content parts."""

    async def prepare_video_parts(
        self,
        video_paths: list[str],
    ) -> list[Any]:
        """Load video files and create Part objects."""
        ...

    def validate_video_file(
        self,
        video_path: str,
    ) -> VideoFileInfo:
        """Validate a video file and return its metadata."""
        ...
```

---

## Phase 3: User Story 1 - Video + Text Evolution (P1)

> **Goal**: As an ML engineer, I can provide video file paths alongside text prompts in trainset examples so that GEPA can evolve agents for multimodal tasks like video transcription.

### Task 3.1: Implement VideoBlobService Adapter
- **Priority**: P1
- **Estimate**: M
- **Dependencies**: Task 2.3
- **Story**: US1

**Description**:
Implement `VideoBlobService` in the adapters layer that converts video files to ADK Part objects.

**Acceptance Criteria**:
- [ ] `VideoBlobService` class exists in `src/gepa_adk/adapters/video_blob_service.py`
- [ ] Implements `VideoBlobServiceProtocol`
- [ ] `prepare_video_parts()` reads files and returns `Part.from_bytes()` objects
- [ ] `validate_video_file()` checks existence, size (≤2GB), MIME type
- [ ] Uses `mimetypes.guess_type()` for MIME detection
- [ ] Raises `VideoValidationError` for validation failures
- [ ] Uses structlog for observability (ADR-008)
- [ ] MAX_VIDEO_SIZE_BYTES = 2 * 1024 * 1024 * 1024 (2GB)

**Test Criteria**:
- [ ] Contract test: Implements VideoBlobServiceProtocol
- [ ] Unit test: prepare_video_parts returns Part list
- [ ] Unit test: Order preservation with multiple videos
- [ ] Unit test: Empty list raises ValueError
- [ ] Unit test: File not found raises VideoValidationError
- [ ] Unit test: File >2GB raises VideoValidationError
- [ ] Unit test: Non-video MIME raises VideoValidationError
- [ ] Unit test: validate_video_file returns VideoFileInfo

**Implementation Notes**:
- Import `from google.genai.types import Part` (ADK types in adapters only)
- Use `aiofiles` or sync read in thread pool for async file I/O
- Log video loading with file size and MIME type

---

### Task 3.2: Extend _validate_dataset for videos Field
- **Priority**: P1
- **Estimate**: S
- **Dependencies**: None
- **Story**: US1, US2

**Description**:
Extend the `_validate_dataset` function in `api.py` to accept optional `videos` field in trainset/valset examples.

**Acceptance Criteria**:
- [ ] `_validate_dataset()` accepts examples with `input` OR `videos` (or both)
- [ ] `videos` field must be a non-empty list of strings
- [ ] Raises `ConfigurationError` if neither `input` nor `videos` present
- [ ] Raises `ConfigurationError` if `videos` is not a list
- [ ] Raises `ConfigurationError` if `videos` is empty list
- [ ] Raises `ConfigurationError` if videos item is not a string
- [ ] Error messages follow contract spec patterns

**Test Criteria**:
- [ ] Contract test: Input only (backward compatible)
- [ ] Contract test: Videos only
- [ ] Contract test: Input and videos together
- [ ] Contract test: Neither input nor videos raises error
- [ ] Contract test: Videos not a list raises error
- [ ] Contract test: Videos empty list raises error
- [ ] Contract test: Videos item not string raises error
- [ ] Contract test: Mixed examples (text-only + multimodal)

**Implementation Notes**:
File validation (existence, size, MIME) is NOT done here - deferred to execution time.

---

### Task 3.3: Extend AgentExecutor for Multimodal Content
- **Priority**: P1
- **Estimate**: M
- **Dependencies**: None
- **Story**: US1

**Description**:
Extend `AgentExecutor.execute_agent()` to accept optional `input_content: Content` parameter for multimodal inputs.

**Acceptance Criteria**:
- [ ] New `input_content: Content | None = None` keyword parameter added
- [ ] When `input_content` provided, use it instead of wrapping `input_text`
- [ ] When only `input_text` provided, wrap in `Content(parts=[Part(text=input_text)])`
- [ ] All existing overrides (instruction, schema, session_state) work with multimodal
- [ ] ExecutionResult structure unchanged
- [ ] Logging indicates multimodal vs text-only execution

**Test Criteria**:
- [ ] Contract test: Text only (backward compatible)
- [ ] Contract test: Multimodal content passed to agent
- [ ] Contract test: Content takes precedence over input_text
- [ ] Contract test: Empty text without content uses empty text part
- [ ] Contract test: All overrides work with multimodal
- [ ] Contract test: Result structure unchanged

**Implementation Notes**:
```python
def _build_content(
    self,
    input_text: str,
    input_content: Content | None = None,
) -> Content:
    if input_content is not None:
        return input_content
    return Content(role="user", parts=[Part(text=input_text)])
```

---

### Task 3.4: Extend ADKAdapter for Multimodal Content Assembly
- **Priority**: P1
- **Estimate**: M
- **Dependencies**: Task 3.1, Task 3.3
- **Story**: US1

**Description**:
Extend `ADKAdapter._run_single_example()` to assemble multimodal `Content` from examples containing `videos` field.

**Acceptance Criteria**:
- [ ] ADKAdapter accepts `VideoBlobServiceProtocol` dependency
- [ ] `_run_single_example()` checks for `videos` field in example
- [ ] When videos present, calls `video_service.prepare_video_parts()`
- [ ] Assembles `Content(parts=[text_part, *video_parts])`
- [ ] Passes assembled Content to executor via `input_content` parameter
- [ ] Text-only examples continue to use `input_text` parameter
- [ ] Proper error propagation for video validation failures

**Test Criteria**:
- [ ] Unit test: Text-only example uses input_text
- [ ] Unit test: Video example assembles Content correctly
- [ ] Unit test: Text + video example includes both parts
- [ ] Unit test: Multiple videos creates multiple parts
- [ ] Unit test: Video validation error propagates

**Implementation Notes**:
```python
async def _prepare_multimodal_content(
    self,
    example: dict[str, Any],
) -> Content | None:
    videos = example.get("videos")
    if not videos:
        return None

    parts = []
    if input_text := example.get("input"):
        parts.append(Part(text=input_text))

    video_parts = await self._video_service.prepare_video_parts(videos)
    parts.extend(video_parts)

    return Content(parts=parts, role="user")
```

---

### Task 3.5: Wire VideoBlobService Dependency
- **Priority**: P1
- **Estimate**: S
- **Dependencies**: Task 3.1, Task 3.4
- **Story**: US1

**Description**:
Wire `VideoBlobService` into the dependency chain so ADKAdapter receives it.

**Acceptance Criteria**:
- [ ] `VideoBlobService` instantiated in appropriate factory/composition root
- [ ] ADKAdapter constructor accepts optional `video_service: VideoBlobServiceProtocol`
- [ ] Default to `VideoBlobService()` if not provided
- [ ] Dependency injection follows existing patterns in codebase

**Test Criteria**:
- [ ] Integration test: Full evolution with video trainset

---

### Task 3.6: Export VideoValidationError from Public API
- **Priority**: P1
- **Estimate**: XS
- **Dependencies**: Task 2.1
- **Story**: US1

**Description**:
Export `VideoValidationError` from the public API for user error handling.

**Acceptance Criteria**:
- [ ] `VideoValidationError` exported from `gepa_adk.__init__`
- [ ] Documented in `__all__` list

**Test Criteria**:
- [ ] Unit test: Import from gepa_adk works

---

## Phase 4: User Story 2 - Backward Compatibility (P1)

> **Goal**: As a current GEPA user, my existing text-only trainsets must continue to work without any changes.

### Task 4.1: Verify Text-Only Trainset Compatibility
- **Priority**: P1
- **Estimate**: S
- **Dependencies**: Task 3.2, Task 3.4
- **Story**: US2

**Description**:
Ensure all existing text-only trainset patterns continue to work unchanged.

**Acceptance Criteria**:
- [ ] `{"input": "text"}` examples work unchanged
- [ ] `{"input": "text", "expected": "answer"}` examples work unchanged
- [ ] Mixed datasets (text-only + multimodal) work correctly
- [ ] No performance regression for text-only execution
- [ ] Existing test suite passes without modification

**Test Criteria**:
- [ ] Regression test: Run existing test suite
- [ ] Integration test: Text-only evolution end-to-end
- [ ] Integration test: Mixed text/multimodal dataset

---

## Phase 5: User Story 3 - Multiple Videos (P2)

> **Goal**: As an ML engineer, I can provide multiple video files per trainset example for comparison or multi-source analysis tasks.

### Task 5.1: Support Multiple Videos Per Example
- **Priority**: P2
- **Estimate**: S
- **Dependencies**: Task 3.4
- **Story**: US3

**Description**:
Verify and test that multiple videos per example are handled correctly.

**Acceptance Criteria**:
- [ ] `{"videos": ["/path1.mp4", "/path2.mp4"]}` creates multiple video parts
- [ ] Order of videos is preserved in Content parts
- [ ] Text + multiple videos works correctly
- [ ] Validation errors reference specific problematic video

**Test Criteria**:
- [ ] Unit test: Two videos creates two parts
- [ ] Unit test: Order preservation verified
- [ ] Unit test: Error identifies failing video path
- [ ] Integration test: Comparison task with two videos

---

## Phase 6: User Story 4 - Video-Only Input (P3)

> **Goal**: As an ML engineer, I can provide video-only trainset examples without text prompts for pure visual analysis tasks.

### Task 6.1: Support Video-Only Examples
- **Priority**: P3
- **Estimate**: S
- **Dependencies**: Task 3.2, Task 3.4
- **Story**: US4

**Description**:
Ensure video-only examples (no text input) work correctly.

**Acceptance Criteria**:
- [ ] `{"videos": ["/path.mp4"]}` (no input field) is valid
- [ ] Content contains only video parts
- [ ] Agent receives video-only Content
- [ ] Works with both single and multiple videos

**Test Criteria**:
- [ ] Unit test: Video-only Content assembly
- [ ] Integration test: Video-only evolution

---

## Phase 7: Testing & Quality

### Task 7.1: Contract Tests
- **Priority**: P1
- **Estimate**: M
- **Dependencies**: Task 3.1, Task 3.2, Task 3.3
- **Story**: All

**Description**:
Create contract tests for all new protocols and extended interfaces.

**Acceptance Criteria**:
- [ ] `tests/contracts/test_video_blob_contract.py` exists
- [ ] `tests/contracts/test_trainset_validation_contract.py` covers new cases
- [ ] `tests/contracts/test_agent_executor_multimodal_contract.py` exists
- [ ] All contract tests use `@pytest.mark.contract` marker

**Test Files**:
- `tests/contracts/test_video_blob_contract.py`
- `tests/contracts/test_trainset_validation_contract.py`
- `tests/contracts/test_agent_executor_multimodal_contract.py`

---

### Task 7.2: Unit Tests
- **Priority**: P1
- **Estimate**: M
- **Dependencies**: Task 3.1, Task 3.4
- **Story**: All

**Description**:
Create unit tests for VideoBlobService and ADKAdapter multimodal extensions.

**Acceptance Criteria**:
- [ ] `tests/unit/adapters/test_video_blob_service.py` exists
- [ ] `tests/unit/adapters/test_adk_adapter_multimodal.py` exists
- [ ] Tests use mocks for file I/O
- [ ] All unit tests use `@pytest.mark.unit` marker

**Test Files**:
- `tests/unit/adapters/test_video_blob_service.py`
- `tests/unit/adapters/test_adk_adapter_multimodal.py`

---

### Task 7.3: Integration Tests
- **Priority**: P1
- **Estimate**: M
- **Dependencies**: Task 3.5, Task 4.1
- **Story**: All

**Description**:
Create integration tests for end-to-end multimodal evolution.

**Acceptance Criteria**:
- [ ] `tests/integration/test_multimodal_evolution.py` exists
- [ ] Tests use real video files (small test fixtures)
- [ ] Covers happy path: video + text evolution
- [ ] Covers backward compatibility: text-only evolution
- [ ] Covers error handling: missing file, oversized file
- [ ] All integration tests use `@pytest.mark.integration` marker

**Test Files**:
- `tests/integration/test_multimodal_evolution.py`

**Test Fixtures Needed**:
- Small valid video file (MP4, ~100KB)
- Text file (for MIME type validation)

---

## Phase 8: Documentation & Polish

### Task 8.1: Update API Documentation
- **Priority**: P2
- **Estimate**: S
- **Dependencies**: Task 3.6
- **Story**: All

**Description**:
Update API reference documentation to include multimodal input support.

**Acceptance Criteria**:
- [ ] `evolve()` documentation mentions `videos` field
- [ ] `VideoValidationError` documented
- [ ] Supported video formats documented
- [ ] Size limits documented (2GB)

---

### Task 8.2: Add Multimodal Example to Guides
- **Priority**: P2
- **Estimate**: S
- **Dependencies**: Task 7.3
- **Story**: US1

**Description**:
Add multimodal evolution example to the guides documentation.

**Acceptance Criteria**:
- [ ] Video transcription example in guides
- [ ] Error handling example
- [ ] Links to quickstart.md content

---

### Task 8.3: Final Code Review & Cleanup
- **Priority**: P1
- **Estimate**: S
- **Dependencies**: All previous tasks

**Description**:
Final review ensuring code quality, documentation, and test coverage.

**Acceptance Criteria**:
- [ ] All tests pass
- [ ] No ruff/linting errors
- [ ] Type hints complete
- [ ] Docstrings for all public APIs
- [ ] No TODO comments left
- [ ] Hexagonal architecture rules verified (imports)

---

## Summary

| Phase | Tasks | Priority | Estimated Effort |
|-------|-------|----------|------------------|
| Phase 1: Setup | 1 | P0 | XS |
| Phase 2: Foundation | 3 | P1 | S |
| Phase 3: US1 Video+Text | 6 | P1 | M-L |
| Phase 4: US2 Backward Compat | 1 | P1 | S |
| Phase 5: US3 Multiple Videos | 1 | P2 | S |
| Phase 6: US4 Video-Only | 1 | P3 | S |
| Phase 7: Testing | 3 | P1 | M |
| Phase 8: Documentation | 3 | P1-P2 | S |

**Total Tasks**: 19
**Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 7 → Phase 8

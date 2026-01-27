# Research: Multimodal Input Support

**Feature**: 235-multimodal-input
**Date**: 2026-01-27
**Status**: Complete

## Overview

This document consolidates research findings for implementing multimodal input support (video blobs) in gepa-adk trainset/valset examples.

## Research Topics

### 1. Video Blob Loading Pattern

**Decision**: Follow agent-workflow-suite's VideoBlobService pattern

**Rationale**:
- Proven pattern already in use in related codebase
- Clean separation of concerns (service handles file I/O and blob creation)
- Built-in validation for file existence, size limits, and MIME types
- Optional caching support for evolution iterations

**Implementation Pattern**:
```python
from google.genai.types import Part

# Read video file bytes
with open(file_path, "rb") as f:
    video_bytes = f.read()

# Create Part object with inline data
part = Part.from_bytes(data=video_bytes, mime_type=mime_type)
```

**Alternatives Considered**:
- Direct inline loading in adapter: Rejected - violates single responsibility
- URL-based video references: Rejected - adds complexity, not needed for MVP

### 2. Content Assembly Pattern

**Decision**: Combine text and video parts into single Content object

**Rationale**:
- ADK's Content type natively supports multiple Parts
- Preserves input ordering (text prompt first, then video content)
- Simple assembly pattern used in agent-workflow-suite

**Implementation Pattern**:
```python
from google.genai.types import Content, Part

message_parts = []

# Add text part if provided
if input_text:
    message_parts.append(Part(text=input_text))

# Add video parts
if video_parts:
    message_parts.extend(video_parts)

# Assemble into Content
content = Content(parts=message_parts, role="user")
```

**Alternatives Considered**:
- Separate text and video requests: Rejected - loses multimodal context
- Custom wrapper type: Rejected - unnecessary complexity when Content works

### 3. AgentExecutor Signature Update

**Decision**: Accept `str | Content` for input parameter with backward compatibility

**Rationale**:
- Maintains backward compatibility with existing text-only callers
- Single entry point for all input types
- Minimal API surface change

**Implementation Pattern**:
```python
async def execute_agent(
    self,
    agent: Any,
    input_text: str,  # Keep existing parameter name for compatibility
    *,
    input_content: Content | None = None,  # New optional multimodal
    ...
) -> ExecutionResult:
    # Build content from either source
    if input_content:
        content = input_content
    else:
        content = Content(parts=[Part(text=input_text)], role="user")
```

**Alternatives Considered**:
- Replace input_text with union type: Rejected - breaks existing callers
- Add separate method: Rejected - duplicates logic unnecessarily

### 4. Dataset Validation Extension

**Decision**: Require at least one of `input` (text) or `videos` (paths) per example

**Rationale**:
- Maintains backward compatibility (input-only still works)
- Supports video-only examples for pure visual agents
- Clear validation error messages

**Implementation Pattern**:
```python
def _validate_dataset(dataset, name, *, allow_empty=False):
    for i, example in enumerate(dataset):
        has_input = bool(example.get("input"))
        has_videos = bool(example.get("videos"))

        if not has_input and not has_videos:
            raise ConfigurationError(
                f"{name}[{i}] must have 'input' or 'videos' field",
                field=f"{name}[{i}]",
                constraint="must contain 'input' or 'videos'",
            )
```

**Alternatives Considered**:
- Always require input text: Rejected - limits video-only use cases
- New validation function: Rejected - existing function is extensible

### 5. Exception Handling

**Decision**: Add VideoValidationError inheriting from ConfigurationError

**Rationale**:
- Follows existing exception hierarchy (ADR-009)
- ConfigurationError is appropriate for input validation failures
- Provides specific error context for video-related failures

**Implementation Pattern**:
```python
class VideoValidationError(ConfigurationError):
    """Raised when video file validation fails."""

    def __init__(
        self,
        message: str,
        *,
        video_path: str,
        field: str | None = None,
        constraint: str | None = None,
    ):
        super().__init__(
            message,
            field=field,
            value=video_path,
            constraint=constraint,
        )
        self.video_path = video_path
```

**Alternatives Considered**:
- Generic ConfigurationError: Rejected - loses video-specific context
- New base exception: Rejected - overcomplicates hierarchy

### 6. Port Interface Design

**Decision**: Create VideoBlobServiceProtocol in ports layer

**Rationale**:
- Follows hexagonal architecture (ADR-000)
- Enables testing with mock implementations
- Separates interface from google.genai.types dependency

**Implementation Pattern**:
```python
# ports/video_blob_service.py
from typing import Protocol, Any

class VideoBlobServiceProtocol(Protocol):
    """Protocol for video blob loading service."""

    async def prepare_video_parts(
        self,
        video_paths: list[str],
    ) -> list[Any]:  # Returns list[Part] but avoid import in ports
        """Load video files and return Part objects."""
        ...

    def validate_video_file(
        self,
        video_path: str,
    ) -> None:
        """Validate video file exists, size, and type."""
        ...
```

**Alternatives Considered**:
- No port interface: Rejected - violates hexagonal architecture
- Return bytes instead of Parts: Rejected - service should own Part creation

### 7. Memory Management

**Decision**: Load videos on-demand per example, no persistent caching in MVP

**Rationale**:
- Simple implementation for MVP
- Memory released after each example processes
- Caching can be added later as optimization

**Implementation Pattern**:
```python
async def prepare_video_parts(self, video_paths: list[str]) -> list[Part]:
    parts = []
    for path in video_paths:
        # Validate first (fast failure)
        self.validate_video_file(path)

        # Load bytes and create Part
        video_bytes = Path(path).read_bytes()
        mime_type = self._detect_mime_type(path)
        parts.append(Part.from_bytes(data=video_bytes, mime_type=mime_type))
    return parts
    # Parts go out of scope after use, memory freed by GC
```

**Alternatives Considered**:
- Pre-load all videos: Rejected - memory explosion risk
- LRU cache: Rejected - adds complexity, defer to future optimization

## ADK Types Reference

**Imports** (adapters layer only):
```python
from google.genai.types import Content, Part
```

**Creating Parts**:
```python
# Text part
Part(text="Hello")  # type: ignore[misc]

# Binary part from bytes
Part.from_bytes(data=video_bytes, mime_type="video/mp4")  # type: ignore[attr-defined]
```

**Creating Content**:
```python
Content(
    role="user",  # Required: "user", "model", "system"
    parts=[part1, part2, ...]  # List of Part objects
)
```

**Type Ignores**: Required due to ADK's dynamic typing; use `# type: ignore[misc]` or `# type: ignore[attr-defined]`

## Validation Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Max video file size | 2GB | Gemini API limit |
| Supported MIME types | video/* | Gemini multimodal support |
| Max videos per example | 5 (recommended) | Memory considerations |
| Max video size recommended | 500MB | Performance/memory balance |

## File Structure Summary

| File | Action | Purpose |
|------|--------|---------|
| `ports/video_blob_service.py` | CREATE | Protocol interface |
| `adapters/video_blob_service.py` | CREATE | Service implementation |
| `adapters/adk_adapter.py` | MODIFY | Content preparation |
| `adapters/agent_executor.py` | MODIFY | Accept multimodal input |
| `domain/exceptions.py` | MODIFY | Add VideoValidationError |
| `api.py` | MODIFY | Extend dataset validation |

## Open Questions (Resolved)

1. ~~Should videos be cached across iterations?~~ → No, defer to future optimization
2. ~~Should we support image files too?~~ → Out of scope per spec
3. ~~How to handle duplicate video paths?~~ → Process each reference (let user dedupe)

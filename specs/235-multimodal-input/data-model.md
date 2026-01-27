# Data Model: Multimodal Input Support

**Feature**: 235-multimodal-input
**Date**: 2026-01-27
**Status**: Complete

## Overview

This document defines the data structures and relationships for multimodal input support in gepa-adk trainset/valset examples.

## Entities

### 1. Trainset Example (Extended)

**Purpose**: Dictionary containing input data for a single evolution example.

**Current Structure** (unchanged):
```python
{
    "input": str,           # Required: Text prompt for agent
    "expected": str | None  # Optional: Reference output for scoring
}
```

**Extended Structure**:
```python
{
    "input": str | None,           # Optional when videos present
    "videos": list[str] | None,    # Optional: List of video file paths
    "expected": str | None         # Optional: Reference output for scoring
}
```

**Validation Rules**:
- At least one of `input` or `videos` must be present
- If `videos` present, must be a non-empty list of strings
- Each video path must be valid filesystem path
- `input` can be empty string if `videos` is present
- `expected` remains optional regardless of input type

**State Transitions**: N/A (immutable input structure)

### 2. Video File Metadata

**Purpose**: Internal representation of validated video file information.

**Structure**:
```python
@dataclass
class VideoFileInfo:
    """Validated video file metadata."""

    path: str          # Absolute file path
    size_bytes: int    # File size in bytes
    mime_type: str     # MIME type (e.g., "video/mp4")
```

**Validation Rules**:
- `path` must exist and be readable
- `size_bytes` must be <= 2GB (2,147,483,648 bytes)
- `mime_type` must start with "video/"

**Note**: This is an internal data structure, not persisted. Used for validation and logging.

### 3. Multimodal Content Parts

**Purpose**: Represents the assembled multimodal message for agent execution.

**Structure** (ADK types):
```python
from google.genai.types import Content, Part

# Text part
Part(text="transcribe this lecture")

# Video part (binary blob)
Part.from_bytes(data=video_bytes, mime_type="video/mp4")

# Combined content
Content(
    role="user",
    parts=[
        Part(text="transcribe this lecture"),
        Part.from_bytes(data=video1_bytes, mime_type="video/mp4"),
        Part.from_bytes(data=video2_bytes, mime_type="video/mp4"),
    ]
)
```

**Assembly Order**:
1. Text part first (if present)
2. Video parts in order provided

## Relationships

```
Trainset
├── Example 1
│   ├── input: str (text prompt)
│   ├── videos: [path1, path2] → VideoFileInfo[] → Part[]
│   └── expected: str (reference)
├── Example 2
│   ├── input: str
│   └── expected: str
└── Example 3
    └── videos: [path3] → VideoFileInfo → Part
              ↓
        Content(parts=[Part(text), Part(video1), Part(video2)])
              ↓
        AgentExecutor.execute_agent(input_content=content)
```

## Exception Types

### VideoValidationError

**Purpose**: Raised when video file validation fails.

**Inheritance**: `ConfigurationError` → `EvolutionError`

**Attributes**:
```python
class VideoValidationError(ConfigurationError):
    video_path: str      # Path that failed validation
    field: str | None    # Field name (e.g., "trainset[0].videos[0]")
    value: object        # The invalid value
    constraint: str      # What constraint was violated
```

**Use Cases**:
- File not found: `VideoValidationError("Video file not found", video_path=path, constraint="file must exist")`
- File too large: `VideoValidationError("Video exceeds 2GB limit", video_path=path, constraint="size <= 2GB")`
- Invalid type: `VideoValidationError("Not a video file", video_path=path, constraint="must be video/* MIME type")`

## Protocol Interface

### VideoBlobServiceProtocol

**Purpose**: Port interface for video blob loading service.

**Location**: `src/gepa_adk/ports/video_blob_service.py`

```python
from typing import Protocol, Any, runtime_checkable

@runtime_checkable
class VideoBlobServiceProtocol(Protocol):
    """Protocol for loading video files as multimodal content parts.

    Implementations handle:
    - File existence and permission validation
    - File size validation (<=2GB)
    - MIME type validation (video/*)
    - Binary data loading and Part creation
    """

    async def prepare_video_parts(
        self,
        video_paths: list[str],
    ) -> list[Any]:
        """Load video files and create Part objects.

        Args:
            video_paths: List of filesystem paths to video files.

        Returns:
            List of Part objects with inline video data.

        Raises:
            VideoValidationError: If any video fails validation.
            OSError: If file read fails.
        """
        ...

    def validate_video_file(
        self,
        video_path: str,
    ) -> VideoFileInfo:
        """Validate a video file and return its metadata.

        Args:
            video_path: Filesystem path to video file.

        Returns:
            VideoFileInfo with validated metadata.

        Raises:
            VideoValidationError: If validation fails.
        """
        ...
```

## Trainset Schema (JSON Schema representation)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TrainsetExample",
  "type": "object",
  "properties": {
    "input": {
      "type": "string",
      "description": "Text prompt for the agent"
    },
    "videos": {
      "type": "array",
      "items": {
        "type": "string",
        "description": "Filesystem path to video file"
      },
      "minItems": 1,
      "description": "List of video file paths"
    },
    "expected": {
      "type": "string",
      "description": "Reference output for scoring comparison"
    }
  },
  "anyOf": [
    {"required": ["input"]},
    {"required": ["videos"]}
  ],
  "additionalProperties": true
}
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Code                               │
│  trainset = [{"input": "...", "videos": ["path1", "path2"]}]   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    api.py: _validate_dataset()                   │
│  - Validates structure                                          │
│  - Ensures input OR videos present                              │
│  - Optionally validates video paths exist                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ADKAdapter._run_single_example()                 │
│  - Extracts input text                                          │
│  - Extracts video paths                                         │
│  - Calls VideoBlobService if videos present                     │
│  - Assembles Content(parts=[text_part, *video_parts])          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      VideoBlobService                            │
│  - validate_video_file() for each path                          │
│  - Read bytes from disk                                         │
│  - Part.from_bytes(data, mime_type)                            │
│  - Returns list[Part]                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  AgentExecutor.execute_agent()                   │
│  - Accepts input_content: Content                               │
│  - Passes to runner.run_async()                                 │
│  - Returns ExecutionResult                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Migration Notes

**Backward Compatibility**:
- Existing trainsets with only `input` field continue to work unchanged
- No migration required for existing code
- New `videos` field is purely additive

**Breaking Changes**: None

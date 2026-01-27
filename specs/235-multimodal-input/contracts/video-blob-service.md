# Contract: VideoBlobServiceProtocol

**Feature**: 235-multimodal-input
**Date**: 2026-01-27
**Type**: Port Protocol

## Overview

Defines the contract for video blob loading services that convert video files to multimodal content parts.

## Protocol Definition

```python
from typing import Protocol, Any, runtime_checkable

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
    ) -> "VideoFileInfo":
        """Validate a video file and return its metadata."""
        ...
```

## Method Contracts

### prepare_video_parts

**Signature**:
```python
async def prepare_video_parts(
    self,
    video_paths: list[str],
) -> list[Any]:
```

**Preconditions**:
- `video_paths` is a non-empty list
- All paths are strings (not Path objects)

**Postconditions**:
- Returns list of Part objects, one per input path
- Return list length equals input list length
- Order is preserved (output[i] corresponds to input[i])
- Each Part contains inline video data

**Error Conditions**:
| Condition | Exception | Message Pattern |
|-----------|-----------|-----------------|
| Empty list | `ValueError` | "video_paths cannot be empty" |
| File not found | `VideoValidationError` | "Video file not found: {path}" |
| File too large | `VideoValidationError` | "Video exceeds 2GB limit: {size} bytes" |
| Invalid MIME type | `VideoValidationError` | "Not a video file: {mime_type}" |
| Permission denied | `PermissionError` | OS-level message |
| Read error | `OSError` | OS-level message |

### validate_video_file

**Signature**:
```python
def validate_video_file(
    self,
    video_path: str,
) -> VideoFileInfo:
```

**Preconditions**:
- `video_path` is a non-empty string

**Postconditions**:
- Returns VideoFileInfo with path, size_bytes, mime_type
- File exists and is readable (validated)
- Size is within limits (validated)
- MIME type is video/* (validated)

**Error Conditions**:
| Condition | Exception | Constraint |
|-----------|-----------|------------|
| File not found | `VideoValidationError` | "file must exist" |
| File >2GB | `VideoValidationError` | "size <= 2GB" |
| Non-video MIME | `VideoValidationError` | "must be video/* MIME type" |

## Test Cases

### Contract Test: Protocol Compliance

```python
def test_video_blob_service_implements_protocol():
    """Service must implement VideoBlobServiceProtocol."""
    service = VideoBlobService()
    assert isinstance(service, VideoBlobServiceProtocol)
```

### Contract Test: prepare_video_parts Returns Parts

```python
@pytest.mark.asyncio
async def test_prepare_video_parts_returns_part_list(video_service, temp_video_file):
    """prepare_video_parts must return list of Part objects."""
    parts = await video_service.prepare_video_parts([temp_video_file])

    assert isinstance(parts, list)
    assert len(parts) == 1
    # Part type check (ADK-specific)
    assert hasattr(parts[0], "inline_data") or hasattr(parts[0], "text")
```

### Contract Test: Order Preservation

```python
@pytest.mark.asyncio
async def test_prepare_video_parts_preserves_order(video_service, temp_video_files):
    """Output order must match input order."""
    paths = temp_video_files  # [path1, path2, path3]
    parts = await video_service.prepare_video_parts(paths)

    assert len(parts) == len(paths)
    # Order verification via metadata or known content
```

### Contract Test: Empty List Rejection

```python
@pytest.mark.asyncio
async def test_prepare_video_parts_rejects_empty_list(video_service):
    """Empty video_paths must raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        await video_service.prepare_video_parts([])
```

### Contract Test: File Not Found

```python
@pytest.mark.asyncio
async def test_prepare_video_parts_file_not_found(video_service):
    """Missing file must raise VideoValidationError."""
    with pytest.raises(VideoValidationError) as exc_info:
        await video_service.prepare_video_parts(["/nonexistent/video.mp4"])

    assert "not found" in str(exc_info.value).lower()
    assert exc_info.value.video_path == "/nonexistent/video.mp4"
```

### Contract Test: File Size Limit

```python
@pytest.mark.asyncio
async def test_prepare_video_parts_size_limit(video_service, oversized_video_mock):
    """Files >2GB must raise VideoValidationError."""
    with pytest.raises(VideoValidationError) as exc_info:
        await video_service.prepare_video_parts([oversized_video_mock])

    assert "2GB" in str(exc_info.value)
    assert exc_info.value.constraint == "size <= 2GB"
```

### Contract Test: MIME Type Validation

```python
@pytest.mark.asyncio
async def test_prepare_video_parts_mime_type(video_service, text_file):
    """Non-video files must raise VideoValidationError."""
    with pytest.raises(VideoValidationError) as exc_info:
        await video_service.prepare_video_parts([text_file])

    assert "video" in str(exc_info.value).lower()
```

### Contract Test: validate_video_file Returns Metadata

```python
def test_validate_video_file_returns_info(video_service, temp_video_file):
    """validate_video_file must return VideoFileInfo."""
    info = video_service.validate_video_file(temp_video_file)

    assert info.path == temp_video_file
    assert info.size_bytes > 0
    assert info.mime_type.startswith("video/")
```

## Implementation Notes

- Protocol uses `list[Any]` return type to avoid importing ADK types in ports layer
- Implementations import and return `google.genai.types.Part` objects
- Runtime checkable for isinstance() verification in dependency injection
- Sync `validate_video_file` allows fast pre-validation without async context

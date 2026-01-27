# Contract: Trainset Validation Extension

**Feature**: 235-multimodal-input
**Date**: 2026-01-27
**Type**: API Contract

## Overview

Extends the existing `_validate_dataset` function to support optional `videos` field while maintaining backward compatibility.

## Current Contract (Unchanged)

```python
def _validate_dataset(
    dataset: list[dict[str, Any]],
    name: str,
    *,
    allow_empty: bool = False,
    required_keys: set[str] | None = None,
) -> None:
```

**Current Behavior**:
- Requires `input` key by default
- Raises `ConfigurationError` for missing keys

## Extended Contract

### New Validation Rules

| Condition | Current Behavior | New Behavior |
|-----------|------------------|--------------|
| `input` only | VALID | VALID (unchanged) |
| `videos` only | INVALID | VALID (new) |
| `input` + `videos` | N/A | VALID (new) |
| Neither | INVALID | INVALID (unchanged) |

### videos Field Contract

**Type**: `list[str]` (list of file paths)

**Validation Rules**:
1. If present, must be a list
2. If present, must be non-empty
3. Each item must be a string
4. File existence validation is deferred to execution (not in _validate_dataset)

### Error Messages

| Condition | Error Message |
|-----------|---------------|
| Neither input nor videos | `"{name}[{i}] must have 'input' or 'videos' field"` |
| videos is not a list | `"{name}[{i}].videos must be a list"` |
| videos is empty list | `"{name}[{i}].videos cannot be empty"` |
| videos item not string | `"{name}[{i}].videos[{j}] must be a string"` |

## Test Cases

### Contract Test: Input Only (Backward Compatible)

```python
def test_validate_dataset_input_only():
    """Text-only examples must remain valid."""
    dataset = [{"input": "What is 2+2?"}]
    _validate_dataset(dataset, "trainset")  # Should not raise
```

### Contract Test: Videos Only

```python
def test_validate_dataset_videos_only():
    """Video-only examples must be valid."""
    dataset = [{"videos": ["/path/to/video.mp4"]}]
    _validate_dataset(dataset, "trainset")  # Should not raise
```

### Contract Test: Input and Videos Together

```python
def test_validate_dataset_input_and_videos():
    """Examples with both input and videos must be valid."""
    dataset = [
        {
            "input": "transcribe this",
            "videos": ["/path/to/video.mp4"]
        }
    ]
    _validate_dataset(dataset, "trainset")  # Should not raise
```

### Contract Test: Neither Input Nor Videos

```python
def test_validate_dataset_neither_input_nor_videos():
    """Examples with neither must raise ConfigurationError."""
    dataset = [{"expected": "something"}]

    with pytest.raises(ConfigurationError) as exc_info:
        _validate_dataset(dataset, "trainset")

    assert "input" in str(exc_info.value)
    assert "videos" in str(exc_info.value)
```

### Contract Test: Videos Not a List

```python
def test_validate_dataset_videos_not_list():
    """videos field must be a list."""
    dataset = [{"videos": "/path/to/video.mp4"}]  # String, not list

    with pytest.raises(ConfigurationError) as exc_info:
        _validate_dataset(dataset, "trainset")

    assert "must be a list" in str(exc_info.value)
```

### Contract Test: Videos Empty List

```python
def test_validate_dataset_videos_empty():
    """videos field cannot be empty list."""
    dataset = [{"videos": []}]

    with pytest.raises(ConfigurationError) as exc_info:
        _validate_dataset(dataset, "trainset")

    assert "cannot be empty" in str(exc_info.value)
```

### Contract Test: Videos Item Not String

```python
def test_validate_dataset_videos_item_not_string():
    """Each video path must be a string."""
    dataset = [{"videos": [123]}]  # Integer, not string

    with pytest.raises(ConfigurationError) as exc_info:
        _validate_dataset(dataset, "trainset")

    assert "must be a string" in str(exc_info.value)
```

### Contract Test: Multiple Examples Mixed

```python
def test_validate_dataset_mixed_examples():
    """Dataset can contain mix of text-only and multimodal examples."""
    dataset = [
        {"input": "text only"},
        {"videos": ["/path/to/video.mp4"]},
        {"input": "with video", "videos": ["/path/to/video2.mp4"]},
    ]
    _validate_dataset(dataset, "trainset")  # Should not raise
```

### Contract Test: Expected Field Still Optional

```python
def test_validate_dataset_expected_optional():
    """expected field remains optional for all example types."""
    dataset = [
        {"input": "text only"},
        {"input": "with expected", "expected": "answer"},
        {"videos": ["/path/to/video.mp4"]},
        {"videos": ["/path/to/video.mp4"], "expected": "transcript"},
    ]
    _validate_dataset(dataset, "trainset")  # Should not raise
```

## Implementation Notes

- Validation of video file existence is NOT done in `_validate_dataset`
- File validation happens at execution time in VideoBlobService
- This separation allows fast structural validation during API call
- Deferred file validation provides better error context (during which example)

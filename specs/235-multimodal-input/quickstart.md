# Quickstart: Multimodal Input Support

**Feature**: 235-multimodal-input
**Date**: 2026-01-27

## Overview

This guide shows how to use video files in trainset/valset examples for evolving multimodal agents.

## Basic Usage

### Video + Text Input

Evolve an agent using video files with companion text prompts:

```python
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from gepa_adk import evolve


class TranscriptOutput(BaseModel):
    """Agent output schema for transcription."""

    transcript: str = Field(description="Video transcript text")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")


# Create agent with multimodal model
agent = LlmAgent(
    name="transcriber",
    model="gemini-2.0-flash-exp",  # Multimodal-capable model
    instruction="You are a video transcription agent. Produce accurate transcripts.",
    output_schema=TranscriptOutput,
)

# Trainset with video files
trainset = [
    {
        "input": "Transcribe the speech in this video",
        "videos": ["/data/lecture1.mp4"],
    },
    {
        "input": "Create a transcript of this meeting recording",
        "videos": ["/data/meeting2.mp4"],
    },
    {
        "input": "Transcribe the dialogue in this video",
        "videos": ["/data/interview3.mp4"],
    },
]

# Evolve the agent's instruction for better transcription
result = await evolve(agent, trainset)

print(f"Original score: {result.original_score:.3f}")
print(f"Final score: {result.final_score:.3f}")
print(f"Evolved instruction:\n{result.evolved_components['instruction']}")
```

### Video-Only Input

For pure visual analysis without text prompts:

```python
trainset = [
    {"videos": ["/data/video1.mp4"]},
    {"videos": ["/data/video2.mp4"]},
]

result = await evolve(agent, trainset)
```

### Multiple Videos Per Example

For comparison or multi-source analysis:

```python
trainset = [
    {
        "input": "Compare the content of these two videos",
        "videos": ["/data/before.mp4", "/data/after.mp4"],
    },
]

result = await evolve(agent, trainset)
```

## With Critic Agent

Add a critic for quality scoring:

```python
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from gepa_adk import evolve


class CriticOutput(BaseModel):
    """Critic scoring schema."""

    score: float = Field(ge=0.0, le=1.0)
    feedback: str


critic = LlmAgent(
    name="transcript_critic",
    model="gemini-2.0-flash-exp",
    instruction="Evaluate transcript quality for accuracy and completeness.",
    output_schema=CriticOutput,
)

trainset = [
    {
        "input": "Transcribe this lecture",
        "videos": ["/data/lecture.mp4"],
        "expected": "Expected transcript text for reference...",
    },
]

result = await evolve(agent, trainset, critic=critic)
```

## Backward Compatibility

Text-only trainsets continue to work exactly as before:

```python
# This still works unchanged
trainset = [
    {"input": "What is 2+2?", "expected": "4"},
    {"input": "What is the capital of France?", "expected": "Paris"},
]

result = await evolve(agent, trainset)
```

## Error Handling

### Missing Video File

```python
trainset = [{"videos": ["/nonexistent/video.mp4"]}]

try:
    result = await evolve(agent, trainset)
except VideoValidationError as e:
    print(f"Video error: {e}")
    print(f"Problem file: {e.video_path}")
```

### File Too Large

```python
# Files over 2GB will raise VideoValidationError
trainset = [{"videos": ["/data/huge_video.mp4"]}]  # 3GB file

try:
    result = await evolve(agent, trainset)
except VideoValidationError as e:
    print(f"Video exceeds size limit: {e}")
```

### Invalid File Type

```python
# Non-video files will raise VideoValidationError
trainset = [{"videos": ["/data/document.pdf"]}]

try:
    result = await evolve(agent, trainset)
except VideoValidationError as e:
    print(f"Not a video file: {e}")
```

## Supported Video Formats

Any format supported by the underlying model provider:
- MP4 (recommended)
- MOV
- AVI
- WEBM
- MKV

**Size Limits**:
- Maximum: 2GB per file (Gemini API constraint)
- Recommended: Under 500MB for optimal performance

## Synchronous Wrapper

For scripts and notebooks:

```python
from gepa_adk import evolve_sync

trainset = [
    {"input": "Transcribe this", "videos": ["/data/video.mp4"]},
]

result = evolve_sync(agent, trainset)
```

## Next Steps

- See [Multi-Agent Guide](../../docs/guides/multi-agent.md) for workflow evolution with videos
- See [Critic Agents Guide](../../docs/guides/critic-agents.md) for custom scoring
- See [API Reference](../../docs/reference/index.md) for full parameter documentation

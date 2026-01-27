"""Example: Multimodal video transcription evolution.

This example demonstrates evolving a video transcription agent using trainset
examples with video files. The agent learns to produce accurate transcripts
from video content through evolutionary optimization.

The multimodal input support allows trainset examples to include:
- Text-only input (backward compatible)
- Video files with optional text prompts
- Multiple videos per example for comparison tasks

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - GOOGLE_API_KEY environment variable set (for Gemini)
    - Video files in supported formats (MP4, MOV, AVI, WEBM, MKV)

Usage:
    python examples/video_transcription_evolution.py

Note:
    This example requires actual video files to run. Update the video paths
    in create_trainset() to point to your local video files. Videos must be
    under 2GB per the Gemini API limit.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, EvolutionResult, VideoValidationError, evolve
from gepa_adk.utils import EncodingSafeProcessor

# -----------------------------------------------------------------------------
# Console Output Encoding
# -----------------------------------------------------------------------------
_encoding_processor = EncodingSafeProcessor()


def safe_print(text: str) -> None:
    """Print text safely on Windows consoles with cp1252 encoding.

    Args:
        text: Text to print, may contain Unicode characters.
    """
    print(_encoding_processor.sanitize_string(text))


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        EncodingSafeProcessor(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class TranscriptOutput(BaseModel):
    """Structured output for video transcription.

    This schema defines the expected output format for the transcription agent.

    Attributes:
        transcript: The transcribed text from the video.
        confidence: Confidence score for the transcription quality.
    """

    transcript: str = Field(description="Transcribed text from the video")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for transcription accuracy",
    )


class CriticOutput(BaseModel):
    """Structured output for critic evaluation.

    Attributes:
        score: Quality score (0.0-1.0).
        feedback: Evaluation feedback explaining the score.
    """

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality assessment score",
    )
    feedback: str = Field(description="Detailed feedback on transcription quality")


def create_agent() -> LlmAgent:
    """Create the video transcription agent to be evolved.

    Returns:
        LlmAgent configured for video transcription with Gemini model.
    """
    return LlmAgent(
        name="transcriber",
        model="gemini-2.0-flash-exp",  # Multimodal-capable model
        instruction="Transcribe the speech and dialogue from the video accurately.",
        output_schema=TranscriptOutput,
    )


def create_critic() -> LlmAgent:
    """Create a critic agent for scoring transcription quality.

    Returns:
        LlmAgent configured as a critic for evaluating transcriptions.
    """
    return LlmAgent(
        name="transcript_critic",
        model="gemini-2.0-flash-exp",
        instruction="""Evaluate the transcription quality. Consider:
- Accuracy: Does the transcript match the spoken content?
- Completeness: Are all speakers and dialogue captured?
- Formatting: Is the transcript well-formatted and readable?
- Speaker identification: Are different speakers distinguished?
Provide a score from 0.0 to 1.0 where 1.0 is a perfect transcription.""",
        output_schema=CriticOutput,
    )


def create_trainset() -> list[dict[str, Any]]:
    """Create training examples with video files.

    Update the video paths to point to actual video files on your system.
    Supported formats: MP4, MOV, AVI, WEBM, MKV (under 2GB each).

    Returns:
        List of training examples with video paths and optional prompts.
    """
    # NOTE: Update these paths to point to your actual video files
    return [
        # Video with text prompt
        {
            "input": "Transcribe the main speech in this video",
            "videos": ["/path/to/lecture.mp4"],
        },
        # Video with expected output for reference
        {
            "input": "Create a transcript of this meeting recording",
            "videos": ["/path/to/meeting.mp4"],
            "expected": "Expected transcript text for scoring...",
        },
        # Video-only example (no text prompt needed)
        {
            "videos": ["/path/to/interview.mp4"],
        },
    ]


def create_comparison_trainset() -> list[dict[str, Any]]:
    """Create training examples with multiple videos for comparison tasks.

    This demonstrates using multiple videos per example for tasks like
    comparing content across videos or analyzing video pairs.

    Returns:
        List of examples with multiple videos each.
    """
    return [
        {
            "input": "Compare the speaking styles in these two videos",
            "videos": ["/path/to/speaker1.mp4", "/path/to/speaker2.mp4"],
        },
        {
            "input": "Identify common topics discussed in both videos",
            "videos": ["/path/to/video_a.mp4", "/path/to/video_b.mp4"],
        },
    ]


async def run_evolution(
    agent: LlmAgent, critic: LlmAgent, trainset: list[dict[str, Any]]
) -> EvolutionResult:
    """Run evolutionary optimization on the transcription agent.

    Args:
        agent: The transcription agent to evolve.
        critic: The critic agent for scoring.
        trainset: Training examples with video files.

    Returns:
        EvolutionResult containing the evolved instruction and metrics.

    Raises:
        VideoValidationError: If any video file is invalid (not found, too large,
            or not a video file).
    """
    config = EvolutionConfig(
        max_iterations=3,
        patience=2,
    )

    logger.info(
        "evolution.starting",
        agent_name=agent.name,
        trainset_size=len(trainset),
        max_iterations=config.max_iterations,
    )

    try:
        result = await evolve(agent, trainset, critic=critic, config=config)

        logger.info(
            "evolution.complete",
            original_score=result.original_score,
            final_score=result.final_score,
            improvement=result.improvement,
            total_iterations=result.total_iterations,
        )

        return result

    except VideoValidationError as e:
        logger.error(
            "evolution.video_error",
            video_path=e.video_path,
            constraint=e.constraint,
            error=str(e),
        )
        raise


async def main() -> None:
    """Run the video transcription evolution example."""
    # Check for Google API key
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY environment variable required")

    logger.info("example.video_transcription.start")

    try:
        # Create agent, critic, and training data
        agent = create_agent()
        critic = create_critic()
        trainset = create_trainset()

        # Run evolution with critic scoring
        result = await run_evolution(agent, critic, trainset)

        # Display results
        print("\n" + "=" * 60)
        print("VIDEO TRANSCRIPTION EVOLUTION RESULTS")
        print("=" * 60)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score: {result.final_score:.3f}")
        print(f"Improvement: {result.improvement:.2%}")
        print(f"Iterations: {result.total_iterations}")
        print("\n" + "-" * 60)
        print("EVOLVED TRANSCRIPTION INSTRUCTION:")
        print("-" * 60)
        safe_print(result.evolved_components["instruction"])
        print("=" * 60)

        logger.info("example.video_transcription.success")

    except VideoValidationError as e:
        print(f"\nVideo validation error: {e}")
        print(f"Problem file: {e.video_path}")
        print(f"Constraint: {e.constraint}")
        print("\nPlease update the video paths in create_trainset() to point to")
        print("actual video files on your system.")
        logger.error("example.video_transcription.video_error", error=str(e))

    except Exception as e:
        logger.error("example.video_transcription.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

"""Example: Multimodal video description evolution with database persistence.

This example demonstrates evolving a video description agent using trainset
examples with video files. The agent learns to produce vivid, detailed
descriptions of video content through evolutionary optimization.

A literary-style critic (inspired by Victorian sensibilities) evaluates
the descriptions, rewarding vivid imagery, narrative flow, and attention
to detail - demonstrating how GEPA can optimize for subjective qualities.

Features demonstrated:
- Multimodal input support (video files + text prompts)
- DatabaseSessionService for SQLite persistence
- App/Runner pattern for ADK integration
- Post-run database exploration for debugging

The multimodal input support allows trainset examples to include:
- Text-only input (backward compatible)
- Video files with optional text prompts
- Multiple videos per example for comparison tasks

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - Google Cloud authentication configured:
        - GOOGLE_GENAI_USE_VERTEXAI=TRUE
        - GOOGLE_CLOUD_PROJECT=your-project-id
        - GOOGLE_CLOUD_LOCATION=us-central1 (optional)
    - Video files in examples/data/videos/ (see README.md there)

Usage:
    python examples/video_transcription_evolution.py

After running, explore the ADK database:
    sqlite3 data/video_evolution_sessions.db "SELECT * FROM sessions;"
    sqlite3 data/video_evolution_sessions.db "SELECT * FROM events LIMIT 20;"

Note:
    Place sample1.mp4 and sample2.mp4 in examples/data/videos/.
    Videos must be under 2GB per the Gemini API limit.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
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


class VideoDescription(BaseModel):
    """Structured output for video description.

    This schema defines the expected output format for the video description agent.

    Attributes:
        description: A detailed description of what happens in the video.
        key_moments: Notable moments or events observed.
    """

    description: str = Field(description="Detailed description of the video content")
    key_moments: list[str] = Field(
        description="List of notable moments or events in the video"
    )


class CriticOutput(BaseModel):
    """Structured output for critic evaluation.

    Attributes:
        score: Quality score (0.0-1.0).
        feedback: Evaluation feedback in a literary critic's voice.
    """

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality assessment score",
    )
    feedback: str = Field(
        description="Thoughtful critique of the description's quality and completeness"
    )


def create_agent() -> LlmAgent:
    """Create the video description agent to be evolved.

    Returns:
        LlmAgent configured for video description with Gemini model.
    """
    return LlmAgent(
        name="video_describer",
        model="gemini-2.5-flash",  # Multimodal-capable model
        instruction=(
            "Describe what happens in the video. "
            "Note the key events, actions, and any notable details you observe."
        ),
        output_schema=VideoDescription,
    )


def create_critic() -> LlmAgent:
    """Create a critic agent for scoring video descriptions.

    The critic evaluates descriptions as Charles Dickens himself might -
    demanding ornate Victorian prose, thematic depth, and moral resonance
    even in the simplest of scenes.

    Returns:
        LlmAgent configured as a harsh Dickensian critic.
    """
    return LlmAgent(
        name="dickensian_critic",
        model="gemini-2.5-flash",
        instruction="""You are a harsh literary critic in the tradition of Victorian England,
evaluating prose as Charles Dickens himself might judge it. You are EXACTING and UNFORGIVING.

PROSE STYLE (most important - penalize heavily if missing):
- Demand ORNATE, ELABORATE sentences with subordinate clauses and rhetorical flourishes
- Expect period-appropriate vocabulary: "countenance" not "face", "forthwith" not "then"
- Require emotional embellishment and dramatic flair in every passage
- Plain, modern, utilitarian prose deserves scores below 0.5 - it is LAZY writing

DICKENSIAN THEMES (the scene MUST evoke these, however tangentially):
- The struggle between nature and industry, innocence and corruption
- Social commentary - what does this scene say about the human condition?
- Redemption and hope amid hardship - find the moral lesson
- The dignity of the overlooked - even moss and bark have stories of perseverance
- Sentimentality and pathos - the reader should FEEL something profound

STRUCTURAL DEMANDS:
- Opening should hook like the first line of a great novel
- Build toward emotional crescendo, not mere catalog of observations
- Close with reflection or moral insight, not abrupt ending

A score of 0.7 is GENEROUS for competent but uninspired work.
A score above 0.8 requires genuinely Victorian prose with thematic depth.
A score of 1.0 is reserved for prose Dickens himself would publish.

Be withering in your criticism. Mediocrity deserves no quarter.""",
        output_schema=CriticOutput,
    )


def get_examples_dir() -> Path:
    """Get the examples directory path.

    Returns:
        Path to the examples directory.
    """
    return Path(__file__).parent


def create_trainset() -> list[dict[str, Any]]:
    """Create training examples with video files.

    Videos should be placed in examples/data/videos/ directory.
    See examples/data/videos/README.md for setup instructions.

    Supported formats: MP4, MOV, AVI, WEBM, MKV (under 2GB each).

    Note:
        This example uses minimal trainset size to limit API calls.
        For production, use more diverse examples (5-10 recommended).

    Returns:
        List of training examples with video paths and optional prompts.
    """
    videos_dir = get_examples_dir() / "data" / "videos"

    # Using minimal examples to limit API calls for demo
    return [
        # Video with descriptive prompt
        {
            "input": "Describe what happens in this video in vivid detail",
            "videos": [str(videos_dir / "sample1.mp4")],
        },
        # Second video sample
        {
            "input": "Provide a rich description of the events in this video",
            "videos": [str(videos_dir / "sample2.mp4")],
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
    agent: LlmAgent,
    critic: LlmAgent,
    trainset: list[dict[str, Any]],
    runner: Runner,
) -> EvolutionResult:
    """Run evolutionary optimization on the video description agent.

    Args:
        agent: The video description agent to evolve.
        critic: The critic agent for scoring.
        trainset: Training examples with video files.
        runner: ADK Runner with session service for persistence.

    Returns:
        EvolutionResult containing the evolved instruction and metrics.

    Raises:
        VideoValidationError: If any video file is invalid (not found, too large,
            or not a video file).
    """
    # Conservative API limits for example - adjust for production use
    config = EvolutionConfig(
        max_iterations=2,  # Keep low for demo
        patience=1,  # Stop early if no improvement
        max_concurrent_evals=1,  # Sequential to limit API calls
    )

    logger.info(
        "evolution.starting",
        agent_name=agent.name,
        trainset_size=len(trainset),
        max_iterations=config.max_iterations,
    )

    try:
        result = await evolve(
            agent,
            trainset,
            critic=critic,
            config=config,
            runner=runner,  # Use runner for session persistence
        )

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
    """Run the video description evolution example."""
    # Check for Vertex AI configuration
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").upper() == "TRUE":
        if not os.getenv("GOOGLE_CLOUD_PROJECT"):
            raise ValueError("GOOGLE_CLOUD_PROJECT required when using Vertex AI")
    elif not os.getenv("GOOGLE_API_KEY"):
        raise ValueError(
            "Set GOOGLE_GENAI_USE_VERTEXAI=TRUE with GOOGLE_CLOUD_PROJECT, "
            "or set GOOGLE_API_KEY"
        )

    logger.info("example.video_description.start")

    # Set up SQLite database for session persistence
    data_dir = get_examples_dir().parent / "data"
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / "video_evolution_sessions.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    session_service = DatabaseSessionService(db_url=db_url)

    # Initialize database tables before concurrent operations
    await session_service.list_sessions(app_name="video_description_evolution")

    print(f"Session database: {db_path}")

    try:
        # Create agent, critic, and training data
        agent = create_agent()
        critic = create_critic()
        trainset = create_trainset()

        # Create Runner with database session service
        runner = Runner(
            app_name="video_description_evolution",
            agent=agent,
            session_service=session_service,
        )

        # Run evolution with critic scoring and session persistence
        result = await run_evolution(agent, critic, trainset, runner)

        # Display results
        print("\n" + "=" * 60)
        print("VIDEO DESCRIPTION EVOLUTION RESULTS")
        print("=" * 60)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score: {result.final_score:.3f}")
        print(f"Improvement: {result.improvement:.2%}")
        print(f"Iterations: {result.total_iterations}")
        print("\n" + "-" * 60)
        print("EVOLVED DESCRIPTION INSTRUCTION:")
        print("-" * 60)
        safe_print(result.evolved_components["instruction"])
        print("=" * 60)

        # Display database stats
        print("\n" + "-" * 60)
        print("ADK DATABASE STATS")
        print("-" * 60)

        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # ADK database has these tables:
        # - sessions: app_name, user_id, id, state (JSON), timestamps
        # - events: id, app_name, user_id, session_id, invocation_id, event_data (JSON)
        # - app_states, user_states: state storage
        # - adk_internal_metadata: schema version

        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
        print(f"Total sessions: {session_count}")

        cursor.execute("SELECT COUNT(*) FROM events")
        event_count = cursor.fetchone()[0]
        print(f"Total events: {event_count}")

        # Show recent sessions with state
        cursor.execute(
            "SELECT id, app_name, user_id FROM sessions ORDER BY update_time DESC LIMIT 3"
        )
        print("\nRecent sessions:")
        for row in cursor.fetchall():
            print(f"  {row[0][:40]}... ({row[1]}/{row[2]})")

        conn.close()

        print("\n" + "-" * 60)
        print("EXPLORE THE ADK DATABASE:")
        print("-" * 60)
        print(
            "Tables: sessions, events, app_states, user_states, adk_internal_metadata"
        )
        print("")
        print("# List all sessions:")
        print(f'sqlite3 {db_path} "SELECT id, app_name, user_id FROM sessions;"')
        print("")
        print("# View session state (JSON):")
        print(f'sqlite3 {db_path} "SELECT state FROM sessions LIMIT 1;"')
        print("")
        print("# View events for a session (event_data is JSON with full Event):")
        print(
            f'sqlite3 {db_path} "SELECT id, invocation_id, event_data FROM events LIMIT 5;"'
        )
        print("")
        print("# Pretty-print event JSON:")
        query = "SELECT json_extract(event_data, '$.author') as author FROM events;"
        print(f'sqlite3 {db_path} "{query}"')
        print("=" * 60)

        logger.info("example.video_description.success")

    except VideoValidationError as e:
        print(f"\nVideo validation error: {e}")
        print(f"Problem file: {e.video_path}")
        print(f"Constraint: {e.constraint}")
        print(
            "\nPlease ensure sample1.mp4 and sample2.mp4 are in examples/data/videos/"
        )
        logger.error("example.video_description.video_error", error=str(e))

    except Exception as e:
        logger.error("example.video_description.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

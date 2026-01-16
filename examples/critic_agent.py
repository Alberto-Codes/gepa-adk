"""Example: Evolution with critic agent.

This example shows how to use a dedicated critic agent for scoring
during evolution, separating generation from evaluation.

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/critic_agent.py
"""

from __future__ import annotations

import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, EvolutionResult, evolve_sync

# Configure structured logging
logger = structlog.get_logger()


class StoryOutput(BaseModel):
    """Output from the storytelling agent.

    Attributes:
        story: The generated story content.
        genre: The genre of the story.
    """

    story: str
    genre: str


class CriticOutput(BaseModel):
    """Output from the critic agent.

    Attributes:
        feedback: Detailed feedback on the story.
        creativity_score: Score for creativity (0.0-1.0).
        coherence_score: Score for plot coherence (0.0-1.0).
        engagement_score: Score for reader engagement (0.0-1.0).
        score: Overall quality score (0.0-1.0).
    """

    feedback: str
    creativity_score: float = Field(ge=0.0, le=1.0)
    coherence_score: float = Field(ge=0.0, le=1.0)
    engagement_score: float = Field(ge=0.0, le=1.0)
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall story quality score",
    )


def create_main_agent() -> LlmAgent:
    """Create the main storytelling agent.

    Returns:
        LlmAgent configured for story generation.
    """
    return LlmAgent(
        name="storyteller",
        model="ollama/gpt-oss:20b",
        instruction="Write a short, engaging story based on the given prompt.",
        output_schema=StoryOutput,
    )


def create_critic_agent() -> LlmAgent:
    """Create the critic agent for evaluation.

    Returns:
        LlmAgent configured as a story critic.
    """
    return LlmAgent(
        name="story_critic",
        model="ollama/gpt-oss:20b",
        instruction="""Evaluate the story quality. Consider:
- Creativity and originality of the concept
- Plot coherence and logical flow
- Character development and engagement
- Writing style and readability
- Overall impact and memorability

Provide constructive feedback and scores for each dimension.""",
        output_schema=CriticOutput,
    )


def create_trainset() -> list[dict[str, Any]]:
    """Create training prompts for story generation.

    Returns:
        List of story prompts.
    """
    return [
        {"input": "A robot learns to paint"},
        {"input": "A detective solves an impossible mystery"},
        {"input": "Two strangers meet on a train to nowhere"},
        {"input": "A child discovers a door to another world"},
        {"input": "An inventor accidentally creates something magical"},
    ]


def run_evolution(
    agent: LlmAgent,
    critic: LlmAgent,
    trainset: list[dict[str, Any]],
) -> EvolutionResult:
    """Run evolution with critic scoring.

    Args:
        agent: The main agent to evolve.
        critic: The critic agent for scoring.
        trainset: Training prompts.

    Returns:
        EvolutionResult with the evolved instruction.
    """
    config = EvolutionConfig(
        max_iterations=15,
        patience=5,
    )

    logger.info(
        "evolution.starting",
        agent_name=agent.name,
        critic_name=critic.name,
        trainset_size=len(trainset),
    )

    result = evolve_sync(agent, trainset, critic=critic, config=config)

    logger.info(
        "evolution.complete",
        original_score=result.original_score,
        final_score=result.final_score,
        improvement=result.improvement,
    )

    return result


def main() -> None:
    """Run the critic agent evolution example."""
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.critic_agent.start")

    try:
        # Create agents
        agent = create_main_agent()
        critic = create_critic_agent()
        trainset = create_trainset()

        # Run evolution with critic
        result = run_evolution(agent, critic, trainset)

        # Display results
        print("\n" + "=" * 60)
        print("CRITIC AGENT EVOLUTION RESULTS")
        print("=" * 60)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score: {result.final_score:.3f}")
        print(f"Improvement: {result.improvement:.2%}")
        print(f"Iterations: {result.total_iterations}")
        print("\n" + "-" * 60)
        print("EVOLVED INSTRUCTION:")
        print("-" * 60)
        print(result.evolved_instruction)
        print("=" * 60)

        logger.info("example.critic_agent.success")

    except Exception as e:
        logger.error("example.critic_agent.failed", error=str(e))
        raise


if __name__ == "__main__":
    main()

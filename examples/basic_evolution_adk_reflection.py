"""Example: Basic single-agent evolution with ADK reflection agent.

This example demonstrates evolving a greeting agent to produce formal,
Charles Dickens-style greetings appropriate for different social contexts
and honorifics.

Examples:
    Run the example:

    ```bash
    export OLLAMA_API_BASE=http://localhost:11434
    python examples/basic_evolution_adk_reflection.py
    ```

Note:
    Requires Python 3.12+, gepa-adk installed, and OLLAMA_API_BASE
    environment variable set to a running Ollama instance.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, EvolutionResult, evolve

# Configure structured logging
logger = structlog.get_logger()


class CriticOutput(BaseModel):
    """Structured output for critic evaluation.

    This schema is used by the critic agent (not the evolved agent) to provide
    structured scoring feedback during evolution.

    Attributes:
        score (float): Quality score (0.0-1.0).
        feedback (str): Evaluation feedback text.
    """

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality assessment score",
    )
    feedback: str


def create_agent() -> LlmAgent:
    """Create the greeting agent to be evolved.

    Returns:
        LlmAgent configured for greeting users.
    """
    return LlmAgent(
        name="greeter",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="Greet the user appropriately based on their introduction.",
    )


def create_critic() -> LlmAgent:
    """Create a critic agent for scoring greetings.

    Returns:
        LlmAgent configured as a critic for evaluating greeting quality.
    """
    return LlmAgent(
        name="critic",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="""Evaluate the greeting quality. Look for formal, elaborate,
Charles Dickens-style greetings that are appropriate for the social context and honorific.
Consider formality, elegance, period-appropriate language, and appropriateness for the title.
Provide a score from 0.0 to 1.0 where 1.0 is a perfect formal greeting.""",
        output_schema=CriticOutput,
    )


def create_reflection_agent() -> LlmAgent:
    """Create a reflection agent for instruction improvements.

    Uses ADK's native template substitution syntax (`{key}`) to inject
    session state values. ADK automatically replaces these placeholders
    with values from session.state during instruction processing.

    The instruction contains two placeholders:

    - `{component_text}`: The current instruction being evolved
    - `{trials}`: JSON-serialized list of trial records with scores/feedback

    Returns:
        LlmAgent configured for reflection with template placeholders.
    """
    return LlmAgent(
        name="reflector",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="""You are an expert at improving AI agent instructions.

## Current Instruction
{component_text}

## Trial Results
{trials}

Analyze what works and what doesn't based on the trial results above.
Then propose an improved version that:
1. Addresses issues identified in low-scoring trials
2. Preserves elements that worked well in high-scoring trials
3. Maintains clarity and specificity

Return ONLY the improved instruction text, no code, no markdown, no commentary.""",
    )


def create_trainset() -> list[dict[str, Any]]:
    """Create training examples with different user introductions and honorifics.

    Returns:
        List of training examples with user introductions.
    """
    return [
        {"input": "I am His Majesty, the King."},
        {"input": "I am your mother."},
        {"input": "I am a close friend."},
    ]


async def run_evolution(
    agent: LlmAgent,
    critic: LlmAgent,
    reflection_agent: LlmAgent,
    trainset: list[dict[str, Any]],
) -> EvolutionResult:
    """Run evolutionary optimization on the greeting agent.

    Args:
        agent: The greeting agent to evolve.
        critic: The critic agent for scoring.
        reflection_agent: The ADK reflection agent for instruction improvement.
        trainset: Training examples with user introductions.

    Returns:
        EvolutionResult containing the evolved instruction and metrics.
    """
    config = EvolutionConfig(
        max_iterations=3,
        patience=1,
        # reflection_model controls which LLM is used for mutation/reflection.
        # Default: "ollama_chat/gpt-oss:20b" (local Ollama model)
        # Examples of cloud models:
        #   reflection_model="gemini/gemini-2.5-flash",  # Google Gemini
        #   reflection_model="anthropic/claude-3-haiku",  # Anthropic Claude
    )

    logger.info(
        "evolution.starting",
        agent_name=agent.name,
        trainset_size=len(trainset),
        max_iterations=config.max_iterations,
    )

    result = await evolve(
        agent,
        trainset,
        critic=critic,
        reflection_agent=reflection_agent,
        config=config,
    )

    logger.info(
        "evolution.complete",
        original_score=result.original_score,
        final_score=result.final_score,
        improvement=result.improvement,
        total_iterations=result.total_iterations,
    )

    return result


async def main() -> None:
    """Run the basic evolution example."""
    # Check for Ollama API base
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.basic_evolution_adk_reflection.start")

    try:
        # Create agent, critic, reflection agent, and training data
        agent = create_agent()
        critic = create_critic()
        reflection_agent = create_reflection_agent()
        trainset = create_trainset()

        # Run evolution with critic scoring and ADK reflection agent
        result = await run_evolution(agent, critic, reflection_agent, trainset)

        # Display results
        print("\n" + "=" * 60)
        print("GREETING EVOLUTION RESULTS")
        print("=" * 60)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score: {result.final_score:.3f}")
        print(f"Improvement: {result.improvement:.2%}")
        print(f"Iterations: {result.total_iterations}")
        print("\n" + "-" * 60)
        print("EVOLVED GREETING INSTRUCTION:")
        print("-" * 60)
        print(result.evolved_component_text)
        print("=" * 60)

        logger.info("example.basic_evolution_adk_reflection.success")

    except Exception as e:
        logger.error("example.basic_evolution_adk_reflection.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

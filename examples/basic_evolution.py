"""Example: Basic single-agent evolution - Hello World Greeting.

This example demonstrates evolving a greeting agent to produce formal,
Charles Dickens-style greetings appropriate for different social contexts
and honorifics.

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/basic_evolution.py
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
from gepa_adk.utils import EncodingSafeProcessor

# -----------------------------------------------------------------------------
# Console Output Encoding
# -----------------------------------------------------------------------------
# Create a shared EncodingSafeProcessor instance for sanitizing both structlog
# output and direct print() statements. This prevents UnicodeEncodeError when
# printing LLM-generated text containing characters like smart quotes or dashes.
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
# Configure structlog with EncodingSafeProcessor to prevent UnicodeEncodeError
# on Windows consoles (cp1252 encoding). LLM outputs often contain Unicode
# characters like smart quotes (''), em dashes (—), and ellipses (…) that
# cannot be encoded to cp1252, causing crashes when logged.
#
# The EncodingSafeProcessor sanitizes these characters before they reach the
# console renderer, replacing them with ASCII equivalents (e.g., ' -> ', — -> --).
# On UTF-8 consoles (macOS/Linux), this is transparent.
# -----------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        EncodingSafeProcessor(),  # Sanitize Unicode for Windows cp1252 consoles
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class CriticOutput(BaseModel):
    """Structured output for critic evaluation.

    This schema is used by the critic agent (not the evolved agent) to provide
    structured scoring feedback during evolution.

    Attributes:
        score: Quality score (0.0-1.0).
        feedback: Evaluation feedback.
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
    agent: LlmAgent, critic: LlmAgent, trainset: list[dict[str, Any]]
) -> EvolutionResult:
    """Run evolutionary optimization on the greeting agent.

    Args:
        agent: The greeting agent to evolve.
        critic: The critic agent for scoring.
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

    result = await evolve(agent, trainset, critic=critic, config=config)

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

    logger.info("example.basic_evolution.start")

    try:
        # Create agent, critic, and training data
        agent = create_agent()
        critic = create_critic()
        trainset = create_trainset()

        # Run evolution with critic scoring
        result = await run_evolution(agent, critic, trainset)

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
        safe_print(result.evolved_component_text)
        print("=" * 60)

        logger.info("example.basic_evolution.success")

    except Exception as e:
        logger.error("example.basic_evolution.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

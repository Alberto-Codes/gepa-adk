"""Example: Generation config evolution demo.

This example demonstrates evolving an agent's LLM generation configuration
(temperature, top_p, max_output_tokens) alongside its instruction to optimize
performance on a creative writing task.

The evolution process tunes both the instruction and generation parameters
to find the optimal combination for producing engaging stories.

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/config_evolution_demo.py
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, EvolutionResult, evolve
from gepa_adk.adapters import get_handler
from gepa_adk.utils import EncodingSafeProcessor

# -----------------------------------------------------------------------------
# Console Output Encoding
# -----------------------------------------------------------------------------
_encoding_processor = EncodingSafeProcessor()


def safe_print(text: str) -> None:
    """Print text safely on Windows consoles with cp1252 encoding."""
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


class CriticOutput(BaseModel):
    """Structured output for critic evaluation.

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
    """Create the story-writing agent to be evolved.

    Returns:
        LlmAgent configured for creative story writing with initial
        generation config parameters.
    """
    return LlmAgent(
        name="storyteller",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="Write a short, engaging story based on the given prompt.",
        generate_content_config=GenerateContentConfig(
            temperature=0.7,
            top_p=0.9,
            max_output_tokens=512,
        ),
    )


def create_critic() -> LlmAgent:
    """Create a critic agent for scoring stories.

    Returns:
        LlmAgent configured as a critic for evaluating story quality.
    """
    return LlmAgent(
        name="critic",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="""Evaluate the story quality. Look for:
- Engaging narrative with clear beginning, middle, and end
- Creative and vivid descriptions
- Appropriate tone for the prompt
- Good pacing and flow

Provide a score from 0.0 to 1.0 where 1.0 is an excellent, captivating story.""",
        output_schema=CriticOutput,
    )


def create_trainset() -> list[dict[str, Any]]:
    """Create training examples with story prompts.

    Returns:
        List of training examples with story prompts.
    """
    return [
        {"input": "A robot discovers it can dream."},
        {"input": "The last tree on Earth blooms."},
        {"input": "A letter arrives from the future."},
    ]


def demonstrate_handler_usage(agent: LlmAgent) -> None:
    """Demonstrate direct handler usage for config serialization.

    Args:
        agent: The LlmAgent to demonstrate with.
    """
    print("\n" + "-" * 60)
    print("HANDLER DEMONSTRATION")
    print("-" * 60)

    # Get the config handler
    handler = get_handler("generate_content_config")

    # Serialize current config
    yaml_text = handler.serialize(agent)
    print("Current config (YAML):")
    safe_print(yaml_text)

    # Show apply/restore pattern
    print("\nApplying temporary config change...")
    original = handler.apply(agent, "temperature: 0.3\ntop_p: 0.5")
    print(f"Temp config: temp={agent.generate_content_config.temperature}")

    # Restore original
    handler.restore(agent, original)
    print(f"Restored: temp={agent.generate_content_config.temperature}")
    print("-" * 60)


async def run_evolution(
    agent: LlmAgent, critic: LlmAgent, trainset: list[dict[str, Any]]
) -> EvolutionResult:
    """Run evolutionary optimization on both instruction and config.

    Args:
        agent: The storyteller agent to evolve.
        critic: The critic agent for scoring.
        trainset: Training examples with story prompts.

    Returns:
        EvolutionResult containing evolved instruction, config, and metrics.
    """
    config = EvolutionConfig(
        max_iterations=3,
        patience=1,
    )

    logger.info(
        "evolution.starting",
        agent_name=agent.name,
        trainset_size=len(trainset),
        max_iterations=config.max_iterations,
        components=["instruction", "generate_content_config"],
    )

    # Evolve both instruction AND generation config
    result = await evolve(
        agent,
        trainset,
        critic=critic,
        config=config,
        components=["instruction", "generate_content_config"],
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
    """Run the config evolution demo."""
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.config_evolution_demo.start")

    try:
        # Create agent, critic, and training data
        agent = create_agent()
        critic = create_critic()
        trainset = create_trainset()

        # Demonstrate handler usage
        demonstrate_handler_usage(agent)

        # Run evolution with both instruction and config
        result = await run_evolution(agent, critic, trainset)

        # Display results
        print("\n" + "=" * 60)
        print("CONFIG EVOLUTION RESULTS")
        print("=" * 60)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score: {result.final_score:.3f}")
        print(f"Improvement: {result.improvement:.2%}")
        print(f"Iterations: {result.total_iterations}")

        print("\n" + "-" * 60)
        print("EVOLVED INSTRUCTION:")
        print("-" * 60)
        safe_print(result.evolved_components.get("instruction", "N/A"))

        print("\n" + "-" * 60)
        print("EVOLVED GENERATION CONFIG:")
        print("-" * 60)
        config_text = result.evolved_components.get("generate_content_config", "N/A")
        safe_print(config_text)

        print("=" * 60)

        logger.info("example.config_evolution_demo.success")

    except Exception as e:
        logger.error("example.config_evolution_demo.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

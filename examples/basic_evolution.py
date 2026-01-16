"""Example: Basic single-agent evolution.

This example shows how to evolve a single agent's instruction using
gepa-adk's evolutionary optimization.

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/basic_evolution.py
"""

from __future__ import annotations

import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, EvolutionResult, evolve_sync

# Configure structured logging
logger = structlog.get_logger()


class CriticOutput(BaseModel):
    """Structured output for critic evaluation.

    Attributes:
        feedback: Evaluation feedback.
        score: Quality score (0.0-1.0).
    """

    feedback: str
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality assessment score",
    )


def create_agent() -> LlmAgent:
    """Create the agent to be evolved.

    Returns:
        LlmAgent configured for Q&A tasks.
    """
    return LlmAgent(
        name="qa_assistant",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="You are a helpful assistant that answers questions accurately and concisely.",
    )


def create_critic() -> LlmAgent:
    """Create a critic agent for scoring.

    Returns:
        LlmAgent configured as a critic for evaluation.
    """
    return LlmAgent(
        name="critic",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="""Evaluate the response quality. Consider accuracy and clarity.
Provide a score from 0.0 to 1.0 where 1.0 is perfect.""",
        output_schema=CriticOutput,
    )


def create_trainset() -> list[dict[str, Any]]:
    """Create training examples for evolution.

    Returns:
        List of training examples with input and expected output.
    """
    return [
        {"input": "What is the capital of France?", "expected": "Paris"},
        {"input": "What is 2 + 2?", "expected": "4"},
        {"input": "Who wrote Romeo and Juliet?", "expected": "William Shakespeare"},
        {"input": "What is the chemical symbol for water?", "expected": "H2O"},
        {"input": "What year did World War II end?", "expected": "1945"},
    ]


def run_evolution(
    agent: LlmAgent, critic: LlmAgent, trainset: list[dict[str, Any]]
) -> EvolutionResult:
    """Run evolutionary optimization on the agent.

    Args:
        agent: The agent to evolve.
        critic: The critic agent for scoring.
        trainset: Training examples for evaluation.

    Returns:
        EvolutionResult containing the evolved instruction and metrics.
    """
    config = EvolutionConfig(
        max_iterations=10,
        patience=7,
    )

    logger.info(
        "evolution.starting",
        agent_name=agent.name,
        trainset_size=len(trainset),
        max_iterations=config.max_iterations,
    )

    result = evolve_sync(agent, trainset, critic=critic, config=config)

    logger.info(
        "evolution.complete",
        original_score=result.original_score,
        final_score=result.final_score,
        improvement=result.improvement,
        total_iterations=result.total_iterations,
    )

    return result


def main() -> None:
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
        result = run_evolution(agent, critic, trainset)

        # Display results
        print("\n" + "=" * 60)
        print("EVOLUTION RESULTS")
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

        logger.info("example.basic_evolution.success")

    except Exception as e:
        logger.error("example.basic_evolution.failed", error=str(e))
        raise


if __name__ == "__main__":
    main()

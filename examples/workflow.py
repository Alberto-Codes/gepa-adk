"""Example: Workflow evolution with SequentialAgent.

This example shows how to evolve agents within an ADK workflow structure,
preserving the workflow configuration while optimizing agent instructions.

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/workflow.py
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, MultiAgentEvolutionResult, evolve_workflow

# Configure structured logging
logger = structlog.get_logger()


class IdeaOutput(BaseModel):
    """Output from the ideation agent.

    Attributes:
        ideas: List of generated ideas.
        best_idea: The most promising idea.
    """

    ideas: list[str]
    best_idea: str


class OutlineOutput(BaseModel):
    """Output from the outline agent.

    Attributes:
        outline: Structured outline sections.
        structure: Description of the structure.
    """

    outline: list[str]
    structure: str


class ArticleOutput(BaseModel):
    """Output from the article writing agent.

    Attributes:
        article: The complete article text.
        word_count: Number of words in the article.
        score: Self-assessed quality score.
    """

    article: str
    word_count: int
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality score for the article",
    )


def create_workflow() -> SequentialAgent:
    """Create a SequentialAgent workflow for article writing.

    Returns:
        SequentialAgent containing the ideator, outliner, and writer.
    """
    ideator = LlmAgent(
        name="ideator",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="Generate creative ideas for the given topic.",
        output_schema=IdeaOutput,
    )

    outliner = LlmAgent(
        name="outliner",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="Create a structured outline from the best idea.",
        output_schema=OutlineOutput,
    )

    writer = LlmAgent(
        name="writer",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="Write a complete article following the outline.",
        output_schema=ArticleOutput,
    )

    return SequentialAgent(
        name="ArticleWorkflow",
        sub_agents=[ideator, outliner, writer],
    )


def create_trainset() -> list[dict[str, Any]]:
    """Create training topics for article writing.

    Returns:
        List of article topics.
    """
    return [
        {"input": "Write about sustainable living tips"},
        {"input": "Write about productivity habits for developers"},
        {"input": "Write about personal finance basics for beginners"},
    ]


async def run_evolution(
    workflow: SequentialAgent,
    trainset: list[dict[str, Any]],
) -> MultiAgentEvolutionResult:
    """Run workflow evolution.

    Args:
        workflow: The SequentialAgent workflow to evolve.
        trainset: Training topics.

    Returns:
        MultiAgentEvolutionResult with evolved instructions for all agents.
    """
    config = EvolutionConfig(
        max_iterations=5,
        patience=2,
    )

    logger.info(
        "evolution.workflow.starting",
        workflow_name=workflow.name,
        trainset_size=len(trainset),
    )

    result = await evolve_workflow(
        workflow=workflow,
        trainset=trainset,
        config=config,
        # primary defaults to last agent (writer)
    )

    logger.info(
        "evolution.workflow.complete",
        original_score=result.original_score,
        final_score=result.final_score,
        improvement=result.improvement,
    )

    return result


async def async_main() -> None:
    """Async entry point for the example."""
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.workflow.start")

    try:
        # Create workflow and training data
        workflow = create_workflow()
        trainset = create_trainset()

        # Run evolution
        result = await run_evolution(workflow, trainset)

        # Display results
        print("\n" + "=" * 60)
        print("WORKFLOW EVOLUTION RESULTS")
        print("=" * 60)
        print(f"Primary agent: {result.primary_agent}")
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score: {result.final_score:.3f}")
        print(f"Improvement: {result.improvement:.2%}")
        print(f"Iterations: {result.total_iterations}")

        print("\n" + "-" * 60)
        print("EVOLVED INSTRUCTIONS:")
        print("-" * 60)
        for name, instruction in result.evolved_instructions.items():
            print(f"\n[{name}]")
            print(instruction)
        print("=" * 60)

        logger.info("example.workflow.success")

    except Exception as e:
        logger.error("example.workflow.failed", error=str(e))
        raise


def main() -> None:
    """Run the workflow evolution example."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

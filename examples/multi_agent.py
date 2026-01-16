"""Example: Multi-agent co-evolution.

This example shows how to evolve multiple agents together in a
coordinated pipeline where agents share session state.

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/multi_agent.py
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, MultiAgentEvolutionResult, evolve_group

# Configure structured logging
logger = structlog.get_logger()


class ResearchOutput(BaseModel):
    """Output from the research agent.

    Attributes:
        findings: Key research findings.
        sources: List of sources referenced.
    """

    findings: str
    sources: list[str]


class AnalysisOutput(BaseModel):
    """Output from the analysis agent.

    Attributes:
        analysis: Detailed analysis of findings.
        key_insights: List of key insights extracted.
    """

    analysis: str
    key_insights: list[str]


class ReportOutput(BaseModel):
    """Output from the report writing agent.

    Attributes:
        report: The complete report.
        summary: Executive summary.
        score: Self-assessed quality score.
    """

    report: str
    summary: str
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality score for the report",
    )


def create_agents() -> list[LlmAgent]:
    """Create the multi-agent pipeline.

    Returns:
        List of agents: researcher, analyst, reporter.
    """
    researcher = LlmAgent(
        name="researcher",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="Research the topic and gather relevant information and findings.",
        output_schema=ResearchOutput,
    )

    analyst = LlmAgent(
        name="analyst",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="Analyze the research findings and extract key insights.",
        output_schema=AnalysisOutput,
    )

    reporter = LlmAgent(
        name="reporter",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="Write a comprehensive report based on the analysis.",
        output_schema=ReportOutput,
    )

    return [researcher, analyst, reporter]


def create_trainset() -> list[dict[str, Any]]:
    """Create training topics for the research pipeline.

    Returns:
        List of research topics.
    """
    return [
        {"input": "Impact of artificial intelligence on healthcare"},
        {"input": "Future trends in renewable energy"},
        {"input": "Evolution of remote work practices"},
        {"input": "Advances in space exploration technology"},
        {"input": "Trends in sustainable agriculture"},
    ]


async def run_evolution(
    agents: list[LlmAgent],
    trainset: list[dict[str, Any]],
) -> MultiAgentEvolutionResult:
    """Run multi-agent co-evolution.

    Args:
        agents: List of agents to evolve together.
        trainset: Training topics.

    Returns:
        MultiAgentEvolutionResult with evolved instructions for all agents.
    """
    config = EvolutionConfig(
        max_iterations=15,
        patience=7,
    )

    logger.info(
        "evolution.multi_agent.starting",
        agent_count=len(agents),
        agent_names=[a.name for a in agents],
        trainset_size=len(trainset),
    )

    result = await evolve_group(
        agents=agents,
        primary="reporter",  # Score based on final report quality
        trainset=trainset,
        share_session=True,  # Agents share context
        config=config,
    )

    logger.info(
        "evolution.multi_agent.complete",
        original_score=result.original_score,
        final_score=result.final_score,
        improvement=result.improvement,
    )

    return result


async def async_main() -> None:
    """Async entry point for the example."""
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.multi_agent.start")

    try:
        # Create agents and training data
        agents = create_agents()
        trainset = create_trainset()

        # Run evolution
        result = await run_evolution(agents, trainset)

        # Display results
        print("\n" + "=" * 60)
        print("MULTI-AGENT EVOLUTION RESULTS")
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

        logger.info("example.multi_agent.success")

    except Exception as e:
        logger.error("example.multi_agent.failed", error=str(e))
        raise


def main() -> None:
    """Run the multi-agent evolution example."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

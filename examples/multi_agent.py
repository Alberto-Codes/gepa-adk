"""Example: Multi-agent co-evolution.

This example shows how to evolve multiple agents together in a
coordinated pipeline where agents share session state.

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - Ollama running locally with gpt-oss:20b model pulled
    - OLLAMA_API_BASE environment variable set (defaults to http://localhost:11434)

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
from gepa_adk.domain.types import TrajectoryConfig

# Configure structured logging
logger = structlog.get_logger()


class CriticOutput(BaseModel):
    """Output from the external critic agent.

    Attributes:
        score: Quality score (0.0-1.0).
        feedback: Detailed feedback on the report.
        dimension_scores: Per-dimension scores for report evaluation.
        actionable_guidance: Specific improvement suggestions.
    """

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall report quality score",
    )
    feedback: str
    dimension_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Per-dimension scores (clarity, completeness, accuracy)",
    )
    actionable_guidance: str = Field(
        default="",
        description="Specific improvement suggestions",
    )


def create_agents() -> tuple[list[LlmAgent], LlmAgent]:
    """Create the multi-agent pipeline and external critic.

    Returns:
        Tuple of (pipeline agents, critic agent).
        Pipeline agents: content_producer, formatter.
        Critic: External agent that evaluates formatted output quality.
    """
    # First agent: Produces content (no output_schema)
    # Uses output_key to save content to session state for the formatter
    content_producer = LlmAgent(
        name="content_producer",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),  # General purpose model via Ollama
        instruction="Generate informative content about the given topic. Provide detailed information, facts, and insights.",
        output_key="raw_content",  # Saves output to session state
    )

    # Second agent: Formats the content (no output_schema)
    # Accesses content_producer's output via {raw_content} template
    formatter = LlmAgent(
        name="formatter",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),  # General purpose model via Ollama
        instruction="Format the content in {raw_content} into a well-structured, polished document. Ensure clarity, proper organization, and professional presentation.",
    )

    # External critic - evaluates formatter's output independently
    # This avoids the conflict of interest where formatter scores itself
    critic = LlmAgent(
        name="format_critic",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),  # General purpose model via Ollama
        instruction="""Evaluate the overall report quality focusing on content and structure.

Consider:
- Content quality: Depth, accuracy, and value of the information
- Structure: Organization, logical flow, and clear sections
- Clarity: Readability and ease of understanding
- Completeness: Coverage of the topic and thoroughness
- Presentation: Professional formatting and polish

Provide:
1. An overall score from 0.0 to 1.0
2. Detailed feedback explaining your evaluation of content and structure
3. Dimension scores as a dict with keys: content_quality, structure, clarity, completeness, presentation
4. Actionable guidance with specific suggestions for improvement

All scores must be between 0.0 and 1.0.""",
        output_schema=CriticOutput,
    )

    # Note: No reflection_agent - uses default LiteLLM proposer for instruction mutation
    # The default proposer calls litellm.acompletion() directly with a simpler prompt

    return [content_producer, formatter], critic


def create_trainset() -> list[dict[str, Any]]:
    """Create training topics for content production and formatting.

    Returns:
        List of content topics.
    """
    return [
        {"input": "Impact of artificial intelligence on healthcare"},
        {"input": "Future trends in renewable energy"},
        {"input": "Evolution of remote work practices"},
    ]


async def run_evolution(
    agents: list[LlmAgent],
    critic: LlmAgent,
    trainset: list[dict[str, Any]],
) -> MultiAgentEvolutionResult:
    """Run multi-agent co-evolution with external critic.

    Args:
        agents: List of agents to evolve together.
        critic: External critic agent that scores the formatter's output.
        trainset: Training topics.

    Returns:
        MultiAgentEvolutionResult with evolved instructions for all agents.

    Note:
        Uses an external critic to avoid conflict of interest where the
        formatter would score itself. The critic evaluates formatted output
        quality independently, ensuring honest scoring for evolution.
        Uses default LiteLLM proposer for instruction mutation.
    """
    config = EvolutionConfig(
        max_iterations=3,
        patience=2,
    )

    # Disable trajectory capture for faster execution
    trajectory_config = TrajectoryConfig(
        include_tool_calls=False,
        include_state_deltas=False,
        include_token_usage=False,
    )

    logger.info(
        "evolution.multi_agent.starting",
        agent_count=len(agents),
        agent_names=[a.name for a in agents],
        trainset_size=len(trainset),
        has_critic=True,
    )

    result = await evolve_group(
        agents=agents,
        primary="formatter",  # Score based on final formatted output quality
        trainset=trainset,
        critic=critic,  # External critic - honest scoring without self-assessment
        share_session=True,  # Agents share context (formatter accesses {raw_content})
        config=config,
        trajectory_config=trajectory_config,  # Disable trajectory capture for speed
        # No reflection_agent - uses default LiteLLM proposer
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
    # Note: Requires Ollama running locally with qwen3-coder:30b model pulled
    # OLLAMA_API_BASE defaults to http://localhost:11434 if not set
    logger.info("example.multi_agent.start")

    try:
        # Create agents and training data
        agents, critic = create_agents()
        trainset = create_trainset()

        # Run evolution with external critic (uses default LiteLLM proposer)
        result = await run_evolution(agents, critic, trainset)

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

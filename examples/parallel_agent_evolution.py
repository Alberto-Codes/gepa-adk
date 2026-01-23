"""Example: ParallelAgent evolution with concurrent execution preservation.

This example demonstrates evolving agents within a ParallelAgent workflow where:
1. Multiple researcher agents execute concurrently
2. The ParallelAgent type is preserved during evolution (not flattened)
3. Each branch produces output that can be accessed via output_key
4. A synthesizer agent combines the parallel outputs

Key Concepts:
    - ParallelAgent structure preservation during workflow evolution
    - Concurrent execution is maintained when cloning the workflow
    - Each parallel branch has its own output_key for session state
    - Parallel outputs can be combined by subsequent agents

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/parallel_agent_evolution.py
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm

from gepa_adk import (
    CriticOutput,
    EvolutionConfig,
    MultiAgentEvolutionResult,
    evolve_workflow,
)
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


# -----------------------------------------------------------------------------
# ParallelAgent Workflow (Contains agents that get evolved)
# -----------------------------------------------------------------------------
def create_parallel_researchers() -> ParallelAgent:
    """Create parallel researcher agents that execute concurrently.

    These agents research different aspects of a topic simultaneously.
    Each agent has an output_key so their results are available in
    session state for the synthesizer.

    Returns:
        ParallelAgent with three concurrent researcher branches.
    """
    researcher1 = LlmAgent(
        name="historical_researcher",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "Research the historical background and context.\n"
            "Focus on key events, dates, and influential figures.\n"
            "Provide a concise but informative summary."
        ),
        output_key="historical_context",
    )

    researcher2 = LlmAgent(
        name="current_researcher",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "Research the current state and recent developments.\n"
            "Focus on trends, challenges, and opportunities.\n"
            "Provide a concise but informative summary."
        ),
        output_key="current_trends",
    )

    researcher3 = LlmAgent(
        name="future_researcher",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "Research future predictions and projections.\n"
            "Focus on emerging technologies, potential impacts, and forecasts.\n"
            "Provide a concise but informative summary."
        ),
        output_key="future_predictions",
    )

    # All three researchers execute CONCURRENTLY
    # This is preserved during evolution - they won't be flattened to sequential
    return ParallelAgent(
        name="ParallelResearch",
        sub_agents=[researcher1, researcher2, researcher3],
    )


def create_synthesizer() -> LlmAgent:
    """Create a synthesizer agent that combines parallel outputs.

    The synthesizer accesses all three researcher outputs via template
    strings, creating a unified analysis from the parallel research.

    Returns:
        LlmAgent configured to synthesize parallel research outputs.
    """
    return LlmAgent(
        name="synthesizer",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "Synthesize the following research into a cohesive analysis:\n\n"
            "## Historical Context\n"
            "{historical_context}\n\n"
            "## Current Trends\n"
            "{current_trends}\n\n"
            "## Future Predictions\n"
            "{future_predictions}\n\n"
            "Create a well-structured synthesis that connects past, present, and future."
        ),
        output_key="synthesis",
    )


def create_research_pipeline() -> SequentialAgent:
    """Create the full research pipeline with parallel research stage.

    The pipeline structure is:
    1. ParallelAgent: Three researchers execute concurrently
    2. Synthesizer: Combines all research into a unified analysis

    This demonstrates nested workflow structure preservation:
    - The ParallelAgent is preserved (not flattened)
    - The SequentialAgent order is maintained

    Returns:
        SequentialAgent containing parallel research and synthesis stages.
    """
    parallel_research = create_parallel_researchers()
    synthesizer = create_synthesizer()

    return SequentialAgent(
        name="ResearchPipeline",
        sub_agents=[parallel_research, synthesizer],
    )


# -----------------------------------------------------------------------------
# Critic Agent (Scores the synthesis - NOT evolved)
# -----------------------------------------------------------------------------
def create_critic() -> LlmAgent:
    """Create a critic agent for scoring the synthesized output.

    The critic evaluates the quality of the synthesis, checking for
    integration of all three research perspectives.

    Returns:
        LlmAgent configured as a synthesis quality critic.
    """
    return LlmAgent(
        name="synthesis_critic",
        description=(
            "A research synthesis critic who evaluates how well "
            "parallel research outputs are integrated into a cohesive analysis."
        ),
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "You are a research synthesis critic. Evaluate how well the synthesis:\n\n"
            "## Dimension Scores (0.0-1.0 each):\n"
            "- integration: Does it effectively combine historical, current, and future?\n"
            "- coherence: Is the narrative logical and well-connected?\n"
            "- insight: Does it provide meaningful connections and insights?\n"
            "- completeness: Does it adequately represent all three perspectives?\n\n"
            "## Scoring Guide:\n"
            "- 0.0-0.2: Poor synthesis. Sources not integrated, disjointed.\n"
            "- 0.3-0.4: Basic synthesis. Sources mentioned but not connected.\n"
            "- 0.5-0.6: Average synthesis. Some connections made.\n"
            "- 0.7-0.8: Good synthesis. Clear connections between perspectives.\n"
            "- 0.9-1.0: Excellent synthesis. Insightful integration, compelling narrative.\n\n"
            "## In Your Feedback:\n"
            "- Identify specific areas where integration works well or could improve\n"
            "- Suggest concrete ways to better connect the three perspectives\n"
        ),
        output_schema=CriticOutput,
    )


# -----------------------------------------------------------------------------
# Training Data
# -----------------------------------------------------------------------------
def create_trainset() -> list[dict[str, Any]]:
    """Create training examples for evolution.

    Each example is a research topic that benefits from parallel
    investigation across historical, current, and future perspectives.
    """
    return [
        {"input": "Research the evolution and impact of artificial intelligence."},
        {"input": "Research the development of renewable energy technologies."},
        {"input": "Research the transformation of global communication systems."},
    ]


# -----------------------------------------------------------------------------
# Evolution Runner
# -----------------------------------------------------------------------------
async def run_parallel_agent_evolution(
    workflow: SequentialAgent,
    critic: LlmAgent,
    trainset: list[dict[str, Any]],
) -> MultiAgentEvolutionResult:
    """Run evolutionary optimization on the ParallelAgent workflow.

    The evolution process:
    1. Each training example runs through the full pipeline:
       - ParallelAgent executes all three researchers concurrently
       - Synthesizer combines the outputs
    2. The critic scores the synthesis
    3. The reflection agent suggests improved instructions
    4. Instructions are updated and the process repeats

    CRITICAL: The ParallelAgent is preserved during evolution. The three
    researchers continue to execute concurrently, not sequentially.

    Args:
        workflow: The SequentialAgent containing the ParallelAgent.
        critic: Separate critic agent for scoring (not evolved).
        trainset: Training examples for evolution.

    Returns:
        MultiAgentEvolutionResult with evolved instructions for all agents.
    """
    config = EvolutionConfig(
        max_iterations=4,
        patience=2,
    )

    # Count agents in the parallel stage
    parallel_stage = workflow.sub_agents[0]
    parallel_agent_count = (
        len(parallel_stage.sub_agents)
        if isinstance(parallel_stage, ParallelAgent)
        else 0
    )

    logger.info(
        "parallel_agent_evolution.starting",
        workflow_name=workflow.name,
        parallel_branches=parallel_agent_count,
        trainset_size=len(trainset),
        evolution_iterations=config.max_iterations,
    )

    # evolve_workflow() preserves the ParallelAgent structure:
    # - ParallelAgent type is maintained when cloning
    # - All branches execute concurrently during evaluation
    # - Session state contains all parallel outputs
    result = await evolve_workflow(
        workflow=workflow,
        trainset=trainset,
        critic=critic,
        round_robin=True,  # Evolve all agents including parallel branches
        config=config,
    )

    logger.info(
        "parallel_agent_evolution.complete",
        original_score=result.original_score,
        final_score=result.final_score,
        improvement=result.improvement,
        total_iterations=result.total_iterations,
    )

    return result


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
async def main() -> None:
    """Run the ParallelAgent evolution example."""
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.parallel_agent.start")

    try:
        # Create the research pipeline with parallel research stage
        workflow = create_research_pipeline()

        # Verify the parallel structure
        parallel_stage = workflow.sub_agents[0]
        logger.info(
            "parallel_agent.config",
            workflow_name=workflow.name,
            stage_count=len(workflow.sub_agents),
            parallel_branches=[a.name for a in parallel_stage.sub_agents]
            if isinstance(parallel_stage, ParallelAgent)
            else [],
        )

        # Create the critic agent (scores output, NOT evolved)
        critic = create_critic()

        # Create training examples
        trainset = create_trainset()

        # Run evolution
        result = await run_parallel_agent_evolution(workflow, critic, trainset)

        # Display results
        print("\n" + "=" * 70)
        print("PARALLELAGENT EVOLUTION RESULTS")
        print("=" * 70)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score:    {result.final_score:.3f}")
        print(f"Improvement:    {result.improvement:.2%}")
        print(f"Iterations:     {result.total_iterations}")

        print("\n" + "-" * 70)
        print("EVOLVED AGENT INSTRUCTIONS:")
        print("-" * 70)

        # In evolve_workflow(), evolved_components uses qualified names
        for qualified_name, instruction in result.evolved_components.items():
            print(f"\n>>> {qualified_name.upper()} <<<")
            print("-" * 70)
            safe_print(instruction)

        print("\n" + "=" * 70)
        logger.info("example.parallel_agent.success")

    except Exception as e:
        logger.error("example.parallel_agent.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

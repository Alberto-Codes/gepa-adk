"""Example: LoopAgent evolution with iteration preservation.

This example demonstrates evolving agents within a LoopAgent workflow where:
1. An inner refiner agent improves content through multiple iterations
2. The LoopAgent executes the refiner 3 times per evaluation
3. The max_iterations configuration is preserved during evolution
4. A critic agent scores the final iteration's output

Key Concepts:
    - LoopAgent structure preservation during workflow evolution
    - max_iterations is maintained when cloning the workflow
    - Each training example runs through all loop iterations
    - Final iteration output is used for scoring

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/loop_agent_evolution.py
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent, LoopAgent
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
# LoopAgent Workflow (Contains the agent that gets evolved)
# -----------------------------------------------------------------------------
def create_refiner() -> LlmAgent:
    """Create the refiner agent that runs inside the loop.

    The refiner improves content through each iteration. With max_iterations=3,
    this agent runs 3 times per training example, each time building on the
    previous iteration's output.

    Returns:
        LlmAgent configured for iterative content refinement.
    """
    return LlmAgent(
        name="refiner",
        model=LiteLlm(model="ollama_chat/llama3.2:latest"),
        instruction=(
            "Review and improve the current content. Focus on:\n"
            "- Clarity and readability\n"
            "- Adding concrete examples\n"
            "- Removing redundancy\n"
            "- Strengthening the conclusion\n\n"
            "Produce an improved version of the content."
        ),
        output_key="refined_content",
    )


def create_refinement_loop(refiner: LlmAgent) -> LoopAgent:
    """Create a LoopAgent that runs the refiner multiple times.

    The LoopAgent executes its sub_agents for max_iterations times.
    This creates an iterative refinement workflow where output improves
    through multiple passes.

    IMPORTANT: The max_iterations value (3) is preserved during evolution.
    This means each training example runs through all 3 iterations, and
    the final iteration's output is used for scoring.

    Args:
        refiner: The inner agent to run in the loop.

    Returns:
        LoopAgent configured for 3 refinement iterations.
    """
    return LoopAgent(
        name="RefinementLoop",
        sub_agents=[refiner],
        max_iterations=3,  # This is preserved during evolution!
    )


# -----------------------------------------------------------------------------
# Critic Agent (Scores the refined output - NOT evolved)
# -----------------------------------------------------------------------------
def create_critic() -> LlmAgent:
    """Create a critic agent for scoring the refined content.

    The critic evaluates the quality of the final refined output after
    all loop iterations complete. It scores on dimensions like clarity,
    structure, and persuasiveness.

    Returns:
        LlmAgent configured as a quality critic with structured output.
    """
    return LlmAgent(
        name="quality_critic",
        description=(
            "A content quality critic who evaluates refined text for "
            "clarity, structure, examples, and persuasiveness."
        ),
        model=LiteLlm(model="ollama_chat/llama3.2:latest"),
        instruction=(
            "You are a content quality critic. Evaluate the refined content on:\n\n"
            "## Dimension Scores (0.0-1.0 each):\n"
            "- clarity: Is the content clear and easy to understand?\n"
            "- structure: Is it well-organized with logical flow?\n"
            "- examples: Does it include concrete, helpful examples?\n"
            "- persuasiveness: Is the conclusion strong and compelling?\n\n"
            "## Scoring Guide:\n"
            "- 0.0-0.2: Poor quality. Hard to follow, no examples.\n"
            "- 0.3-0.4: Below average. Some issues with clarity or structure.\n"
            "- 0.5-0.6: Average. Acceptable but could be improved.\n"
            "- 0.7-0.8: Good quality. Clear, well-structured, has examples.\n"
            "- 0.9-1.0: Excellent. Highly refined, persuasive, comprehensive.\n\n"
            "## In Your Feedback:\n"
            "- Identify specific passages that work well or need improvement\n"
            "- Suggest concrete improvements for weak areas\n"
            "- Note whether the iterative refinement improved the content\n"
        ),
        output_schema=CriticOutput,
    )


# -----------------------------------------------------------------------------
# Training Data
# -----------------------------------------------------------------------------
def create_trainset() -> list[dict[str, Any]]:
    """Create training examples for evolution.

    Each example tests the refinement loop with content that benefits
    from iterative improvement. The critic scores the final refined output.
    """
    return [
        {"input": "Explain why regular exercise is important for mental health."},
        {"input": "Describe the benefits of learning a second language."},
        {"input": "Explain how compound interest works for beginners."},
    ]


# -----------------------------------------------------------------------------
# Evolution Runner
# -----------------------------------------------------------------------------
async def run_loop_agent_evolution(
    workflow: LoopAgent,
    critic: LlmAgent,
    trainset: list[dict[str, Any]],
) -> MultiAgentEvolutionResult:
    """Run evolutionary optimization on the LoopAgent workflow.

    The evolution process:
    1. Each training example runs through the LoopAgent (3 iterations)
    2. The critic scores the final iteration's output
    3. The reflection agent suggests improved instructions for the refiner
    4. The refiner's instruction is updated and the process repeats

    CRITICAL: The max_iterations=3 is preserved during evolution. This means
    the refiner runs 3 times per example, allowing it to iteratively improve
    content before scoring.

    Args:
        workflow: The LoopAgent containing the refiner to evolve.
        critic: Separate critic agent for scoring (not evolved).
        trainset: Training examples for evolution.

    Returns:
        MultiAgentEvolutionResult with evolved refiner instruction.
    """
    config = EvolutionConfig(
        max_iterations=4,
        patience=2,
    )

    logger.info(
        "loop_agent_evolution.starting",
        workflow_name=workflow.name,
        loop_iterations=workflow.max_iterations,
        trainset_size=len(trainset),
        evolution_iterations=config.max_iterations,
    )

    # evolve_workflow() preserves the LoopAgent structure:
    # - max_iterations is maintained when cloning the workflow
    # - Each evaluation runs through all loop iterations
    # - Final iteration output is used for scoring
    result = await evolve_workflow(
        workflow=workflow,
        trainset=trainset,
        critic=critic,
        config=config,
    )

    logger.info(
        "loop_agent_evolution.complete",
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
    """Run the LoopAgent evolution example."""
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.loop_agent.start")

    try:
        # Create the refinement workflow
        refiner = create_refiner()
        refinement_loop = create_refinement_loop(refiner)

        # Verify the loop configuration
        logger.info(
            "loop_agent.config",
            workflow_name=refinement_loop.name,
            max_iterations=refinement_loop.max_iterations,
            sub_agents=[a.name for a in refinement_loop.sub_agents],
        )

        # Create the critic agent (scores output, NOT evolved)
        critic = create_critic()

        # Create training examples
        trainset = create_trainset()

        # Run evolution
        result = await run_loop_agent_evolution(refinement_loop, critic, trainset)

        # Display results
        print("\n" + "=" * 70)
        print("LOOPAGENT EVOLUTION RESULTS")
        print("=" * 70)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score:    {result.final_score:.3f}")
        print(f"Improvement:    {result.improvement:.2%}")
        print(f"Iterations:     {result.total_iterations}")
        print(f"Loop iterations per example: {refinement_loop.max_iterations}")

        print("\n" + "-" * 70)
        print("EVOLVED REFINER INSTRUCTION:")
        print("-" * 70)

        # In evolve_workflow(), evolved_components uses qualified names
        for qualified_name, instruction in result.evolved_components.items():
            print(f"\n>>> {qualified_name.upper()} <<<")
            print("-" * 70)
            safe_print(instruction)

        print("\n" + "=" * 70)
        logger.info("example.loop_agent.success")

    except Exception as e:
        logger.error("example.loop_agent.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

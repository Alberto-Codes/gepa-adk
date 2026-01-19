"""Example: Multi-agent evolution with SECRET scoring criteria.

This example demonstrates evolving a two-generator pipeline where:
1. Generator 1 creates initial content (starts with generic instructions)
2. Generator 2 expands on Generator 1's output using shared session state
3. A critic agent scores output based on a SECRET CRITERIA unknown to generators
4. A reflection agent improves generator instructions based on critic feedback

SECRET CRITERIA: The critic wants a RAW, VISCERAL, FIRST-PERSON writing style!
- The generators start with generic "be helpful" instructions
- The critic scores LOW if the writing is dry, clinical, or detached
- The critic gives feedback about voice, presence, and fearless observations
- Through evolution, generators should learn to write with raw immediacy

This creates a meaningful evolution scenario where improvement is visible:
- Initial scores will be LOW (generators produce dry, formal responses)
- Critic feedback describes what's missing: urgency, subjectivity, personal asides
- Reflection agent learns from feedback and updates instructions
- Final scores should be HIGHER (generators write with raw presence)

Key Concepts:
    - Multi-agent pipelines with shared session state via output_key
    - Separate critic agent with hidden scoring criteria
    - Reflection-based instruction improvement from feedback
    - Unified executor for consistent execution

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

from gepa_adk import (
    CriticOutput,
    EvolutionConfig,
    MultiAgentEvolutionResult,
    evolve_group,
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
# Pipeline Agents (These get evolved)
# -----------------------------------------------------------------------------
def create_generator1() -> LlmAgent:
    """Create the first generator agent.

    Generator 1 creates initial content based on the user's question.
    Its output is saved to session state via output_key so Generator 2
    can access it.

    Returns:
        LlmAgent configured for initial content generation.
    """
    return LlmAgent(
        name="generator1",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "You are a helpful assistant. Answer the user's question "
            "with a clear, informative response."
        ),
        output_key="gen1_output",  # Saves output to session.state["gen1_output"]
    )


def create_generator2() -> LlmAgent:
    """Create the second generator agent.

    Generator 2 expands on Generator 1's output using the {gen1_output}
    template to access shared session state. This creates a pipeline
    where content flows from Generator 1 → Generator 2.

    Returns:
        LlmAgent configured for content expansion.
    """
    return LlmAgent(
        name="generator2",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "You received this initial response:\n"
            "{gen1_output}\n\n"
            "Rewrite and expand this into a richer response with additional "
            "details, examples, and clarifications woven throughout."
        ),
        output_key="gen2_output",  # Final pipeline output
    )


# -----------------------------------------------------------------------------
# Critic Agent (Scores the pipeline output - NOT evolved)
# -----------------------------------------------------------------------------
def create_critic() -> LlmAgent:
    """Create a critic agent for scoring pipeline output.

    The critic is a SEPARATE agent that evaluates the quality of the
    pipeline's output. It is NOT part of the evolved pipeline - it only
    provides scores for the evolution process.

    IMPORTANT: The critic judges on a SECRET CRITERIA that the generators
    don't know about. This creates a meaningful evolution scenario where
    generators must learn from feedback to match the hidden criteria.

    SECRET CRITERIA: Raw, visceral, first-person writing with fearless
    observations and irreverent humor - like a fever dream dispatched
    from the edge of reality.

    Returns:
        LlmAgent configured as a quality critic with structured output.
    """
    return LlmAgent(
        name="fever_dream_critic",
        description=(
            "A literary critic who demands raw, visceral, first-person writing. "
            "Scores on voice, urgency, authenticity, and irreverence dimensions."
        ),
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "You are a literary critic who demands VISCERAL, ALIVE writing.\n\n"
            "You DESPISE dry, clinical, corporate prose. You want writing that\n"
            "GRABS you by the throat and drags you into the scene.\n\n"
            "## What You're Looking For:\n"
            "- **First-person immediacy**: 'I' statements, personal asides, being THERE\n"
            "- **Raw sensory detail**: What does it FEEL like? Taste like? Sound like?\n"
            "- **Fearless observations**: Say the uncomfortable truth. No hedging.\n"
            "- **Dark humor and hyperbole**: Absurdist comparisons, savage wit\n"
            "- **Urgency**: Write like the words are on fire. No filler. No padding.\n"
            "- **Subjectivity**: Strong opinions, personal stakes, emotional investment\n\n"
            "## Dimension Scores (0.0-1.0 each):\n"
            "- voice: Is there a distinct, personal voice? Or generic corporate drone?\n"
            "- urgency: Does it feel ALIVE and immediate? Or flat and distant?\n"
            "- authenticity: Does it feel REAL and honest? Or sanitized and safe?\n"
            "- irreverence: Does it take risks? Mock pretension? Or play it safe?\n\n"
            "## Scoring Guide:\n"
            "- 0.0-0.2: Corporate sludge. Sounds like a brochure. No soul.\n"
            "- 0.3-0.4: Some life, but still too cautious. Playing it safe.\n"
            "- 0.5-0.6: Glimpses of voice breaking through. Getting warmer.\n"
            "- 0.7-0.8: NOW we're talking. I can feel the writer in there.\n"
            "- 0.9-1.0: Electric. Unhinged in the best way. I'm THERE.\n\n"
            "## In Your Feedback:\n"
            "- Quote specific passages that work or don't work\n"
            "- Describe what's MISSING: 'Needs more personal stakes'\n"
            "- Give concrete alternatives: 'Instead of X, try something like Y'\n\n"
            "FORBIDDEN WORDS in your feedback: 'Hunter', 'Thompson', 'gonzo',\n"
            "'Fear and Loathing'. Describe the STYLE you want, never the author."
        ),
        output_schema=CriticOutput,
    )


# -----------------------------------------------------------------------------
# Reflection Agent (Improves instructions)
# -----------------------------------------------------------------------------
def create_reflection_agent() -> LlmAgent:
    """Create a reflection agent for instruction improvement.

    The reflection agent analyzes the critic's feedback and suggests
    improved instructions for the generator agents.

    CRITICAL: The instruction MUST use {component_text} and {trials}
    as template placeholders. ADK substitutes these from session state
    with the current instruction text and trial results (including
    critic feedback).

    Returns:
        LlmAgent configured for reflection and instruction improvement.
    """
    return LlmAgent(
        name="reflector",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "## Current Instruction\n"
            "{component_text}\n\n"
            "## Trial Results\n"
            "{trials}\n\n"
            "Based on the trial results above, write an improved instruction.\n"
            "Return ONLY the improved instruction text."
        ),
        output_key="proposed_component_text",
    )


# -----------------------------------------------------------------------------
# Training Data
# -----------------------------------------------------------------------------
def create_trainset() -> list[dict[str, Any]]:
    """Create training examples for evolution.

    Each example tests the pipeline with a different question.
    The critic scores based on SECRET CRITERIA (visceral, first-person style).

    These questions invite strong opinions and personal experience -
    perfect for developing a distinctive voice.
    """
    return [
        {"input": "What does it feel like to be truly exhausted?"},
        {"input": "Describe a moment when everything went wrong."},
        {"input": "What is the worst advice you've ever received?"},
    ]


# -----------------------------------------------------------------------------
# Evolution Runner
# -----------------------------------------------------------------------------
async def run_multi_agent_evolution(
    pipeline_agents: list[LlmAgent],
    critic: LlmAgent,
    reflection_agent: LlmAgent,
    trainset: list[dict[str, Any]],
) -> MultiAgentEvolutionResult:
    """Run evolutionary optimization on the multi-agent pipeline.

    The evolution process:
    1. Runs the pipeline (generator1 → generator2) on each training example
    2. The critic scores the final output (generator2's response)
    3. The reflection agent suggests improved instructions based on feedback
    4. Generator instructions are updated and the process repeats

    Both generator1 and generator2 instructions can be evolved, creating
    a trickle-down effect where improvements to generator1 also improve
    the input that generator2 receives.

    Args:
        pipeline_agents: Agents to evolve [generator1, generator2].
        critic: Separate critic agent for scoring (not evolved).
        reflection_agent: Agent for instruction improvement.
        trainset: Training examples for evolution.

    Returns:
        MultiAgentEvolutionResult with evolved instructions for all agents.
    """
    config = EvolutionConfig(
        max_iterations=6,  # More iterations for style evolution
        patience=3,
    )

    logger.info(
        "multi_agent_evolution.starting",
        pipeline_agents=[a.name for a in pipeline_agents],
        critic_agent=critic.name,
        trainset_size=len(trainset),
        max_iterations=config.max_iterations,
    )

    # evolve_group() with critic parameter:
    # - pipeline_agents are evolved (their instructions are optimized)
    # - critic scores the primary agent's output (generator2)
    # - reflection_agent improves instructions based on feedback
    result = await evolve_group(
        agents=pipeline_agents,
        primary="generator2",  # Score generator2's output (final pipeline output)
        trainset=trainset,
        critic=critic,  # Separate critic for scoring!
        reflection_agent=reflection_agent,
        config=config,
    )

    logger.info(
        "multi_agent_evolution.complete",
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
    """Run the multi-agent evolution example."""
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.multi_agent.start")

    try:
        # Create the pipeline agents (these get evolved)
        generator1 = create_generator1()
        generator2 = create_generator2()
        pipeline_agents = [generator1, generator2]

        # Create the critic agent (scores output, NOT evolved)
        critic = create_critic()

        # Create reflection agent (improves instructions)
        reflection_agent = create_reflection_agent()

        # Create training examples
        trainset = create_trainset()

        # Run evolution
        result = await run_multi_agent_evolution(
            pipeline_agents, critic, reflection_agent, trainset
        )

        # Display results
        print("\n" + "=" * 70)
        print("MULTI-AGENT EVOLUTION RESULTS")
        print("=" * 70)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score:    {result.final_score:.3f}")
        print(f"Improvement:    {result.improvement:.2%}")
        print(f"Iterations:     {result.total_iterations}")

        print("\n" + "-" * 70)
        print("EVOLVED GENERATOR INSTRUCTIONS:")
        print("-" * 70)

        for agent_name, instruction in result.evolved_components.items():
            print(f"\n>>> {agent_name.upper()} <<<")
            print("-" * 70)
            safe_print(instruction)

        print("\n" + "=" * 70)
        logger.info("example.multi_agent.success")

    except Exception as e:
        logger.error("example.multi_agent.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

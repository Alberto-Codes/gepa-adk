"""Example: Custom reflection prompt configuration.

This example demonstrates how to customize the reflection prompt used during
evolution to tailor the mutation strategy for your specific use case.

The reflection prompt is the template sent to the reflection model to generate
improved agent instructions. By customizing it, you can:
- Request specific output formats (e.g., JSON)
- Add domain-specific guidelines
- Use chain-of-thought reasoning
- Optimize for different model capabilities

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/custom_reflection_prompt.py
"""

from __future__ import annotations

import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, EvolutionResult, evolve_sync
from gepa_adk.engine.proposer import DEFAULT_PROMPT_TEMPLATE

# Configure structured logging
logger = structlog.get_logger()


class CriticOutput(BaseModel):
    """Structured output for critic evaluation.

    Attributes:
        score: Quality score (0.0-1.0).
        feedback: Detailed evaluation feedback.
    """

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall greeting quality score from 0.0 to 1.0",
    )
    feedback: str = Field(
        description="Detailed feedback explaining the score and suggestions for improvement",
    )


# -----------------------------------------------------------------------------
# Example 1: Minimal/Fast Prompt
# -----------------------------------------------------------------------------
# A concise prompt for quick iterations with capable models.

MINIMAL_PROMPT = """Instruction:
{input_text}

Feedback:
{input_feedback}

Improved instruction:"""


# -----------------------------------------------------------------------------
# Example 2: Chain-of-Thought Prompt
# -----------------------------------------------------------------------------
# A detailed prompt that encourages step-by-step reasoning.

CHAIN_OF_THOUGHT_PROMPT = """You are an expert at improving AI agent instructions.

## Current Instruction
{input_text}

## Performance Feedback
{input_feedback}

## Analysis Process
1. What patterns appear in successful examples (high scores)?
2. What patterns appear in failed examples (low scores)?
3. What specific changes would address the failures while preserving successes?

Think through each step carefully, then provide the improved instruction.

## Improved Instruction
"""


# -----------------------------------------------------------------------------
# Example 3: Domain-Specific Prompt (Code Review)
# -----------------------------------------------------------------------------
# A prompt tailored for a specific domain. This demonstrates the pattern for
# domain-specific prompts - not used in the comparison test below (which uses
# a greeting agent), but shows how you would structure prompts for other domains.

CODE_REVIEW_PROMPT = """You are improving a code review agent's instructions.

## Current Instruction
{input_text}

## Evaluation Feedback
{input_feedback}

## Domain Guidelines
- The agent should identify bugs, security issues, and style problems
- Feedback should be actionable and specific
- Code examples should be provided when suggesting fixes
- Tone should be constructive, not critical

Provide an improved instruction that addresses the feedback while
following these domain guidelines.

## Improved Instruction
"""


# -----------------------------------------------------------------------------
# Example 4: Extending the Default Prompt
# -----------------------------------------------------------------------------
# Add custom guidelines to the built-in default prompt.

EXTENDED_DEFAULT_PROMPT = (
    DEFAULT_PROMPT_TEMPLATE
    + """

## Additional Guidelines
- Focus on clarity and conciseness
- Preserve any safety constraints in the original instruction
- Consider edge cases mentioned in the feedback
- Keep the instruction under 200 words
"""
)


def create_agent() -> LlmAgent:
    """Create the agent to be evolved.

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
        instruction="""Evaluate the greeting quality. Consider:
- Formality and elegance appropriate to the social context
- Period-appropriate language (Charles Dickens style)
- Appropriateness for the title/honorific used
- Overall warmth and sincerity

Provide:
1. A score from 0.0 to 1.0 where 1.0 is a perfect formal greeting
2. Detailed feedback explaining your evaluation and suggestions for improvement

All scores must be between 0.0 and 1.0.""",
        output_schema=CriticOutput,
    )


def create_trainset() -> list[dict[str, Any]]:
    """Create training examples.

    Returns:
        List of training examples.
    """
    return [
        {"input": "I am His Majesty, the King."},
        {"input": "I am your mother."},
        {"input": "I am a close friend."},
    ]


def run_with_custom_prompt(
    agent: LlmAgent,
    critic: LlmAgent,
    trainset: list[dict[str, Any]],
    prompt_name: str,
    custom_prompt: str,
) -> EvolutionResult:
    """Run evolution with a custom reflection prompt.

    Args:
        agent: The agent to evolve.
        critic: The critic agent for scoring.
        trainset: Training examples.
        prompt_name: Name of the prompt for logging.
        custom_prompt: The custom reflection prompt template.

    Returns:
        EvolutionResult containing the evolved instruction and metrics.
    """
    config = EvolutionConfig(
        max_iterations=3,
        patience=2,
        reflection_prompt=custom_prompt,
    )

    logger.info(
        "evolution.starting",
        prompt_name=prompt_name,
        agent_name=agent.name,
    )

    # Create a fresh agent for each run
    fresh_agent = LlmAgent(
        name=agent.name,
        model=agent.model,
        instruction=agent.instruction,
    )

    result = evolve_sync(fresh_agent, trainset, critic=critic, config=config)

    logger.info(
        "evolution.complete",
        prompt_name=prompt_name,
        original_score=result.original_score,
        final_score=result.final_score,
        improvement=result.improvement,
    )

    return result


def main() -> None:
    """Run the custom reflection prompt examples."""
    # Check for Ollama API base
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.custom_reflection_prompt.start")

    # Create agent, critic, and training data
    agent = create_agent()
    critic = create_critic()
    trainset = create_trainset()

    # Define prompts to test
    prompts = [
        ("Default (None)", None),
        ("Minimal/Fast", MINIMAL_PROMPT),
        ("Chain-of-Thought", CHAIN_OF_THOUGHT_PROMPT),
        ("Extended Default", EXTENDED_DEFAULT_PROMPT),
    ]

    results: list[tuple[str, EvolutionResult]] = []

    for prompt_name, custom_prompt in prompts:
        print(f"\n{'=' * 60}")
        print(f"Testing: {prompt_name}")
        print("=" * 60)

        config = EvolutionConfig(
            max_iterations=3,
            patience=2,
            reflection_prompt=custom_prompt,
        )

        # Create a fresh agent for each run
        fresh_agent = LlmAgent(
            name=agent.name,
            model=agent.model,
            instruction=agent.instruction,
        )

        result = evolve_sync(fresh_agent, trainset, critic=critic, config=config)
        results.append((prompt_name, result))

        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score: {result.final_score:.3f}")
        print(f"Improvement: {result.improvement:.2%}")

    # Summary comparison
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"{'Prompt':<20} {'Original':>10} {'Final':>10} {'Improvement':>12}")
    print("-" * 60)
    for prompt_name, result in results:
        print(
            f"{prompt_name:<20} {result.original_score:>10.3f} "
            f"{result.final_score:>10.3f} {result.improvement:>11.2%}"
        )
    print("=" * 60)

    # Show the default prompt template for reference
    print("\n" + "-" * 60)
    print("DEFAULT_PROMPT_TEMPLATE (for reference):")
    print("-" * 60)
    print(
        DEFAULT_PROMPT_TEMPLATE[:500] + "..."
        if len(DEFAULT_PROMPT_TEMPLATE) > 500
        else DEFAULT_PROMPT_TEMPLATE
    )

    logger.info("example.custom_reflection_prompt.success")


if __name__ == "__main__":
    main()

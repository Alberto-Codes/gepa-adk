"""Example: Sandwich evolution with nested workflow structure preservation.

This example demonstrates evolving agents within a nested workflow where:
1. A ParallelAgent runs 4 ingredient agents concurrently (bread, meat, veggie, cheese)
2. A SequentialAgent chains the parallel ingredients to an assembler
3. The assembler creates a sandwich with BUILD notation, NAME, and MENU description
4. A biased critic secretly prefers patty melts and gives directional feedback
5. Evolution converges the ingredients toward a patty melt

Key Concepts:
    - ParallelAgent structure preservation (concurrent ingredient generation)
    - SequentialAgent structure preservation (ingredients -> assembly)
    - Nested workflow cloning during evolution
    - Biased critic guiding evolution toward a hidden preference
    - Multi-component evolution with round_robin

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/sandwich_evolution.py
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
# Model Configuration
# -----------------------------------------------------------------------------
MODEL = "ollama_chat/llama3.2:latest"


# -----------------------------------------------------------------------------
# Ingredient Agents (run in parallel)
# -----------------------------------------------------------------------------
def create_bread_agent() -> LlmAgent:
    """Create the bread ingredient agent."""
    return LlmAgent(
        name="bread",
        model=LiteLlm(model=MODEL),
        instruction=(
            "Suggest a type of bread for a sandwich. "
            "Just output the bread name and basic style (e.g., 'sourdough, sliced thick'). "
            "Keep it short - just the bread."
        ),
        output_key="bread",
    )


def create_meat_agent() -> LlmAgent:
    """Create the meat/protein ingredient agent."""
    return LlmAgent(
        name="meat",
        model=LiteLlm(model=MODEL),
        instruction=(
            "Suggest a meat or protein for a sandwich. "
            "Just output the meat name and basic prep (e.g., 'turkey, sliced thin'). "
            "Keep it short - just the protein."
        ),
        output_key="meat",
    )


def create_veggie_agent() -> LlmAgent:
    """Create the vegetable ingredient agent."""
    return LlmAgent(
        name="veggie",
        model=LiteLlm(model=MODEL),
        instruction=(
            "Suggest a vegetable topping for a sandwich. "
            "Just output the veggie name and prep (e.g., 'lettuce, shredded'). "
            "Keep it short - just the vegetable."
        ),
        output_key="veggie",
    )


def create_cheese_agent() -> LlmAgent:
    """Create the cheese ingredient agent."""
    return LlmAgent(
        name="cheese",
        model=LiteLlm(model=MODEL),
        instruction=(
            "Suggest a cheese for a sandwich. "
            "Just output the cheese name (e.g., 'cheddar' or 'swiss'). "
            "Keep it short - just the cheese."
        ),
        output_key="cheese",
    )


# -----------------------------------------------------------------------------
# Workflow Construction
# -----------------------------------------------------------------------------
def create_ingredient_station() -> ParallelAgent:
    """Create the parallel agent that generates all ingredients concurrently.

    The ParallelAgent runs all 4 ingredient agents at the same time,
    storing their outputs in session state with their output_keys.
    """
    return ParallelAgent(
        name="IngredientStation",
        sub_agents=[
            create_bread_agent(),
            create_meat_agent(),
            create_veggie_agent(),
            create_cheese_agent(),
        ],
    )


def create_assembler() -> LlmAgent:
    """Create the sandwich assembler agent.

    Takes the ingredients from session state and creates a sandwich
    with BUILD notation, NAME, and MENU description.
    """
    return LlmAgent(
        name="assembler",
        model=LiteLlm(model=MODEL),
        instruction="""You are a sandwich chef. Given these ingredients:
- Bread: {bread}
- Meat: {meat}
- Veggie: {veggie}
- Cheese: {cheese}

Create a sandwich. Output in this exact format:

BUILD: [bread, prep] -> [protein, prep] -> [veggie, prep] -> [cheese, prep] -> [bread, prep]
NAME: [creative sandwich name]
MENU: [one sentence menu description]""",
        output_key="sandwich_result",
    )


def create_sandwich_shop() -> SequentialAgent:
    """Create the full sandwich shop workflow.

    SequentialAgent that:
    1. Runs IngredientStation (ParallelAgent) to generate all ingredients
    2. Runs Assembler to combine ingredients into a sandwich

    This nested structure (Sequential containing Parallel) is preserved
    during evolution - the ParallelAgent always runs concurrently.
    """
    return SequentialAgent(
        name="SandwichShop",
        sub_agents=[
            create_ingredient_station(),
            create_assembler(),
        ],
    )


# -----------------------------------------------------------------------------
# Patty Melt Critic (Biased toward patty melts)
# -----------------------------------------------------------------------------
def create_patty_melt_critic() -> LlmAgent:
    """Create a critic that secretly prefers patty melts.

    The critic scores based on how close the sandwich is to a classic patty melt:
    - Rye bread, grilled with butter
    - Beef patty
    - Caramelized/grilled onions
    - American or Swiss cheese, melted

    IMPORTANT: The critic never says "patty melt" - just gives hints.
    """
    return LlmAgent(
        name="patty_melt_critic",
        model=LiteLlm(model=MODEL),
        instruction="""You are a sandwich critic with a SECRET preference. Your ideal sandwich has:
- Rye bread, grilled with butter until golden
- A beef patty, well-seasoned
- Caramelized or grilled onions
- American or Swiss cheese, melted

Score sandwiches 0.0-1.0 based on how close they match YOUR ideal.

CRITICAL RULES:
1. NEVER mention "patty melt" in your feedback
2. Give subtle hints toward your preference without revealing it
3. Be encouraging but guide them toward your ideal

Hint examples (adapt to what's wrong):
- Wrong bread: "A darker, heartier bread that grills beautifully would elevate this"
- Wrong meat: "Consider a classic formed beef preparation"
- Wrong veggie: "Savory, caramelized alliums would add depth"
- Wrong cheese: "A classic American diner cheese that melts smoothly"

Score guide:
- 0.9-1.0: Matches your ideal closely
- 0.6-0.8: Has some right elements
- 0.3-0.5: Generic sandwich, needs guidance
- 0.1-0.2: Completely different direction""",
        output_schema=CriticOutput,
    )


# -----------------------------------------------------------------------------
# Training Data
# -----------------------------------------------------------------------------
def create_trainset() -> list[dict[str, Any]]:
    """Create training examples for evolution.

    Simple prompts asking for a sandwich - the ingredient agents
    will generate different combinations each time.
    """
    return [
        {"input": "Make me a delicious sandwich."},
        {"input": "I'd like a satisfying sandwich please."},
        {"input": "Create a tasty sandwich for lunch."},
    ]


# -----------------------------------------------------------------------------
# Evolution Runner
# -----------------------------------------------------------------------------
async def run_sandwich_evolution(
    workflow: SequentialAgent,
    critic: LlmAgent,
    trainset: list[dict[str, Any]],
) -> MultiAgentEvolutionResult:
    """Run evolutionary optimization on the sandwich shop workflow.

    The evolution process:
    1. Each example runs through the full workflow (parallel ingredients -> assembly)
    2. The critic scores the assembled sandwich
    3. Reflection proposes improved instructions for ingredient agents
    4. Instructions evolve to converge toward the critic's hidden preference

    With round_robin=True, all ingredient agents get evolved over iterations.
    """
    config = EvolutionConfig(
        max_iterations=12,
        patience=4,
    )

    logger.info(
        "sandwich_evolution.starting",
        workflow_name=workflow.name,
        trainset_size=len(trainset),
        evolution_iterations=config.max_iterations,
    )

    result = await evolve_workflow(
        workflow=workflow,
        trainset=trainset,
        critic=critic,
        config=config,
        round_robin=True,  # Evolve all ingredient agents
    )

    logger.info(
        "sandwich_evolution.complete",
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
    """Run the sandwich evolution example."""
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.sandwich.start")

    try:
        # Create the sandwich shop workflow
        sandwich_shop = create_sandwich_shop()

        # Log the workflow structure
        ingredient_station = sandwich_shop.sub_agents[0]
        logger.info(
            "sandwich_shop.config",
            workflow_name=sandwich_shop.name,
            workflow_type="SequentialAgent",
            sub_workflows=[
                {
                    "name": ingredient_station.name,
                    "type": "ParallelAgent",
                    "agents": [a.name for a in ingredient_station.sub_agents],
                },
                {"name": "assembler", "type": "LlmAgent"},
            ],
        )

        # Create the biased critic
        critic = create_patty_melt_critic()

        # Create training examples
        trainset = create_trainset()

        # Store original instructions for comparison
        # Note: sub_agents typed as BaseAgent but these are LlmAgent instances
        ingredient_station = sandwich_shop.sub_agents[0]
        originals = {
            "bread.instruction": ingredient_station.sub_agents[0].instruction,  # type: ignore[union-attr]
            "meat.instruction": ingredient_station.sub_agents[1].instruction,  # type: ignore[union-attr]
            "veggie.instruction": ingredient_station.sub_agents[2].instruction,  # type: ignore[union-attr]
            "cheese.instruction": ingredient_station.sub_agents[3].instruction,  # type: ignore[union-attr]
            "assembler.instruction": sandwich_shop.sub_agents[1].instruction,  # type: ignore[union-attr]
        }

        # Run evolution
        result = await run_sandwich_evolution(sandwich_shop, critic, trainset)

        # Display results
        print("\n" + "=" * 70)
        print("SANDWICH EVOLUTION RESULTS")
        print("=" * 70)

        # Score history
        print("\nSCORE PROGRESSION:")
        print("-" * 40)
        for record in result.iteration_history:
            status = "ACCEPTED" if record.accepted else "rejected"
            print(
                f"  Iter {record.iteration_number}: {record.score:.2f} "
                f"({record.evolved_component}) [{status}]"
            )

        print(f"\nIterations run: {result.total_iterations}")

        # Compare original vs evolved
        print("\n" + "-" * 70)
        print("INSTRUCTION COMPARISON (original -> evolved):")
        print("-" * 70)

        for name, evolved in result.evolved_components.items():
            original = originals.get(name, "")
            changed = original.strip() != evolved.strip()
            marker = "CHANGED" if changed else "unchanged"

            print(f"\n>>> {name.upper()} [{marker}] <<<")
            if changed:
                print(
                    "ORIGINAL:",
                    original[:80] + "..." if len(original) > 80 else original,
                )
                print(
                    "EVOLVED: ", evolved[:80] + "..." if len(evolved) > 80 else evolved
                )
            else:
                print("(no change)")

        print("\n" + "=" * 70)
        print("Goal: Watch ingredients evolve toward a PATTY MELT!")
        print("(rye bread, beef patty, caramelized onions, american cheese)")
        print("=" * 70)

        logger.info("example.sandwich.success")

    except Exception as e:
        logger.error("example.sandwich.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

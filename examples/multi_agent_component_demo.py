"""Example: Per-agent component evolution with multi-agent pipelines.

This example demonstrates the v0.3 per-agent component configuration feature:
1. Create a three-agent pipeline (planner, implementer, validator)
2. Configure different components to evolve for each agent
3. Exclude specific agents from evolution while keeping them in the pipeline
4. Access evolved components via qualified names

Key Concepts:
    - Dict-based agent configuration (v0.3 API)
    - Per-agent component configuration via `components` parameter
    - Qualified component names (agent.component format per ADR-012)
    - Excluding agents from evolution with empty component lists

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - GOOGLE_API_KEY environment variable set for Gemini

Usage:
    python examples/multi_agent_component_demo.py
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from gepa_adk import (
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
# Output Schemas
# -----------------------------------------------------------------------------
class PlanOutput(BaseModel):
    """Schema for planner output."""

    steps: list[str] = Field(description="Ordered list of implementation steps")
    approach: str = Field(description="Overall approach description")


class ValidationOutput(BaseModel):
    """Schema for validator output with scoring."""

    is_valid: bool = Field(description="Whether the implementation is valid")
    feedback: str = Field(description="Validation feedback")
    score: float = Field(ge=0.0, le=1.0, description="Quality score")


# -----------------------------------------------------------------------------
# Pipeline Agents
# -----------------------------------------------------------------------------
def create_planner() -> LlmAgent:
    """Create the planner agent.

    The planner creates a high-level implementation plan that the
    implementer will use. Its output is saved to session state.
    """
    return LlmAgent(
        name="planner",
        model="gemini-2.5-flash",
        instruction=(
            "Create a clear, step-by-step implementation plan for the task. "
            "Be specific about the approach and key considerations."
        ),
        output_key="plan",  # Saves output to session.state["plan"]
    )


def create_implementer() -> LlmAgent:
    """Create the implementer agent.

    The implementer uses the planner's output via {plan} template to
    create the actual implementation.
    """
    return LlmAgent(
        name="implementer",
        model="gemini-2.5-flash",
        instruction=(
            "Based on this plan:\n"
            "{plan}\n\n"
            "Create the implementation. Be thorough and follow the plan's steps."
        ),
        output_key="implementation",  # Saves to session.state["implementation"]
    )


def create_validator() -> LlmAgent:
    """Create the validator agent.

    The validator reviews the implementation and provides a score.
    This is the primary agent whose output is used for scoring.
    """
    return LlmAgent(
        name="validator",
        model="gemini-2.5-flash",
        instruction=(
            "Review this implementation:\n"
            "{implementation}\n\n"
            "Evaluate correctness, completeness, and quality. "
            "Provide specific feedback and a score from 0.0 to 1.0."
        ),
        output_schema=ValidationOutput,  # Structured output for scoring
    )


# -----------------------------------------------------------------------------
# Training Data
# -----------------------------------------------------------------------------
def create_trainset() -> list[dict[str, Any]]:
    """Create training examples for evolution."""
    return [
        {"input": "Create a Python function to calculate factorial recursively."},
        {"input": "Create a Python function to reverse a string without slicing."},
    ]


# -----------------------------------------------------------------------------
# Evolution with Per-Agent Components
# -----------------------------------------------------------------------------
async def run_per_agent_evolution() -> MultiAgentEvolutionResult:
    """Demonstrate per-agent component evolution.

    This example shows:
    1. Creating agents as a dict (v0.3 API)
    2. Configuring different components per agent
    3. Excluding the implementer from evolution (it follows the plan)
    """
    # Create agents as dict (v0.3 API)
    agents = {
        "planner": create_planner(),
        "implementer": create_implementer(),
        "validator": create_validator(),
    }

    # Per-agent component configuration
    # - Planner: evolve instruction to improve planning
    # - Implementer: excluded (empty list) - follows the plan, doesn't need evolution
    # - Validator: evolve instruction to improve evaluation criteria
    components = {
        "planner": ["instruction"],
        "implementer": [],  # Empty list excludes from evolution
        "validator": ["instruction"],
    }

    trainset = create_trainset()

    config = EvolutionConfig(
        max_iterations=3,
        patience=2,
    )

    logger.info(
        "per_agent_evolution.starting",
        agents=list(agents.keys()),
        components=components,
        trainset_size=len(trainset),
    )

    result = await evolve_group(
        agents=agents,
        primary="validator",  # Score based on validator output
        trainset=trainset,
        components=components,  # Per-agent configuration
        config=config,
    )

    logger.info(
        "per_agent_evolution.complete",
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
    """Run the per-agent component evolution example."""
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY environment variable required")

    logger.info("example.per_agent_components.start")

    try:
        result = await run_per_agent_evolution()

        # Display results
        print("\n" + "=" * 70)
        print("PER-AGENT COMPONENT EVOLUTION RESULTS")
        print("=" * 70)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score:    {result.final_score:.3f}")
        print(f"Improvement:    {result.improvement:.2%}")
        print(f"Iterations:     {result.total_iterations}")

        print("\n" + "-" * 70)
        print("EVOLVED COMPONENTS (qualified names):")
        print("-" * 70)

        # Access evolved components via qualified names (agent.component format)
        for qualified_name, value in result.evolved_components.items():
            print(f"\n>>> {qualified_name} <<<")
            print("-" * 70)
            safe_print(
                str(value)[:500] + "..." if len(str(value)) > 500 else str(value)
            )

        # Note: implementer has no evolved components (excluded)
        implementer_components = [
            k for k in result.evolved_components if k.startswith("implementer.")
        ]
        if not implementer_components:
            print("\n>>> implementer (excluded from evolution) <<<")
            print("-" * 70)
            print(
                "No evolved components - implementer was excluded via empty component list"
            )

        print("\n" + "=" * 70)
        logger.info("example.per_agent_components.success")

    except Exception as e:
        logger.error("example.per_agent_components.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

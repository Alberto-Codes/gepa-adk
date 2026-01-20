"""Example: Validated Output Schema Evolution.

This example demonstrates evolving a Pydantic output schema with automatic
validation. The schema reflection agent uses the validate_output_schema tool
to self-correct syntax errors, reducing wasted evolution iterations.

The evolution process automatically selects a component-aware reflection agent
when evolving output_schema components. This agent validates proposed schemas
before returning them, ensuring only syntactically valid schemas reach the
evolution engine.

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/schema_evolution_validated.py
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, EvolutionResult, evolve
from gepa_adk.utils import EncodingSafeProcessor

# -----------------------------------------------------------------------------
# Console Output Encoding
# -----------------------------------------------------------------------------
_encoding_processor = EncodingSafeProcessor()


def safe_print(text: str) -> None:
    """Print text safely on Windows consoles with cp1252 encoding.

    Args:
        text: Text to print, may contain Unicode characters.
    """
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


class TaskOutput(BaseModel):
    """Initial output schema for task completion (to be evolved).

    This schema is intentionally basic and will be evolved during the
    optimization process to improve its structure and fields.
    """

    result: str


class CriticOutput(BaseModel):
    """Structured output for critic evaluation.

    This schema is used by the critic agent to provide structured scoring
    feedback during schema evolution.
    """

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality score based on schema completeness",
    )
    feedback: str = Field(description="Detailed feedback on schema quality")


# -----------------------------------------------------------------------------
# Agent Creation
# -----------------------------------------------------------------------------


def create_agent() -> LlmAgent:
    """Create the task agent with a basic output schema to be evolved.

    Returns:
        LlmAgent configured with a basic output schema that needs improvement.
    """
    return LlmAgent(
        name="task_agent",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="""Complete the given task and provide structured output.
Include your reasoning and a confidence score.""",
        output_schema=TaskOutput,
    )


def create_critic() -> LlmAgent:
    """Create a critic agent for evaluating schema quality.

    The critic evaluates whether the output schema captures all necessary
    information from the task completion.

    Returns:
        LlmAgent configured as a critic for evaluating schema completeness.
    """
    return LlmAgent(
        name="schema_critic",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="""Evaluate the quality of the task output schema.

A good schema should:
1. Capture the task result clearly
2. Include reasoning or explanation
3. Provide a confidence or quality score (0.0-1.0)
4. Have clear field descriptions
5. Use appropriate field types and constraints

Score 1.0 if the schema has all these elements with proper Pydantic features.
Score lower if fields are missing, poorly named, or lack constraints.""",
        output_schema=CriticOutput,
    )


# -----------------------------------------------------------------------------
# Training Data
# -----------------------------------------------------------------------------


def create_trainset() -> list[dict[str, Any]]:
    """Create training examples for schema evolution.

    Returns:
        List of training examples with different task types.
    """
    return [
        {"input": "Summarize this article: Python is a programming language."},
        {"input": "Translate to French: Hello, how are you?"},
        {"input": "Solve the equation: 2x + 5 = 15"},
        {"input": "Write a haiku about nature."},
    ]


# -----------------------------------------------------------------------------
# Evolution
# -----------------------------------------------------------------------------


async def run_schema_evolution(
    agent: LlmAgent,
    critic: LlmAgent,
    trainset: list[dict[str, Any]],
) -> EvolutionResult:
    """Run evolutionary optimization on the output schema.

    This evolves the output_schema component specifically, triggering
    automatic selection of the schema reflection agent with validation tools.

    Args:
        agent: The task agent with schema to evolve.
        critic: The critic agent for schema evaluation.
        trainset: Training examples for evolution.

    Returns:
        EvolutionResult containing the evolved schema and metrics.

    Note:
        When components=["output_schema"] is specified, gepa-adk automatically
        uses a schema reflection agent equipped with the validate_output_schema
        tool. This agent validates proposed schemas before returning them,
        reducing wasted iterations on syntactically invalid proposals.
    """
    config = EvolutionConfig(
        max_iterations=5,
        patience=2,
        # reflection_model can be customized for the reflection agent
        # Default: "ollama_chat/gpt-oss:20b"
        # Examples: "gemini/gemini-2.0-flash", "anthropic/claude-3-haiku"
    )

    logger.info(
        "schema_evolution.starting",
        agent_name=agent.name,
        trainset_size=len(trainset),
        max_iterations=config.max_iterations,
        component="output_schema",
    )

    # Evolve the output_schema component
    # This automatically uses the schema reflection agent with validation tools
    result = await evolve(
        agent,
        trainset,
        critic=critic,
        config=config,
        components=["output_schema"],  # Target schema for evolution
    )

    logger.info(
        "schema_evolution.complete",
        original_score=result.original_score,
        final_score=result.final_score,
        improvement=result.improvement,
        total_iterations=result.total_iterations,
    )

    return result


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


async def main() -> None:
    """Run the validated schema evolution example."""
    # Check for Ollama API base
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.schema_evolution_validated.start")

    try:
        # Create agent, critic, and training data
        agent = create_agent()
        critic = create_critic()
        trainset = create_trainset()

        # Display original schema
        from gepa_adk.utils.schema_utils import serialize_pydantic_schema

        original_schema = serialize_pydantic_schema(agent.output_schema)
        print("\n" + "=" * 60)
        print("ORIGINAL OUTPUT SCHEMA")
        print("=" * 60)
        safe_print(original_schema)

        # Run schema evolution with automatic validation
        result = await run_schema_evolution(agent, critic, trainset)

        # Display results
        print("\n" + "=" * 60)
        print("SCHEMA EVOLUTION RESULTS")
        print("=" * 60)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score: {result.final_score:.3f}")
        print(f"Improvement: {result.improvement:.2%}")
        print(f"Iterations: {result.total_iterations}")
        print("\n" + "-" * 60)
        print("EVOLVED OUTPUT SCHEMA:")
        print("-" * 60)
        safe_print(result.evolved_components["output_schema"])
        print("=" * 60)
        print("\nNOTE: The evolved schema was automatically validated during")
        print("reflection using the validate_output_schema tool. All returned")
        print("proposals are guaranteed to be syntactically valid Pydantic schemas.")
        print("=" * 60)

        logger.info("example.schema_evolution_validated.success")

    except Exception as e:
        logger.error("example.schema_evolution_validated.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

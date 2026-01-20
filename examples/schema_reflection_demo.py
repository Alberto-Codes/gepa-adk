"""Example: Schema Reflection with Validation.

This example demonstrates evolving a content generator agent using the
schema reflection agent, which validates proposed schemas before returning them.

Scenario:
- Generator: Uses a simple output schema (just "response" field)
- Critic: Evaluates outputs, looking for reasoning, confidence, and key points
- Evolution: Improves the generator's instruction based on critic feedback

The schema reflection agent has a validate_output_schema tool that catches
syntax errors early, preventing wasted evolution iterations.

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - Ollama running locally (uses .env for OLLAMA_API_BASE)

Usage:
    python examples/schema_reflection_demo.py
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, evolve
from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA
from gepa_adk.engine.reflection_agents import SCHEMA_REFLECTION_INSTRUCTION
from gepa_adk.utils import EncodingSafeProcessor
from gepa_adk.utils.schema_tools import validate_output_schema

# -----------------------------------------------------------------------------
# Console Output Encoding (Windows compatibility)
# -----------------------------------------------------------------------------
_encoding_processor = EncodingSafeProcessor()


def safe_print(text: str) -> None:
    """Print text safely on Windows consoles."""
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


# =============================================================================
# Output Schemas
# =============================================================================


class SimpleResponse(BaseModel):
    """Initial simple schema - just a response field.

    This is intentionally basic. The critic will score lower because outputs
    lack structure like reasoning and confidence.
    """

    response: str = Field(description="The response text")


class CriticOutput(BaseModel):
    """Critic evaluation output."""

    score: float = Field(ge=0.0, le=1.0, description="Quality score")
    feedback: str = Field(description="Feedback for improvement")


# =============================================================================
# Agent Factories
# =============================================================================


def _get_model() -> LiteLlm:
    """Get LLM model - uses Ollama."""
    return LiteLlm(model="ollama_chat/gpt-oss:20b")


def create_generator() -> LlmAgent:
    """Create the content generator agent.

    Uses SimpleResponse schema - the instruction will be evolved to produce
    better structured outputs.
    """
    return LlmAgent(
        name="content_generator",
        model=_get_model(),
        instruction="""Answer the question. Provide a clear response.""",
        output_schema=SimpleResponse,
    )


def create_critic() -> LlmAgent:
    """Create the critic agent.

    Evaluates outputs looking for:
    - Clear main response
    - Reasoning/explanation
    - Confidence indication
    - Structured key points
    """
    return LlmAgent(
        name="output_critic",
        model=_get_model(),
        instruction="""Evaluate the response quality. Look for:

1. Clear main response (required)
2. Reasoning or explanation (highly valuable)
3. Confidence indication (valuable)
4. Key points or structure (valuable for complex topics)

Score from 0.0 to 1.0:
- 0.9-1.0: Well-structured with reasoning and key points
- 0.6-0.8: Good response with some structure
- 0.3-0.5: Basic response, lacks explanation
- 0.0-0.2: Poor or unclear response

Provide specific feedback about how to improve the response structure.""",
        output_schema=CriticOutput,
    )


def create_schema_reflector() -> LlmAgent:
    """Create the schema reflection agent with validation tool.

    This agent can validate proposed Pydantic schemas before returning them,
    reducing wasted iterations on invalid syntax.

    Note:
        Uses LiteLlm wrapper for Ollama compatibility. The standard
        create_schema_reflection_agent() factory uses string model names
        which work with Gemini but require LiteLlm for other providers.
    """
    return LlmAgent(
        name="schema_reflector",
        model=_get_model(),
        instruction=SCHEMA_REFLECTION_INSTRUCTION,
        tools=[FunctionTool(validate_output_schema)],
        output_key="proposed_component_text",
    )


def create_trainset() -> list[dict[str, Any]]:
    """Create training examples."""
    return [
        {"input": "What are the benefits of regular exercise?"},
        {"input": "Explain how solar panels work."},
        {"input": "What should I consider when adopting a pet?"},
    ]


# =============================================================================
# Main
# =============================================================================


async def main() -> None:
    """Run the schema reflection evolution demo."""
    print()
    print("=" * 60)
    print("SCHEMA REFLECTION DEMO")
    print("Feature: 142-component-aware-reflection")
    print("=" * 60)
    print()
    print("This demo evolves a content generator agent using schema")
    print("reflection with validation. The reflection agent validates")
    print("proposed schemas before accepting them.")
    print()

    # Create agents
    generator = create_generator()
    critic = create_critic()
    schema_reflector = create_schema_reflector()
    trainset = create_trainset()

    print(f"Generator: {generator.name}")
    print(f"  Schema: {generator.output_schema.__name__}")
    print(f"Critic: {critic.name}")
    print(f"Reflection agent: {schema_reflector.name}")
    print(f"  Has validation tool: {schema_reflector.tools is not None}")
    print(f"Training examples: {len(trainset)}")
    print(f"Component to evolve: {COMPONENT_OUTPUT_SCHEMA}")

    print()
    print("-" * 60)
    print("Starting evolution...")
    print("-" * 60)

    config = EvolutionConfig(
        max_iterations=3,
        patience=2,
    )

    try:
        result = await evolve(
            agent=generator,
            trainset=trainset,
            critic=critic,
            reflection_agent=schema_reflector,
            config=config,
            components=[COMPONENT_OUTPUT_SCHEMA],  # Evolve the output_schema
        )

        print()
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score: {result.final_score:.3f}")
        print(f"Improvement: {result.improvement:+.1%}")
        print(f"Iterations: {result.total_iterations}")

        print()
        print("-" * 60)
        print("EVOLVED OUTPUT SCHEMA:")
        print("-" * 60)
        safe_print(result.evolved_components.get(COMPONENT_OUTPUT_SCHEMA, "N/A"))
        print("-" * 60)

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        logger.exception("evolution_failed")


if __name__ == "__main__":
    asyncio.run(main())

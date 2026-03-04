"""Example: Schema Reflection with Validation.

Demonstrates evolving a generator's OUTPUT SCHEMA to improve scores.
The schema reflection agent uses validate_output_schema tool to verify
proposed schemas are syntactically valid before evaluation.

Key Insight:
    LLMs fill ALL fields in their output_schema. If the schema has `reasoning: str`,
    the generator produces reasoning. If not, it doesn't. This means evolving
    the schema directly affects what the generator produces.

Scenario:
- Generator: Uses a SIMPLE schema with just "response" field
- Critic: HARSHLY scores based on JSON structure (not content quality)
- Evolution: Schema reflection proposes richer schemas with more fields
- Result: Generator fills new fields, critic gives higher scores

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - Ollama running locally (uses .env for OLLAMA_API_BASE)

Examples:
    Run the demo:

    ```python
    python examples/schema_reflection_demo.py
    ```

See Also:
    - [`reflection_agents`][gepa_adk.adapters.agents.reflection_agents]:
      Reflection agent factories.
    - [`gepa_adk.utils.schema_tools`][gepa_adk.utils.schema_tools]: Schema validation tools.
    - [`gepa_adk.domain.types`][gepa_adk.domain.types]: Component type constants.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, evolve
from gepa_adk.adapters.agents.reflection_agents import SCHEMA_REFLECTION_INSTRUCTION
from gepa_adk.domain.types import COMPONENT_OUTPUT_SCHEMA
from gepa_adk.utils import EncodingSafeProcessor
from gepa_adk.utils.schema_tools import validate_output_schema

load_dotenv()

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

    Examples:
        ```python
        resp = SimpleResponse(response="Hello world")
        ```
    """

    response: str = Field(description="The response text")


class CriticOutput(BaseModel):
    """Critic evaluation output.

    Examples:
        ```python
        output = CriticOutput(score=0.8, feedback="Good structure")
        ```
    """

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

    HARSH scoring based on structural elements in the JSON output.
    The critic examines the actual JSON fields present, not just content quality.
    This incentivizes schema evolution to add fields like reasoning, confidence.
    """
    return LlmAgent(
        name="output_critic",
        model=_get_model(),
        instruction="""You are a STRICT structural evaluator. Examine the JSON response structure.

Score STRICTLY based on what JSON fields are present in the output:

- 0.1-0.2: Only has a "response" field with plain text. NO other structural fields.
- 0.3-0.4: Has response + ONE additional field (like reasoning OR confidence)
- 0.5-0.6: Has response + TWO additional fields (reasoning AND confidence)
- 0.7-0.8: Has response + reasoning + confidence + one more (key_points, sources, etc.)
- 0.9-1.0: Comprehensive structure with 4+ meaningful fields

IMPORTANT: Be HARSH. If the JSON output only contains a single "response" field
with no structured reasoning, confidence scores, or key points fields,
the score MUST be 0.1-0.2. Do NOT give high scores for good content
if the STRUCTURE is missing fields.

In your feedback, explicitly list what structural fields are MISSING that would
improve the score (e.g., "Missing: reasoning, confidence, key_points fields").""",
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
    print("Goal: Evolve the generator's OUTPUT SCHEMA to improve scores.")
    print()
    print("How it works:")
    print("  1. Generator has simple schema: just 'response' field")
    print("  2. Critic HARSHLY scores based on JSON structure:")
    print("     - Only 'response' = 0.1-0.2 (FAIL)")
    print("     - +reasoning, +confidence = higher scores")
    print("  3. Schema evolution proposes richer schemas")
    print("  4. Generator fills new fields -> scores improve")
    print()

    # Create agents
    generator = create_generator()
    critic = create_critic()
    schema_reflector = create_schema_reflector()
    trainset = create_trainset()

    print(f"Generator: {generator.name}")
    schema = generator.output_schema
    print(f"  Schema: {schema.__name__ if schema else None}")
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

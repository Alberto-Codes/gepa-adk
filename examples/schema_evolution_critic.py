"""Example: Output Schema Evolution via Critic Feedback.

This example demonstrates evolving an agent's output_schema based on critic
feedback. The summarizer agent starts with a minimal schema (just 'summary'),
but the critic expects comprehensive analysis. GEPA evolves the schema to
match expectations.

**Session Persistence:**

This example uses DatabaseSessionService with SQLite to persist all sessions
and events. After running, you can explore the database to see the full
history of agent executions, reflection proposals, and evolution progress.

**Unified Execution Path:**

This example uses the AsyncGEPAEngine directly (not the evolve() API) to
demonstrate multi-component candidates. The unified AgentExecutor ensures
consistent session management across the generator, critic, and reflection
agents even when using the engine directly.

The Pattern:
    - Basic example: Agent doesn't know Dickens style -> critic feedback
      shapes instruction evolution
    - This example: Agent has minimal schema -> critic feedback shapes
      output_schema evolution

Key Insight:
    The summarizer doesn't know its schema is lacking. The critic's feedback
    ("missing key points", "no sentiment", "needs confidence score") drives
    GEPA to propose schema mutations that add these fields.

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/schema_evolution_critic.py

After running, explore the SQLite database:
    sqlite3 data/schema_evolution.db "SELECT COUNT(*) FROM sessions;"
    sqlite3 data/schema_evolution.db "SELECT DISTINCT json_extract(event_data, '$.author') FROM events;"
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
from pathlib import Path
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import DatabaseSessionService
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig
from gepa_adk.adapters import AgentExecutor, CriticScorer
from gepa_adk.adapters.adk_adapter import ADKAdapter
from gepa_adk.domain.models import Candidate, EvolutionResult
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.utils import EncodingSafeProcessor
from gepa_adk.utils.schema_utils import serialize_pydantic_schema

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


# =============================================================================
# Output Schemas
# =============================================================================


class MinimalSummary(BaseModel):
    """Minimal output schema - just a summary.

    This intentionally lacking schema will be evolved based on critic feedback.
    The summarizer doesn't know it needs more fields - the critic will guide
    the evolution toward a richer schema.
    """

    summary: str = Field(description="Brief summary of the article")


class CriticOutput(BaseModel):
    """Structured output for critic evaluation.

    The critic expects comprehensive analysis and will penalize outputs
    that lack key_points, sentiment, confidence, etc. - even though the
    generator's schema doesn't have these fields yet.
    """

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality assessment score",
    )
    feedback: str = Field(
        description="Detailed feedback on what's missing or could be improved"
    )


# =============================================================================
# Agent Creation
# =============================================================================


def create_summarizer() -> LlmAgent:
    """Create the summarizer agent with a minimal output schema.

    The agent has a reasonable instruction but a lacking schema.
    It doesn't know the critic expects key_points, sentiment, confidence, etc.

    Returns:
        LlmAgent configured for article summarization with minimal schema.
    """
    return LlmAgent(
        name="summarizer",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="""Analyze and summarize the given article or text.
Provide a clear, concise summary that captures the main points.""",
        output_schema=MinimalSummary,
    )


def create_critic() -> LlmAgent:
    """Create a critic that expects comprehensive structured analysis.

    The critic's expectations exceed what the minimal schema can provide:
    - Key points as a list
    - Sentiment analysis
    - Confidence score
    - Word count or reading time

    This gap between critic expectations and generator capabilities
    drives the schema evolution.

    Returns:
        LlmAgent configured as a demanding critic.
    """
    critic_instruction = """Evaluate the quality of article summaries.
A high-quality summary should include:

1. **Structured Key Points**: A list of 3-5 main takeaways, not just prose
2. **Sentiment Analysis**: The overall tone/sentiment of the original article
3. **Confidence Score**: How confident the summary is in its accuracy
4. **Completeness Metrics**: Word count, reading time, or coverage percentage

Score harshly if the output is just a plain text summary without structured fields.
A score of 1.0 requires ALL of the above elements in a structured format.
A plain text summary alone should score 0.3 or lower.

Provide specific feedback on what structured fields are missing."""

    return LlmAgent(
        name="summary_critic",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=critic_instruction,
        output_schema=CriticOutput,
    )


def create_trainset() -> list[dict[str, Any]]:
    """Create training examples with articles to summarize.

    Returns:
        List of articles/texts for the summarizer to analyze.
    """
    return [
        {
            "input": """
            The tech industry saw unprecedented growth in AI investments during 2024,
            with venture capital firms pouring over $50 billion into AI startups.
            Major players like OpenAI, Anthropic, and Google DeepMind led the charge,
            while concerns about AI safety and regulation grew louder. Critics argue
            that the rapid pace of development outstrips our ability to ensure these
            systems are safe, while proponents point to transformative applications
            in healthcare, education, and scientific research.
            """
        },
        {
            "input": """
            Local community garden initiative transforms abandoned lot into thriving
            green space. Volunteers from the neighborhood spent six months clearing
            debris and planting vegetables. The garden now provides fresh produce
            to over 50 families and has become a gathering place for community events.
            Organizers plan to expand next year and add educational programs for
            local schools.
            """
        },
        {
            "input": """
            New study reveals that remote work has permanently changed urban housing
            patterns. Cities are seeing population decline in downtown areas while
            suburbs and smaller towns experience growth. The shift has implications
            for commercial real estate, public transportation, and local tax revenues.
            Economists predict these trends will continue as companies adopt hybrid
            work models permanently.
            """
        },
    ]


# =============================================================================
# Reflection Agent with Output Schema
# =============================================================================


class SchemaProposal(BaseModel):
    """Structured output for schema evolution proposals.

    By using an output_schema on the reflection agent, we ENFORCE that the
    LLM produces only a class definition without imports. This is more
    reliable than text-based instructions.
    """

    class_definition: str = Field(
        description=(
            "The complete Pydantic class definition. "
            "Must start with 'class' and inherit from BaseModel. "
            "NO import statements - just the class definition itself. "
            "Use only: BaseModel, Field, str, int, float, bool, list, dict, Optional."
        )
    )
    reasoning: str = Field(description="Brief explanation of what was changed and why")


def create_schema_reflection_agent() -> LlmAgent:
    """Create a reflection agent specialized for schema evolution.

    The agent has an output_schema that enforces structured output,
    guaranteeing we get just the class definition without imports.

    Note:
        Uses ADK template placeholders {component_text} and {trials} for
        automatic substitution from session state.

    Returns:
        LlmAgent configured for schema reflection with enforced output format.
    """
    return LlmAgent(
        name="schema_reflector",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction="""You improve Pydantic output schemas based on critic feedback.

## Current Schema
{component_text}

## Evaluation Trials
{trials}

Based on the feedback above, propose an improved schema that addresses the
critic's concerns (e.g., adding key_points, sentiment, confidence fields).

RULES:
1. Output ONLY the class definition - NO imports
2. The class MUST inherit from BaseModel
3. Use Field() for descriptions and constraints
4. Available types: str, int, float, bool, list, dict, Optional, Union

The execution environment already has BaseModel, Field, and all basic types.""",
        output_schema=SchemaProposal,
    )


# =============================================================================
# Component Selector for Schema-Only Evolution
# =============================================================================


class OutputSchemaOnlySelector:
    """Component selector that only evolves the output_schema.

    This selector ensures only the output_schema component is mutated,
    leaving the instruction unchanged. This focuses evolution entirely
    on schema structure.
    """

    async def select_components(
        self,
        components: list[str],
        iteration: int,
        candidate_idx: int,
    ) -> list[str]:
        """Select only output_schema for evolution.

        Args:
            components: Available component keys.
            iteration: Current iteration number.
            candidate_idx: Index of candidate being evolved.

        Returns:
            List containing only 'output_schema' if available.
        """
        if "output_schema" in components:
            return ["output_schema"]
        return components[:1]  # Fallback to first component


# =============================================================================
# Evolution
# =============================================================================


async def run_evolution(
    agent: LlmAgent,
    critic: LlmAgent,
    trainset: list[dict[str, Any]],
    session_service: DatabaseSessionService,
) -> EvolutionResult:
    """Run evolutionary optimization targeting the output_schema.

    Uses the engine directly to enable multi-component candidates
    while only evolving the output_schema component.

    The unified AgentExecutor provides consistent session management
    across all three agent types (generator, critic, and reflection)
    even when using AsyncGEPAEngine directly.

    Args:
        agent: The summarizer agent to evolve.
        critic: The critic agent for scoring.
        trainset: Articles to summarize.
        session_service: Database session service for persistence.

    Returns:
        EvolutionResult containing the evolved schema and metrics.
    """
    config = EvolutionConfig(
        max_iterations=5,
        patience=2,
    )

    # Create reflection agent with structured output_schema
    # This ENFORCES that the LLM returns structured output with class_definition field
    # No imports will be included because ADK validates against the schema
    schema_reflector = create_schema_reflection_agent()

    # Serialize the initial schema for the candidate
    initial_schema = serialize_pydantic_schema(MinimalSummary)

    logger.info(
        "evolution.starting",
        agent_name=agent.name,
        trainset_size=len(trainset),
        max_iterations=config.max_iterations,
        evolving_component="output_schema",
    )

    # Show the initial schema
    print("\n" + "=" * 60)
    print("INITIAL OUTPUT SCHEMA (minimal):")
    print("=" * 60)
    safe_print(initial_schema)
    print("=" * 60 + "\n")

    # Create unified executor for consistent session management
    # This ensures all agent types (generator, critic, reflection) share the
    # same execution infrastructure and session service
    executor = AgentExecutor(session_service=session_service)

    # Create scorer from critic with unified executor
    scorer = CriticScorer(critic_agent=critic, executor=executor)

    # Create adapter with reflection agent that has output_schema
    # The output_field="class_definition" tells ADK to extract just that field
    # from the structured SchemaProposal output
    # Pass executor for unified execution path
    adapter = ADKAdapter(
        agent=agent,
        scorer=scorer,
        reflection_agent=schema_reflector,
        reflection_output_field="class_definition",  # Extract from SchemaProposal
        executor=executor,
    )

    # Create initial candidate with both instruction and output_schema
    # Only output_schema will be evolved (via component selector)
    initial_candidate = Candidate(
        components={
            "instruction": str(agent.instruction),
            "output_schema": initial_schema,
        },
        generation=0,
    )

    # Create engine with schema-only selector
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=config,
        initial_candidate=initial_candidate,
        batch=trainset,
        component_selector=OutputSchemaOnlySelector(),
    )

    # Run evolution
    result = await engine.run()

    logger.info(
        "evolution.complete",
        original_score=result.original_score,
        final_score=result.final_score,
        improvement=result.improvement,
        total_iterations=result.total_iterations,
    )

    return result


def get_examples_dir() -> Path:
    """Get the examples directory path."""
    return Path(__file__).parent


async def main() -> None:
    """Run the schema evolution example."""
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.schema_evolution_critic.start")

    # Set up SQLite database for session persistence
    data_dir = get_examples_dir().parent / "data"
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / "schema_evolution.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    session_service = DatabaseSessionService(db_url=db_url)

    # Initialize database tables before concurrent operations
    await session_service.list_sessions(app_name="schema_evolution")

    print(f"Session database: {db_path}")

    try:
        # Create agents and training data
        summarizer = create_summarizer()
        critic = create_critic()
        trainset = create_trainset()

        # Run evolution targeting output_schema
        result = await run_evolution(summarizer, critic, trainset, session_service)

        # Display results
        print("\n" + "=" * 60)
        print("SCHEMA EVOLUTION RESULTS")
        print("=" * 60)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score: {result.final_score:.3f}")
        print(f"Improvement: {result.improvement:.2%}")
        print(f"Iterations: {result.total_iterations}")

        # Get evolved output_schema from the evolved_components dictionary
        evolved_schema = result.evolved_components.get(
            "output_schema", result.evolved_components.get("instruction", "")
        )

        print("\n" + "-" * 60)
        print("EVOLVED OUTPUT SCHEMA:")
        print("-" * 60)
        safe_print(evolved_schema)
        print("=" * 60)

        # Display database stats
        print("\n" + "-" * 60)
        print("SQLite Database Stats")
        print("-" * 60)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM events")
        event_count = cursor.fetchone()[0]
        print(f"Total sessions in database: {session_count}")
        print(f"Total events in database: {event_count}")

        # Show reflector events
        cursor.execute("""
            SELECT json_extract(event_data, '$.author') as author, COUNT(*) as cnt
            FROM events
            WHERE json_extract(event_data, '$.author') LIKE '%reflector%'
            GROUP BY author
        """)
        reflector_counts = cursor.fetchall()
        if reflector_counts:
            print("\nReflector events:")
            for author, count in reflector_counts:
                print(f"  {author}: {count}")
        conn.close()

        print(f"\nSessions persisted to: {db_path}")

        # Explain what happened
        print("\n" + "-" * 60)
        print("WHAT HAPPENED:")
        print("-" * 60)
        print("""
The summarizer started with a minimal schema containing only 'summary: str'.
The critic scored poorly because it expected structured fields like key_points,
sentiment, and confidence.

This example uses a REFLECTION AGENT with output_schema to ENFORCE structured
output. The SchemaProposal model has:
  - class_definition: The Pydantic class (no imports needed)
  - reasoning: Why the change was made

Because the reflection agent has output_schema=SchemaProposal:
  1. ADK validates the output matches the schema
  2. We extract only the class_definition field
  3. No string parsing needed - it's enforced at the LLM level

Key points demonstrated:
  - Schema evolution driven by critic feedback
  - Reflection agent with output_schema for structured proposals
  - Schema validation (no imports/functions allowed in execution)
  - Using AsyncGEPAEngine directly for multi-component candidates
  - Custom ComponentSelector to evolve only output_schema

This mirrors the basic_evolution.py pattern:
  - Basic: Agent doesn't know Dickens style -> critic shapes instruction
  - Schema: Agent has minimal schema -> critic shapes output_schema
""")

        logger.info("example.schema_evolution_critic.success")

    except Exception as e:
        logger.error("example.schema_evolution_critic.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

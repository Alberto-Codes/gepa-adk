"""Example: App/Runner Integration for Evolution with SQLite Persistence.

This example demonstrates how to use an existing ADK Runner with evolution,
enabling seamless integration with production infrastructure. When you pass
a Runner to evolve(), evolve_group(), or evolve_workflow(), the evolution
engine uses your Runner's session_service for all operations.

This example uses DatabaseSessionService (SQLAlchemy async) to persist all
evolution sessions to a local SQLite database file. After running, you can
query the database to see all sessions, events, and state changes.

This is useful when:
- You have existing ADK infrastructure with custom session storage
- You want evolution sessions to be visible alongside your production sessions
- You need a database-backed session service for persistence and debugging

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/app_runner_integration.py

After running, inspect the database:
    sqlite3 data/evolution_sessions.db "SELECT COUNT(*) FROM sessions;"
    sqlite3 data/evolution_sessions.db "SELECT app_name, user_id, id FROM sessions LIMIT 10;"
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import structlog
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, evolve
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
# Output Schema
# -----------------------------------------------------------------------------
class CriticOutput(BaseModel):
    """Structured output for critic evaluation.

    Attributes:
        score: Quality score (0.0-1.0).
        feedback: Evaluation feedback.
    """

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Quality assessment score",
    )
    feedback: str


# -----------------------------------------------------------------------------
# Example Functions
# -----------------------------------------------------------------------------
def create_agents() -> tuple[LlmAgent, LlmAgent]:
    """Create the generator and critic agents.

    Returns:
        Tuple of (generator_agent, critic_agent).
    """
    # Use Ollama via LiteLLM
    ollama_base = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
    model = LiteLlm(model="ollama_chat/llama3.2:latest", api_base=ollama_base)

    generator = LlmAgent(
        name="greeter",
        model=model,
        instruction="""You are a greeting assistant. Generate a warm, literary
greeting for the given context. Be creative and evocative.""",
    )

    critic = LlmAgent(
        name="critic",
        model=model,
        instruction="""You are a literary critic inspired by Carlos Fuentes, the
renowned Mexican author known for his rich prose, cultural depth, and poetic
expression. Evaluate the greeting for:
- Literary quality and evocative language
- Cultural sensitivity and warmth
- Poetic resonance and emotional depth
- Appropriateness to the context

Score from 0.0 to 1.0 where 1.0 represents prose worthy of Fuentes himself.""",
        output_schema=CriticOutput,
    )

    return generator, critic


def create_trainset() -> list[dict[str, Any]]:
    """Create training examples.

    Returns:
        List of training examples with input contexts.
    """
    return [
        {"input": "A new employee's first day at the office"},
        {"input": "A customer entering a small bookshop"},
        {"input": "A friend you haven't seen in years"},
        {"input": "A formal business meeting introduction"},
        {"input": "A casual neighborhood gathering"},
    ]


async def run_evolution_with_runner() -> None:
    """Run evolution using a Runner with SQLite session persistence.

    This demonstrates the App/Runner pattern where you pass your existing
    Runner to evolution, and it uses your Runner's session_service for
    all operations (evolved agent, critic, reflection agent).

    All sessions are persisted to a local SQLite database file.
    """
    safe_print("\n" + "=" * 70)
    safe_print("App/Runner Integration Example (SQLite Persistence)")
    safe_print("=" * 70 + "\n")

    # Create agents
    generator, critic = create_agents()

    # Use SQLite for persistent session storage via DatabaseSessionService
    # Store in data/ directory (gitignored)
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / "evolution_sessions.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    session_service = DatabaseSessionService(db_url=db_url)

    # Initialize database tables before concurrent operations
    # This avoids race conditions during evolution
    await session_service.list_sessions(app_name="evolution_demo")

    # Create a Runner with the SQLite session service
    runner = Runner(
        app_name="evolution_demo",
        agent=generator,
        session_service=session_service,
    )

    safe_print("Created Runner with DatabaseSessionService")
    safe_print(f"  App name: {runner.app_name}")
    safe_print(f"  Database URL: {db_url}")
    safe_print("")

    # Create training data
    trainset = create_trainset()

    # Configure evolution with minimal iterations for demo
    config = EvolutionConfig(
        max_iterations=3,
        patience=2,
    )

    safe_print("Starting evolution with Runner...")
    safe_print("  All sessions will be persisted to SQLite.")
    safe_print("")

    # Run evolution, passing the Runner
    # This is the key feature: evolution extracts session_service from Runner
    result = await evolve(
        agent=generator,
        trainset=trainset,
        critic=critic,
        config=config,
        runner=runner,  # <-- Pass your Runner here
    )

    # Display results
    safe_print("\n" + "-" * 70)
    safe_print("Evolution Results")
    safe_print("-" * 70)
    safe_print(f"Original score: {result.original_score:.3f}")
    safe_print(f"Final score:    {result.final_score:.3f}")
    safe_print(f"Improvement:    {result.improvement:.1%}")
    safe_print(f"Iterations:     {result.total_iterations}")

    # Query SQLite to show persisted sessions
    safe_print("\n" + "-" * 70)
    safe_print("SQLite Database Stats")
    safe_print("-" * 70)

    import sqlite3

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Count sessions
    cursor.execute("SELECT COUNT(*) FROM sessions")
    session_count = cursor.fetchone()[0]
    safe_print(f"Total sessions in database: {session_count}")

    # Count events
    cursor.execute("SELECT COUNT(*) FROM events")
    event_count = cursor.fetchone()[0]
    safe_print(f"Total events in database: {event_count}")

    # Show sample session IDs
    cursor.execute("SELECT id FROM sessions LIMIT 5")
    sample_ids = [row[0] for row in cursor.fetchall()]
    safe_print("Sample session IDs:")
    for sid in sample_ids:
        safe_print(f"  - {sid[:36]}...")

    conn.close()

    safe_print("\n" + "-" * 70)
    safe_print("Evolved Instruction")
    safe_print("-" * 70)
    evolved_instruction = result.evolved_components.get("instruction", "N/A")
    safe_print(evolved_instruction)

    safe_print("\n" + "=" * 70)
    safe_print("Example Complete")
    safe_print("=" * 70)
    safe_print(f"\nSessions persisted to: {db_path.absolute()}")
    safe_print("Query the database with:")
    safe_print(f'  sqlite3 {db_path} "SELECT COUNT(*) FROM sessions;"')
    safe_print(f'  sqlite3 {db_path} "SELECT app_name, id FROM sessions LIMIT 5;"')


async def main() -> None:
    """Run the example."""
    # Check for required environment
    if not os.environ.get("OLLAMA_API_BASE"):
        safe_print(
            "Note: OLLAMA_API_BASE not set, using default http://localhost:11434"
        )
        os.environ["OLLAMA_API_BASE"] = "http://localhost:11434"

    await run_evolution_with_runner()


if __name__ == "__main__":
    asyncio.run(main())

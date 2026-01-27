"""Example: Model selection evolution with SQLite persistence.

This example demonstrates evolving which model an agent uses by providing
a list of allowed model choices. The evolution process tests different
models to find the best one for the task.

Key features demonstrated:
- Opt-in model evolution via model_choices parameter
- Auto-include of current model in allowed choices
- Combined evolution of instruction and model
- SQLite persistence via DatabaseSessionService

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)
    - Multiple Ollama models available (check with: curl http://localhost:11434/api/tags)

Usage:
    python examples/model_evolution.py

After running, inspect the database:
    sqlite3 data/model_evolution.db "SELECT COUNT(*) FROM sessions;"
    sqlite3 data/model_evolution.db "SELECT app_name, user_id, id FROM sessions LIMIT 10;"
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import structlog
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, EvolutionResult, evolve
from gepa_adk.utils import EncodingSafeProcessor

# -----------------------------------------------------------------------------
# Console Output Encoding
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
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# -----------------------------------------------------------------------------
# Critic Output Schema
# -----------------------------------------------------------------------------
class CriticOutput(BaseModel):
    """Schema for critic agent's structured output."""

    score: float = Field(ge=0.0, le=1.0, description="Quality score 0.0-1.0")
    feedback: str = Field(description="Explanation of the score")


# -----------------------------------------------------------------------------
# Main Evolution Function
# -----------------------------------------------------------------------------
async def main() -> None:
    """Run model selection evolution example with SQLite persistence."""
    # Check environment
    ollama_base = os.environ.get("OLLAMA_API_BASE")
    if not ollama_base:
        safe_print("Warning: OLLAMA_API_BASE not set. Using http://localhost:11434")
        os.environ["OLLAMA_API_BASE"] = "http://localhost:11434"

    # Available models - adjust based on your Ollama installation
    # You can list available models with: ollama list
    # Or curl http://localhost:11434/api/tags to see available models
    model_choices = [
        "ollama_chat/llama3.2:latest",
        "ollama_chat/gemma3:4b",
        "ollama_chat/granite4:3b",
    ]

    safe_print("=" * 70)
    safe_print("Model Selection Evolution Example (SQLite Persistence)")
    safe_print("=" * 70)
    safe_print(f"\nAvailable model choices: {model_choices}")

    # Create the agent to evolve
    agent = LlmAgent(
        name="summarizer",
        model=LiteLlm(model="ollama_chat/llama3.2:latest"),
        instruction="Summarize the given text concisely.",
    )

    safe_print(f"\nInitial model: {agent.model.model}")
    safe_print(f"Initial instruction: {agent.instruction}")

    # Create critic agent for scoring - STRICT evaluation
    critic = LlmAgent(
        name="critic",
        model=LiteLlm(model="ollama_chat/llama3.2:latest"),
        instruction="""You are an EXACTING and UNFORGIVING summary critic. You have VERY HIGH STANDARDS.

STRICT SCORING CRITERIA:

CONTENT ACCURACY (most important - penalize heavily if missing):
- The summary MUST capture ALL key facts from the original text
- Missing any important detail deserves a score below 0.4
- Incorrect information is UNACCEPTABLE - score below 0.3

CONCISENESS:
- A good summary is 1-2 sentences MAX for short texts
- Unnecessary words or repetition deserve harsh penalties
- "Padding" or filler content drops the score by at least 0.2

CLARITY:
- The summary must be immediately understandable
- Awkward phrasing or grammatical issues deserve scores below 0.5
- Vague language like "various things" or "some stuff" is LAZY - penalize heavily

SCORING GUIDE:
- 0.0-0.3: Missing key information, factual errors, or incomprehensible
- 0.3-0.5: Captures some content but missing important details or too verbose
- 0.5-0.7: Adequate but unremarkable - this is AVERAGE work
- 0.7-0.8: Good summary with minor issues - this is COMPETENT
- 0.8-0.9: Excellent - all key points, concise, clear - RARE
- 0.9-1.0: Perfect summary - reserved for exceptional work

A score above 0.6 requires GENUINELY good summarization.
A score of 0.8+ is RARE and demands near-perfect execution.
Be harsh. Mediocrity deserves no quarter.""",
        output_schema=CriticOutput,
    )

    # Training data
    trainset = [
        {
            "input": """The quick brown fox jumps over the lazy dog. This sentence
contains every letter of the English alphabet and is commonly used for font
testing and typing practice.""",
            "expected": "A pangram sentence used for font and typing practice.",
        },
        {
            "input": """Machine learning is a subset of artificial intelligence that
enables systems to learn and improve from experience without being explicitly
programmed. It focuses on developing algorithms that can access data and use
it to learn for themselves.""",
            "expected": "ML enables systems to learn from data without explicit programming.",
        },
    ]

    # Setup SQLite persistence via DatabaseSessionService
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / "model_evolution.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    session_service = DatabaseSessionService(db_url=db_url)

    # Initialize database tables before concurrent operations
    await session_service.list_sessions(app_name="model_evolution_demo")

    # Create Runner with SQLite session service
    runner = Runner(
        app_name="model_evolution_demo",
        agent=agent,
        session_service=session_service,
    )

    safe_print("\nCreated Runner with DatabaseSessionService")
    safe_print(f"  App name: {runner.app_name}")
    safe_print(f"  Database: {db_path}")

    # Evolution configuration
    config = EvolutionConfig(
        max_iterations=10,  # More iterations to see model changes
        patience=3,
        reflection_model="ollama_chat/llama3.2:latest",
    )

    safe_print("\nStarting model selection evolution...")
    safe_print("  All sessions will be persisted to SQLite.")
    safe_print("-" * 70)

    # Run evolution with model_choices and Runner for persistence
    result: EvolutionResult = await evolve(
        agent,
        trainset,
        critic=critic,
        model_choices=model_choices,
        components=["instruction", "model"],  # Evolve both
        config=config,
        runner=runner,  # <-- Pass Runner for SQLite persistence
    )

    # Display results
    safe_print("\n" + "=" * 70)
    safe_print("Evolution Results")
    safe_print("=" * 70)
    safe_print(f"\nOriginal score: {result.original_score:.3f}")
    safe_print(f"Final score: {result.final_score:.3f}")
    safe_print(f"Improvement: {result.improvement:.3f}")
    safe_print(f"Total iterations: {result.total_iterations}")

    safe_print("\n" + "-" * 70)
    safe_print("Evolved Components")
    safe_print("-" * 70)

    if "instruction" in result.evolved_components:
        safe_print(
            f"\nEvolved instruction:\n{result.evolved_components['instruction']}"
        )

    if "model" in result.evolved_components:
        safe_print(f"\nEvolved model: {result.evolved_components['model']}")

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

    safe_print("\n" + "=" * 70)
    safe_print("Example complete!")
    safe_print("=" * 70)
    safe_print(f"\nSessions persisted to: {db_path.absolute()}")
    safe_print("Query the database with:")
    safe_print(f'  sqlite3 {db_path} "SELECT COUNT(*) FROM sessions;"')
    safe_print(f'  sqlite3 {db_path} "SELECT app_name, id FROM sessions LIMIT 5;"')


if __name__ == "__main__":
    asyncio.run(main())

"""Example: Model selection evolution.

This example demonstrates evolving which model an agent uses by providing
a list of allowed model choices. The evolution process tests different
models to find the best one for the task.

Key features demonstrated:
- Opt-in model evolution via model_choices parameter
- Auto-include of current model in allowed choices
- Combined evolution of instruction and model

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)
    - Multiple Ollama models available (e.g., llama3.2, mistral, phi3)

Usage:
    python examples/model_evolution.py
"""

from __future__ import annotations

import asyncio
import os

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
    """Run model selection evolution example."""
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

    safe_print("=" * 60)
    safe_print("Model Selection Evolution Example")
    safe_print("=" * 60)
    safe_print(f"\nAvailable model choices: {model_choices}")

    # Create the agent to evolve
    agent = LlmAgent(
        name="summarizer",
        model=LiteLlm(model="ollama_chat/llama3.2:latest"),
        instruction="Summarize the given text concisely.",
    )

    safe_print(f"\nInitial model: {agent.model.model}")
    safe_print(f"Initial instruction: {agent.instruction}")

    # Create critic agent for scoring
    critic = LlmAgent(
        name="critic",
        model=LiteLlm(model="ollama_chat/llama3.2:latest"),
        instruction="""Evaluate the summary quality. Consider:
- Accuracy: Does it capture the main points?
- Conciseness: Is it brief but complete?
- Clarity: Is it easy to understand?

Score 0.0-1.0 where 1.0 is an excellent summary.""",
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

    # Evolution configuration
    config = EvolutionConfig(
        max_iterations=3,  # Keep short for demo
        patience=2,
        reflection_model="ollama_chat/llama3.2:latest",
    )

    safe_print("\nStarting model selection evolution...")
    safe_print("-" * 60)

    # Run evolution with model_choices
    result: EvolutionResult = await evolve(
        agent,
        trainset,
        critic=critic,
        model_choices=model_choices,
        components=["instruction", "model"],  # Evolve both
        config=config,
    )

    # Display results
    safe_print("\n" + "=" * 60)
    safe_print("Evolution Results")
    safe_print("=" * 60)
    safe_print(f"\nOriginal score: {result.original_score:.3f}")
    safe_print(f"Final score: {result.final_score:.3f}")
    safe_print(f"Improvement: {result.improvement:.3f}")
    safe_print(f"Total iterations: {result.total_iterations}")

    safe_print("\n" + "-" * 60)
    safe_print("Evolved Components")
    safe_print("-" * 60)

    if "instruction" in result.evolved_components:
        safe_print(
            f"\nEvolved instruction:\n{result.evolved_components['instruction']}"
        )

    if "model" in result.evolved_components:
        safe_print(f"\nEvolved model: {result.evolved_components['model']}")

    safe_print("\n" + "=" * 60)
    safe_print("Example complete!")
    safe_print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

"""Example: Multi-agent evolution with Ollama reflection agent.

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/multi_agent.py
"""

from __future__ import annotations

import asyncio
import os

import structlog
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel, Field

from gepa_adk import EvolutionConfig, evolve_group

logger = structlog.get_logger()


class ValidationOutput(BaseModel):
    """Structured output for validation scoring."""

    score: float = Field(ge=0.0, le=1.0, description="Quality score")
    feedback: str


def create_agents() -> list[LlmAgent]:
    """Create a simple two-agent pipeline."""
    generator = LlmAgent(
        name="generator",
        model=LiteLlm(model="ollama_chat/llama3.1:latest"),
        instruction="Answer the user's question clearly and concisely.",
        output_key="draft_output",
    )

    validator = LlmAgent(
        name="validator",
        model=LiteLlm(model="ollama_chat/llama3.1:latest"),
        instruction=(
            "Review the draft answer:\n{draft_output}\n\n"
            "Provide a score from 0.0 to 1.0 and short feedback."
        ),
        output_schema=ValidationOutput,
    )

    return [generator, validator]


def create_reflection_agent() -> LlmAgent:
    """Create reflection agent with schema guidance for Ollama."""
    return LlmAgent(
        name="reflector",
        model=LiteLlm(model="ollama_chat/llama3.1:latest"),
        instruction=(
            "Improve the instruction based on the feedback.\n"
            "Return ONLY the improved instruction text."
        ),
    )


def create_trainset() -> list[dict[str, str]]:
    """Create a small training set."""
    return [
        {"input": "What is 2+2?"},
        {"input": "Explain gravity simply."},
    ]


async def main() -> None:
    """Run multi-agent evolution with an Ollama reflection agent."""
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    agents = create_agents()
    reflection_agent = create_reflection_agent()
    trainset = create_trainset()

    config = EvolutionConfig(max_iterations=3, patience=1)

    logger.info("example.multi_agent.start", agents=[a.name for a in agents])

    result = await evolve_group(
        agents=agents,
        primary="validator",
        trainset=trainset,
        reflection_agent=reflection_agent,
        config=config,
    )

    logger.info(
        "example.multi_agent.complete",
        final_score=result.final_score,
        iterations=result.total_iterations,
    )

    print("Evolved components:")
    for agent_name, component_text in result.evolved_components.items():
        print(f"- {agent_name}: {component_text}")


if __name__ == "__main__":
    asyncio.run(main())

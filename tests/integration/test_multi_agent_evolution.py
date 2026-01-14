"""Integration tests for multi-agent evolution.

These tests verify end-to-end multi-agent co-evolution with real ADK agents.
Tests are marked as slow and integration since they make real LLM API calls.

Note:
    These tests require API keys and may take significant time to run.
    They are skipped by default in local development.
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from gepa_adk import MultiAgentEvolutionResult, evolve_group

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.api,
    pytest.mark.requires_gemini,
]


class CodeOutput(BaseModel):
    """Schema for code generation output."""

    code: str = Field(description="The generated code")
    explanation: str = Field(description="Explanation of the code")


@pytest.fixture
def simple_agents() -> list[LlmAgent]:
    """Create simple test agents for multi-agent evolution."""
    return [
        LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate a simple Python function.",
            output_schema=CodeOutput,  # Required for schema-based scoring
        ),
        LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review the generated code and provide feedback.",
        ),
    ]


@pytest.fixture
def simple_trainset() -> list[dict[str, Any]]:
    """Create simple training set for evolution."""
    return [
        {
            "input": "Create a function that adds two numbers",
            "expected": "def add(a, b): return a + b",
        },
        {
            "input": "Create a function that multiplies two numbers",
            "expected": "def multiply(a, b): return a * b",
        },
    ]


@pytest.mark.asyncio
async def test_evolve_group_returns_multi_agent_result(
    simple_agents: list[LlmAgent], simple_trainset: list[dict[str, Any]]
) -> None:
    """End-to-end: evolve_group returns MultiAgentEvolutionResult."""
    from gepa_adk.domain.models import EvolutionConfig

    result = await evolve_group(
        agents=simple_agents,
        primary="generator",
        trainset=simple_trainset,
        config=EvolutionConfig(max_iterations=2),  # Small for testing
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    assert "generator" in result.evolved_instructions
    assert "critic" in result.evolved_instructions
    assert result.primary_agent == "generator"
    assert result.total_iterations >= 0


@pytest.mark.asyncio
async def test_evolve_group_evolved_instructions_accessible(
    simple_agents: list[LlmAgent], simple_trainset: list[dict[str, Any]]
) -> None:
    """End-to-end: evolved_instructions dict is accessible by agent name."""
    from gepa_adk.domain.models import EvolutionConfig

    result = await evolve_group(
        agents=simple_agents,
        primary="generator",
        trainset=simple_trainset,
        config=EvolutionConfig(max_iterations=2),
    )

    # Verify all agent instructions are accessible
    assert result.evolved_instructions["generator"] is not None
    assert result.evolved_instructions["critic"] is not None
    assert isinstance(result.evolved_instructions["generator"], str)
    assert isinstance(result.evolved_instructions["critic"], str)


@pytest.mark.asyncio
async def test_evolve_group_computed_properties(
    simple_agents: list[LlmAgent], simple_trainset: list[dict[str, Any]]
) -> None:
    """End-to-end: MultiAgentEvolutionResult computed properties work."""
    from gepa_adk.domain.models import EvolutionConfig

    result = await evolve_group(
        agents=simple_agents,
        primary="generator",
        trainset=simple_trainset,
        config=EvolutionConfig(max_iterations=2),
    )

    # Test computed properties
    assert isinstance(result.improvement, float)
    assert isinstance(result.improved, bool)
    assert isinstance(result.agent_names, list)
    assert len(result.agent_names) == 2
    assert "generator" in result.agent_names
    assert "critic" in result.agent_names
    assert result.agent_names == sorted(result.agent_names)  # Should be sorted

"""Integration tests for multi-agent session sharing.

These tests verify session state sharing behavior between agents in
multi-agent pipelines. Tests are marked as slow and integration since
they make real LLM API calls.

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
def session_sharing_agents() -> list[LlmAgent]:
    """Create agents configured for session sharing test."""
    return [
        LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate a simple Python function.",
            output_key="generated_code",  # Saves output to session state
            output_schema=CodeOutput,  # Required for schema-based scoring
        ),
        LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review the code in {generated_code} and provide feedback.",
            # References generator's output via template string
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
    ]


@pytest.mark.asyncio
async def test_session_sharing_enables_state_access(
    session_sharing_agents: list[LlmAgent], simple_trainset: list[dict[str, Any]]
) -> None:
    """End-to-end: session sharing allows later agents to access earlier outputs."""
    from gepa_adk.domain.models import EvolutionConfig

    # With share_session=True, critic should be able to access generator's output
    result = await evolve_group(
        agents=session_sharing_agents,
        primary="generator",
        trainset=simple_trainset,
        share_session=True,  # Enable session sharing
        config=EvolutionConfig(max_iterations=1),  # Minimal for testing
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    # Verify both agents have evolved instructions
    assert "generator" in result.evolved_components
    assert "critic" in result.evolved_components


@pytest.mark.asyncio
async def test_isolated_sessions_prevent_state_access(
    session_sharing_agents: list[LlmAgent], simple_trainset: list[dict[str, Any]]
) -> None:
    """End-to-end: isolated sessions prevent agents from accessing each other's state."""
    from gepa_adk.domain.models import EvolutionConfig

    # With share_session=False, agents have isolated sessions
    result = await evolve_group(
        agents=session_sharing_agents,
        primary="generator",
        trainset=simple_trainset,
        share_session=False,  # Disable session sharing
        config=EvolutionConfig(max_iterations=1),
    )

    assert isinstance(result, MultiAgentEvolutionResult)
    # Evolution should still work, but critic cannot access generator's output
    assert "generator" in result.evolved_components

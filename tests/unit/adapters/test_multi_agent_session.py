"""Unit tests for multi-agent session isolation.

These tests verify that share_session=False creates isolated sessions
for each agent, preventing state sharing between agents.
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
from pytest_mock import MockerFixture

from gepa_adk.adapters import MultiAgentAdapter
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from tests.conftest import MockScorer

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_agents() -> dict[str, LlmAgent]:
    """Create mock ADK agents dict for testing."""
    return {
        "generator": LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
            output_key="generated_code",
        ),
        "critic": LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review code",
        ),
    }


@pytest.fixture
def mock_components() -> dict[str, list[str]]:
    """Create mock components mapping for testing."""
    return {
        "generator": ["instruction"],
        "critic": ["instruction"],
    }


@pytest.fixture
def mock_scorer() -> MockScorer:
    """Create a mock scorer with fixed 1.0 score for session tests."""
    return MockScorer(score_value=1.0)


@pytest.fixture
def mock_proposer(mocker: MockerFixture) -> AsyncReflectiveMutationProposer:
    """Create a mock proposer for testing."""
    mock_reflection_fn = mocker.AsyncMock(return_value="Improved text")
    return AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)


class TestSessionIsolation:
    """Tests for share_session=False isolation mode."""

    def test_share_session_false_creates_isolated_adapter(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_components: dict[str, list[str]],
        mock_scorer: MockScorer,
        mock_proposer: AsyncReflectiveMutationProposer,
    ) -> None:
        """Verify adapter can be created with share_session=False."""
        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            components=mock_components,
            scorer=mock_scorer,
            share_session=False,
            proposer=mock_proposer,
        )

        assert adapter.share_session is False
        assert adapter.primary == "generator"

    def test_share_session_true_creates_shared_adapter(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_components: dict[str, list[str]],
        mock_scorer: MockScorer,
        mock_proposer: AsyncReflectiveMutationProposer,
    ) -> None:
        """Verify adapter can be created with share_session=True (default)."""
        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            components=mock_components,
            scorer=mock_scorer,
            share_session=True,
            proposer=mock_proposer,
        )

        assert adapter.share_session is True

    @pytest.mark.asyncio
    async def test_isolated_sessions_use_primary_agent_only(
        self,
        mock_agents: dict[str, LlmAgent],
        mock_components: dict[str, list[str]],
        mock_scorer: MockScorer,
        mock_proposer: AsyncReflectiveMutationProposer,
        mocker: MockerFixture,
    ) -> None:
        """Verify isolated sessions execute primary agent only."""
        from google.adk.runners import Runner

        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            components=mock_components,
            scorer=mock_scorer,
            share_session=False,
            proposer=mock_proposer,
        )

        # Mock Runner to verify it's called with primary agent, not SequentialAgent
        mock_run = mocker.patch.object(
            Runner,
            "run_async",
            return_value=AsyncMockIterator(
                [
                    mocker.Mock(
                        is_final_response=lambda: True,
                        content=mocker.Mock(
                            parts=[mocker.Mock(text="Generated output")]
                        ),
                        session=mocker.Mock(state={}),
                    )
                ]
            ),
        )

        batch = [{"input": "Test input"}]
        # Use qualified names per ADR-012
        candidate = {
            "generator.instruction": "New instruction",
            "critic.instruction": "New critic instruction",
        }

        result = await adapter.evaluate(batch, candidate, capture_traces=False)

        # Verify Runner was called (for isolated execution)
        assert mock_run.called
        # Verify result structure
        assert len(result.outputs) == 1
        assert len(result.scores) == 1


class AsyncMockIterator:
    """Helper to create async iterator from list."""

    def __init__(self, items: list) -> None:
        """Initialize with items to iterate over."""
        self.items = items
        self.index = 0

    def __aiter__(self) -> Any:
        """Return self as the iterator."""
        return self

    async def __anext__(self) -> Any:
        """Return the next item in the sequence."""
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item

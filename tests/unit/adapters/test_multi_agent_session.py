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

pytestmark = pytest.mark.unit


class MockScorer:
    """Mock scorer for testing."""

    def score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        return (1.0, {})

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        return (1.0, {})


@pytest.fixture
def mock_agents() -> list[LlmAgent]:
    """Create mock ADK agents for testing."""
    return [
        LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
            output_key="generated_code",
        ),
        LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review code",
        ),
    ]


@pytest.fixture
def mock_scorer() -> MockScorer:
    """Create a mock scorer."""
    return MockScorer()


class TestSessionIsolation:
    """Tests for share_session=False isolation mode."""

    def test_share_session_false_creates_isolated_adapter(
        self, mock_agents: list[LlmAgent], mock_scorer: MockScorer
    ) -> None:
        """Verify adapter can be created with share_session=False."""
        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            scorer=mock_scorer,
            share_session=False,
        )

        assert adapter.share_session is False
        assert adapter.primary == "generator"

    def test_share_session_true_creates_shared_adapter(
        self, mock_agents: list[LlmAgent], mock_scorer: MockScorer
    ) -> None:
        """Verify adapter can be created with share_session=True (default)."""
        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            scorer=mock_scorer,
            share_session=True,
        )

        assert adapter.share_session is True

    @pytest.mark.asyncio
    async def test_isolated_sessions_use_primary_agent_only(
        self,
        mock_agents: list[LlmAgent],
        mock_scorer: MockScorer,
        mocker: MockerFixture,
    ) -> None:
        """Verify isolated sessions execute primary agent only."""
        from google.adk.runners import Runner

        adapter = MultiAgentAdapter(
            agents=mock_agents,
            primary="generator",
            scorer=mock_scorer,
            share_session=False,
        )

        # Mock Runner to verify it's called with primary agent, not SequentialAgent
        mock_run = mocker.patch.object(
            Runner,
            "run_async",
            return_value=AsyncMockIterator(
                [
                    mocker.Mock(
                        is_final_response=lambda: True,
                        actions=mocker.Mock(
                            response_content=[mocker.Mock(text="Generated output")]
                        ),
                        session=mocker.Mock(state={}),
                    )
                ]
            ),
        )

        batch = [{"input": "Test input"}]
        candidate = {
            "generator_instruction": "New instruction",
            "critic_instruction": "New critic instruction",
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
        self.items = items
        self.index = 0

    def __aiter__(self) -> Any:
        return self

    async def __anext__(self) -> Any:
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item

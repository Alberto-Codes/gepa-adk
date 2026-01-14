"""Unit tests for ADKAdapter proposer delegation.

These tests verify that ADKAdapter correctly delegates to AsyncReflectiveMutationProposer
for generating instruction mutations via LLM reflection.
"""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters import ADKAdapter
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

# Import fixtures from conftest (pytest will auto-discover them)
# Import MockScorer from test_adk_adapter
from tests.unit.adapters.test_adk_adapter import MockScorer


@pytest.fixture
def mock_agent() -> LlmAgent:
    """Create a mock ADK agent."""
    return LlmAgent(
        name="test_agent",
        model="gemini-2.0-flash",
        instruction="Original instruction",
    )


@pytest.fixture
def mock_scorer() -> MockScorer:
    """Create a mock scorer."""
    return MockScorer(score_value=0.85)


pytestmark = pytest.mark.unit


class TestADKAdapterProposerDelegation:
    """Unit tests for ADKAdapter proposer delegation (Phase 3: User Story 1).

    Note:
        Tests verify that ADKAdapter delegates to AsyncReflectiveMutationProposer
        for generating instruction mutations via LLM reflection.
    """

    @pytest.mark.asyncio
    async def test_constructor_accepts_proposer_parameter(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mock_proposer
    ) -> None:
        """Verify constructor accepts proposer parameter."""
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            proposer=mock_proposer,
        )

        assert adapter._proposer is mock_proposer

    @pytest.mark.asyncio
    async def test_constructor_creates_default_proposer(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor creates default proposer when None provided."""
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            proposer=None,
        )

        assert isinstance(adapter._proposer, AsyncReflectiveMutationProposer)

    @pytest.mark.asyncio
    async def test_propose_new_texts_delegates_to_proposer(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mock_proposer
    ) -> None:
        """Verify propose_new_texts delegates to proposer."""
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            proposer=mock_proposer,
        )

        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [
                {
                    "Inputs": {"input": "test"},
                    "Generated Outputs": "output",
                    "Feedback": "score: 0.8 | needs improvement",
                }
            ]
        }
        components_to_update = ["instruction"]

        # Configure mock to return a proposal
        mock_proposer.propose.return_value = {"instruction": "improved text"}

        result = await adapter.propose_new_texts(
            candidate, reflective_dataset, components_to_update
        )

        # Verify proposer was called
        mock_proposer.propose.assert_called_once_with(
            candidate, reflective_dataset, components_to_update
        )

        # Verify result contains proposed text
        assert result["instruction"] == "improved text"

    @pytest.mark.asyncio
    async def test_custom_proposer_is_used(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mock_proposer
    ) -> None:
        """Verify custom proposer is used instead of default."""
        # Create adapter with custom proposer
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            proposer=mock_proposer,
        )

        # Verify custom proposer is stored
        assert adapter._proposer is mock_proposer

        # Verify custom proposer is called
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [
                {
                    "Inputs": {"input": "test"},
                    "Generated Outputs": "output",
                    "Feedback": "score: 0.8",
                }
            ]
        }
        mock_proposer.propose.return_value = {"instruction": "custom result"}

        result = await adapter.propose_new_texts(
            candidate, reflective_dataset, ["instruction"]
        )

        assert result["instruction"] == "custom result"
        mock_proposer.propose.assert_called_once()

    @pytest.mark.asyncio
    async def test_propose_new_texts_fallback_on_none(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mock_proposer
    ) -> None:
        """Verify fallback to unchanged values when proposer returns None."""
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            proposer=mock_proposer,
        )

        candidate = {"instruction": "original text"}
        reflective_dataset = {}  # Empty dataset
        components_to_update = ["instruction"]

        # Configure mock to return None (empty dataset case)
        mock_proposer.propose.return_value = None

        result = await adapter.propose_new_texts(
            candidate, reflective_dataset, components_to_update
        )

        # Verify fallback to original candidate value
        assert result["instruction"] == "original text"

    @pytest.mark.asyncio
    async def test_propose_new_texts_merges_partial_result(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mock_proposer
    ) -> None:
        """Verify partial results are merged with candidate values."""
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            proposer=mock_proposer,
        )

        candidate = {
            "instruction": "original instruction",
            "other_component": "original other",
        }
        reflective_dataset = {
            "instruction": [
                {
                    "Inputs": {"input": "test"},
                    "Generated Outputs": "output",
                    "Feedback": "score: 0.8",
                }
            ]
        }
        components_to_update = ["instruction", "other_component"]

        # Proposer only returns result for one component
        mock_proposer.propose.return_value = {"instruction": "improved instruction"}

        result = await adapter.propose_new_texts(
            candidate, reflective_dataset, components_to_update
        )

        # Verify merged result
        assert result["instruction"] == "improved instruction"
        assert result["other_component"] == "original other"

    @pytest.mark.asyncio
    async def test_propose_new_texts_propagates_proposer_exception(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mock_proposer
    ) -> None:
        """Verify proposer exceptions propagate to caller."""
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            proposer=mock_proposer,
        )

        candidate = {"instruction": "original"}
        reflective_dataset = {"instruction": [{"Feedback": "test"}]}
        components_to_update = ["instruction"]

        # Configure mock to raise exception
        mock_proposer.propose.side_effect = ValueError("Proposer error")

        # Verify exception propagates
        with pytest.raises(ValueError, match="Proposer error"):
            await adapter.propose_new_texts(
                candidate, reflective_dataset, components_to_update
            )

"""Unit tests for MultiAgentAdapter state-based output extraction.

Feature: 122-adk-session-state
Tasks: T017-T018 - Unit/integration tests for multi_agent refactor

Tests verify that MultiAgentAdapter._extract_primary_output uses the shared
extract_output_from_state utility for state-based output extraction.

Contract reference: specs/122-adk-session-state/contracts/
"""

from typing import Any

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters import MultiAgentAdapter
from gepa_adk.utils.events import extract_output_from_state
from tests.conftest import MockScorer

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_generator_with_output_key() -> LlmAgent:
    """Create mock generator agent with output_key."""
    return LlmAgent(
        name="generator",
        model="gemini-2.0-flash",
        instruction="Generate code",
        output_key="generated_code",
    )


@pytest.fixture
def mock_generator_without_output_key() -> LlmAgent:
    """Create mock generator agent without output_key."""
    return LlmAgent(
        name="generator",
        model="gemini-2.0-flash",
        instruction="Generate code",
    )


@pytest.fixture
def mock_scorer() -> MockScorer:
    """Create a mock scorer."""
    return MockScorer(score_value=0.85)


class TestExtractPrimaryOutputWithSharedUtility:
    """T017-T018: Tests for _extract_primary_output using shared utility.

    Verify that _extract_primary_output delegates to extract_output_from_state
    for state-based output extraction.
    """

    def test_extract_from_state_when_output_key_exists(
        self, mock_generator_with_output_key: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify output extracted from state when output_key exists."""
        adapter = MultiAgentAdapter(
            agents=[mock_generator_with_output_key],
            primary="generator",
            scorer=mock_scorer,
        )

        pipeline_output = "pipeline final output"
        session_state = {"generated_code": "def foo(): pass"}

        result = adapter._extract_primary_output(
            pipeline_output=pipeline_output,
            session_state=session_state,
            primary_agent=mock_generator_with_output_key,
        )

        # Should return state value, not pipeline output
        assert result == "def foo(): pass"

    def test_extract_from_pipeline_when_output_key_missing_from_state(
        self, mock_generator_with_output_key: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify fallback to pipeline output when output_key not in state."""
        adapter = MultiAgentAdapter(
            agents=[mock_generator_with_output_key],
            primary="generator",
            scorer=mock_scorer,
        )

        pipeline_output = "pipeline final output"
        session_state = {"other_key": "other value"}  # No generated_code

        result = adapter._extract_primary_output(
            pipeline_output=pipeline_output,
            session_state=session_state,
            primary_agent=mock_generator_with_output_key,
        )

        # Should return pipeline output as fallback
        assert result == "pipeline final output"

    def test_extract_from_pipeline_when_no_output_key(
        self, mock_generator_without_output_key: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify pipeline output used when agent has no output_key."""
        adapter = MultiAgentAdapter(
            agents=[mock_generator_without_output_key],
            primary="generator",
            scorer=mock_scorer,
        )

        pipeline_output = "pipeline final output"
        session_state = {"generated_code": "state value"}

        result = adapter._extract_primary_output(
            pipeline_output=pipeline_output,
            session_state=session_state,
            primary_agent=mock_generator_without_output_key,
        )

        # Should return pipeline output since agent has no output_key
        assert result == "pipeline final output"

    def test_extract_from_state_with_non_string_value(
        self, mock_generator_with_output_key: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify non-string state values are converted to string."""
        adapter = MultiAgentAdapter(
            agents=[mock_generator_with_output_key],
            primary="generator",
            scorer=mock_scorer,
        )

        pipeline_output = "pipeline output"
        session_state = {"generated_code": 42}  # Non-string value

        result = adapter._extract_primary_output(
            pipeline_output=pipeline_output,
            session_state=session_state,
            primary_agent=mock_generator_with_output_key,
        )

        # Should convert to string
        assert result == "42"

    def test_extract_returns_pipeline_when_state_empty(
        self, mock_generator_with_output_key: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify pipeline output used when state is empty."""
        adapter = MultiAgentAdapter(
            agents=[mock_generator_with_output_key],
            primary="generator",
            scorer=mock_scorer,
        )

        pipeline_output = "pipeline output"
        session_state: dict[str, Any] = {}

        result = adapter._extract_primary_output(
            pipeline_output=pipeline_output,
            session_state=session_state,
            primary_agent=mock_generator_with_output_key,
        )

        # Should return pipeline output
        assert result == "pipeline output"


class TestExtractOutputFromStateDirectUsage:
    """Tests demonstrating direct usage of extract_output_from_state utility."""

    def test_shared_utility_works_with_multi_agent_pattern(self) -> None:
        """Verify shared utility works with multi-agent session state pattern."""
        # Simulate multi-agent session state
        session_state = {
            "generator_output": "Generated code here",
            "critic_output": "Review: looks good",
            "iteration_count": 3,
        }

        # Extract generator output
        generator_result = extract_output_from_state(session_state, "generator_output")
        assert generator_result == "Generated code here"

        # Extract critic output
        critic_result = extract_output_from_state(session_state, "critic_output")
        assert critic_result == "Review: looks good"

        # Non-existent key returns None
        missing_result = extract_output_from_state(session_state, "missing_key")
        assert missing_result is None

    def test_shared_utility_handles_none_output_key(self) -> None:
        """Verify shared utility handles None output_key correctly."""
        session_state = {"some_key": "value"}

        result = extract_output_from_state(session_state, None)

        assert result is None

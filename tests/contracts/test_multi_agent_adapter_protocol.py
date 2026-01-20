"""Contract tests for MultiAgentAdapter protocol compliance.

These tests verify that MultiAgentAdapter correctly implements the AsyncGEPAAdapter
protocol with proper method signatures, return types, and behavior contracts.

Note:
    Contract tests focus on protocol compliance, not business logic.
    They ensure the adapter can be used by the evolution engine.
"""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters import MultiAgentAdapter
from gepa_adk.ports.adapter import AsyncGEPAAdapter
from tests.conftest import MockScorer

pytestmark = pytest.mark.contract


@pytest.fixture
def mock_agents() -> list[LlmAgent]:
    """Create mock ADK agents for testing."""
    return [
        LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code",
        ),
        LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review code",
        ),
    ]


@pytest.fixture
def mock_scorer() -> MockScorer:
    """Create a mock scorer with fixed 1.0 score for contract tests."""
    return MockScorer(score_value=1.0)


@pytest.fixture
def adapter(mock_agents: list[LlmAgent], mock_scorer: MockScorer) -> MultiAgentAdapter:
    """Create a MultiAgentAdapter instance for testing."""
    return MultiAgentAdapter(
        agents=mock_agents,
        primary="generator",
        scorer=mock_scorer,
    )


class TestMultiAgentAdapterProtocolCompliance:
    """Contract tests verifying MultiAgentAdapter implements AsyncGEPAAdapter protocol.

    Note:
        These tests ensure the adapter can be used by the evolution engine
        without testing the full implementation logic.
    """

    def test_adapter_has_required_methods(self, adapter: MultiAgentAdapter) -> None:
        """Verify MultiAgentAdapter has all required protocol methods."""
        assert hasattr(adapter, "evaluate")
        assert hasattr(adapter, "make_reflective_dataset")
        assert hasattr(adapter, "propose_new_texts")

    def test_adapter_methods_are_async(self, adapter: MultiAgentAdapter) -> None:
        """Verify all adapter methods are coroutines."""
        import inspect

        assert inspect.iscoroutinefunction(adapter.evaluate)
        assert inspect.iscoroutinefunction(adapter.make_reflective_dataset)
        assert inspect.iscoroutinefunction(adapter.propose_new_texts)

    def test_adapter_satisfies_protocol(self, adapter: MultiAgentAdapter) -> None:
        """Verify MultiAgentAdapter instance checks as AsyncGEPAAdapter."""
        # Protocol is runtime_checkable, so isinstance should work
        assert isinstance(adapter, AsyncGEPAAdapter)

    def test_constructor_validates_agents_list(self, mock_scorer: MockScorer) -> None:
        """Ensure constructor rejects empty agents list."""
        from gepa_adk.domain.exceptions import MultiAgentValidationError

        with pytest.raises(
            MultiAgentValidationError, match="agents list cannot be empty"
        ):
            MultiAgentAdapter(
                agents=[],
                primary="generator",
                scorer=mock_scorer,
            )

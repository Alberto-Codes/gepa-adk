"""Contract tests for MultiAgentAdapter protocol compliance.

These tests verify that MultiAgentAdapter correctly implements the AsyncGEPAAdapter
protocol with proper method signatures, return types, and behavior contracts.
"""

from __future__ import annotations

import inspect

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters import MultiAgentAdapter
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from gepa_adk.ports.adapter import AsyncGEPAAdapter
from tests.conftest import MockScorer

pytestmark = pytest.mark.contract


@pytest.fixture
def mock_agents() -> dict[str, LlmAgent]:
    """Create mock ADK agents dict for testing."""
    return {
        "generator": LlmAgent(
            name="generator",
            model="gemini-2.5-flash",
            instruction="Generate code",
        ),
        "critic": LlmAgent(
            name="critic",
            model="gemini-2.5-flash",
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
    """Create a mock scorer with fixed 1.0 score for contract tests."""
    return MockScorer(score_value=1.0)


@pytest.fixture
def mock_proposer(mocker) -> AsyncReflectiveMutationProposer:
    """Create a mock proposer for testing."""
    mock_reflection_fn = mocker.AsyncMock(return_value=("Improved text", None))
    return AsyncReflectiveMutationProposer(adk_reflection_fn=mock_reflection_fn)


@pytest.fixture
def adapter(
    mock_agents: dict[str, LlmAgent],
    mock_components: dict[str, list[str]],
    mock_scorer: MockScorer,
    mock_proposer: AsyncReflectiveMutationProposer,
) -> MultiAgentAdapter:
    """Create a MultiAgentAdapter instance for testing."""
    return MultiAgentAdapter(
        agents=mock_agents,
        primary="generator",
        components=mock_components,
        scorer=mock_scorer,
        proposer=mock_proposer,
    )


class TestMultiAgentAdapterProtocolRuntimeCheckable:
    """Positive compliance: isinstance checks for MultiAgentAdapter."""

    def test_adapter_satisfies_protocol(self, adapter: MultiAgentAdapter) -> None:
        """MultiAgentAdapter instance checks as AsyncGEPAAdapter."""
        assert isinstance(adapter, AsyncGEPAAdapter)

    def test_adapter_has_required_methods(self, adapter: MultiAgentAdapter) -> None:
        """MultiAgentAdapter has all required protocol methods."""
        assert hasattr(adapter, "evaluate")
        assert hasattr(adapter, "make_reflective_dataset")
        assert hasattr(adapter, "propose_new_texts")


class TestMultiAgentAdapterProtocolBehavior:
    """Behavioral expectations: async protocol methods on MultiAgentAdapter."""

    def test_evaluate_is_async(self, adapter: MultiAgentAdapter) -> None:
        """Evaluate is an async method."""
        assert inspect.iscoroutinefunction(adapter.evaluate)

    def test_make_reflective_dataset_is_async(self, adapter: MultiAgentAdapter) -> None:
        """make_reflective_dataset is an async method."""
        assert inspect.iscoroutinefunction(adapter.make_reflective_dataset)

    def test_propose_new_texts_is_async(self, adapter: MultiAgentAdapter) -> None:
        """propose_new_texts is an async method."""
        assert inspect.iscoroutinefunction(adapter.propose_new_texts)


class TestMultiAgentAdapterProtocolNonCompliance:
    """Negative cases: objects missing required methods are not instances."""

    def test_missing_all_methods_not_isinstance(self) -> None:
        """Class without any protocol methods is not an AsyncGEPAAdapter."""

        class Incomplete:
            pass

        assert not isinstance(Incomplete(), AsyncGEPAAdapter)

    def test_missing_evaluate_not_isinstance(self) -> None:
        """Class missing evaluate is not an AsyncGEPAAdapter."""

        class MissingEvaluate:
            async def make_reflective_dataset(self, *a, **kw): ...

            async def propose_new_texts(self, *a, **kw): ...

        assert not isinstance(MissingEvaluate(), AsyncGEPAAdapter)

    def test_missing_propose_not_isinstance(self) -> None:
        """Class missing propose_new_texts is not an AsyncGEPAAdapter."""

        class MissingPropose:
            async def evaluate(self, *a, **kw): ...

            async def make_reflective_dataset(self, *a, **kw): ...

        assert not isinstance(MissingPropose(), AsyncGEPAAdapter)

    def test_missing_make_reflective_dataset_not_isinstance(self) -> None:
        """Class missing make_reflective_dataset is not an AsyncGEPAAdapter."""

        class MissingReflective:
            async def evaluate(self, *a, **kw): ...

            async def propose_new_texts(self, *a, **kw): ...

        assert not isinstance(MissingReflective(), AsyncGEPAAdapter)

    def test_runtime_checkable_limitation_documented(self) -> None:
        """@runtime_checkable only checks method existence, not signatures."""

        class WrongSignature:
            async def evaluate(self): ...

            async def make_reflective_dataset(self): ...

            async def propose_new_texts(self): ...

        # isinstance passes because runtime_checkable doesn't check signatures
        assert isinstance(WrongSignature(), AsyncGEPAAdapter)

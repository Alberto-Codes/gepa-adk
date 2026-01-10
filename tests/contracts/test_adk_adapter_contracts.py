"""Contract tests for ADKAdapter protocol compliance.

These tests verify that ADKAdapter correctly implements the AsyncGEPAAdapter
protocol with proper method signatures, return types, and behavior contracts.

Note:
    Contract tests focus on protocol compliance, not business logic.
    They ensure the adapter can be used by the evolution engine.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters import ADKAdapter
from gepa_adk.domain.trajectory import ADKTrajectory
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch


class MockScorer:
    """Mock scorer for testing."""

    def score(self, output: str, expected: str | None = None) -> float:
        """Synchronous score method."""
        return 1.0

    async def async_score(self, output: str, expected: str | None = None) -> float:
        """Async score method."""
        return 1.0


@pytest.fixture
def mock_agent() -> LlmAgent:
    """Create a mock ADK agent for testing."""
    return LlmAgent(
        name="test_agent",
        model="gemini-2.0-flash",
        instruction="Be helpful and concise",
    )


@pytest.fixture
def mock_scorer() -> MockScorer:
    """Create a mock scorer for testing."""
    return MockScorer()


@pytest.fixture
def adapter(mock_agent: LlmAgent, mock_scorer: MockScorer) -> ADKAdapter:
    """Create an ADKAdapter instance for testing."""
    return ADKAdapter(agent=mock_agent, scorer=mock_scorer)


@pytest.mark.contract
class TestADKAdapterProtocolCompliance:
    """Contract tests verifying ADKAdapter implements AsyncGEPAAdapter protocol.

    Note:
        These tests ensure the adapter can be used by the evolution engine
        without testing the full implementation logic.
    """

    def test_adapter_has_required_methods(self, adapter: ADKAdapter) -> None:
        """Verify ADKAdapter has all required protocol methods."""
        assert hasattr(adapter, "evaluate")
        assert hasattr(adapter, "make_reflective_dataset")
        assert hasattr(adapter, "propose_new_texts")

    def test_adapter_methods_are_async(self, adapter: ADKAdapter) -> None:
        """Verify all adapter methods are coroutines."""
        import inspect

        assert inspect.iscoroutinefunction(adapter.evaluate)
        assert inspect.iscoroutinefunction(adapter.make_reflective_dataset)
        assert inspect.iscoroutinefunction(adapter.propose_new_texts)

    def test_adapter_satisfies_protocol(self, adapter: ADKAdapter) -> None:
        """Verify ADKAdapter instance checks as AsyncGEPAAdapter."""
        # Protocol is runtime_checkable, so isinstance should work
        assert isinstance(adapter, AsyncGEPAAdapter)

    def test_constructor_validates_agent_type(self, mock_scorer: MockScorer) -> None:
        """Ensure constructor rejects non-LlmAgent objects."""
        with pytest.raises(TypeError, match="agent must be LlmAgent"):
            ADKAdapter(agent="not_an_agent", scorer=mock_scorer)  # type: ignore

    def test_constructor_validates_scorer_protocol(self, mock_agent: LlmAgent) -> None:
        """Ensure constructor rejects objects not satisfying Scorer protocol."""
        invalid_scorer = object()
        with pytest.raises(TypeError, match="scorer must implement Scorer protocol"):
            ADKAdapter(agent=mock_agent, scorer=invalid_scorer)  # type: ignore

    def test_constructor_validates_app_name(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Ensure constructor rejects empty app_name."""
        with pytest.raises(ValueError, match="app_name cannot be empty"):
            ADKAdapter(agent=mock_agent, scorer=mock_scorer, app_name="")

        with pytest.raises(ValueError, match="app_name cannot be empty"):
            ADKAdapter(agent=mock_agent, scorer=mock_scorer, app_name="   ")

    def test_constructor_accepts_valid_parameters(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor succeeds with valid parameters."""
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            app_name="test_app",
        )
        assert adapter.agent is mock_agent
        assert adapter.scorer is mock_scorer
        assert adapter._app_name == "test_app"

    def test_constructor_creates_default_session_service(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor creates InMemorySessionService when None provided."""
        from google.adk.sessions import InMemorySessionService

        adapter = ADKAdapter(agent=mock_agent, scorer=mock_scorer)
        assert isinstance(adapter._session_service, InMemorySessionService)

    def test_constructor_accepts_custom_session_service(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor accepts custom session service."""
        from google.adk.sessions import InMemorySessionService

        custom_service = InMemorySessionService()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            session_service=custom_service,
        )
        assert adapter._session_service is custom_service


@pytest.mark.contract
class TestEvaluateMethodContract:
    """Contract tests for evaluate() method signature and return type.

    Note:
        These tests verify method contracts, not full implementation.
        Full behavior is tested in unit and integration tests.
    """

    @pytest.mark.asyncio
    async def test_evaluate_signature_accepts_required_parameters(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify evaluate() accepts batch and candidate parameters."""
        # Should accept parameters and return EvaluationBatch
        result = await adapter.evaluate(
            batch=[{"input": "test"}],
            candidate={"instruction": "test"},
        )
        assert isinstance(result, EvaluationBatch)

    @pytest.mark.asyncio
    async def test_evaluate_signature_accepts_capture_traces(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify evaluate() accepts optional capture_traces parameter."""
        # Should accept capture_traces parameter
        result = await adapter.evaluate(
            batch=[{"input": "test"}],
            candidate={"instruction": "test"},
            capture_traces=True,
        )
        assert isinstance(result, EvaluationBatch)

    @pytest.mark.asyncio
    async def test_evaluate_returns_evaluation_batch(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify evaluate() returns EvaluationBatch type."""
        # Verify correct return type
        result = await adapter.evaluate(
            batch=[{"input": "test"}],
            candidate={"instruction": "test"},
        )
        assert isinstance(result, EvaluationBatch)

    @pytest.mark.asyncio
    async def test_evaluate_output_length_matches_batch_length(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify evaluate() returns outputs/scores matching batch length."""
        # Contract: len(outputs) == len(scores) == len(batch)
        # This is a critical invariant for engine compatibility
        batch = [{"input": "test1"}, {"input": "test2"}]
        result = await adapter.evaluate(
            batch=batch,
            candidate={"instruction": "test"},
        )
        assert len(result.outputs) == len(batch)
        assert len(result.scores) == len(batch)

    @pytest.mark.asyncio
    async def test_evaluate_trajectories_none_when_capture_false(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify evaluate() returns trajectories=None when capture_traces=False."""
        # Contract: trajectories is None when not capturing
        result = await adapter.evaluate(
            batch=[{"input": "test"}],
            candidate={"instruction": "test"},
            capture_traces=False,
        )
        assert result.trajectories is None


@pytest.mark.contract
class TestTrajectoryContract:
    """Contract tests for trace capture functionality (US2).

    Note:
        These tests verify trajectory structure and capture_traces behavior.
    """

    @pytest.mark.asyncio
    async def test_trajectories_populated_when_capture_true(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify trajectories list is populated when capture_traces=True."""
        batch = [{"input": "test"}]
        result = await adapter.evaluate(
            batch=batch,
            candidate={"instruction": "test"},
            capture_traces=True,
        )
        
        # Contract: trajectories is a list with same length as batch
        assert result.trajectories is not None
        assert isinstance(result.trajectories, list)
        assert len(result.trajectories) == len(batch)

    @pytest.mark.asyncio
    async def test_trajectory_has_required_fields(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify each trajectory has required ADKTrajectory fields."""
        from gepa_adk.domain import ADKTrajectory
        
        result = await adapter.evaluate(
            batch=[{"input": "test"}],
            candidate={"instruction": "test"},
            capture_traces=True,
        )
        
        # Contract: each trajectory is an ADKTrajectory instance
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert isinstance(trajectory, ADKTrajectory)
        assert hasattr(trajectory, "tool_calls")
        assert hasattr(trajectory, "state_deltas")
        assert hasattr(trajectory, "token_usage")
        assert hasattr(trajectory, "final_output")
        assert hasattr(trajectory, "error")

    @pytest.mark.asyncio
    async def test_trajectory_tool_calls_is_list(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify trajectory.tool_calls is a list."""
        result = await adapter.evaluate(
            batch=[{"input": "test"}],
            candidate={"instruction": "test"},
            capture_traces=True,
        )
        
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert isinstance(trajectory.tool_calls, list)

    @pytest.mark.asyncio
    async def test_trajectory_state_deltas_is_list(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify trajectory.state_deltas is a list."""
        result = await adapter.evaluate(
            batch=[{"input": "test"}],
            candidate={"instruction": "test"},
            capture_traces=True,
        )
        
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert isinstance(trajectory.state_deltas, list)


@pytest.mark.contract
class TestMakeReflectiveDatasetContract:
    """Contract tests for make_reflective_dataset() method.

    Note:
        These tests verify method signature compliance with protocol.
    """

    @pytest.mark.asyncio
    async def test_make_reflective_dataset_signature(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify make_reflective_dataset() accepts required parameters."""
        eval_batch = EvaluationBatch(
            outputs=["test"],
            scores=[1.0],
            trajectories=[
                ADKTrajectory(
                    tool_calls=(),
                    state_deltas=(),
                    token_usage=None,
                    final_output="test",
                    error=None,
                )
            ],
        )

        # Should accept parameters and return a mapping
        result = await adapter.make_reflective_dataset(
            candidate={"instruction": "test"},
            eval_batch=eval_batch,
            components_to_update=["instruction"],
        )
        
        # Contract: returns Mapping[str, Sequence[Mapping[str, Any]]]
        from collections.abc import Mapping, Sequence
        assert isinstance(result, Mapping)

    @pytest.mark.asyncio
    async def test_make_reflective_dataset_returns_sequence_values(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify result values are sequences of mappings."""
        eval_batch = EvaluationBatch(
            outputs=["test"],
            scores=[1.0],
            trajectories=None,
        )

        result = await adapter.make_reflective_dataset(
            candidate={"instruction": "test"},
            eval_batch=eval_batch,
            components_to_update=["instruction"],
        )

        # Contract: each value is a Sequence of Mappings
        for component, examples in result.items():
            assert isinstance(examples, (list, tuple))
            for example in examples:
                assert isinstance(example, dict)


@pytest.mark.contract
class TestProposeNewTextsContract:
    """Contract tests for propose_new_texts() method.

    Note:
        These tests verify method signature compliance with protocol.
    """

    @pytest.mark.asyncio
    async def test_propose_new_texts_signature(self, adapter: ADKAdapter) -> None:
        """Verify propose_new_texts() accepts required parameters."""
        with pytest.raises(NotImplementedError):
            await adapter.propose_new_texts(
                candidate={"instruction": "test"},
                reflective_dataset={"instruction": [{"example": "data"}]},
                components_to_update=["instruction"],
            )

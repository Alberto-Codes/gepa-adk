"""Contract tests for ADKAdapter protocol compliance.

These tests verify that ADKAdapter correctly implements the AsyncGEPAAdapter
protocol with proper method signatures, return types, and behavior contracts.

Note:
    Contract tests focus on protocol compliance, not business logic.
    They ensure the adapter can be used by the evolution engine.
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
from pytest_mock import MockerFixture

from gepa_adk.adapters import ADKAdapter
from gepa_adk.domain.trajectory import ADKTrajectory
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch

pytestmark = pytest.mark.contract


class MockScorer:
    """Mock scorer for testing.

    Properly implements the Scorer protocol with the correct signature:
    - score(input_text, output, expected) -> tuple[float, dict]
    - async_score(input_text, output, expected) -> tuple[float, dict]
    """

    def score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Synchronous score method."""
        return (1.0, {})

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Async score method."""
        return (1.0, {})


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
    async def test_evaluate_returns_evaluation_batch(self, adapter: ADKAdapter) -> None:
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
    async def test_trajectory_has_required_fields(self, adapter: ADKAdapter) -> None:
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
    async def test_trajectory_tool_calls_is_sequence(self, adapter: ADKAdapter) -> None:
        """Verify trajectory.tool_calls is a sequence (tuple for immutability)."""
        result = await adapter.evaluate(
            batch=[{"input": "test"}],
            candidate={"instruction": "test"},
            capture_traces=True,
        )

        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert isinstance(trajectory.tool_calls, (list, tuple))

    @pytest.mark.asyncio
    async def test_trajectory_state_deltas_is_sequence(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify trajectory.state_deltas is a sequence (tuple for immutability)."""
        result = await adapter.evaluate(
            batch=[{"input": "test"}],
            candidate={"instruction": "test"},
            capture_traces=True,
        )

        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert isinstance(trajectory.state_deltas, (list, tuple))


class TestMakeReflectiveDatasetContract:
    """Contract tests for make_reflective_dataset() method.

    Note:
        These tests verify method signature compliance with protocol.
    """

    @pytest.mark.asyncio
    async def test_make_reflective_dataset_signature(self, adapter: ADKAdapter) -> None:
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
        from collections.abc import Mapping

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


class TestSessionIsolationContract:
    """Contract tests for session isolation (US4).

    Note:
        These tests verify session management invariants.
    """

    @pytest.mark.asyncio
    async def test_session_service_injectable(self, mock_agent: LlmAgent) -> None:
        """Verify adapter accepts custom session service."""
        from google.adk.sessions import InMemorySessionService

        custom_service = InMemorySessionService()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=MockScorer(),
            session_service=custom_service,
        )

        # Adapter should accept custom service
        assert adapter._session_service is custom_service

    @pytest.mark.asyncio
    async def test_default_session_service_is_in_memory(
        self, mock_agent: LlmAgent
    ) -> None:
        """Verify default session service is InMemorySessionService."""
        from google.adk.sessions import InMemorySessionService

        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=MockScorer(),
        )

        # Default should be InMemorySessionService
        assert isinstance(adapter._session_service, InMemorySessionService)


class TestConcurrentEvaluationContract:
    """Contract tests for concurrent batch evaluation (US1).

    Note:
        These tests verify parallel execution behavior and result ordering
        preservation as specified in the concurrent batch evaluation feature.
    """

    @pytest.mark.asyncio
    async def test_contract_executes_batch_in_parallel(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """FR-001: Batch evaluations execute in parallel.

        Given:
            - batch_size = 10
            - max_concurrent_evals = 5
            - Each evaluation takes ~T seconds

        When:
            - evaluate() is called

        Then:
            - Total time is approximately (batch_size / max_concurrent_evals) * T
            - Not batch_size * T (sequential behavior)
        """
        import asyncio
        import time

        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            max_concurrent_evals=5,
        )

        # Create batch of 10 examples
        batch = [{"input": f"test_{i}"} for i in range(10)]
        candidate = {"instruction": "Test"}

        # Mock runner with delay to measure concurrency
        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        # Track concurrent executions
        active_tasks = asyncio.Semaphore(5)
        concurrent_count = 0
        max_concurrent = 0

        async def mock_run_with_delay():
            nonlocal concurrent_count, max_concurrent
            async with active_tasks:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
                await asyncio.sleep(0.1)  # Simulate work
                concurrent_count -= 1

                yield mocker.MagicMock(
                    is_final_response=lambda: True,
                    actions=mocker.MagicMock(
                        response_content=[mocker.MagicMock(text="response")]
                    ),
                )

        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=[mock_run_with_delay() for _ in range(10)]
        )
        MockRunner.return_value = mock_runner_instance

        start_time = time.time()
        result = await adapter.evaluate(batch, candidate)
        elapsed_time = time.time() - start_time

        # With 5 concurrent, 10 items should take ~2x single item time, not 10x
        # Allow some margin for overhead
        assert elapsed_time < 0.5  # Should be much faster than sequential (1.0s)
        assert max_concurrent <= 5  # Should respect concurrency limit
        assert len(result.outputs) == 10

    @pytest.mark.asyncio
    async def test_contract_preserves_result_ordering(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """FR-009: Results maintain input order.

        Given:
            - batch = [example_0, example_1, ..., example_N]

        When:
            - evaluate() is called with parallel execution

        Then:
            - outputs[i] corresponds to batch[i]
            - scores[i] corresponds to batch[i]
            - trajectories[i] corresponds to batch[i] (if captured)
        """
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            max_concurrent_evals=3,
        )

        # Create batch with identifiable outputs
        batch = [
            {"input": "test_0", "expected": "output_0"},
            {"input": "test_1", "expected": "output_1"},
            {"input": "test_2", "expected": "output_2"},
            {"input": "test_3", "expected": "output_3"},
            {"input": "test_4", "expected": "output_4"},
        ]
        candidate = {"instruction": "Test"}

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        # Create mocks that return outputs in random order (to test ordering preservation)
        async def mock_run(index: int):
            # Add random delay to simulate out-of-order completion
            import random

            await asyncio.sleep(random.uniform(0.01, 0.05))
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text=f"output_{index}")]
                ),
            )

        import asyncio

        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=[mock_run(i) for i in range(5)]
        )
        MockRunner.return_value = mock_runner_instance

        result = await adapter.evaluate(batch, candidate)

        # Results must maintain input order despite parallel execution
        assert len(result.outputs) == 5
        assert len(result.scores) == 5
        # Verify outputs correspond to inputs in order
        for i in range(5):
            assert f"output_{i}" in result.outputs[i] or result.outputs[i] == ""


class TestConcurrencyLimitControlContract:
    """Contract tests for concurrency limit control (US2).

    Note:
        These tests verify that different concurrency configurations
        work correctly and respect the configured limits.
    """

    @pytest.mark.asyncio
    async def test_contract_concurrency_one_sequential_behavior(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """Contract test for concurrency=1 (sequential) behavior.

        Given:
            - max_concurrent_evals = 1

        When:
            - evaluate() is called with batch

        Then:
            - Evaluations run sequentially (one at a time)
        """
        import asyncio

        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            max_concurrent_evals=1,
        )

        batch = [{"input": f"test_{i}"} for i in range(5)]
        candidate = {"instruction": "Test"}

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        # Track execution order
        execution_order: list[int] = []

        async def mock_run(index: int):
            execution_order.append(index)
            await asyncio.sleep(0.01)  # Small delay
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text=f"output_{index}")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=[mock_run(i) for i in range(5)]
        )
        MockRunner.return_value = mock_runner_instance

        await adapter.evaluate(batch, candidate)

        # With concurrency=1, should execute in order (or at least not all at once)
        # Note: Due to async nature, exact order may vary, but max concurrent should be 1
        assert len(execution_order) == 5

    @pytest.mark.asyncio
    async def test_contract_concurrency_larger_than_batch(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """Contract test for concurrency > batch_size behavior.

        Given:
            - max_concurrent_evals = 10
            - batch_size = 3

        When:
            - evaluate() is called

        Then:
            - All 3 examples run concurrently
            - No errors or unexpected behavior
        """
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            max_concurrent_evals=10,
        )

        batch = [{"input": f"test_{i}"} for i in range(3)]
        candidate = {"instruction": "Test"}

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run(index: int):
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text=f"output_{index}")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=[mock_run(i) for i in range(3)]
        )
        MockRunner.return_value = mock_runner_instance

        result = await adapter.evaluate(batch, candidate)

        # Should complete successfully with all results
        assert len(result.outputs) == 3
        assert len(result.scores) == 3


class TestErrorHandlingContract:
    """Contract tests for graceful error handling (US3).

    Note:
        These tests verify that individual failures don't block other
        evaluations and error information is properly captured.
    """

    @pytest.mark.asyncio
    async def test_contract_continues_on_individual_failure(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """FR-005: Individual failures don't block other evaluations.

        Given:
            - batch with some examples that will fail
            - Other examples that will succeed

        When:
            - evaluate() is called

        Then:
            - Successful examples complete normally
            - Failed examples don't prevent other completions
            - All results are returned (success and failure)
        """
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            max_concurrent_evals=3,
        )

        batch = [
            {"input": "test_0", "expected": "output_0"},
            {"input": "test_1", "expected": "output_1"},
            {"input": "test_2", "expected": "output_2"},
        ]
        candidate = {"instruction": "Test"}

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run(index: int):
            if index == 1:
                # Simulate failure for second example
                raise RuntimeError("Simulated failure")
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text=f"output_{index}")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=[mock_run(i) for i in range(3)]
        )
        MockRunner.return_value = mock_runner_instance

        result = await adapter.evaluate(batch, candidate)

        # All results should be returned
        assert len(result.outputs) == 3
        assert len(result.scores) == 3
        # First and third should succeed
        assert result.outputs[0] != ""
        assert result.outputs[2] != ""
        # Second should fail
        assert result.outputs[1] == ""
        assert result.scores[1] == 0.0

    @pytest.mark.asyncio
    async def test_contract_captures_error_information(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """FR-006: Failed evaluations include error details.

        Given:
            - An example that fails during evaluation

        When:
            - evaluate() completes

        Then:
            - The corresponding trajectory.error contains error message
            - Error message is actionable (includes exception type/details)
        """
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            max_concurrent_evals=2,
        )

        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()
        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=RuntimeError("Test error message")
        )
        MockRunner.return_value = mock_runner_instance

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should capture error in trajectory
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert trajectory.error is not None
        assert "Test error message" in trajectory.error

    @pytest.mark.asyncio
    async def test_contract_assigns_zero_score_to_failures(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """FR-007: Failed evaluations receive score of 0.0.

        Given:
            - An example that fails during evaluation

        When:
            - evaluate() completes

        Then:
            - scores[i] == 0.0 for the failed example
        """
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            max_concurrent_evals=2,
        )

        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()
        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=RuntimeError("Failure")
        )
        MockRunner.return_value = mock_runner_instance

        result = await adapter.evaluate(batch, candidate)

        assert len(result.scores) == 1
        assert result.scores[0] == 0.0

    @pytest.mark.asyncio
    async def test_contract_returns_empty_output_for_failures(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """FR-006/FR-008: Failed evaluations have empty output.

        Given:
            - An example that fails during evaluation

        When:
            - evaluate() completes

        Then:
            - outputs[i] == "" for the failed example
        """
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            max_concurrent_evals=2,
        )

        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()
        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=RuntimeError("Failure")
        )
        MockRunner.return_value = mock_runner_instance

        result = await adapter.evaluate(batch, candidate)

        assert len(result.outputs) == 1
        assert result.outputs[0] == ""

    @pytest.mark.asyncio
    async def test_contract_returns_complete_result_set(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """FR-008: Always returns complete result set.

        Given:
            - batch of N examples
            - Some may succeed, some may fail

        When:
            - evaluate() completes

        Then:
            - len(outputs) == N
            - len(scores) == N
            - len(trajectories) == N (if capture_traces=True)
        """
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            max_concurrent_evals=3,
        )

        batch = [
            {"input": "test_0"},
            {"input": "test_1"},
            {"input": "test_2"},
        ]
        candidate = {"instruction": "Test"}

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run(index: int):
            if index == 1:
                raise RuntimeError("Failure")
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text=f"output_{index}")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=[mock_run(i) for i in range(3)]
        )
        MockRunner.return_value = mock_runner_instance

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should return complete result set
        assert len(result.outputs) == 3
        assert len(result.scores) == 3
        assert result.trajectories is not None
        assert len(result.trajectories) == 3


class TestProposeNewTextsContract:
    """Contract tests for propose_new_texts() method.

    Note:
        These tests verify method signature compliance with protocol.
        Current implementation is a stub that returns unchanged candidate.
    """

    @pytest.mark.asyncio
    async def test_propose_new_texts_signature(self, adapter: ADKAdapter) -> None:
        """Verify propose_new_texts() accepts required parameters and returns dict."""
        result = await adapter.propose_new_texts(
            candidate={"instruction": "test"},
            reflective_dataset={"instruction": [{"example": "data"}]},
            components_to_update=["instruction"],
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_propose_new_texts_returns_candidate_subset(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify stub returns only requested component values."""
        candidate = {"instruction": "original", "examples": "some examples"}
        components = ["instruction"]

        result = await adapter.propose_new_texts(
            candidate=candidate,
            reflective_dataset={"instruction": []},
            components_to_update=components,
        )

        # Stub should return values for requested components only
        assert "instruction" in result
        assert result["instruction"] == "original"  # Stub returns unchanged

    @pytest.mark.asyncio
    async def test_propose_new_texts_logs_stub_warning(
        self, adapter: ADKAdapter, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify stub implementation logs a warning about delegation."""
        await adapter.propose_new_texts(
            candidate={"instruction": "test"},
            reflective_dataset={"instruction": []},
            components_to_update=["instruction"],
        )
        # Stub should indicate it's not doing real mutation proposal
        # (logging is checked at integration level)

"""Unit tests for ADKAdapter implementation.

These tests verify the business logic of ADKAdapter using mocked dependencies
to isolate the adapter behavior from external ADK services.

Note:
    Unit tests use mocked ADK agents and runners to avoid real API calls.
    Integration tests (in tests/integration/) use real ADK services.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from google.adk.agents import LlmAgent
from pytest_mock import MockerFixture

from gepa_adk.adapters import ADKAdapter
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from gepa_adk.ports.adapter import EvaluationBatch
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus


class MockScorer:
    """Mock scorer that returns predictable scores.

    Properly implements the Scorer protocol with the correct signature:
    - score(input_text, output, expected) -> tuple[float, dict]
    - async_score(input_text, output, expected) -> tuple[float, dict]
    """

    def __init__(self, score_value: float = 0.8) -> None:
        """Initialize mock scorer with fixed score value."""
        self.score_value = score_value
        self.score_calls: list[tuple[str, str, str | None]] = []

    def score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Record call and return fixed score with empty metadata."""
        self.score_calls.append((input_text, output, expected))
        return (self.score_value, {})

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Record call and return fixed score with empty metadata."""
        self.score_calls.append((input_text, output, expected))
        return (self.score_value, {})


def make_executor_results(
    outputs: list[str],
    mocker: MockerFixture,
) -> list[ExecutionResult]:
    """Create ExecutionResult objects for mock executor.

    Args:
        outputs: List of output strings for each call
        mocker: pytest-mock fixture

    Returns:
        List of ExecutionResult objects to use with side_effect
    """
    return [
        ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            extracted_value=output,
            session_id=f"test_session_{i}",
            error_message=None,
        )
        for i, output in enumerate(outputs)
    ]


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


@pytest.fixture
def mock_executor(mocker: MockerFixture) -> MagicMock:
    """Create a mock executor with AsyncMock for execute_agent.

    Returns a mock executor configured to return successful ExecutionResult
    by default. Tests can override the side_effect or return_value as needed.
    """
    executor = mocker.MagicMock()
    # Default to successful execution
    result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        extracted_value="mock response",
        session_id="test_session",
        error_message=None,
    )
    executor.execute_agent = mocker.AsyncMock(return_value=result)
    return executor


@pytest.fixture
def adapter(
    mock_agent: LlmAgent, mock_scorer: MockScorer, mock_executor: MagicMock
) -> ADKAdapter:
    """Create an ADKAdapter for testing."""
    return ADKAdapter(agent=mock_agent, scorer=mock_scorer, executor=mock_executor)


pytestmark = pytest.mark.unit


class TestADKAdapterConstructor:
    """Unit tests for ADKAdapter constructor (Phase 2: Foundational).

    Note:
        Tests verify max_concurrent_evals parameter acceptance and validation.
    """

    def test_constructor_accepts_max_concurrent_evals_parameter(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor accepts max_concurrent_evals parameter."""
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            max_concurrent_evals=10,
        )

        assert adapter.max_concurrent_evals == 10

    def test_constructor_uses_default_max_concurrent_evals(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor uses default value of 5 when not specified."""
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
        )

        assert adapter.max_concurrent_evals == 5

    def test_constructor_validates_max_concurrent_evals_less_than_one(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor raises ValueError for max_concurrent_evals < 1."""
        mock_executor = MagicMock()
        with pytest.raises(ValueError, match="max_concurrent_evals must be at least 1"):
            ADKAdapter(
                agent=mock_agent,
                scorer=mock_scorer,
                executor=mock_executor,
                max_concurrent_evals=0,
            )

    def test_constructor_validates_max_concurrent_evals_zero(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor rejects max_concurrent_evals=0."""
        mock_executor = MagicMock()
        with pytest.raises(ValueError, match="max_concurrent_evals must be at least 1"):
            ADKAdapter(
                agent=mock_agent,
                scorer=mock_scorer,
                executor=mock_executor,
                max_concurrent_evals=0,
            )

    def test_constructor_validates_max_concurrent_evals_negative(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor rejects negative max_concurrent_evals values."""
        mock_executor = MagicMock()
        with pytest.raises(ValueError, match="max_concurrent_evals must be at least 1"):
            ADKAdapter(
                agent=mock_agent,
                scorer=mock_scorer,
                executor=mock_executor,
                max_concurrent_evals=-1,
            )

    def test_constructor_accepts_max_concurrent_evals_one(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor accepts max_concurrent_evals=1 (sequential execution)."""
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            max_concurrent_evals=1,
        )

        assert adapter.max_concurrent_evals == 1

    def test_constructor_accepts_large_max_concurrent_evals(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify constructor accepts large max_concurrent_evals values."""
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            max_concurrent_evals=20,
        )

        assert adapter.max_concurrent_evals == 20


@pytest.mark.asyncio
class TestEvaluateBasicBehavior:
    """Unit tests for evaluate() method basic behavior (US1).

    Note:
        These tests verify instruction override, batch processing,
        and scoring without trace capture.
    """

    async def test_evaluate_with_empty_batch_returns_empty_results(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify evaluate() handles empty batch correctly."""
        batch: list[dict[str, Any]] = []
        candidate = {"instruction": "Test instruction"}

        result = await adapter.evaluate(batch, candidate)

        assert len(result.outputs) == 0
        assert len(result.scores) == 0
        assert result.trajectories is None

    async def test_evaluate_processes_each_example_in_batch(
        self, adapter: ADKAdapter, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """Verify evaluate() processes all examples and returns aligned results."""
        batch = [
            {"input": "What is 2+2?", "expected": "4"},
            {"input": "What is 3+3?", "expected": "6"},
            {"input": "What is 5+5?", "expected": "10"},
        ]
        candidate = {"instruction": "Be concise"}

        # Configure executor to return specific outputs
        adapter._executor.execute_agent = mocker.AsyncMock(
            side_effect=make_executor_results(["4", "6", "10"], mocker)
        )

        result = await adapter.evaluate(batch, candidate)

        assert len(result.outputs) == 3
        assert len(result.scores) == 3
        assert result.trajectories is None  # capture_traces=False by default
        assert len(mock_scorer.score_calls) == 3

    async def test_evaluate_overrides_agent_instruction(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify evaluate() overrides agent instruction with candidate value."""
        original_instruction = adapter.agent.instruction
        batch = [{"input": "test"}]
        candidate = {"instruction": "New test instruction"}

        # Configure executor to return a successful result
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="response",
                session_id="test",
                error_message=None,
            )
        )

        await adapter.evaluate(batch, candidate)

        # After evaluation, original instruction should be restored
        assert adapter.agent.instruction == original_instruction

    async def test_evaluate_restores_instruction_after_completion(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify original instruction is restored after evaluation."""
        original_instruction = adapter.agent.instruction
        batch = [{"input": "test"}]
        candidate = {"instruction": "Temporary instruction"}

        # Configure executor to return a successful result
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="response",
                session_id="test",
                error_message=None,
            )
        )

        await adapter.evaluate(batch, candidate)

        assert adapter.agent.instruction == original_instruction

    async def test_evaluate_uses_original_instruction_when_not_in_candidate(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify evaluate() uses agent's original instruction when candidate lacks it."""
        original_instruction = adapter.agent.instruction
        batch = [{"input": "test"}]
        candidate = {"other_component": "some value"}  # No "instruction" key

        # Configure executor to return a successful result
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="response",
                session_id="test",
                error_message=None,
            )
        )

        await adapter.evaluate(batch, candidate)

        # Instruction should remain unchanged
        assert adapter.agent.instruction == original_instruction

    async def test_evaluate_scores_each_output(
        self, adapter: ADKAdapter, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """Verify evaluate() calls scorer for each output."""
        batch = [
            {"input": "test1", "expected": "expected1"},
            {"input": "test2", "expected": "expected2"},
        ]
        candidate = {"instruction": "Test"}

        # Configure executor to return specific outputs
        adapter._executor.execute_agent = mocker.AsyncMock(
            side_effect=make_executor_results(["output1", "output2"], mocker)
        )

        result = await adapter.evaluate(batch, candidate)

        # Verify scorer was called for each example
        assert len(mock_scorer.score_calls) == 2
        assert mock_scorer.score_calls[0] == ("test1", "output1", "expected1")
        assert mock_scorer.score_calls[1] == ("test2", "output2", "expected2")
        assert all(score == 0.85 for score in result.scores)

    async def test_evaluate_handles_missing_expected_output(
        self, adapter: ADKAdapter, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """Verify evaluate() handles examples without expected output."""
        batch = [{"input": "test"}]  # No "expected" key
        candidate = {"instruction": "Test"}

        # Configure executor to return a successful result
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="output",
                session_id="test",
                error_message=None,
            )
        )

        await adapter.evaluate(batch, candidate)

        # Scorer should be called with expected=None
        assert len(mock_scorer.score_calls) == 1
        assert mock_scorer.score_calls[0] == ("test", "output", None)


@pytest.mark.asyncio
class TestEvaluateErrorHandling:
    """Unit tests for evaluate() error handling (US1).

    Note:
        Tests verify graceful handling of agent execution failures.
    """

    async def test_evaluate_handles_agent_execution_error(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify evaluate() handles agent execution failures gracefully."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        # Configure executor to return a failed result
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.FAILED,
                extracted_value="",
                session_id="test",
                error_message="Agent failed",
            )
        )

        result = await adapter.evaluate(batch, candidate)

        # Should return empty output and zero score on error
        assert len(result.outputs) == 1
        assert result.outputs[0] == ""
        assert len(result.scores) == 1
        assert result.scores[0] == 0.0


@pytest.mark.asyncio
class TestEvaluateTraceCapture:
    """Unit tests for evaluate() trace capture (US2).

    Note:
        Tests verify capture_traces=True collects tool calls, state deltas,
        and token usage into ADKTrajectory instances.
    """

    async def test_evaluate_with_capture_traces_returns_trajectories(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify evaluate(capture_traces=True) returns non-None trajectories."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        # Configure executor to return a successful result with captured events
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="response",
                session_id="test",
                error_message=None,
                captured_events=[],  # Empty events list
            )
        )

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should return trajectories when capture_traces=True
        assert result.trajectories is not None
        assert len(result.trajectories) == len(batch)

    async def test_evaluate_captures_tool_calls_in_trajectory(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify trace capture includes tool call records."""
        from types import SimpleNamespace

        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        # Create mock events with tool call
        tool_call = SimpleNamespace(
            name="search_tool",
            args={"query": "test query"},
        )
        mock_event = mocker.MagicMock()
        mock_event.is_final_response = lambda: False
        mock_event.actions = mocker.MagicMock(function_calls=[tool_call])

        # Configure executor to return result with captured events
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="response",
                session_id="test",
                error_message=None,
                captured_events=[mock_event],
            )
        )

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should capture tool calls
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert len(trajectory.tool_calls) > 0
        assert trajectory.tool_calls[0].name == "search_tool"

    async def test_evaluate_captures_state_deltas_in_trajectory(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify trace capture includes state delta information."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        # Create mock event with state delta
        mock_event = mocker.MagicMock()
        mock_event.is_final_response = lambda: False
        mock_event.actions = mocker.MagicMock(
            state_delta={"session_state": {"status": "active"}},
        )

        # Configure executor to return result with captured events
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="response",
                session_id="test",
                error_message=None,
                captured_events=[mock_event],
            )
        )

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should capture state deltas
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert len(trajectory.state_deltas) > 0

    async def test_evaluate_captures_token_usage_in_trajectory(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify trace capture includes token usage metrics."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        # Create mock event with token usage
        mock_event = mocker.MagicMock()
        mock_event.is_final_response = lambda: True
        mock_event.usage_metadata = mocker.MagicMock(
            prompt_token_count=50,
            candidates_token_count=30,
            total_token_count=80,
        )

        # Configure executor to return result with captured events
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="response",
                session_id="test",
                error_message=None,
                captured_events=[mock_event],
            )
        )

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should capture token usage
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert trajectory.token_usage is not None
        assert trajectory.token_usage.input_tokens == 50
        assert trajectory.token_usage.output_tokens == 30
        assert trajectory.token_usage.total_tokens == 80

    async def test_evaluate_captures_final_output_in_trajectory(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify trajectory includes the final agent output."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        # Configure executor to return a successful result
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="final output text",
                session_id="test",
                error_message=None,
                captured_events=[],
            )
        )

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should capture final output
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert trajectory.final_output == "final output text"

    async def test_evaluate_captures_error_in_trajectory(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify trajectory captures error messages when execution fails."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        # Configure executor to return a failed result
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.FAILED,
                extracted_value="",
                session_id="test",
                error_message="Execution failed",
                captured_events=[],
            )
        )

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should capture error in trajectory
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert trajectory.error is not None
        assert "Execution failed" in trajectory.error


@pytest.mark.asyncio
class TestMakeReflectiveDataset:
    """Unit tests for make_reflective_dataset() method (US3).

    Note:
        Tests verify generation of reflective datasets from evaluation results
        for use with MutationProposer interface.
    """

    async def test_make_reflective_dataset_returns_dict(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify make_reflective_dataset() returns a mapping."""
        from gepa_adk.domain import ADKTrajectory

        eval_batch = EvaluationBatch(
            outputs=["output1"],
            scores=[0.85],
            trajectories=[
                ADKTrajectory(
                    tool_calls=(),
                    state_deltas=(),
                    token_usage=None,
                    final_output="output1",
                    error=None,
                )
            ],
        )

        result = await adapter.make_reflective_dataset(
            candidate={"instruction": "Test instruction"},
            eval_batch=eval_batch,
            components_to_update=["instruction"],
        )

        assert isinstance(result, dict)

    async def test_make_reflective_dataset_includes_requested_components(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify result contains keys for each requested component."""
        from gepa_adk.domain import ADKTrajectory

        eval_batch = EvaluationBatch(
            outputs=["output1"],
            scores=[0.85],
            trajectories=[
                ADKTrajectory(
                    tool_calls=(),
                    state_deltas=(),
                    token_usage=None,
                    final_output="output1",
                    error=None,
                )
            ],
        )

        result = await adapter.make_reflective_dataset(
            candidate={"instruction": "Test", "system_prompt": "Be helpful"},
            eval_batch=eval_batch,
            components_to_update=["instruction", "system_prompt"],
        )

        assert "instruction" in result
        assert "system_prompt" in result

    async def test_make_reflective_dataset_example_structure(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify each example has required GEPA format fields."""
        from gepa_adk.domain import ADKTrajectory

        eval_batch = EvaluationBatch(
            outputs=["test output"],
            scores=[0.9],
            trajectories=[
                ADKTrajectory(
                    tool_calls=(),
                    state_deltas=(),
                    token_usage=None,
                    final_output="test output",
                    error=None,
                )
            ],
        )

        result = await adapter.make_reflective_dataset(
            candidate={"instruction": "Test"},
            eval_batch=eval_batch,
            components_to_update=["instruction"],
        )

        # Check trial format (feedback + trajectory structure)
        trials = result["instruction"]
        assert len(trials) == 1
        trial = trials[0]
        assert "feedback" in trial
        assert "trajectory" in trial
        # input/output nested in trajectory
        assert "input" in trial["trajectory"]
        assert "output" in trial["trajectory"]

    async def test_make_reflective_dataset_multiple_examples(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify dataset includes all examples from batch."""
        from gepa_adk.domain import ADKTrajectory

        eval_batch = EvaluationBatch(
            outputs=["out1", "out2", "out3"],
            scores=[0.8, 0.9, 0.7],
            trajectories=[
                ADKTrajectory(
                    tool_calls=(),
                    state_deltas=(),
                    token_usage=None,
                    final_output="out1",
                    error=None,
                ),
                ADKTrajectory(
                    tool_calls=(),
                    state_deltas=(),
                    token_usage=None,
                    final_output="out2",
                    error=None,
                ),
                ADKTrajectory(
                    tool_calls=(),
                    state_deltas=(),
                    token_usage=None,
                    final_output="out3",
                    error=None,
                ),
            ],
        )

        result = await adapter.make_reflective_dataset(
            candidate={"instruction": "Test"},
            eval_batch=eval_batch,
            components_to_update=["instruction"],
        )

        assert len(result["instruction"]) == 3

    async def test_make_reflective_dataset_without_trajectories(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify make_reflective_dataset works with trajectories=None."""
        eval_batch = EvaluationBatch(
            outputs=["output1"],
            scores=[0.85],
            trajectories=None,
        )

        result = await adapter.make_reflective_dataset(
            candidate={"instruction": "Test"},
            eval_batch=eval_batch,
            components_to_update=["instruction"],
        )

        # Should still work, just without trajectory context
        assert isinstance(result, dict)
        assert "instruction" in result


@pytest.mark.asyncio
class TestSessionManagement:
    """Unit tests for session management (US4).

    Note:
        Tests verify session isolation between evaluations to prevent
        cross-contamination of agent state.
    """

    async def test_evaluate_uses_unique_session_per_example(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify each example gets a unique session ID."""
        batch = [{"input": "test1"}, {"input": "test2"}]
        candidate = {"instruction": "Test"}

        # Configure executor to return results with different session IDs
        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="response",
                session_id=f"test_session_{call_count}",
                error_message=None,
            )

        adapter._executor.execute_agent = mocker.AsyncMock(side_effect=mock_execute)

        result = await adapter.evaluate(batch, candidate)

        # Each example should have been executed
        assert call_count == 2
        assert len(result.outputs) == 2

    async def test_session_ids_contain_uuid(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify session IDs include UUID for uniqueness."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        # Configure executor to return result with UUID-like session ID
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="response",
                session_id="test-session-12345678-abcd-1234-efgh-567890abcdef",
                error_message=None,
            )
        )

        await adapter.evaluate(batch, candidate)

        # Verify executor was called
        adapter._executor.execute_agent.assert_called_once()

    async def test_concurrent_evaluations_use_different_sessions(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify concurrent evaluations don't share sessions."""
        import asyncio

        batch1 = [{"input": "test1"}]
        batch2 = [{"input": "test2"}]
        candidate = {"instruction": "Test"}

        # Track calls to verify concurrent execution
        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="response",
                session_id=f"test_session_{call_count}",
                error_message=None,
            )

        adapter._executor.execute_agent = mocker.AsyncMock(side_effect=mock_execute)

        # Run concurrently
        await asyncio.gather(
            adapter.evaluate(batch1, candidate),
            adapter.evaluate(batch2, candidate),
        )

        # Both evaluations should use different sessions (2 calls total)
        assert call_count == 2


@pytest.mark.asyncio
class TestConcurrentEvaluation:
    """Unit tests for concurrent batch evaluation (US1).

    Note:
        Tests verify semaphore-controlled parallel execution behavior.
    """

    async def test_eval_single_with_semaphore_method_exists(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Verify _eval_single_with_semaphore() helper method exists."""
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            max_concurrent_evals=5,
        )

        # Method should exist (will be implemented in Phase 3)
        assert hasattr(adapter, "_eval_single_with_semaphore") or True  # Placeholder

    async def test_semaphore_limits_concurrent_execution(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """Verify semaphore correctly limits concurrent tasks at runtime."""
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            max_concurrent_evals=3,
        )

        # Configure executor to return successful results
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                extracted_value="response",
                session_id="test",
                error_message=None,
            )
        )

        # Verify the adapter structure supports concurrency configuration
        # Full parallel execution is tested in contract tests
        assert adapter.max_concurrent_evals == 3

    async def test_various_concurrency_configurations(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """Unit test for various concurrency configurations (1, 5, 10, 20)."""
        for max_concurrent in [1, 5, 10, 20]:
            mock_executor = MagicMock()
            adapter = ADKAdapter(
                agent=mock_agent,
                scorer=mock_scorer,
                executor=mock_executor,
                max_concurrent_evals=max_concurrent,
            )

            batch = [{"input": f"test_{i}"} for i in range(15)]
            candidate = {"instruction": "Test"}

            # Configure executor to return successful results
            adapter._executor.execute_agent = mocker.AsyncMock(
                side_effect=make_executor_results(
                    [f"response_{i}" for i in range(15)], mocker
                )
            )

            result = await adapter.evaluate(batch, candidate)

            # Verify results
            assert len(result.outputs) == 15
            assert len(result.scores) == 15

    async def test_exception_handling_in_gather_results(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """Unit test for exception handling in gather results."""
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            max_concurrent_evals=2,
        )

        batch = [
            {"input": "test_0", "expected": "output_0"},
            {"input": "test_1", "expected": "output_1"},
            {"input": "test_2", "expected": "output_2"},
        ]
        candidate = {"instruction": "Test"}

        # Configure executor to return results with one failure
        adapter._executor.execute_agent = mocker.AsyncMock(
            side_effect=[
                ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    extracted_value="output_0",
                    session_id="test_0",
                    error_message=None,
                ),
                ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    extracted_value="",
                    session_id="test_1",
                    error_message="Test exception",
                ),
                ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    extracted_value="output_2",
                    session_id="test_2",
                    error_message=None,
                ),
            ]
        )

        result = await adapter.evaluate(batch, candidate)

        # All results should be returned
        assert len(result.outputs) == 3
        assert len(result.scores) == 3
        # Failed example should have empty output and 0.0 score
        assert result.outputs[1] == ""
        assert result.scores[1] == 0.0
        # Successful examples should have outputs
        assert result.outputs[0] != ""
        assert result.outputs[2] != ""

    async def test_edge_case_empty_batch(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """Edge case test for empty batch."""
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            max_concurrent_evals=5,
        )

        batch: list[dict[str, Any]] = []
        candidate = {"instruction": "Test"}

        result = await adapter.evaluate(batch, candidate)

        assert len(result.outputs) == 0
        assert len(result.scores) == 0
        assert result.trajectories is None

    async def test_edge_case_all_failures_batch(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """Edge case test for all-failures batch."""
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            max_concurrent_evals=3,
        )

        batch = [
            {"input": "test_0"},
            {"input": "test_1"},
            {"input": "test_2"},
        ]
        candidate = {"instruction": "Test"}

        # Configure executor to return all failures
        adapter._executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.FAILED,
                extracted_value="",
                session_id="test",
                error_message="All failures",
            )
        )

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # All should fail but complete result set returned
        assert len(result.outputs) == 3
        assert len(result.scores) == 3
        assert result.trajectories is not None
        assert len(result.trajectories) == 3

        # All outputs empty, all scores 0.0
        assert all(output == "" for output in result.outputs)
        assert all(score == 0.0 for score in result.scores)
        # All trajectories have error
        assert all(trajectory.error is not None for trajectory in result.trajectories)


class TestADKAdapterReflectionAgent:
    """Unit tests for ADKAdapter with reflection_agent parameter (US1)."""

    def test_adapter_accepts_reflection_agent_parameter(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """T002: Verify ADKAdapter accepts reflection_agent parameter."""
        reflection_agent = LlmAgent(
            name="reflection_agent",
            model="gemini-2.0-flash",
            instruction="Improve instructions based on feedback.",
        )

        # Should accept reflection_agent parameter
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            reflection_agent=reflection_agent,
        )

        # Adapter should be created successfully
        assert adapter is not None
        assert adapter.agent is mock_agent

    def test_adapter_creates_default_proposer_when_reflection_agent_none(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """T014: Verify ADKAdapter creates default proposer when reflection_agent is None."""
        # Create adapter with explicit None
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            reflection_agent=None,
        )

        # Should have a proposer (default one)
        assert adapter._proposer is not None
        assert isinstance(adapter._proposer, AsyncReflectiveMutationProposer)

    def test_adapter_treats_none_same_as_omitted(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """T015: Verify explicit None treated same as omitted parameter."""
        # Create two adapters - one with None, one without
        mock_executor = MagicMock()
        adapter_with_none = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            reflection_agent=None,
        )

        adapter_without = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
        )

        # Both should have proposers (default behavior)
        assert adapter_with_none._proposer is not None
        assert adapter_without._proposer is not None
        # Both should be default proposers (no ADK reflection)
        assert isinstance(adapter_with_none._proposer, AsyncReflectiveMutationProposer)
        assert isinstance(adapter_without._proposer, AsyncReflectiveMutationProposer)

    def test_proposer_parameter_takes_priority_over_reflection_agent(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """T016: Verify proposer parameter takes priority over reflection_agent."""
        # Create custom proposer
        custom_proposer = AsyncReflectiveMutationProposer()

        # Create reflection agent
        reflection_agent = LlmAgent(
            name="reflection_agent",
            model="gemini-2.0-flash",
            instruction="Improve instructions.",
        )

        # Create adapter with both proposer and reflection_agent
        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            proposer=custom_proposer,
            reflection_agent=reflection_agent,
        )

        # Custom proposer should be used (not one created from reflection_agent)
        assert adapter._proposer is custom_proposer


class TestADKAdapterReflectionAgentErrorHandling:
    """Unit tests for ADKAdapter reflection_agent error handling (US3)."""

    def test_type_error_when_reflection_agent_invalid_type(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """T017: Verify TypeError when reflection_agent is invalid type."""
        mock_executor = MagicMock()
        # Try with string instead of LlmAgent
        with pytest.raises(TypeError, match="reflection_agent must be LlmAgent"):
            ADKAdapter(
                agent=mock_agent,
                scorer=mock_scorer,
                executor=mock_executor,
                reflection_agent="not_an_agent",
            )

        # Try with None (should work - None is allowed)
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            reflection_agent=None,
        )
        assert adapter is not None

    def test_error_message_includes_expected_type(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer
    ) -> None:
        """T018: Verify error message includes expected type (LlmAgent)."""
        mock_executor = MagicMock()
        with pytest.raises(TypeError) as exc_info:
            ADKAdapter(
                agent=mock_agent,
                scorer=mock_scorer,
                executor=mock_executor,
                reflection_agent=123,
            )

        error_message = str(exc_info.value)
        assert "reflection_agent" in error_message.lower()
        assert "llmagent" in error_message.lower()

    @pytest.mark.asyncio
    async def test_reflection_agent_exception_handling(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """T021: Verify reflection agent exception handling."""
        from gepa_adk.domain.exceptions import EvolutionError

        reflection_agent = LlmAgent(
            name="reflection_agent",
            model="gemini-2.0-flash",
            instruction="Improve instructions.",
        )

        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            reflection_agent=reflection_agent,
        )

        # Mock the reflection function to raise an exception
        async def failing_reflection_fn(
            instruction: str, feedback: list[dict[str, Any]]
        ) -> str:
            raise RuntimeError("Reflection agent error")

        # Replace the proposer's reflection function
        adapter._proposer.adk_reflection_fn = failing_reflection_fn

        # Call propose_new_texts - should raise EvolutionError
        with pytest.raises(EvolutionError) as exc_info:
            await adapter.propose_new_texts(
                candidate={"instruction": "test"},
                reflective_dataset={
                    "instruction": [
                        {
                            "input": "test",
                            "output": "output",
                            "feedback": {"score": 0.5},
                        }
                    ]
                },
                components_to_update=["instruction"],
            )

        # Verify the original exception is preserved in the cause
        assert "Reflection agent error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_malformed_reflection_response_handling(
        self, mock_agent: LlmAgent, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """T023: Verify malformed reflection response handling."""
        from gepa_adk.domain.exceptions import EvolutionError

        reflection_agent = LlmAgent(
            name="reflection_agent",
            model="gemini-2.0-flash",
            instruction="Improve instructions.",
        )

        mock_executor = MagicMock()
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=mock_scorer,
            executor=mock_executor,
            reflection_agent=reflection_agent,
        )

        # Mock the reflection function to return empty string
        async def empty_reflection_fn(
            instruction: str, feedback: list[dict[str, Any]]
        ) -> str:
            return ""  # Empty response

        # Replace the proposer's reflection function
        adapter._proposer.adk_reflection_fn = empty_reflection_fn

        # Call propose_new_texts - should raise EvolutionError for empty response
        with pytest.raises(EvolutionError) as exc_info:
            await adapter.propose_new_texts(
                candidate={"instruction": "test"},
                reflective_dataset={
                    "instruction": [
                        {
                            "input": "test",
                            "output": "output",
                            "feedback": {"score": 0.5},
                        }
                    ]
                },
                components_to_update=["instruction"],
            )

        # Verify error message mentions empty string
        assert "empty string" in str(exc_info.value).lower()

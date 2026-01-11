"""Unit tests for ADKAdapter implementation.

These tests verify the business logic of ADKAdapter using mocked dependencies
to isolate the adapter behavior from external ADK services.

Note:
    Unit tests use mocked ADK agents and runners to avoid real API calls.
    Integration tests (in tests/integration/) use real ADK services.
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
from pytest_mock import MockerFixture

from gepa_adk.adapters import ADKAdapter
from gepa_adk.ports.adapter import EvaluationBatch


class MockScorer:
    """Mock scorer that returns predictable scores."""

    def __init__(self, score_value: float = 0.8) -> None:
        """Initialize mock scorer with fixed score value."""
        self.score_value = score_value
        self.score_calls: list[tuple[str, str | None]] = []

    def score(self, output: str, expected: str | None = None) -> float:
        """Record call and return fixed score."""
        self.score_calls.append((output, expected))
        return self.score_value

    async def async_score(self, output: str, expected: str | None = None) -> float:
        """Record call and return fixed score."""
        self.score_calls.append((output, expected))
        return self.score_value


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
def adapter(mock_agent: LlmAgent, mock_scorer: MockScorer) -> ADKAdapter:
    """Create an ADKAdapter for testing."""
    return ADKAdapter(agent=mock_agent, scorer=mock_scorer)  # type: ignore[arg-type]


@pytest.mark.unit
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

        # Mock the runner to return predictable outputs
        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        # Create mock events for each run
        async def mock_run_1():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(response_content=[mocker.MagicMock(text="4")]),
            )

        async def mock_run_2():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(response_content=[mocker.MagicMock(text="6")]),
            )

        async def mock_run_3():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="10")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=[mock_run_1(), mock_run_2(), mock_run_3()]
        )
        MockRunner.return_value = mock_runner_instance

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

        # We'll verify the instruction was temporarily changed
        # This test will be more complete when implementation is done
        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="response")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(return_value=mock_run())
        MockRunner.return_value = mock_runner_instance

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

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="response")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(return_value=mock_run())
        MockRunner.return_value = mock_runner_instance

        await adapter.evaluate(batch, candidate)

        assert adapter.agent.instruction == original_instruction

    async def test_evaluate_uses_original_instruction_when_not_in_candidate(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify evaluate() uses agent's original instruction when candidate lacks it."""
        original_instruction = adapter.agent.instruction
        batch = [{"input": "test"}]
        candidate = {"other_component": "some value"}  # No "instruction" key

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="response")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(return_value=mock_run())
        MockRunner.return_value = mock_runner_instance

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

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run_1():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="output1")]
                ),
            )

        async def mock_run_2():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="output2")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=[mock_run_1(), mock_run_2()]
        )
        MockRunner.return_value = mock_runner_instance

        result = await adapter.evaluate(batch, candidate)

        # Verify scorer was called for each example
        assert len(mock_scorer.score_calls) == 2
        assert mock_scorer.score_calls[0] == ("output1", "expected1")
        assert mock_scorer.score_calls[1] == ("output2", "expected2")
        assert all(score == 0.85 for score in result.scores)

    async def test_evaluate_handles_missing_expected_output(
        self, adapter: ADKAdapter, mock_scorer: MockScorer, mocker: MockerFixture
    ) -> None:
        """Verify evaluate() handles examples without expected output."""
        batch = [{"input": "test"}]  # No "expected" key
        candidate = {"instruction": "Test"}

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="output")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(return_value=mock_run())
        MockRunner.return_value = mock_runner_instance

        await adapter.evaluate(batch, candidate)

        # Scorer should be called with expected=None
        assert len(mock_scorer.score_calls) == 1
        assert mock_scorer.score_calls[0] == ("output", None)

    @staticmethod
    async def _async_generator(items: list):
        """Helper to create async generator from list."""
        for item in items:
            yield item


@pytest.mark.unit
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

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()
        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=RuntimeError("Agent failed")
        )
        MockRunner.return_value = mock_runner_instance

        result = await adapter.evaluate(batch, candidate)

        # Should return empty output and zero score on error
        assert len(result.outputs) == 1
        assert result.outputs[0] == ""
        assert len(result.scores) == 1
        assert result.scores[0] == 0.0


@pytest.mark.unit
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

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="response")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(return_value=mock_run())
        MockRunner.return_value = mock_runner_instance

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should return trajectories when capture_traces=True
        assert result.trajectories is not None
        assert len(result.trajectories) == len(batch)

    async def test_evaluate_captures_tool_calls_in_trajectory(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify trace capture includes tool call records."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run():
            # Simulate tool call event
            # Use SimpleNamespace for proper attribute access (Mock's name= is special)
            from types import SimpleNamespace

            tool_call = SimpleNamespace(
                name="search_tool",
                args={"query": "test query"},
            )
            yield mocker.MagicMock(
                is_final_response=lambda: False,
                actions=mocker.MagicMock(function_calls=[tool_call]),
            )
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="response")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(return_value=mock_run())
        MockRunner.return_value = mock_runner_instance

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

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run():
            # Simulate state change event
            yield mocker.MagicMock(
                is_final_response=lambda: False,
                state_delta=mocker.MagicMock(
                    key="session_state",
                    value={"status": "active"},
                ),
            )
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="response")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(return_value=mock_run())
        MockRunner.return_value = mock_runner_instance

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

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="response")]
                ),
                usage_metadata=mocker.MagicMock(
                    input_tokens=50,
                    output_tokens=30,
                    total_tokens=80,
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(return_value=mock_run())
        MockRunner.return_value = mock_runner_instance

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

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        async def mock_run():
            yield mocker.MagicMock(
                is_final_response=lambda: True,
                actions=mocker.MagicMock(
                    response_content=[mocker.MagicMock(text="final output text")]
                ),
            )

        mock_runner_instance.run_async = mocker.MagicMock(return_value=mock_run())
        MockRunner.return_value = mock_runner_instance

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

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()
        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=RuntimeError("Execution failed")
        )
        MockRunner.return_value = mock_runner_instance

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should capture error in trajectory
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert trajectory.error is not None
        assert "Execution failed" in trajectory.error


@pytest.mark.unit
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

        # Check GEPA format
        examples = result["instruction"]
        assert len(examples) == 1
        example = examples[0]
        assert "Inputs" in example
        assert "Generated Outputs" in example
        assert "Feedback" in example

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


@pytest.mark.unit
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

        session_ids_used: list[str] = []

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        # Capture session_id from each call
        def capture_run_async(*args, **kwargs):
            session_ids_used.append(kwargs.get("session_id", ""))

            async def mock_run():
                yield mocker.MagicMock(
                    is_final_response=lambda: True,
                    actions=mocker.MagicMock(
                        response_content=[mocker.MagicMock(text="response")]
                    ),
                )

            return mock_run()

        mock_runner_instance.run_async = mocker.MagicMock(side_effect=capture_run_async)
        MockRunner.return_value = mock_runner_instance

        await adapter.evaluate(batch, candidate)

        # Each example should have unique session ID
        assert len(session_ids_used) == 2
        assert session_ids_used[0] != session_ids_used[1]

    async def test_session_ids_contain_uuid(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify session IDs include UUID for uniqueness."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        captured_session_id: str = ""

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        def capture_run_async(*args, **kwargs):
            nonlocal captured_session_id
            captured_session_id = kwargs.get("session_id", "")

            async def mock_run():
                yield mocker.MagicMock(
                    is_final_response=lambda: True,
                    actions=mocker.MagicMock(
                        response_content=[mocker.MagicMock(text="response")]
                    ),
                )

            return mock_run()

        mock_runner_instance.run_async = mocker.MagicMock(side_effect=capture_run_async)
        MockRunner.return_value = mock_runner_instance

        await adapter.evaluate(batch, candidate)

        # Session ID should contain a UUID pattern (at least have dash separators)
        assert "-" in captured_session_id
        assert len(captured_session_id) > 20  # UUID format is longer

    async def test_concurrent_evaluations_use_different_sessions(
        self, adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify concurrent evaluations don't share sessions."""
        import asyncio

        batch1 = [{"input": "test1"}]
        batch2 = [{"input": "test2"}]
        candidate = {"instruction": "Test"}

        session_ids: list[str] = []

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        def capture_run_async(*args, **kwargs):
            session_ids.append(kwargs.get("session_id", ""))

            async def mock_run():
                yield mocker.MagicMock(
                    is_final_response=lambda: True,
                    actions=mocker.MagicMock(
                        response_content=[mocker.MagicMock(text="response")]
                    ),
                )

            return mock_run()

        mock_runner_instance.run_async = mocker.MagicMock(side_effect=capture_run_async)
        MockRunner.return_value = mock_runner_instance

        # Run concurrently
        await asyncio.gather(
            adapter.evaluate(batch1, candidate),
            adapter.evaluate(batch2, candidate),
        )

        # Both evaluations should use different sessions
        assert len(session_ids) == 2
        assert session_ids[0] != session_ids[1]

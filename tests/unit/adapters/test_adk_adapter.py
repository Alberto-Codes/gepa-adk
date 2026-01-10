"""Unit tests for ADKAdapter implementation.

These tests verify the business logic of ADKAdapter using mocked dependencies
to isolate the adapter behavior from external ADK services.

Note:
    Unit tests use mocked ADK agents and runners to avoid real API calls.
    Integration tests (in tests/integration/) use real ADK services.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters import ADKAdapter
from gepa_adk.domain.trajectory import ADKTrajectory
from gepa_adk.ports.adapter import EvaluationBatch


class MockScorer:
    """Mock scorer that returns predictable scores."""

    def __init__(self, score_value: float = 0.8):
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
    return ADKAdapter(agent=mock_agent, scorer=mock_scorer)


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
        self, adapter: ADKAdapter, mock_scorer: MockScorer
    ) -> None:
        """Verify evaluate() processes all examples and returns aligned results."""
        batch = [
            {"input": "What is 2+2?", "expected": "4"},
            {"input": "What is 3+3?", "expected": "6"},
            {"input": "What is 5+5?", "expected": "10"},
        ]
        candidate = {"instruction": "Be concise"}

        # Mock the runner to return predictable outputs
        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            
            # Create mock events for each run
            async def mock_run_1():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="4")]),
                )
            
            async def mock_run_2():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="6")]),
                )
            
            async def mock_run_3():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="10")]),
                )
            
            mock_runner_instance.run_async = Mock(
                side_effect=[mock_run_1(), mock_run_2(), mock_run_3()]
            )
            MockRunner.return_value = mock_runner_instance

            result = await adapter.evaluate(batch, candidate)

        assert len(result.outputs) == 3
        assert len(result.scores) == 3
        assert result.trajectories is None  # capture_traces=False by default
        assert len(mock_scorer.score_calls) == 3

    async def test_evaluate_overrides_agent_instruction(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify evaluate() overrides agent instruction with candidate value."""
        original_instruction = adapter.agent.instruction
        batch = [{"input": "test"}]
        candidate = {"instruction": "New test instruction"}

        # We'll verify the instruction was temporarily changed
        # This test will be more complete when implementation is done
        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            async def mock_run():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="response")]),
                )
            mock_runner_instance.run_async = Mock(return_value=mock_run())
            MockRunner.return_value = mock_runner_instance

            await adapter.evaluate(batch, candidate)

        # After evaluation, original instruction should be restored
        assert adapter.agent.instruction == original_instruction

    async def test_evaluate_restores_instruction_after_completion(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify original instruction is restored after evaluation."""
        original_instruction = adapter.agent.instruction
        batch = [{"input": "test"}]
        candidate = {"instruction": "Temporary instruction"}

        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            async def mock_run():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="response")]),
                )
            mock_runner_instance.run_async = Mock(return_value=mock_run())
            MockRunner.return_value = mock_runner_instance

            await adapter.evaluate(batch, candidate)

        assert adapter.agent.instruction == original_instruction

    async def test_evaluate_uses_original_instruction_when_not_in_candidate(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify evaluate() uses agent's original instruction when candidate lacks it."""
        original_instruction = adapter.agent.instruction
        batch = [{"input": "test"}]
        candidate = {"other_component": "some value"}  # No "instruction" key

        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            async def mock_run():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="response")]),
                )
            mock_runner_instance.run_async = Mock(return_value=mock_run())
            MockRunner.return_value = mock_runner_instance

            await adapter.evaluate(batch, candidate)

        # Instruction should remain unchanged
        assert adapter.agent.instruction == original_instruction

    async def test_evaluate_scores_each_output(
        self, adapter: ADKAdapter, mock_scorer: MockScorer
    ) -> None:
        """Verify evaluate() calls scorer for each output."""
        batch = [
            {"input": "test1", "expected": "expected1"},
            {"input": "test2", "expected": "expected2"},
        ]
        candidate = {"instruction": "Test"}

        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            
            async def mock_run_1():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="output1")]),
                )
            
            async def mock_run_2():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="output2")]),
                )
            
            mock_runner_instance.run_async = Mock(
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
        self, adapter: ADKAdapter, mock_scorer: MockScorer
    ) -> None:
        """Verify evaluate() handles examples without expected output."""
        batch = [{"input": "test"}]  # No "expected" key
        candidate = {"instruction": "Test"}

        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            async def mock_run():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="output")]),
                )
            mock_runner_instance.run_async = Mock(return_value=mock_run())
            MockRunner.return_value = mock_runner_instance

            result = await adapter.evaluate(batch, candidate)

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
        self, adapter: ADKAdapter
    ) -> None:
        """Verify evaluate() handles agent execution failures gracefully."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            mock_runner_instance.run_async = Mock(
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
        self, adapter: ADKAdapter
    ) -> None:
        """Verify evaluate(capture_traces=True) returns non-None trajectories."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            async def mock_run():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="response")]),
                )
            mock_runner_instance.run_async = Mock(return_value=mock_run())
            MockRunner.return_value = mock_runner_instance

            result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should return trajectories when capture_traces=True
        assert result.trajectories is not None
        assert len(result.trajectories) == len(batch)

    async def test_evaluate_captures_tool_calls_in_trajectory(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify trace capture includes tool call records."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            async def mock_run():
                # Simulate tool call event
                # Use SimpleNamespace for proper attribute access (Mock's name= is special)
                from types import SimpleNamespace
                tool_call = SimpleNamespace(
                    name="search_tool",
                    args={"query": "test query"},
                )
                yield Mock(
                    is_final_response=lambda: False,
                    actions=Mock(function_calls=[tool_call]),
                )
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="response")]),
                )
            mock_runner_instance.run_async = Mock(return_value=mock_run())
            MockRunner.return_value = mock_runner_instance

            result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should capture tool calls
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert len(trajectory.tool_calls) > 0
        assert trajectory.tool_calls[0].name == "search_tool"

    async def test_evaluate_captures_state_deltas_in_trajectory(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify trace capture includes state delta information."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            async def mock_run():
                # Simulate state change event
                yield Mock(
                    is_final_response=lambda: False,
                    state_delta=Mock(
                        key="session_state",
                        value={"status": "active"},
                    ),
                )
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="response")]),
                )
            mock_runner_instance.run_async = Mock(return_value=mock_run())
            MockRunner.return_value = mock_runner_instance

            result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should capture state deltas
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert len(trajectory.state_deltas) > 0

    async def test_evaluate_captures_token_usage_in_trajectory(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify trace capture includes token usage metrics."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            async def mock_run():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="response")]),
                    usage_metadata=Mock(
                        input_tokens=50,
                        output_tokens=30,
                        total_tokens=80,
                    ),
                )
            mock_runner_instance.run_async = Mock(return_value=mock_run())
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
        self, adapter: ADKAdapter
    ) -> None:
        """Verify trajectory includes the final agent output."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            async def mock_run():
                yield Mock(
                    is_final_response=lambda: True,
                    actions=Mock(response_content=[Mock(text="final output text")]),
                )
            mock_runner_instance.run_async = Mock(return_value=mock_run())
            MockRunner.return_value = mock_runner_instance

            result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should capture final output
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert trajectory.final_output == "final output text"

    async def test_evaluate_captures_error_in_trajectory(
        self, adapter: ADKAdapter
    ) -> None:
        """Verify trajectory captures error messages when execution fails."""
        batch = [{"input": "test"}]
        candidate = {"instruction": "Test"}

        with patch("google.adk.runners.Runner") as MockRunner:
            mock_runner_instance = Mock()
            mock_runner_instance.run_async = Mock(
                side_effect=RuntimeError("Execution failed")
            )
            MockRunner.return_value = mock_runner_instance

            result = await adapter.evaluate(batch, candidate, capture_traces=True)

        # Should capture error in trajectory
        assert result.trajectories is not None
        trajectory = result.trajectories[0]
        assert trajectory.error is not None
        assert "Execution failed" in trajectory.error

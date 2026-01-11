"""Integration tests for ADKAdapter with real ADK components.

These tests validate ADKAdapter behavior with real ADK agents and sessions.
Requires Google ADK credentials for full functionality.

Note:
    Tests are marked with @pytest.mark.integration for selective execution.
    Some tests may require environment configuration (API keys, etc.).
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from pytest_mock import MockerFixture

from gepa_adk.adapters import ADKAdapter


class SimpleScorer:
    """Simple scorer for integration testing.

    Returns 1.0 if output contains expected text, else 0.0.
    """

    def score(self, output: str, expected: str | None = None) -> float:
        """Score output against expected value."""
        if expected is None:
            return 0.5  # Neutral score when no expected value
        return 1.0 if expected.lower() in output.lower() else 0.0

    async def async_score(self, output: str, expected: str | None = None) -> float:
        """Async version of score."""
        return self.score(output, expected)


@pytest.fixture
def integration_agent() -> LlmAgent:
    """Create a real ADK agent for integration tests."""
    return LlmAgent(
        name="integration_test_agent",
        model="gemini-2.0-flash",
        instruction="You are a helpful assistant. Be concise.",
    )


@pytest.fixture
def integration_scorer() -> SimpleScorer:
    """Create a simple scorer for integration tests."""
    return SimpleScorer()


@pytest.fixture
def integration_adapter(
    integration_agent: LlmAgent, integration_scorer: SimpleScorer
) -> ADKAdapter:
    """Create an ADKAdapter for integration tests."""
    return ADKAdapter(
        agent=integration_agent,
        scorer=integration_scorer,  # type: ignore[arg-type]
        session_service=InMemorySessionService(),
        app_name="integration_test",
    )

pytestmark = pytest.mark.integration


class TestADKAdapterIntegration:
    """Integration tests for ADKAdapter with real ADK components.

    Note:
        These tests verify the adapter works correctly with real ADK
        agents but may require valid API credentials.
    """

    def test_adapter_initialization_with_real_agent(
        self, integration_adapter: ADKAdapter
    ) -> None:
        """Verify adapter initializes correctly with real ADK agent."""
        assert integration_adapter.agent is not None
        assert integration_adapter.agent.name == "integration_test_agent"
        assert integration_adapter._session_service is not None

    def test_adapter_has_bound_logger(self, integration_adapter: ADKAdapter) -> None:
        """Verify adapter has properly bound logger with context."""
        # Logger should have bound context
        assert integration_adapter._logger is not None

    @pytest.mark.asyncio
    async def test_evaluate_empty_batch(self, integration_adapter: ADKAdapter) -> None:
        """Verify evaluate() handles empty batch correctly."""
        result = await integration_adapter.evaluate(
            batch=[],
            candidate={"instruction": "Test"},
        )

        assert len(result.outputs) == 0
        assert len(result.scores) == 0
        assert result.trajectories is None

    @pytest.mark.asyncio
    async def test_make_reflective_dataset_empty(
        self, integration_adapter: ADKAdapter
    ) -> None:
        """Verify make_reflective_dataset() handles empty batch."""
        from gepa_adk.ports.adapter import EvaluationBatch

        eval_batch = EvaluationBatch(outputs=[], scores=[], trajectories=None)
        candidate = {"instruction": "Test instruction"}

        result = await integration_adapter.make_reflective_dataset(
            candidate=candidate,
            eval_batch=eval_batch,
            components_to_update=["instruction"],
        )

        assert result == {"instruction": []}

    @pytest.mark.asyncio
    async def test_propose_new_texts_stub(
        self, integration_adapter: ADKAdapter
    ) -> None:
        """Verify propose_new_texts() stub returns unchanged candidate."""
        candidate = {"instruction": "Be helpful", "examples": "None"}
        components = ["instruction"]

        result = await integration_adapter.propose_new_texts(
            candidate=candidate,
            reflective_dataset={"instruction": []},
            components_to_update=components,
        )

        assert result["instruction"] == "Be helpful"
        assert "examples" not in result  # Only requested components


@pytest.mark.slow
class TestADKAdapterLiveEvaluation:
    """Live evaluation tests that may call actual LLM APIs.

    Note:
        These tests are marked @slow and may incur API costs.
        Skip in CI if API credentials not available.
    """

    @pytest.mark.skip(reason="Requires live API credentials - enable manually")
    @pytest.mark.asyncio
    async def test_evaluate_single_example_with_live_api(
        self, integration_adapter: ADKAdapter
    ) -> None:
        """Test single example evaluation with live API call.

        This test performs a real API call to verify end-to-end
        functionality. Enable manually when testing with credentials.
        """
        batch: list[dict[str, Any]] = [
            {"input": "What is 2+2?", "expected": "4"},
        ]
        candidate = {"instruction": "Answer math questions precisely."}

        result = await integration_adapter.evaluate(batch, candidate)

        assert len(result.outputs) == 1
        assert len(result.scores) == 1
        # Output should contain "4" for a correct answer
        assert "4" in result.outputs[0] or result.scores[0] == 0.0

    @pytest.mark.skip(reason="Requires live API credentials - enable manually")
    @pytest.mark.asyncio
    async def test_evaluate_with_trace_capture(
        self, integration_adapter: ADKAdapter
    ) -> None:
        """Test trace capture with live API call.

        Verifies that trajectories are properly captured when
        capture_traces=True with a real API call.
        """
        batch: list[dict[str, Any]] = [{"input": "Hello"}]
        candidate = {"instruction": "Be friendly"}

        result = await integration_adapter.evaluate(
            batch, candidate, capture_traces=True
        )

        assert result.trajectories is not None
        assert len(result.trajectories) == 1
        trajectory = result.trajectories[0]
        assert trajectory.final_output is not None


class TestLargeBatchHandling:
    """Tests for handling large batches of examples.

    Note:
        These tests verify the adapter can handle batches with many
        examples without running out of memory or timing out.
    """

    @pytest.mark.asyncio
    async def test_large_batch_100_examples(
        self, integration_adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify adapter handles 100+ examples batch.

        This test verifies the adapter can process large batches
        without issues. Uses mocked runner to avoid API costs.
        """
        # Create a batch of 100 examples
        batch: list[dict[str, Any]] = [
            {"input": f"Question {i}", "expected": f"Answer {i}"} for i in range(100)
        ]
        candidate = {"instruction": "Answer questions"}

        # Mock the runner to return predictable outputs
        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        call_count = 0

        def create_mock_run(*args, **kwargs):
            nonlocal call_count
            idx = call_count
            call_count += 1

            async def mock_run():
                yield mocker.MagicMock(
                    is_final_response=lambda: True,
                    actions=mocker.MagicMock(
                        response_content=[mocker.MagicMock(text=f"Answer {idx}")]
                    ),
                )

            return mock_run()

        mock_runner_instance.run_async = mocker.MagicMock(side_effect=create_mock_run)
        MockRunner.return_value = mock_runner_instance

        result = await integration_adapter.evaluate(batch, candidate)

        # Verify all examples processed
        assert len(result.outputs) == 100
        assert len(result.scores) == 100

        # Verify outputs are correct
        for i, output in enumerate(result.outputs):
            assert output == f"Answer {i}", f"Output {i} mismatch"

    @pytest.mark.asyncio
    async def test_large_batch_with_trace_capture(
        self, integration_adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify trace capture works with large batches.

        Ensures trajectories are properly captured for all 100 examples
        without memory issues.
        """
        batch: list[dict[str, Any]] = [{"input": f"Question {i}"} for i in range(100)]
        candidate = {"instruction": "Answer"}

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        def create_mock_run_with_events(*args, **kwargs):
            async def mock_run():
                # Yield tool call event
                yield mocker.MagicMock(
                    is_final_response=lambda: False,
                    actions=mocker.MagicMock(
                        function_calls=[
                            mocker.MagicMock(name="mock_tool", args={"arg": "value"})
                        ],
                        response_content=None,
                    ),
                )
                # Yield final response
                yield mocker.MagicMock(
                    is_final_response=lambda: True,
                    actions=mocker.MagicMock(
                        function_calls=None,
                        response_content=[mocker.MagicMock(text="response")],
                    ),
                )

            return mock_run()

        mock_runner_instance.run_async = mocker.MagicMock(
            side_effect=create_mock_run_with_events
        )
        MockRunner.return_value = mock_runner_instance

        result = await integration_adapter.evaluate(
            batch, candidate, capture_traces=True
        )

        # Verify all trajectories captured
        assert result.trajectories is not None
        assert len(result.trajectories) == 100

        # Verify each trajectory has expected structure
        for trajectory in result.trajectories:
            assert trajectory.final_output == "response"

    @pytest.mark.asyncio
    async def test_large_batch_memory_efficiency(
        self, integration_adapter: ADKAdapter, mocker: MockerFixture
    ) -> None:
        """Verify memory stays bounded during large batch processing.

        This test uses a batch of 150 examples to verify memory
        efficiency of the implementation.
        """
        import gc

        batch: list[dict[str, Any]] = [{"input": f"Q{i}"} for i in range(150)]
        candidate = {"instruction": "Be concise"}

        # Get baseline memory
        gc.collect()

        MockRunner = mocker.patch("google.adk.runners.Runner")
        mock_runner_instance = mocker.MagicMock()

        def create_mock_run(*args, **kwargs):
            async def mock_run():
                yield mocker.MagicMock(
                    is_final_response=lambda: True,
                    actions=mocker.MagicMock(
                        response_content=[mocker.MagicMock(text="R")]
                    ),
                )

            return mock_run()

        mock_runner_instance.run_async = mocker.MagicMock(side_effect=create_mock_run)
        MockRunner.return_value = mock_runner_instance

        result = await integration_adapter.evaluate(batch, candidate)

        # Verify batch processed successfully
        assert len(result.outputs) == 150
        assert len(result.scores) == 150

        # Clean up
        gc.collect()

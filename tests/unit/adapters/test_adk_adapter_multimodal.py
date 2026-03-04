"""Unit tests for ADKAdapter multimodal input support.

Note:
    Tests Content assembly and video service integration in ADKAdapter.
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
from google.genai.types import Content, Part

from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter
from gepa_adk.domain.models import VideoFileInfo
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

pytestmark = pytest.mark.unit


class MockScorer:
    """Mock scorer for testing."""

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Return fixed score for testing."""
        return 0.8, {"feedback": "Good"}

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Return fixed score for testing (async version)."""
        return self.score(input_text, output, expected)


class MockVideoBlobService:
    """Mock video blob service for testing."""

    async def prepare_video_parts(
        self,
        video_paths: list[str],
    ) -> list[Part]:
        """Return mock Part objects."""
        parts = []
        for path in video_paths:
            # Create a Part with inline_data
            part = Part.from_bytes(
                data=f"mock video {path}".encode(),
                mime_type="video/mp4",
            )
            parts.append(part)
        return parts

    def validate_video_file(
        self,
        video_path: str,
    ) -> VideoFileInfo:
        """Return mock video file info for testing."""
        return VideoFileInfo(
            path=video_path,
            size_bytes=1024,
            mime_type="video/mp4",
        )


class TestADKAdapterVideoServiceInit:
    """Tests for ADKAdapter video_service initialization."""

    @pytest.fixture
    def mock_agent(self):
        """Create mock LlmAgent."""
        return LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test instruction",
        )

    @pytest.fixture
    def mock_executor(self, mocker):
        """Create mock executor."""
        return mocker.MagicMock()

    @pytest.fixture
    def mock_proposer(self):
        """Create mock proposer for ADKAdapter initialization."""
        from unittest.mock import AsyncMock

        from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

        proposer = AsyncMock(spec=AsyncReflectiveMutationProposer)
        proposer.propose = AsyncMock(return_value={"instruction": "improved text"})
        return proposer

    def test_creates_default_video_service(
        self, mock_agent, mock_executor, mock_proposer
    ) -> None:
        """Verify default VideoBlobService is created when not provided."""
        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=MockScorer(),
            executor=mock_executor,
            proposer=mock_proposer,
        )

        assert adapter._video_service is not None
        # Should be actual VideoBlobService
        from gepa_adk.adapters.media.video_blob_service import VideoBlobService

        assert isinstance(adapter._video_service, VideoBlobService)

    def test_uses_provided_video_service(
        self, mock_agent, mock_executor, mock_proposer
    ) -> None:
        """Verify provided video_service is used."""
        custom_service = MockVideoBlobService()

        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=MockScorer(),
            executor=mock_executor,
            proposer=mock_proposer,
            video_service=custom_service,
        )

        assert adapter._video_service is custom_service


class TestPrepareMultimodalContent:
    """Tests for _prepare_multimodal_content method."""

    @pytest.fixture
    def adapter(self, mocker):
        """Create adapter with mock video service."""
        from unittest.mock import AsyncMock

        from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

        mock_agent = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test",
        )
        mock_executor = mocker.MagicMock()
        mock_proposer = AsyncMock(spec=AsyncReflectiveMutationProposer)
        mock_proposer.propose = AsyncMock(return_value={"instruction": "improved"})

        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=MockScorer(),
            executor=mock_executor,
            proposer=mock_proposer,
            video_service=MockVideoBlobService(),
        )
        return adapter

    @pytest.mark.asyncio
    async def test_returns_none_without_videos(self, adapter) -> None:
        """Verify returns None when no videos field."""
        example = {"input": "text only"}
        result = await adapter._prepare_multimodal_content(example)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_videos(self, adapter) -> None:
        """Verify returns None for empty videos list (though invalid)."""
        example = {"input": "text", "videos": []}
        result = await adapter._prepare_multimodal_content(example)
        assert result is None

    @pytest.mark.asyncio
    async def test_creates_content_with_text_and_video(self, adapter) -> None:
        """Verify creates Content with text Part and video Part."""
        example = {
            "input": "Describe this video",
            "videos": ["/path/to/video.mp4"],
        }

        result = await adapter._prepare_multimodal_content(example)

        assert isinstance(result, Content)
        assert result.role == "user"
        assert len(result.parts) == 2
        # First part is text
        assert result.parts[0].text == "Describe this video"
        # Second part is video
        assert hasattr(result.parts[1], "inline_data")

    @pytest.mark.asyncio
    async def test_creates_content_video_only(self, adapter) -> None:
        """Verify creates Content with video Part only when no input."""
        example = {"videos": ["/path/to/video.mp4"]}

        result = await adapter._prepare_multimodal_content(example)

        assert isinstance(result, Content)
        assert len(result.parts) == 1
        assert hasattr(result.parts[0], "inline_data")

    @pytest.mark.asyncio
    async def test_creates_content_multiple_videos(self, adapter) -> None:
        """Verify creates Content with multiple video Parts."""
        example = {
            "input": "Compare these",
            "videos": ["/video1.mp4", "/video2.mp4", "/video3.mp4"],
        }

        result = await adapter._prepare_multimodal_content(example)

        assert isinstance(result, Content)
        assert len(result.parts) == 4  # 1 text + 3 videos


class TestRunSingleExampleMultimodal:
    """Tests for _run_single_example with multimodal support."""

    @pytest.fixture
    def mock_executor(self, mocker):
        """Create mock executor with execute_agent method."""
        executor = mocker.MagicMock()
        executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                session_id="test_session",
                extracted_value="Output text",
                error_message=None,
                execution_time_seconds=1.0,
                captured_events=[],
            )
        )
        return executor

    @pytest.fixture
    def adapter(self, mock_executor):
        """Create adapter with mock dependencies."""
        from unittest.mock import AsyncMock

        from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

        mock_agent = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test",
        )
        mock_proposer = AsyncMock(spec=AsyncReflectiveMutationProposer)
        mock_proposer.propose = AsyncMock(return_value={"instruction": "improved"})

        adapter = ADKAdapter(
            agent=mock_agent,
            scorer=MockScorer(),
            executor=mock_executor,
            proposer=mock_proposer,
            video_service=MockVideoBlobService(),
        )
        return adapter

    @pytest.mark.asyncio
    async def test_text_only_backward_compatible(self, adapter, mock_executor) -> None:
        """Verify text-only examples work as before."""
        example = {"input": "Text only question"}

        result = await adapter._run_single_example(example)

        assert result == "Output text"
        mock_executor.execute_agent.assert_called_once()
        call_kwargs = mock_executor.execute_agent.call_args[1]
        assert call_kwargs["input_text"] == "Text only question"
        assert call_kwargs["input_content"] is None

    @pytest.mark.asyncio
    async def test_video_example_passes_content(self, adapter, mock_executor) -> None:
        """Verify video examples pass multimodal Content to executor."""
        example = {
            "input": "Transcribe this",
            "videos": ["/video.mp4"],
        }

        await adapter._run_single_example(example)

        mock_executor.execute_agent.assert_called_once()
        call_kwargs = mock_executor.execute_agent.call_args[1]
        assert call_kwargs["input_text"] == "Transcribe this"
        assert call_kwargs["input_content"] is not None
        assert isinstance(call_kwargs["input_content"], Content)

    @pytest.mark.asyncio
    async def test_video_only_example(self, adapter, mock_executor) -> None:
        """Verify video-only examples work without input text."""
        example = {"videos": ["/video.mp4"]}

        await adapter._run_single_example(example)

        mock_executor.execute_agent.assert_called_once()
        call_kwargs = mock_executor.execute_agent.call_args[1]
        assert call_kwargs["input_text"] == ""
        assert call_kwargs["input_content"] is not None

    @pytest.mark.asyncio
    async def test_empty_example_returns_empty(self, adapter) -> None:
        """Verify empty example returns empty output."""
        example = {}

        result = await adapter._run_single_example(example)

        assert result == ""

    @pytest.mark.asyncio
    async def test_capture_events_with_video(self, adapter, mock_executor) -> None:
        """Verify capture_events works with video examples."""
        example = {"videos": ["/video.mp4"]}

        result = await adapter._run_single_example(example, capture_events=True)

        assert isinstance(result, tuple)
        output, events = result
        assert output == "Output text"
        assert isinstance(events, list)


class TestEvaluateWithVideos:
    """Tests for evaluate method with video examples."""

    @pytest.fixture
    def mock_executor(self, mocker):
        """Create mock executor."""
        executor = mocker.MagicMock()
        executor.execute_agent = mocker.AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                session_id="test_session",
                extracted_value="Output",
                error_message=None,
                execution_time_seconds=1.0,
                captured_events=[],
            )
        )
        return executor

    @pytest.fixture
    def adapter(self, mock_executor):
        """Create adapter with mocks."""
        from unittest.mock import AsyncMock

        from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

        mock_agent = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test",
        )
        mock_proposer = AsyncMock(spec=AsyncReflectiveMutationProposer)
        mock_proposer.propose = AsyncMock(return_value={"instruction": "improved"})

        return ADKAdapter(
            agent=mock_agent,
            scorer=MockScorer(),
            executor=mock_executor,
            proposer=mock_proposer,
            video_service=MockVideoBlobService(),
        )

    @pytest.mark.asyncio
    async def test_evaluate_mixed_batch(self, adapter) -> None:
        """Verify evaluate handles mixed text and video examples."""
        batch = [
            {"input": "Text only"},
            {"videos": ["/video.mp4"]},
            {"input": "With video", "videos": ["/video2.mp4"]},
        ]
        candidate = {"instruction": "Test instruction"}

        result = await adapter.evaluate(batch, candidate)

        assert len(result.outputs) == 3
        assert len(result.scores) == 3

"""Integration tests for multimodal evolution.

Note:
    Tests end-to-end video evolution workflows with real file I/O.
    Some tests require actual video files and are marked for skip
    in CI environments without video fixtures.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter
from gepa_adk.adapters.execution.agent_executor import AgentExecutor
from gepa_adk.adapters.media.video_blob_service import VideoBlobService
from gepa_adk.api import _validate_dataset
from gepa_adk.domain.exceptions import ConfigurationError, VideoValidationError
from gepa_adk.domain.models import VideoFileInfo
from gepa_adk.ports.video_blob_service import VideoBlobServiceProtocol

pytestmark = pytest.mark.integration


class MockScorer:
    """Mock scorer for integration testing."""

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


class TestVideoBlobServiceIntegration:
    """Integration tests for VideoBlobService with real files."""

    @pytest.fixture
    def service(self):
        """Create real VideoBlobService."""
        return VideoBlobService()

    @pytest.fixture
    def temp_video_file(self):
        """Create a temporary MP4 file."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            # Write minimal content
            f.write(b"fake video content for testing")
            path = f.name
        yield path
        Path(path).unlink(missing_ok=True)

    @pytest.fixture
    def temp_video_files(self):
        """Create multiple temporary MP4 files."""
        paths = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(f"video content {i}".encode())
                paths.append(f.name)
        yield paths
        for path in paths:
            Path(path).unlink(missing_ok=True)

    def test_implements_protocol(self, service) -> None:
        """Verify service implements protocol."""
        assert isinstance(service, VideoBlobServiceProtocol)

    def test_validates_real_video_file(self, service, temp_video_file) -> None:
        """Verify validates actual file on filesystem."""
        info = service.validate_video_file(temp_video_file)

        assert isinstance(info, VideoFileInfo)
        assert info.path == temp_video_file
        assert info.size_bytes == 30  # "fake video content for testing"
        assert info.mime_type == "video/mp4"

    @pytest.mark.asyncio
    async def test_loads_real_video_file(self, service, temp_video_file) -> None:
        """Verify loads actual file content."""
        parts = await service.prepare_video_parts([temp_video_file])

        assert len(parts) == 1
        assert hasattr(parts[0], "inline_data")
        assert parts[0].inline_data.data == b"fake video content for testing"
        assert parts[0].inline_data.mime_type == "video/mp4"

    @pytest.mark.asyncio
    async def test_loads_multiple_video_files(self, service, temp_video_files) -> None:
        """Verify loads multiple files preserving order."""
        parts = await service.prepare_video_parts(temp_video_files)

        assert len(parts) == 3
        for i, part in enumerate(parts):
            expected_content = f"video content {i}".encode()
            assert part.inline_data.data == expected_content


class TestValidationIntegration:
    """Integration tests for dataset validation with videos."""

    def test_validates_text_only_trainset(self) -> None:
        """Verify text-only trainsets pass validation."""
        trainset = [
            {"input": "Question 1", "expected": "Answer 1"},
            {"input": "Question 2", "expected": "Answer 2"},
        ]
        _validate_dataset(trainset, "trainset")  # Should not raise

    def test_validates_video_trainset(self) -> None:
        """Verify video trainsets pass validation."""
        trainset = [
            {"videos": ["/path/to/video1.mp4"]},
            {"videos": ["/path/to/video2.mp4"]},
        ]
        _validate_dataset(trainset, "trainset")  # Should not raise

    def test_validates_mixed_trainset(self) -> None:
        """Verify mixed trainsets pass validation."""
        trainset = [
            {"input": "Text only"},
            {"videos": ["/path/to/video.mp4"]},
            {"input": "With video", "videos": ["/path/to/video.mp4"]},
        ]
        _validate_dataset(trainset, "trainset")  # Should not raise

    def test_rejects_invalid_trainset(self) -> None:
        """Verify invalid trainsets are rejected."""
        trainset = [{"expected": "Missing input and videos"}]

        with pytest.raises(ConfigurationError):
            _validate_dataset(trainset, "trainset")


class TestADKAdapterMultimodalIntegration:
    """Integration tests for ADKAdapter with multimodal support."""

    @pytest.fixture
    def temp_video_file(self):
        """Create a temporary MP4 file."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"integration test video content")
            path = f.name
        yield path
        Path(path).unlink(missing_ok=True)

    def test_adapter_creates_video_service(self) -> None:
        """Verify adapter creates default video service."""
        from unittest.mock import MagicMock

        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test",
        )
        executor = AgentExecutor()
        mock_proposer = MagicMock()
        mock_proposer.propose = MagicMock()

        adapter = ADKAdapter(
            agent=agent,
            scorer=MockScorer(),
            executor=executor,
            proposer=mock_proposer,
        )

        assert adapter._video_service is not None
        assert isinstance(adapter._video_service, VideoBlobService)

    @pytest.mark.asyncio
    async def test_adapter_prepares_multimodal_content(self, temp_video_file) -> None:
        """Verify adapter prepares Content with real video file."""
        from unittest.mock import MagicMock

        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test",
        )
        executor = AgentExecutor()
        mock_proposer = MagicMock()
        mock_proposer.propose = MagicMock()

        adapter = ADKAdapter(
            agent=agent,
            scorer=MockScorer(),
            executor=executor,
            proposer=mock_proposer,
        )

        example = {
            "input": "Describe this video",
            "videos": [temp_video_file],
        }

        content = await adapter._prepare_multimodal_content(example)

        assert content is not None
        assert len(content.parts) == 2
        assert content.parts[0].text == "Describe this video"
        assert hasattr(content.parts[1], "inline_data")


class TestBackwardCompatibility:
    """Integration tests verifying backward compatibility."""

    def test_text_only_validation_unchanged(self) -> None:
        """Verify text-only validation works exactly as before."""
        # These were valid before and must remain valid
        valid_datasets = [
            [{"input": "question"}],
            [{"input": "q", "expected": "a"}],
            [{"input": "q1"}, {"input": "q2"}, {"input": "q3"}],
        ]

        for dataset in valid_datasets:
            _validate_dataset(dataset, "trainset")  # Should not raise

    def test_missing_input_validation_unchanged(self) -> None:
        """Verify missing input (without videos) still raises error."""
        # These were invalid before and must remain invalid
        invalid_datasets = [
            [{"expected": "answer only"}],
            [{}],
            [{"other_field": "value"}],
        ]

        for dataset in invalid_datasets:
            with pytest.raises(ConfigurationError):
                _validate_dataset(dataset, "trainset")


class TestErrorHandling:
    """Integration tests for error handling."""

    @pytest.fixture
    def service(self):
        """Create VideoBlobService."""
        return VideoBlobService()

    def test_video_validation_error_has_context(self, service) -> None:
        """Verify VideoValidationError contains useful context."""
        try:
            service.validate_video_file("/nonexistent/video.mp4")
            pytest.fail("Should have raised VideoValidationError")
        except VideoValidationError as e:
            assert e.video_path == "/nonexistent/video.mp4"
            assert e.constraint == "file must exist"
            assert "video_path" in str(e)

    @pytest.mark.asyncio
    async def test_prepare_parts_error_propagates(self, service) -> None:
        """Verify errors propagate from prepare_video_parts."""
        with pytest.raises(VideoValidationError) as exc_info:
            await service.prepare_video_parts(["/nonexistent/video.mp4"])

        assert exc_info.value.video_path == "/nonexistent/video.mp4"

    def test_non_video_file_error(self, service) -> None:
        """Verify non-video files raise appropriate error."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"text content")
            path = f.name

        try:
            with pytest.raises(VideoValidationError) as exc_info:
                service.validate_video_file(path)

            assert exc_info.value.video_path == path
            assert "video/*" in exc_info.value.constraint
        finally:
            Path(path).unlink(missing_ok=True)

"""Contract tests for VideoBlobServiceProtocol compliance.

Note:
    These tests ensure implementations satisfy the VideoBlobServiceProtocol
    with correct method signatures, return types, and runtime checks.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from gepa_adk.domain.exceptions import VideoValidationError
from gepa_adk.domain.models import VideoFileInfo
from gepa_adk.ports.video_blob_service import VideoBlobServiceProtocol

pytestmark = pytest.mark.contract


class MockVideoBlobService:
    """Minimal video blob service implementation for contract testing.

    Note:
        Returns mock Part objects for all inputs to verify protocol compliance.
    """

    async def prepare_video_parts(
        self,
        video_paths: list[str],
    ) -> list[Any]:
        """Return mock parts for testing."""
        if not video_paths:
            raise ValueError("video_paths cannot be empty")
        return [{"mock_part": path} for path in video_paths]

    def validate_video_file(
        self,
        video_path: str,
    ) -> VideoFileInfo:
        """Return mock video info for testing."""
        return VideoFileInfo(
            path=video_path,
            size_bytes=1024,
            mime_type="video/mp4",
        )


class TestVideoBlobServiceProtocol:
    """Contract tests for VideoBlobServiceProtocol compliance."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Verify @runtime_checkable decorator works for isinstance() checks."""
        service = MockVideoBlobService()
        assert isinstance(service, VideoBlobServiceProtocol), (
            "MockVideoBlobService should satisfy VideoBlobServiceProtocol"
        )

    def test_mock_service_satisfies_protocol(self) -> None:
        """Verify minimal MockVideoBlobService implementation satisfies protocol."""
        service = MockVideoBlobService()
        assert isinstance(service, VideoBlobServiceProtocol)

        # Verify both methods exist and are callable
        assert hasattr(service, "prepare_video_parts")
        assert hasattr(service, "validate_video_file")
        assert callable(service.prepare_video_parts)
        assert callable(service.validate_video_file)

    @pytest.mark.asyncio
    async def test_prepare_video_parts_returns_list(self) -> None:
        """Verify return type contract: list[Any]."""
        service = MockVideoBlobService()
        result = await service.prepare_video_parts(["/test/video.mp4"])

        assert isinstance(result, list), "prepare_video_parts() must return a list"
        assert len(result) == 1, "List length must match input length"

    @pytest.mark.asyncio
    async def test_prepare_video_parts_preserves_order(self) -> None:
        """Verify output order matches input order."""
        service = MockVideoBlobService()
        paths = ["/video1.mp4", "/video2.mp4", "/video3.mp4"]
        result = await service.prepare_video_parts(paths)

        assert len(result) == len(paths)
        # Mock implementation includes path in result for verification
        for i, (part, path) in enumerate(zip(result, paths, strict=True)):
            assert part["mock_part"] == path, f"Order mismatch at index {i}"

    @pytest.mark.asyncio
    async def test_prepare_video_parts_rejects_empty_list(self) -> None:
        """Verify empty video_paths raises ValueError."""
        service = MockVideoBlobService()

        with pytest.raises(ValueError, match="cannot be empty"):
            await service.prepare_video_parts([])

    def test_validate_video_file_returns_video_file_info(self) -> None:
        """Verify return type contract: VideoFileInfo."""
        service = MockVideoBlobService()
        result = service.validate_video_file("/test/video.mp4")

        assert isinstance(result, VideoFileInfo), (
            "validate_video_file() must return VideoFileInfo"
        )
        assert result.path == "/test/video.mp4"
        assert result.size_bytes > 0
        assert result.mime_type.startswith("video/")


class TestVideoBlobServiceRealImplementation:
    """Contract tests for VideoBlobService (real implementation)."""

    @pytest.fixture
    def service(self):
        """Create real VideoBlobService instance."""
        from gepa_adk.adapters.media.video_blob_service import VideoBlobService

        return VideoBlobService()

    @pytest.fixture
    def temp_video_file(self):
        """Create a temporary video file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content for testing")
            path = f.name
        yield path
        Path(path).unlink(missing_ok=True)

    @pytest.fixture
    def temp_text_file(self):
        """Create a temporary text file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"text content")
            path = f.name
        yield path
        Path(path).unlink(missing_ok=True)

    def test_real_service_implements_protocol(self, service) -> None:
        """Verify VideoBlobService implements VideoBlobServiceProtocol."""
        assert isinstance(service, VideoBlobServiceProtocol)

    def test_validate_video_file_returns_info(self, service, temp_video_file) -> None:
        """Verify validate_video_file returns VideoFileInfo for valid file."""
        info = service.validate_video_file(temp_video_file)

        assert isinstance(info, VideoFileInfo)
        assert info.path == temp_video_file
        assert info.size_bytes > 0
        assert info.mime_type == "video/mp4"

    def test_validate_video_file_raises_for_missing_file(self, service) -> None:
        """Verify validate_video_file raises VideoValidationError for missing file."""
        with pytest.raises(VideoValidationError) as exc_info:
            service.validate_video_file("/nonexistent/video.mp4")

        assert exc_info.value.video_path == "/nonexistent/video.mp4"
        assert exc_info.value.constraint is not None
        assert "file must exist" in exc_info.value.constraint

    def test_validate_video_file_raises_for_non_video(
        self, service, temp_text_file
    ) -> None:
        """Verify validate_video_file raises VideoValidationError for non-video."""
        with pytest.raises(VideoValidationError) as exc_info:
            service.validate_video_file(temp_text_file)

        assert exc_info.value.video_path == temp_text_file
        assert exc_info.value.constraint is not None
        assert "video/*" in exc_info.value.constraint

    @pytest.mark.asyncio
    async def test_prepare_video_parts_returns_parts(
        self, service, temp_video_file
    ) -> None:
        """Verify prepare_video_parts returns list of Part objects."""
        parts = await service.prepare_video_parts([temp_video_file])

        assert isinstance(parts, list)
        assert len(parts) == 1
        # Verify Part has inline_data (ADK Part structure)
        assert hasattr(parts[0], "inline_data")

    @pytest.mark.asyncio
    async def test_prepare_video_parts_preserves_order(self, service) -> None:
        """Verify output order matches input order with multiple files."""
        # Create multiple temp files
        temp_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(f"video content {i}".encode())
                temp_files.append(f.name)

        try:
            parts = await service.prepare_video_parts(temp_files)

            assert len(parts) == len(temp_files)
            # Each part should have inline_data
            for part in parts:
                assert hasattr(part, "inline_data")
        finally:
            for path in temp_files:
                Path(path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_prepare_video_parts_raises_for_empty(self, service) -> None:
        """Verify prepare_video_parts raises ValueError for empty list."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await service.prepare_video_parts([])

    @pytest.mark.asyncio
    async def test_prepare_video_parts_raises_for_missing(self, service) -> None:
        """Verify prepare_video_parts raises VideoValidationError for missing file."""
        with pytest.raises(VideoValidationError) as exc_info:
            await service.prepare_video_parts(["/nonexistent/video.mp4"])

        assert exc_info.value.video_path == "/nonexistent/video.mp4"

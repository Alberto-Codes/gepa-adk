"""Unit tests for VideoBlobService adapter.

Note:
    Tests video file validation, MIME type detection, and Part creation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from gepa_adk.adapters.video_blob_service import (
    MAX_VIDEO_SIZE_BYTES,
    VideoBlobService,
)
from gepa_adk.domain.exceptions import VideoValidationError
from gepa_adk.domain.models import VideoFileInfo

pytestmark = pytest.mark.unit


class TestVideoBlobServiceInit:
    """Tests for VideoBlobService initialization."""

    def test_creates_instance(self) -> None:
        """Verify service can be instantiated."""
        service = VideoBlobService()
        assert service is not None

    def test_max_video_size_is_2gb(self) -> None:
        """Verify MAX_VIDEO_SIZE_BYTES is 2GB."""
        assert MAX_VIDEO_SIZE_BYTES == 2 * 1024 * 1024 * 1024


class TestDetectMimeType:
    """Tests for MIME type detection."""

    def test_detects_mp4(self) -> None:
        """Verify MP4 MIME type detection."""
        service = VideoBlobService()
        assert service._detect_mime_type("/video.mp4") == "video/mp4"

    def test_detects_mov(self) -> None:
        """Verify MOV MIME type detection."""
        service = VideoBlobService()
        assert service._detect_mime_type("/video.mov") == "video/quicktime"

    def test_detects_avi(self) -> None:
        """Verify AVI MIME type detection."""
        service = VideoBlobService()
        # mimetypes module may return either video/x-msvideo or video/avi
        # depending on the platform's MIME database
        assert service._detect_mime_type("/video.avi") in (
            "video/x-msvideo",
            "video/avi",
        )

    def test_detects_webm(self) -> None:
        """Verify WEBM MIME type detection."""
        service = VideoBlobService()
        assert service._detect_mime_type("/video.webm") == "video/webm"

    def test_unknown_extension_returns_octet_stream(self) -> None:
        """Verify unknown extension returns application/octet-stream."""
        service = VideoBlobService()
        assert service._detect_mime_type("/file.unknown") == "application/octet-stream"


class TestValidateVideoFile:
    """Tests for validate_video_file method."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return VideoBlobService()

    @pytest.fixture
    def temp_video_file(self):
        """Create a temporary video file."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            path = f.name
        yield path
        Path(path).unlink(missing_ok=True)

    @pytest.fixture
    def temp_text_file(self):
        """Create a temporary text file."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"text content")
            path = f.name
        yield path
        Path(path).unlink(missing_ok=True)

    def test_validates_existing_video_file(self, service, temp_video_file) -> None:
        """Verify validates existing video file successfully."""
        info = service.validate_video_file(temp_video_file)

        assert isinstance(info, VideoFileInfo)
        assert info.path == temp_video_file
        assert info.size_bytes > 0
        assert info.mime_type == "video/mp4"

    def test_raises_for_nonexistent_file(self, service) -> None:
        """Verify raises VideoValidationError for nonexistent file."""
        with pytest.raises(VideoValidationError) as exc_info:
            service.validate_video_file("/nonexistent/video.mp4")

        assert exc_info.value.video_path == "/nonexistent/video.mp4"
        assert exc_info.value.constraint == "file must exist"

    def test_raises_for_directory(self, service, tmp_path) -> None:
        """Verify raises VideoValidationError for directory path."""
        with pytest.raises(VideoValidationError) as exc_info:
            service.validate_video_file(str(tmp_path))

        assert exc_info.value.constraint == "path must be a file"

    def test_raises_for_non_video_mime_type(self, service, temp_text_file) -> None:
        """Verify raises VideoValidationError for non-video MIME type."""
        with pytest.raises(VideoValidationError) as exc_info:
            service.validate_video_file(temp_text_file)

        assert exc_info.value.video_path == temp_text_file
        assert exc_info.value.constraint == "must be video/* MIME type"

    def test_raises_for_oversized_file(self, service, mocker) -> None:
        """Verify raises VideoValidationError for file exceeding 2GB."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            path = f.name

        try:
            # Mock the file stat to return oversized file
            mock_stat = mocker.MagicMock()
            mock_stat.st_size = MAX_VIDEO_SIZE_BYTES + 1

            mocker.patch.object(Path, "exists", return_value=True)
            mocker.patch.object(Path, "is_file", return_value=True)
            mocker.patch.object(Path, "stat", return_value=mock_stat)

            with pytest.raises(VideoValidationError) as exc_info:
                service.validate_video_file(path)

            assert exc_info.value.constraint == "size <= 2GB"
        finally:
            Path(path).unlink(missing_ok=True)


class TestPrepareVideoParts:
    """Tests for prepare_video_parts method."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return VideoBlobService()

    @pytest.fixture
    def temp_video_file(self):
        """Create a temporary video file."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content for testing")
            path = f.name
        yield path
        Path(path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_raises_for_empty_list(self, service) -> None:
        """Verify raises ValueError for empty video_paths."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await service.prepare_video_parts([])

    @pytest.mark.asyncio
    async def test_returns_single_part(self, service, temp_video_file) -> None:
        """Verify returns single Part for single video."""
        parts = await service.prepare_video_parts([temp_video_file])

        assert len(parts) == 1
        assert hasattr(parts[0], "inline_data")

    @pytest.mark.asyncio
    async def test_returns_multiple_parts(self, service) -> None:
        """Verify returns multiple Parts for multiple videos."""
        temp_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(f"video content {i}".encode())
                temp_files.append(f.name)

        try:
            parts = await service.prepare_video_parts(temp_files)

            assert len(parts) == 3
            for part in parts:
                assert hasattr(part, "inline_data")
        finally:
            for path in temp_files:
                Path(path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_preserves_order(self, service) -> None:
        """Verify output order matches input order."""
        temp_files = []
        contents = []
        for i in range(3):
            content = f"video content {i}".encode()
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(content)
                temp_files.append(f.name)
                contents.append(content)

        try:
            parts = await service.prepare_video_parts(temp_files)

            assert len(parts) == 3
            # Verify content matches order
            for i, part in enumerate(parts):
                assert part.inline_data.data == contents[i]
        finally:
            for path in temp_files:
                Path(path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_raises_for_invalid_file(self, service) -> None:
        """Verify raises VideoValidationError for invalid file."""
        with pytest.raises(VideoValidationError):
            await service.prepare_video_parts(["/nonexistent/video.mp4"])

    @pytest.mark.asyncio
    async def test_part_has_correct_mime_type(self, service, temp_video_file) -> None:
        """Verify Part has correct MIME type."""
        parts = await service.prepare_video_parts([temp_video_file])

        assert parts[0].inline_data.mime_type == "video/mp4"


class TestLoadVideoBytes:
    """Tests for async video byte loading."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return VideoBlobService()

    @pytest.mark.asyncio
    async def test_loads_file_content(self, service) -> None:
        """Verify loads correct file content."""
        content = b"test video bytes"
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(content)
            path = f.name

        try:
            result = await service._load_video_bytes(path)
            assert result == content
        finally:
            Path(path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_runs_in_executor(self, service, mocker) -> None:
        """Verify file read runs in thread pool executor."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"content")
            path = f.name

        try:
            mock_loop = mocker.MagicMock()
            mock_loop.run_in_executor = mocker.AsyncMock(return_value=b"content")
            mocker.patch("asyncio.get_event_loop", return_value=mock_loop)

            await service._load_video_bytes(path)

            mock_loop.run_in_executor.assert_called_once()
        finally:
            Path(path).unlink(missing_ok=True)

"""VideoBlobService adapter for video file loading.

This module implements the VideoBlobServiceProtocol, providing video file I/O
and validation logic for multimodal agent inputs. It converts video files to
ADK Part objects for inclusion in Content messages.

Attributes:
    VideoBlobService (class): Implementation of VideoBlobServiceProtocol.
    MAX_VIDEO_SIZE_BYTES (int): Maximum video file size (2GB Gemini API limit).

Examples:
    Basic usage:

    ```python
    from gepa_adk.adapters.media.video_blob_service import VideoBlobService

    service = VideoBlobService()
    parts = await service.prepare_video_parts(["/data/video.mp4"])
    # parts[0] is a Part with inline video data
    ```

    Validation:

    ```python
    info = service.validate_video_file("/data/video.mp4")
    print(f"Size: {info.size_bytes} bytes, Type: {info.mime_type}")
    ```

See Also:
    - [`gepa_adk.ports.video_blob_service`][gepa_adk.ports.video_blob_service]:
        Protocol definition.

Note:
    This adapter follows hexagonal architecture principles, implementing
    the VideoBlobServiceProtocol from the ports layer. ADK types (Part)
    are only imported and used within this adapter layer.
"""

from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path

import structlog
from google.genai.types import Part

from gepa_adk.domain.exceptions import VideoValidationError
from gepa_adk.domain.models import VideoFileInfo

logger = structlog.get_logger(__name__)

# Maximum video file size: 2GB (Gemini API constraint)
MAX_VIDEO_SIZE_BYTES = 2 * 1024 * 1024 * 1024


class VideoBlobService:
    """Video blob loading service for multimodal content.

    Implements VideoBlobServiceProtocol to convert video files to ADK Part
    objects. Validates video files for existence, size limits, and MIME types
    before loading.

    Attributes:
        _logger (BoundLogger): Structured logger for video operations.

    Examples:
        Load a single video:

        ```python
        service = VideoBlobService()
        parts = await service.prepare_video_parts(["/data/lecture.mp4"])
        assert len(parts) == 1
        ```

        Load multiple videos:

        ```python
        paths = ["/data/intro.mp4", "/data/main.mp4"]
        parts = await service.prepare_video_parts(paths)
        assert len(parts) == 2
        ```

        Handle validation errors:

        ```python
        from gepa_adk.domain.exceptions import VideoValidationError

        try:
            parts = await service.prepare_video_parts(["/missing.mp4"])
        except VideoValidationError as e:
            print(f"Invalid: {e.video_path}")
        ```

    Note:
        Adapter implements VideoBlobServiceProtocol for dependency injection
        and testing. All ADK-specific Part creation is encapsulated here.
    """

    def __init__(self) -> None:
        """Initialize VideoBlobService.

        Examples:
            Default initialization:

            ```python
            service = VideoBlobService()
            ```

        Note:
            Creates a service instance with a bound logger for video
            operations. No external dependencies are required.
        """
        self._logger = logger.bind(component="VideoBlobService")

    def _detect_mime_type(self, video_path: str) -> str:
        """Detect MIME type of a video file.

        Uses Python's mimetypes module to guess the MIME type based on
        file extension.

        Args:
            video_path: Path to the video file.

        Returns:
            Detected MIME type string (e.g., "video/mp4").

        Note:
            Scans file extension only, not file content. Falls back to
            "application/octet-stream" for unknown types.
        """
        mime_type, _ = mimetypes.guess_type(video_path)
        return mime_type or "application/octet-stream"

    def validate_video_file(self, video_path: str) -> VideoFileInfo:
        """Validate a video file and return its metadata.

        Checks that the file exists, is within size limits, and has
        a valid video MIME type.

        Args:
            video_path: Absolute path to the video file to validate.

        Returns:
            VideoFileInfo containing validated metadata.

        Raises:
            VideoValidationError: If validation fails.

        Examples:
            Validate a video file:

            ```python
            info = service.validate_video_file("/data/video.mp4")
            print(f"Size: {info.size_bytes}")
            ```

        Note:
            Operates synchronously for fast pre-validation. File content
            is not read, only metadata is checked.
        """
        path = Path(video_path)

        # Check file existence
        if not path.exists():
            self._logger.warning(
                "video.validation_failed",
                video_path=video_path,
                reason="file_not_found",
            )
            raise VideoValidationError(
                f"Video file not found: {video_path}",
                video_path=video_path,
                constraint="file must exist",
            )

        # Check file is not a directory
        if not path.is_file():
            self._logger.warning(
                "video.validation_failed",
                video_path=video_path,
                reason="not_a_file",
            )
            raise VideoValidationError(
                f"Path is not a file: {video_path}",
                video_path=video_path,
                constraint="path must be a file",
            )

        # Check file size
        size_bytes = path.stat().st_size
        if size_bytes > MAX_VIDEO_SIZE_BYTES:
            self._logger.warning(
                "video.validation_failed",
                video_path=video_path,
                reason="file_too_large",
                size_bytes=size_bytes,
                max_bytes=MAX_VIDEO_SIZE_BYTES,
            )
            raise VideoValidationError(
                f"Video exceeds 2GB limit: {size_bytes} bytes",
                video_path=video_path,
                constraint="size <= 2GB",
            )

        # Check MIME type
        mime_type = self._detect_mime_type(video_path)
        if not mime_type.startswith("video/"):
            self._logger.warning(
                "video.validation_failed",
                video_path=video_path,
                reason="invalid_mime_type",
                mime_type=mime_type,
            )
            raise VideoValidationError(
                f"Not a video file: {mime_type}",
                video_path=video_path,
                constraint="must be video/* MIME type",
            )

        self._logger.debug(
            "video.validated",
            video_path=video_path,
            size_bytes=size_bytes,
            mime_type=mime_type,
        )

        return VideoFileInfo(
            path=video_path,
            size_bytes=size_bytes,
            mime_type=mime_type,
        )

    async def _load_video_bytes(self, video_path: str) -> bytes:
        """Load video file bytes asynchronously.

        Reads the file content in a thread pool to avoid blocking
        the event loop.

        Args:
            video_path: Path to the video file.

        Returns:
            Raw bytes of the video file.

        Note:
            Spawns blocking file read in thread pool via run_in_executor
            to prevent blocking the event loop during large file reads.
        """
        loop = asyncio.get_running_loop()

        def read_file() -> bytes:
            with open(video_path, "rb") as f:
                return f.read()

        return await loop.run_in_executor(None, read_file)

    async def prepare_video_parts(self, video_paths: list[str]) -> list[Part]:
        """Load video files and create Part objects for multimodal content.

        Validates and loads all video files, converting them to ADK Part
        objects with inline video data.

        Args:
            video_paths: List of absolute paths to video files.

        Returns:
            List of Part objects, one per input path. Order is preserved.

        Raises:
            ValueError: If video_paths is empty.
            VideoValidationError: If any file fails validation.

        Examples:
            Load videos:

            ```python
            parts = await service.prepare_video_parts(
                [
                    "/data/intro.mp4",
                    "/data/main.mp4",
                ]
            )
            assert len(parts) == 2
            ```

        Note:
            Operations include async file I/O. Videos are validated before
            loading to provide early failure with clear error messages.
        """
        if not video_paths:
            raise ValueError("video_paths cannot be empty")

        self._logger.info(
            "video.prepare_start",
            video_count=len(video_paths),
        )

        parts: list[Part] = []

        for video_path in video_paths:
            # Validate first
            info = self.validate_video_file(video_path)

            # Load video bytes
            video_bytes = await self._load_video_bytes(video_path)

            # Create Part with inline data
            part = Part.from_bytes(
                data=video_bytes,
                mime_type=info.mime_type,
            )
            parts.append(part)

            self._logger.debug(
                "video.loaded",
                video_path=video_path,
                size_bytes=info.size_bytes,
                mime_type=info.mime_type,
            )

        self._logger.info(
            "video.prepare_complete",
            video_count=len(parts),
        )

        return parts


__all__ = ["VideoBlobService", "MAX_VIDEO_SIZE_BYTES"]

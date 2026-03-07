"""Protocol definition for video blob loading services.

This module defines the VideoBlobServiceProtocol that enables loading video
files and converting them to multimodal content parts for agent execution.
The protocol provides methods for validating video files and preparing them
as Part objects for the ADK Content API.

Attributes:
    VideoBlobServiceProtocol (protocol): Protocol for video blob loading.

Examples:
    Implement a video blob service:

    ```python
    from gepa_adk.ports import VideoBlobServiceProtocol
    from gepa_adk.domain.models import VideoFileInfo


    class MockVideoBlobService:
        async def prepare_video_parts(
            self,
            video_paths: list[str],
        ) -> list[Any]:
            # Return mock Part objects
            return [{"mock": path} for path in video_paths]

        def validate_video_file(
            self,
            video_path: str,
        ) -> VideoFileInfo:
            return VideoFileInfo(
                path=video_path,
                size_bytes=1024,
                mime_type="video/mp4",
            )
    ```

    Verify protocol compliance:

    ```python
    from gepa_adk.ports import VideoBlobServiceProtocol

    service = MockVideoBlobService()
    assert isinstance(service, VideoBlobServiceProtocol)
    ```

See Also:
    - [`VideoFileInfo`][gepa_adk.domain.models.VideoFileInfo]: Metadata returned by validation.
    - [`gepa_adk.adapters.media`][gepa_adk.adapters.media]: Video blob service implementations.

Note:
    The protocol uses list[Any] as the return type for prepare_video_parts()
    to avoid importing ADK types in the ports layer. Implementations in the
    adapters layer return google.genai.types.Part objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from gepa_adk.domain.models import VideoFileInfo


@runtime_checkable
class VideoBlobServiceProtocol(Protocol):
    """Protocol for loading video files as multimodal content parts.

    Implementations provide video file I/O and validation logic,
    converting video files to Part objects for multimodal agent input.

    The protocol defines an async method for loading multiple videos
    and a sync method for validating individual files.

    Examples:
        Implement a video blob service:

        ```python
        class SimpleVideoBlobService:
            async def prepare_video_parts(
                self,
                video_paths: list[str],
            ) -> list[Any]:
                # Load videos and return Part objects
                parts = []
                for path in video_paths:
                    self.validate_video_file(path)
                    # ... load and create Part
                return parts

            def validate_video_file(
                self,
                video_path: str,
            ) -> VideoFileInfo:
                # Validate and return metadata
                ...
        ```

        Verify protocol compliance:

        ```python
        from gepa_adk.ports import VideoBlobServiceProtocol

        service = SimpleVideoBlobService()
        assert isinstance(service, VideoBlobServiceProtocol)
        ```

    Note:
        All implementations must provide both prepare_video_parts() and
        validate_video_file() methods. Video size is limited to 2GB per
        the Gemini API constraint. Only video/* MIME types are accepted.
    """

    async def prepare_video_parts(
        self,
        video_paths: list[str],
    ) -> list[Any]:
        """Load video files and create Part objects for multimodal content.

        Reads video files from disk and converts them to Part objects
        suitable for inclusion in ADK Content. Files are validated before
        loading.

        Args:
            video_paths: List of absolute paths to video files. Must be
                non-empty. All paths must point to existing video files
                under 2GB with video/* MIME types.

        Returns:
            List of Part objects, one per input path. Order is preserved
            such that output[i] corresponds to video_paths[i]. Part objects
            contain inline video data with appropriate MIME type.

        Raises:
            ValueError: If video_paths is empty.
            VideoValidationError: If any file is not found, exceeds 2GB,
                or has a non-video MIME type.
            PermissionError: If any file cannot be read due to permissions.
            OSError: If any file cannot be read due to I/O errors.

        Examples:
            Load a single video:

            ```python
            parts = await service.prepare_video_parts(["/data/video.mp4"])
            assert len(parts) == 1
            ```

            Load multiple videos preserving order:

            ```python
            paths = ["/data/intro.mp4", "/data/main.mp4", "/data/outro.mp4"]
            parts = await service.prepare_video_parts(paths)
            assert len(parts) == 3
            # parts[0] is intro, parts[1] is main, parts[2] is outro
            ```

        Note:
            Operations include async file I/O for reading video bytes.
            Video files are validated before loading to provide early
            failure with clear error messages.
        """
        ...

    def validate_video_file(
        self,
        video_path: str,
    ) -> "VideoFileInfo":
        """Validate a video file and return its metadata.

        Checks that the file exists, is within size limits, and has
        a valid video MIME type. Returns metadata on success.

        Args:
            video_path: Absolute path to the video file to validate.

        Returns:
            VideoFileInfo containing validated metadata:

            - path: The validated file path
            - size_bytes: File size in bytes
            - mime_type: Detected MIME type (e.g., "video/mp4")

        Raises:
            VideoValidationError: If the file does not exist, exceeds 2GB,
                or has a non-video MIME type. The exception includes the
                video_path and constraint fields for debugging.

        Examples:
            Validate a video file:

            ```python
            info = service.validate_video_file("/data/lecture.mp4")
            print(f"Size: {info.size_bytes} bytes")
            print(f"Type: {info.mime_type}")
            ```

            Handle validation errors:

            ```python
            from gepa_adk.domain.exceptions import VideoValidationError

            try:
                info = service.validate_video_file("/missing.mp4")
            except VideoValidationError as e:
                print(f"Invalid: {e.video_path} - {e.constraint}")
            ```

        Note:
            Operates synchronously for fast pre-validation without async
            context. File content is not read, only metadata is checked.
        """
        ...

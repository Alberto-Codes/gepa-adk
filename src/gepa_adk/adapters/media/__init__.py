"""Multimodal adapters for media handling.

Currently contains VideoBlobService for video file loading and validation.

Anticipated growth: image processing adapters, audio adapters,
multi-format media services.

Attributes:
    VideoBlobService: Implementation of VideoBlobServiceProtocol.
    MAX_VIDEO_SIZE_BYTES: Maximum allowed video file size (2GB).

Examples:
    Load a video file as a blob:

    ```python
    from gepa_adk.adapters.media import VideoBlobService

    service = VideoBlobService()
    blob = service.load(path="/path/to/video.mp4")
    ```

See Also:
    - [`gepa_adk.adapters`][gepa_adk.adapters]: Parent adapter layer re-exports.
    - [`gepa_adk.ports.video_blob_service`][gepa_adk.ports.video_blob_service]:
        VideoBlobServiceProtocol that VideoBlobService implements.

Note:
    This package provides multimodal media adapters for video blob services.
"""

from gepa_adk.adapters.media.video_blob_service import (
    MAX_VIDEO_SIZE_BYTES,
    VideoBlobService,
)

__all__ = [
    "VideoBlobService",
    "MAX_VIDEO_SIZE_BYTES",
]

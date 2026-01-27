"""Unit tests for _validate_dataset multimodal support.

Note:
    Tests the extended validation that accepts videos field as alternative to input.
"""

from __future__ import annotations

import pytest

from gepa_adk.api import _validate_dataset
from gepa_adk.domain.exceptions import ConfigurationError

pytestmark = pytest.mark.unit


class TestValidateDatasetBackwardCompatibility:
    """Tests for backward compatibility with text-only datasets."""

    def test_accepts_input_only(self) -> None:
        """Verify input-only examples remain valid."""
        dataset = [{"input": "What is 2+2?"}]
        _validate_dataset(dataset, "trainset")  # Should not raise

    def test_accepts_input_with_expected(self) -> None:
        """Verify input with expected field remains valid."""
        dataset = [{"input": "What is 2+2?", "expected": "4"}]
        _validate_dataset(dataset, "trainset")  # Should not raise

    def test_accepts_multiple_input_examples(self) -> None:
        """Verify multiple input-only examples remain valid."""
        dataset = [
            {"input": "Question 1"},
            {"input": "Question 2"},
            {"input": "Question 3"},
        ]
        _validate_dataset(dataset, "trainset")  # Should not raise


class TestValidateDatasetVideosOnly:
    """Tests for video-only examples."""

    def test_accepts_videos_only(self) -> None:
        """Verify video-only examples are valid."""
        dataset = [{"videos": ["/path/to/video.mp4"]}]
        _validate_dataset(dataset, "trainset")  # Should not raise

    def test_accepts_videos_with_expected(self) -> None:
        """Verify videos with expected field is valid."""
        dataset = [{"videos": ["/path/to/video.mp4"], "expected": "Transcript text"}]
        _validate_dataset(dataset, "trainset")  # Should not raise

    def test_accepts_multiple_videos_per_example(self) -> None:
        """Verify multiple videos in single example is valid."""
        dataset = [{"videos": ["/path/to/video1.mp4", "/path/to/video2.mp4"]}]
        _validate_dataset(dataset, "trainset")  # Should not raise


class TestValidateDatasetInputAndVideos:
    """Tests for examples with both input and videos."""

    def test_accepts_input_and_videos(self) -> None:
        """Verify examples with both input and videos are valid."""
        dataset = [{"input": "Transcribe this", "videos": ["/path/to/video.mp4"]}]
        _validate_dataset(dataset, "trainset")  # Should not raise

    def test_accepts_input_videos_and_expected(self) -> None:
        """Verify examples with input, videos, and expected are valid."""
        dataset = [
            {
                "input": "Transcribe this",
                "videos": ["/path/to/video.mp4"],
                "expected": "Expected transcript",
            }
        ]
        _validate_dataset(dataset, "trainset")  # Should not raise


class TestValidateDatasetMixedExamples:
    """Tests for datasets with mixed example types."""

    def test_accepts_mixed_text_and_video_examples(self) -> None:
        """Verify mixed text-only and video examples are valid."""
        dataset = [
            {"input": "Text only question"},
            {"videos": ["/path/to/video.mp4"]},
            {"input": "Another text question"},
        ]
        _validate_dataset(dataset, "trainset")  # Should not raise

    def test_accepts_all_example_types(self) -> None:
        """Verify all example types in single dataset are valid."""
        dataset = [
            {"input": "Text only"},
            {"videos": ["/path/to/video.mp4"]},
            {"input": "With video", "videos": ["/path/to/video2.mp4"]},
            {"videos": ["/video1.mp4", "/video2.mp4"]},
            {"input": "With expected", "expected": "Answer"},
            {"videos": ["/video.mp4"], "expected": "Transcript"},
        ]
        _validate_dataset(dataset, "trainset")  # Should not raise


class TestValidateDatasetNeitherInputNorVideos:
    """Tests for invalid examples missing both input and videos."""

    def test_rejects_neither_input_nor_videos(self) -> None:
        """Verify examples with neither input nor videos raise error."""
        dataset = [{"expected": "something"}]

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_dataset(dataset, "trainset")

        assert "input" in str(exc_info.value)
        assert "videos" in str(exc_info.value)

    def test_rejects_empty_example(self) -> None:
        """Verify empty examples raise error."""
        dataset = [{}]

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_dataset(dataset, "trainset")

        assert "input" in str(exc_info.value)
        assert "videos" in str(exc_info.value)


class TestValidateDatasetVideosFieldStructure:
    """Tests for videos field structure validation."""

    def test_rejects_videos_not_a_list(self) -> None:
        """Verify videos field must be a list."""
        dataset = [{"videos": "/path/to/video.mp4"}]  # String, not list

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_dataset(dataset, "trainset")

        assert "must be a list" in str(exc_info.value)

    def test_rejects_empty_videos_list(self) -> None:
        """Verify videos list cannot be empty."""
        dataset = [{"videos": []}]

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_dataset(dataset, "trainset")

        assert "cannot be empty" in str(exc_info.value)

    def test_rejects_videos_item_not_string(self) -> None:
        """Verify each video path must be a string."""
        dataset = [{"videos": [123]}]  # Integer, not string

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_dataset(dataset, "trainset")

        assert "must be a string" in str(exc_info.value)

    def test_rejects_videos_with_none_item(self) -> None:
        """Verify None is not accepted as video path."""
        dataset = [{"videos": [None]}]

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_dataset(dataset, "trainset")

        assert "must be a string" in str(exc_info.value)

    def test_rejects_mixed_valid_and_invalid_videos(self) -> None:
        """Verify mixed valid/invalid video paths in list raises error."""
        dataset = [{"videos": ["/valid/path.mp4", 123]}]

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_dataset(dataset, "trainset")

        assert "must be a string" in str(exc_info.value)


class TestValidateDatasetErrorMessages:
    """Tests for error message content."""

    def test_error_includes_example_index(self) -> None:
        """Verify error message includes the example index."""
        dataset = [
            {"input": "valid"},
            {"expected": "invalid - no input or videos"},
        ]

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_dataset(dataset, "trainset")

        # Should reference trainset[1]
        assert "trainset[1]" in str(exc_info.value)

    def test_error_includes_videos_index(self) -> None:
        """Verify error message includes video item index."""
        dataset = [{"videos": ["/valid.mp4", 123]}]

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_dataset(dataset, "trainset")

        # Should reference videos[1]
        assert "videos[1]" in str(exc_info.value)

    def test_error_includes_dataset_name(self) -> None:
        """Verify error message uses provided dataset name."""
        dataset = [{}]

        with pytest.raises(ConfigurationError) as exc_info:
            _validate_dataset(dataset, "valset")

        assert "valset" in str(exc_info.value)


class TestValidateDatasetExpectedOptional:
    """Tests verifying expected field remains optional."""

    def test_expected_optional_with_input(self) -> None:
        """Verify expected is optional with input."""
        dataset = [{"input": "question"}]
        _validate_dataset(dataset, "trainset")  # Should not raise

    def test_expected_optional_with_videos(self) -> None:
        """Verify expected is optional with videos."""
        dataset = [{"videos": ["/video.mp4"]}]
        _validate_dataset(dataset, "trainset")  # Should not raise

    def test_expected_optional_with_both(self) -> None:
        """Verify expected is optional with input and videos."""
        dataset = [{"input": "prompt", "videos": ["/video.mp4"]}]
        _validate_dataset(dataset, "trainset")  # Should not raise

"""Unit tests for FileStopper.

Tests cover all acceptance criteria from issue #197:
- Stop when file exists
- Continue when file missing
- Remove file on stop (remove_on_stop=True)
- Keep file on stop (remove_on_stop=False)
- Handle nonexistent directory gracefully
- Accept string path
- Accept Path object
- Protocol compliance
"""

from pathlib import Path

import pytest

from gepa_adk.adapters.stoppers import FileStopper
from gepa_adk.domain.stopper import StopperState
from gepa_adk.ports.stopper import StopperProtocol

pytestmark = pytest.mark.unit


@pytest.fixture
def default_state() -> StopperState:
    """Create a default stopper state for testing."""
    return StopperState(
        iteration=5,
        best_score=0.5,
        stagnation_counter=0,
        total_evaluations=50,
        candidates_count=1,
        elapsed_seconds=30.0,
    )


class TestFileStopperInitialization:
    """Tests for FileStopper initialization."""

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        """FileStopper accepts string path and converts to Path."""
        path_str = str(tmp_path / "stop_file")
        stopper = FileStopper(path_str)

        assert stopper.stop_file_path == Path(path_str)

    def test_accepts_path_object(self, tmp_path: Path) -> None:
        """FileStopper accepts Path object directly."""
        path = tmp_path / "stop_file"
        stopper = FileStopper(path)

        assert stopper.stop_file_path == path

    def test_remove_on_stop_default_false(self, tmp_path: Path) -> None:
        """FileStopper remove_on_stop defaults to False."""
        stopper = FileStopper(tmp_path / "stop_file")

        assert stopper.remove_on_stop is False

    def test_remove_on_stop_true(self, tmp_path: Path) -> None:
        """FileStopper accepts remove_on_stop=True."""
        stopper = FileStopper(tmp_path / "stop_file", remove_on_stop=True)

        assert stopper.remove_on_stop is True


class TestFileStopperBehavior:
    """Tests for FileStopper stopping behavior."""

    def test_stops_when_file_exists(
        self, tmp_path: Path, default_state: StopperState
    ) -> None:
        """Stopper returns True when stop file exists."""
        stop_file = tmp_path / "stop_file"
        stop_file.touch()
        stopper = FileStopper(stop_file)

        result = stopper(default_state)

        assert result is True

    def test_continues_when_file_missing(
        self, tmp_path: Path, default_state: StopperState
    ) -> None:
        """Stopper returns False when stop file does not exist."""
        stop_file = tmp_path / "stop_file"
        stopper = FileStopper(stop_file)

        result = stopper(default_state)

        assert result is False

    def test_remove_on_stop_deletes_file(
        self, tmp_path: Path, default_state: StopperState
    ) -> None:
        """Stopper with remove_on_stop=True deletes file after triggering."""
        stop_file = tmp_path / "stop_file"
        stop_file.touch()
        stopper = FileStopper(stop_file, remove_on_stop=True)

        result = stopper(default_state)

        assert result is True
        assert not stop_file.exists()

    def test_remove_on_stop_false_keeps_file(
        self, tmp_path: Path, default_state: StopperState
    ) -> None:
        """Stopper with remove_on_stop=False (default) keeps file after triggering."""
        stop_file = tmp_path / "stop_file"
        stop_file.touch()
        stopper = FileStopper(stop_file, remove_on_stop=False)

        result = stopper(default_state)

        assert result is True
        assert stop_file.exists()

    def test_handles_nonexistent_directory(
        self, tmp_path: Path, default_state: StopperState
    ) -> None:
        """Stopper handles path in nonexistent directory gracefully."""
        # Path in directory that doesn't exist
        nonexistent_path = tmp_path / "nonexistent_dir" / "stop_file"
        stopper = FileStopper(nonexistent_path)

        result = stopper(default_state)

        # Should not raise, just return False
        assert result is False


class TestFileStopperProtocolCompliance:
    """Tests verifying FileStopper satisfies StopperProtocol."""

    def test_satisfies_stopper_protocol(self, tmp_path: Path) -> None:
        """FileStopper instance satisfies StopperProtocol."""
        stopper = FileStopper(tmp_path / "stop_file")

        assert isinstance(stopper, StopperProtocol)

    def test_call_returns_bool(
        self, tmp_path: Path, default_state: StopperState
    ) -> None:
        """FileStopper __call__ returns a boolean value."""
        stopper = FileStopper(tmp_path / "stop_file")

        result = stopper(default_state)

        assert isinstance(result, bool)


class TestFileStopperEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_file_removed_between_check_and_delete(
        self, tmp_path: Path, default_state: StopperState
    ) -> None:
        """Stopper handles race condition where file disappears before delete.

        This tests the remove_on_stop=True path where the file might be
        removed by another process between exists() check and unlink().
        """
        stop_file = tmp_path / "stop_file"
        stop_file.touch()

        stopper = FileStopper(stop_file, remove_on_stop=True)

        # File exists at start
        assert stop_file.exists()

        # First call triggers stop and removes file
        result1 = stopper(default_state)
        assert result1 is True
        assert not stop_file.exists()

        # Second call - file already gone, should return False without error
        result2 = stopper(default_state)
        assert result2 is False

    def test_multiple_calls_without_file(
        self, tmp_path: Path, default_state: StopperState
    ) -> None:
        """Multiple calls without file consistently return False."""
        stopper = FileStopper(tmp_path / "stop_file")

        results = [stopper(default_state) for _ in range(5)]

        assert all(r is False for r in results)

    def test_file_created_between_calls(
        self, tmp_path: Path, default_state: StopperState
    ) -> None:
        """Stopper detects file creation between calls."""
        stop_file = tmp_path / "stop_file"
        stopper = FileStopper(stop_file)

        # First call - no file
        assert stopper(default_state) is False

        # Create file
        stop_file.touch()

        # Second call - file exists
        assert stopper(default_state) is True


class TestFileStopperRemoveStopFile:
    """Tests for FileStopper.remove_stop_file() method."""

    def test_remove_stop_file_deletes_existing(self, tmp_path: Path) -> None:
        """remove_stop_file() deletes existing stop file."""
        stop_file = tmp_path / "stop_file"
        stop_file.touch()
        stopper = FileStopper(stop_file)

        assert stop_file.exists()

        stopper.remove_stop_file()

        assert not stop_file.exists()

    def test_remove_stop_file_idempotent(self, tmp_path: Path) -> None:
        """remove_stop_file() is idempotent - no error when file missing."""
        stop_file = tmp_path / "stop_file"
        stopper = FileStopper(stop_file)

        # File doesn't exist
        assert not stop_file.exists()

        # Should not raise
        stopper.remove_stop_file()

        # Still doesn't exist
        assert not stop_file.exists()

    def test_remove_stop_file_multiple_calls(self, tmp_path: Path) -> None:
        """remove_stop_file() can be called multiple times safely."""
        stop_file = tmp_path / "stop_file"
        stop_file.touch()
        stopper = FileStopper(stop_file)

        # First removal
        stopper.remove_stop_file()
        assert not stop_file.exists()

        # Second removal (file already gone)
        stopper.remove_stop_file()
        assert not stop_file.exists()

        # Third removal
        stopper.remove_stop_file()
        assert not stop_file.exists()

"""FileStopper for stopping evolution when a file exists.

This module provides a stopper that terminates evolution when a specified
file exists, enabling external orchestration and graceful shutdown signals.

Attributes:
    FileStopper (class): Stop evolution when a stop file exists.

Examples:
    Basic usage:

    ```python
    from gepa_adk.adapters.stoppers import FileStopper

    stopper = FileStopper("/tmp/gepa_stop")
    ```

    With automatic file removal:

    ```python
    stopper = FileStopper("/tmp/gepa_stop", remove_on_stop=True)
    ```

    External orchestration (from another process):

    ```bash
    touch /tmp/gepa_stop  # Signal evolution to stop
    ```

Note:
    This stopper is particularly useful for CI/CD pipelines, job schedulers,
    and external monitoring systems that cannot easily send process signals
    but can create files.
"""

from pathlib import Path

from gepa_adk.domain.stopper import StopperState


class FileStopper:
    """Stop evolution when a specified file exists.

    Useful for external orchestration where CI/CD pipelines, job schedulers,
    or monitoring tools can signal graceful termination by creating a file.

    Attributes:
        stop_file_path (Path): Path to the stop signal file.
        remove_on_stop (bool): If True, remove the file after triggering stop.

    Examples:
        Stop when file exists:

        ```python
        stopper = FileStopper("/tmp/gepa_stop")
        ```

        Auto-remove file after triggering:

        ```python
        stopper = FileStopper("/tmp/gepa_stop", remove_on_stop=True)
        ```

    Note:
        Any path that doesn't exist simply won't trigger a stop. Invalid paths
        are handled gracefully without raising errors.
    """

    def __init__(
        self, stop_file_path: str | Path, remove_on_stop: bool = False
    ) -> None:
        """Initialize the stopper with a stop file path.

        Args:
            stop_file_path: Path to the stop signal file. Can be a string
                or Path object. Will be converted to Path internally.
            remove_on_stop: If True, automatically remove the stop file
                after triggering a stop. Defaults to False.

        Note:
            Configure the path based on your orchestration system. Common
            locations include /tmp/, /var/run/, or project-specific directories.
        """
        self.stop_file_path = Path(stop_file_path)
        self.remove_on_stop = remove_on_stop

    def __call__(self, state: StopperState) -> bool:
        """Check if evolution should stop based on file existence.

        Args:
            state: Current evolution state snapshot (not used for file-based
                stopping, but required by the StopperProtocol).

        Returns:
            True if the stop file exists, False otherwise.

        Note:
            Once this returns True, the stop file may be removed if
            remove_on_stop was enabled. Subsequent calls will return False.
        """
        if self.stop_file_path.exists():
            if self.remove_on_stop:
                self.stop_file_path.unlink(missing_ok=True)
            return True
        return False

    def remove_stop_file(self) -> None:
        """Manually remove the stop file.

        This is idempotent - safe to call even if the file doesn't exist.
        Useful for resetting the stop condition before starting a new
        evolution run.

        Note:
            Only call this when you explicitly want to remove the stop file.
            The file is automatically removed during __call__ if remove_on_stop=True.
        """
        self.stop_file_path.unlink(missing_ok=True)


__all__ = ["FileStopper"]

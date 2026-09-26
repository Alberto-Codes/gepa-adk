"""Select routine or full compatibility coverage from GitHub event evidence.

Routine coverage retains all Linux Python/ADK combinations and representative
macOS/Windows locked-dependency legs. Full coverage runs weekly, when explicitly
requested, for release-please branches, and for platform/dependency-sensitive
changes: pyproject.toml, uv.lock, .python-version, .github/**, scripts/**,
src/gepa_adk/utils/**, tests/conftest.py, and tests/fixtures/**. Unknown events or
unavailable git history fail safe to full coverage. Malformed JSON fails the CLI.
"""

import json
import os
import re
import subprocess
from pathlib import Path

_SENSITIVE_FILES = {"pyproject.toml", "uv.lock", ".python-version", "tests/conftest.py"}
_SENSITIVE_PREFIXES = (".github/", "scripts/", "src/gepa_adk/utils/", "tests/fixtures/")


def _result(full: bool, reason: str) -> dict:
    """Construct a matrix and explain its routing decision.

    Args:
        full: Whether all supported combinations are required.
        reason: Human-readable routing evidence.

    Returns:
        JSON-serializable matrix, mode, and reason.
    """
    rows = [
        {"os": runner, "python-version": python, "adk-version": adk}
        for runner in ("ubuntu-latest", "macos-latest", "windows-latest")
        for python in ("3.12", "3.13")
        for adk in ("1.39.1", "")
        if full
        or runner == "ubuntu-latest"
        or (runner, python, adk)
        in {("macos-latest", "3.13", ""), ("windows-latest", "3.12", "")}
    ]
    return {
        "matrix": {"include": rows},
        "mode": "full" if full else "routine",
        "reason": reason,
    }


def plan_matrix(event_name: str, event: dict, force_full: bool = False) -> dict:
    """Plan compatibility coverage using the current repository's git history.

    Args:
        event_name: GitHub event name.
        event: Decoded GitHub event payload.
        force_full: Explicit reusable-workflow or dispatch override.

    Returns:
        Matrix and decision evidence; missing history selects full coverage.
    """
    if force_full:
        return _result(True, "Full compatibility explicitly requested")
    if event_name == "schedule":
        return _result(True, "Scheduled full compatibility check")
    if event_name == "workflow_dispatch":
        return _result(False, "Manual routine measurement (force_full is false)")
    if event_name == "pull_request":
        pull = event.get("pull_request") or {}
        head = pull.get("head") or {}
        if head.get("ref", "").startswith("release-please--"):
            return _result(True, "Release-please compatibility check")
        base_sha = (pull.get("base") or {}).get("sha")
        head_sha = head.get("sha")
    elif event_name == "push":
        base_sha, head_sha = event.get("before"), event.get("after")
    else:
        return _result(True, f"Unknown event: {event_name}")
    for sha in (base_sha, head_sha):
        if (
            not isinstance(sha, str)
            or not re.fullmatch(r"[0-9a-fA-F]{40}", sha)
            or set(sha) == {"0"}
        ):
            return _result(True, "Missing or invalid comparison commit")
    try:
        # Disable rename detection so both the old and new path are inspected.
        diff = subprocess.run(
            [
                "git",
                "diff",
                "--no-renames",
                "--name-only",
                "-z",
                base_sha,
                head_sha,
                "--",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return _result(True, "Comparison history unavailable")
    paths = diff.stdout.split("\0")
    if any(
        path in _SENSITIVE_FILES or path.startswith(_SENSITIVE_PREFIXES)
        for path in paths
    ):
        return _result(True, "Platform or dependency-sensitive change")
    return _result(False, "Changes outside platform and dependency-sensitive paths")


def main() -> None:
    """Read GitHub's event environment and emit the matrix as JSON.

    Raises:
        OSError: The event file cannot be read.
        ValueError: The event JSON is malformed or is not an object.
    """
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event = json.loads(Path(event_path).read_text()) if event_path else {}
    if not isinstance(event, dict):
        raise ValueError("GitHub event must be a JSON object")
    print(
        json.dumps(
            plan_matrix(
                os.environ.get("GITHUB_EVENT_NAME", ""),
                event,
                os.environ.get("FORCE_FULL", "false").lower() == "true",
            )
        )
    )


if __name__ == "__main__":
    main()

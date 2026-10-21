"""Select routine or full compatibility coverage from GitHub event evidence.

Routine coverage runs six legs: all four Linux Python/ADK combinations plus one
representative locked-dependency leg each on macOS (Python 3.13) and Windows
(Python 3.12). Full coverage runs ten legs: the Linux cross-product plus every
macOS and Windows combination except Python 3.12 with ADK 1.39.1.

Full coverage runs weekly, when explicitly requested, for release-please pull
requests, and for pushes whose diff touches pyproject.toml, uv.lock or
.python-version. Every other pull request, Dependabot included, runs routine
coverage without inspecting its diff. Other pushes run routine coverage. Unknown
events, a pull request without a head ref, and a push with invalid commits or
unavailable git history fail safe to full coverage. Malformed JSON fails the CLI.

Examples:
    Emit the matrix for a local event payload, as the CI planner job does:

    ```bash
    GITHUB_EVENT_NAME=push GITHUB_EVENT_PATH=event.json python scripts/ci_matrix.py
    ```

See Also:
    - [`plan_matrix`][scripts.ci_matrix.plan_matrix]: The routing decision
      behind each emitted matrix.
    - `.github/workflows/ci.yml`: The workflow that consumes ``plan.json``.
"""

import json
import os
import re
import subprocess
from pathlib import Path

_DEPENDENCY_FILES = {"pyproject.toml", "uv.lock", ".python-version"}
# Full mode skips these non-Linux legs; Linux keeps the whole cross-product.
_FULL_EXCLUDED = {
    ("macos-latest", "3.12", "1.39.1"),
    ("windows-latest", "3.12", "1.39.1"),
}
_ROUTINE_NON_LINUX = {("macos-latest", "3.13", ""), ("windows-latest", "3.12", "")}


def _result(full: bool, reason: str) -> dict:
    """Construct a matrix and explain its routing decision.

    Args:
        full: Whether the ten-leg full matrix is required instead of the
            six-leg routine matrix.
        reason: Human-readable routing evidence.

    Returns:
        JSON-serializable matrix, mode, and reason.
    """
    rows = [
        {"os": runner, "python-version": python, "adk-version": adk}
        for runner in ("ubuntu-latest", "macos-latest", "windows-latest")
        for python in ("3.12", "3.13")
        for adk in ("1.39.1", "")
        if runner == "ubuntu-latest"
        or (runner, python, adk) in _ROUTINE_NON_LINUX
        or (full and (runner, python, adk) not in _FULL_EXCLUDED)
    ]
    return {
        "matrix": {"include": rows},
        "mode": "full" if full else "routine",
        "reason": reason,
    }


def plan_matrix(event_name: str, event: dict, force_full: bool = False) -> dict:  # noqa: PLR0911  # one early return per event kind
    """Plan compatibility coverage from the event and, for pushes, git history.

    Args:
        event_name: GitHub event name.
        event: Decoded GitHub event payload.
        force_full: Explicit reusable-workflow or dispatch override.

    Returns:
        Matrix and decision evidence; missing push history or a missing pull
        request head selects full coverage.
    """
    if force_full:
        return _result(True, "Full compatibility explicitly requested")
    if event_name == "schedule":
        return _result(True, "Scheduled full compatibility check")
    if event_name == "workflow_dispatch":
        return _result(False, "Manual routine measurement (force_full is false)")
    if event_name == "pull_request":
        head_ref = ((event.get("pull_request") or {}).get("head") or {}).get("ref")
        if not isinstance(head_ref, str):
            return _result(True, "Missing pull request head")
        if head_ref.startswith("release-please--"):
            return _result(True, "Release-please compatibility check")
        return _result(
            False,
            "Pull request: routine coverage; full runs on main for dependency changes",
        )
    if event_name != "push":
        return _result(True, f"Unknown event: {event_name}")
    base_sha, head_sha = event.get("before"), event.get("after")
    for sha in (base_sha, head_sha):
        if (
            not isinstance(sha, str)
            or not re.fullmatch(r"[0-9a-fA-F]{40}", sha)
            or set(sha) == {"0"}
        ):
            return _result(True, "Missing or invalid comparison commit")
    try:
        # Disable rename detection so both the old and new path are inspected.
        diff = subprocess.run(  # noqa: S603  # fixed argv list, no shell
            [  # noqa: S607  # git resolved from PATH as in CI
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
    if any(path in _DEPENDENCY_FILES for path in paths):
        return _result(True, "Dependency change on main")
    return _result(False, "Push without dependency changes")


def main() -> None:
    """Read GitHub's event environment and emit the matrix as JSON.

    Raises:
        OSError: The event file cannot be read.
        ValueError: The event JSON is malformed or is not an object.
    """
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event = json.loads(Path(event_path).read_text()) if event_path else {}
    if not isinstance(event, dict):
        raise ValueError("GitHub event must be a JSON object")  # noqa: TRY004  # callers and tests expect ValueError for a malformed event
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

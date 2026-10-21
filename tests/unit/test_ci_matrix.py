"""Exercise the CI matrix CLI against independent event files and git history."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci_matrix.py"
FULL = {
    (runner, python, adk)
    for runner in ("ubuntu-latest", "macos-latest", "windows-latest")
    for python in ("3.12", "3.13")
    for adk in ("1.39.1", "")
} - {("macos-latest", "3.12", "1.39.1"), ("windows-latest", "3.12", "1.39.1")}
ROUTINE = {entry for entry in FULL if entry[0] == "ubuntu-latest"} | {
    ("macos-latest", "3.13", ""),
    ("windows-latest", "3.12", ""),
}


def _isolated_env() -> dict[str, str]:
    """Pass only OS runtime settings to fixture subprocesses.

    Returns:
        Platform environment without Git overrides or inherited credentials.
    """
    runtime_keys = {
        "PATH",
        "HOME",
        "USERPROFILE",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "TMP",
        "TEMP",
        "TMPDIR",
        "LANG",
        "LC_ALL",
    }
    return {key: os.environ[key] for key in os.environ if key.upper() in runtime_keys}


def test_subprocess_environment_excludes_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Credentials cannot appear in subprocess kwargs printed by showlocals.

    Args:
        monkeypatch: Isolated environment overrides.
    """
    monkeypatch.setenv("ACCEPTANCE_DUMMY_TOKEN", "dummy-secret-marker")
    monkeypatch.setenv("GIT_DIR", "/unrelated/repository")
    monkeypatch.setenv("SystemRoot", "platform-root")
    environment = _isolated_env()
    assert "ACCEPTANCE_DUMMY_TOKEN" not in environment
    assert "GIT_DIR" not in environment
    assert {key.upper(): value for key, value in environment.items()}[
        "SYSTEMROOT"
    ] == "platform-root"


def _git(repo: Path, *args: str) -> str:
    """Run git in an isolated fixture repository and return its output.

    Args:
        repo: Temporary repository.
        *args: Git arguments.

    Returns:
        Stripped git output.
    """
    return subprocess.run(  # noqa: S603  # fixed argv list, no shell
        ["git", "-C", str(repo), *args],  # noqa: S607  # git resolved from PATH as in CI
        env=_isolated_env(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _create_repo(tmp_path: Path) -> Path:
    """Create a repository with a base commit and a routine source change.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        Repository containing two commits.
    """
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "ci@example.invalid")
    _git(tmp_path, "config", "user.name", "CI fixture")
    (tmp_path / "base.txt").write_text("base\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "base")
    (tmp_path / "src/gepa_adk").mkdir(parents=True)
    (tmp_path / "src/gepa_adk/api.py").write_text("# ordinary change\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "routine")
    return tmp_path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create the isolated two-commit repository used by routing tests.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        Repository containing a routine source change.
    """
    return _create_repo(tmp_path)


def _run(repo: Path, event: str, payload: object, force: str = "false") -> dict:
    """Invoke the public CLI with an event file.

    Args:
        repo: Working repository.
        event: GitHub event name.
        payload: JSON event payload.
        force: Explicit full-matrix input.

    Returns:
        Decoded CLI output.
    """
    event_file = repo / "event.json"
    event_file.write_text(json.dumps(payload))
    result = subprocess.run(  # noqa: S603  # fixed argv list, no shell
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        env={
            **_isolated_env(),
            "GITHUB_EVENT_NAME": event,
            "GITHUB_EVENT_PATH": str(event_file),
            "FORCE_FULL": force,
        },
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _assert_matrix(result: dict, full: bool) -> None:
    """Assert exact supported combinations without duplicates.

    Args:
        result: CLI result.
        full: Whether the ten full-mode combinations are required.
    """
    rows = result["matrix"]["include"]
    actual = {(r["os"], r["python-version"], r["adk-version"]) for r in rows}
    expected = FULL if full else ROUTINE
    assert actual == expected
    assert len(rows) == len(expected)
    assert result["mode"] == ("full" if full else "routine")
    assert result["reason"]


@pytest.mark.parametrize("event", ["push", "pull_request"])
def test_routine_change(repo: Path, event: str) -> None:
    """Ordinary pushes and non-release pull requests run the six routine legs.

    Args:
        repo: Temporary repository.
        event: GitHub event type.
    """
    base, head = _git(repo, "rev-parse", "HEAD~"), _git(repo, "rev-parse", "HEAD")
    payload = {"before": base, "after": head}
    if event == "pull_request":
        payload = {
            "pull_request": {
                "base": {"sha": base},
                "head": {"sha": head, "ref": "feature/ordinary-change"},
            }
        }
    _assert_matrix(_run(repo, event, payload), full=False)


@pytest.mark.parametrize(
    ("event", "payload", "force", "full"),
    [
        ("workflow_dispatch", {}, "false", False),
        ("workflow_dispatch", {}, "true", True),
        ("workflow_call", {}, "true", True),
        ("schedule", {}, "false", True),
        ("release", {}, "false", True),
        ("unknown", {}, "false", True),
        ("push", {}, "false", True),
        ("pull_request", {}, "false", True),
        (
            "pull_request",
            {"pull_request": {"head": {"ref": "feature/ordinary-change"}}},
            "false",
            False,
        ),
        (
            "pull_request",
            {"pull_request": {"head": {"ref": "release-please--branches--main"}}},
            "false",
            True,
        ),
    ],
)
def test_event_routes(
    repo: Path, event: str, payload: dict, force: str, full: bool
) -> None:
    """Explicit full checks and incomplete event data preserve compatibility.

    A non-release pull request is routine even without comparison commits.

    Args:
        repo: Temporary repository.
        event: GitHub event type.
        payload: Event data.
        force: Full coverage override.
        full: Expected coverage mode.
    """
    _assert_matrix(_run(repo, event, payload, force), full=full)


@pytest.mark.parametrize("base", ["0" * 40, "f" * 40, "--all"])
def test_unavailable_base(repo: Path, base: str) -> None:
    """A missing, zero or invalid base cannot silently select routine checks.

    Args:
        repo: Temporary repository.
        base: Unavailable or invalid commit.
    """
    _assert_matrix(
        _run(repo, "push", {"before": base, "after": _git(repo, "rev-parse", "HEAD")}),
        full=True,
    )


def _commit_path(repo: Path, path: str) -> tuple[str, str]:
    """Commit a change to one path and return the comparison commits.

    Args:
        repo: Temporary repository.
        path: Repository-relative file to create or modify.

    Returns:
        The base and head commit SHAs around the change.
    """
    base = _git(repo, "rev-parse", "HEAD")
    file = repo / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text("changed\n")
    _git(repo, "add", path)
    _git(repo, "commit", "-m", f"change {path}")
    return base, _git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize("path", ["pyproject.toml", "uv.lock", ".python-version"])
def test_dependency_push_is_full(repo: Path, path: str) -> None:
    """A push to main that changes a dependency file selects all full legs.

    Args:
        repo: Temporary repository.
        path: Dependency file to modify.
    """
    base, head = _commit_path(repo, path)
    result = _run(repo, "push", {"before": base, "after": head})
    _assert_matrix(result, full=True)
    assert result["reason"] == "Dependency change on main"


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/ci.yml",
        ".github/actions/setup/action.yml",
        "scripts/check.py",
        "src/gepa_adk/utils/io.py",
        "tests/conftest.py",
        "tests/fixtures/models.py",
        "pyproject.toml.bak",
        "docs/uv.lock",
    ],
)
def test_formerly_sensitive_push_is_routine(repo: Path, path: str) -> None:
    """A push touching only non-dependency paths keeps routine coverage.

    Args:
        repo: Temporary repository.
        path: Formerly sensitive or near-miss path to modify.
    """
    base, head = _commit_path(repo, path)
    _assert_matrix(_run(repo, "push", {"before": base, "after": head}), full=False)


def test_dependency_rename_is_full(repo: Path) -> None:
    """Moving a dependency file away still counts its old path as changed.

    Args:
        repo: Temporary repository.
    """
    _commit_path(repo, "uv.lock")
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "mv", "uv.lock", "old.lock")
    _git(repo, "commit", "-m", "rename")
    _assert_matrix(
        _run(repo, "push", {"before": base, "after": _git(repo, "rev-parse", "HEAD")}),
        full=True,
    )


def test_malformed_event_is_error(repo: Path) -> None:
    """Malformed JSON must fail the planner rather than obscure broken input.

    Args:
        repo: Temporary repository.
    """
    event_file = repo / "event.json"
    event_file.write_text("{")
    result = subprocess.run(  # noqa: S603  # fixed argv list, no shell
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        env={
            **_isolated_env(),
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_EVENT_PATH": str(event_file),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "JSONDecodeError" in result.stderr


def test_release_branch_with_routine_diff(repo: Path) -> None:
    """A release branch must run full coverage even for an ordinary change.

    Args:
        repo: Temporary repository.
    """
    payload = {
        "pull_request": {
            "base": {"sha": _git(repo, "rev-parse", "HEAD~")},
            "head": {
                "sha": _git(repo, "rev-parse", "HEAD"),
                "ref": "release-please--branches--main",
            },
        }
    }
    _assert_matrix(_run(repo, "pull_request", payload), full=True)


def test_dependabot_lockfile_pull_request_is_routine(repo: Path) -> None:
    """A Dependabot lockfile pull request runs routine coverage without a diff.

    Args:
        repo: Temporary repository.
    """
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "uv.lock").write_text("bumped\n")
    _git(repo, "add", "uv.lock")
    _git(repo, "commit", "-m", "bump lockfile")
    payload = {
        "pull_request": {
            "base": {"sha": base},
            "head": {
                "sha": _git(repo, "rev-parse", "HEAD"),
                "ref": "dependabot/uv/production-dependencies-abc123",
            },
        }
    }
    _assert_matrix(_run(repo, "pull_request", payload), full=False)


def test_hook_environment_cannot_redirect_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inherited hook paths cannot redirect fixture writes or CLI comparisons.

    Args:
        tmp_path: Pytest temporary directory.
        monkeypatch: Environment override fixture.
    """
    decoy = tmp_path / "decoy"
    target = tmp_path / "target"
    decoy.mkdir()
    target.mkdir()
    _create_repo(decoy)
    _git(decoy, "config", "user.name", "Decoy owner")
    decoy_head = _git(decoy, "rev-parse", "HEAD")
    tracked_state = [decoy / ".git" / name for name in ("HEAD", "index", "config")]
    before = {path: path.read_bytes() for path in tracked_state}
    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(decoy / ".git/index"))

    _create_repo(target)
    base = _git(target, "rev-parse", "HEAD~")
    # Make the target HEAD unique: the decoy cannot resolve this comparison.
    (target / "base.txt").write_text("target only\n")
    _git(target, "add", "base.txt")
    _git(target, "commit", "-m", "target only")
    head = _git(target, "rev-parse", "HEAD")
    _assert_matrix(_run(target, "push", {"before": base, "after": head}), full=False)

    assert Path(_git(target, "rev-parse", "--show-toplevel")).samefile(target)
    assert _git(target, "config", "user.name") == "CI fixture"
    assert _git(decoy, "rev-parse", "HEAD") == decoy_head
    assert {path: path.read_bytes() for path in tracked_state} == before

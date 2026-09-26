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
}
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
    return subprocess.run(
        ["git", "-C", str(repo), *args],
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
    result = subprocess.run(
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
        full: Whether all twelve combinations are required.
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
    """Ordinary changes retain all Linux combinations and both other platforms.

    Args:
        repo: Temporary repository.
        event: GitHub event type.
    """
    base, head = _git(repo, "rev-parse", "HEAD~"), _git(repo, "rev-parse", "HEAD")
    payload = {"before": base, "after": head}
    if event == "pull_request":
        payload = {"pull_request": {"base": {"sha": base}, "head": {"sha": head}}}
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


@pytest.mark.parametrize(
    "path",
    [
        "pyproject.toml",
        "uv.lock",
        ".python-version",
        ".github/workflows/ci.yml",
        ".github/actions/setup/action.yml",
        "scripts/check.py",
        "src/gepa_adk/utils/io.py",
        "tests/conftest.py",
        "tests/fixtures/models.py",
    ],
)
def test_sensitive_changes(repo: Path, path: str) -> None:
    """Every declared dependency or platform-sensitive path selects all legs.

    Args:
        repo: Temporary repository.
        path: Sensitive file to modify.
    """
    base = _git(repo, "rev-parse", "HEAD")
    file = repo / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text("sensitive\n")
    _git(repo, "add", path)
    _git(repo, "commit", "-m", "sensitive")
    _assert_matrix(
        _run(repo, "push", {"before": base, "after": _git(repo, "rev-parse", "HEAD")}),
        full=True,
    )


def test_sensitive_rename(repo: Path) -> None:
    """Moving a sensitive file outside its directory still requires all legs.

    Args:
        repo: Temporary repository.
    """
    (repo / "scripts").mkdir()
    (repo / "scripts/old.py").write_text("sensitive\n")
    _git(repo, "add", "scripts/old.py")
    _git(repo, "commit", "-m", "sensitive base")
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "mv", "scripts/old.py", "new.txt")
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
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        env={
            **_isolated_env(),
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_EVENT_PATH": str(event_file),
        },
        capture_output=True,
        text=True,
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

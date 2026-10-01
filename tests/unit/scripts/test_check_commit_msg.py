"""Tests for the commit message gate and its ``prepare-commit-msg`` partner.

Range-mode tests build throwaway repositories under ``tmp_path`` with every
inherited ``GIT_*`` variable removed, so a run inside a git hook never
reaches this repository's own index or history.

Examples:
    Run this suite alone:

    ```console
    $ uv run pytest tests/unit/scripts/test_check_commit_msg.py -q
    ```

See Also:
    - [scripts.check_commit_msg][]: The commit-msg gate under test.
    - [scripts.prepare_commit_msg][]: The trailer stripper under test.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts import prepare_commit_msg
from scripts.check_commit_msg import (
    TYPES,
    body_problems,
    is_bot_author,
    main,
    message_lines,
    problems,
    run_git,
    strip_coauthors,
    subject_problems,
)

pytestmark = pytest.mark.unit

HUMAN = ("dev@example.com", "Dev Person")
DEPENDABOT = (
    "49699333+dependabot[bot]@users.noreply.github.com",
    "dependabot[bot]",
)
ACTIONS = (
    "41898282+github-actions[bot]@users.noreply.github.com",
    "github-actions[bot]",
)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create an isolated empty repository and change into it.

    Args:
        tmp_path: Per-test temporary directory.
        monkeypatch: Restores the environment and working directory.

    Returns:
        The repository directory.
    """
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.chdir(tmp_path)
    run_git(["init", "-q", "-b", "main"])
    return tmp_path


def _commit(message: str, author: tuple[str, str] = HUMAN) -> str:
    """Record an empty commit in the current repository.

    Args:
        message: The full commit message.
        author: Email and name of the author.

    Returns:
        The new commit's full hash.
    """
    email, name = author
    run_git(
        [
            "-c",
            f"user.email={email}",
            "-c",
            f"user.name={name}",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--allow-empty",
            "--no-verify",
            "-q",
            "-m",
            message,
        ]
    )
    return run_git(["rev-parse", "HEAD"]).stdout.strip()


def _message_file(tmp_path: Path, text: str) -> Path:
    """Write a commit message file the way git hands it to a hook.

    Args:
        tmp_path: Directory for the file.
        text: The message text.

    Returns:
        The file path.
    """
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Message parsing
# --------------------------------------------------------------------------- #


def test_strips_comment_lines() -> None:
    """Remove git's comment lines."""
    text = "feat: add feature\n# This is a comment\n\nMore text"
    assert message_lines(text) == ["feat: add feature", "", "More text"]


def test_strips_trailing_blank_lines() -> None:
    """Drop trailing blank lines."""
    assert message_lines("feat: add feature\n\n") == ["feat: add feature"]


def test_scissors_line_cuts_off_rest() -> None:
    """Discard everything after the scissors line."""
    text = "feat: add feature\n# --- >8 ---\nhidden"
    assert message_lines(text) == ["feat: add feature"]


@pytest.mark.parametrize("kind", TYPES)
def test_every_allowed_type_passes(kind: str) -> None:
    """Accept each type the PR rules allow, plus build and ci."""
    assert subject_problems(f"{kind}: do a thing") == []
    assert subject_problems(f"{kind}(scope)!: do a thing") == []


def test_type_set_is_the_pr_rules_set() -> None:
    """Pin the vocabulary to the PR rules plus build and ci."""
    assert set(TYPES) == {
        "feat",
        "fix",
        "docs",
        "refactor",
        "test",
        "chore",
        "perf",
        "build",
        "ci",
    }


@pytest.mark.parametrize("kind", ["style", "revert", "unknown", "Feat"])
def test_other_types_fail(kind: str) -> None:
    """Refuse a type outside the vocabulary."""
    found = subject_problems(f"{kind}: something")
    assert f"the type {kind!r} is not one of" in found[0]


def test_empty_subject() -> None:
    """Refuse an empty subject."""
    assert "the subject is not" in subject_problems("")[0]


def test_free_text_subject() -> None:
    """Refuse a subject with no type prefix."""
    assert "the subject is not" in subject_problems("update stuff")[0]


def test_empty_scope() -> None:
    """Refuse empty parentheses."""
    assert "the scope is empty" in subject_problems("feat(): add feature")[0]


def test_trailing_period() -> None:
    """Refuse a description ending with a period."""
    assert "ends with a period" in subject_problems("feat: add feature.")[0]


def test_empty_description() -> None:
    """Refuse an empty description."""
    assert "the description is empty" in subject_problems("feat: ")[0]


def test_second_line_must_be_blank() -> None:
    """Refuse a body that starts on the second line."""
    assert body_problems(["feat: x", "body"]) == [
        "the body needs one blank line after the subject"
    ]


def test_breaking_change_must_be_upper_case() -> None:
    """Refuse a lower-case breaking-change footer."""
    found = body_problems(["feat!: x", "", "breaking change: gone"])
    assert "upper case" in found[0]
    assert body_problems(["feat!: x", "", "BREAKING CHANGE: gone"]) == []


@pytest.mark.parametrize(
    "text",
    [
        'Merge branch "feature"\n',
        "Merge pull request #1 from a/b\n",
        'Revert "feat: add feature"\n',
        "fixup! feat: add feature\n",
        "squash! feat: add feature\n",
        "amend! feat: add feature\n",
    ],
)
def test_generated_messages_are_skipped(text: str) -> None:
    """Skip messages git writes itself."""
    assert problems(text) == []


def test_empty_message_fails() -> None:
    """Refuse a message holding only comments."""
    assert problems("# only a comment\n") == ["the message is empty"]


def test_worker_trailers_pass() -> None:
    """Allow Generated-By and Specified-By trailers."""
    text = (
        "feat(engine): add a thing\n\nCloses #1\n\n"
        "Generated-By: claude-opus-5-5 (via Claude Code Agent tool, builder)\n"
        "Specified-By: unknown\n"
    )
    assert problems(text) == []


@pytest.mark.parametrize(
    "trailer",
    [
        "Co-Authored-By: X <x@y>",
        "Co-authored-by: Claude <noreply@anthropic.com>",
        "co-authored-by: Someone Human <human@example.com>",
        "Co-Authored-By:   Cursor Agent <cursoragent@cursor.com>",
    ],
)
def test_every_co_authored_by_is_refused(trailer: str) -> None:
    """Refuse any Co-Authored-By trailer, whatever the identity."""
    found = problems(f"chore(hooks): add gates\n\n{trailer}\n")
    assert len(found) == 1
    assert "Co-Authored-By" in found[0]


def test_removes_every_co_authored_by_line() -> None:
    """Drop each trailer and the blank run it leaves behind."""
    text = (
        "feat: x\n\nBody.\n\nGenerated-By: m\n"
        "Co-Authored-By: A <a@b>\nco-authored-by: B <c@d>\n"
    )
    assert strip_coauthors(text) == "feat: x\n\nBody.\n\nGenerated-By: m\n"


def test_trailing_blank_lines_collapse() -> None:
    """Leave no double blank line where the trailer block stood."""
    text = "feat: x\n\nCo-Authored-By: A <a@b>\n"
    assert strip_coauthors(text) == "feat: x\n"


def test_message_without_trailer_is_unchanged() -> None:
    """Return a message without trailers byte for byte."""
    text = "feat: x\n\nmentions co-authored-by in prose\n"
    assert strip_coauthors(text) == text


@pytest.mark.parametrize(
    ("email", "name"),
    [
        DEPENDABOT,
        ACTIONS,
        ("release-please[bot]@users.noreply.github.com", "release-please[bot]"),
        ("bot@example.com", "renovate[bot]"),
    ],
)
def test_bot_identities(email: str, name: str) -> None:
    """Recognise a ``[bot]`` login by email or by name."""
    assert is_bot_author(email, name)


@pytest.mark.parametrize(
    ("email", "name"),
    [
        HUMAN,
        ("12345+someone@users.noreply.github.com", "Someone"),
        ("robot@example.com", "Robot"),
    ],
)
def test_human_identities(email: str, name: str) -> None:
    """Do not treat a person's noreply address as a bot."""
    assert not is_bot_author(email, name)


# --------------------------------------------------------------------------- #
# Hook mode
# --------------------------------------------------------------------------- #


def test_conforming_message_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pass a conforming message."""
    path = _message_file(tmp_path, "chore(hooks): add gates\n")
    assert main([str(path)]) == 0
    assert "checked" in capsys.readouterr().out


def test_update_stuff_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Refuse the free-text subject the issue names."""
    path = _message_file(tmp_path, "update stuff\n")
    assert main([str(path)]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_co_authored_by_is_refused_and_left_in_place(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Refuse a surviving trailer without rewriting the file."""
    text = "chore(hooks): add gates\n\nCo-Authored-By: X <x@y>\n"
    path = _message_file(tmp_path, text)
    assert main([str(path)]) == 1
    assert "Co-Authored-By" in capsys.readouterr().out
    assert path.read_text(encoding="utf-8") == text


def test_no_arguments_fails(capsys: pytest.CaptureFixture[str]) -> None:
    """Fail when no message file is named."""
    assert main([]) == 1
    assert "name the commit message file" in capsys.readouterr().out


def test_missing_file_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Fail on a message file that does not exist."""
    assert main([str(tmp_path / "nope")]) == 1
    assert "missing" in capsys.readouterr().out


def test_no_author_allowlist(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pass any committer identity; there is no author allowlist."""
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "stranger@example.org")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Stranger")
    path = _message_file(repo, "fix: a thing\n")
    assert main([str(path)]) == 0


def test_strips_trailers_so_the_check_passes(tmp_path: Path) -> None:
    """Strip every trailer at prepare time, then pass the gate."""
    path = _message_file(
        tmp_path,
        "chore(hooks): add gates\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n",
    )
    assert prepare_commit_msg.main([str(path)]) == 0
    assert path.read_text(encoding="utf-8") == "chore(hooks): add gates\n"
    assert main([str(path)]) == 0


def test_extra_hook_arguments_and_missing_files_are_ignored(tmp_path: Path) -> None:
    """Accept git's source and sha arguments after the file."""
    path = _message_file(tmp_path, "feat: x\n")
    assert prepare_commit_msg.main([str(path), "message"]) == 0
    assert prepare_commit_msg.main([str(tmp_path / "nope")]) == 0
    assert path.read_text(encoding="utf-8") == "feat: x\n"


# --------------------------------------------------------------------------- #
# Range mode
# --------------------------------------------------------------------------- #


def test_clean_range_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Pass a range of conforming human commits."""
    base = _commit("chore: start")
    _commit("feat(engine): add a thing", ("anyone@example.net", "Anyone"))
    _commit("fix: repair it")
    assert main(["--range", f"{base}..HEAD"]) == 0
    assert capsys.readouterr().out.count("checked") == 2


def test_empty_range_passes(repo: Path) -> None:
    """Pass a range that holds no commit."""
    _commit("chore: start")
    assert main(["--range", "HEAD..HEAD"]) == 0


def test_human_bad_message_fails(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail a human commit with a non-conforming subject."""
    base = _commit("chore: start")
    _commit("update stuff")
    assert main(["--range", f"{base}..HEAD"]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_human_co_authored_by_fails(repo: Path) -> None:
    """Fail a recorded commit that carries a Co-Authored-By trailer."""
    base = _commit("chore: start")
    _commit("feat: x\n\nCo-Authored-By: X <x@y>")
    assert main(["--range", f"{base}..HEAD"]) == 1


@pytest.mark.parametrize("bot", [DEPENDABOT, ACTIONS])
def test_bot_commits_are_skipped(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    bot: tuple[str, str],
) -> None:
    """Skip a ``[bot]`` author even when its message would fail."""
    base = _commit("chore: start")
    _commit("Bump foo from 1 to 2", bot)
    assert main(["--range", f"{base}..HEAD"]) == 0
    assert "skipped" in capsys.readouterr().out


def test_bot_skip_does_not_hide_a_human_failure(repo: Path) -> None:
    """Still fail the human commit next to a skipped bot commit."""
    base = _commit("chore: start")
    _commit("Bump foo from 1 to 2", DEPENDABOT)
    _commit("update stuff")
    assert main(["--range", f"{base}..HEAD"]) == 1


def test_merge_commit_is_skipped(repo: Path) -> None:
    """Skip a git-generated merge message in history."""
    base = _commit("chore: start")
    _commit("Merge branch 'topic'")
    assert main(["--range", f"{base}..HEAD"]) == 0


def test_bad_range_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Fail when git refuses the range."""
    _commit("chore: start")
    assert main(["--range", "nope..HEAD"]) == 1
    assert "git log refused the range" in capsys.readouterr().out


def test_range_takes_exactly_one_argument(capsys: pytest.CaptureFixture[str]) -> None:
    """Fail when ``--range`` has no range or too many."""
    assert main(["--range"]) == 1
    assert main(["--range", "a..b", "c"]) == 1
    assert "takes one revision range" in capsys.readouterr().out

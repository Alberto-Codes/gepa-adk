"""Commit gate: every message follows Conventional Commits 1.0.0.

The subject reads ``<type>[(scope)][!]: <description>``. The type is one
of the pull request rules' types (``feat``, ``fix``, ``docs``,
``refactor``, ``test``, ``chore``, ``perf``) plus ``build`` and ``ci`` for
dependency and workflow commits. A scope may not be empty, the
description may not be empty or end with a period, and a body starts one
blank line after the subject. A breaking change writes ``BREAKING
CHANGE`` in upper case.

``.claude/rules/pull-requests.md`` forbids every ``Co-Authored-By``
trailer, so the gate refuses one whatever identity it names. Worker
evidence uses ``Generated-By`` and ``Specified-By`` instead. The
``prepare-commit-msg`` stage (``scripts/prepare_commit_msg.py``) strips
such trailers first, so the refusal fires only on one that survives.

The gate reads the file pre-commit hands it at the ``commit-msg`` stage.
It skips a merge, a revert and a ``fixup!``, ``squash!`` or ``amend!``
message, because git writes those. CI is the backstop, because a hook can
be bypassed: ``--range`` checks every message a push or pull request adds,
skipping commits whose author is a ``[bot]`` login such as dependabot,
release-please or github-actions.

Examples:
    Run against one message file, then against a range:

    ```console
    $ uv run python scripts/check_commit_msg.py .git/COMMIT_EDITMSG
    checked .git/COMMIT_EDITMSG: feat, 1 issue reference
    $ uv run python scripts/check_commit_msg.py --range main..HEAD
    checked 79fde80dd: chore, 0 issue references
    ```

See Also:
    - [scripts.prepare_commit_msg][]: Strips ``Co-Authored-By`` trailers first.
    - [scripts.check_suppressions][]: The suppression gate wired beside it.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

SPEC = "https://www.conventionalcommits.org/en/v1.0.0/"
TYPES = (
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "test",
)
RANGE = "--range"
RANGE_ARGS = 2
COAUTHOR_PROBLEM = (
    "Co-Authored-By is forbidden by .claude/rules/pull-requests.md; "
    "record a worker with Generated-By or Specified-By instead"
)
_CO_AUTHORED_BY = re.compile(r"^\s*Co-Authored-By:", re.IGNORECASE)
_SUBJECT = re.compile(
    r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^()\n]*)\))?(?P<bang>!)?: (?P<rest>.*)$"
)
_GENERATED = re.compile(
    r"^(?:Merge (?:branch|branches|pull request|remote-tracking|tag|commit)\b"
    r"|Merge [0-9a-f]{7,40} into [0-9a-f]{7,40}$"
    r"|Revert \"[^\"]*\""
    r"|fixup!|squash!|amend!)",
)
_BREAKING = re.compile(r"^(?P<token>BREAKING[ -]CHANGE)(?=:| #)", re.IGNORECASE)
_COMMENT = re.compile(r"^#(?:\s|$)")
_SCISSORS = re.compile(r"^# --- >8 ---$", re.MULTILINE)
_ISSUE = re.compile(r"#\d+")
_TRAILING_REFS = re.compile(r"\s*\((?:#\d+(?:,\s*)?)+\)$")
_BOT = "[bot]"


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run git with a fixed argument list and capture its text output.

    Args:
        args: Arguments after ``git``.

    Returns:
        The completed process.

    Raises:
        FileNotFoundError: When git is not on ``PATH``.
    """
    git = shutil.which("git")
    if git is None:
        raise FileNotFoundError("git is not on PATH")
    return subprocess.run(  # noqa: S603  # fixed argv list, no shell
        [git, *args], capture_output=True, text=True, check=True
    )


def is_bot_author(email: str, name: str) -> bool:
    """Whether a commit author is a GitHub ``[bot]`` login.

    Args:
        email: The author email, such as
            ``49699333+dependabot[bot]@users.noreply.github.com``.
        name: The author name, such as ``dependabot[bot]``.

    Returns:
        True when the name or the email's local part ends with ``[bot]``.
    """
    local = email.rpartition("@")[0] if "@" in email else email
    return name.strip().endswith(_BOT) or local.endswith(_BOT)


def strip_coauthors(text: str) -> str:
    """Drop every ``Co-Authored-By`` line from a message.

    Args:
        text: Raw commit message file contents.

    Returns:
        The message without those lines and without the blank lines they
        leave at the end.
    """
    kept = [line for line in text.splitlines() if not _CO_AUTHORED_BY.match(line)]
    if len(kept) == len(text.splitlines()):
        return text
    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept) + ("\n" if text.endswith("\n") else "")


def message_lines(text: str) -> list[str]:
    """The message with git's own lines removed.

    Args:
        text: The raw content of the commit message file.

    Returns:
        The remaining lines, with trailing blank lines dropped.
    """
    cut = _SCISSORS.search(text)
    if cut is not None:
        text = text[: cut.start()]
    lines = [line for line in text.splitlines() if not _COMMENT.match(line)]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def subject_problems(subject: str) -> list[str]:
    """Why the subject line fails the specification, if it does.

    Args:
        subject: The first line of the message.

    Returns:
        Failure messages, empty when the subject passes.
    """
    match = _SUBJECT.match(subject)
    if match is None:
        return [f"the subject is not '<type>[(scope)][!]: <description>': {subject!r}"]
    kind = match["type"]
    if kind not in TYPES:
        return [f"the type {kind!r} is not one of: {', '.join(TYPES)}"]
    problems: list[str] = []
    scope = match["scope"]
    if scope is not None and not scope.strip():
        problems.append("the scope is empty: write a scope or drop the parentheses")
    description = _TRAILING_REFS.sub("", match["rest"].strip()).strip()
    if not description:
        problems.append("the description is empty")
    elif description.endswith("."):
        problems.append("the description ends with a period: drop it")
    return problems


def body_problems(lines: list[str]) -> list[str]:
    """Why the body and the footers fail the specification, if they do.

    Args:
        lines: Every line of the message, subject first.

    Returns:
        Failure messages, empty when the body passes.
    """
    problems: list[str] = []
    if len(lines) > 1 and lines[1].strip():
        problems.append("the body needs one blank line after the subject")
    for line in lines[1:]:
        match = _BREAKING.match(line)
        if match is not None and match["token"] not in {
            "BREAKING CHANGE",
            "BREAKING-CHANGE",
        }:
            problems.append(
                "write 'BREAKING CHANGE' or 'BREAKING-CHANGE' in upper case, "
                f"not {match['token']!r}"
            )
    return problems


def coauthor_problems(lines: list[str]) -> list[str]:
    """One failure for each ``Co-Authored-By`` trailer, whoever it names.

    Args:
        lines: Every line of the message, subject first.

    Returns:
        Failure messages, empty when no such trailer remains.
    """
    return [COAUTHOR_PROBLEM for line in lines if _CO_AUTHORED_BY.match(line)]


def problems(text: str) -> list[str]:
    """Every way the message fails the specification.

    Args:
        text: The raw content of the commit message file.

    Returns:
        Failure messages, empty when the message passes or git wrote it.
    """
    lines = message_lines(text)
    if not lines:
        return ["the message is empty"]
    if _GENERATED.match(lines[0]):
        return []
    return subject_problems(lines[0]) + body_problems(lines) + coauthor_problems(lines)


def summary(text: str) -> str:
    """The one-line report for a message that passed.

    Args:
        text: The raw content of the commit message file.

    Returns:
        The type and the issue reference count.
    """
    lines = message_lines(text)
    match = _SUBJECT.match(lines[0])
    kind = match["type"] if match else "generated"
    refs = len(set(_ISSUE.findall("\n".join(lines))))
    unit = "reference" if refs == 1 else "references"
    return f"{kind}, {refs} issue {unit}"


def messages_in_range(rev_range: str) -> list[tuple[str, str, str, str]]:
    """Every commit message in a revision range.

    Args:
        rev_range: A git range such as ``main..HEAD``.

    Returns:
        The short hash, author email, author name and message of each
        commit, newest first.
    """
    proc = run_git(["log", "-z", "--format=%H%n%ae%n%an%n%B", rev_range])
    found = []
    for chunk in proc.stdout.split("\0"):
        if not chunk.strip():
            continue
        sha, email, name, body = [*chunk.split("\n", 3), "", "", ""][:4]
        found.append((sha[:9], email, name, body))
    return found


def report(label: str, text: str) -> bool:
    """Check one message and print the outcome.

    Args:
        label: What to name the message in the output.
        text: The raw message.

    Returns:
        True when the message failed.
    """
    found = problems(text)
    for problem in found:
        print(f"FAIL {label}: {problem}")
    if not found:
        print(f"checked {label}: {summary(text)}")
    return bool(found)


def check_range(rev_range: str) -> int:
    """Check every non-bot commit message in a range.

    Args:
        rev_range: A git range such as ``main..HEAD``.

    Returns:
        Process exit code: 1 on any failure, else 0.
    """
    try:
        found = messages_in_range(rev_range)
    except subprocess.CalledProcessError as error:
        reason = (error.stderr or "").strip().splitlines()
        print(
            f"FAIL {rev_range}: git log refused the range: {reason[0] if reason else ''}"
        )
        return 1
    failed = False
    for sha, email, name, text in found:
        if is_bot_author(email, name):
            print(f"skipped {sha}: bot author {name}")
            continue
        failed |= report(sha, text)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """Run the gate.

    Args:
        argv: The message file pre-commit passes, or ``--range <range>``.
            None reads ``sys.argv``.

    Returns:
        Process exit code: 1 on any failure, else 0.
    """
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print("FAIL: name the commit message file")
        return 1
    if args[0] == RANGE:
        if len(args) != RANGE_ARGS:
            print(f"FAIL: {RANGE} takes one revision range")
            return 1
        code = check_range(args[1])
    else:
        failed = False
        for path in (Path(arg) for arg in args):
            if not path.is_file():
                print(f"FAIL {path}: missing")
                failed = True
                continue
            failed |= report(str(path), path.read_text(encoding="utf-8"))
        code = 1 if failed else 0
    if code:
        print(f"the specification is at {SPEC}")
    return code


if __name__ == "__main__":
    sys.exit(main())

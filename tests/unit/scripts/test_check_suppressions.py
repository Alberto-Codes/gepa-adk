"""Tests for the suppression ratchet in ``scripts/check_suppressions.py``.

Each test builds a small tree under ``tmp_path`` and changes into it, so
the scanner reads a fixture ``pyproject.toml`` and baseline keys are short
relative paths. Suppression directives appear here only inside string
literals, which the tokenizer-based scanner ignores by design.

Examples:
    Run this suite alone:

    ```console
    $ uv run pytest tests/unit/scripts/test_check_suppressions.py -q
    ```

See Also:
    - [scripts.check_suppressions][]: The gate under test.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from scripts.check_suppressions import (
    count_filterwarnings,
    count_per_file_ignores,
    count_ty_overrides,
    main,
    read_baseline,
    scan,
)

pytestmark = pytest.mark.unit

NOQA = "# noqa: E501"

PYPROJECT = """\
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "D100"]
"scripts/x.py" = ["S603"]

[tool.ty.src]
include = ["src"]

[[tool.ty.overrides]]
include = ["tests/**"]

[tool.ty.overrides.rules]
unresolved-attribute = "ignore"

[[tool.ty.overrides]]
include = ["src/a.py"]

[tool.pytest.ini_options]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning",
    "ignore:.*foo.*:UserWarning",
    "default::ResourceWarning",
]
"""

TOML_BASELINE = "filterwarnings\t2\nper-file-ignores\t3\nty-overrides\t2\n"


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Change into ``tmp_path`` holding a fixture pyproject and ``pkg``.

    Args:
        tmp_path: Per-test temporary directory.
        monkeypatch: Restores the working directory afterwards.

    Returns:
        The relative scan root ``pkg``.
    """
    monkeypatch.chdir(tmp_path)
    Path("pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    root = Path("pkg")
    root.mkdir()
    (root / "clean.py").write_text("import os\n\nprint(os)\n", encoding="utf-8")
    return root


def _run(root: Path, baseline: str | None = TOML_BASELINE, *extra: str) -> int:
    """Run ``main`` over ``root`` against a baseline file.

    Args:
        root: The directory to scan.
        baseline: Baseline text to write first, or None for no file.
        *extra: Further command-line arguments.

    Returns:
        The exit code.
    """
    path = Path("baseline.txt")
    if baseline is not None:
        path.write_text(baseline, encoding="utf-8")
    return main([str(root), "--baseline", str(path), *extra])


def _write(path: Path, text: str) -> None:
    """Write ``text`` to ``path``.

    Args:
        path: File to write.
        text: Content.
    """
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# pyproject counters
# --------------------------------------------------------------------------- #


def test_count_per_file_ignores_missing_tables_is_zero() -> None:
    """Count zero when the ruff tables are absent at any depth."""
    for data in (
        {},
        {"tool": {}},
        {"tool": {"ruff": {}}},
        {"tool": {"ruff": {"lint": {}}}},
    ):
        assert count_per_file_ignores(data) == 0


def test_count_per_file_ignores_sums_codes_across_patterns() -> None:
    """Count every code, so a new code on an existing pattern counts."""
    data = {
        "tool": {
            "ruff": {"lint": {"per-file-ignores": {"a": ["E1", "E2"], "b": ["W3"]}}}
        }
    }
    assert count_per_file_ignores(data) == 3
    data["tool"]["ruff"]["lint"]["per-file-ignores"]["a"].append("F4")
    assert count_per_file_ignores(data) == 4


def test_count_ty_overrides_counts_table_headers() -> None:
    """Count each ``[[tool.ty.overrides]]`` block once."""
    assert count_ty_overrides({}) == 0
    assert count_ty_overrides({"tool": {"ty": {"overrides": [{}, {}, {}]}}}) == 3


def test_count_filterwarnings_counts_only_ignore_entries() -> None:
    """Count entries that start with ``ignore``, not ``error`` or ``default``."""
    data = {
        "tool": {
            "pytest": {
                "ini_options": {
                    "filterwarnings": ["error", "ignore::X", "ignore:y:Z", "default"]
                }
            }
        }
    }
    assert count_filterwarnings(data) == 2
    assert count_filterwarnings({}) == 0


def test_real_pyproject_counts_match_baseline() -> None:
    """Keep the committed baseline in step with the real pyproject."""
    repo = Path(__file__).resolve().parents[3]
    baseline = read_baseline(repo / "scripts" / "suppressions_baseline.txt")
    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    assert baseline["per-file-ignores"] == count_per_file_ignores(data)
    assert baseline["ty-overrides"] == count_ty_overrides(data)
    assert baseline["filterwarnings"] == count_filterwarnings(data)


# --------------------------------------------------------------------------- #
# Scanner
# --------------------------------------------------------------------------- #


def test_planted_suppression_in_code_line_is_flagged(tmp_path: Path) -> None:
    """Flag a suppression comment on a code line."""
    probe = tmp_path / "probe.py"
    _write(probe, f"import os  {NOQA}\n")
    findings, files_scanned = scan([tmp_path])
    assert files_scanned == 1
    assert len(findings) == 1
    assert findings[0].endswith(f"import os  {NOQA}")


def test_standalone_comment_suppression_is_flagged(tmp_path: Path) -> None:
    """Flag a suppression on its own comment line."""
    _write(tmp_path / "probe.py", f"{NOQA}\nimport os\n")
    findings, _ = scan([tmp_path])
    assert len(findings) == 1
    assert findings[0].endswith(NOQA)


@pytest.mark.parametrize(
    "template",
    [
        'S = "this mentions {d} in prose"\n',
        '"""A docstring naming {d}."""\n',
    ],
)
@pytest.mark.parametrize(
    "directive",
    [NOQA, "# type: ignore[assignment]", "# ty: ignore", "# pyright: ignore"],
)
def test_directive_inside_a_string_is_not_flagged(
    tmp_path: Path, template: str, directive: str
) -> None:
    """Ignore directive text inside strings and docstrings."""
    _write(tmp_path / "probe.py", template.format(d=directive))
    assert scan([tmp_path]) == ([], 1)


@pytest.mark.parametrize(
    "directive",
    [
        NOQA,
        "# type: ignore[assignment]",
        "# ty: ignore[invalid-assignment]",
        "#ty:ignore",
        "# ruff: noqa",
        "# pyright: ignore",
    ],
)
def test_every_directive_kind_is_flagged(tmp_path: Path, directive: str) -> None:
    """Flag each supported suppression directive."""
    _write(tmp_path / "probe.py", f"value = 1  {directive}\n")
    findings, _ = scan([tmp_path])
    assert len(findings) == 1


def test_unparseable_file_falls_back_to_line_scan(tmp_path: Path) -> None:
    """Scan an untokenizable file line by line."""
    _write(tmp_path / "probe.py", f"def broken(:\n    pass  {NOQA}\n")
    findings, files_scanned = scan([tmp_path])
    assert files_scanned == 1
    assert len(findings) == 1
    assert "pass" in findings[0]


def test_pycache_is_skipped(tmp_path: Path) -> None:
    """Skip ``__pycache__`` directories."""
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    _write(cache / "probe.py", f"x = 1  {NOQA}\n")
    assert scan([tmp_path]) == ([], 0)


# --------------------------------------------------------------------------- #
# Baseline ratchet
# --------------------------------------------------------------------------- #


def test_clean_tree_with_matching_toml_counts_passes(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pass a tree with no inline suppression and matching toml counts."""
    code = _run(tree)
    out = capsys.readouterr().out
    assert code == 0, out
    assert "FAIL" not in out


def test_unlisted_file_with_a_suppression_fails(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail a file the baseline does not list as soon as it suppresses."""
    _write(tree / "new.py", f"x = 1  {NOQA}\n")
    assert _run(tree) == 1
    out = capsys.readouterr().out
    assert "FAIL pkg/new.py: 1 inline suppression(s) (baseline 0)" in out
    assert f"pkg/new.py:1: x = 1  {NOQA}" in out


def test_listed_file_at_recorded_count_passes(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pass a listed file whose count equals its baseline entry."""
    _write(tree / "old.py", f"x = 1  {NOQA}\ny = 2  # type: ignore\n")
    assert _run(tree, TOML_BASELINE + "pkg/old.py\t2\n") == 0, capsys.readouterr().out


def test_listed_file_that_grows_fails(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail a listed file that gained a suppression."""
    _write(tree / "old.py", f"x = 1  {NOQA}\ny = 2  {NOQA}\nz = 3  {NOQA}\n")
    assert _run(tree, TOML_BASELINE + "pkg/old.py\t2\n") == 1
    assert "FAIL pkg/old.py: 3 inline suppression(s) (baseline 2)" in (
        capsys.readouterr().out
    )


def test_listed_file_that_shrinks_fails_naming_update(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail a listed file that lost a suppression until the ratchet moves."""
    _write(tree / "old.py", f"x = 1  {NOQA}\n")
    assert _run(tree, TOML_BASELINE + "pkg/old.py\t2\n") == 1
    out = capsys.readouterr().out
    assert "FAIL pkg/old.py: 1 inline suppression(s), baseline records 2" in out
    assert "--update-baseline" in out


def test_listed_file_now_clean_fails_naming_update(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail a listed file that dropped every suppression."""
    assert _run(tree, TOML_BASELINE + "pkg/clean.py\t1\n") == 1
    out = capsys.readouterr().out
    assert "FAIL pkg/clean.py: 0 inline suppression(s), baseline records 1" in out
    assert "--update-baseline" in out


def test_missing_path_fails_naming_update(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail a baseline entry whose file no longer exists."""
    assert _run(tree, TOML_BASELINE + "pkg/gone.py\t4\n") == 1
    out = capsys.readouterr().out
    assert "FAIL pkg/gone.py: in the baseline but no longer exists" in out
    assert "--update-baseline" in out


def test_entries_outside_scanned_roots_are_ignored(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Leave entries for roots this run did not scan alone."""
    assert _run(tree, TOML_BASELINE + "elsewhere/far.py\t4\n") == 0, (
        capsys.readouterr().out
    )


@pytest.mark.parametrize(
    ("key", "recorded", "expected"),
    [
        ("per-file-ignores", 2, "FAIL per-file-ignores: 3 (baseline 2)"),
        ("ty-overrides", 1, "FAIL ty-overrides: 2 (baseline 1)"),
        ("filterwarnings", 1, "FAIL filterwarnings: 2 (baseline 1)"),
    ],
)
def test_toml_count_that_grows_fails(
    tree: Path,
    capsys: pytest.CaptureFixture[str],
    key: str,
    recorded: int,
    expected: str,
) -> None:
    """Fail each pyproject count that exceeds its recorded value."""
    baseline = TOML_BASELINE.replace(f"{key}\t{recorded + 1}", f"{key}\t{recorded}")
    assert _run(tree, baseline) == 1
    assert expected in capsys.readouterr().out.splitlines()


@pytest.mark.parametrize("key", ["per-file-ignores", "ty-overrides", "filterwarnings"])
def test_toml_count_that_shrinks_fails_naming_update(
    tree: Path, capsys: pytest.CaptureFixture[str], key: str
) -> None:
    """Fail each pyproject count that fell below its recorded value."""
    lines = TOML_BASELINE.splitlines()
    bumped = [
        f"{line.split(chr(9))[0]}\t{int(line.split(chr(9))[1]) + 5}"
        if line.startswith(key)
        else line
        for line in lines
    ]
    assert _run(tree, "\n".join(bumped) + "\n") == 1
    out = capsys.readouterr().out
    assert f"FAIL {key}: " in out
    assert "baseline records" in out
    assert "--update-baseline" in out


def test_unlisted_toml_count_fails(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail a non-zero pyproject count that the baseline omits."""
    assert _run(tree, "per-file-ignores\t3\nty-overrides\t2\n") == 1
    assert "FAIL filterwarnings: 2 (baseline 0)" in capsys.readouterr().out.splitlines()


def test_update_baseline_rewrites_and_exits_zero(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rewrite the baseline from the tree and pass on the next run."""
    _write(tree / "old.py", f"x = 1  {NOQA}\ny = 2  # type: ignore\n")
    path = Path("baseline.txt")
    assert _run(tree, "pkg/gone.py\t9\nfar/away.py\t1\n", "--update-baseline") == 0
    assert path.read_text(encoding="utf-8") == (
        "far/away.py\t1\n"
        "filterwarnings\t2\n"
        "per-file-ignores\t3\n"
        "pkg/old.py\t2\n"
        "ty-overrides\t2\n"
    )
    capsys.readouterr()
    assert main([str(tree), "--baseline", str(path)]) == 0


def test_malformed_baseline_line_fails(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Refuse a baseline line that is not ``key<TAB>count``."""
    assert _run(tree, TOML_BASELINE + "pkg/old.py two\n") == 1
    assert "malformed" in capsys.readouterr().out

"""Boundary and ratchet tests for the size gate in ``scripts/check_loc.py``.

Every fixture module is generated under ``tmp_path`` and the test changes
into that directory, so baseline keys are short relative paths such as
``pkg/mod.py``. Each case pins one boundary of the real counter or one
ratchet rule of the real ``main``.

Examples:
    Run this suite alone:

    ```console
    $ uv run pytest tests/unit/scripts/test_check_loc.py -q
    ```

See Also:
    - [scripts.check_loc][]: The gate under test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_loc import (
    count_code_lines,
    count_function_lines,
    main,
    read_baseline,
)

pytestmark = pytest.mark.unit


def _module_source(code_lines: int) -> str:
    """Build a module source with exactly ``code_lines`` code lines.

    Args:
        code_lines: Number of assignment lines to emit.

    Returns:
        The module source text.
    """
    return "".join(f"x{i} = {i}\n" for i in range(code_lines))


def _function_source(body_lines: int) -> str:
    """Build a decorated function with exactly ``body_lines`` code lines.

    Args:
        body_lines: Number of assignment lines in the function body.

    Returns:
        The module source text defining ``long_one``.
    """
    body = "".join(f"    a{i} = {i}\n" for i in range(body_lines))
    return (
        "import functools\n\n\n"
        "@functools.cache\n"
        "def long_one(\n    first: int,\n    second: int,\n) -> None:\n"
        f"{body}"
    )


@pytest.fixture
def pkg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Change into ``tmp_path`` and create an empty ``pkg`` directory.

    Args:
        tmp_path: Per-test temporary directory.
        monkeypatch: Restores the working directory afterwards.

    Returns:
        The relative package directory ``pkg``.
    """
    monkeypatch.chdir(tmp_path)
    directory = Path("pkg")
    directory.mkdir()
    return directory


def _run(pkg: Path, baseline: str | None = None, *extra: str) -> tuple[int, Path]:
    """Run ``main`` over ``pkg`` against a baseline file.

    Args:
        pkg: The package directory to scan.
        baseline: Baseline text to write first, or None for no file.
        *extra: Further command-line arguments.

    Returns:
        The exit code and the baseline path.
    """
    path = Path("baseline.txt")
    if baseline is not None:
        path.write_text(baseline, encoding="utf-8")
    return main([str(pkg), "--baseline", str(path), *extra]), path


@pytest.mark.parametrize(
    ("lines", "exit_code"),
    [(300, 0), (301, 1), (320, 1), (321, 1)],
)
def test_module_limit(
    pkg: Path,
    capsys: pytest.CaptureFixture[str],
    lines: int,
    exit_code: int,
) -> None:
    """Hold the 300-line module limit at its exact boundary."""
    (pkg / "mod.py").write_text(_module_source(lines), encoding="utf-8")
    assert count_code_lines(pkg / "mod.py") == lines
    code, _ = _run(pkg)
    assert code == exit_code
    out = capsys.readouterr().out
    expected = f"FAIL pkg/mod.py: {lines} code lines (limit 300)"
    assert (expected in out.splitlines()) is (exit_code == 1)
    assert ("FAIL" in out) is (exit_code == 1)


def test_docstring_and_comment_lines_do_not_count(tmp_path: Path) -> None:
    """Add only documentation lines and see no count change."""
    plain = tmp_path / "plain.py"
    documented = tmp_path / "documented.py"
    commented = tmp_path / "commented.py"
    source = _module_source(10) + _function_source(5)
    plain.write_text(source, encoding="utf-8")
    documented.write_text(
        '"""Module.\n\nMore text.\n"""\n'
        + source.replace(
            ") -> None:\n", ') -> None:\n    """Doc.\n\n    More.\n    """\n'
        ),
        encoding="utf-8",
    )
    commented.write_text(
        "# header\n\n"
        + source.replace("    a0 = 0\n", "    # note\n    a0 = 0  # tail\n"),
        encoding="utf-8",
    )
    for path in (documented, commented):
        assert count_code_lines(path) == count_code_lines(plain)
        assert count_function_lines(path) == count_function_lines(plain)


def test_function_count_excludes_decorator_and_signature(tmp_path: Path) -> None:
    """Count only body lines of a decorated, multi-line signature."""
    path = tmp_path / "mod.py"
    path.write_text(_function_source(7), encoding="utf-8")
    assert count_function_lines(path) == [("long_one", 7)]


def test_nested_function_counts_toward_parent(tmp_path: Path) -> None:
    """Charge a nested function's lines to its enclosing function."""
    path = tmp_path / "mod.py"
    path.write_text(
        "class Box:\n"
        "    def outer(self) -> int:\n"
        "        def inner() -> int:\n"
        "            return 1\n"
        "        return inner()\n",
        encoding="utf-8",
    )
    counts = dict(count_function_lines(path))
    assert counts["Box.outer"] == 3
    assert counts["Box.outer.inner"] == 1


def _fail_line(qualname: str, lines: int) -> str:
    """Build the exact FAIL line ``main`` prints for an unlisted long function.

    Args:
        qualname: Qualified name of the function.
        lines: Body code lines of the function.

    Returns:
        The expected output line.
    """
    return f"FAIL pkg/mod.py:{qualname}: {lines} code lines (function limit 50)"


@pytest.mark.parametrize(("lines", "exit_code"), [(50, 0), (51, 1)])
def test_function_limit_boundary(
    pkg: Path,
    capsys: pytest.CaptureFixture[str],
    lines: int,
    exit_code: int,
) -> None:
    """Pass a 50-line function and fail a 51-line one with its FAIL line."""
    (pkg / "mod.py").write_text(_function_source(lines), encoding="utf-8")
    assert count_function_lines(pkg / "mod.py") == [("long_one", lines)]
    code, _ = _run(pkg)
    assert code == exit_code
    out = capsys.readouterr().out.splitlines()
    assert (_fail_line("long_one", lines) in out) is (exit_code == 1)
    assert any(line.startswith("FAIL") for line in out) is (exit_code == 1)


def test_long_nested_function_fails_by_qualname(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail a long nested function by its own qualname and its parent too."""
    body = "".join(f"        b{i} = {i}\n" for i in range(51))
    (pkg / "mod.py").write_text(
        f"def outer() -> None:\n    def inner() -> None:\n{body}    inner()\n",
        encoding="utf-8",
    )
    code, _ = _run(pkg)
    assert code == 1
    out = capsys.readouterr().out.splitlines()
    assert _fail_line("outer.inner", 51) in out
    assert _fail_line("outer", 53) in out


def test_long_method_fails_by_class_qualname(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Name a long method as Class.method in its FAIL line."""
    body = "".join(f"        c{i} = {i}\n" for i in range(51))
    (pkg / "mod.py").write_text(
        f"class Box:\n    def run(self) -> None:\n{body}", encoding="utf-8"
    )
    code, _ = _run(pkg)
    assert code == 1
    assert _fail_line("Box.run", 51) in capsys.readouterr().out.splitlines()


def test_module_and_function_limits_both_report(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Report a long module and a long function from the same file."""
    (pkg / "mod.py").write_text(
        _module_source(260) + _function_source(51), encoding="utf-8"
    )
    total = count_code_lines(pkg / "mod.py")
    assert total > 300
    code, _ = _run(pkg)
    assert code == 1
    out = capsys.readouterr().out.splitlines()
    assert f"FAIL pkg/mod.py: {total} code lines (limit 300)" in out
    assert _fail_line("long_one", 51) in out


def test_empty_root_fails(pkg: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Fail loudly when a root holds no Python file."""
    code, _ = _run(pkg)
    assert code == 1
    assert "FAIL pkg: no Python files found" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# Baseline ratchet
# --------------------------------------------------------------------------- #


def test_listed_module_at_recorded_count_passes(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pass an oversized module whose count equals its baseline entry."""
    (pkg / "mod.py").write_text(_module_source(310), encoding="utf-8")
    code, _ = _run(pkg, "pkg/mod.py\t310\n")
    out = capsys.readouterr().out
    assert code == 0, out
    assert "FAIL" not in out


def test_listed_module_that_grows_fails(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail an oversized module that grew past its recorded count."""
    (pkg / "mod.py").write_text(_module_source(311), encoding="utf-8")
    code, _ = _run(pkg, "pkg/mod.py\t310\n")
    assert code == 1
    out = capsys.readouterr().out.splitlines()
    assert "FAIL pkg/mod.py: 311 code lines (baseline 310)" in out


def test_listed_module_that_shrinks_fails_naming_update(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail a shrunk module until the ratchet is lowered."""
    (pkg / "mod.py").write_text(_module_source(305), encoding="utf-8")
    code, _ = _run(pkg, "pkg/mod.py\t310\n")
    assert code == 1
    out = capsys.readouterr().out
    assert "FAIL pkg/mod.py: 305 code lines, baseline records 310" in out
    assert "--update-baseline" in out


def test_listed_module_back_under_limit_fails_naming_update(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail a listed module that now fits, so its entry is removed."""
    (pkg / "mod.py").write_text(_module_source(20), encoding="utf-8")
    code, _ = _run(pkg, "pkg/mod.py\t310\n")
    assert code == 1
    out = capsys.readouterr().out
    assert "FAIL pkg/mod.py: 20 code lines, baseline records 310" in out
    assert "--update-baseline" in out


def test_listed_function_grows_and_shrinks(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Apply the ratchet to function entries as well as modules."""
    (pkg / "mod.py").write_text(_function_source(60), encoding="utf-8")
    assert _run(pkg, "pkg/mod.py:long_one\t60\n")[0] == 0
    assert _run(pkg, "pkg/mod.py:long_one\t59\n")[0] == 1
    assert "FAIL pkg/mod.py:long_one: 60 code lines (baseline 59)" in (
        capsys.readouterr().out
    )
    assert _run(pkg, "pkg/mod.py:long_one\t61\n")[0] == 1
    out = capsys.readouterr().out
    assert "baseline records 61" in out
    assert "--update-baseline" in out


def test_missing_path_fails_naming_update(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail a baseline entry whose module or function no longer exists."""
    (pkg / "mod.py").write_text(_module_source(10), encoding="utf-8")
    code, _ = _run(pkg, "pkg/gone.py\t400\npkg/mod.py:gone\t70\n")
    assert code == 1
    out = capsys.readouterr().out
    assert "FAIL pkg/gone.py: in the baseline but no longer exists" in out
    assert "FAIL pkg/mod.py:gone: in the baseline but no longer exists" in out
    assert "--update-baseline" in out


def test_entries_outside_scanned_roots_are_ignored(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Leave entries for unscanned roots alone, as the edit hook needs."""
    (pkg / "mod.py").write_text(_module_source(10), encoding="utf-8")
    code, _ = _run(pkg, "other/far.py\t400\n")
    assert code == 0, capsys.readouterr().out


def test_unlisted_module_over_limit_fails_with_baseline_present(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fail an oversized module that the baseline does not list."""
    (pkg / "mod.py").write_text(_module_source(301), encoding="utf-8")
    (pkg / "big.py").write_text(_module_source(400), encoding="utf-8")
    code, _ = _run(pkg, "pkg/big.py\t400\n")
    assert code == 1
    out = capsys.readouterr().out.splitlines()
    assert "FAIL pkg/mod.py: 301 code lines (limit 300)" in out
    assert not any("big.py" in line for line in out)


def test_update_baseline_rewrites_and_exits_zero(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rewrite the baseline from the tree, listing only what exceeds a limit."""
    (pkg / "mod.py").write_text(
        _module_source(260) + _function_source(51), encoding="utf-8"
    )
    (pkg / "small.py").write_text(_module_source(5), encoding="utf-8")
    total = count_code_lines(pkg / "mod.py")
    code, path = _run(pkg, "pkg/gone.py\t999\nother/far.py\t400\n", "--update-baseline")
    assert code == 0
    assert path.read_text(encoding="utf-8") == (
        f"other/far.py\t400\npkg/mod.py\t{total}\npkg/mod.py:long_one\t51\n"
    )
    assert read_baseline(path) == {
        "other/far.py": 400,
        "pkg/mod.py": total,
        "pkg/mod.py:long_one": 51,
    }
    capsys.readouterr()
    assert _run(pkg)[0] == 0


def test_malformed_baseline_line_fails(
    pkg: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Refuse a baseline line that is not ``key<TAB>count``."""
    (pkg / "mod.py").write_text(_module_source(10), encoding="utf-8")
    code, _ = _run(pkg, "pkg/mod.py 12\n")
    assert code == 1
    assert "malformed" in capsys.readouterr().out

#!/usr/bin/env python3
"""Suppression gate: fail when a change silences a gate instead of fixing it.

CLAUDE.md forbids adding ``# noqa``, ``# type: ignore`` and
``per-file-ignores`` to make a gate pass. This gate gives that rule teeth.
gepa-adk predates it and carries suppressions with reasons, so
``scripts/suppressions_baseline.txt`` records what exists today and the
gate fails only on growth.

It counts, per file under ``src``, ``tests``, ``examples``, ``scripts``
and ``.claude/hooks``, every inline suppression comment (``noqa``,
``ruff: noqa``, ``type: ignore``, ``ty: ignore``, ``pyright: ignore``),
all kinds together. Only ``COMMENT`` tokens count: a directive inside a
string or docstring suppresses nothing. A file that cannot be tokenized
falls back to a line scan. From ``pyproject.toml`` it counts three more
keys: ``per-file-ignores`` (ruff codes summed over every pattern),
``ty-overrides`` (``[[tool.ty.overrides]]`` blocks) and
``filterwarnings`` (pytest entries that start with ``ignore``).

The baseline holds one ``key<TAB>count`` per line, and is a ratchet that
only moves down:

- an unlisted file or key fails with any suppression;
- a listed one fails when its count exceeds the recorded value;
- a listed one whose count fell, or whose file no longer exists, fails
  until ``--update-baseline`` lowers the entry.

Examples:
    Check the default roots, then lower the ratchet after a cleanup:

    ```console
    $ uv run python scripts/check_suppressions.py
    check_suppressions: 410 files scanned, 61 baseline entries hold
    $ uv run python scripts/check_suppressions.py --update-baseline
    wrote 61 entries to scripts/suppressions_baseline.txt
    ```

    List the suppression comments in one directory:

    ```python
    from pathlib import Path

    from scripts.check_suppressions import scan

    findings, scanned = scan([Path("scripts")])
    ```

See Also:
    - [scripts.check_loc][]: The same ratchet over module and function size.
    - [scripts.check_commit_msg][]: The commit message gate wired beside it.
"""

from __future__ import annotations

import argparse
import re
import sys
import tokenize
import tomllib
from pathlib import Path
from typing import Any

# A suppression comment anywhere in a line of Python.
SUPPRESSION = re.compile(
    r"#\s*(noqa|type:\s*ignore|ty:\s*ignore|ruff:\s*noqa|pyright:\s*ignore)"
)
ROOTS = ("src", "tests", "examples", "scripts", ".claude/hooks")
BASELINE = Path(__file__).resolve().parent / "suppressions_baseline.txt"
PYPROJECT = Path("pyproject.toml")
UPDATE = "--update-baseline"
TOML_KEYS = ("per-file-ignores", "ty-overrides", "filterwarnings")
_SKIP_PARTS = frozenset({"__pycache__", ".venv"})


def _file_findings(lines: list[str]) -> list[tuple[int, str]]:
    """Find the suppression comments in one file's lines.

    Args:
        lines: The file's lines with their endings.

    Returns:
        ``(line number, stripped line)`` for each suppression comment.
    """
    try:
        return [
            (token.start[0], token.line.strip())
            for token in tokenize.generate_tokens(iter(lines).__next__)
            if token.type == tokenize.COMMENT and SUPPRESSION.search(token.string)
        ]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # An untokenizable file still gets checked, line by line.
        return [
            (number, line.strip())
            for number, line in enumerate(lines, start=1)
            if SUPPRESSION.search(line)
        ]


def _python_files(paths: list[Path]) -> list[Path]:
    """Expand files and directories into the Python files to scan.

    Args:
        paths: Files or directories.

    Returns:
        Every ``.py`` file, skipping caches and virtual environments.
    """
    found: list[Path] = []
    for root in paths:
        files = sorted(root.rglob("*.py")) if root.is_dir() else [root]
        found.extend(f for f in files if not _SKIP_PARTS.intersection(f.parts))
    return found


def scan_counts(paths: list[Path]) -> tuple[dict[Path, list[tuple[int, str]]], int]:
    """Collect suppression comments per file under the given paths.

    Args:
        paths: Files or directories to scan.

    Returns:
        The findings for each file that has any, and the number of files
        scanned.
    """
    per_file: dict[Path, list[tuple[int, str]]] = {}
    scanned = 0
    for file in _python_files(paths):
        try:
            lines = file.read_text(encoding="utf-8", errors="replace").splitlines(
                keepends=True
            )
        except OSError:
            continue
        scanned += 1
        findings = _file_findings(lines)
        if findings:
            per_file[file] = findings
    return per_file, scanned


def scan(paths: list[Path]) -> tuple[list[str], int]:
    """Report every suppression comment found under the given paths.

    Args:
        paths: Files or directories to scan.

    Returns:
        One ``file:line: text`` string per finding, and the number of
        files scanned.
    """
    per_file, scanned = scan_counts(paths)
    findings = [
        f"{file}:{number}: {text}"
        for file, hits in per_file.items()
        for number, text in hits
    ]
    return findings, scanned


def _table(data: dict[str, Any], *keys: str) -> Any:
    """Walk nested TOML tables, returning an empty dict where one is missing.

    Args:
        data: Parsed TOML.
        *keys: The table names to descend through.

    Returns:
        The value at the end of the path, or ``{}``.
    """
    node: Any = data
    for key in keys:
        node = node.get(key, {}) if isinstance(node, dict) else {}
    return node


def count_per_file_ignores(data: dict[str, Any]) -> int:
    """Count ruff ``per-file-ignores`` codes summed over every pattern.

    Args:
        data: Parsed ``pyproject.toml``.

    Returns:
        The total number of codes.
    """
    table = _table(data, "tool", "ruff", "lint", "per-file-ignores")
    return sum(len(codes) for codes in table.values() if isinstance(codes, list))


def count_ty_overrides(data: dict[str, Any]) -> int:
    """Count ``[[tool.ty.overrides]]`` blocks.

    Args:
        data: Parsed ``pyproject.toml``.

    Returns:
        The number of override blocks.
    """
    overrides = _table(data, "tool", "ty", "overrides")
    return len(overrides) if isinstance(overrides, list) else 0


def count_filterwarnings(data: dict[str, Any]) -> int:
    """Count pytest ``filterwarnings`` entries that ignore a warning.

    Args:
        data: Parsed ``pyproject.toml``.

    Returns:
        The number of entries starting with ``ignore``.
    """
    entries = _table(data, "tool", "pytest", "ini_options", "filterwarnings")
    if not isinstance(entries, list):
        return 0
    return sum(1 for e in entries if isinstance(e, str) and e.startswith("ignore"))


def toml_counts(pyproject: Path) -> dict[str, int]:
    """Measure the three ``pyproject.toml`` suppression keys.

    Args:
        pyproject: The file to read. A missing file counts zero.

    Returns:
        The count for each of :data:`TOML_KEYS`.
    """
    data: dict[str, Any] = {}
    if pyproject.is_file():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return {
        "per-file-ignores": count_per_file_ignores(data),
        "ty-overrides": count_ty_overrides(data),
        "filterwarnings": count_filterwarnings(data),
    }


def read_baseline(path: Path) -> dict[str, int]:
    """Read a ``key<TAB>count`` baseline file.

    Args:
        path: The baseline file. A missing file reads as empty.

    Returns:
        The recorded count for each key.

    Raises:
        ValueError: When a non-blank line is not ``key<TAB>count``.
    """
    if not path.is_file():
        return {}
    entries: dict[str, int] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        key, sep, count = line.rpartition("\t")
        if not sep or not key or not count.isdigit():
            raise ValueError(f"{path}:{number}: malformed line {line!r}")
        entries[key] = int(count)
    return entries


def write_baseline(path: Path, entries: dict[str, int]) -> None:
    """Write non-zero entries sorted by key, one ``key<TAB>count`` per line.

    Args:
        path: The baseline file to replace.
        entries: The count for each key.
    """
    text = "".join(f"{k}\t{entries[k]}\n" for k in sorted(entries) if entries[k])
    path.write_text(text, encoding="utf-8")


def _key_path(path: Path) -> str:
    """Name a file the way the baseline does.

    Args:
        path: A scanned file or root.

    Returns:
        The path relative to the working directory with forward slashes,
        or the path as given when it lies elsewhere.
    """
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def in_scope(key: str, roots: list[Path]) -> bool:
    """Whether a baseline key belongs to this run.

    Args:
        key: A file path or one of :data:`TOML_KEYS`.
        roots: The files and directories this run scanned.

    Returns:
        True for a pyproject key, or a path at or under a scanned root.
    """
    if key in TOML_KEYS:
        return True
    for root in roots:
        prefix = _key_path(root).rstrip("/")
        if prefix in {"", "."} or key == prefix or key.startswith(prefix + "/"):
            return True
    return False


def compare(
    counts: dict[str, int], baseline: dict[str, int], roots: list[Path]
) -> list[str]:
    """Apply the ratchet rules and describe every failure.

    Args:
        counts: Measured counts per file key and pyproject key.
        baseline: Recorded counts from :func:`read_baseline`.
        roots: The paths this run scanned.

    Returns:
        One ``FAIL`` line per failure, empty when the tree passes.
    """
    hint = f"run scripts/check_suppressions.py {UPDATE} to lower the ratchet"
    failures: list[str] = []
    for key, n in sorted(counts.items()):
        recorded = baseline.get(key, 0)
        unit = "" if key in TOML_KEYS else " inline suppression(s)"
        if n > recorded:
            failures.append(f"FAIL {key}: {n}{unit} (baseline {recorded})")
        elif n < recorded:
            failures.append(
                f"FAIL {key}: {n}{unit}, baseline records {recorded}; {hint}"
            )
    failures.extend(
        f"FAIL {key}: in the baseline but no longer exists; {hint}"
        for key in sorted(baseline)
        if key not in counts and in_scope(key, roots)
    )
    return failures


def measure(
    roots: list[Path], pyproject: Path
) -> tuple[dict[str, int], dict[str, list[tuple[int, str]]], int]:
    """Measure every baseline key for this run.

    Args:
        roots: Existing files or directories to scan.
        pyproject: The ``pyproject.toml`` to count.

    Returns:
        The count for each key, the findings for each file key, and the
        number of files scanned. Every scanned file appears in the counts,
        with zero when it is clean, so a shrink to zero is caught.
    """
    per_file, scanned = scan_counts(roots)
    counts = {_key_path(f): 0 for f in _python_files(roots)}
    findings = {_key_path(f): hits for f, hits in per_file.items()}
    counts.update({k: len(v) for k, v in findings.items()})
    counts.update(toml_counts(pyproject))
    return counts, findings, scanned


def main(argv: list[str] | None = None) -> int:
    """Check or rewrite the suppression baseline.

    Args:
        argv: Paths to scan (default :data:`ROOTS`), ``--baseline PATH``
            and ``--update-baseline``. None reads ``sys.argv``.

    Returns:
        Process exit code: 1 on any failure, else 0.
    """
    parser = argparse.ArgumentParser(description="Gate suppression ratchet.")
    parser.add_argument("paths", nargs="*", default=list(ROOTS))
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument(UPDATE, dest="update", action="store_true")
    args = parser.parse_args(argv)
    roots = [Path(p) for p in args.paths if Path(p).exists()]
    try:
        baseline = read_baseline(args.baseline)
    except ValueError as error:
        print(f"FAIL {error}")
        return 1
    counts, findings, scanned = measure(roots, PYPROJECT)
    if args.update:
        entries = {k: v for k, v in baseline.items() if not in_scope(k, roots)}
        entries.update(counts)
        write_baseline(args.baseline, entries)
        print(
            f"wrote {sum(1 for v in entries.values() if v)} entries to {args.baseline}"
        )
        return 0
    failures = compare(counts, baseline, roots)
    for line in failures:
        print(line)
        key = line.removeprefix("FAIL ").split(": ", 1)[0]
        for number, text in findings.get(key, []):
            print(f"  {key}:{number}: {text}")
    if failures:
        print("Fix the cause instead of silencing the gate.")
        return 1
    print(
        f"check_suppressions: {scanned} files scanned, {len(baseline)} baseline entries hold"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

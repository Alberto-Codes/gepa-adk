"""Size gate: fail when a module or a function grows past its limit.

Counts *code* lines: lines carrying at least one real token, excluding
comments and docstrings, so docvet-mandated documentation never pushes a
file over the limit. The module limit is 300 code lines and the function
limit is 50 body code lines. Decorators and the signature do not count,
and a nested function counts toward its parent and is also checked on
its own.

gepa-adk predates the gate, so ``scripts/loc_baseline.txt`` records every
module and function already past its limit, one ``key<TAB>count`` per
line. A module key is its path from the repository root; a function key
appends ``:qualname``. The baseline is a ratchet that only moves down:

- an unlisted module or function fails above its limit;
- a listed one fails when its count exceeds the recorded value;
- a listed one whose count fell below the recorded value fails until
  ``--update-baseline`` lowers the entry;
- an entry whose module or function no longer exists fails the same way.

Only entries under the scanned roots are compared, so the edit hook can
check one directory at a time.

Examples:
    Run against the source tree, then lower the ratchet after a split:

    ```console
    $ uv run python scripts/check_loc.py src
    checked 120 files
    $ uv run python scripts/check_loc.py src --update-baseline
    wrote 64 entries to scripts/loc_baseline.txt
    ```

    Count the body lines of every function in one file:

    ```python
    from pathlib import Path

    from scripts.check_loc import count_function_lines

    for qualname, lines in count_function_lines(Path("scripts/check_loc.py")):
        print(qualname, lines)
    ```

See Also:
    - [scripts.check_suppressions][]: The same ratchet over gate suppressions.
    - [scripts.check_commit_msg][]: The commit message gate wired beside it.
"""

from __future__ import annotations

import argparse
import ast
import io
import sys
import tokenize
from pathlib import Path

LIMIT = 300
FUNCTION_LIMIT = 50
BASELINE = Path(__file__).resolve().parent / "loc_baseline.txt"
UPDATE = "--update-baseline"

_SKIP_TOKENS = frozenset(
    {
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.COMMENT,
        tokenize.ENDMARKER,
        tokenize.ENCODING,
    }
)


def _docstring_lines(tree: ast.Module) -> set[int]:
    """Collect the line numbers occupied by docstrings.

    Args:
        tree: Parsed module AST.

    Returns:
        All 1-based line numbers inside module, class, or function
        docstrings.
    """
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
            and body[0].end_lineno is not None
        ):
            lines.update(range(body[0].lineno, body[0].end_lineno + 1))
    return lines


def _code_lines(text: str) -> set[int]:
    """Collect the line numbers that carry code.

    A line carries code when it holds at least one token that is not a
    comment, and it is not part of a docstring.

    Args:
        text: Python source text.

    Returns:
        All 1-based code line numbers.
    """
    doc_lines = _docstring_lines(ast.parse(text))
    token_lines: set[int] = set()
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type in _SKIP_TOKENS:
            continue
        token_lines.update(range(tok.start[0], tok.end[0] + 1))
    return token_lines - doc_lines


def count_code_lines(path: Path) -> int:
    """Count lines of actual code in a Python file.

    A line counts when it carries at least one token that is not a
    comment, and it is not part of a docstring.

    Args:
        path: The Python file to measure.

    Returns:
        The number of code lines.
    """
    return len(_code_lines(path.read_text(encoding="utf-8")))


def count_function_lines(path: Path) -> list[tuple[str, int]]:
    """Count the body code lines of every function and method in a file.

    A body spans its first statement to the function's last line, so
    decorators and the signature are excluded. Docstring, comment and
    blank lines do not count. A nested function is listed on its own and
    also counts toward its parent.

    Args:
        path: The Python file to measure.

    Returns:
        ``(qualname, code lines)`` pairs in source order, where the
        qualname joins enclosing class and function names with dots.
    """
    text = path.read_text(encoding="utf-8")
    code = _code_lines(text)
    results: list[tuple[str, int]] = []
    stack: list[tuple[ast.AST, str]] = [(ast.parse(text), "")]
    while stack:
        node, prefix = stack.pop()
        children = list(ast.iter_child_nodes(node))
        for child in reversed(children):
            name = getattr(child, "name", "")
            qualname = f"{prefix}{name}" if name else prefix.rstrip(".")
            stack.append((child, f"{qualname}." if qualname else ""))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = node.end_lineno or node.body[-1].lineno
            span = range(node.body[0].lineno, end + 1)
            results.append((prefix.rstrip("."), len(code.intersection(span))))
    return results


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
    """Write entries sorted by key, one ``key<TAB>count`` per line.

    Args:
        path: The baseline file to replace.
        entries: The count for each key.
    """
    text = "".join(f"{key}\t{entries[key]}\n" for key in sorted(entries))
    path.write_text(text, encoding="utf-8")


def _key_path(path: Path) -> str:
    """Name a file the way the baseline does.

    Args:
        path: A file found under a scanned root.

    Returns:
        The path relative to the working directory with forward slashes,
        or the path as given when it lies elsewhere.
    """
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def measure(roots: list[Path]) -> tuple[dict[str, int], list[str]]:
    """Measure every module and function under the given roots.

    Args:
        roots: Directories to scan.

    Returns:
        The count for each module key and ``path:qualname`` key, and the
        roots that held no Python file. A repeated qualname keeps its
        largest count.
    """
    counts: dict[str, int] = {}
    empty: list[str] = []
    for root in roots:
        paths = sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
        if not paths:
            empty.append(str(root))
        for path in paths:
            key = _key_path(path)
            counts[key] = count_code_lines(path)
            for qualname, n in count_function_lines(path):
                name = f"{key}:{qualname}"
                counts[name] = max(n, counts.get(name, 0))
    return counts, empty


def limit_for(key: str) -> int:
    """The limit that applies to a baseline key.

    Args:
        key: A module path, or ``path:qualname`` for a function.

    Returns:
        :data:`FUNCTION_LIMIT` for a function key, else :data:`LIMIT`.
    """
    return FUNCTION_LIMIT if ":" in key else LIMIT


def in_scope(key: str, roots: list[Path]) -> bool:
    """Whether a baseline key lies under one of the scanned roots.

    Args:
        key: A module path, or ``path:qualname`` for a function.
        roots: The directories this run scanned.

    Returns:
        True when the key's path starts with a scanned root.
    """
    path = key.split(":", 1)[0]
    for root in roots:
        prefix = _key_path(root).rstrip("/")
        if prefix in {"", "."} or path == prefix or path.startswith(prefix + "/"):
            return True
    return False


def _over_limit(key: str, n: int) -> str:
    """The failure line for an unlisted key past its limit.

    Args:
        key: The module or function key.
        n: Its measured count.

    Returns:
        The ``FAIL`` line.
    """
    if ":" in key:
        return f"FAIL {key}: {n} code lines (function limit {FUNCTION_LIMIT})"
    return f"FAIL {key}: {n} code lines (limit {LIMIT})"


def compare(
    counts: dict[str, int], baseline: dict[str, int], roots: list[Path]
) -> list[str]:
    """Apply the ratchet rules and describe every failure.

    Args:
        counts: Measured counts from :func:`measure`.
        baseline: Recorded counts from :func:`read_baseline`.
        roots: The directories this run scanned.

    Returns:
        One ``FAIL`` line per failure, empty when the tree passes.
    """
    hint = f"run scripts/check_loc.py {UPDATE} to lower the ratchet"
    failures: list[str] = []
    for key, n in counts.items():
        recorded = baseline.get(key)
        if recorded is None:
            if n > limit_for(key):
                failures.append(_over_limit(key, n))
        elif n > recorded:
            failures.append(f"FAIL {key}: {n} code lines (baseline {recorded})")
        elif n < recorded:
            failures.append(
                f"FAIL {key}: {n} code lines, baseline records {recorded}; {hint}"
            )
    failures.extend(
        f"FAIL {key}: in the baseline but no longer exists; {hint}"
        for key in baseline
        if key not in counts and in_scope(key, roots)
    )
    return failures


def update(
    counts: dict[str, int], baseline: dict[str, int], roots: list[Path]
) -> dict[str, int]:
    """Build the baseline that records the current tree.

    Args:
        counts: Measured counts from :func:`measure`.
        baseline: The previous entries.
        roots: The directories this run scanned; entries elsewhere are kept.

    Returns:
        Entries outside the scanned roots plus every key past its limit.
    """
    kept = {k: v for k, v in baseline.items() if not in_scope(k, roots)}
    kept.update({k: n for k, n in counts.items() if n > limit_for(k)})
    return kept


def main(argv: list[str] | None = None) -> int:
    """Check or rewrite the size baseline for the given roots.

    Args:
        argv: Roots to scan (default ``src``), ``--baseline PATH`` and
            ``--update-baseline``. None reads ``sys.argv``.

    Returns:
        Process exit code: 1 on any failure, else 0.
    """
    parser = argparse.ArgumentParser(description="Module and function size gate.")
    parser.add_argument("roots", nargs="*", default=["src"])
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument(UPDATE, dest="update", action="store_true")
    args = parser.parse_args(argv)
    roots = [Path(r) for r in args.roots]
    try:
        baseline = read_baseline(args.baseline)
    except ValueError as error:
        print(f"FAIL {error}")
        return 1
    counts, empty = measure(roots)
    failures = [f"FAIL {root}: no Python files found" for root in empty]
    if args.update and not failures:
        entries = update(counts, baseline, roots)
        write_baseline(args.baseline, entries)
        print(f"wrote {len(entries)} entries to {args.baseline}")
        return 0
    failures += compare(counts, baseline, roots)
    for line in failures:
        print(line)
    modules = sum(1 for key in counts if ":" not in key)
    print(f"checked {modules} files")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

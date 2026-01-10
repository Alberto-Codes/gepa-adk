#!/usr/bin/env python3
"""Docstring staleness detection script.

Detects docstrings that are stale relative to code changes (drift) or just old
(age), using git blame to compare modification timestamps.

Output: Markdown report with drift and age metrics
"""

from __future__ import annotations

import argparse
import ast
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Setup paths
root = Path(__file__).resolve().parents[1]
src = root / "src" / "gepa_adk"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Fix Windows console encoding for Unicode output (emojis, etc.)
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


@dataclass
class DocstringInfo:
    """Information about a docstring location."""

    file: Path
    name: str
    kind: str  # "module", "class", "function"
    start_line: int
    end_line: int


@dataclass
class StalenessResult:
    """Result of staleness analysis."""

    file: Path
    name: str
    kind: str
    drift_days: int | None  # None if no code to compare
    age_days: int
    docstring_date: datetime
    code_date: datetime | None  # None if no code lines


def should_skip(path: Path) -> bool:
    """Check if a file should be skipped during parsing."""
    if "__pycache__" in path.parts:
        return True
    if path.name == "__main__.py":
        return True
    if path.name.startswith("_") and path.name not in {"__init__.py"}:
        return True
    return False


def get_docstring_line_range(
    node: ast.AsyncFunctionDef | ast.FunctionDef | ast.ClassDef | ast.Module,
    source_lines: list[str],
) -> tuple[int, int] | None:
    """Get the line range of a docstring for a given AST node.

    Args:
        node: AST node (Module, ClassDef, or FunctionDef)
        source_lines: Source code split into lines

    Returns:
        Tuple of (start_line, end_line) 1-indexed, or None if no docstring
    """
    docstring = ast.get_docstring(node, clean=False)
    if not docstring:
        return None

    # For module docstrings, start at line 1
    # For class/function, start after the def line
    if isinstance(node, ast.Module):
        start_line = 1
    else:
        start_line = node.lineno + 1

    # Scan forward from start_line to find where the docstring actually ends
    # (handling cases where there are decorators, etc.)
    for i, line in enumerate(source_lines[start_line - 1 :], start=start_line):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            # Found start of docstring
            quote_char = '"""' if stripped.startswith('"""') else "'''"
            if stripped.count(quote_char) >= 2:
                # Single-line docstring
                return (i, i)
            else:
                # Multi-line docstring - find closing quote
                for j, end_line in enumerate(source_lines[i:], start=i + 1):
                    if quote_char in end_line:
                        return (i, j)
            break

    return None


def find_docstrings(file: Path) -> list[DocstringInfo]:
    """Find all docstrings in a Python file.

    Args:
        file: Path to Python file

    Returns:
        List of DocstringInfo objects
    """
    try:
        source = file.read_text(encoding="utf-8")
        source_lines = source.splitlines()
        tree = ast.parse(source, filename=str(file))
    except (SyntaxError, UnicodeDecodeError) as exc:
        logger.warning("Failed to parse %s: %s", file, exc)
        return []

    docstrings: list[DocstringInfo] = []

    # Module docstring
    module_range = get_docstring_line_range(tree, source_lines)
    if module_range:
        docstrings.append(
            DocstringInfo(
                file=file,
                name="<module>",
                kind="module",
                start_line=module_range[0],
                end_line=module_range[1],
            )
        )

    # Walk AST for class and function docstrings
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            doc_range = get_docstring_line_range(node, source_lines)
            if doc_range:
                docstrings.append(
                    DocstringInfo(
                        file=file,
                        name=node.name,
                        kind="class",
                        start_line=doc_range[0],
                        end_line=doc_range[1],
                    )
                )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc_range = get_docstring_line_range(node, source_lines)
            if doc_range:
                docstrings.append(
                    DocstringInfo(
                        file=file,
                        name=node.name,
                        kind="function",
                        start_line=doc_range[0],
                        end_line=doc_range[1],
                    )
                )

    return docstrings


def get_line_timestamps(file: Path, start_line: int, end_line: int) -> list[datetime]:
    """Get git blame timestamps for a line range.

    Args:
        file: Path to file (relative to repo root)
        start_line: Start line (1-indexed)
        end_line: End line (1-indexed)

    Returns:
        List of datetime objects for each line's last modification
    """
    rel_path = file.relative_to(root)

    try:
        result = subprocess.run(
            [
                "git",
                "blame",
                "--line-porcelain",
                f"-L{start_line},{end_line}",
                str(rel_path),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.warning(
            "git blame failed for %s:%d-%d: %s", file, start_line, end_line, exc
        )
        return []

    # Parse --line-porcelain output
    # Format: lines starting with "committer-time <unix-timestamp>"
    timestamps: list[datetime] = []
    for line in result.stdout.splitlines():
        if line.startswith("committer-time "):
            unix_time = int(line.split()[1])
            timestamps.append(datetime.fromtimestamp(unix_time))

    return timestamps


def get_code_line_range(
    node: ast.AsyncFunctionDef | ast.FunctionDef | ast.ClassDef | ast.Module,
    docstring_end: int,
) -> tuple[int, int] | None:
    """Get the line range for code (excluding docstring) in a function/class.

    Args:
        node: AST node (ClassDef or FunctionDef)
        docstring_end: Last line of docstring

    Returns:
        Tuple of (start_line, end_line) for code lines, or None if no code
    """
    # Get end_lineno (available in Python 3.8+, may be None for some nodes)
    end_lineno: int | None = getattr(node, "end_lineno", None)

    if isinstance(node, ast.Module):
        # For modules, code is everything after the docstring
        if end_lineno is not None:
            code_start = docstring_end + 1
            if code_start <= end_lineno:
                return (code_start, end_lineno)
        return None

    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        # Code starts after docstring, ends at node.end_lineno
        if end_lineno is not None:
            code_start = docstring_end + 1
            if code_start <= end_lineno:
                return (code_start, end_lineno)

    return None


def analyze_file(
    file: Path, drift_threshold: int, age_threshold: int
) -> list[StalenessResult]:
    """Analyze a single Python file for stale docstrings.

    Args:
        file: Path to Python file
        drift_threshold: Days threshold for drift detection
        age_threshold: Days threshold for age detection

    Returns:
        List of StalenessResult objects for stale docstrings
    """
    try:
        source = file.read_text(encoding="utf-8")
        source_lines = source.splitlines()
        tree = ast.parse(source, filename=str(file))
    except (SyntaxError, UnicodeDecodeError) as exc:
        logger.debug("Failed to parse %s: %s", file, exc)
        return []

    results: list[StalenessResult] = []
    now = datetime.now()

    def analyze_node(
        node: ast.AsyncFunctionDef | ast.FunctionDef | ast.ClassDef | ast.Module,
        name: str,
        kind: str,
    ) -> None:
        """Analyze a single node for staleness."""
        doc_range = get_docstring_line_range(node, source_lines)
        if not doc_range:
            return

        # Get docstring timestamps
        doc_timestamps = get_line_timestamps(file, doc_range[0], doc_range[1])
        if not doc_timestamps:
            return

        docstring_date = max(doc_timestamps)
        age_days = (now - docstring_date).days

        # Get code timestamps (if there is code)
        code_range = get_code_line_range(node, doc_range[1])
        if code_range:
            code_timestamps = get_line_timestamps(file, code_range[0], code_range[1])
            if code_timestamps:
                code_date = max(code_timestamps)
                drift_days = (code_date - docstring_date).days
            else:
                code_date = None
                drift_days = None
        else:
            code_date = None
            drift_days = None

        # Check thresholds
        is_drifted = drift_days is not None and drift_days > drift_threshold
        is_aged = age_days > age_threshold

        if is_drifted or is_aged:
            results.append(
                StalenessResult(
                    file=file,
                    name=name,
                    kind=kind,
                    drift_days=drift_days,
                    age_days=age_days,
                    docstring_date=docstring_date,
                    code_date=code_date,
                )
            )

    # Analyze module docstring
    analyze_node(tree, "<module>", "module")

    # Analyze class and function docstrings
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            analyze_node(node, node.name, "class")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            analyze_node(node, node.name, "function")

    return results


def analyze_codebase(
    drift_threshold: int,
    age_threshold: int,
    files: list[Path] | None = None,
) -> list[StalenessResult]:
    """Analyze entire codebase for stale docstrings.

    Args:
        drift_threshold: Days threshold for drift detection
        age_threshold: Days threshold for age detection
        files: Optional list of specific files to analyze (default: entire codebase)

    Returns:
        List of all StalenessResult objects
    """
    all_results: list[StalenessResult] = []

    if files is not None:
        # Analyze only specified files
        for py_file in sorted(files):
            if should_skip(py_file):
                continue
            logger.debug("Analyzing %s", py_file.relative_to(root))
            file_results = analyze_file(py_file, drift_threshold, age_threshold)
            all_results.extend(file_results)
    else:
        # Original: analyze entire codebase
        for py_file in sorted(src.rglob("*.py")):
            if should_skip(py_file):
                continue
            logger.debug("Analyzing %s", py_file.relative_to(root))
            file_results = analyze_file(py_file, drift_threshold, age_threshold)
            all_results.extend(file_results)

    return all_results


def generate_report(
    results: list[StalenessResult],
    drift_threshold: int,
    age_threshold: int,
    mode: str,
    limit: int = 0,
) -> str:
    """Generate markdown report from staleness results.

    Args:
        results: List of StalenessResult objects
        drift_threshold: Days threshold used for drift
        age_threshold: Days threshold used for age
        mode: Report mode ("all", "drift", or "age")
        limit: Max results to show per section (0 for all)

    Returns:
        Markdown report as string
    """
    # Separate drifted and aged results
    drifted = [
        r
        for r in results
        if r.drift_days is not None and r.drift_days > drift_threshold
    ]
    aged = [r for r in results if r.age_days > age_threshold]

    # Sort by severity (worst first)
    drifted.sort(key=lambda r: r.drift_days or 0, reverse=True)
    aged.sort(key=lambda r: r.age_days, reverse=True)

    # Apply limit for display
    drifted_total = len(drifted)
    aged_total = len(aged)
    drifted_display = drifted if limit == 0 else drifted[:limit]
    aged_display = aged if limit == 0 else aged[:limit]

    # Build report
    lines: list[str] = []
    lines.append("# Stale Docstrings Report")
    lines.append("")
    lines.append(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"Thresholds: drift={drift_threshold} days, age={age_threshold} days"
    )
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    if mode in ("all", "drift"):
        lines.append(
            f"- **Drifted**: {len(drifted)} docstrings (code changed, docstring stale)"
        )
    if mode in ("all", "age"):
        lines.append(
            f"- **Aged**: {len(aged)} docstrings (untouched > {age_threshold} days)"
        )
    if mode == "all":
        # Count unique items (some may be both drifted and aged)
        unique = {(r.file, r.name) for r in results}
        lines.append(f"- **Total candidates**: {len(unique)} unique items")
    lines.append("")

    # Drifted section
    if mode in ("all", "drift") and drifted:
        lines.append("## Drifted Docstrings (code newer than docstring)")
        lines.append("")
        if limit > 0 and drifted_total > limit:
            lines.append(f"*Showing top {limit} of {drifted_total} total*")
            lines.append("")
        lines.append(
            "| File | Name | Kind | Drift (days) | Docstring Date | Code Date |"
        )
        lines.append(
            "|------|------|------|--------------|----------------|-----------|"
        )
        for r in drifted_display:
            rel_file = r.file.relative_to(root)
            doc_date = r.docstring_date.strftime("%Y-%m-%d")
            code_date = r.code_date.strftime("%Y-%m-%d") if r.code_date else "N/A"
            line = (
                f"| `{rel_file}` | `{r.name}` | {r.kind} | "
                f"{r.drift_days} | {doc_date} | {code_date} |"
            )
            lines.append(line)
        lines.append("")

    # Aged section
    if mode in ("all", "age") and aged:
        lines.append(f"## Aged Docstrings (untouched > {age_threshold} days)")
        lines.append("")
        if limit > 0 and aged_total > limit:
            lines.append(f"*Showing top {limit} of {aged_total} total*")
            lines.append("")
        lines.append("| File | Name | Kind | Age (days) | Last Modified |")
        lines.append("|------|------|------|------------|---------------|")
        for r in aged_display:
            rel_file = r.file.relative_to(root)
            doc_date = r.docstring_date.strftime("%Y-%m-%d")
            lines.append(
                f"| `{rel_file}` | `{r.name}` | {r.kind} | {r.age_days} | {doc_date} |"
            )
        lines.append("")

    # No results message
    if not drifted and not aged:
        lines.append("✨ No stale docstrings found! All docstrings are up to date.")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Generate docstring staleness report."""
    parser = argparse.ArgumentParser(
        description="Detect stale docstrings using git blame timestamps"
    )
    parser.add_argument(
        "--drift-threshold",
        type=int,
        default=30,
        help="Days threshold for drift detection (default: 30)",
    )
    parser.add_argument(
        "--age-threshold",
        type=int,
        default=30,
        help="Days threshold for age detection (default: 30)",
    )
    parser.add_argument(
        "--mode",
        choices=["all", "drift", "age"],
        default="all",
        help="Which metrics to report (default: all)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max results to show per section (default: 5, use 0 for all)",
    )
    parser.add_argument(
        "--files",
        type=Path,
        nargs="+",
        help="Specific files to analyze (default: entire codebase)",
    )

    args = parser.parse_args()

    logger.info("Starting docstring staleness detection...")
    logger.info("Drift threshold: %d days", args.drift_threshold)
    logger.info("Age threshold: %d days", args.age_threshold)
    logger.info("Mode: %s", args.mode)

    try:
        # Parse file list (convert to absolute paths)
        file_list = None
        if args.files:
            file_list = [root / f if not f.is_absolute() else f for f in args.files]
            logger.info("Analyzing %d specific files", len(file_list))

        # Analyze codebase
        results = analyze_codebase(args.drift_threshold, args.age_threshold, file_list)

        # Generate report
        report = generate_report(
            results, args.drift_threshold, args.age_threshold, args.mode, args.limit
        )

        # Output report
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(report, encoding="utf-8")
            logger.info("Report written to: %s", args.output)
        else:
            print(report)

        logger.info("Analysis complete - found %d stale items", len(results))

    except Exception as exc:
        logger.error("Failed to generate staleness report: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Check for Python files that won't be included in mkdocs documentation.

This script detects files that would be excluded from `make docs-build` due to
missing `__init__.py` files in parent directories. Mirrors the logic in
`docs/gen_ref_pages.py`.

Examples:
    Check specific files:
        $ python scripts/docstring_docs_coverage.py --files src/module/file.py

    Check all src files:
        $ python scripts/docstring_docs_coverage.py --all
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CoverageIssue:
    """Represents a file excluded from docs coverage."""

    file: str
    missing_init: str
    reason: str


def should_skip(path: Path) -> bool:
    """Check if a file should be skipped from docs generation."""
    if "__pycache__" in path.parts:
        return True
    if path.name == "__main__.py":
        return True
    if path.name.startswith("_") and path.name not in {"__init__.py"}:
        return True
    return False


def is_importable(path: Path, src_root: Path) -> tuple[bool, str | None]:
    """Check if a file can be imported (all parent dirs have __init__.py).

    Args:
        path: Path to the Python file
        src_root: Root of the source tree

    Returns:
        Tuple of (is_importable, missing_init_path or None)
    """
    rel = path.relative_to(src_root)
    for i in range(len(rel.parts) - 1):
        init_path = src_root.joinpath(*rel.parts[: i + 1], "__init__.py")
        if not init_path.exists():
            return False, str(init_path)
    return True, None


def check_docs_coverage(files: list[Path], src_root: Path) -> list[CoverageIssue]:
    """Check files for docs coverage issues.

    Args:
        files: List of Python files to check
        src_root: Root of the source tree (e.g., src/agent_workflow_suite)

    Returns:
        List of coverage issues found
    """
    issues = []

    for file_path in files:
        # Only check files under src_root
        try:
            file_path.relative_to(src_root)
        except ValueError:
            continue

        if should_skip(file_path):
            continue

        importable, missing_init = is_importable(file_path, src_root)
        if not importable and missing_init:
            issues.append(
                CoverageIssue(
                    file=str(file_path),
                    missing_init=missing_init,
                    reason=f"Missing {missing_init}",
                )
            )

    return issues


def main() -> int:
    """Run docs coverage check."""
    parser = argparse.ArgumentParser(
        description="Check for Python files excluded from mkdocs documentation"
    )
    parser.add_argument(
        "--files",
        nargs="*",
        help="Specific files to check",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all Python files in src/",
    )
    parser.add_argument(
        "--src-root",
        default="src/agent_workflow_suite",
        help="Source root directory",
    )

    args = parser.parse_args()

    src_root = Path(args.src_root).resolve()
    if not src_root.exists():
        print(f"ERROR: Source root not found: {src_root}", file=sys.stderr)
        return 1

    # Collect files to check
    if args.all:
        files = list(src_root.rglob("*.py"))
    elif args.files:
        files = [Path(f).resolve() for f in args.files if f.endswith(".py")]
    else:
        print("No files specified. Use --files or --all", file=sys.stderr)
        return 1

    issues = check_docs_coverage(files, src_root)

    if not issues:
        print("No docs coverage issues found.")
        return 0

    print("# Docs Coverage Issues\n")
    print(f"Found {len(issues)} file(s) excluded from `make docs-build`:\n")
    print("| File | Missing Init |")
    print("|------|--------------|")
    for issue in issues:
        print(f"| `{issue.file}` | `{issue.missing_init}` |")

    print(f"\n**Total docs coverage issues**: {len(issues)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Check for griffe docstring warnings (missing parameter types).

This script uses griffe (the mkdocstrings parser) to detect docstring issues
that would cause warnings during mkdocs build, specifically:
- Missing type annotations in Args/Keyword Args sections
- Other docstring parsing warnings

Usage:
    python scripts/docstring_griffe_check.py [--files FILE1 FILE2 ...]

Exit codes:
    0: No warnings found
    1: Warnings found (printed to stdout)
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Iterator
from typing import Any, cast


def _iter_objects(obj: object) -> Iterator[object]:
    """Recursively iterate through all griffe objects."""
    yield obj
    try:
        if hasattr(obj, "members"):
            members: dict[str, Any] = cast(Any, obj).members
            for member in members.values():
                yield from _iter_objects(member)
    except Exception:
        # Skip objects that can't be resolved (e.g., aliases to external modules)
        pass


def check_griffe_warnings(files: list[str] | None = None) -> list[str]:
    """Run griffe and capture any docstring warnings.

    Args:
        files (list[str] | None): Optional list of files to check.
            If None, checks all of src/gepa_adk.

    Returns:
        list[str]: List of warning messages.
    """
    import griffe

    # Capture griffe's logger output
    warnings: list[str] = []

    class WarningCapture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            if record.levelno >= logging.WARNING:
                warnings.append(record.getMessage())

    # Set up logging capture
    griffe_logger = logging.getLogger("griffe")
    handler = WarningCapture()
    handler.setLevel(logging.WARNING)
    griffe_logger.addHandler(handler)
    original_level = griffe_logger.level
    griffe_logger.setLevel(logging.WARNING)

    try:
        # Load the package
        pkg = griffe.load("gepa_adk", search_paths=["src"], docstring_parser="google")

        # Trigger docstring parsing for all objects (warnings are emitted on parse)
        for obj in _iter_objects(pkg):
            try:
                if hasattr(obj, "docstring"):
                    docstring = cast(Any, obj).docstring
                    if docstring:
                        _ = docstring.parsed
            except Exception:
                # Skip objects that can't be resolved (e.g., aliases to external modules)
                pass
    finally:
        griffe_logger.removeHandler(handler)
        griffe_logger.setLevel(original_level)

    # Filter to only requested files if specified
    if files:
        filtered = []
        for w in warnings:
            # Warning format: "src/gepa_adk/api.py:1098: No type..."
            if ":" in w:
                warn_file = w.split(":")[0]
                if any(warn_file in f or f in warn_file for f in files):
                    filtered.append(w)
        warnings = filtered

    return warnings


def main() -> int:
    """Run griffe check and report warnings.

    Returns:
        int: Exit code (0 = success, 1 = warnings found).
    """
    parser = argparse.ArgumentParser(description="Check for griffe docstring warnings")
    parser.add_argument(
        "--files",
        nargs="*",
        help="Specific files to check (default: all src/gepa_adk)",
    )
    args = parser.parse_args()

    warnings = check_griffe_warnings(args.files)

    if not warnings:
        print("No griffe docstring warnings found.")
        return 0

    print(f"Found {len(warnings)} griffe docstring warning(s):")
    for w in warnings:
        print(f"  {w}")

    return 1


if __name__ == "__main__":
    sys.exit(main())

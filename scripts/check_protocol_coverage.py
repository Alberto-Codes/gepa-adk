#!/usr/bin/env python3
"""Check that every @runtime_checkable Protocol in ports/ has a contract test.

Scans ``src/gepa_adk/ports/`` for ``@runtime_checkable`` Protocol definitions
and verifies that each has at least one corresponding contract test in
``tests/contracts/`` that imports the Protocol from ``gepa_adk.ports`` and
performs an ``isinstance`` check.

Exit codes:
    0 — all Protocols covered
    1 — one or more Protocols lack coverage
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PORTS_DIR = PROJECT_ROOT / "src" / "gepa_adk" / "ports"
CONTRACTS_DIR = PROJECT_ROOT / "tests" / "contracts"

# Pattern: @runtime_checkable on one line, class Name(Protocol): on the next
PROTOCOL_RE = re.compile(
    r"@runtime_checkable\s*\n\s*class\s+(\w+)\s*\(.*Protocol.*\)\s*:",
    re.MULTILINE,
)


def discover_protocols() -> dict[str, Path]:
    """Find all @runtime_checkable Protocols in ports/.

    Returns:
        Mapping of protocol name to source file path.
    """
    protocols: dict[str, Path] = {}
    for py_file in sorted(PORTS_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        text = py_file.read_text()
        for match in PROTOCOL_RE.finditer(text):
            protocols[match.group(1)] = py_file
    return protocols


def check_coverage(protocol_name: str) -> bool:
    """Check if a Protocol has a corresponding contract test.

    A Protocol is considered covered if any file in tests/contracts/ both
    imports the Protocol name from gepa_adk.ports (single or multi-line)
    and uses isinstance with it.

    Args:
        protocol_name: Name of the Protocol class to check.

    Returns:
        True if the Protocol has contract test coverage.
    """
    # Match both single-line and multi-line imports from gepa_adk.ports
    ports_import_pattern = re.compile(r"from\s+gepa_adk\.ports")
    name_pattern = re.compile(rf"\b{re.escape(protocol_name)}\b")
    isinstance_pattern = re.compile(rf"isinstance\s*\(.*\b{re.escape(protocol_name)}\b")

    for test_file in sorted(CONTRACTS_DIR.glob("*.py")):
        if test_file.name == "__init__.py":
            continue
        text = test_file.read_text()
        has_ports_import = ports_import_pattern.search(text)
        has_name = name_pattern.search(text)
        has_isinstance = isinstance_pattern.search(text)
        if has_ports_import and has_name and has_isinstance:
            return True
    return False


def main() -> int:
    """Run protocol coverage check."""
    print("Checking Protocol contract test coverage...")
    print()

    if not PORTS_DIR.is_dir():
        print(f"ERROR: ports directory not found: {PORTS_DIR}")
        return 1

    if not CONTRACTS_DIR.is_dir():
        print(f"ERROR: contracts directory not found: {CONTRACTS_DIR}")
        return 1

    protocols = discover_protocols()
    if not protocols:
        print("WARNING: No @runtime_checkable Protocols found in ports/")
        return 1

    covered: list[str] = []
    uncovered: list[tuple[str, Path]] = []

    for name, source in sorted(protocols.items()):
        if check_coverage(name):
            covered.append(name)
        else:
            uncovered.append((name, source))

    total = len(protocols)
    covered_count = len(covered)

    print(f"Protocols found: {total}")
    print(f"Covered:         {covered_count}")
    print(f"Uncovered:       {len(uncovered)}")
    print()

    if uncovered:
        print("UNCOVERED Protocols (missing contract test):")
        for name, source in uncovered:
            rel = source.relative_to(PROJECT_ROOT)
            print(f"  {name} ({rel})")
        print()
        print(f"FAILED: {len(uncovered)} Protocol(s) lack contract test coverage")
        return 1

    print(f"All {total} Protocols have contract test coverage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

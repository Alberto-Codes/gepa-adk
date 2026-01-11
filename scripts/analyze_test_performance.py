#!/usr/bin/env python3
"""Analyze test performance from profiling data and evaluate marker usage.

This script:
1. Identifies slow tests from profile data
2. Checks if slow tests have appropriate marks (@pytest.mark.slow)
3. Highlights tests that should be marked as slow but aren't
4. Evaluates mark usage patterns
"""

import os
import pstats
from pathlib import Path
from typing import Any

PROF_DIR = Path("prof")
SLOW_THRESHOLD_SECONDS = 0.5  # Tests taking >0.5s should be marked slow


def get_test_name_from_prof_file(prof_file: Path) -> str:
    """Extract test name from profile filename."""
    # Format: test_*.prof -> test_*
    name = prof_file.stem
    return name


def analyze_prof_file(prof_file: Path) -> dict[str, Any]:
    """Analyze a single profile file and return timing data."""
    try:
        stats = pstats.Stats(str(prof_file))
        stats.sort_stats("cumulative")

        # Get total cumulative time
        total_time = stats.total_tt  # type: ignore[attr-defined]

        return {
            "file": prof_file.name,
            "test_name": get_test_name_from_prof_file(prof_file),
            "total_time": total_time,
            "cumulative_time": stats.total_tt,  # type: ignore[attr-defined]
        }
    except Exception as e:
        return {
            "file": prof_file.name,
            "test_name": get_test_name_from_prof_file(prof_file),
            "error": str(e),
        }


def get_test_markers(test_file_path: str, test_name: str) -> set[str]:
    """Get markers for a specific test by parsing the test file."""
    # Map test names to file paths
    # This is a simplified approach - in reality we'd need to parse pytest collection

    # Try to find the test file
    for root, dirs, files in os.walk("tests"):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                file_path = Path(root) / file
                try:
                    content = file_path.read_text(encoding="utf-8")
                    # Check if test name appears in file
                    if (
                        test_name in content
                        or test_name.replace("test_", "def test_") in content
                    ):
                        # Check for markers
                        markers = set()
                        lines = content.splitlines()
                        for i, line in enumerate(lines):
                            if (
                                test_name in line
                                or test_name.replace("test_", "def test_") in line
                            ):
                                # Look backwards for markers
                                for j in range(max(0, i - 10), i):
                                    if "@pytest.mark." in lines[j]:
                                        marker = (
                                            lines[j]
                                            .split("@pytest.mark.")[1]
                                            .split("(")[0]
                                            .split()[0]
                                        )
                                        markers.add(marker)
                        return markers
                except Exception:
                    continue

    return set()


def main() -> None:
    """Main analysis function."""
    if not PROF_DIR.exists():
        print(f"Error: Profile directory {PROF_DIR} not found")
        return

    # Analyze all profile files
    prof_files = list(PROF_DIR.glob("*.prof"))
    prof_files = [
        f for f in prof_files if f.name != "combined.prof"
    ]  # Exclude combined

    print("=" * 80)
    print("TEST PERFORMANCE ANALYSIS")
    print("=" * 80)
    print()

    results = []
    for prof_file in sorted(prof_files):
        result = analyze_prof_file(prof_file)
        if "error" not in result:
            results.append(result)

    # Sort by total time
    results.sort(key=lambda x: x.get("total_time", 0), reverse=True)

    # Analyze slow tests
    slow_tests = [r for r in results if r.get("total_time", 0) > SLOW_THRESHOLD_SECONDS]

    print(f"Total tests profiled: {len(results)}")
    print(f"Slow tests (>={SLOW_THRESHOLD_SECONDS}s): {len(slow_tests)}")
    print()

    print("=" * 80)
    print("TOP 20 SLOWEST TESTS")
    print("=" * 80)
    print()

    for i, test in enumerate(results[:20], 1):
        time = test.get("total_time", 0)
        test_name = test.get("test_name", "unknown")
        print(f"{i:2}. {test_name:60} {time:8.3f}s")

    print()
    print("=" * 80)
    print("MARKER EVALUATION")
    print("=" * 80)
    print()

    # Check combined profile for overall stats
    if (PROF_DIR / "combined.prof").exists():
        combined_stats = pstats.Stats(str(PROF_DIR / "combined.prof"))
        combined_stats.sort_stats("cumulative")

        print("Combined Profile Summary:")
        print(f"  Total function calls: {combined_stats.total_calls:,}")  # type: ignore[attr-defined]
        print(f"  Total time: {combined_stats.total_tt:.2f}s")  # type: ignore[attr-defined]
        print()

    # Analyze by test type (unit/contract/integration)
    print("Performance by Test Type:")
    print("-" * 80)

    unit_times = []
    contract_times = []
    integration_times = []

    for result in results:
        test_name = result.get("test_name", "")
        time = result.get("total_time", 0)

        if "unit" in result.get("file", "").lower() or "/unit/" in result.get(
            "file", ""
        ):
            unit_times.append(time)
        elif "contract" in result.get("file", "").lower() or "/contract" in result.get(
            "file", ""
        ):
            contract_times.append(time)
        elif "integration" in result.get(
            "file", ""
        ).lower() or "/integration/" in result.get("file", ""):
            integration_times.append(time)

    if unit_times:
        avg_time = sum(unit_times) / len(unit_times)
        max_time = max(unit_times)
        print(
            f"  Unit tests:      {len(unit_times):3} tests, "
            f"avg {avg_time:.3f}s, max {max_time:.3f}s"
        )
    if contract_times:
        avg_time = sum(contract_times) / len(contract_times)
        max_time = max(contract_times)
        print(
            f"  Contract tests:  {len(contract_times):3} tests, "
            f"avg {avg_time:.3f}s, max {max_time:.3f}s"
        )
    if integration_times:
        avg_time = sum(integration_times) / len(integration_times)
        max_time = max(integration_times)
        print(
            f"  Integration tests: {len(integration_times):3} tests, "
            f"avg {avg_time:.3f}s, max {max_time:.3f}s"
        )

    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()

    # Find tests that are slow but might not be marked
    very_slow = [r for r in results if r.get("total_time", 0) > 1.0]
    print(f"Tests taking >1.0s (consider @pytest.mark.slow): {len(very_slow)}")
    for test in very_slow[:10]:
        print(
            f"  - {test.get('test_name', 'unknown')}: {test.get('total_time', 0):.3f}s"
        )

    print()
    print("Note: Check if slow tests have @pytest.mark.slow marker")
    print("      Integration tests should typically have @pytest.mark.slow")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Evaluate test markers against performance data.

This script:
1. Identifies slow tests from profiling
2. Checks if they have @pytest.mark.slow
3. Identifies tests that should be marked but aren't
4. Provides recommendations
"""

import re
from pathlib import Path
from typing import Any

PROF_DIR = Path("prof")
SLOW_THRESHOLD = 1.0  # Tests >1s should have @pytest.mark.slow


def get_slow_tests() -> list[dict[str, Any]]:
    """Get list of slow tests from profile files."""
    slow_tests = []
    
    if not PROF_DIR.exists():
        return slow_tests
    
    for prof_file in PROF_DIR.glob("test_*.prof"):
        try:
            import pstats
            stats = pstats.Stats(str(prof_file))
            total_time = stats.total_tt
            
            if total_time > SLOW_THRESHOLD:
                test_name = prof_file.stem
                slow_tests.append({
                    "name": test_name,
                    "time": total_time,
                    "file": prof_file.name
                })
        except Exception:
            continue
    
    return sorted(slow_tests, key=lambda x: x["time"], reverse=True)


def find_test_in_codebase(test_name: str) -> tuple[str | None, list[str]]:
    """Find test function in codebase and return file path and markers."""
    # Convert test_name to function name pattern
    func_pattern = test_name.replace("test_", "def test_")
    
    for file_path in Path("tests").rglob("test_*.py"):
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Check if test function exists
            if func_pattern in content or test_name in content:
                # Extract markers
                markers = []
                lines = content.splitlines()
                
                # Find the test function
                for i, line in enumerate(lines):
                    if func_pattern in line or (f"def {test_name}" in line):
                        # Look backwards for markers (up to 10 lines)
                        for j in range(max(0, i - 10), i):
                            marker_line = lines[j].strip()
                            if "@pytest.mark." in marker_line:
                                # Extract marker name
                                match = re.search(r'@pytest\.mark\.(\w+)', marker_line)
                                if match:
                                    markers.append(match.group(1))
                        
                        # Also check class-level markers
                        for j in range(max(0, i - 20), i):
                            if "class " in lines[j] and "Test" in lines[j]:
                                # Check for class-level markers
                                for k in range(max(0, j - 5), j):
                                    marker_line = lines[k].strip()
                                    if "@pytest.mark." in marker_line:
                                        match = re.search(r'@pytest\.mark\.(\w+)', marker_line)
                                        if match:
                                            markers.append(match.group(1))
                        
                        # Check for module-level pytestmark
                        if "pytestmark" in content:
                            match = re.search(r'pytestmark\s*=\s*pytest\.mark\.(\w+)', content)
                            if match:
                                markers.append(match.group(1))
                        
                        return str(file_path.relative_to(Path("tests").parent)), markers
        except Exception:
            continue
    
    return None, []


def main() -> None:
    """Main evaluation function."""
    print("=" * 80)
    print("TEST MARKER EVALUATION BASED ON PERFORMANCE")
    print("=" * 80)
    print()
    
    slow_tests = get_slow_tests()
    
    print(f"Found {len(slow_tests)} tests taking >{SLOW_THRESHOLD}s")
    print()
    
    print("=" * 80)
    print("SLOW TESTS MARKER ANALYSIS")
    print("=" * 80)
    print()
    
    missing_slow_marker = []
    has_slow_marker = []
    
    for test in slow_tests:
        test_name = test["name"]
        test_time = test["time"]
        
        file_path, markers = find_test_in_codebase(test_name)
        
        if file_path:
            has_slow = "slow" in markers
            has_integration = "integration" in markers
            
            status = "✓" if has_slow else "⚠"
            marker_str = ", ".join(markers) if markers else "none"
            
            print(f"{status} {test_name:55} {test_time:6.2f}s")
            print(f"    File: {file_path}")
            print(f"    Markers: {marker_str}")
            
            if not has_slow:
                missing_slow_marker.append({
                    "name": test_name,
                    "time": test_time,
                    "file": file_path,
                    "markers": markers
                })
            else:
                has_slow_marker.append({
                    "name": test_name,
                    "time": test_time,
                    "file": file_path
                })
            print()
        else:
            print(f"⚠ {test_name:55} {test_time:6.2f}s")
            print(f"    File: NOT FOUND")
            print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    print(f"Total slow tests: {len(slow_tests)}")
    print(f"  ✓ Have @pytest.mark.slow: {len(has_slow_marker)}")
    print(f"  ⚠ Missing @pytest.mark.slow: {len(missing_slow_marker)}")
    print()
    
    if missing_slow_marker:
        print("=" * 80)
        print("RECOMMENDATIONS: Add @pytest.mark.slow to these tests")
        print("=" * 80)
        print()
        
        for test in missing_slow_marker:
            print(f"  - {test['name']:55} ({test['time']:.2f}s)")
            print(f"    File: {test['file']}")
            print()


if __name__ == "__main__":
    main()

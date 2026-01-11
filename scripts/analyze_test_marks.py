#!/usr/bin/env python3
"""Analyze pytest marker usage across all test files.

This script identifies:
- Tests with marks vs without marks
- Distribution of marks by test type (unit/contract/integration)
- Tests that should have marks but don't
- Inconsistent mark usage
"""

import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict

# Marker patterns
MARK_PATTERN = re.compile(r"@pytest\.mark\.(\w+)")
MARKERS = ["unit", "contract", "integration", "slow", "api", "requires_ollama", "requires_gemini"]


def get_all_tests() -> list[str]:
    """Get all test node IDs from pytest."""
    result = subprocess.run(
        ["uv", "run", "pytest", "--co", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    tests = []
    for line in result.stdout.splitlines():
        if "::test_" in line:
            tests.append(line.strip())
    return tests


def analyze_file(file_path: Path) -> dict:
    """Analyze a single test file for marker usage."""
    content = file_path.read_text(encoding="utf-8")
    
    # Find all marks in the file
    marks_found = set(MARK_PATTERN.findall(content))
    
    # Find test functions
    test_functions = re.findall(r"^\s*(?:async\s+)?def\s+(test_\w+)", content, re.MULTILINE)
    test_classes = re.findall(r"^class\s+(Test\w+)", content, re.MULTILINE)
    
    # Check if marks are at class level or function level
    class_marks = set()
    function_marks: DefaultDict[str, set] = defaultdict(set)
    
    lines = content.splitlines()
    current_class = None
    for i, line in enumerate(lines):
        # Check for class definition
        class_match = re.match(r"^class\s+(Test\w+)", line)
        if class_match:
            current_class = class_match.group(1)
            # Check if class has marks
            if i > 0:
                prev_line = lines[i - 1].strip()
                if prev_line.startswith("@pytest.mark."):
                    mark_match = MARK_PATTERN.search(prev_line)
                    if mark_match:
                        class_marks.add(mark_match.group(1))
        
        # Check for function definition
        func_match = re.match(r"^\s*(?:async\s+)?def\s+(test_\w+)", line)
        if func_match:
            func_name = func_match.group(1)
            # Check previous lines for marks
            for j in range(max(0, i - 5), i):
                prev_line = lines[j].strip()
                if prev_line.startswith("@pytest.mark."):
                    mark_match = MARK_PATTERN.search(prev_line)
                    if mark_match:
                        function_marks[func_name].add(mark_match.group(1))
    
    return {
        "file": str(file_path),
        "marks_found": marks_found,
        "test_functions": test_functions,
        "test_classes": test_classes,
        "class_marks": class_marks,
        "function_marks": dict(function_marks),
    }


def infer_test_type(file_path: Path) -> str | None:
    """Infer expected test type from file path."""
    path_str = str(file_path)
    if "/unit/" in path_str or "\\unit\\" in path_str:
        return "unit"
    elif "/contracts/" in path_str or "\\contracts\\" in path_str:
        return "contract"
    elif "/integration/" in path_str or "\\integration\\" in path_str:
        return "integration"
    return None


def main() -> None:
    """Main analysis function."""
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"
    
    # Analyze all test files
    test_files = list(tests_dir.rglob("test_*.py"))
    
    results = []
    for test_file in sorted(test_files):
        result = analyze_file(test_file)
        result["expected_type"] = infer_test_type(test_file)
        results.append(result)
    
    # Statistics
    stats = {
        "total_files": len(results),
        "files_with_marks": 0,
        "files_without_marks": 0,
        "mark_distribution": defaultdict(int),
        "missing_marks": defaultdict(list),
        "inconsistent_marks": [],
    }
    
    print("=" * 80)
    print("PYTEST MARKER ANALYSIS")
    print("=" * 80)
    print()
    
    for result in results:
        file_path = Path(result["file"])
        relative_path = file_path.relative_to(project_root)
        
        marks = result["marks_found"]
        expected_type = result["expected_type"]
        
        if marks:
            stats["files_with_marks"] += 1
            for mark in marks:
                stats["mark_distribution"][mark] += 1
        else:
            stats["files_without_marks"] += 1
        
        # Check for missing marks
        if expected_type and expected_type not in marks:
            # Check if any marks are present
            if not marks or not any(m in MARKERS for m in marks):
                stats["missing_marks"][expected_type].append(str(relative_path))
        
        # Check for inconsistent usage
        if expected_type == "contract" and "contract" not in marks:
            if result["test_functions"] or result["test_classes"]:
                stats["inconsistent_marks"].append((str(relative_path), "contract"))
        elif expected_type == "unit" and "unit" not in marks:
            if result["test_functions"] or result["test_classes"]:
                stats["inconsistent_marks"].append((str(relative_path), "unit"))
        elif expected_type == "integration" and "integration" not in marks:
            if result["test_functions"] or result["test_classes"]:
                stats["inconsistent_marks"].append((str(relative_path), "integration"))
    
    # Print summary
    print("SUMMARY")
    print("-" * 80)
    print(f"Total test files: {stats['total_files']}")
    print(f"Files with marks: {stats['files_with_marks']}")
    print(f"Files without marks: {stats['files_without_marks']}")
    print()
    
    print("MARK DISTRIBUTION")
    print("-" * 80)
    for mark in MARKERS:
        count = stats["mark_distribution"].get(mark, 0)
        print(f"  {mark:20} {count:3} files")
    print()
    
    print("FILES MISSING EXPECTED MARKS")
    print("-" * 80)
    for test_type, files in stats["missing_marks"].items():
        print(f"\n{test_type.upper()} tests missing @pytest.mark.{test_type}:")
        for file in files:
            print(f"  - {file}")
    
    if not stats["missing_marks"]:
        print("  None found!")
    print()
    
    print("INCONSISTENT MARK USAGE")
    print("-" * 80)
    if stats["inconsistent_marks"]:
        for file, expected_mark in stats["inconsistent_marks"]:
            print(f"  {file} - expected @pytest.mark.{expected_mark}")
    else:
        print("  None found!")
    print()
    
    # Detailed file-by-file analysis
    print("=" * 80)
    print("DETAILED FILE ANALYSIS")
    print("=" * 80)
    print()
    
    for result in results:
        file_path = Path(result["file"])
        relative_path = file_path.relative_to(project_root)
        marks = result["marks_found"]
        expected_type = result["expected_type"]
        
        status = "✓" if (expected_type and expected_type in marks) or (not expected_type and marks) else "⚠"
        
        print(f"{status} {relative_path}")
        if marks:
            print(f"    Marks: {', '.join(sorted(marks))}")
        else:
            print(f"    Marks: NONE")
        if expected_type:
            print(f"    Expected: {expected_type}")
        if result["test_functions"]:
            print(f"    Test functions: {len(result['test_functions'])}")
        if result["test_classes"]:
            print(f"    Test classes: {len(result['test_classes'])}")
        print()


if __name__ == "__main__":
    main()

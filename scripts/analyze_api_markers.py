#!/usr/bin/env python3
"""Analyze API marker usage in integration tests.

Checks if tests that make real API calls have appropriate markers:
- @pytest.mark.api for any real API calls
- @pytest.mark.requires_gemini for Gemini API calls
- @pytest.mark.requires_ollama for Ollama calls
"""

import re
from pathlib import Path
from typing import Any


def find_api_calls_in_file(file_path: Path) -> dict[str, Any]:
    """Analyze a test file for API calls and markers."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return {}

    result = {
        "file": str(file_path.relative_to(Path("tests").parent)),
        "has_api_marker": False,
        "has_gemini_marker": False,
        "has_ollama_marker": False,
        "uses_gemini": False,
        "uses_ollama": False,
        "uses_real_agent": False,
        "test_functions": [],
    }

    # Check for markers (support both single and list format)
    api_patterns = [
        r"@pytest\.mark\.api",
        r"pytestmark\s*=\s*pytest\.mark\.api",
        r"pytestmark\s*=\s*\[.*pytest\.mark\.api",
    ]
    for pattern in api_patterns:
        if re.search(pattern, content):
            result["has_api_marker"] = True
            break

    gemini_patterns = [
        r"@pytest\.mark\.requires_gemini",
        r"pytestmark\s*=\s*\[.*pytest\.mark\.requires_gemini",
    ]
    for pattern in gemini_patterns:
        if re.search(pattern, content):
            result["has_gemini_marker"] = True
            break

    ollama_patterns = [
        r"@pytest\.mark\.requires_ollama",
        r"pytestmark\s*=\s*\[.*pytest\.mark\.requires_ollama",
    ]
    for pattern in ollama_patterns:
        if re.search(pattern, content):
            result["has_ollama_marker"] = True
            break

    # Check for Gemini usage
    gemini_patterns = [
        r"gemini-2\.0-flash",
        r"gemini-2\.5-flash",
        r"gemini/gemini",
        r'model=["\']gemini',
    ]
    for pattern in gemini_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            result["uses_gemini"] = True
            break

    # Check for Ollama usage
    ollama_patterns = [
        r"ollama/",
        r"OLLAMA_API_BASE",
    ]
    for pattern in ollama_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            result["uses_ollama"] = True
            break

    # Check for real ADK agents (these make API calls)
    if "LlmAgent(" in content or "SequentialAgent(" in content:
        result["uses_real_agent"] = True

    # Find test functions
    test_funcs = re.findall(r"def (test_\w+)", content)
    result["test_functions"] = test_funcs

    return result


def main() -> None:
    """Main analysis function."""
    print("=" * 80)
    print("API MARKER USAGE ANALYSIS")
    print("=" * 80)
    print()

    integration_files = list(Path("tests/integration").rglob("test_*.py"))

    issues = []
    correct = []

    for file_path in sorted(integration_files):
        analysis = find_api_calls_in_file(file_path)

        if not analysis:
            continue

        # Determine if this file makes API calls
        makes_api_calls = (
            analysis["uses_gemini"]
            or analysis["uses_ollama"]
            or analysis["uses_real_agent"]
        )

        if not makes_api_calls:
            continue  # Skip files that don't make API calls

        # Check for issues
        file_issues = []

        if makes_api_calls and not analysis["has_api_marker"]:
            file_issues.append("Missing @pytest.mark.api")

        if analysis["uses_gemini"] and not analysis["has_gemini_marker"]:
            file_issues.append("Missing @pytest.mark.requires_gemini")

        if analysis["uses_ollama"] and not analysis["has_ollama_marker"]:
            file_issues.append("Missing @pytest.mark.requires_ollama")

        if file_issues:
            issues.append(
                {
                    "file": analysis["file"],
                    "issues": file_issues,
                    "uses_gemini": analysis["uses_gemini"],
                    "uses_ollama": analysis["uses_ollama"],
                    "uses_real_agent": analysis["uses_real_agent"],
                }
            )
        else:
            correct.append(analysis["file"])

    print("FILES WITH ISSUES:")
    print("-" * 80)

    if issues:
        for item in issues:
            print(f"\n⚠ {item['file']}")
            for issue in item["issues"]:
                print(f"    - {issue}")
            if item["uses_gemini"]:
                print("    Uses: Gemini API")
            if item["uses_ollama"]:
                print("    Uses: Ollama")
            if item["uses_real_agent"]:
                print("    Uses: Real ADK agents (makes API calls)")
    else:
        print("  None found!")

    print()
    print("=" * 80)
    print("CORRECTLY MARKED FILES:")
    print("-" * 80)

    if correct:
        for file in correct:
            print(f"  ✓ {file}")
    else:
        print("  None found!")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("-" * 80)
    print(f"Total integration files analyzed: {len(integration_files)}")
    print(f"Files making API calls: {len(issues) + len(correct)}")
    print(f"  ✓ Correctly marked: {len(correct)}")
    print(f"  ⚠ Needs fixes: {len(issues)}")
    print()


if __name__ == "__main__":
    main()

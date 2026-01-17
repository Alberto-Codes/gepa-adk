#!/bin/bash
# Code Quality Check and Remediation Script
#
# Runs comprehensive code quality checks on Python files:
# 1. Linting with ruff (includes import sorting via extend-select)
# 2. Formatting with ruff format
# 3. Docstring freshness (staleness detection via git blame)
# 4. Docstring enrichment (missing sections audit)
# 5. Docs coverage (missing __init__.py detection)
# 6. Type checking with ty
#
# IMPORTANT: Scope of Remediation
# ===============================
# When checking unstaged files (default mode), ALL files in the git diff are
# considered in scope for remediation. This means:
# - If a file appears in the diff, the ENTIRE file is in scope, not just the
#   changed lines
# - If tools report issues in parts of the file that weren't directly modified,
#   those issues should still be remediated
# - Remediation should follow project code practices, patterns, ADRs, and
#   overall best practices
# - The goal is to ensure all touched files meet quality standards, not just
#   the specific lines that were changed
#
# Usage:
#   ./scripts/code_quality_check.sh                    # Check unstaged .py files
#   ./scripts/code_quality_check.sh --all               # Check all .py files
#   ./scripts/code_quality_check.sh --files file1.py file2.py  # Check specific files
#   ./scripts/code_quality_check.sh --no-type-check     # Skip type checking
#   ./scripts/code_quality_check.sh --no-docstring-checks  # Skip freshness/enrichment
#   ./scripts/code_quality_check.sh --verbose           # Show detailed output

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Default options
CHECK_ALL=false
SKIP_TYPE_CHECK=false
SKIP_DOCSTRING_CHECKS=false
VERBOSE=false
SPECIFIC_FILES=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            CHECK_ALL=true
            shift
            ;;
        --no-type-check)
            SKIP_TYPE_CHECK=true
            shift
            ;;
        --no-docstring-checks)
            SKIP_DOCSTRING_CHECKS=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --files)
            shift
            while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do
                SPECIFIC_FILES+=("$1")
                shift
            done
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Usage: $0 [--all] [--files FILE1 FILE2 ...] [--no-type-check] [--no-docstring-checks] [--verbose]" >&2
            exit 1
            ;;
    esac
done

# Find Python files to check
if [[ ${#SPECIFIC_FILES[@]} -gt 0 ]]; then
    # Check specific files provided
    FILES=()
    for file in "${SPECIFIC_FILES[@]}"; do
        if [[ -f "$file" && "$file" =~ \.py$ ]]; then
            FILES+=("$file")
        elif [[ ! "$file" =~ \.py$ ]]; then
            echo "Warning: Skipping non-Python file: $file" >&2
        else
            echo "Warning: File not found: $file" >&2
        fi
    done
elif [[ "$CHECK_ALL" == true ]]; then
    # Check all Python files in the project
    FILES=($(find . -name "*.py" -type f ! -path "./.venv/*" ! -path "./.git/*" ! -path "*/__pycache__/*" | sort))
else
    # Check only unstaged Python files
    # NOTE: All files in the diff are in scope for remediation, not just changed lines
    # If a file appears in the diff, the entire file should meet quality standards
    FILES=($((git diff --name-only --diff-filter=ACMR; git ls-files --others --exclude-standard) | grep -E '\.py$' | sort -u))
fi

# Check if any files found
if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "No Python files to check."
    exit 0
fi

# Output file list
echo "Found ${#FILES[@]} Python file(s) to check:"
for file in "${FILES[@]}"; do
    echo "  - $file"
done
if [[ "$CHECK_ALL" == false && ${#SPECIFIC_FILES[@]} -eq 0 ]]; then
    echo ""
    echo "Note: All files in the diff are in scope for remediation (entire files, not just changed lines)."
    echo "      Issues found anywhere in these files should be fixed per project standards."
fi
echo ""

# Counters for summary (initialize as integers)
LINT_FIXES=0
FORMAT_FIXES=0
FRESHNESS_ISSUES=0
ENRICHMENT_ISSUES=0
DOCS_COVERAGE_ISSUES=0
GRIFFE_ISSUES=0
TYPE_ERRORS=0

# Filter to only src/ files for docstring checks (skip tests/ and scripts/)
SRC_FILES=()
for file in "${FILES[@]}"; do
    if [[ "$file" == src/* ]] || [[ "$file" == ./src/* ]]; then
        SRC_FILES+=("$file")
    fi
done

# Step 1: Linting and Auto-Fix (includes import sorting via extend-select)
echo "[1/7] Linting (includes imports + docstring style)..."
if [[ "$VERBOSE" == true ]]; then
    if printf '%s\0' "${FILES[@]}" | xargs -0 uv run ruff check --fix 2>&1 | tee /tmp/lint_output.txt; then
        LINT_FIXES=$(grep -oP '\d+(?= fixed)' /tmp/lint_output.txt 2>/dev/null | head -1 || echo "0")
        echo "✓ Linting complete"
    else
        echo "⚠ Linting had issues (some may require manual fix)"
    fi
else
    if OUTPUT=$(printf '%s\0' "${FILES[@]}" | xargs -0 uv run ruff check --fix 2>&1); then
        if echo "$OUTPUT" | grep -q "fixed"; then
            LINT_FIXES=$(echo "$OUTPUT" | grep -oP '\d+(?= fixed)' | head -1 | tr -d '\n' || echo "0")
            LINT_FIXES=${LINT_FIXES:-0}
            echo "✓ Fixed $LINT_FIXES issue(s)"
        else
            echo "✓ All checks passed"
        fi
    else
        # Ruff exits non-zero if unfixable issues remain
        LINT_FIXES=$(echo "$OUTPUT" | grep -oP '\d+(?= fixed)' | head -1 | tr -d '\n' || echo "0")
        LINT_FIXES=${LINT_FIXES:-0}
        if [[ $LINT_FIXES -gt 0 ]]; then
            echo "✓ Fixed $LINT_FIXES issue(s), some issues remain (manual fix required)"
        else
            echo "⚠ Linting issues found (manual fix required)"
        fi
        if [[ "$VERBOSE" == false ]]; then
            echo "$OUTPUT" | head -20
        fi
    fi
fi

# Step 2: Formatting
echo "[2/7] Formatting..."
if OUTPUT=$(printf '%s\0' "${FILES[@]}" | xargs -0 uv run ruff format 2>&1); then
    FORMAT_FIXES=$(echo "$OUTPUT" | grep -oP '\d+(?= files? reformatted)' | head -1 || echo "0")
    FORMAT_FIXES=${FORMAT_FIXES:-0}
    if [[ "$FORMAT_FIXES" -gt 0 ]]; then
        echo "✓ Reformatted $FORMAT_FIXES file(s)"
    else
        echo "✓ No formatting changes needed"
    fi
else
    echo "⚠ Formatting had issues"
fi

# Step 3: Docstring Freshness (staleness detection)
if [[ "$SKIP_DOCSTRING_CHECKS" == false && ${#SRC_FILES[@]} -gt 0 ]]; then
    echo "[3/7] Docstring freshness..."
    FRESHNESS_SCRIPT="$SCRIPT_DIR/docstring_freshness.py"
    if [[ -f "$FRESHNESS_SCRIPT" ]]; then
        if OUTPUT=$(python "$FRESHNESS_SCRIPT" --drift-threshold 30 --age-threshold 90 --limit 0 --files "${SRC_FILES[@]}" 2>&1); then
            if echo "$OUTPUT" | grep -q "No stale docstrings"; then
                echo "✓ All docstrings fresh"
            else
                # Count stale items from summary line
                FRESHNESS_ISSUES=$(echo "$OUTPUT" | grep -oP '(?<=found )\d+(?= stale)' | head -1 || echo "0")
                FRESHNESS_ISSUES=${FRESHNESS_ISSUES:-0}
                if [[ $FRESHNESS_ISSUES -gt 0 ]]; then
                    echo "⚠ Found $FRESHNESS_ISSUES stale docstring(s):"
                    # Show all stale items (file:line for each)
                    echo "$OUTPUT" | grep -E "^\| \`" | sed 's/^|/  /'
                    if [[ "$VERBOSE" == true ]]; then
                        echo ""
                        echo "$OUTPUT"
                    fi
                else
                    echo "✓ All docstrings fresh"
                fi
            fi
        else
            echo "⚠ Freshness check had issues"
        fi
    else
        echo "⚠ Freshness script not found, skipping"
    fi
else
    echo "[3/7] Docstring freshness... (skipped)"
fi

# Step 4: Docstring Enrichment (missing sections audit)
if [[ "$SKIP_DOCSTRING_CHECKS" == false && ${#SRC_FILES[@]} -gt 0 ]]; then
    echo "[4/7] Docstring enrichment..."
    ENRICHMENT_SCRIPT="$SCRIPT_DIR/docstring_enrichment.py"
    if [[ -f "$ENRICHMENT_SCRIPT" ]]; then
        if OUTPUT=$(python "$ENRICHMENT_SCRIPT" --limit 0 --files "${SRC_FILES[@]}" 2>&1); then
            if echo "$OUTPUT" | grep -q "No enrichment opportunities"; then
                echo "✓ All docstrings complete"
            else
                # Count opportunities from output
                ENRICHMENT_ISSUES=$(echo "$OUTPUT" | grep -oP '\*\*Total enrichment opportunities\*\*: \d+' | grep -oP '\d+' || echo "0")
                ENRICHMENT_ISSUES=${ENRICHMENT_ISSUES:-0}
                if [[ $ENRICHMENT_ISSUES -gt 0 ]]; then
                    echo "⚠ Found $ENRICHMENT_ISSUES enrichment opportunity(s):"
                    # Show all enrichment items (file:line for each)
                    echo "$OUTPUT" | grep -E "^\| \`" | sed 's/^|/  /'
                    if [[ "$VERBOSE" == true ]]; then
                        echo ""
                        echo "$OUTPUT"
                    fi
                else
                    echo "✓ All docstrings complete"
                fi
            fi
        else
            echo "⚠ Enrichment check had issues"
        fi
    else
        echo "⚠ Enrichment script not found, skipping"
    fi
else
    echo "[4/7] Docstring enrichment... (skipped)"
fi

# Step 5: Docs Coverage (missing __init__.py detection)
if [[ "$SKIP_DOCSTRING_CHECKS" == false && ${#SRC_FILES[@]} -gt 0 ]]; then
    echo "[5/7] Docs coverage..."
    COVERAGE_SCRIPT="$SCRIPT_DIR/docstring_docs_coverage.py"
    if [[ -f "$COVERAGE_SCRIPT" ]]; then
        if OUTPUT=$(python "$COVERAGE_SCRIPT" --files "${SRC_FILES[@]}" 2>&1); then
            if echo "$OUTPUT" | grep -q "No docs coverage issues"; then
                echo "✓ All files included in docs"
            else
                # Count issues from output
                DOCS_COVERAGE_ISSUES=$(echo "$OUTPUT" | grep -oP '(?<=Found )\d+(?= file)' | head -1 || echo "0")
                DOCS_COVERAGE_ISSUES=${DOCS_COVERAGE_ISSUES:-0}
                if [[ $DOCS_COVERAGE_ISSUES -gt 0 ]]; then
                    echo "⚠ Found $DOCS_COVERAGE_ISSUES file(s) excluded from docs:"
                    # Show all issues (file and missing init)
                    echo "$OUTPUT" | grep -E "^\| \`" | sed 's/^|/  /'
                    if [[ "$VERBOSE" == true ]]; then
                        echo ""
                        echo "$OUTPUT"
                    fi
                else
                    echo "✓ All files included in docs"
                fi
            fi
        else
            echo "⚠ Coverage check had issues"
        fi
    else
        echo "⚠ Coverage script not found, skipping"
    fi
else
    echo "[5/7] Docs coverage... (skipped)"
fi

# Step 6: Griffe Docstring Warnings (missing parameter types in docstrings)
if [[ "$SKIP_DOCSTRING_CHECKS" == false && ${#SRC_FILES[@]} -gt 0 ]]; then
    echo "[6/7] Griffe docstring warnings..."
    GRIFFE_SCRIPT="$SCRIPT_DIR/docstring_griffe_check.py"
    if [[ -f "$GRIFFE_SCRIPT" ]]; then
        if OUTPUT=$(uv run python "$GRIFFE_SCRIPT" --files "${SRC_FILES[@]}" 2>&1); then
            echo "✓ No griffe warnings"
        else
            # Count warnings from output
            GRIFFE_ISSUES=$(echo "$OUTPUT" | grep -oP '(?<=Found )\d+(?= griffe)' | head -1 || echo "0")
            GRIFFE_ISSUES=${GRIFFE_ISSUES:-0}
            if [[ $GRIFFE_ISSUES -gt 0 ]]; then
                echo "⚠ Found $GRIFFE_ISSUES griffe docstring warning(s):"
                echo "$OUTPUT" | grep -E "^  " | head -10
                if [[ "$VERBOSE" == true ]]; then
                    echo ""
                    echo "$OUTPUT"
                fi
            else
                echo "✓ No griffe warnings"
            fi
        fi
    else
        echo "⚠ Griffe script not found, skipping"
    fi
else
    echo "[6/7] Griffe docstring warnings... (skipped)"
fi

# Step 7: Type Checking
if [[ "$SKIP_TYPE_CHECK" == false ]]; then
    echo "[7/7] Type checking..."
    if [[ "$VERBOSE" == true ]]; then
        if printf '%s\0' "${FILES[@]}" | xargs -0 uv run ty check 2>&1; then
            echo "✓ All type checks passed"
        else
            TYPE_ERRORS=1
            echo "⚠ Type checking found issues"
        fi
    else
        if OUTPUT=$(printf '%s\0' "${FILES[@]}" | xargs -0 uv run ty check 2>&1); then
            echo "✓ All type checks passed"
        else
            TYPE_ERRORS=1
            echo "⚠ Type checking found issues"
            echo "$OUTPUT" | head -20
        fi
    fi
else
    echo "[7/7] Type checking... (skipped)"
fi

# Summary
echo ""
echo "Summary:"
echo "- Files processed: ${#FILES[@]}"
# Ensure all variables are clean integers
LINT_FIXES=$(echo "${LINT_FIXES:-0}" | tr -d '[:space:]')
FORMAT_FIXES=$(echo "${FORMAT_FIXES:-0}" | tr -d '[:space:]')
FRESHNESS_ISSUES=$(echo "${FRESHNESS_ISSUES:-0}" | tr -d '[:space:]')
ENRICHMENT_ISSUES=$(echo "${ENRICHMENT_ISSUES:-0}" | tr -d '[:space:]')
DOCS_COVERAGE_ISSUES=$(echo "${DOCS_COVERAGE_ISSUES:-0}" | tr -d '[:space:]')
GRIFFE_ISSUES=$(echo "${GRIFFE_ISSUES:-0}" | tr -d '[:space:]')
TYPE_ERRORS=$(echo "${TYPE_ERRORS:-0}" | tr -d '[:space:]')

if [[ $LINT_FIXES -gt 0 ]]; then
    echo "- Linting: Fixed $LINT_FIXES issue(s)"
fi
if [[ $FORMAT_FIXES -gt 0 ]]; then
    echo "- Formatting: Reformatted $FORMAT_FIXES file(s)"
fi
if [[ $FRESHNESS_ISSUES -gt 0 ]]; then
    echo "- Docstring freshness: $FRESHNESS_ISSUES stale (review recommended)"
fi
if [[ $ENRICHMENT_ISSUES -gt 0 ]]; then
    echo "- Docstring enrichment: $ENRICHMENT_ISSUES opportunities"
fi
if [[ $DOCS_COVERAGE_ISSUES -gt 0 ]]; then
    echo "- Docs coverage: $DOCS_COVERAGE_ISSUES file(s) excluded (missing __init__.py)"
fi
if [[ $GRIFFE_ISSUES -gt 0 ]]; then
    echo "- Griffe warnings: $GRIFFE_ISSUES (missing param types in docstrings)"
fi
if [[ $TYPE_ERRORS -gt 0 ]]; then
    echo "- Type errors: Found (see output above)"
fi

# Show reference docs if there are docstring issues
if [[ $FRESHNESS_ISSUES -gt 0 || $ENRICHMENT_ISSUES -gt 0 || $DOCS_COVERAGE_ISSUES -gt 0 || $GRIFFE_ISSUES -gt 0 ]]; then
    echo ""
    echo "Reference:"
    echo "  - ADR: docs/adr/ADR-017-DOCSTRING-QUALITY.md"
    echo "  - Templates: docs/contributing/docstring-templates.md"
fi

# Exit status - type errors, docs coverage, and griffe issues block; others are advisory
if [[ $TYPE_ERRORS -gt 0 ]]; then
    echo ""
    echo "Status: ⚠ Type errors require attention"
    exit 1
elif [[ $DOCS_COVERAGE_ISSUES -gt 0 ]]; then
    echo ""
    echo "Status: ⚠ Docs coverage issues require attention (add missing __init__.py)"
    exit 1
elif [[ $GRIFFE_ISSUES -gt 0 ]]; then
    echo ""
    echo "Status: ⚠ Griffe warnings require attention (add types to docstring params)"
    exit 1
elif [[ $FRESHNESS_ISSUES -gt 0 || $ENRICHMENT_ISSUES -gt 0 ]]; then
    echo ""
    echo "Status: ✓ Ready (docstring improvements available)"
    exit 0
else
    echo ""
    echo "Status: ✓ Ready"
    exit 0
fi


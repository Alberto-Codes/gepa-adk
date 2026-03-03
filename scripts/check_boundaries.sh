#!/bin/bash
# Hexagonal Architecture Boundary Enforcement
#
# Verifies import layer boundaries defined in ADR-000:
#   domain/   → stdlib only (exception: structlog)
#   ports/    → domain + stdlib
#   adapters/ → ports + domain + external libs (ADK, LiteLLM)
#   engine/   → ports + domain + structlog (may import adapter defaults)
#   utils/    → stdlib + structlog
#
# Checks performed:
#   1. No google.*/litellm imports outside adapters/  (AC 1)
#   2. No adapter imports in domain/ or ports/         (AC 2)
#   3. No engine imports in domain/, ports/, adapters/ (AC 3)
#   4. TYPE_CHECKING-guarded imports are excluded       (AC 4)
#
# Note: structlog is allowed in domain/, engine/, utils/ per ADR-000.
# Since checks target google.* and litellm specifically, structlog is
# naturally excluded from violation detection.
#
# Usage: ./scripts/check_boundaries.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$PROJECT_ROOT/src/gepa_adk"

VIOLATIONS=0

# Check if a line is inside a triple-quoted docstring.
# Counts """ occurrences from file start to line_num-1; odd count = inside string.
# This prevents false positives from code examples in docstring Examples: sections.
is_inside_docstring() {
    local file="$1"
    local line_num="$2"

    if (( line_num <= 1 )); then
        return 1  # first line cannot be inside a docstring
    fi

    local count
    count=$(head -n "$((line_num - 1))" "$file" | grep -o '"""' | wc -l)
    count=${count:-0}

    # Odd count means we're inside a triple-quoted string
    if (( count % 2 == 1 )); then
        return 0  # inside docstring
    fi
    return 1  # not inside docstring
}

# Check if an import line is guarded by TYPE_CHECKING (within 3 lines above).
# Catches the common pattern:
#   if TYPE_CHECKING:
#       from google.adk.agents import LlmAgent  # type-only, not runtime
is_type_checking_guarded() {
    local file="$1"
    local line_num="$2"

    local start=$((line_num - 3))
    if (( start < 1 )); then
        start=1
    fi

    local end=$((line_num - 1))
    if (( end < start )); then
        return 1  # line 1 cannot have anything above it
    fi

    if sed -n "${start},${end}p" "$file" | grep -qE '(if TYPE_CHECKING:|if typing\.TYPE_CHECKING:)'; then
        return 0  # guarded — skip this import
    fi
    return 1  # not guarded — real violation
}

# Scan directories for imports matching a pattern, report violations.
# Note: commented imports (# from ...) are naturally excluded because '#'
# does not match the (from|import) token at the start of the grep pattern.
# Triple-single-quote strings (''') are NOT detected by is_inside_docstring;
# only """ is counted. This is acceptable because ruff enforces """ for docstrings.
# Usage: check_imports "description" "grep_pattern" dir1 [dir2 ...]
check_imports() {
    local description="$1"
    local pattern="$2"
    shift 2
    local dirs=("$@")

    for dir in "${dirs[@]}"; do
        [[ -d "$dir" ]] || continue

        while IFS=: read -r file line_num content; do
            [[ -z "$file" ]] && continue

            if is_inside_docstring "$file" "$line_num"; then
                continue
            fi

            if is_type_checking_guarded "$file" "$line_num"; then
                continue
            fi

            echo "  $file:$line_num: $content"
            echo "    ↳ $description"
            VIOLATIONS=$((VIOLATIONS + 1))
        done < <(grep -rn --include='*.py' -E "$pattern" "$dir" 2>/dev/null || true)
    done
}

echo "Checking hexagonal layer boundaries..."
echo ""

# Rule 1 (AC 1): No google.* imports outside adapters/
echo "[1/4] No google.* imports in domain/, ports/, engine/, utils/..."
check_imports \
    "google.* imports only allowed in adapters/" \
    "^[[:space:]]*(from[[:space:]]+google\.|import[[:space:]]+google\.)" \
    "$SRC_DIR/domain" "$SRC_DIR/ports" "$SRC_DIR/engine" "$SRC_DIR/utils"

# Rule 2 (AC 1): No litellm imports outside adapters/
echo "[2/4] No litellm imports in domain/, ports/, engine/, utils/..."
check_imports \
    "litellm imports only allowed in adapters/" \
    "^[[:space:]]*(from[[:space:]]+litellm|import[[:space:]]+litellm)" \
    "$SRC_DIR/domain" "$SRC_DIR/ports" "$SRC_DIR/engine" "$SRC_DIR/utils"

# Rule 3 (AC 2): No adapter imports in domain/ or ports/
echo "[3/4] No adapter imports in domain/ or ports/..."
check_imports \
    "adapter imports not allowed in domain/ or ports/" \
    "^[[:space:]]*(from[[:space:]]+gepa_adk\.adapters|import[[:space:]]+gepa_adk\.adapters)" \
    "$SRC_DIR/domain" "$SRC_DIR/ports"

# Rule 4 (AC 3): No engine imports in domain/, ports/, or adapters/
echo "[4/4] No engine imports in domain/, ports/, or adapters/..."
check_imports \
    "engine imports not allowed in domain/, ports/, or adapters/" \
    "^[[:space:]]*(from[[:space:]]+gepa_adk\.engine|import[[:space:]]+gepa_adk\.engine)" \
    "$SRC_DIR/domain" "$SRC_DIR/ports" "$SRC_DIR/adapters"

echo ""
if (( VIOLATIONS > 0 )); then
    echo "FAILED: Found $VIOLATIONS boundary violation(s)"
    exit 1
else
    echo "All boundary checks passed."
    exit 0
fi

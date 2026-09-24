#!/usr/bin/env bash
# PostToolUse hook: vet every Python file a tool call just changed.
# Runs ruff format, ruff check and docvet on each file. ty, lint-imports,
# pytest, uv-secure and the coverage floor stay in the pre-commit and
# pre-push hooks and the CLAUDE.md gate table.
# Reads the hook JSON on stdin. Write and Edit name the file. A Bash
# command reports the files it changed in tool_response.bashEditDiff
# when bashEditDiffEnabled is on. Without that list the hook takes every
# Python file under src, tests, scripts or examples whose mtime falls inside the
# command's duration. Findings return as additionalContext. A clean file returns
# nothing, so a clean edit costs no tokens. Each gate's output is capped
# at 30 lines. Paths are canonical (Python realpath, no GNU coreutils
# dependency) and prefixed with ./, so `..` cannot leave the root and a
# name that starts with `-` is never read as an option.
set -u
input=$(cat)
tool=$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null) || exit 0
root="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
canon() { python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$1"; }
root=$(canon "$root") || exit 0
cd "$root" || exit 0

# Print the project-relative ./path of one Python file inside the root.
inside() {
  local f="$1"
  case "$f" in *.py) ;; *) return 1 ;; esac
  case "$f" in /*) ;; *) f="$root/$f" ;; esac
  f=$(canon "$f") || return 1
  case "$f" in "$root"/*) f="./${f#"$root"/}" ;; *) return 1 ;; esac
  [ -f "$f" ] && printf '%s\n' "$f"
}

candidates=""
case "$tool" in
  Write|Edit)
    candidates=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
    ;;
  Bash)
    candidates=$(printf '%s' "$input" \
      | jq -r '.tool_response.bashEditDiff.files[]?.filePath // empty' 2>/dev/null)
    if [ -z "$candidates" ]; then
      ms=$(printf '%s' "$input" | jq -r '.duration_ms // 0' 2>/dev/null)
      candidates=$(python3 - "$ms" <<'PY'
import os, sys, time
try:
    window = float(sys.argv[1]) / 1000
except ValueError:
    window = 0.0
since = time.time() - window - 2
for top in ("src", "tests", "scripts", "examples"):
    for base, _dirs, names in os.walk(top):
        for name in names:
            if not name.endswith(".py"):
                continue
            path = os.path.join(base, name)
            try:
                recent = os.path.getmtime(path) >= since
            except OSError:
                continue
            if recent:
                print(path)
PY
)
    fi
    ;;
  *) exit 0 ;;
esac
files=""
while IFS= read -r c; do
  [ -n "$c" ] || continue
  rel=$(inside "$c") && files+="$rel"$'\n'
done <<< "$candidates"
files=$(printf '%s' "$files" | sort -u)
[ -n "$files" ] || exit 0

# Print the gate findings for one file, or nothing when it is clean.
vet() {
  local rel="$1" one="" fmt chk doc
  fmt=$(uv run ruff format --check --diff "$rel" 2>&1) \
    || one+="ruff format:"$'\n'"$(printf '%s\n' "$fmt" | head -30)"$'\n'
  chk=$(uv run ruff check --no-fix --output-format concise "$rel" 2>&1) \
    || one+="ruff check:"$'\n'"$(printf '%s\n' "$chk" | head -30)"$'\n'
  doc=$(uv run docvet check --quiet "$rel" 2>&1 | head -30)
  [ -n "$doc" ] && one+="docvet:"$'\n'"$doc"$'\n'
  printf '%s' "$one"
}
out=""
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  one=$(vet "$rel")
  [ -n "$one" ] && out+="== $rel"$'\n'"$one"$'\n'
done <<< "$files"
[ -z "$out" ] && exit 0
jq -n --arg c "$out" '{hookSpecificOutput: {hookEventName: "PostToolUse",
  additionalContext: ("Gate findings. Fix them before the next gate run.\n" + $c)}}'

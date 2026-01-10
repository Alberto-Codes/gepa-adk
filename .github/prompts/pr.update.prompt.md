```prompt
---
description: Update PR description based on diff analysis
name: pr.update
argument-hint: "[PR_NUMBER]"
---

# PR Description Update

Update an existing pull request's description by analyzing the actual diff and preserving important context from the current description.

## User Input

```text
${input:pr_number:PR number (optional - auto-detects from current branch)}
```

---

## Workflow

### 1. Get PR Number

```bash
# If not provided, detect from current branch
gh pr list --head $(git branch --show-current) --json number --jq '.[0].number'
```

- If no PR found: Error "No PR found for current branch. Create one first with /pr.create"
- Store PR number for subsequent commands

### 2. Get Current PR Body

```bash
gh pr view PR_NUMBER --json body,title --jq '{title: .title, body: .body}'
```

**Preserve from existing body:**
- Issue numbers (`Closes #123`, `Addresses #456`, `Related to #789`)
- Breaking changes documentation
- Specific testing instructions user added
- Important reviewer notes

### 3. Get PR Diff

⚠️ **Critical:** Use **remote branch**, not `HEAD` (which includes uncommitted local changes)

```bash
# Ensure we have latest
git fetch origin develop
git fetch origin $(git branch --show-current)

# Get diff comparing remote branches (what's actually in PR)
git diff origin/develop...origin/$(git branch --show-current) > /tmp/pr_diff.txt
```

**Read the diff file** using read_file tool, then delete it.

**Fallback if branch not pushed:**
```bash
gh pr diff PR_NUMBER > /tmp/pr_diff.txt
```

### 4. Analyze Changes

From the diff, identify:

| Analysis | Look For |
|----------|----------|
| **Type** | `feat`, `fix`, `docs`, `refactor`, `test`, `chore` |
| **Scope** | From `specs/XXX-name/` or component (engine, domain, ports) |
| **Key changes** | Files modified, patterns used, new APIs |
| **Test coverage** | Tests added/modified in `tests/` |
| **Breaking changes** | API signatures, schema changes, config changes |
| **ADR compliance** | Relevant ADRs from `docs/adr/` |

### 5. Read PR Template

Load `.github/pull_request_template.md` to understand required sections.

### 6. Generate Updated Description

**Merge existing context with new analysis:**

| Section | Source |
|---------|--------|
| Description | Diff analysis - what actually changed |
| Rationale | Why changes were made (from commits, issues) |
| Testing | Test commands: `uv run pytest path/to/tests -v` |
| Impact | Performance, security, dependencies |
| Related | **Preserve** existing issue links + add new ones |
| Review Notes | ADR compliance, focus areas, limitations |

### 7. Update PR

```bash
# Write description to temp file
cat > /tmp/pr_description.md << 'EOF'
<generated PR description>
EOF

# Update PR body
gh pr edit PR_NUMBER --body-file /tmp/pr_description.md

# Clean up
rm /tmp/pr_description.md /tmp/pr_diff.txt
```

### 8. Verify Update

```bash
gh pr view PR_NUMBER --json body --jq '.body' | head -50
```

Display:
- Confirmation of update
- Summary of changes made to description
- PR URL for review

---

## Error Handling

| Condition | Action |
|-----------|--------|
| No PR for branch | Error: suggest `/pr.create` first |
| Branch not pushed | Use `gh pr diff` instead of git diff |
| Diff too large (>300 files) | Summarize by directory, not file |
| PR already merged | Error: cannot update merged PR |

---

## What to Preserve

**Always keep from existing PR body:**
- Issue references (Closes, Addresses, Related to)
- Breaking changes documentation
- User-added testing instructions
- Reviewer notes and questions

**Enhance with:**
- Accurate diff-based analysis
- Updated scope and type classification
- Current test coverage status
- ADR compliance notes

---

## Examples

```bash
# Update PR for current branch (auto-detect)
/pr.update

# Update specific PR by number
/pr.update 27
```

---

## Notes

- **Always read current PR first** - Don't lose important context
- **Use remote branch for diff** - `origin/branch`, not `HEAD`
- **Be specific** - Generic descriptions don't help reviewers
- **Link context** - Reference specs/, ADRs, or related issues
- **Verify after update** - Confirm changes applied correctly
```

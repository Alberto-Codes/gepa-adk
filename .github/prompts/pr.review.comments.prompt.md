---
description: Analyze PR review comments and implement fixes
name: pr.review.comments
argument-hint: "[PR_NUMBER]"
---

# PR Review Comments Analysis & Implementation

Analyze GitHub PR review comments, create action plan, and implement fixes with quality checks.

## User Input

```text
${input:prNumber:PR number (optional - defaults to current branch's PR)}
```

---

## Workflow

### 1. Find PR

```bash
# If PR number provided, use it
# Otherwise, get PR for current branch
gh pr view --json number,title,url --jq '{number, title, url}'
```

If no PR exists for current branch, error and suggest running `/pr.create` first.

### 2. Fetch Review Comments

**Inline review comments (primary):**
```bash
gh api "repos/{owner}/{repo}/pulls/{PR_NUMBER}/comments" --paginate \
  --jq '.[] | {id, path, line, body, user: .user.login, created_at, in_reply_to_id}'
```

**Review summaries:**
```bash
gh pr view {PR_NUMBER} --json reviews \
  --jq '.reviews[] | {state, author: .author.login, body, submittedAt}'
```

**General PR comments:**
```bash
gh api "repos/{owner}/{repo}/issues/{PR_NUMBER}/comments" \
  --jq '.[] | {id, body, user: .user.login, created_at}'
```

### 3. Analyze Comments

**Group by severity:**

| Severity | Indicator | Action |
|----------|-----------|--------|
| 🔴 **CRITICAL** | Security, breaking changes, blockers | Must fix before merge |
| 🟡 **IMPORTANT** | Quality, consistency, bugs | Should fix before merge |
| 🔵 **MINOR** | Style, clarity, nice-to-have | Fix if time permits |

**Group by file** to minimize context switching.

**Identify patterns:**
- Same issue across multiple files → fix systematically
- Conflicting feedback → clarify with reviewer
- Already addressed → note as resolved

### 4. Create Action Plan

For each issue, document:

```markdown
### [SEVERITY] Issue Title
- **File(s):** `path/to/file.py:L123`
- **Reviewer:** @username
- **Problem:** Description of the issue
- **Fix:** Proposed solution
- **Status:** [ ] Pending / [x] Resolved
```

### 5. Implement Fixes

1. **Read affected files** - Understand current implementation
2. **Make changes** - Apply fixes per action plan
3. **Run quality checks:**
   ```bash
   uv run ruff check --fix          # Fix linting issues
   uv run ruff format               # Format code
   uv run ty check                  # Type check code
   uv run pytest -x                 # Run tests (stop on first failure)
   ```
4. **Verify changes** - `git diff` to confirm

### 6. Respond to Comments (Optional)

```bash
# Reply to a specific comment
gh api "repos/{owner}/{repo}/pulls/{PR_NUMBER}/comments/{COMMENT_ID}/replies" \
  -X POST -f body="Fixed in latest commit"
```

### 7. Commit Changes

```bash
# Stage and commit with descriptive message
git add -A
git commit -m "fix: address PR review feedback

- Fix issue 1 description
- Fix issue 2 description

Co-authored-by: Reviewer <reviewer@example.com>"

# Push changes
git push
```

---

## Analysis Output Format

```markdown
## PR Review Analysis: #{PR_NUMBER}

### Summary
- **Total comments:** X
- **Critical:** X | **Important:** X | **Minor:** X
- **Files affected:** X

### 🔴 Critical Issues
1. [Issue description] - `file.py:L123` (@reviewer)

### 🟡 Important Issues
1. [Issue description] - `file.py:L456` (@reviewer)

### 🔵 Minor Issues
1. [Issue description] - `file.py:L789` (@reviewer)

### Already Resolved
- [Issue] - Addressed in commit abc123
```

---

## Tips

- **Group related comments** before implementing (avoid piecemeal fixes)
- **Prioritize by impact** - Fix blockers first, then important, then minor
- **Keep it focused** - Only implement what reviewers requested
- **Run checks incrementally** - Verify no regressions after each change
- **Reply to comments** - Let reviewers know their feedback was addressed
- **Batch commits** - One commit per logical fix, not per comment

---

## Error Handling

| Condition | Action |
|-----------|--------|
| No PR for branch | Suggest running `/pr.create` first |
| No review comments | Report "No review comments found" |
| PR already merged | Error: "PR #{number} is already merged" |
| API rate limit | Wait and retry, or use `--paginate` for large PRs |

---
description: Create a draft PR by comparing current branch to develop, using PR template
name: pr.create
argument-hint: "[--base BRANCH] [--no-draft] [--no-push]"
---

# PR Creation

Create a draft pull request by comparing the current branch to develop, generating a PR description from the template, and using GitHub CLI to create and push the PR.

## User Input

```text
${input:options:Optional flags: --base BRANCH, --no-draft, --no-push}
```

---

## Workflow

### 1. Check Current Branch

```bash
git branch --show-current
```

- If on `develop`: Error "Cannot create PR from develop branch. Please create a feature branch first."
- Get remote tracking: `git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "No upstream"`

### 2. Get Diff Against Develop

```bash
# Ensure develop is up to date
git fetch origin develop

# Get diff comparing merge-base to branch tip (ONLY committed changes)
git diff $(git merge-base origin/develop HEAD)..$(git rev-parse HEAD) > /tmp/pr_diff.txt
```

**Read the diff file** using read_file tool, then delete it.

Analyze:
- Changed files and purposes
- Type of change: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Scope from file paths (e.g., `specs/002-domain-models/` → `002-domain-models`)
- Breaking changes indicators
- Test coverage

### 3. Read PR Template

Load `.github/pull_request_template.md` to understand required sections.

### 4. Search Open Issues for Relationships

```bash
gh issue list --state open --limit 100 --json number,title,body,labels,url
```

Match issues using:
- **Direct:** Branch name contains issue number (e.g., `feat/110-*` → Issue #110)
- **Keyword:** Issue title/body contains component names from changed files
- **Label:** Issue labels match change type

Format relationships:
- `Closes #123` - PR fully implements issue
- `Addresses #456` - PR partially addresses issue
- `Related to #789` - PR is related but doesn't solve

### 5. Generate PR Description

**Title format:** `type(scope): Brief description`

Example: `feat(002-domain-models): Add core domain models for evolution engine`

**Fill template sections:**

| Section | Source |
|---------|--------|
| Why | Issue descriptions, commit messages, problem context |
| What | Summary of file changes and functionality |
| How | Implementation details, patterns, decisions |
| Related Issues | Issues found in step 4 |
| Design Rationale | Link relevant ADRs from `docs/adr/` |
| Breaking Changes | API/schema/config changes from diff |
| How to Test | Test commands: `uv run pytest path/to/tests -v` |
| Impact Assessment | Performance, security, dependencies |

### 6. Push Branch if Needed

```bash
# Check if branch exists on origin
git ls-remote --heads origin $(git branch --show-current)

# Push if not exists (unless --no-push)
git push -u origin $(git branch --show-current)
```

### 7. Create PR

```bash
# Write description to temp file
cat > /tmp/pr_description.md << 'EOF'
<generated PR description>
EOF

# Create draft PR (default) or ready PR (--no-draft)
gh pr create --draft --base develop \
  --head $(git branch --show-current) \
  --title "type(scope): Brief description" \
  --body-file /tmp/pr_description.md

# Clean up
rm /tmp/pr_description.md /tmp/pr_diff.txt
```

### 8. Verify and Report

```bash
gh pr view --json number,url --jq '"\(.number): \(.url)"'
```

Display:
- PR number and URL
- Summary of changes included
- Any warnings (unstaged changes, etc.)

---

## Error Handling

| Condition | Action |
|-----------|--------|
| On develop branch | Error: suggest creating feature branch |
| No committed changes | Warn: diff is empty, nothing to PR |
| Unstaged changes | Warn: won't be included in PR |
| PR already exists | Offer to update existing PR |
| Push fails | Show error, suggest manual push |

---

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--base BRANCH` | Base branch for PR | `develop` |
| `--no-draft` | Create ready-for-review PR | Draft |
| `--no-push` | Skip pushing branch | Push |

---

## Examples

```bash
# Create draft PR from current branch (default)
/pr.create

# Create ready-for-review PR
/pr.create --no-draft

# Create PR against main instead of develop
/pr.create --base main

# Create PR without pushing (already pushed)
/pr.create --no-push
```

---

## Notes

- **Always output `git diff` to a file** - prevents timeouts and pagination issues
- Diff uses `$(git merge-base origin/develop HEAD)..$(git rev-parse HEAD)` - only committed changes
- PRs are **drafts by default** - use `--no-draft` for ready PRs
- Issue matching is conservative - only obvious relationships included
- Clean up all temp files after PR creation

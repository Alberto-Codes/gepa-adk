---
description: Create a draft PR for the current branch
---
Create a draft pull request for the current branch targeting `develop`.

## PR Template Reference

Use the PR template from `.github/PULL_REQUEST_TEMPLATE.md`:
- **Title**: `type(scope): description` (50 chars max, imperative mood)
- **Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`
- **Scope**: Noun describing codebase section (e.g., `engine`, `adapter`, `domain`)
- **Breaking changes**: Add `!` after scope → `feat(engine)!: remove deprecated method`

## Steps

### 1. Gather Context

Run these commands to understand what changed:

```bash
# Current branch and status
git branch --show-current
git status

# Commits on this branch (not in develop)
git log develop..HEAD --oneline

# Full diff from develop (file names only)
git diff develop --name-only

# Full diff with stats
git diff develop --stat

# Detailed diff for review
git diff develop
```

### 2. Analyze Changes

From the diff output, identify:
- **Why**: Problem solved or motivation for the change
- **What**: List of changes (2-4 bullets, imperative mood)
- **Type**: Is this a `feat`, `fix`, `docs`, `refactor`, `test`, or `chore`?
- **Scope**: Which area of code (`engine`, `adapter`, `domain`, `ports`, `api`, etc.)
- **Breaking**: Any breaking changes requiring `!` and `BREAKING CHANGE:` footer?

### 3. Check for Linked Issues

Look for issue references in:
- Branch name (e.g., `feat/191-stopper-protocol` → issue #191)
- Commit messages
- The work context

### 4. Push Branch and Create Draft PR

```bash
# Push branch to remote (with upstream tracking)
git push -u origin $(git branch --show-current)

# Create draft PR using gh CLI
gh pr create --draft --base develop --title "<type>(<scope>): <description>" --body "$(cat <<'EOF'
<Why this change? Problem solved?>

- <What changed - bullet 1>
- <What changed - bullet 2>

Test: `uv run pytest -v`

Closes #<issue_number>

---

## PR Review

### Checklist
- [ ] Self-reviewed my code
- [ ] Tests pass (`uv run pytest`)
- [ ] Lint passes (`uv run ruff check .`)
- [ ] Breaking changes use `!` in title and `BREAKING CHANGE:` in body

### Review Focus
<Where should reviewers concentrate?>

### Related
<Other PRs, issues, ADRs>
EOF
)"
```

### 5. Output PR URL

After creating the PR, output the URL so it can be opened.

## PR Body Format

```markdown
<Why this change? 1-2 sentences explaining the motivation.>

- <Imperative bullet describing change 1>
- <Imperative bullet describing change 2>
- <Imperative bullet describing change 3>

Test: `uv run pytest -v`

Closes #<issue_number>

---

## PR Review

### Checklist
- [ ] Self-reviewed my code
- [ ] Tests pass (`uv run pytest`)
- [ ] Lint passes (`uv run ruff check .`)
- [ ] Breaking changes use `!` in title and `BREAKING CHANGE:` in body

### Review Focus
<Areas needing attention, known limitations>

### Related
<Links to related PRs, issues, ADRs>
```

## Multi-Commit PRs

If the PR contains multiple logical changes, add footer blocks:

```markdown
<Primary change description>

- Bullets for primary change

Test: `uv run pytest -v`

Closes #123

feat(models)!: rename field for consistency

BREAKING CHANGE: `OldName` → `NewName` in SomeClass

docs(reference): add glossary

- Define canonical terminology
```

## Examples

**Feature PR title:**
```
feat(ports): add StopperProtocol for pluggable stop conditions
```

**Bug fix PR title:**
```
fix(engine): handle empty batch gracefully
```

**Breaking change PR title:**
```
feat(adapter)!: remove deprecated evaluate_sync method
```

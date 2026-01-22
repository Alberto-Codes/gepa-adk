---
description: Create a draft PR for the current branch
---
Create a draft pull request for the current branch targeting develop.

## 1. Gather Context

Run these commands to understand what changed:

```bash
git branch --show-current
git status
git log develop..HEAD --oneline
git diff develop --name-only
git diff develop --stat
```

## 2. Analyze Changes

From the diff, identify:
- **Why**: Problem solved or motivation
- **What**: 2-4 bullets in imperative mood
- **Type**: feat | fix | docs | refactor | test | chore | perf
- **Scope**: engine, adapter, domain, ports, api
- **Issue**: Extract from branch name (e.g., feat/191-foo → #191)

## 3. Push and Create PR

```bash
git push -u origin HEAD
```

Create draft PR with gh CLI using this body structure:

```
<motivation paragraph - why this change was needed>

- <bullet 1 in imperative mood>
- <bullet 2>
- <bullet 3>

Test: `uv run pytest -v`

Closes #<issue>

---

## PR Review

### Checklist
- [ ] Self-reviewed my code
- [ ] Tests pass (`uv run pytest`)
- [ ] Lint passes (`uv run ruff check .`)
- [ ] Breaking changes use `!` in title and `BREAKING CHANGE:` in body

### Review Focus
<where should reviewers concentrate?>

### Related
<other PRs, issues, ADRs for context>
```

## Title Format

`type(scope): description` (50 chars max, imperative mood)

Examples:
- `feat(ports): add StopperProtocol for pluggable stop conditions`
- `fix(engine): handle empty batch gracefully`
- `feat(adapter)!: remove deprecated evaluate_sync method` (breaking)

## 4. Output PR URL

After creating, output the URL so it can be opened.

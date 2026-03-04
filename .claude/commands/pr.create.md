---
description: Create a draft PR for the current branch
---
Create a draft pull request for the current branch targeting main.

## 1. Gather Context

```bash
git branch --show-current
git status
git log main..HEAD --oneline
git diff main --stat
```

## 2. Create PR

Push and create draft PR:

```bash
git push -u origin HEAD
gh pr create --draft --title "<title>" --body "<body>"
```

**Title**: `type(scope): description` (50 chars max, imperative mood)
- Types: feat | fix | docs | refactor | test | chore | perf
- Scope: engine, adapter, domain, ports, api (NOT issue numbers)
- Breaking: add exclamation mark (!) after scope

**Body**: Follow `.github/PULL_REQUEST_TEMPLATE.md` exactly:

```
<motivation - why this change was needed>

- <bullet 1 in imperative mood>
- <bullet 2>

Test: `uv run pytest -v`

Closes #<issue from branch name>

---

## PR Review

### Checklist
- [ ] Self-reviewed my code
- [ ] Tests pass (`uv run pytest`)
- [ ] Lint passes (`uv run ruff check .`)
- [ ] Breaking changes use exclamation mark in title and BREAKING CHANGE: in body

### Review Focus
<where should reviewers concentrate?>

### Related
<other PRs, issues, ADRs>
```

## 3. Output PR URL

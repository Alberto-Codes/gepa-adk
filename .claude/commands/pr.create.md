---
description: Create a draft PR for the current branch
---
Create a draft pull request for the current branch targeting develop.

## PR Template Reference

Use the PR template from .github/PULL_REQUEST_TEMPLATE.md:
- Title format: type(scope): description (50 chars max, imperative mood)
- Types: feat, fix, docs, refactor, test, chore, perf
- Scope: Noun describing codebase section (engine, adapter, domain, ports)
- Breaking changes: Add exclamation mark after scope (e.g., feat(engine)!: description)

## Steps

### 1. Gather Context

Run these commands to understand what changed:

```bash
git branch --show-current
git status
git log develop..HEAD --oneline
git diff develop --name-only
git diff develop --stat
git diff develop
```

### 2. Analyze Changes

From the diff output, identify:
- Why: Problem solved or motivation for the change
- What: List of changes (2-4 bullets, imperative mood)
- Type: Is this a feat, fix, docs, refactor, test, or chore?
- Scope: Which area of code (engine, adapter, domain, ports, api)
- Breaking: Any breaking changes requiring exclamation mark and BREAKING CHANGE footer?

### 3. Check for Linked Issues

Look for issue references in:
- Branch name (e.g., feat/191-stopper-protocol maps to issue 191)
- Commit messages
- The work context

### 4. Push Branch and Create Draft PR

Push the branch to remote with upstream tracking:
```bash
git push -u origin HEAD
```

Then create a draft PR using gh CLI with:
- --draft flag
- --base develop
- Appropriate title following conventional commit format
- Body with motivation, bullet points, test command, and issue link

### 5. Output PR URL

After creating the PR, output the URL so it can be opened.

## PR Body Structure

The PR body should contain:

1. Motivation paragraph explaining why this change is needed
2. Bullet list of what changed (imperative mood)
3. Test command: uv run pytest -v
4. Issue link: Closes #NUMBER
5. PR Review section with checklist

## Checklist Items

The PR should include these checklist items:
- Self-reviewed my code
- Tests pass (uv run pytest)
- Lint passes (uv run ruff check .)
- Breaking changes documented properly

## Multi-Commit PRs

If the PR contains multiple logical changes, add footer blocks after the main content.
Each footer starts with a conventional commit type line, then details.

## Title Examples

Feature: feat(ports): add StopperProtocol for pluggable stop conditions
Bug fix: fix(engine): handle empty batch gracefully
Breaking: feat(adapter)!: remove deprecated evaluate_sync method

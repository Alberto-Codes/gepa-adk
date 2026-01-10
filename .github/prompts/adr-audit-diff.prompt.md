---
description: Audit git diff or staged changes against ADRs
agent: adr-auditor
---

# Audit Git Changes

Analyze the current git diff (staged and/or unstaged changes) for ADR compliance.

## Instructions

1. First, get the git status to understand what's changed:
   - Run `git status` to see modified files
   - Run `git diff` for unstaged changes
   - Run `git diff --cached` for staged changes

2. Identify which ADRs apply based on the changed files:
   - `src/**/cli/**` → ADR-007 (CLI Pattern)
   - `src/**/adapters/**` → ADR-000, ADR-006, ADR-012
   - `src/**/domain/**` → ADR-000, ADR-011
   - `src/**/ports/**` → ADR-000, ADR-002
   - `src/**/core/services/**` → ADR-012
   - `tests/**` → ADR-005

3. Read the relevant ADRs from `docs/ADR-*.md`

4. Analyze each changed file against the applicable ADRs

5. Generate a compliance report with:
   - Summary of violations by severity
   - Specific file:line locations
   - Quotes of the violated ADR rules
   - Code examples showing the fix

## User Input

```text
$ARGUMENTS
```

If no arguments provided, audit all uncommitted changes (both staged and unstaged).

---
description: Create GitHub issues for ADR violations using gh CLI
name: adr.create-issues
tools:
  - runInTerminal
---

# Create GitHub Issues for ADR Violations

Create GitHub issues for each ADR violation from an audit report using `gh` CLI.

## Instructions

### 1. Parse Audit Report

Look for the ADR Compliance Audit Report in the conversation above.

### 2. Group Violations

Create **one issue per ADR violation type**, not per occurrence.

Example: 3 ADR-000 violations in different files = 1 issue.

### 3. Create Issues

**For implementation-ready fixes:**

```bash
gh issue create \
  --title "[ADR-XXX] Fix: <brief description>" \
  --label "enhancement,adr-violation" \
  --body "## Summary

ADR-XXX (<ADR Title>) violation in \`<file(s)>\`.

## Violations

| File | Line | Issue |
|------|------|-------|
| path/file.py | 42 | Description |

## ADR Reference

See [ADR-XXX](docs/adr/ADR-XXX-name.md) for the required pattern.

## Remediation

<specific fix steps>

## Acceptance Criteria

- [ ] Code follows ADR-XXX pattern
- [ ] No new violations introduced
- [ ] Tests pass"
```

**For complex violations needing design:**

```bash
gh issue create \
  --title "[Idea] ADR-XXX compliance: <description>" \
  --label "idea,adr-violation" \
  --body "## Problem

<describe architectural drift>

## ADR Reference

See [ADR-XXX](docs/adr/ADR-XXX-name.md).

## Discussion Needed

- Option A: ...
- Option B: ..."
```

### 4. Label Convention

Always include `adr-violation` label for tracking.

## Example

Audit found:
- 2 ADR-000 violations (external imports in domain)
- 1 ADR-001 violation (sync/async bridge)

Create 2 issues:

```bash
gh issue create \
  --title "[ADR-000] Fix: External imports in domain layer" \
  --label "enhancement,adr-violation" \
  --body "..."

gh issue create \
  --title "[ADR-001] Fix: Sync/async bridge in engine" \
  --label "enhancement,adr-violation" \
  --body "..."
```

## User Input

```text
$ARGUMENTS
```

If no arguments, process the most recent audit report in this conversation.

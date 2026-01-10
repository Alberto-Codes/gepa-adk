---
description: Audit git diff or staged changes against ADRs
name: adr.audit-diff
argument-hint: "[--staged | --unstaged | --all]"
---

# Audit Git Changes Against ADRs

Analyze current git changes for ADR compliance.

## Context

Reference the [ADR index](../../docs/adr/README.md) for available architectural decisions.

## Instructions

### 1. Get Git Status

```bash
git status
git diff              # unstaged changes
git diff --cached     # staged changes
```

### 2. Map Changed Files to ADRs

| Path Pattern | Relevant ADRs |
|-------------|---------------|
| `src/**/domain/**` | [ADR-000](../../docs/adr/ADR-000-hexagonal-architecture.md) (Domain layer rules) |
| `src/**/ports/**` | [ADR-000](../../docs/adr/ADR-000-hexagonal-architecture.md), [ADR-002](../../docs/adr/ADR-002-protocol-for-interfaces.md) |
| `src/**/adapters/**` | [ADR-000](../../docs/adr/ADR-000-hexagonal-architecture.md), [ADR-006](../../docs/adr/ADR-006-external-library-integration.md) |
| `src/**/engine/**` | [ADR-001](../../docs/adr/ADR-001-async-first-architecture.md) |
| `tests/**` | [ADR-005](../../docs/adr/ADR-005-three-layer-testing.md) |
| `**/exceptions.py` | [ADR-009](../../docs/adr/ADR-009-exception-hierarchy.md) |
| `**/logging.py`, `**/utils/log*` | [ADR-008](../../docs/adr/ADR-008-structured-logging.md) |

### 3. Read Applicable ADRs

Load only the ADRs relevant to the changed files.

### 4. Analyze Each Changed File

Check against applicable ADR rules.

### 5. Generate Report

```markdown
## ADR Compliance Report

### Summary
- **Files checked**: X
- **Violations**: Y (critical: Z)

### Violations

| Severity | File:Line | ADR | Violation | Fix |
|----------|-----------|-----|-----------|-----|
| CRITICAL | path:42 | ADR-000 | External import in domain | Move to adapters/ |
```

## User Input

```text
$ARGUMENTS
```

If no arguments, audit all uncommitted changes.

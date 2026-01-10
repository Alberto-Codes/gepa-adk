---
description: Fetch GitHub issue, create conventional branch, analyze codebase, and generate implementation plan
name: issue.implement
argument-hint: "<issue-number> [--no-branch]"
tools:
  - githubRepo
  - terminalLastCommand
  - codebase
---

# Issue Implementation Planner

Fetch issue, create branch, analyze codebase, generate actionable plan.

## Context

This project follows architectural decisions documented in the [ADR index](../../docs/adr/README.md).

**Key ADRs:**

- [ADR-000: Hexagonal Architecture](../../docs/adr/ADR-000-hexagonal-architecture.md) - Domain/Ports/Adapters
- [ADR-001: Async-First](../../docs/adr/ADR-001-async-first-architecture.md) - All core APIs async
- [ADR-002: Protocol Interfaces](../../docs/adr/ADR-002-protocol-for-interfaces.md) - Use Protocol, not ABC
- [ADR-005: Three-Layer Testing](../../docs/adr/ADR-005-three-layer-testing.md) - TDD approach
- [ADR-006: External Libraries](../../docs/adr/ADR-006-external-library-integration.md) - Behind ports only
- [ADR-009: Exceptions](../../docs/adr/ADR-009-exception-hierarchy.md) - EvolutionError hierarchy

## User Input

```text
${input:issueNumber:Issue number (e.g., 123, #123, or URL)}
```

Add `--no-branch` to skip branch creation.

---

## Workflow

### 1. Fetch Issue

```bash
gh issue view <NUMBER> --json number,title,body,labels,state
```

Extract:
- **Title, body** → requirements
- **Labels** → branch type:
  - `bug` → `fix/`
  - `enhancement`, `feature` → `feat/`
  - `docs` → `docs/`
  - default → `feat/`
- **State** → warn if closed

### 2. Create Branch (unless `--no-branch`)

**Convention:** `<type>/<number>-<slug>`

```bash
git checkout develop && git pull
git checkout -b <branch-name>
```

Example: Issue #42 "Add async evolution engine" → `feat/42-add-async-evolution-engine`

### 3. Gather Context

```bash
# Check ADRs
ls docs/adr/

# Understand package structure
ls src/gepa_adk/

# Review tests
ls tests/ 2>/dev/null || echo "No tests yet"

# Check config
head -50 pyproject.toml
```

**Project conventions:**
- **Package manager**: `uv` (`uv add`, `uv run`, `uv sync`)
- **Line length**: 100 characters
- **Docstrings**: Google convention
- **Type hints**: Required (checked by `ty`)
- **Target**: Python 3.12+

### 4. Generate Plan

Create `IMPLEMENTATION_PLAN_<number>.md`:

```markdown
# Implementation Plan: Issue #<NUMBER>

**Title:** <title>
**Branch:** <branch-name>

## Requirements

- [ ] Requirement 1
- [ ] Requirement 2

## ADR Compliance

| ADR | Applies | Notes |
|-----|---------|-------|
| [ADR-000](docs/adr/ADR-000-hexagonal-architecture.md) | Yes/No | Domain/ports/adapters |
| [ADR-001](docs/adr/ADR-001-async-first-architecture.md) | Yes/No | Async APIs |
| [ADR-002](docs/adr/ADR-002-protocol-for-interfaces.md) | Yes/No | Protocol interfaces |
| [ADR-005](docs/adr/ADR-005-three-layer-testing.md) | Yes | Testing strategy |
| [ADR-009](docs/adr/ADR-009-exception-hierarchy.md) | Yes/No | Exception handling |

## Tasks

1. [ ] Write tests first (TDD)
2. [ ] Implement domain layer
3. [ ] Create port interfaces (if needed)
4. [ ] Implement adapters (if needed)
5. [ ] Verify checks pass

## Files

**New:**
- `src/gepa_adk/<layer>/<file>.py`
- `tests/test_<feature>.py`

**Modified:**
- List existing files

## Verification

```bash
uv run pytest
uv run ruff check --fix
uv run ruff format
uv run ty check
```

## Definition of Done

- [ ] All requirements implemented
- [ ] Tests pass (TDD)
- [ ] Type hints on all functions
- [ ] Google-style docstrings
- [ ] No lint errors
- [ ] ADR compliant
```

### 5. Report

- ✅ Branch created: `<branch-name>`
- ✅ Plan saved: `IMPLEMENTATION_PLAN_<number>.md`
- 📋 Next: Review plan, write tests first, implement

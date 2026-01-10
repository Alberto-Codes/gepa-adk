---
description: Full ADR compliance audit of source or test directories
name: adr.audit-full
argument-hint: "[src | tests | all]"
---

# Full Codebase ADR Audit

Comprehensive ADR compliance audit across the codebase.

## Context

Reference the [ADR index](../../docs/adr/README.md) for all architectural decisions.

## Instructions

### 1. Load All ADRs

Read all ADRs from `docs/adr/`:

- [ADR-000: Hexagonal Architecture](../../docs/adr/ADR-000-hexagonal-architecture.md)
- [ADR-001: Async-First Architecture](../../docs/adr/ADR-001-async-first-architecture.md)
- [ADR-002: Protocol for Interfaces](../../docs/adr/ADR-002-protocol-for-interfaces.md)
- [ADR-005: Three-Layer Testing](../../docs/adr/ADR-005-three-layer-testing.md)
- [ADR-006: External Library Integration](../../docs/adr/ADR-006-external-library-integration.md)
- [ADR-008: Structured Logging](../../docs/adr/ADR-008-structured-logging.md)
- [ADR-009: Exception Hierarchy](../../docs/adr/ADR-009-exception-hierarchy.md)
- [ADR-010: Docstring Quality](../../docs/adr/ADR-010-docstring-quality.md)

### 2. Scan Target Directory

```bash
find <target> -name "*.py" -type f
```

### 3. Categorize Files by Layer

| Layer | Path Pattern | Primary ADRs |
|-------|-------------|--------------|
| Domain | `domain/` | ADR-000, ADR-009 |
| Ports | `ports/` | ADR-000, ADR-002 |
| Adapters | `adapters/` | ADR-000, ADR-006, ADR-008 |
| Engine | `engine/` | ADR-001 |
| Utils | `utils/` | ADR-008 |
| Tests | `tests/` | ADR-005 |

### 4. Apply ADR Checks

For each file, verify compliance with applicable ADRs.

### 5. Generate Comprehensive Report

```markdown
## Full ADR Compliance Audit

**Target**: <directory>
**Files scanned**: X
**Total violations**: Y

### By Severity

| Severity | Count |
|----------|-------|
| CRITICAL | X |
| HIGH | Y |
| MEDIUM | Z |

### Violations by ADR

#### ADR-000: Hexagonal Architecture
- file.py:42 - External import in domain layer

#### ADR-001: Async-First Architecture
- (none)
```

## User Input

```text
$ARGUMENTS
```

**Valid targets:**
- `src` - Source directory audit
- `tests` - Test directory audit
- `all` - Both src and tests
- Specific path like `src/gepa_adk/engine/`

Default: `src/gepa_adk/`

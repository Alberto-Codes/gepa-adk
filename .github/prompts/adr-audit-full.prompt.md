---
description: Full ADR compliance audit of source or test directories
agent: adr-auditor
---

# Full Codebase ADR Audit

Perform a comprehensive ADR compliance audit across the specified directory.

## Instructions

1. Scan all Python files in the target directory
2. Load ALL ADRs from `docs/ADR-*.md`
3. Categorize files by layer:
   - Domain (`domain/`)
   - Ports (`ports/`)
   - Adapters (`adapters/`)
   - CLI (`cli/`)
   - Core Services (`core/services/`)
   - Tests (`tests/`)

4. Apply relevant ADR checks to each category
5. Generate a comprehensive report sorted by severity

## User Input

```text
$ARGUMENTS
```

If no arguments provided, audit `src/agent_workflow_suite/`.

Valid targets:
- `src` or `src/` - Full source audit
- `tests` or `tests/` - Full test audit  
- `all` - Both src and tests
- Specific path like `src/agent_workflow_suite/cli/`

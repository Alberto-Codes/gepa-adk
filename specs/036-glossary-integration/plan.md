# Implementation Plan: MkDocs Glossary Integration

**Branch**: `036-glossary-integration` | **Date**: 2026-01-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/036-glossary-integration/spec.md`

## Summary

Integrate mkdocs-ezglossary plugin to enable auto-linked glossary terms with hover tooltips across all documentation pages. This converts the existing static glossary (`docs/reference/glossary.md`) to definition list format with sections, enabling automatic cross-referencing, plural form recognition, and inline term tooltips.

## Technical Context

**Language/Version**: Python 3.12 (MkDocs plugin ecosystem)
**Primary Dependencies**: mkdocs-ezglossary-plugin>=2.1.0, Material for MkDocs (existing)
**Storage**: N/A (static site generation)
**Testing**: Manual verification via `uv run mkdocs serve` + `uv run mkdocs build`
**Target Platform**: GitHub Pages static site (https://alberto-codes.github.io/gepa-adk/)
**Project Type**: Documentation infrastructure (no source code changes)
**Performance Goals**: N/A (build-time plugin, no runtime impact)
**Constraints**: Must preserve existing glossary content and definitions
**Scale/Scope**: ~25 glossary terms across 5 sections

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Status | Notes |
|-----------|----------|--------|-------|
| I. Hexagonal Architecture | NO | N/A | Documentation-only change, no source code |
| II. Async-First Design | NO | N/A | No I/O operations added |
| III. Protocol-Based Interfaces | NO | N/A | No interfaces added |
| IV. Three-Layer Testing | NO | N/A | MkDocs build verification suffices |
| V. Observability & Code Documentation | NO | N/A | Enhances docs, no code docstrings changed |
| VI. Documentation Synchronization | YES | PASS | This IS a docs feature; mkdocs build verification applies |

**Gate Status**: PASS - Documentation-only feature aligns with Section VI requirements.

**Constitution Check (Post-Design)**: Re-verified - no violations. Feature adds documentation infrastructure without touching source code layers.

## Project Structure

### Documentation (this feature)

```text
specs/036-glossary-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (empty - no API contracts)
└── tasks.md             # Phase 3 output (/speckit.tasks)
```

### Source Code (repository root)

```text
# Documentation infrastructure only - no src/ changes
docs/
├── reference/
│   └── glossary.md      # MODIFY: Convert to ezglossary definition list format
mkdocs.yml               # MODIFY: Add ezglossary plugin + def_list extension
pyproject.toml           # MODIFY: Add mkdocs-ezglossary-plugin to dev deps
```

**Structure Decision**: Documentation-only feature modifies three files in the docs infrastructure. No source code (`src/`) or test (`tests/`) changes required.

## Complexity Tracking

> No violations. Documentation-only feature with minimal complexity.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| No new source layers | PASS | Only docs infrastructure |
| Single plugin addition | PASS | ezglossary is well-maintained, single-purpose |
| Format migration | PASS | Straightforward definition list syntax |

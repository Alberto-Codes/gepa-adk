# Data Model: MkDocs Glossary Integration

**Feature**: 036-glossary-integration
**Date**: 2026-01-18

## Overview

This feature does not introduce new runtime data models. All data structures are configuration and content artifacts processed at MkDocs build time.

---

## Configuration Entities

### GlossarySection

A logical grouping of related glossary terms.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | string | Section identifier (e.g., "core", "trial") |
| display_name | string | Human-readable heading (e.g., "Core Concepts") |
| terms | list[GlossaryTerm] | Terms belonging to this section |

**Defined Sections**:
- `core` → "Core Concepts"
- `trial` → "Trial Data Structures"
- `evolution` → "Evolution Process"
- `model` → "Data Model Types"
- `abbr` → "Abbreviations"

---

### GlossaryTerm

A domain-specific term with its definition.

| Attribute | Type | Description |
|-----------|------|-------------|
| section | string | Parent section prefix |
| name | string | Term identifier (snake_case or PascalCase) |
| definition | string | Multi-line definition text (Markdown) |
| aliases | list[string] | Optional alternate names (auto-handled by plurals) |

**Markdown Format**:
```markdown
section:term_name
:   Definition text. Supports **formatting** and `code`.
```

---

### TermReference

An occurrence of a glossary term in documentation (conceptual only—handled by plugin at build time).

| Attribute | Type | Description |
|-----------|------|-------------|
| syntax | string | Reference markup: `<section:term>` |
| target | GlossaryTerm | Resolved term definition |
| page | string | Source page containing the reference |

---

## Content Structure

### Glossary Page Layout

```text
docs/reference/glossary.md
├── # Glossary (title)
├── ## Core Concepts
│   └── <glossary::core>
├── ## Trial Data Structures
│   └── <glossary::trial>
├── ## Evolution Process
│   └── <glossary::evolution>
├── ## Data Model Types
│   └── <glossary::model>
└── ## Abbreviations
    └── <glossary::abbr>
```

### Term Definition Inventory

| Section | Terms | Count |
|---------|-------|-------|
| core | component, component_text, evolved_component_text, evolved_components | 4 |
| trial | trial, trials, feedback, trajectory | 4 |
| evolution | evolution, mutation, merge, reflection, proposed_component_text | 5 |
| model | Candidate, IterationRecord, EvolutionResult, MultiAgentEvolutionResult | 4 |
| abbr | ADK, GEPA, LLM | 3 |
| **Total** | | **20** |

---

## Configuration Files

### mkdocs.yml Plugin Configuration

```yaml
plugins:
  - ezglossary:
      strict: true
      ignore_case: true
      inline_refs: short
      plurals: en
      tooltip: short
      sections:
        - core
        - trial
        - evolution
        - model
        - abbr
```

### pyproject.toml Dependency

```toml
[dependency-groups]
dev = [
    # ... existing deps ...
    "mkdocs-ezglossary-plugin>=2.1.0",
]
```

---

## State Transitions

N/A - Static content generation, no runtime state.

## Validation Rules

| Rule | Enforcement |
|------|-------------|
| Section must be defined | `strict: true` warns on undefined sections |
| Term must exist | Undefined terms render as plain text (no broken links) |
| Definition must be non-empty | Manual review during content migration |
| No duplicate terms per section | Plugin deduplicates automatically |

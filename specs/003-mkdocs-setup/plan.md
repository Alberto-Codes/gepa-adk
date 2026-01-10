# Implementation Plan: MkDocs Material Documentation Setup (Full Automation)

**Branch**: `003-mkdocs-setup` | **Date**: January 10, 2026 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-mkdocs-setup/spec.md`

## Summary

Set up MkDocs Material documentation with **fully automated API reference generation**. Leveraging all installed dev dependencies to eliminate manual maintenance: new modules automatically appear in docs with proper navigation, inherited docstrings, last-updated timestamps, and production optimization.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: 
- `mkdocs-material>=9.7.1` - Theme
- `mkdocstrings-python>=2.0.1` - API docstring rendering
- `mkdocs-gen-files>=0.5.0` - Auto-generate API pages
- `mkdocs-literate-nav>=0.6.1` - Auto-generate navigation
- `mkdocs-section-index>=0.3.9` - Clean `__init__` handling
- `mkdocs-git-revision-date-localized>=1.4.7` - Last updated timestamps
- `mkdocs-macros-plugin>=1.3.7` - Dynamic variables
- `mkdocs-glightbox>=0.4.0` - Image lightbox
- `mkdocs-minify-plugin>=0.8.0` - Production optimization
- `griffe-inherited-docstrings>=1.1.2` - Inherit parent docstrings
- `griffe-warnings-deprecated>=1.1.0` - Deprecation notices

**Storage**: N/A (static site generation)  
**Testing**: `uv run mkdocs build --strict` and `uv run mkdocs serve`  
**Target Platform**: GitHub Pages (static HTML)  
**Project Type**: Single Python package (`src/gepa_adk/`)  
**Performance Goals**: Build < 60s, serve startup < 5s  
**Constraints**: Must work with existing `.github/workflows/docs.yml`  
**Scale/Scope**: ~8 ADRs, 4+ domain modules (auto-scaling)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Relevant? | Status | Notes |
|-----------|-----------|--------|-------|
| I. Hexagonal Architecture | No | ✅ N/A | Documentation only |
| II. Async-First Design | No | ✅ N/A | No runtime code |
| III. Protocol-Based Interfaces | No | ✅ N/A | No new interfaces |
| IV. Three-Layer Testing | No | ✅ N/A | Validated by CI build |
| V. Observability & Documentation | Yes | ✅ Supports | Renders existing docstrings |

**Gate Result**: ✅ PASS

## Docstring Practices Alignment

This plan is designed to fully render your existing docstring conventions (ADR-010, `docstring-templates.md`):

| Docstring Feature | Your Convention | mkdocstrings Rendering |
|-------------------|-----------------|------------------------|
| **Google-style** | Enforced via ruff D | `docstring_style: google` |
| **Attributes section** with types | `name (type): Description` | `show_symbol_type_heading: true` |
| **Examples section** | Fenced ` ```python ` blocks | Syntax highlighted, copy button |
| **Note:** admonitions | Used in every class/function | Blue info callout box |
| **Warning:** admonitions | For critical misuse warnings | Orange warning callout box |
| **See Also:** cross-refs | `` [`module`][module] `` syntax | `signature_crossrefs: true` |
| **Raises:** section | Exception documentation | Links to exception class docs |
| **`__all__` exports** | All modules export explicitly | Required for gen-files script |
| **`@deprecated` decorator** | Template in docstring-templates.md | `griffe_warnings_deprecated` |

### Example: How Your Code Will Render

Your `EvolutionConfig` class docstring:
```python
"""Configuration parameters for an evolution run.

Attributes:
    max_iterations: Maximum number of evolution iterations...

Examples:
    Creating a configuration with defaults:

    \`\`\`python
    config = EvolutionConfig(max_iterations=100, patience=10)
    \`\`\`

Note:
    All numeric parameters are validated in __post_init__...
"""
```

Will render as:
- **Heading**: `EvolutionConfig` with signature
- **Attributes table**: Type-annotated fields with descriptions
- **Examples**: Syntax-highlighted, copyable code block
- **Note**: Blue admonition box with implementation detail
- **Source**: Expandable link to GitHub source

## Project Structure

### Documentation Artifacts

```text
specs/003-mkdocs-setup/
├── plan.md              # This file
├── research.md          # Research findings (automation strategy)
├── quickstart.md        # Quick reference guide
└── checklists/
    └── requirements.md  # Validation checklist
```

### Files to Create

```text
# Root level
mkdocs.yml                        # Main configuration (full automation)

# Scripts for automation
scripts/
└── gen_ref_pages.py              # Auto-generate API reference pages

# Documentation content
docs/
├── index.md                      # Landing page
├── getting-started.md            # Quick start guide
├── reference/                    # AUTO-GENERATED (by gen_ref_pages.py)
│   └── SUMMARY.md                # AUTO-GENERATED navigation
├── adr/                          # EXISTING - add to nav
│   ├── README.md
│   └── ADR-*.md
└── contributing/                 # EXISTING - add to nav
    └── docstring-templates.md
```

**Key Insight**: The `docs/reference/` folder and its contents are **generated at build time** by `gen_ref_pages.py`. No manual API pages needed!

## Design: mkdocs.yml Configuration

```yaml
site_name: GEPA-ADK
site_description: Async-first evolution engine for agentic development
site_url: https://alberto-codes.github.io/gepa-adk/
repo_url: https://github.com/Alberto-Codes/gepa-adk
repo_name: Alberto-Codes/gepa-adk
edit_uri: edit/develop/

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - navigation.indexes
    - search.suggest
    - search.highlight
    - content.code.copy
    - content.action.edit
  palette:
    - scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode

plugins:
  - search
  - gen-files:
      scripts:
        - scripts/gen_ref_pages.py
  - literate-nav:
      nav_file: SUMMARY.md
  - section-index
  - mkdocstrings:
      default_handler: python
      handlers:
        python:
          paths: [src]
          options:
            # Docstring parsing (ADR-010 compliance)
            docstring_style: google
            docstring_section_style: spacy  # Clean admonition rendering
            
            # Source display
            show_source: true
            show_root_heading: true
            show_root_full_path: false
            
            # Symbol type display (matches Attributes section pattern)
            show_symbol_type_heading: true
            show_symbol_type_toc: true
            
            # Member ordering (preserves logical source order)
            members_order: source
            group_by_category: true
            show_submodules: true
            
            # Signature rendering (matches your type hint practices)
            show_signature_annotations: true
            separate_signature: true
            signature_crossrefs: true  # Links types to their docs
            
            # Inheritance (ADR-000 hexagonal)
            show_bases: true
            show_inheritance_diagram: true
            
            # Griffe extensions for your docstring patterns
            extensions:
              - griffe_inherited_docstrings  # Child classes get parent docstrings
              - griffe_warnings_deprecated   # @deprecated decorator support
  - git-revision-date-localized:
      enable_creation_date: true
      type: timeago
  - glightbox
  - minify:
      minify_html: true
  - macros

markdown_extensions:
  # Mermaid diagrams (ADR architecture diagrams)
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  
  # Code highlighting (Examples sections)
  - pymdownx.highlight:
      anchor_linenums: true
      line_spans: __span
      pygments_lang_class: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  
  # Admonitions (Note:, Warning: sections from docstrings)
  - admonition
  - pymdownx.details  # Collapsible admonitions
  
  # Cross-references and TOC
  - toc:
      permalink: true
  - attr_list
  - md_in_html
  
  # Tables (docstring-templates.md uses tables)
  - tables

extra:
  project_name: GEPA-ADK
  version: "0.1.0"

nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - API Reference: reference/
  - Architecture:
    - adr/index.md
    - Hexagonal Architecture: adr/ADR-000-hexagonal-architecture.md
    - Async-First: adr/ADR-001-async-first-architecture.md
    - Protocol Interfaces: adr/ADR-002-protocol-for-interfaces.md
    - Three-Layer Testing: adr/ADR-005-three-layer-testing.md
    - External Libraries: adr/ADR-006-external-library-integration.md
    - Structured Logging: adr/ADR-008-structured-logging.md
    - Exception Hierarchy: adr/ADR-009-exception-hierarchy.md
    - Docstring Quality: adr/ADR-010-docstring-quality.md
  - Contributing:
    - Docstring Templates: contributing/docstring-templates.md
```

## Design: API Generation Script

**`scripts/gen_ref_pages.py`**:
```python
"""Generate the code reference pages and navigation.

This script is executed by mkdocs-gen-files during the build process.
It automatically creates API documentation pages for all Python modules
in src/gepa_adk/ and generates the navigation structure.

Note:
    This script runs at build time, not at runtime. The generated files
    are virtual and do not appear in the repository.
"""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

root = Path(__file__).parent.parent
src = root / "src"

for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = tuple(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1] == "__main__":
        continue

    nav[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"::: {ident}")

    mkdocs_gen_files.set_edit_path(full_doc_path, path.relative_to(root))

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
```

## Automation Benefits Matrix

| Manual Task Eliminated | Plugin Responsible |
|-----------------------|-------------------|
| Create API page for each module | `mkdocs-gen-files` |
| Update nav when adding modules | `mkdocs-literate-nav` |
| Handle `__init__.py` sections | `mkdocs-section-index` |
| Copy parent docstrings | `griffe-inherited-docstrings` |
| Add "last updated" dates | `git-revision-date-localized` |
| Optimize for production | `mkdocs-minify-plugin` |
| Add image lightbox | `mkdocs-glightbox` |

## Implementation Tasks

### Phase 1: Core Setup
1. Create `mkdocs.yml` with full plugin configuration
2. Create `scripts/gen_ref_pages.py` for API automation
3. Create `docs/index.md` landing page
4. Create `docs/getting-started.md` quick start guide
5. Create `docs/adr/index.md` for ADR section landing

### Phase 2: Validation
6. Run `uv run mkdocs build --strict` to verify build
7. Run `uv run mkdocs serve` and test all pages
8. Verify API reference auto-generates for all modules
9. Verify Mermaid diagrams render correctly
10. Verify "last updated" timestamps appear

### Phase 3: CI Integration
11. Verify `.github/workflows/docs.yml` has `fetch-depth: 0`
12. Test PR to confirm CI passes

## Validation Checklist

| Requirement | Test |
|-------------|------|
| FR-001 Config file | `mkdocs.yml` exists and valid |
| FR-002 Material theme | Theme renders correctly |
| FR-003 API auto-gen | All modules appear in `/reference/` |
| FR-004 Mermaid | Diagrams render as graphics |
| FR-005 Landing page | `docs/index.md` accessible |
| FR-006 Getting started | Guide exists and links work |
| FR-007 ADR integration | All ADRs in navigation |
| FR-008 Contributing | Templates page accessible |
| FR-009 Local preview | `mkdocs serve` works |
| FR-010 Static build | `mkdocs build` succeeds |
| SC-001 Build time | < 60 seconds |
| SC-002 API coverage | All public modules documented |
| SC-003 Mermaid | 100% render correctly |
| SC-004 Serve time | < 5 seconds to start |
| SC-005 CI pass | Workflow succeeds |

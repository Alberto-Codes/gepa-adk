# Research: MkDocs Glossary Integration

**Feature**: 036-glossary-integration
**Date**: 2026-01-18

## Executive Summary

Research confirms mkdocs-ezglossary-plugin v2.1.0+ is the appropriate solution for cross-referenced glossary functionality. The plugin integrates seamlessly with Material for MkDocs and requires minimal configuration.

---

## Decision 1: Plugin Selection

**Decision**: Use `mkdocs-ezglossary-plugin>=2.1.0`

**Rationale**:
- Purpose-built for MkDocs glossary functionality
- Native Material for MkDocs integration
- Supports all required features: auto-linking, tooltips, sections, plurals
- Well-maintained with recent releases
- Definition list format is clean and readable

**Alternatives Considered**:
- **abbr extension + manual links**: Too labor-intensive, no auto-linking
- **mkdocs-glossary (older)**: Less feature-rich, no section support
- **Custom MkDocs hooks**: Over-engineering for standard use case

---

## Decision 2: Configuration Options

**Decision**: Use the following mkdocs.yml configuration:

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

**Rationale**:
- `strict: true` - Warns on undefined sections (catches typos)
- `ignore_case: true` - Matches "Component" and "component" (FR-006)
- `inline_refs: short` - Shows concise backlinks to term usage
- `plurals: en` - English plural recognition (FR-005)
- `tooltip: short` - Shows definition on hover (FR-002)
- Explicit sections match the five categories in the existing glossary

**Alternatives Considered**:
- `tooltip: full` - Too verbose for inline viewing
- `plurals: inflect` - Requires additional dependency, overkill for English-only
- `markdown_links: true` - Not needed; angle bracket syntax is sufficient

---

## Decision 3: Definition List Format

**Decision**: Convert glossary to ezglossary definition list format with sections.

**Format Syntax**:
```markdown
section:term_name
:   Definition text here. Can include **bold**, *italic*, `code`,
    and multiple paragraphs.
```

**Example for existing glossary terms**:
```markdown
core:component
:   An evolvable unit with a name and text content. Components are the
    fundamental building blocks that the evolution engine optimizes.

core:component_text
:   The current text content of a component being evolved. This is the value
    associated with a component name in a Candidate's components dictionary.

trial:trial
:   One performance record from evaluating a component_text against a test case.
    A trial contains two main parts: feedback and trajectory.

model:Candidate
:   A mutable container holding components being evolved. Includes lineage
    tracking for evolution history.

abbr:ADK
:   Agent Development Kit (Google)
```

**Rationale**:
- Clean, readable Markdown format
- Section prefix enables categorical organization
- Definition list extension (`def_list`) is already common in MkDocs setups
- Preserves existing definition content with minimal reformatting

---

## Decision 4: Inline Reference Syntax

**Decision**: Use angle bracket syntax `<section:term>` for explicit references.

**Examples**:
```markdown
The <core:component_text> is validated by StateGuard before acceptance.

See <model:EvolutionResult> for the complete result structure.

The <abbr:ADK> provides the agent framework.
```

**With custom text**:
```markdown
Each <core:component|evolvable component> has a text value.
```

**Rationale**:
- Clear, unambiguous syntax distinguishes from regular text
- Section prefix prevents collisions with similar terms
- Custom text option available when needed
- No additional configuration required (unlike Markdown links)

---

## Decision 5: Glossary Summary Page Structure

**Decision**: Use section-based summary directives on the glossary page.

**Format**:
```markdown
# Glossary

## Core Concepts
<glossary::core>

## Trial Data Structures
<glossary::trial>

## Evolution Process
<glossary::evolution>

## Data Model Types
<glossary::model>

## Abbreviations
<glossary::abbr>
```

**Rationale**:
- Automatic rendering of all terms in each section
- Alphabetical ordering within sections
- Includes definitions and backlinks by default
- Clean separation matches existing glossary structure

---

## Decision 6: Markdown Extension Requirement

**Decision**: Add `def_list` to markdown_extensions in mkdocs.yml.

**Configuration**:
```yaml
markdown_extensions:
  # ... existing extensions ...
  - def_list
```

**Rationale**:
- Required for ezglossary definition list parsing
- Standard Python-Markdown extension (no additional dependency)
- Already commonly used with Material for MkDocs

---

## Section Mapping

Map existing glossary sections to ezglossary section prefixes:

| Existing Heading | Section Prefix | Terms |
|------------------|----------------|-------|
| Core Concepts | `core` | component, component_text, evolved_component_text, evolved_components |
| Trial Data Structures | `trial` | trial, trials, feedback, trajectory |
| Evolution Process | `evolution` | evolution, mutation, merge, reflection, proposed_component_text |
| Data Model Types | `model` | Candidate, IterationRecord, EvolutionResult, MultiAgentEvolutionResult |
| Abbreviations | `abbr` | ADK, GEPA, LLM |

**Total**: ~17 primary terms + related/alias terms

---

## Edge Case Handling

| Edge Case | Solution |
|-----------|----------|
| Terms in code blocks | ezglossary skips code blocks by default (FR-008 satisfied) |
| Substring matches | Plugin uses word boundary matching; "text" won't match in "context" |
| Case variations | `ignore_case: true` handles Component/component |
| Missing definitions | `strict: true` warns; undefined terms render as plain text |
| Special characters in terms | Use HTML entities (e.g., `&#35;` for `#`) |

---

## Verification Plan

1. **Build test**: `uv run mkdocs build` succeeds without warnings
2. **Serve test**: `uv run mkdocs serve` shows tooltips on hover
3. **Auto-link test**: Navigate to any doc page with glossary terms, verify links appear
4. **Plural test**: Write "components" in a doc, verify link to "component" definition
5. **Code block test**: Verify terms in ` ``` ` blocks are not linked

---

## References

- [mkdocs-ezglossary documentation](https://realtimeprojects.github.io/mkdocs-ezglossary/)
- [PyPI - mkdocs-ezglossary-plugin](https://pypi.org/project/mkdocs-ezglossary-plugin/)
- [Material for MkDocs - Tooltips](https://squidfunk.github.io/mkdocs-material/reference/tooltips/)
- [Python-Markdown def_list](https://python-markdown.github.io/extensions/definition_lists/)

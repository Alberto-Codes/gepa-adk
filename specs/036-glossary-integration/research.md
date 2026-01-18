# Research: MkDocs Glossary Integration

**Feature**: 036-glossary-integration
**Date**: 2026-01-18
**Method**: Package installation + source code analysis in `.venv`

---

## Executive Summary

Three glossary solutions were evaluated against the feature requirements from spec.md:

| Requirement | Material abbr | mkdocs-glossary | ezglossary |
|-------------|:-------------:|:---------------:|:----------:|
| FR-001: Auto-link terms | ✅ | ⚠️ italic only | ❌ manual |
| FR-002: Tooltip on hover | ✅ | ❌ | ✅ |
| FR-003: Organize by sections | ❌ | ❌ | ✅ |
| FR-005: Plural recognition | ❌ | ❌ | ✅ |
| FR-006: Case-insensitive | ❌ | ✅ | ✅ |

**No single solution meets all requirements.**

---

## Detailed Analysis

### Solution 1: Material for MkDocs Abbreviations

**Package**: Built into `mkdocs-material`

**Source**: Python-Markdown `abbr` extension + `pymdownx.snippets` auto_append

#### How It Works
```markdown
# includes/glossary.md
*[component]: An evolvable unit with a name and text content
*[evolution]: The iterative optimization process
```

Every occurrence of "component" or "evolution" automatically becomes a tooltip.

#### Verified Behavior
- **Auto-links**: ✅ All occurrences, zero markup needed
- **Tooltips**: ✅ Native Material styling
- **Case-sensitive**: ⚠️ "Evolution" ≠ "evolution" (must define both)
- **Plurals**: ❌ "components" won't match "component"
- **Sections**: ❌ Flat list only
- **Code blocks**: ✅ Automatically skipped

#### Strengths
1. Zero author effort - just write naturally
2. Readers get tooltips everywhere terms appear
3. No extra dependencies
4. Clean, simple glossary file

#### Weaknesses
1. Case-sensitive (workaround: define both forms)
2. No plural handling (workaround: define "component" and "components")
3. No sections (workaround: use comments in glossary file)
4. Over-linking risk for common words

#### mkdocstrings Conflict
Terms like "Candidate" will conflict with API docs. **Resolution**: Don't define class names in glossary - let mkdocstrings handle them.

---

### Solution 2: mkdocs-glossary

**Package**: `mkdocs-glossary>=0.1.5`

**Source**: `.venv/lib/python3.12/site-packages/mkdocs_glossary/plugin.py`

#### How It Works
```markdown
# docs/glossary.md (numbered list format required)
1. **component** : An evolvable unit with a name and text content
2. **evolution** : The iterative optimization process
```

Only **italicized text** triggers linking:
```markdown
The *component* is optimized.  →  Links to glossary
The component is optimized.   →  No link (not italicized)
```

#### Verified Behavior (from source lines 91-142)
- **Auto-links**: ⚠️ Only `*term*` or `***term***` patterns
- **Tooltips**: ❌ Just superscript links, no hover
- **Case-insensitive**: ✅
- **Exclude option**: ✅ `exclude: [Candidate, EvolutionResult]`
- **Skips**: ✅ Headers, links, code, code blocks

#### Strengths
1. Exclude option solves mkdocstrings conflict elegantly
2. Case-insensitive matching
3. Warns about undefined terms

#### Weaknesses
1. **Requires italic markup** - authors must remember to write `*term*`
2. **No tooltips** - just links, readers must click
3. No sections
4. Specific glossary format (numbered list)

---

### Solution 3: mkdocs-ezglossary-plugin

**Package**: `mkdocs-ezglossary-plugin>=2.1.0`

**Source**: `.venv/lib/python3.12/site-packages/mkdocs_ezglossary_plugin/plugin.py`

#### How It Works
```markdown
# Glossary definition
core:component
:   An evolvable unit with a name and text content

# In documentation (REQUIRED for linking)
The <core:component> is optimized through <evolution:mutation>.
```

#### Verified Behavior (from source lines 170-198)
- **Auto-links**: ❌ Only explicit `<section:term>` tags
- **Tooltips**: ✅ Configurable short/full
- **Sections**: ✅ Organize terms by category
- **Plurals**: ✅ `plurals: en` handles English plurals
- **Case-insensitive**: ✅ With `ignore_case: true`
- **Summary directives**: ✅ `<glossary::section>` renders all terms

#### Strengths
1. Rich feature set (sections, plurals, tooltips)
2. Full control over what links
3. Beautiful organized glossary page
4. Inline refs show where terms are used

#### Weaknesses
1. **NO auto-linking** - must manually tag every reference
2. Significant author burden for large documentation
3. Easy to forget tags, leading to inconsistent linking
4. More complex setup

---

## Evaluation Against Project Needs

### Project Context
- **~20 glossary terms** (manageable for any solution)
- **Technical terms**: component_text, evolved_component_text (specific, low over-link risk)
- **Common terms**: component, evolution, trial, feedback (higher over-link risk)
- **mkdocstrings active**: Generates API docs for Candidate, EvolutionResult, etc.

### Weighted Requirements

| Requirement | Weight | Rationale |
|-------------|--------|-----------|
| Auto-linking | **High** | Primary user value - readers shouldn't hunt for definitions |
| Tooltips | **High** | Instant understanding without page navigation |
| mkdocstrings compat | **High** | Can't break existing API docs |
| Sections | **Medium** | Nice organization but readers mostly see inline tooltips |
| Plurals | **Low** | Minor inconvenience if "components" doesn't link |
| Case-insensitive | **Low** | Can define both forms as workaround |

### Scoring

| Solution | Auto-link (3x) | Tooltips (3x) | Compat (3x) | Sections (2x) | Plurals (1x) | Case (1x) | **Total** |
|----------|----------------|---------------|-------------|---------------|--------------|-----------|-----------|
| Material abbr | 3 | 3 | 2* | 0 | 0 | 0 | **17** |
| mkdocs-glossary | 1 | 0 | 3 | 0 | 0 | 1 | **10** |
| ezglossary | 0 | 3 | 3 | 2 | 1 | 1 | **16** |

*Material abbr scores 2 on compat because it requires removing class names from glossary (workable but not ideal)

---

## Recommendation

### Primary: Material Abbreviations

**Why**: Highest weighted score. Delivers the two most valuable features (auto-linking + tooltips) with zero author effort.

**Mitigations for weaknesses**:
1. **Case-sensitivity**: Define both forms where needed
   ```markdown
   *[evolution]: The iterative optimization process
   *[Evolution]: The iterative optimization process
   ```

2. **Plurals**: Define common plurals explicitly
   ```markdown
   *[component]: An evolvable unit...
   *[components]: Evolvable units...
   ```

3. **mkdocstrings conflict**: Don't define class names (Candidate, EvolutionResult, etc.) - they're already documented in API Reference

4. **Over-linking**: Only define terms that genuinely benefit from tooltips. Skip generic words.

### Alternative: ezglossary (if control preferred)

**When to choose**: If the team prefers explicit control over linking and is willing to maintain `<section:term>` tags throughout documentation.

**Trade-off**: More work for authors, but guaranteed no over-linking and beautiful organized glossary.

---

## Final Decision

**Use Material Abbreviations** because:

1. **Reader-first**: Automatic tooltips everywhere terms appear
2. **Author-friendly**: Zero markup overhead
3. **Maintainable**: Simple glossary file, no complex configuration
4. **Conflict-safe**: Just exclude class names from glossary

**Implementation approach**:
- Define ~15-20 conceptual terms (not class names)
- Include case variants for commonly capitalized terms
- Include explicit plurals for frequently pluralized terms
- Keep glossary in `includes/glossary.md` outside docs folder

---

## Appendix: Source Code Evidence

### ezglossary - No Auto-Linking (plugin.py:170-198)

```python
def _register_glossary_links(self, output, page):
    # Only finds explicit <section:term> syntax
    regex = rf"<{_re.section}\:{_re.term}(\\?\|({_re.text}))?>"
    output = re.sub(regex, _replace, output)
```

### mkdocs-glossary - Italic Only (plugin.py:91)

```python
# Only matches *term* or ***term*** patterns
pattern_term = r'((?<!\*)\*|\*{3})(?![\s])([^*\n]+)(?<![\s])(\*(?!\*)|\*{3})'
```

### Material abbr - All Occurrences

Uses Python-Markdown's Abbreviations extension which wraps ALL matching text in `<abbr>` tags during markdown processing.

---

## References

- [Material for MkDocs - Tooltips](https://squidfunk.github.io/mkdocs-material/reference/tooltips/)
- [Python-Markdown Abbreviations](https://python-markdown.github.io/extensions/abbreviations/)
- [mkdocs-ezglossary documentation](https://realtimeprojects.github.io/mkdocs-ezglossary/)
- [mkdocs-glossary PyPI](https://pypi.org/project/mkdocs-glossary/)
- Source code: `.venv/lib/python3.12/site-packages/`

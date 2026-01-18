# Quickstart: MkDocs Glossary Integration

**Feature**: 036-glossary-integration
**Time to complete**: 5-10 minutes

## Prerequisites

- Python 3.12+
- uv package manager
- Existing gepa-adk development setup

## Step 1: Install the Dependency

```bash
uv add --dev mkdocs-ezglossary-plugin
uv sync
```

## Step 2: Configure MkDocs

Add to `mkdocs.yml`:

```yaml
# In plugins section (add after existing plugins)
plugins:
  - search
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
  # ... rest of existing plugins ...

# In markdown_extensions section (add if not present)
markdown_extensions:
  - def_list
  # ... rest of existing extensions ...
```

## Step 3: Convert Glossary Format

Transform `docs/reference/glossary.md` to definition list format:

**Before (standard Markdown)**:
```markdown
### Component

An evolvable unit with a name and text content.
```

**After (ezglossary format)**:
```markdown
core:component
:   An evolvable unit with a name and text content. Components are the
    fundamental building blocks that the evolution engine optimizes.
```

## Step 4: Add Section Summaries

Replace manual term listings with summary directives:

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

## Step 5: Test the Integration

```bash
# Build docs (should complete without warnings)
uv run mkdocs build

# Serve locally and test tooltips
uv run mkdocs serve
```

Open http://127.0.0.1:8000 and:
1. Navigate to any documentation page
2. Hover over glossary terms to see tooltips
3. Click terms to jump to definitions
4. Verify plural forms link correctly

## Adding New Terms

To add a new glossary term:

1. Open `docs/reference/glossary.md`
2. Add the term in the appropriate section file location:
   ```markdown
   section:new_term
   :   Definition of the new term. Include relevant context
       and cross-references to related concepts.
   ```
3. Reference in docs using: `<section:new_term>`

## Explicit Term References

Use angle bracket syntax to explicitly link to terms:

```markdown
The <core:component_text> is validated before acceptance.

See <model:EvolutionResult> for the complete structure.
```

With custom link text:
```markdown
Each <core:component|evolvable component> has a text value.
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Terms not linking | Check section prefix matches defined sections |
| Build warnings about undefined sections | Add section to `sections:` list in mkdocs.yml |
| Tooltips not appearing | Verify `tooltip: short` is set in config |
| Plurals not recognized | Ensure `plurals: en` is configured |

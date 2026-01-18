# Contracts: MkDocs Glossary Integration

**Feature**: 036-glossary-integration

## Overview

This feature does not define API contracts. It is a documentation infrastructure enhancement with no programmatic interfaces.

## Why No Contracts?

- **No runtime API**: The glossary plugin operates at MkDocs build time only
- **No external integrations**: All functionality is encapsulated within MkDocs
- **Configuration-driven**: Behavior is controlled via mkdocs.yml settings
- **Content-based**: Terms and definitions are Markdown content, not API schemas

## Verification

Feature verification relies on:
1. `uv run mkdocs build` - Build succeeds without warnings
2. `uv run mkdocs serve` - Visual inspection of tooltips and links
3. Manual testing of auto-linking and plural recognition

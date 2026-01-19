# Quickstart: Cross-Platform Encoding Support

**Feature**: 001-cross-platform-encoding
**Date**: 2026-01-18

## Overview

This feature adds automatic encoding-safe logging to prevent `UnicodeEncodeError` on Windows consoles when LLM outputs contain non-ASCII Unicode characters.

## What Changes

### For Library Users

**Nothing changes** - the fix is automatic. All logging in gepa-adk will automatically handle Unicode characters that Windows consoles cannot display.

### For Library Developers

When adding new logging statements that might contain LLM/user content, **no special handling is needed**. The `EncodingSafeProcessor` automatically sanitizes all string values before they reach the console.

```python
# This just works - no special handling needed
import structlog

logger = structlog.get_logger(__name__)

# LLM output with smart quotes? No problem.
logger.info("Proposal preview", text=llm_response[:100])
```

## Quick Verification

To verify encoding safety works:

```python
import structlog

logger = structlog.get_logger(__name__)

# This would crash on Windows cp1252 without the fix:
logger.info("Test", message="Smart \u2018quotes\u2019 and em\u2014dash")

# Output: Test message="Smart 'quotes' and em--dash"
```

## Character Mappings

The processor converts these Unicode characters to ASCII equivalents:

| Input | Output | Character Name |
|-------|--------|----------------|
| `'` `'` | `'` | Smart single quotes |
| `"` `"` | `"` | Smart double quotes |
| `‑` | `-` | Non-breaking hyphen |
| `–` | `-` | En dash |
| `—` | `--` | Em dash |
| `…` | `...` | Ellipsis |

Characters without mappings that can't be encoded are replaced with `?`.

## Related Files

| File | Purpose |
|------|---------|
| `src/gepa_adk/utils/encoding.py` | EncodingSafeProcessor implementation |
| `docs/adr/ADR-011-cross-platform-encoding.md` | Architecture decision |
| `tests/unit/test_encoding.py` | Unit tests |
| `tests/contracts/test_encoding_contract.py` | Protocol compliance tests |

## ADR Reference

See [ADR-011: Cross-Platform Encoding](../../docs/adr/ADR-011-cross-platform-encoding.md) for:
- Full decision rationale
- Alternative approaches considered
- Integration with ADR-008 logging pattern

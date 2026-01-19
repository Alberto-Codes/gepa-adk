# ADR-011: Cross-Platform Encoding Support

> **Status**: Accepted
> **Date**: 2026-01-18
> **Deciders**: gepa-adk maintainers

## Context

When running gepa-adk on Windows, `UnicodeEncodeError` exceptions occur when logging LLM-generated content containing Unicode characters that cannot be encoded to the console's default cp1252 encoding. Common problematic characters include:

- **Smart quotes**: U+2018/U+2019 (single), U+201C/U+201D (double)
- **Dashes**: U+2011 (non-breaking hyphen), U+2013 (en dash), U+2014 (em dash)
- **Other**: U+2026 (ellipsis), U+00A0 (non-breaking space)

LLMs frequently output these characters in their responses, making this a recurring issue for Windows users. This is a known problem affecting many Python projects (Ray, Aider, Loguru) as documented in various GitHub issues.

### Root Cause

Windows consoles default to cp1252 encoding (`sys.stdout.encoding`), which cannot represent many Unicode characters. When Python's print/logging attempts to write these characters, it raises:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2011' in position X
```

### Options Considered

| Option | Description | Verdict |
|--------|-------------|---------|
| `PYTHONIOENCODING` env var | User sets environment variable | Requires user action |
| `sys.stdout.reconfigure()` | Modify stdout at import | Invasive, may break tools |
| structlog `UnicodeEncoder` | Built-in processor | Produces bytes, not strings |
| Custom processor | Encode/decode sanitization | Clean, follows patterns |

## Decision

### Implement EncodingSafeProcessor

Add a custom structlog processor (`EncodingSafeProcessor`) that sanitizes strings before they reach the console renderer using a two-phase strategy:

1. **Smart replacements**: Map common Unicode characters to ASCII equivalents that preserve semantic meaning
2. **Fallback encoding**: Use encode/decode with 'replace' error handler for remaining unencodable characters

### Character Mapping Table

| Unicode | Name | Replacement |
|---------|------|-------------|
| U+2018 | Left single quote | `'` (apostrophe) |
| U+2019 | Right single quote | `'` (apostrophe) |
| U+201C | Left double quote | `"` (quotation mark) |
| U+201D | Right double quote | `"` (quotation mark) |
| U+2011 | Non-breaking hyphen | `-` (hyphen-minus) |
| U+2013 | En dash | `-` (hyphen-minus) |
| U+2014 | Em dash | `--` (double hyphen) |
| U+2026 | Horizontal ellipsis | `...` (three periods) |
| U+00A0 | Non-breaking space | ` ` (regular space) |
| Other | Unencodable | `?` (via 'replace') |

### Processor Position

Place `EncodingSafeProcessor` in the processor chain **before** the renderer:

```
merge_contextvars → add_log_level → TimeStamper → RedactionProcessor → EncodingSafeProcessor → ConsoleRenderer
```

This ensures:
1. All event dict values are sanitized
2. Runs after redaction (don't sanitize before secrets are removed)
3. ConsoleRenderer receives clean, encodable strings

## Implementation

### Location

```
src/gepa_adk/utils/encoding.py    # EncodingSafeProcessor implementation
```

### Usage

```python
import structlog
from gepa_adk.utils.encoding import EncodingSafeProcessor

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        EncodingSafeProcessor(),  # Before renderer
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
```

### Example

```python
# Input (LLM output with smart quotes)
logger.info("LLM said", response="User said 'hello' with — emphasis")

# Output (cp1252 safe)
{"event": "LLM said", "response": "User said 'hello' with -- emphasis"}
```

### Encoding Detection

The processor detects console encoding at initialization:

```python
self.encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
```

- Windows (cp1252): Smart replacements + fallback to `?`
- macOS/Linux (UTF-8): Smart replacements only (most chars pass through)

## Consequences

### Positive

- **Automatic protection**: All log statements automatically sanitized
- **Meaning preserved**: Smart replacements maintain semantic content
- **No user configuration**: Works out of the box
- **Non-invasive**: Doesn't modify global state
- **Cross-platform**: Consistent behavior on all platforms
- **Idempotent**: Safe to process multiple times

### Negative

- **Character loss**: Some Unicode characters are replaced with ASCII
- **Slight overhead**: Additional processing per log event (<1ms)
- **False positives**: UTF-8 consoles get unnecessary replacements for mapped chars

### Neutral

- Follows existing structlog processor pattern
- ~50 lines of code

---

## References

### Related ADRs

- **ADR-008**: Structured Logging Pattern
- **ADR-006**: External Library Integration

### External References

- [Ray Project Issue #59967](https://github.com/ray-project/ray/issues/59967) - Windows cp1252 encoding
- [Loguru Issue #124](https://github.com/Delgan/loguru/issues/124) - Windows UnicodeEncodeError
- [structlog Documentation](https://www.structlog.org/en/stable/processors.html)
- [Python Unicode HOWTO](https://docs.python.org/3/howto/unicode.html)
- [Python UTF-8 Mode](https://docs.python.org/3/using/windows.html#utf-8-mode)

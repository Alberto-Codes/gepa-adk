# Research: Cross-Platform Encoding Support for Logging

**Feature**: 001-cross-platform-encoding
**Date**: 2026-01-18
**Status**: Complete

## Executive Summary

This research addresses UnicodeEncodeError exceptions on Windows when logging LLM-generated content containing non-ASCII Unicode characters (smart quotes, em dashes, non-breaking hyphens). After exploring structlog's built-in options and common solutions used by other projects, the recommended approach is a **custom structlog processor** that sanitizes strings before they reach the console renderer.

## Research Questions

### Q1: What causes UnicodeEncodeError on Windows consoles?

**Finding**: Windows consoles default to cp1252 encoding, which cannot represent many Unicode characters that are common in LLM outputs (U+2011 non-breaking hyphen, U+2018/U+2019 smart quotes, U+2014 em dash). When Python's print/logging attempts to write these characters, it raises `UnicodeEncodeError: 'charmap' codec can't encode character`.

This is a **widespread problem** in 2025-2026, affecting many Python projects:
- [Ray Project Issue #59967](https://github.com/ray-project/ray/issues/59967) - SessionFileHandler uses cp1252 on Windows
- [Aider AI Issues #2769, #2770, #3483](https://github.com/Aider-AI/aider/issues/3483) - UnicodeEncodeError with block characters
- [Loguru Issue #124](https://github.com/Delgan/loguru/issues/124) - charmap codec can't encode characters
- [Python Bug #37111](https://bugs.python.org/issue37111) - Logging inconsistent Unicode handling

**Root Cause**: Python's `io.TextIOWrapper` uses `locale.getencoding()` on Windows, which returns "cp1252". This encoding cannot represent many Unicode characters.

### Q2: Does structlog have a built-in solution?

**Finding**: No. We examined structlog's `.venv` installed package:

#### UnicodeEncoder (structlog.processors)
```python
class UnicodeEncoder:
    def __call__(self, logger, name, event_dict):
        for key, value in event_dict.items():
            if isinstance(value, str):
                event_dict[key] = value.encode(self._encoding, self._errors)  # str → bytes!
        return event_dict
```

**Why it doesn't work:**
1. Produces `bytes`, not sanitized `str`
2. ConsoleRenderer would render bytes as `b'hello'` (ugly repr)
3. Only handles top-level values, not nested structures
4. Default encoding is UTF-8, not console encoding
5. Note in docs: "Not very useful in a Python 3-only world"

#### UnicodeDecoder (structlog.processors)
- Does the opposite (bytes → str)
- Not applicable to this problem

#### BytesLogger (structlog._output)
- Writes bytes directly to `sys.stdout.buffer`
- Would require a bytes-producing renderer
- Doesn't solve the encoding problem, just changes where it occurs

**Conclusion**: structlog has no processor that does encode→decode round-trip to sanitize strings while keeping them as strings.

### Q3: How do other projects solve this?

#### Loguru's Approach
From [Issue #124](https://github.com/Delgan/loguru/issues/124), Loguru's maintainer says "this is not a problem related to Loguru itself" and recommends:
1. `logger.add("file.log", encoding="utf8")` for files
2. `PYTHONIOENCODING=utf-8` environment variable
3. `sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')`

#### Python stdlib logging (3.9+)
From [Python Bug #37111](https://bugs.python.org/issue37111), Python 3.9+ added `encoding` and `errors` parameters to `logging.basicConfig()`. But this only affects file handlers, not console output.

#### sys.stdout.reconfigure() Approach
```python
import sys
sys.stdout.reconfigure(errors='replace')
# or
sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
```

**Pros:**
- Simple one-liner
- Works for all console output

**Cons:**
- Modifies global `sys.stdout` - may break pytest, debuggers, other tools
- `backslashreplace` produces ugly `\u2019` instead of preserving meaning
- Library shouldn't modify global state

#### Environment Variables
- `PYTHONIOENCODING=utf-8:replace`
- `PYTHONUTF8=1` (Python 3.7+)

**Cons:**
- Requires user configuration (spec explicitly forbids this)
- Not portable across all contexts

### Q4: What are the solution options?

| Option | Description | Verdict |
|--------|-------------|---------|
| **A. PYTHONIOENCODING** | User sets env var | ❌ Requires user action |
| **B. sys.stdout.reconfigure()** | Modify stdout at import | ⚠️ Invasive, may break tools |
| **C. structlog UnicodeEncoder** | Built-in processor | ❌ Produces bytes, not strings |
| **D. BytesLogger + custom renderer** | Byte-oriented pipeline | ⚠️ Complex, changes architecture |
| **E. Custom processor** | Encode→decode sanitization | ✅ Clean, follows patterns |

**Decision**: **Option E - Custom Processor**

**Rationale**:
1. Follows ADR-008's processor pipeline pattern
2. Non-invasive - doesn't modify global state
3. Automatic protection - developers can't forget to sanitize
4. Preserves meaning with smart character mappings
5. Library-controlled - no user configuration needed
6. ~15 lines of code

### Q5: How should problematic characters be handled?

**Finding**: Python's codec error handlers provide standard strategies:

| Handler | Behavior | Example |
|---------|----------|---------|
| `replace` | Replace with `?` | `"hello\u2011world"` → `"hello?world"` |
| `backslashreplace` | Replace with `\uXXXX` | `"hello\u2011world"` → `"hello\\u2011world"` |
| `xmlcharrefreplace` | Replace with `&#XXXX;` | `"hello\u2011world"` → `"hello&#8209;world"` |
| `ignore` | Remove character | `"hello\u2011world"` → `"helloworld"` |

**Decision**: Use **character-aware replacement** with fallback to `replace`.

**Rationale**: Per FR-005, preserve meaning by mapping smart characters to ASCII equivalents:
- Smart quotes → Regular quotes (`'` → `'`, `"` → `"`)
- Em dash → Double hyphen (`—` → `--`)
- Non-breaking hyphen → Regular hyphen (`‑` → `-`)
- Other → `?` (replace handler)

### Q6: Where should the sanitization be applied?

**Decision**: Create a custom `EncodingSafeProcessor` placed in the processor chain before ConsoleRenderer:

```
merge_contextvars → add_log_level → TimeStamper → RedactionProcessor → EncodingSafeProcessor → ConsoleRenderer
```

This position ensures:
1. All event dict values are sanitized
2. Runs after redaction (don't want to sanitize before secrets are removed)
3. ConsoleRenderer receives clean, encodable strings

### Q7: Should this require a new ADR?

**Decision**: Yes, create **ADR-011: Cross-Platform Encoding** because:
1. Defines new processor in the logging pipeline (ADR-008 scope)
2. Establishes character mapping conventions
3. Documents cross-platform compatibility requirements
4. Provides guidance for future development

## Technical Design

### EncodingSafeProcessor Implementation

```python
class EncodingSafeProcessor:
    """Sanitize strings for console encoding compatibility.

    This processor ensures all string values in the event dict can be
    safely written to the console regardless of its encoding (cp1252
    on Windows, UTF-8 on macOS/Linux).

    The sanitization strategy:
    1. Apply smart character replacements (preserve meaning)
    2. Encode to console encoding with 'replace' error handler
    3. Decode back to string

    This produces strings that are guaranteed to be writable to the
    console without raising UnicodeEncodeError.
    """

    # Smart character replacements (preserve meaning)
    REPLACEMENTS = {
        '\u2018': "'",   # Left single quote
        '\u2019': "'",   # Right single quote
        '\u201c': '"',   # Left double quote
        '\u201d': '"',   # Right double quote
        '\u2011': '-',   # Non-breaking hyphen
        '\u2013': '-',   # En dash
        '\u2014': '--',  # Em dash
        '\u2026': '...', # Ellipsis
        '\u00a0': ' ',   # Non-breaking space
    }

    def __init__(self):
        import sys
        self.encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'

    def __call__(self, logger, method_name, event_dict):
        return self._sanitize_dict(event_dict)

    def _sanitize_string(self, s: str) -> str:
        # Apply smart replacements first
        for char, replacement in self.REPLACEMENTS.items():
            s = s.replace(char, replacement)
        # Encode/decode with replace for any remaining unencodable chars
        return s.encode(self.encoding, errors='replace').decode(self.encoding)

    def _sanitize_value(self, value):
        if isinstance(value, str):
            return self._sanitize_string(value)
        elif isinstance(value, dict):
            return self._sanitize_dict(value)
        elif isinstance(value, (list, tuple)):
            return type(value)(self._sanitize_value(v) for v in value)
        return value

    def _sanitize_dict(self, d: dict) -> dict:
        return {k: self._sanitize_value(v) for k, v in d.items()}
```

### Processor Chain Integration

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        # RedactionProcessor(),      # If present
        EncodingSafeProcessor(),     # NEW - before renderer
        structlog.dev.ConsoleRenderer(),
    ],
    ...
)
```

## Impact Assessment

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `src/gepa_adk/utils/encoding.py` | NEW | EncodingSafeProcessor implementation |
| `src/gepa_adk/api.py` or entry point | MODIFY | Add processor to chain |
| `docs/adr/ADR-011-cross-platform-encoding.md` | NEW | Document decision |

### Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | Processor sanitizes problematic characters correctly |
| Unit | Nested dicts/lists sanitized recursively |
| Unit | Non-string values pass through unchanged |
| Contract | Processor implements structlog processor protocol |
| Integration | Log statements with Unicode don't raise on Windows |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance overhead | Low | Low | Encoding check is O(n) on string length |
| Character loss | Medium | Low | Use smart replacements, not just replace |
| Console detection failure | Low | Low | Fall back to UTF-8 |

## Recommendations

1. **Implement EncodingSafeProcessor** as a custom structlog processor in `src/gepa_adk/utils/encoding.py`

2. **Create ADR-011** documenting cross-platform encoding requirements and processor design

3. **Integrate into logging configuration** at application entry point

4. **Add comprehensive tests** covering all character mappings and edge cases

5. **Consider upstreaming** - This is a common problem; consider contributing to structlog or publishing as a standalone package

## References

### structlog Documentation
- [structlog Processors](https://www.structlog.org/en/stable/processors.html)
- [structlog API Reference](https://www.structlog.org/en/stable/api.html)

### Related GitHub Issues
- [Ray Project #59967](https://github.com/ray-project/ray/issues/59967) - Windows cp1252 encoding
- [Loguru #124](https://github.com/Delgan/loguru/issues/124) - Windows UnicodeEncodeError
- [structlog #94](https://github.com/hynek/structlog/issues/94) - UTF-8 printing
- [Aider #3483](https://github.com/Aider-AI/aider/issues/3483) - cp1252 encoding errors
- [Python #37111](https://bugs.python.org/issue37111) - Logging Unicode handling

### Python Documentation
- [Unicode HOWTO](https://docs.python.org/3/howto/unicode.html)
- [Python UTF-8 Mode](https://docs.python.org/3/using/windows.html#utf-8-mode)
- [sys.stdout.reconfigure](https://docs.python.org/3/library/sys.html)

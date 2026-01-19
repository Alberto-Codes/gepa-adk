# Data Model: Cross-Platform Encoding Support

**Feature**: 001-cross-platform-encoding
**Date**: 2026-01-18
**Status**: Complete

## Overview

This feature introduces minimal data structures focused on encoding transformation. The primary entity is the `EncodingSafeProcessor` class that operates on structlog event dictionaries.

## Entities

### EncodingSafeProcessor

**Purpose**: A structlog processor that sanitizes string values in event dictionaries to prevent encoding errors on consoles with limited encoding support (e.g., Windows cp1252).

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `encoding` | `str` | Target encoding detected from `sys.stdout.encoding` (e.g., "cp1252", "utf-8") |
| `REPLACEMENTS` | `dict[str, str]` | Class constant mapping Unicode characters to ASCII equivalents |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `__call__` | `(logger, method_name, event_dict) -> EventDict` | structlog processor protocol |
| `_sanitize_string` | `(s: str) -> str` | Sanitize a single string |
| `_sanitize_value` | `(value: Any) -> Any` | Recursively sanitize any value |

**State Transitions**: None (stateless processor)

### Character Replacement Map

**Purpose**: Mapping of common problematic Unicode characters to ASCII equivalents, preserving semantic meaning.

| Unicode | Name | Replacement | Rationale |
|---------|------|-------------|-----------|
| `\u2018` | Left Single Quote | `'` | Preserve quotation |
| `\u2019` | Right Single Quote | `'` | Preserve quotation |
| `\u201c` | Left Double Quote | `"` | Preserve quotation |
| `\u201d` | Right Double Quote | `"` | Preserve quotation |
| `\u2011` | Non-Breaking Hyphen | `-` | Preserve hyphenation |
| `\u2013` | En Dash | `-` | Preserve range/dash |
| `\u2014` | Em Dash | `--` | Preserve emphasis dash |
| `\u2026` | Horizontal Ellipsis | `...` | Preserve ellipsis |
| `\u00a0` | Non-Breaking Space | ` ` | Preserve spacing |

### Event Dictionary (structlog)

**Purpose**: Standard structlog event dictionary passed through the processor chain.

**Structure** (after processing):

```python
{
    "event": str,           # Log message (sanitized)
    "level": str,           # Log level (unchanged)
    "timestamp": str,       # ISO timestamp (unchanged)
    "logger": str,          # Logger name (unchanged)
    # ... additional fields (sanitized if string)
}
```

**Validation Rules**:
- All string values are encoding-safe for target console
- Non-string values pass through unchanged
- Nested structures (dict, list) are recursively processed

## Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                     structlog Pipeline                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Event Dict ──► Processors ──► EncodingSafeProcessor ──► Renderer
│                                       │                          │
│                                       ▼                          │
│                           ┌─────────────────────┐                │
│                           │ Character Mapping   │                │
│                           │ ─────────────────── │                │
│                           │ Smart → ASCII       │                │
│                           │ + fallback replace  │                │
│                           └─────────────────────┘                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Integration Points

### structlog Processor Protocol

The processor must satisfy the structlog processor callable protocol:

```python
from typing import Any, MutableMapping
from structlog.typing import EventDict, WrappedLogger

class EncodingSafeProcessor:
    def __call__(
        self,
        logger: WrappedLogger,
        method_name: str,
        event_dict: EventDict,
    ) -> EventDict:
        ...
```

### Logging Configuration

Integration point in the structlog configuration (per ADR-008):

```python
# Position in processor chain (after redaction, before rendering)
processors=[
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    # RedactionProcessor(),      # If present
    EncodingSafeProcessor(),     # NEW
    structlog.dev.ConsoleRenderer(),
]
```

## Data Invariants

1. **Encoding Detection**: `self.encoding` is always a valid Python codec name
2. **Replacement Map**: All keys are single Unicode characters, all values are ASCII-only
3. **Idempotence**: Processing an already-sanitized string produces the same result
4. **Type Preservation**: Non-string types pass through unchanged (int, float, bool, None)

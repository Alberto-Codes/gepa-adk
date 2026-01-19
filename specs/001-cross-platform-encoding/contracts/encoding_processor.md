# Contract: EncodingSafeProcessor

**Feature**: 001-cross-platform-encoding
**Date**: 2026-01-18
**Type**: structlog Processor Protocol

## Protocol Definition

The `EncodingSafeProcessor` must satisfy the structlog processor callable protocol.

### Signature

```python
from typing import Any, MutableMapping
from structlog.typing import EventDict, WrappedLogger

class EncodingSafeProcessor:
    """Processor that sanitizes strings for console encoding compatibility."""

    def __call__(
        self,
        logger: WrappedLogger,
        method_name: str,
        event_dict: EventDict,
    ) -> EventDict:
        """Process event dictionary, sanitizing all string values.

        Args:
            logger: The wrapped logger instance.
            method_name: Name of the log method called (e.g., "info", "debug").
            event_dict: Mutable mapping of log event data.

        Returns:
            The same event_dict with all string values sanitized for
            console encoding compatibility.
        """
        ...
```

## Contract Tests

### CT-001: Processor Protocol Compliance

```python
def test_processor_is_callable():
    """EncodingSafeProcessor must be callable."""
    processor = EncodingSafeProcessor()
    assert callable(processor)


def test_processor_returns_event_dict():
    """Processor must return the event dictionary."""
    processor = EncodingSafeProcessor()
    event_dict = {"event": "test", "key": "value"}
    result = processor(None, "info", event_dict)
    assert isinstance(result, dict)
    assert "event" in result
```

### CT-002: String Sanitization

```python
def test_sanitizes_smart_quotes():
    """Smart quotes must be replaced with ASCII equivalents."""
    processor = EncodingSafeProcessor()
    event_dict = {"event": "User said \u2018hello\u2019"}
    result = processor(None, "info", event_dict)
    assert result["event"] == "User said 'hello'"


def test_sanitizes_em_dash():
    """Em dash must be replaced with double hyphen."""
    processor = EncodingSafeProcessor()
    event_dict = {"event": "First \u2014 Second"}
    result = processor(None, "info", event_dict)
    assert result["event"] == "First -- Second"


def test_sanitizes_non_breaking_hyphen():
    """Non-breaking hyphen must be replaced with regular hyphen."""
    processor = EncodingSafeProcessor()
    event_dict = {"event": "non\u2011breaking"}
    result = processor(None, "info", event_dict)
    assert result["event"] == "non-breaking"
```

### CT-003: Nested Structure Handling

```python
def test_sanitizes_nested_dicts():
    """Nested dictionaries must be recursively sanitized."""
    processor = EncodingSafeProcessor()
    event_dict = {
        "event": "test",
        "data": {"message": "Smart \u2018quote\u2019"},
    }
    result = processor(None, "info", event_dict)
    assert result["data"]["message"] == "Smart 'quote'"


def test_sanitizes_lists():
    """Lists must be recursively sanitized."""
    processor = EncodingSafeProcessor()
    event_dict = {
        "event": "test",
        "items": ["Item \u2014 one", "Item \u2014 two"],
    }
    result = processor(None, "info", event_dict)
    assert result["items"][0] == "Item -- one"
    assert result["items"][1] == "Item -- two"
```

### CT-004: Type Preservation

```python
def test_preserves_non_string_types():
    """Non-string types must pass through unchanged."""
    processor = EncodingSafeProcessor()
    event_dict = {
        "event": "test",
        "count": 42,
        "ratio": 3.14,
        "enabled": True,
        "data": None,
    }
    result = processor(None, "info", event_dict)
    assert result["count"] == 42
    assert result["ratio"] == 3.14
    assert result["enabled"] is True
    assert result["data"] is None
```

### CT-005: Encoding Fallback

```python
def test_replaces_unmapped_unencodable_chars(monkeypatch):
    """Characters not in mapping but unencodable should be replaced."""
    # Simulate cp1252 encoding
    processor = EncodingSafeProcessor()
    processor.encoding = "cp1252"

    # U+2122 (™) is not in our mapping but can't encode to cp1252
    event_dict = {"event": "Product\u2122"}
    result = processor(None, "info", event_dict)
    # Should use replace error handler (? character)
    assert "\u2122" not in result["event"]
```

### CT-006: Idempotence

```python
def test_idempotent_processing():
    """Processing already-sanitized strings should produce same result."""
    processor = EncodingSafeProcessor()
    event_dict = {"event": "Already ASCII safe"}

    result1 = processor(None, "info", event_dict.copy())
    result2 = processor(None, "info", result1.copy())

    assert result1 == result2
```

## Error Handling

### EH-001: Invalid Event Dict

```python
def test_handles_empty_event_dict():
    """Empty event dict should pass through."""
    processor = EncodingSafeProcessor()
    result = processor(None, "info", {})
    assert result == {}


def test_handles_none_values():
    """None values in event dict should pass through."""
    processor = EncodingSafeProcessor()
    event_dict = {"event": "test", "optional": None}
    result = processor(None, "info", event_dict)
    assert result["optional"] is None
```

## Performance Requirements

- Processing a typical log event (<100 string characters total) must complete in <1ms
- Memory allocation should be O(n) where n is total string content length
- No blocking I/O operations in the processor

## Integration Verification

The processor integrates with structlog's processor chain. Verify with:

```python
import structlog

def test_integration_with_structlog():
    """Processor works in real structlog pipeline."""
    from gepa_adk.utils.encoding import EncodingSafeProcessor

    captured_events = []

    def capture_processor(logger, method_name, event_dict):
        captured_events.append(event_dict.copy())
        return event_dict

    structlog.configure(
        processors=[
            EncodingSafeProcessor(),
            capture_processor,
        ],
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=False,
    )

    logger = structlog.get_logger()
    logger.info("Test with \u2018smart quotes\u2019")

    assert len(captured_events) == 1
    assert captured_events[0]["event"] == "Test with 'smart quotes'"
```

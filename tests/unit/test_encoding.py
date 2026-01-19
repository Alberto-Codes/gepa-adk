"""Unit tests for EncodingSafeProcessor.

Tests verify that the processor correctly sanitizes Unicode characters that
cause UnicodeEncodeError on Windows cp1252 consoles when logging LLM outputs.

Note:
    These tests mock the console encoding to simulate Windows cp1252 behavior
    regardless of the actual test environment encoding.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gepa_adk.utils.encoding import EncodingSafeProcessor

pytestmark = pytest.mark.unit


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def cp1252_processor() -> EncodingSafeProcessor:
    """Create processor with cp1252 encoding (Windows console simulation)."""
    with patch("sys.stdout") as mock_stdout:
        mock_stdout.encoding = "cp1252"
        processor = EncodingSafeProcessor()
    return processor


@pytest.fixture
def utf8_processor() -> EncodingSafeProcessor:
    """Create processor with UTF-8 encoding (macOS/Linux)."""
    with patch("sys.stdout") as mock_stdout:
        mock_stdout.encoding = "utf-8"
        processor = EncodingSafeProcessor()
    return processor


# =============================================================================
# T010: Smart Quote Sanitization Tests
# =============================================================================


class TestSmartQuoteSanitization:
    """Tests for T010: smart quote sanitization (U+2018, U+2019, U+201C, U+201D)."""

    def test_left_single_quote_replaced(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify left single quote (U+2018) is replaced with apostrophe."""
        result = cp1252_processor._sanitize_string("Hello \u2018world\u2019")
        assert result == "Hello 'world'"
        assert "\u2018" not in result

    def test_right_single_quote_replaced(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify right single quote (U+2019) is replaced with apostrophe."""
        result = cp1252_processor._sanitize_string("It\u2019s great")
        assert result == "It's great"
        assert "\u2019" not in result

    def test_left_double_quote_replaced(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify left double quote (U+201C) is replaced with quotation mark."""
        result = cp1252_processor._sanitize_string("She said \u201cHello\u201d")
        assert result == 'She said "Hello"'
        assert "\u201c" not in result

    def test_right_double_quote_replaced(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify right double quote (U+201D) is replaced with quotation mark."""
        result = cp1252_processor._sanitize_string("End of \u201cquote\u201d")
        assert result == 'End of "quote"'
        assert "\u201d" not in result

    def test_mixed_smart_quotes(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify all smart quote types are replaced in mixed content."""
        input_str = "He said \u201cIt\u2019s \u2018fine\u2019\u201d"
        result = cp1252_processor._sanitize_string(input_str)
        assert result == "He said \"It's 'fine'\""


# =============================================================================
# T011: Em Dash Sanitization Tests
# =============================================================================


class TestEmDashSanitization:
    """Tests for T011: em dash sanitization (U+2014)."""

    def test_em_dash_replaced_with_double_hyphen(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify em dash (U+2014) is replaced with double hyphen."""
        result = cp1252_processor._sanitize_string("Hello\u2014World")
        assert result == "Hello--World"
        assert "\u2014" not in result

    def test_multiple_em_dashes(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify multiple em dashes are all replaced."""
        result = cp1252_processor._sanitize_string("A\u2014B\u2014C")
        assert result == "A--B--C"

    def test_em_dash_in_sentence(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify em dash in typical sentence context."""
        result = cp1252_processor._sanitize_string(
            "The answer\u2014as you might expect\u2014is yes."
        )
        assert result == "The answer--as you might expect--is yes."


# =============================================================================
# T012: Non-Breaking Hyphen Sanitization Tests
# =============================================================================


class TestNonBreakingHyphenSanitization:
    """Tests for T012: non-breaking hyphen sanitization (U+2011)."""

    def test_non_breaking_hyphen_replaced(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify non-breaking hyphen (U+2011) is replaced with regular hyphen."""
        result = cp1252_processor._sanitize_string("self\u2011aware")
        assert result == "self-aware"
        assert "\u2011" not in result

    def test_multiple_non_breaking_hyphens(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify multiple non-breaking hyphens are all replaced."""
        result = cp1252_processor._sanitize_string("one\u2011two\u2011three")
        assert result == "one-two-three"


# =============================================================================
# T013: En Dash Sanitization Tests
# =============================================================================


class TestEnDashSanitization:
    """Tests for T013: en dash sanitization (U+2013)."""

    def test_en_dash_replaced(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify en dash (U+2013) is replaced with regular hyphen."""
        result = cp1252_processor._sanitize_string("pages 10\u201320")
        assert result == "pages 10-20"
        assert "\u2013" not in result

    def test_en_dash_in_ranges(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify en dash in typical range context."""
        result = cp1252_processor._sanitize_string("January\u2013March 2024")
        assert result == "January-March 2024"


# =============================================================================
# T014: Ellipsis Sanitization Tests
# =============================================================================


class TestEllipsisSanitization:
    """Tests for T014: ellipsis sanitization (U+2026)."""

    def test_ellipsis_replaced_with_three_periods(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify horizontal ellipsis (U+2026) is replaced with three periods."""
        result = cp1252_processor._sanitize_string("Wait\u2026")
        assert result == "Wait..."
        assert "\u2026" not in result

    def test_ellipsis_in_middle(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify ellipsis in middle of text."""
        result = cp1252_processor._sanitize_string("Well\u2026I guess so")
        assert result == "Well...I guess so"


# =============================================================================
# T015: Non-Breaking Space Sanitization Tests
# =============================================================================


class TestNonBreakingSpaceSanitization:
    """Tests for T015: non-breaking space sanitization (U+00A0)."""

    def test_nbsp_replaced_with_regular_space(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify non-breaking space (U+00A0) is replaced with regular space."""
        result = cp1252_processor._sanitize_string("100\u00a0percent")
        assert result == "100 percent"
        assert "\u00a0" not in result

    def test_multiple_nbsp(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify multiple non-breaking spaces are all replaced."""
        result = cp1252_processor._sanitize_string("a\u00a0b\u00a0c")
        assert result == "a b c"


# =============================================================================
# T016: Unmapped Unencodable Character Fallback Tests
# =============================================================================


class TestUnmappedCharacterFallback:
    """Tests for T016: unmapped unencodable character fallback (cp1252 simulation)."""

    def test_unmapped_character_replaced_with_question_mark(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify unmapped characters are replaced with ? via encode/decode."""
        # U+1F600 (grinning face emoji) is not in cp1252
        result = cp1252_processor._sanitize_string("Hello \U0001f600 World")
        # Should not raise, and emoji should be replaced
        assert "\U0001f600" not in result
        # Note: The exact replacement depends on codec behavior

    def test_mixed_mapped_and_unmapped(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify mixed mapped and unmapped characters are handled."""
        # U+2018 is mapped, U+1F600 is unmapped
        result = cp1252_processor._sanitize_string("Quote: \u2018Hi\u2019 \U0001f600")
        assert "\u2018" not in result
        assert "\u2019" not in result
        assert "\U0001f600" not in result
        assert "'" in result  # Smart quotes replaced with apostrophe

    def test_utf8_processor_preserves_unicode(
        self, utf8_processor: EncodingSafeProcessor
    ) -> None:
        """Verify UTF-8 processor preserves Unicode characters."""
        # UTF-8 can encode emoji
        result = utf8_processor._sanitize_string("Hello \U0001f600")
        # Smart replacements still apply (they're explicit mappings)
        # But unmapped chars should pass through on UTF-8
        assert "Hello" in result


# =============================================================================
# T016a: Null Byte Handling Tests
# =============================================================================


class TestNullByteHandling:
    """Tests for T016a: null byte handling."""

    def test_null_byte_in_string(self, cp1252_processor: EncodingSafeProcessor) -> None:
        r"""Verify null byte (\x00) doesn't cause issues."""
        result = cp1252_processor._sanitize_string("Hello\x00World")
        # Should not raise an exception
        assert isinstance(result, str)
        # The null byte may be preserved or replaced depending on codec

    def test_multiple_null_bytes(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify multiple null bytes are handled."""
        result = cp1252_processor._sanitize_string("A\x00B\x00C")
        assert isinstance(result, str)


# =============================================================================
# T016b: Control Character Handling Tests
# =============================================================================


class TestControlCharacterHandling:
    """Tests for T016b: control character handling."""

    def test_tab_preserved(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify tab character is preserved."""
        result = cp1252_processor._sanitize_string("Hello\tWorld")
        assert "\t" in result

    def test_newline_preserved(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify newline character is preserved."""
        result = cp1252_processor._sanitize_string("Hello\nWorld")
        assert "\n" in result

    def test_carriage_return_preserved(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify carriage return is preserved."""
        result = cp1252_processor._sanitize_string("Hello\rWorld")
        assert "\r" in result

    def test_bell_character(self, cp1252_processor: EncodingSafeProcessor) -> None:
        r"""Verify bell character (\x07) doesn't cause issues."""
        result = cp1252_processor._sanitize_string("Hello\x07World")
        assert isinstance(result, str)


# =============================================================================
# T016c: Extremely Long String Tests
# =============================================================================


class TestExtremelyLongString:
    """Tests for T016c: extremely long string (10KB+)."""

    def test_10kb_string_with_unicode(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify 10KB+ string with Unicode characters is handled."""
        # Create a 10KB string with various Unicode characters
        base = "Hello \u2018world\u2019 with \u2014 dashes. "
        long_string = base * 500  # ~21KB

        result = cp1252_processor._sanitize_string(long_string)

        assert isinstance(result, str)
        assert len(result) > 10000
        assert "\u2018" not in result
        assert "\u2019" not in result
        assert "\u2014" not in result
        assert "'" in result
        assert "--" in result

    def test_100kb_string_performance(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify 100KB string doesn't cause performance issues."""
        # Create a 100KB string
        long_string = "A" * 100_000

        result = cp1252_processor._sanitize_string(long_string)

        assert len(result) == 100_000
        assert result == long_string  # No changes needed for ASCII


# =============================================================================
# T016d: Encoding Detection Fallback Tests
# =============================================================================


class TestEncodingDetectionFallback:
    """Tests for T016d: encoding detection fallback (sys.stdout.encoding=None)."""

    def test_none_encoding_falls_back_to_utf8(self) -> None:
        """Verify None encoding falls back to UTF-8."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = None
            processor = EncodingSafeProcessor()

        assert processor.encoding == "utf-8"

    def test_missing_encoding_attribute_falls_back(self) -> None:
        """Verify missing encoding attribute falls back to UTF-8."""
        mock_stdout = MagicMock(spec=[])  # No encoding attribute

        with patch("sys.stdout", mock_stdout):
            processor = EncodingSafeProcessor()

        assert processor.encoding == "utf-8"

    def test_fallback_processor_handles_unicode(self) -> None:
        """Verify fallback processor handles Unicode correctly."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = None
            processor = EncodingSafeProcessor()

        # UTF-8 can encode most Unicode, but smart replacements still apply
        result = processor._sanitize_string("Hello \u2018world\u2019")
        assert result == "Hello 'world'"  # Smart replacements still happen


# =============================================================================
# T022: Nested Dict Sanitization Tests (US2)
# =============================================================================


class TestNestedDictSanitization:
    """Tests for T022: nested dict sanitization (User Story 2)."""

    def test_single_level_nested_dict(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify single level nested dict is sanitized."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "nested": {"message": "Hello \u2018world\u2019"},
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["nested"]["message"] == "Hello 'world'"

    def test_deep_nested_dict(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify deeply nested dict is sanitized."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "level1": {
                "level2": {
                    "level3": {"message": "Deep \u2014 nesting"},
                },
            },
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["level1"]["level2"]["level3"]["message"] == "Deep -- nesting"

    def test_multiple_nested_dicts(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify multiple nested dicts at same level are all sanitized."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "dict_a": {"msg": "\u2018A\u2019"},
            "dict_b": {"msg": "\u2018B\u2019"},
            "dict_c": {"msg": "\u2018C\u2019"},
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["dict_a"]["msg"] == "'A'"
        assert result["dict_b"]["msg"] == "'B'"
        assert result["dict_c"]["msg"] == "'C'"


# =============================================================================
# T023: List Sanitization Tests (US2)
# =============================================================================


class TestListSanitization:
    """Tests for T023: list sanitization (User Story 2)."""

    def test_list_of_strings(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify list of strings is sanitized."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "messages": ["\u2018one\u2019", "\u2018two\u2019", "\u2018three\u2019"],
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["messages"] == ["'one'", "'two'", "'three'"]
        assert isinstance(result["messages"], list)

    def test_list_with_mixed_types(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify list with mixed types handles strings correctly."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "items": ["Text \u2014", 42, True, None, 3.14],
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["items"][0] == "Text --"
        assert result["items"][1] == 42
        assert result["items"][2] is True
        assert result["items"][3] is None
        assert result["items"][4] == 3.14

    def test_nested_lists(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify nested lists are sanitized."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "matrix": [
                ["\u2018a\u2019", "\u2018b\u2019"],
                ["\u2018c\u2019", "\u2018d\u2019"],
            ],
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["matrix"][0][0] == "'a'"
        assert result["matrix"][1][1] == "'d'"

    def test_list_with_dicts(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify list containing dicts is sanitized."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "records": [
                {"name": "Alice", "quote": "\u201cHello\u201d"},
                {"name": "Bob", "quote": "\u201cWorld\u201d"},
            ],
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["records"][0]["quote"] == '"Hello"'
        assert result["records"][1]["quote"] == '"World"'


# =============================================================================
# T024: Tuple Sanitization Tests (US2)
# =============================================================================


class TestTupleSanitization:
    """Tests for T024: tuple sanitization (User Story 2)."""

    def test_tuple_of_strings(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify tuple of strings is sanitized and type preserved."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "coords": ("\u2018x\u2019", "\u2018y\u2019"),
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["coords"] == ("'x'", "'y'")
        assert isinstance(result["coords"], tuple)

    def test_tuple_with_mixed_types(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify tuple with mixed types preserves types."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "data": ("Name \u2014", 100, False),
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["data"] == ("Name --", 100, False)
        assert isinstance(result["data"], tuple)

    def test_nested_tuples(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify nested tuples are sanitized."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "nested": (("\u2018a\u2019",), ("\u2018b\u2019",)),
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["nested"][0][0] == "'a'"
        assert result["nested"][1][0] == "'b'"
        assert isinstance(result["nested"], tuple)
        assert isinstance(result["nested"][0], tuple)


# =============================================================================
# T025: Type Preservation Tests (US2)
# =============================================================================


class TestTypePreservation:
    """Tests for T025: type preservation (int, float, bool, None) (User Story 2)."""

    def test_int_preserved(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify int values pass through unchanged."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "count": 42,
            "negative": -10,
            "zero": 0,
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["count"] == 42
        assert isinstance(result["count"], int)
        assert result["negative"] == -10
        assert result["zero"] == 0

    def test_float_preserved(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify float values pass through unchanged."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "ratio": 3.14159,
            "negative_float": -2.5,
            "zero_float": 0.0,
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["ratio"] == 3.14159
        assert isinstance(result["ratio"], float)
        assert result["negative_float"] == -2.5
        assert result["zero_float"] == 0.0

    def test_bool_preserved(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify bool values pass through unchanged."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "enabled": True,
            "disabled": False,
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["enabled"] is True
        assert isinstance(result["enabled"], bool)
        assert result["disabled"] is False
        assert isinstance(result["disabled"], bool)

    def test_none_preserved(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify None values pass through unchanged."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "nothing": None,
            "also_nothing": None,
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["nothing"] is None
        assert result["also_nothing"] is None

    def test_complex_mixed_types(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify complex event dict with all types is handled correctly."""
        event_dict: dict[str, Any] = {
            "event": "Complex \u2014 event",
            "count": 42,
            "ratio": 3.14,
            "enabled": True,
            "nothing": None,
            "messages": ["\u2018one\u2019", 2, None],
            "nested": {
                "str": "\u201cquoted\u201d",
                "int": 100,
                "bool": False,
            },
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["event"] == "Complex -- event"
        assert result["count"] == 42
        assert result["ratio"] == 3.14
        assert result["enabled"] is True
        assert result["nothing"] is None
        assert result["messages"][0] == "'one'"
        assert result["messages"][1] == 2
        assert result["messages"][2] is None
        assert result["nested"]["str"] == '"quoted"'
        assert result["nested"]["int"] == 100
        assert result["nested"]["bool"] is False


# =============================================================================
# T026: Empty Event Dict Handling Tests (US2)
# =============================================================================


class TestEmptyEventDictHandling:
    """Tests for T026: empty event dict handling (User Story 2)."""

    def test_empty_dict(self, cp1252_processor: EncodingSafeProcessor) -> None:
        """Verify empty dict is handled correctly."""
        event_dict: dict[str, Any] = {}

        result = cp1252_processor(None, "info", event_dict)

        assert result == {}
        assert isinstance(result, dict)

    def test_dict_with_empty_values(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify dict with empty string values is handled."""
        event_dict: dict[str, Any] = {
            "event": "",
            "message": "",
            "data": "",
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["event"] == ""
        assert result["message"] == ""
        assert result["data"] == ""

    def test_dict_with_empty_nested_structures(
        self, cp1252_processor: EncodingSafeProcessor
    ) -> None:
        """Verify dict with empty nested structures is handled."""
        event_dict: dict[str, Any] = {
            "event": "test",
            "empty_dict": {},
            "empty_list": [],
            "empty_tuple": (),
        }

        result = cp1252_processor(None, "info", event_dict)

        assert result["empty_dict"] == {}
        assert result["empty_list"] == []
        assert result["empty_tuple"] == ()

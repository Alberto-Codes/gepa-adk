"""Unit tests for CriticScorer._extract_json_from_text().

Direct unit tests for the JSON extraction fallback chain: direct parse,
markdown code block extraction, brace-matching, and final fallback.

Note:
    Tests call the private method directly to isolate extraction logic
    from the async scoring pipeline.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters.scoring.critic_scorer import CriticScorer

pytestmark = pytest.mark.unit


@pytest.fixture
def scorer() -> CriticScorer:
    """Create a minimal CriticScorer for testing extraction."""
    agent = LlmAgent(
        name="test_critic",
        model="gemini-2.5-flash",
        instruction="Test critic",
    )
    executor = MagicMock()
    session_service = MagicMock()
    session = MagicMock()
    session.id = "test_session"
    session_service.create_session = MagicMock(return_value=session)
    return CriticScorer(
        critic_agent=agent,
        executor=executor,
        session_service=session_service,
        app_name="test_app",
    )


class TestDirectJsonParse:
    """Path 1: text is already valid JSON."""

    def test_plain_json_object(self, scorer: CriticScorer) -> None:
        """Valid JSON object returns stripped text."""
        text = '{"score": 0.8, "feedback": "Good"}'
        assert scorer._extract_json_from_text(text) == text

    def test_json_with_whitespace(self, scorer: CriticScorer) -> None:
        """JSON with surrounding whitespace is stripped."""
        text = '  {"score": 0.5}  \n'
        assert scorer._extract_json_from_text(text) == '{"score": 0.5}'

    def test_json_array(self, scorer: CriticScorer) -> None:
        """Valid JSON array returns stripped text."""
        text = "[1, 2, 3]"
        assert scorer._extract_json_from_text(text) == text


class TestMarkdownCodeBlockExtraction:
    """Path 2: JSON inside markdown code blocks."""

    def test_json_fenced_block(self, scorer: CriticScorer) -> None:
        """Extract JSON from ```json ... ``` block."""
        text = 'Here is the result:\n```json\n{"score": 0.9}\n```\n'
        assert scorer._extract_json_from_text(text) == '{"score": 0.9}'

    def test_plain_fenced_block(self, scorer: CriticScorer) -> None:
        """Extract JSON from ``` ... ``` block without language tag."""
        text = 'Output:\n```\n{"score": 0.6}\n```'
        assert scorer._extract_json_from_text(text) == '{"score": 0.6}'

    def test_multiple_blocks_first_valid_wins(self, scorer: CriticScorer) -> None:
        """When multiple code blocks exist, first valid JSON wins."""
        text = '```\nnot json\n```\n```json\n{"score": 0.7}\n```\n'
        assert scorer._extract_json_from_text(text) == '{"score": 0.7}'

    def test_invalid_block_skipped(self, scorer: CriticScorer) -> None:
        """Non-JSON code block is skipped, falls through to next path."""
        text = "```\nthis is not json\n```"
        # Should fall through to brace-matching (no braces) then fallback
        result = scorer._extract_json_from_text(text)
        assert result == text


class TestBraceMatchingExtraction:
    """Path 3: JSON embedded in surrounding prose."""

    def test_json_in_prose(self, scorer: CriticScorer) -> None:
        """Extract JSON object embedded in surrounding text."""
        text = 'The evaluation result is {"score": 0.85} based on criteria.'
        assert scorer._extract_json_from_text(text) == '{"score": 0.85}'

    def test_nested_braces(self, scorer: CriticScorer) -> None:
        """Extract JSON with nested objects via brace depth tracking."""
        text = 'Result: {"score": 0.9, "meta": {"detail": "ok"}} done.'
        expected = '{"score": 0.9, "meta": {"detail": "ok"}}'
        assert scorer._extract_json_from_text(text) == expected

    def test_invalid_brace_content_falls_through(self, scorer: CriticScorer) -> None:
        """Unbalanced or non-JSON brace content returns original text."""
        text = "Some text with {broken json here} and more"
        result = scorer._extract_json_from_text(text)
        assert result == text


class TestFallbackBehavior:
    """Final fallback: return original text unchanged."""

    def test_no_json_returns_original(self, scorer: CriticScorer) -> None:
        """Text with no JSON structure returns original text."""
        text = "This is just plain feedback text with no JSON."
        assert scorer._extract_json_from_text(text) == text

    def test_empty_string_returns_empty(self, scorer: CriticScorer) -> None:
        """Empty string returns empty string."""
        assert scorer._extract_json_from_text("") == ""

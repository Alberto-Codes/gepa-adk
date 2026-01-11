"""Contract tests for Scorer protocol compliance.

Note:
    These tests ensure implementations satisfy the Scorer protocol
    with correct method signatures, return types, and runtime checks.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from gepa_adk.ports.scorer import Scorer

pytestmark = pytest.mark.contract


class FixedScorer:
    """Minimal scorer implementation for contract testing.

    Note:
        Returns a fixed score for all inputs to verify protocol compliance.
    """

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Return a fixed score for testing."""
        return 0.5, {"note": "Fixed score for testing"}

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Return a fixed score asynchronously."""
        return self.score(input_text, output, expected)


class TestScorerProtocol:
    """Contract tests for Scorer protocol compliance."""

    def test_scorer_protocol_is_runtime_checkable(self):
        """Verify @runtime_checkable decorator works for isinstance() checks."""
        scorer = FixedScorer()
        assert isinstance(scorer, Scorer), "FixedScorer should satisfy Scorer protocol"

    def test_fixed_scorer_satisfies_protocol(self):
        """Verify minimal FixedScorer implementation satisfies protocol."""
        scorer = FixedScorer()
        assert isinstance(scorer, Scorer)

        # Verify both methods exist and are callable
        assert hasattr(scorer, "score")
        assert hasattr(scorer, "async_score")
        assert callable(scorer.score)
        assert callable(scorer.async_score)

    def test_score_returns_tuple_float_dict(self):
        """Verify return type contract: tuple[float, dict]."""
        scorer = FixedScorer()
        result = scorer.score("input", "output", "expected")

        assert isinstance(result, tuple), "score() must return a tuple"
        assert len(result) == 2, "score() must return (score, metadata)"
        score, metadata = result

        assert isinstance(score, float), "First element must be float"
        assert isinstance(metadata, dict), "Second element must be dict"

    def test_score_with_metadata(self):
        """Verify metadata dict is preserved (FR-007)."""
        scorer = FixedScorer()
        score, metadata = scorer.score("input", "output", "expected")

        assert isinstance(metadata, dict)
        assert "note" in metadata
        assert metadata["note"] == "Fixed score for testing"

    def test_boundary_scores(self):
        """Verify 0.0 and 1.0 are valid scores (edge case)."""

        # Create a scorer that returns boundary values
        class BoundaryScorer:
            def score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict[str, Any]]:
                if output == "zero":
                    return 0.0, {"boundary": "zero"}
                elif output == "one":
                    return 1.0, {"boundary": "one"}
                return 0.5, {}

            async def async_score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict[str, Any]]:
                return self.score(input_text, output, expected)

        scorer = BoundaryScorer()
        assert isinstance(scorer, Scorer)

        score_zero, meta_zero = scorer.score("test", "zero")
        assert score_zero == 0.0
        assert meta_zero["boundary"] == "zero"

        score_one, meta_one = scorer.score("test", "one")
        assert score_one == 1.0
        assert meta_one["boundary"] == "one"

    def test_metadata_accepts_any_dict(self):
        """Verify dict with various types is accepted (protocol doesn't enforce serializability)."""

        # Create a scorer with complex metadata
        class ComplexMetadataScorer:
            def score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict[str, Any]]:
                return 0.7, {
                    "feedback": "Good output",
                    "dimension_scores": {"accuracy": 0.8, "fluency": 0.6},
                    "reasoning": "Output matches expected pattern",
                    "nested": {"level1": {"level2": "value"}},
                    "list_value": [1, 2, 3],
                }

            async def async_score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict[str, Any]]:
                return self.score(input_text, output, expected)

        scorer = ComplexMetadataScorer()
        assert isinstance(scorer, Scorer)

        score, metadata = scorer.score("test", "output")
        assert isinstance(metadata, dict)
        assert "feedback" in metadata
        assert "dimension_scores" in metadata
        assert isinstance(metadata["dimension_scores"], dict)
        assert "nested" in metadata
        assert isinstance(metadata["nested"], dict)

    # User Story 2: Async Scoring Tests
    async def test_async_score_returns_same_format(self):
        """Verify async_score() returns tuple[float, dict] format."""
        scorer = FixedScorer()
        result = await scorer.async_score("input", "output", "expected")

        assert isinstance(result, tuple)
        assert len(result) == 2
        score, metadata = result

        assert isinstance(score, float)
        assert isinstance(metadata, dict)

    async def test_async_score_is_awaitable(self):
        """Verify async_score() method is a coroutine."""
        scorer = FixedScorer()
        coro = scorer.async_score("input", "output", "expected")

        assert asyncio.iscoroutine(coro), "async_score() must be a coroutine"
        result = await coro
        assert isinstance(result, tuple)

    async def test_concurrent_async_scoring(self):
        """Verify multiple async_score calls can run in parallel."""
        scorer = FixedScorer()

        # Create multiple concurrent scoring tasks
        tasks = [
            scorer.async_score(f"input_{i}", f"output_{i}", f"expected_{i}")
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for score, metadata in results:
            assert isinstance(score, float)
            assert isinstance(metadata, dict)

    def test_protocol_requires_both_methods(self):
        """Verify class with only score() does not satisfy Scorer protocol."""

        # Class missing async_score()
        class IncompleteScorer:
            def score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict[str, Any]]:
                return 0.5, {}

        scorer = IncompleteScorer()
        assert not isinstance(scorer, Scorer), (
            "IncompleteScorer should NOT satisfy Scorer protocol (missing async_score)"
        )

    # User Story 3: Optional Expected Parameter Tests
    def test_score_with_none_expected(self):
        """Verify optional expected handling (FR-005)."""

        # Scorer that handles None expected
        class OpenEndedScorer:
            def score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict[str, Any]]:
                if expected is None:
                    # Score based on output quality, not exact match
                    return 0.8, {
                        "evaluation": "open_ended",
                        "output_length": len(output),
                    }
                # Score based on exact match
                match = output.strip() == expected.strip()
                return (1.0 if match else 0.0), {"exact_match": match}

            async def async_score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict[str, Any]]:
                return self.score(input_text, output, expected)

        scorer = OpenEndedScorer()
        assert isinstance(scorer, Scorer)

        # Test with None expected
        score, metadata = scorer.score("Explain gravity", "Gravity is a force...")
        assert isinstance(score, float)
        assert score >= 0.0
        assert metadata["evaluation"] == "open_ended"

        # Test with expected value
        score2, metadata2 = scorer.score("What is 2+2?", "4", "4")
        assert score2 == 1.0
        assert metadata2["exact_match"] is True

    async def test_async_score_with_none_expected(self):
        """Verify async method also handles None expected."""

        class OpenEndedScorer:
            def score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict[str, Any]]:
                if expected is None:
                    return 0.75, {"evaluation": "open_ended"}
                return 1.0, {"exact_match": True}

            async def async_score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict[str, Any]]:
                return self.score(input_text, output, expected)

        scorer = OpenEndedScorer()
        assert isinstance(scorer, Scorer)

        # Test async with None expected
        score, metadata = await scorer.async_score("Explain AI", "AI is...")
        assert isinstance(score, float)
        assert score >= 0.0
        assert metadata["evaluation"] == "open_ended"

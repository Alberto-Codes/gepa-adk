"""Contract tests for LabelAgreementScorer protocol compliance.

These tests ensure LabelAgreementScorer satisfies the Scorer protocol with
correct method signatures and return types, and that the async method
returns the same result as the sync method.

Notes:
    The scorer is pure Python, so no agents, mocks or LLM calls are needed.
"""

from __future__ import annotations

import inspect

import pytest

from gepa_adk import LabelAgreementScorer as RootLabelAgreementScorer
from gepa_adk.adapters import LabelAgreementScorer as AdaptersLabelAgreementScorer
from gepa_adk.adapters.scoring import LabelAgreementScorer
from gepa_adk.ports.scorer import Scorer

pytestmark = pytest.mark.contract


class TestLabelAgreementScorerContract:
    """Protocol compliance of LabelAgreementScorer."""

    @pytest.mark.parametrize("field", [None, "label"])
    def test_is_runtime_checkable_scorer(self, field: str | None) -> None:
        """Both field modes satisfy the Scorer protocol at runtime."""
        assert isinstance(LabelAgreementScorer(field=field), Scorer)

    def test_default_field_is_none(self) -> None:
        """The no-argument constructor compares the whole output."""
        assert LabelAgreementScorer().field is None

    def test_exported_from_package_root_and_adapters(self) -> None:
        """The root and adapters exports are the same class."""
        assert RootLabelAgreementScorer is LabelAgreementScorer
        assert AdaptersLabelAgreementScorer is LabelAgreementScorer

    @pytest.mark.parametrize("method", ["score", "async_score"])
    def test_method_signature(self, method: str) -> None:
        """Both methods take input_text, output and an optional expected."""
        sig = inspect.signature(getattr(LabelAgreementScorer(), method))
        assert list(sig.parameters) == ["input_text", "output", "expected"]
        assert sig.parameters["expected"].default is None

    def test_async_score_is_coroutine_function(self) -> None:
        """The protocol async method must be awaitable, not a sync callable."""
        assert inspect.iscoroutinefunction(LabelAgreementScorer().async_score)


class TestLabelAgreementScorerBehavior:
    """Return shape and sync/async parity."""

    @pytest.mark.parametrize(
        ("field", "output", "expected"),
        [
            ("label", '{"label": "spam"}', "spam"),
            ("label", '{"label": "ham"}', "spam"),
            ("label", "not json", "spam"),
            ("label", "[1, 2]", "spam"),
            ("label", '{"label": "spam"}', None),
            (None, "plain", "plain"),
            (None, '{"a": 1}', '{"a": 2}'),
        ],
    )
    def test_score_returns_float_and_dict(
        self, field: str | None, output: str, expected: str | None
    ) -> None:
        """Each call returns a (float, dict) tuple with the four metadata keys."""
        result = LabelAgreementScorer(field=field).score("q", output, expected)

        assert isinstance(result, tuple)
        assert len(result) == 2
        score, metadata = result
        assert isinstance(score, float)
        assert score in (0.0, 1.0)
        assert isinstance(metadata, dict)
        assert {"field", "actual", "expected", "agreement"} <= metadata.keys()
        assert metadata["field"] == field
        assert metadata["expected"] == expected
        assert metadata["agreement"] is (score == 1.0)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("field", "output", "expected"),
        [
            ("label", '{"label": "spam"}', "spam"),
            ("label", '{"label": "ham"}', "spam"),
            ("label", "not json", "spam"),
            ("label", '{"other": 1}', "spam"),
            (None, '{"b": 2, "a": 1}', '{"a":1,"b":2}'),
            (None, "x", None),
        ],
    )
    async def test_async_score_matches_score(
        self, field: str | None, output: str, expected: str | None
    ) -> None:
        """Awaiting async_score yields the same tuple as score."""
        scorer = LabelAgreementScorer(field=field)
        assert await scorer.async_score("q", output, expected) == scorer.score(
            "q", output, expected
        )

    def test_list_output_with_field_reports_field_missing(self) -> None:
        """A JSON array has no fields, so the field is reported missing."""
        score, metadata = LabelAgreementScorer(field="label").score(
            "q", "[1, 2]", "spam"
        )
        assert score == 0.0
        assert metadata["reason"] == "field_missing"
        assert metadata["actual"] is None

    def test_plain_disagreement_has_no_reason(self) -> None:
        """A compared value that differs carries no error reason."""
        score, metadata = LabelAgreementScorer(field="label").score(
            "q", '{"label": "ham"}', "spam"
        )
        assert score == 0.0
        assert "reason" not in metadata
        assert metadata["actual"] == "ham"

    def test_non_string_field_value_is_stringified(self) -> None:
        """A numeric field value is compared through str()."""
        score, _ = LabelAgreementScorer(field="n").score("q", '{"n": 4}', " 4 ")
        assert score == 1.0

    def test_json_output_against_text_label_falls_back_to_text(self) -> None:
        """Whole-output mode uses stripped text when only one side is JSON."""
        scorer = LabelAgreementScorer()
        assert scorer.score("q", " 4 ", "4")[0] == 1.0
        assert scorer.score("q", '{"a": 1}', "a: 1")[0] == 0.0

"""Unit tests for AsyncGEPAEngine._aggregate_acceptance_score().

Direct unit tests for the score aggregation method, covering error paths
(empty lists, NaN, Inf, -Inf, mixed non-finite) and both sum/mean metrics.
Complements the integration-level tests in test_acceptance_scoring.py which
exercise the same paths through engine.run().

Note:
    Tests call the private method directly to isolate aggregation logic
    from the full evolution loop.
"""

from __future__ import annotations

import math

import pytest

from gepa_adk.domain.exceptions import InvalidScoreListError
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine.async_engine import AsyncGEPAEngine
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.unit


@pytest.fixture
def make_engine():
    """Factory to create an engine with a given acceptance_metric."""

    def _factory(metric: str = "mean") -> AsyncGEPAEngine:
        adapter = create_mock_adapter()
        config = EvolutionConfig(
            max_iterations=1,
            patience=0,
            acceptance_metric=metric,
        )
        return AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=Candidate(
                components={"instruction": "seed"}, generation=0
            ),
            batch=[{"input": "q", "expected": "a"}],
        )

    return _factory


class TestEmptyScoreValidation:
    """Verify empty score list raises InvalidScoreListError."""

    def test_empty_list_raises_with_reason(self, make_engine) -> None:
        """Empty list raises InvalidScoreListError with reason='empty'."""
        engine = make_engine("mean")
        with pytest.raises(InvalidScoreListError) as exc_info:
            engine._aggregate_acceptance_score([])
        assert exc_info.value.reason == "empty"

    def test_empty_list_preserves_scores_attr(self, make_engine) -> None:
        """Empty list error carries the original scores list."""
        engine = make_engine("sum")
        with pytest.raises(InvalidScoreListError) as exc_info:
            engine._aggregate_acceptance_score([])
        assert exc_info.value.scores == []


class TestNonFiniteScoreValidation:
    """Verify non-finite scores raise InvalidScoreListError."""

    @pytest.mark.parametrize(
        ("label", "scores"),
        [
            ("single_nan", [math.nan]),
            ("nan_in_middle", [0.5, math.nan, 0.7]),
            ("positive_inf", [0.5, math.inf, 0.7]),
            ("negative_inf", [0.5, -math.inf, 0.7]),
            ("all_nan", [math.nan, math.nan]),
            ("mixed_non_finite", [math.nan, math.inf, -math.inf]),
        ],
        ids=lambda x: x if isinstance(x, str) else None,
    )
    def test_non_finite_raises_with_reason(
        self, make_engine, label: str, scores: list[float]
    ) -> None:
        """Non-finite values raise InvalidScoreListError with reason='non-finite'."""
        engine = make_engine("mean")
        with pytest.raises(InvalidScoreListError) as exc_info:
            engine._aggregate_acceptance_score(scores)
        assert exc_info.value.reason == "non-finite"

    def test_non_finite_preserves_scores_attr(self, make_engine) -> None:
        """Non-finite error carries the original scores list."""
        bad_scores = [0.5, math.nan, 0.7]
        engine = make_engine("sum")
        with pytest.raises(InvalidScoreListError) as exc_info:
            engine._aggregate_acceptance_score(bad_scores)
        # NaN != NaN, so compare length and finite elements
        assert len(exc_info.value.scores) == 3


class TestSumAggregation:
    """Verify sum-based aggregation returns correct totals."""

    def test_single_score(self, make_engine) -> None:
        """Single score returns itself as sum."""
        engine = make_engine("sum")
        assert engine._aggregate_acceptance_score([0.75]) == 0.75

    def test_multiple_scores(self, make_engine) -> None:
        """Multiple scores return their sum."""
        engine = make_engine("sum")
        result = engine._aggregate_acceptance_score([0.1, 0.2, 0.3])
        assert result == pytest.approx(0.6)

    def test_negative_scores(self, make_engine) -> None:
        """Negative finite scores are valid and summed correctly."""
        engine = make_engine("sum")
        result = engine._aggregate_acceptance_score([-0.5, 0.3, -0.1])
        assert result == pytest.approx(-0.3)

    def test_zero_scores(self, make_engine) -> None:
        """All-zero list sums to zero."""
        engine = make_engine("sum")
        assert engine._aggregate_acceptance_score([0.0, 0.0, 0.0]) == 0.0


class TestMeanAggregation:
    """Verify mean-based aggregation returns correct averages."""

    def test_single_score(self, make_engine) -> None:
        """Single score returns itself as mean."""
        engine = make_engine("mean")
        assert engine._aggregate_acceptance_score([0.75]) == 0.75

    def test_multiple_scores(self, make_engine) -> None:
        """Multiple scores return their mean."""
        engine = make_engine("mean")
        result = engine._aggregate_acceptance_score([0.1, 0.2, 0.3])
        assert result == pytest.approx(0.2)

    def test_negative_scores(self, make_engine) -> None:
        """Negative finite scores produce correct mean."""
        engine = make_engine("mean")
        result = engine._aggregate_acceptance_score([-0.6, 0.0, 0.3])
        assert result == pytest.approx(-0.1)

    def test_zero_scores(self, make_engine) -> None:
        """All-zero list averages to zero."""
        engine = make_engine("mean")
        assert engine._aggregate_acceptance_score([0.0, 0.0, 0.0]) == 0.0

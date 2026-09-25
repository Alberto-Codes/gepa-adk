"""Acceptance tests for issue 388: evaluation_policy needs a candidate_selector.

The engine consults ``evaluation_policy`` only through the Pareto state,
which exists only when a ``candidate_selector`` is set. Passing a policy on
its own therefore did nothing, silently. Engine construction now raises
``ConfigurationError`` for that combination.

Notes:
    The adapter is the configurable mock from ``tests/fixtures/adapters.py``.
"""

from __future__ import annotations

import pytest

from gepa_adk.adapters.selection.candidate_selector import ParetoCandidateSelector
from gepa_adk.adapters.selection.evaluation_policy import (
    FullEvaluationPolicy,
    SubsetEvaluationPolicy,
)
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine import AsyncGEPAEngine
from tests.fixtures.adapters import create_mock_adapter

pytestmark = pytest.mark.unit


def _engine(**kwargs) -> AsyncGEPAEngine:
    return AsyncGEPAEngine(
        adapter=create_mock_adapter(),
        config=EvolutionConfig(max_iterations=1),
        initial_candidate=Candidate(components={"instruction": "seed"}),
        batch=[{"input": "q1"}, {"input": "q2"}, {"input": "q3"}],
        **kwargs,
    )


class TestEvaluationPolicyRequiresSelector:
    """A policy without a selector is refused at construction."""

    def test_subset_policy_without_selector_raises(self) -> None:
        """The error names both fields so the fix is obvious."""
        with pytest.raises(ConfigurationError) as exc_info:
            _engine(evaluation_policy=SubsetEvaluationPolicy(subset_size=2))

        message = str(exc_info.value)
        assert "evaluation_policy" in message
        assert "candidate_selector" in message

    def test_full_policy_without_selector_raises_too(self) -> None:
        """Any explicit policy without a selector is refused, even the default one."""
        with pytest.raises(ConfigurationError, match="candidate_selector"):
            _engine(evaluation_policy=FullEvaluationPolicy())

    def test_policy_with_selector_is_accepted(self) -> None:
        """The valid combination constructs and keeps the policy."""
        policy = SubsetEvaluationPolicy(subset_size=2)
        engine = _engine(
            evaluation_policy=policy, candidate_selector=ParetoCandidateSelector()
        )
        assert engine._evaluation_policy is policy

    def test_neither_is_accepted(self) -> None:
        """No policy and no selector is the plain full-evaluation engine."""
        engine = _engine()
        assert isinstance(engine._evaluation_policy, FullEvaluationPolicy)

    def test_selector_alone_is_accepted(self) -> None:
        """A selector without a policy defaults to full evaluation."""
        engine = _engine(candidate_selector=ParetoCandidateSelector())
        assert isinstance(engine._evaluation_policy, FullEvaluationPolicy)

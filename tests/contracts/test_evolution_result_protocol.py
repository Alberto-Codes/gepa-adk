"""Contract tests for EvolutionResultProtocol compliance.

Verifies that both ``EvolutionResult`` and ``MultiAgentEvolutionResult``
satisfy the ``EvolutionResultProtocol`` structurally, catching future
field renames or removals that would silently break the contract.

Note:
    This is the first contract test for a data-attribute protocol.
    ``isinstance()`` in Python 3.12 checks both data attributes and
    properties via internal ``hasattr()`` calls.
"""

from __future__ import annotations

import pytest

from gepa_adk.domain.models import (
    EvolutionResult,
    MultiAgentEvolutionResult,
)
from gepa_adk.ports.evolution_result import EvolutionResultProtocol

pytestmark = pytest.mark.contract


class TestEvolutionResultProtocol:
    """Contract tests for EvolutionResultProtocol compliance."""

    def test_evolution_result_satisfies_protocol(self) -> None:
        """Verify EvolutionResult passes isinstance check."""
        result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Be helpful"},
            iteration_history=[],
            total_iterations=3,
        )
        assert isinstance(result, EvolutionResultProtocol), (
            "EvolutionResult should satisfy EvolutionResultProtocol"
        )

    def test_multi_agent_evolution_result_satisfies_protocol(self) -> None:
        """Verify MultiAgentEvolutionResult passes isinstance check."""
        result = MultiAgentEvolutionResult(
            evolved_components={"agent1.instruction": "Be helpful"},
            original_score=0.5,
            final_score=0.8,
            primary_agent="agent1",
            iteration_history=[],
            total_iterations=3,
        )
        assert isinstance(result, EvolutionResultProtocol), (
            "MultiAgentEvolutionResult should satisfy EvolutionResultProtocol"
        )

    def test_property_return_types(self) -> None:
        """Verify improvement and improved properties return correct types."""
        result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Be helpful"},
            iteration_history=[],
            total_iterations=3,
        )
        multi_result = MultiAgentEvolutionResult(
            evolved_components={"agent1.instruction": "Be helpful"},
            original_score=0.4,
            final_score=0.7,
            primary_agent="agent1",
            iteration_history=[],
            total_iterations=5,
        )

        for r in (result, multi_result):
            assert isinstance(r.improvement, float), (
                f"{type(r).__name__}.improvement should return float"
            )
            assert isinstance(r.improved, bool), (
                f"{type(r).__name__}.improved should return bool"
            )

    def test_field_access_and_types(self) -> None:
        """Verify all 5 data fields are accessible with correct types."""
        result = EvolutionResult(
            original_score=0.5,
            final_score=0.8,
            evolved_components={"instruction": "Be helpful"},
            iteration_history=[],
            total_iterations=3,
        )
        multi_result = MultiAgentEvolutionResult(
            evolved_components={"agent1.instruction": "Be helpful"},
            original_score=0.4,
            final_score=0.7,
            primary_agent="agent1",
            iteration_history=[],
            total_iterations=5,
        )

        for r in (result, multi_result):
            assert isinstance(r.original_score, float), (
                f"{type(r).__name__}.original_score should be float"
            )
            assert isinstance(r.final_score, float), (
                f"{type(r).__name__}.final_score should be float"
            )
            assert isinstance(r.evolved_components, dict), (
                f"{type(r).__name__}.evolved_components should be dict"
            )
            assert isinstance(r.iteration_history, list), (
                f"{type(r).__name__}.iteration_history should be list"
            )
            assert isinstance(r.total_iterations, int), (
                f"{type(r).__name__}.total_iterations should be int"
            )

    def test_equal_scores_not_improved(self) -> None:
        """Verify improved returns False when scores are equal (strict >)."""
        result = EvolutionResult(
            original_score=0.5,
            final_score=0.5,
            evolved_components={"instruction": "Be helpful"},
            iteration_history=[],
            total_iterations=3,
        )
        multi_result = MultiAgentEvolutionResult(
            evolved_components={"agent1.instruction": "Be helpful"},
            original_score=0.7,
            final_score=0.7,
            primary_agent="agent1",
            iteration_history=[],
            total_iterations=5,
        )

        for r in (result, multi_result):
            assert r.improved is False, (
                f"{type(r).__name__}.improved should be False when scores are equal"
            )
            assert r.improvement == 0.0, (
                f"{type(r).__name__}.improvement should be 0.0 when scores are equal"
            )

    def test_incomplete_class_does_not_satisfy_protocol(self) -> None:
        """Verify class missing improvement property fails isinstance."""

        class IncompleteResult:
            """Missing improvement and improved properties."""

            original_score: float = 0.5
            final_score: float = 0.8
            evolved_components: dict[str, str] = {}
            iteration_history: list = []
            total_iterations: int = 3

        incomplete = IncompleteResult()
        assert not isinstance(incomplete, EvolutionResultProtocol), (
            "Class missing improvement property should NOT satisfy protocol"
        )


__all__ = ["TestEvolutionResultProtocol"]

"""Unit tests for stop reason tracking in AsyncGEPAEngine.

Verifies that the engine correctly sets ``StopReason`` on
``EvolutionResult`` for each termination condition: max iterations,
patience exhaustion, custom stoppers, and baseline-only runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.domain.stopper import StopperState
from gepa_adk.domain.types import StopReason
from gepa_adk.engine.async_engine import AsyncGEPAEngine

if TYPE_CHECKING:
    from tests.fixtures.adapters import MockAdapter

pytestmark = pytest.mark.unit


class TestEngineStopReason:
    """Tests for stop reason tracking in the evolution engine."""

    async def test_max_iterations_stop_reason(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """Engine sets MAX_ITERATIONS when max_iterations reached."""
        config = EvolutionConfig(
            max_iterations=2,
            patience=0,
        )
        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=config,
            initial_candidate=Candidate(
                components={"instruction": "Be helpful"}, generation=0
            ),
            batch=[{"input": "Hello", "expected": "Hi"}],
        )
        result = await engine.run()
        assert result.stop_reason == StopReason.MAX_ITERATIONS

    async def test_patience_exhaustion_stop_reason(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """Engine sets MAX_ITERATIONS when patience exhausted."""
        config = EvolutionConfig(
            max_iterations=50,
            patience=1,
        )
        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=config,
            initial_candidate=Candidate(
                components={"instruction": "Be helpful"}, generation=0
            ),
            batch=[{"input": "Hello", "expected": "Hi"}],
        )
        result = await engine.run()
        assert result.stop_reason == StopReason.MAX_ITERATIONS

    async def test_custom_stopper_stop_reason(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """Engine sets STOPPER_TRIGGERED when custom stopper returns True."""

        class ImmediateStopper:
            """Stopper that triggers after first iteration."""

            def __init__(self) -> None:
                self.call_count = 0

            def __call__(self, state: StopperState) -> bool:
                self.call_count += 1
                return self.call_count >= 2  # noqa: PLR2004

        config = EvolutionConfig(
            max_iterations=50,
            patience=0,
            stop_callbacks=[ImmediateStopper()],
        )
        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=config,
            initial_candidate=Candidate(
                components={"instruction": "Be helpful"}, generation=0
            ),
            batch=[{"input": "Hello", "expected": "Hi"}],
        )
        result = await engine.run()
        assert result.stop_reason == StopReason.STOPPER_TRIGGERED

    async def test_baseline_only_stop_reason(self, mock_adapter: "MockAdapter") -> None:
        """Engine sets MAX_ITERATIONS when max_iterations=0 (baseline only)."""
        config = EvolutionConfig(
            max_iterations=0,
            patience=0,
        )
        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=config,
            initial_candidate=Candidate(
                components={"instruction": "Be helpful"}, generation=0
            ),
            batch=[{"input": "Hello", "expected": "Hi"}],
        )
        result = await engine.run()
        assert result.stop_reason == StopReason.MAX_ITERATIONS

    async def test_result_schema_version_from_engine(
        self, mock_adapter: "MockAdapter"
    ) -> None:
        """Engine result includes schema_version == 1."""
        config = EvolutionConfig(max_iterations=1, patience=0)
        engine = AsyncGEPAEngine(
            adapter=mock_adapter,
            config=config,
            initial_candidate=Candidate(
                components={"instruction": "Be helpful"}, generation=0
            ),
            batch=[{"input": "Hello", "expected": "Hi"}],
        )
        result = await engine.run()
        assert result.schema_version == 1

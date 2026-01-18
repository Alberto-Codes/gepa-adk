"""Integration tests for StateGuard logging in the public API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from structlog.testing import capture_logs

from gepa_adk import evolve
from gepa_adk.domain.models import EvolutionResult, IterationRecord
from gepa_adk.utils import StateGuard

pytestmark = pytest.mark.integration


class OutputSchema(BaseModel):
    """Minimal schema for schema-based scoring in tests."""

    score: float = Field(ge=0.0, le=1.0)
    result: str


@pytest.mark.asyncio
async def test_evolve_logs_state_guard_applied() -> None:
    """Verify evolve() emits structured log when StateGuard applies changes."""
    agent = LlmAgent(
        name="test_agent",
        model="gemini-2.0-flash",
        instruction="Hello {user_id}",
        output_schema=OutputSchema,
    )
    state_guard = StateGuard(required_tokens=["{user_id}"])
    mock_result = EvolutionResult(
        original_score=0.5,
        final_score=0.8,
        evolved_component_text="Hello",
        iteration_history=[
            IterationRecord(
                iteration_number=1,
                score=0.6,
                component_text="Test instruction",
                accepted=True,
            )
        ],
        total_iterations=1,
    )

    with capture_logs() as logs:
        with (
            patch("gepa_adk.api.logger", structlog.get_logger()),
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            await evolve(
                agent,
                [{"input": "test", "expected": "test"}],
                state_guard=state_guard,
            )

    state_guard_logs = [
        entry for entry in logs if entry.get("event") == "evolve.state_guard.applied"
    ]
    assert len(state_guard_logs) == 1
    entry = state_guard_logs[0]
    assert entry["agent_name"] == "test_agent"
    assert entry["repaired_tokens"] == ["{user_id}"]
    assert entry["escaped_tokens"] == []
    assert entry["repaired"] is True
    assert entry["escaped"] is False


@pytest.mark.asyncio
async def test_evolve_logs_state_guard_no_changes() -> None:
    """Verify evolve() emits structured log when StateGuard makes no changes."""
    agent = LlmAgent(
        name="test_agent",
        model="gemini-2.0-flash",
        instruction="Hello {user_id}",
        output_schema=OutputSchema,
    )
    state_guard = StateGuard(required_tokens=["{user_id}"])
    mock_result = EvolutionResult(
        original_score=0.5,
        final_score=0.8,
        evolved_component_text="Hello {user_id}",
        iteration_history=[
            IterationRecord(
                iteration_number=1,
                score=0.6,
                component_text="Test instruction",
                accepted=True,
            )
        ],
        total_iterations=1,
    )

    with capture_logs() as logs:
        with (
            patch("gepa_adk.api.logger", structlog.get_logger()),
            patch("gepa_adk.api.AsyncGEPAEngine") as mock_engine_class,
            patch("gepa_adk.api.ADKAdapter") as mock_adapter_class,
            patch("gepa_adk.api.SchemaBasedScorer") as mock_scorer_class,
        ):
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine_instance

            mock_adapter_instance = MagicMock()
            mock_adapter_class.return_value = mock_adapter_instance

            mock_scorer_instance = MagicMock()
            mock_scorer_class.return_value = mock_scorer_instance

            await evolve(
                agent,
                [{"input": "test", "expected": "test"}],
                state_guard=state_guard,
            )

    state_guard_logs = [
        entry for entry in logs if entry.get("event") == "evolve.state_guard.no_changes"
    ]
    assert len(state_guard_logs) == 1
    entry = state_guard_logs[0]
    assert entry["agent_name"] == "test_agent"

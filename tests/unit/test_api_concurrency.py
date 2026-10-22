"""Exercise configured evaluation concurrency through the real single-agent API.

A yielding executor records overlapping rows without making any LLM calls.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from google.adk.agents import LlmAgent

from gepa_adk import evolve
from gepa_adk.domain.models import EvolutionConfig
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus
from tests.conftest import MockScorer

pytestmark = pytest.mark.unit


class ConcurrencyRecordingExecutor:
    """Record active and peak calls while yielding to the other evaluation tasks."""

    def __init__(self) -> None:
        """Start with no active evaluations or recorded inputs."""
        self.active = 0
        self.peak = 0
        self.inputs: list[str] = []

    async def execute_agent(
        self, agent: Any, input_text: str, **kwargs: Any
    ) -> ExecutionResult:
        """Yield once so every unblocked row can enter before this call completes."""
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.inputs.append(input_text)
        try:
            await asyncio.sleep(0)
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                session_id=f"session-{input_text}",
                extracted_value="answer",
            )
        finally:
            self.active -= 1


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 2])
async def test_evolve_limits_concurrent_evaluation_rows(limit: int) -> None:
    """The real adapter semaphore honors the config on a four-row baseline."""
    agent = LlmAgent(
        name="answerer",
        model="ollama_chat/gpt-oss:20b",
        instruction="Answer the question.",
    )
    executor = ConcurrencyRecordingExecutor()
    trainset = [{"input": f"row-{i}", "expected": "answer"} for i in range(4)]

    result = await evolve(
        agent,
        trainset,
        scorer=MockScorer(),
        reflection_agent=LlmAgent(name="reflector", instruction="Improve the answer."),
        config=EvolutionConfig(max_iterations=0, max_concurrent_evals=limit),
        executor=executor,
    )

    assert sorted(executor.inputs) == [f"row-{i}" for i in range(4)]
    assert result.baseline_failed_evaluations == 0
    assert executor.active == 0
    assert executor.peak == limit

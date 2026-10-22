"""Exercise critic dimensions through the public single-agent evolution API.

Notes:
    Only agent execution is faked; scoring, adaptation and Pareto tracking run
    through their production implementations without making model calls.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from google.adk.agents import LlmAgent

from gepa_adk import evolve
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import EvolutionConfig
from gepa_adk.domain.types import FrontierType
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

pytestmark = pytest.mark.unit


class DimensionExecutor:
    """Answer agent calls and return configured critic dimensions for each row."""

    def __init__(self, dimensions: list[dict[str, float] | None]) -> None:
        """Store the critic dimensions returned for each input row."""
        self.dimensions = dimensions

    async def execute_agent(
        self, agent: Any, input_text: str, **kwargs: Any
    ) -> ExecutionResult:
        if agent.name == "critic":
            index = 0 if "row-a" in input_text else 1
            payload: dict[str, Any] = {"score": 0.5, "feedback": "Improve clarity."}
            if self.dimensions[index] is not None:
                payload["dimension_scores"] = self.dimensions[index]
            text = json.dumps(payload)
        elif agent.name == "reflector":
            text = "Answer precisely and clearly."
        else:
            text = f"Answer for {input_text}"
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            session_id="fake-session",
            extracted_value=text,
        )


async def _evolve_dimensions(
    dimensions: list[dict[str, float] | None],
    frontier_type: FrontierType = FrontierType.OBJECTIVE,
) -> Any:
    agents = {
        name: LlmAgent(
            name=name,
            model="ollama_chat/gpt-oss:20b",
            instruction="Answer the question.",
        )
        for name in ("answerer", "critic", "reflector")
    }
    return await evolve(
        agents["answerer"],
        [{"input": "row-a"}, {"input": "row-b"}],
        critic=agents["critic"],
        reflection_agent=agents["reflector"],
        executor=DimensionExecutor(dimensions),
        candidate_selector="pareto",
        config=EvolutionConfig(max_iterations=1, frontier_type=frontier_type, seed=7),
    )


@pytest.mark.asyncio
async def test_evolve_forwards_critic_dimensions_to_objective_frontier() -> None:
    """Dimension dictionaries reach the result in input order."""
    dimensions = [{"accuracy": 0.9, "clarity": 0.4}, {"accuracy": 0.3, "clarity": 0.8}]
    result = await _evolve_dimensions(dimensions)
    assert result.objective_scores == dimensions
    assert len(result.iteration_history) == 1
    assert result.iteration_history[0].objective_scores == dimensions


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", [None, {}])
@pytest.mark.parametrize("missing_index", [0, 1])
async def test_evolve_rejects_mixed_dimensions_with_example_index(
    missing: dict[str, float] | None, missing_index: int
) -> None:
    """A partially dimensional batch names the example missing dimensions."""
    dimensions: list[dict[str, float] | None] = [{"accuracy": 0.8}, {"accuracy": 0.7}]
    dimensions[missing_index] = missing
    with pytest.raises(ConfigurationError, match=rf"example {missing_index}"):
        await _evolve_dimensions(dimensions)


@pytest.mark.asyncio
@pytest.mark.parametrize("dimensions", [[None, None], [{}, {}], [None, {}]])
async def test_evolve_without_dimensions_keeps_objective_scores_none(
    dimensions: list[dict[str, float] | None],
) -> None:
    """Scalar-only scorers keep the existing instance-frontier behavior."""
    result = await _evolve_dimensions(dimensions, FrontierType.INSTANCE)
    assert result.objective_scores is None
    assert all(record.objective_scores is None for record in result.iteration_history)

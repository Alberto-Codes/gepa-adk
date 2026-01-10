# Quickstart: AsyncGEPAAdapter Protocol

**Feature**: 004-async-gepa-adapter
**Date**: 2026-01-10

## Overview

The `AsyncGEPAAdapter` protocol defines the contract for integrating custom evaluation logic with the gepa-adk evolution engine. Implement this protocol to evolve agents using any backend (Google ADK, OpenAI, custom LLMs).

## Installation

```bash
# gepa-adk is not yet on PyPI, install from source
git clone https://github.com/Alberto-Codes/gepa-adk.git
cd gepa-adk
uv sync
```

## Basic Usage

### Importing the Protocol

```python
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch
```

### Implementing an Adapter

```python
from typing import Any, Mapping, Sequence
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch


class MyAdapter:
    """Custom adapter for your evaluation backend."""

    async def evaluate(
        self,
        batch: list[dict],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate a candidate on a batch of inputs.

        Args:
            batch: List of input data instances.
            candidate: Component name to text mapping.
            capture_traces: Whether to capture execution traces.

        Returns:
            EvaluationBatch with outputs, scores, and optional traces.
        """
        outputs = []
        scores = []
        trajectories = [] if capture_traces else None

        for item in batch:
            # Your evaluation logic here
            output = await self._run_agent(candidate["instruction"], item)
            score = await self._compute_score(output, item)

            outputs.append(output)
            scores.append(score)
            if capture_traces:
                trajectories.append({"input": item, "output": output})

        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            trajectories=trajectories,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build reflective examples from evaluation traces.

        Args:
            candidate: Current candidate components.
            eval_batch: Evaluation results with traces.
            components_to_update: Components to generate examples for.

        Returns:
            Mapping of component name to list of reflective examples.
        """
        dataset = {}
        for component in components_to_update:
            examples = []
            for i, trajectory in enumerate(eval_batch.trajectories or []):
                examples.append({
                    "Inputs": trajectory["input"],
                    "Generated Outputs": eval_batch.outputs[i],
                    "Feedback": f"Score: {eval_batch.scores[i]:.2f}",
                })
            dataset[component] = examples
        return dataset

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose improved component texts based on reflection.

        Args:
            candidate: Current candidate components.
            reflective_dataset: Reflective examples per component.
            components_to_update: Components to propose updates for.

        Returns:
            Mapping of component name to new proposed text.
        """
        proposals = {}
        for component in components_to_update:
            examples = reflective_dataset.get(component, [])
            # Your proposal logic here (e.g., call LLM for reflection)
            new_text = await self._generate_improvement(
                current=candidate[component],
                examples=examples,
            )
            proposals[component] = new_text
        return proposals

    # Private helper methods
    async def _run_agent(self, instruction: str, input_data: dict) -> str:
        # Implementation-specific agent execution
        ...

    async def _compute_score(self, output: str, expected: dict) -> float:
        # Implementation-specific scoring
        ...

    async def _generate_improvement(
        self, current: str, examples: list
    ) -> str:
        # Implementation-specific proposal generation
        ...
```

### Verifying Protocol Compliance

```python
# Runtime check
adapter = MyAdapter()
assert isinstance(adapter, AsyncGEPAAdapter)

# Type checker verification (mypy/pyright)
# The static type checker will verify signature compatibility
```

## Using with the Evolution Engine

```python
from gepa_adk.domain.models import Candidate, EvolutionConfig
# from gepa_adk.engine import AsyncGEPAEngine  # Coming in Issue #6

async def evolve_agent():
    adapter = MyAdapter()
    candidate = Candidate(
        components={"instruction": "Be helpful and concise."}
    )
    config = EvolutionConfig(max_iterations=10)

    # Engine usage (coming in Issue #6)
    # engine = AsyncGEPAEngine(adapter, config)
    # result = await engine.evolve(candidate, validation_data)
```

## EvaluationBatch Structure

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

Trajectory = TypeVar("Trajectory")
RolloutOutput = TypeVar("RolloutOutput")

@dataclass(slots=True, frozen=True)
class EvaluationBatch(Generic[Trajectory, RolloutOutput]):
    outputs: list[RolloutOutput]           # Raw outputs from evaluation
    scores: list[float]                    # Numeric scores (higher = better)
    trajectories: list[Trajectory] | None  # Execution traces (optional)
    objective_scores: list[dict[str, float]] | None  # Multi-objective (optional)
```

## Best Practices

### Error Handling

```python
async def evaluate(self, batch, candidate, capture_traces=False):
    outputs, scores, trajectories = [], [], []

    for item in batch:
        try:
            output = await self._run_agent(candidate["instruction"], item)
            score = await self._compute_score(output, item)
        except Exception as e:
            # Graceful degradation: don't raise, use fallback
            output = f"Error: {e}"
            score = 0.0

        outputs.append(output)
        scores.append(score)
        if capture_traces:
            trajectories.append({"input": item, "output": output})

    return EvaluationBatch(
        outputs=outputs,
        scores=scores,
        trajectories=trajectories if capture_traces else None,
    )
```

### Async Patterns

```python
import asyncio

async def evaluate(self, batch, candidate, capture_traces=False):
    # Parallel evaluation with semaphore for rate limiting
    semaphore = asyncio.Semaphore(5)

    async def eval_one(item):
        async with semaphore:
            return await self._run_agent(candidate["instruction"], item)

    outputs = await asyncio.gather(*[eval_one(item) for item in batch])
    # ... rest of evaluation
```

## Next Steps

- **Issue #6**: `AsyncGEPAEngine` - Core evolution loop using this adapter
- **Issue #8**: `ADKAdapter` - Google ADK-specific implementation
- **Issue #9**: `CriticScorer` - Structured feedback from ADK critic agents

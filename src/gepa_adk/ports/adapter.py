"""Protocol definitions for async adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Mapping, Protocol, Sequence, TypeVar, runtime_checkable

from gepa_adk.domain.types import ComponentName, Score

DataInst = TypeVar("DataInst")
Trajectory = TypeVar("Trajectory")
RolloutOutput = TypeVar("RolloutOutput")


@dataclass(frozen=True, slots=True)
class EvaluationBatch(Generic[Trajectory, RolloutOutput]):
    """Container for evaluation outputs and scores.

    Attributes:
        outputs (list[RolloutOutput]): Per-example outputs produced during evaluation.
        scores (list[Score]): Per-example normalized scores (higher is better).
        trajectories (list[Trajectory] | None): Optional per-example execution traces.
        objective_scores (list[dict[ComponentName, Score]] | None): Optional
            multi-objective scores per example.

    Examples:
        Create a batch with optional traces:

        ```python
        batch = EvaluationBatch(
            outputs=["ok", "ok"],
            scores=[0.9, 0.8],
            trajectories=[{"trace": 1}, {"trace": 2}],
        )
        ```
    """

    outputs: list[RolloutOutput]
    scores: list[Score]
    trajectories: list[Trajectory] | None = None
    objective_scores: list[dict[ComponentName, Score]] | None = None


@runtime_checkable
class AsyncGEPAAdapter(Protocol[DataInst, Trajectory, RolloutOutput]):
    """Protocol for async GEPA adapters used by the evolution engine.

    Implementations provide evaluation, reflection dataset generation, and
    proposal updates for candidate component texts.

    Examples:
        Implement a minimal adapter:

        ```python
        class MyAdapter:
            async def evaluate(self, batch, candidate, capture_traces=False):
                return EvaluationBatch(outputs=[], scores=[])

            async def make_reflective_dataset(
                self, candidate, eval_batch, components_to_update
            ):
                return {component: [] for component in components_to_update}

            async def propose_new_texts(
                self, candidate, reflective_dataset, components_to_update
            ):
                return {
                    component: candidate[component]
                    for component in components_to_update
                }
        ```
    """

    async def evaluate(
        self,
        batch: list[DataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Trajectory, RolloutOutput]:
        """Evaluate a candidate over a batch of inputs.

        Args:
            batch: Input data instances to evaluate.
            candidate: Component name to text mapping.
            capture_traces: Whether to capture execution traces.

        Returns:
            Evaluation results with outputs, scores, and optional traces.

        Examples:
            Basic evaluation:

            ```python
            result = await adapter.evaluate(batch, candidate)
            assert len(result.scores) == len(batch)
            ```
        """

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[Trajectory, RolloutOutput],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build reflective datasets from evaluation traces.

        Args:
            candidate: Current candidate components.
            eval_batch: Evaluation results with traces.
            components_to_update: Components to generate datasets for.

        Returns:
            Mapping of component name to reflective examples.

        Examples:
            Build datasets for specific components:

            ```python
            dataset = await adapter.make_reflective_dataset(
                candidate,
                eval_batch,
                ["instruction"],
            )
            ```
        """

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose updated component texts from reflective datasets.

        Args:
            candidate: Current candidate components.
            reflective_dataset: Reflective examples per component.
            components_to_update: Components to propose updates for.

        Returns:
            Mapping of component name to new proposed text.

        Examples:
            Generate new component texts:

            ```python
            proposals = await adapter.propose_new_texts(
                candidate,
                reflective_dataset,
                ["instruction"],
            )
            ```
        """

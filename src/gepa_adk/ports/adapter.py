"""Protocol definitions for async adapters.

This module defines the AsyncGEPAAdapter protocol and the EvaluationBatch
dataclass that together form the contract between the evolution engine and
external evaluation systems.

Attributes:
    EvaluationBatch (dataclass): Container for evaluation outputs and scores.
    AsyncGEPAAdapter (protocol): Protocol for async GEPA adapters.

Examples:
    Create an EvaluationBatch with scores and outputs:

    ```python
    from gepa_adk.ports.adapter import EvaluationBatch

    batch = EvaluationBatch(
        outputs=["Hello!", "Good day!"],
        scores=[0.8, 0.95],
        inputs=["Greet casually", "Greet formally"],
    )
    assert len(batch.scores) == 2
    ```

See Also:
    - [`ProposerProtocol`][gepa_adk.ports.proposer.ProposerProtocol]:
        Consumes EvaluationBatch for reflective proposals.
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: Domain models used
        alongside adapter results.

Note:
    This module defines the core protocol interface that connects
    gepa-adk's evolution engine to external evaluation systems.
"""

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
        metadata (list[dict[str, Any]] | None): Optional per-example scorer metadata.
            When provided, metadata[i] corresponds to outputs[i] and scores[i]
            (index-aligned). Metadata dicts may contain scorer-specific fields like
            'feedback', 'actionable_guidance', or 'dimension_scores' from
            CriticScorer implementations.
        inputs (list[str] | None): Optional per-example input text that was used
            to generate each output. Used by make_reflective_dataset to provide
            context for reflection. When provided, inputs[i] corresponds to the
            input that produced outputs[i].

    Examples:
        Create a batch with optional traces:

        ```python
        batch = EvaluationBatch(
            outputs=["ok", "ok"],
            scores=[0.9, 0.8],
            trajectories=[{"trace": 1}, {"trace": 2}],
        )
        ```

        Create a batch with inputs for reflection:

        ```python
        batch = EvaluationBatch(
            outputs=["Hello!", "Good morrow!"],
            scores=[0.3, 0.9],
            inputs=["I am the King", "I am your friend"],
        )
        ```

    Note:
        All fields are immutable once created due to frozen=True.
        Use this as the standard return type from adapter evaluations.
        When metadata is not None, len(metadata) must equal len(outputs) and len(scores).
    """

    outputs: list[RolloutOutput]
    scores: list[Score]
    trajectories: list[Trajectory] | None = None
    objective_scores: list[dict[ComponentName, Score]] | None = None
    metadata: list[dict[str, Any]] | None = None
    inputs: list[str] | None = None


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

    Note:
        Adapters must implement all three async methods to satisfy
        the protocol. Use runtime_checkable for isinstance() checks.
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

        Note:
            Output and score lists must have the same length as the
            input batch. Set capture_traces=True to enable reflection.
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

        Note:
            Only call this method when eval_batch contains trajectories.
            Each component receives its own list of reflective examples.
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

        Note:
            Outputs should contain improved text for each requested
            component. The evolution engine uses these as mutation candidates.
        """

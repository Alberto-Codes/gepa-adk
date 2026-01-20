"""Configurable mock adapter factory for testing.

This module provides a factory pattern for creating mock adapters with
configurable behavior, replacing scattered MockAdapter implementations
across the test suite.

Note:
    All adapter variations share the same underlying implementation.
    Use factory parameters to customize behavior for specific test needs.

Examples:
    Create a basic adapter:

    ```python
    adapter = create_mock_adapter(scores=[0.5, 0.6, 0.7])
    ```

    Create adapter with objective scores:

    ```python
    adapter = create_mock_adapter(
        scores=[0.5, 0.6],
        objective_scores={"accuracy": 0.9, "latency": 0.8},
    )
    ```

    Create adapter that tracks calls:

    ```python
    adapter = create_mock_adapter(scores=[0.5], track_calls=True)
    result = await adapter.evaluate(batch, candidate)
    assert adapter.call_count == 1
    ```
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch


class OutputMode(Enum):
    """Output generation modes for mock adapter.

    Attributes:
        NONE: Return None for all outputs (default).
        CANDIDATE_TEXT: Return candidate component text as output.
        INDEXED: Return "output_0", "output_1", etc. as outputs.
    """

    NONE = "none"
    CANDIDATE_TEXT = "candidate_text"
    INDEXED = "indexed"


@dataclass
class AdapterConfig:
    """Configuration for mock adapter behavior.

    Attributes:
        scores: List of scores to return sequentially. Falls back to default_score
            when exhausted.
        default_score: Score to return when scores list is exhausted.
        objective_scores: Optional objective scores dict per example.
        output_mode: How to generate output values.
        output_component: Component name to use for CANDIDATE_TEXT output mode.
        track_calls: Whether to record evaluate calls for inspection.
        custom_evaluate: Optional custom evaluate implementation.
        custom_propose: Optional custom propose implementation.
        custom_reflective_dataset: Optional custom reflective dataset implementation.
    """

    scores: list[float] = field(default_factory=lambda: [0.5])
    default_score: float = 0.5
    objective_scores: dict[str, float] | None = None
    output_mode: OutputMode = OutputMode.NONE
    output_component: str = "instruction"
    track_calls: bool = True
    custom_evaluate: (
        Callable[
            [list[Any], dict[str, str], bool],
            Awaitable[EvaluationBatch[Any, Any]],
        ]
        | None
    ) = None
    custom_propose: (
        Callable[
            [dict[str, str], Mapping[str, Sequence[Mapping[str, Any]]], list[str]],
            Awaitable[dict[str, str]],
        ]
        | None
    ) = None
    custom_reflective_dataset: (
        Callable[
            [dict[str, str], EvaluationBatch[Any, Any], list[str]],
            Awaitable[Mapping[str, Sequence[Mapping[str, Any]]]],
        ]
        | None
    ) = None


class MockAdapter(AsyncGEPAAdapter[dict[str, str], dict[str, Any], Any]):
    """Simple mock adapter for testing engine behavior.

    This class provides a simple interface for tests that need to subclass
    the adapter to create custom variants. For most use cases, prefer
    the create_mock_adapter() factory.

    Attributes:
        call_count: Number of times evaluate was called.
        evaluate_calls: List of (batch, candidate, capture_traces) tuples.

    Examples:
        Basic usage:

        ```python
        adapter = MockAdapter(scores=[0.5, 0.6, 0.7])
        result = await adapter.evaluate(batch, candidate)
        ```

        Subclassing:

        ```python
        class CustomAdapter(MockAdapter):
            async def evaluate(self, batch, candidate, capture_traces=False):
                # Custom evaluation logic
                return EvaluationBatch(...)
        ```

    Note:
        This class maintains backward compatibility with tests that subclass
        MockAdapter. For new tests, prefer create_mock_adapter().
    """

    def __init__(self, scores: list[float] | None = None) -> None:
        """Initialize mock adapter with predetermined scores.

        Args:
            scores: List of scores to return sequentially. Defaults to [0.5].
        """
        self._scores = iter(scores) if scores else iter([0.5])
        self._call_count = 0
        self._evaluate_calls: list[tuple[Any, dict[str, str], bool]] = []

    @property
    def call_count(self) -> int:
        """Return number of evaluate calls."""
        return self._call_count

    @property
    def evaluate_calls(self) -> list[tuple[Any, dict[str, str], bool]]:
        """Return list of evaluate call arguments."""
        return self._evaluate_calls

    async def evaluate(
        self,
        batch: list[Any],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[dict[str, Any], Any]:
        """Evaluate candidate and return mock results.

        Args:
            batch: Input data instances.
            candidate: Candidate components.
            capture_traces: Whether to capture traces.

        Returns:
            Mock evaluation batch with predetermined scores.
        """
        self._call_count += 1
        self._evaluate_calls.append((batch, candidate, capture_traces))
        score = next(self._scores, 0.5)
        return EvaluationBatch(
            outputs=[None] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[dict[str, Any], Any],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build mock reflective dataset.

        Args:
            candidate: Current candidate components.
            eval_batch: Evaluation results.
            components_to_update: Components to generate datasets for.

        Returns:
            Mock reflective dataset.
        """
        return {comp: [] for comp in components_to_update}

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Generate mock text proposals.

        Args:
            candidate: Current candidate components.
            reflective_dataset: Reflective examples.
            components_to_update: Components to propose updates for.

        Returns:
            Mock proposals with improved text.
        """
        return {
            comp: f"Improved: {candidate.get(comp, '')}"
            for comp in components_to_update
        }


class ConfigurableMockAdapter(AsyncGEPAAdapter[dict[str, str], dict[str, Any], Any]):
    """Configurable mock adapter for testing engine behavior.

    This adapter consolidates all test-specific mock adapter variations into
    a single configurable implementation.

    Attributes:
        config: Adapter configuration controlling behavior.
        call_count: Number of times evaluate was called.
        evaluate_calls: List of (batch, candidate, capture_traces) tuples.
        propose_calls: List of (candidate, dataset, components) tuples.

    Examples:
        Basic usage:

        ```python
        adapter = ConfigurableMockAdapter(AdapterConfig(scores=[0.5, 0.6, 0.7]))
        result = await adapter.evaluate(batch, candidate)
        assert result.scores == [0.5] * len(batch)
        ```

        Check call history:

        ```python
        adapter = ConfigurableMockAdapter(AdapterConfig(track_calls=True))
        await adapter.evaluate([{"input": "test"}], {"instruction": "help"})
        assert adapter.call_count == 1
        assert adapter.evaluate_calls[0][1] == {"instruction": "help"}
        ```

    Note:
        Use create_mock_adapter() factory for simpler instantiation.
    """

    def __init__(self, config: AdapterConfig) -> None:
        """Initialize configurable mock adapter.

        Args:
            config: Configuration controlling adapter behavior.
        """
        self._config = config
        self._scores_iter = iter(config.scores)
        self._call_count = 0
        self._evaluate_calls: list[tuple[Any, dict[str, str], bool]] = []
        self._propose_calls: list[
            tuple[dict[str, str], Mapping[str, Sequence[Mapping[str, Any]]], list[str]]
        ] = []

    @property
    def config(self) -> AdapterConfig:
        """Return adapter configuration."""
        return self._config

    @property
    def call_count(self) -> int:
        """Return number of evaluate calls."""
        return self._call_count

    @property
    def evaluate_calls(self) -> list[tuple[Any, dict[str, str], bool]]:
        """Return list of evaluate call arguments."""
        return self._evaluate_calls

    @property
    def propose_calls(
        self,
    ) -> list[
        tuple[dict[str, str], Mapping[str, Sequence[Mapping[str, Any]]], list[str]]
    ]:
        """Return list of propose_new_texts call arguments."""
        return self._propose_calls

    def _get_next_score(self) -> float:
        """Get next score from iterator or default."""
        return next(self._scores_iter, self._config.default_score)

    def _generate_outputs(
        self, batch: list[Any], candidate: dict[str, str]
    ) -> list[Any]:
        """Generate outputs based on configured mode."""
        match self._config.output_mode:
            case OutputMode.NONE:
                return [None] * len(batch)
            case OutputMode.CANDIDATE_TEXT:
                text = candidate.get(self._config.output_component, "")
                return [text] * len(batch)
            case OutputMode.INDEXED:
                return [f"output_{i}" for i in range(len(batch))]
            case _:
                return [None] * len(batch)

    async def evaluate(
        self,
        batch: list[Any],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[dict[str, Any], Any]:
        """Evaluate candidate and return mock results.

        Args:
            batch: Input data instances.
            candidate: Candidate components.
            capture_traces: Whether to capture traces.

        Returns:
            Mock evaluation batch with configured scores and outputs.
        """
        if self._config.custom_evaluate is not None:
            return await self._config.custom_evaluate(batch, candidate, capture_traces)

        self._call_count += 1
        if self._config.track_calls:
            self._evaluate_calls.append((batch, candidate, capture_traces))

        score = self._get_next_score()
        outputs = self._generate_outputs(batch, candidate)
        trajectories = (
            [{"trace": i} for i in range(len(batch))] if capture_traces else None
        )
        objective_scores = (
            [self._config.objective_scores] * len(batch)
            if self._config.objective_scores is not None
            else None
        )

        return EvaluationBatch(
            outputs=outputs,
            scores=[score] * len(batch),
            trajectories=trajectories,
            objective_scores=objective_scores,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[dict[str, Any], Any],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build mock reflective dataset.

        Args:
            candidate: Current candidate components.
            eval_batch: Evaluation results.
            components_to_update: Components to generate datasets for.

        Returns:
            Mock reflective dataset mapping components to examples.
        """
        if self._config.custom_reflective_dataset is not None:
            return await self._config.custom_reflective_dataset(
                candidate, eval_batch, components_to_update
            )

        return {
            component: [
                {
                    "Inputs": {"candidate": candidate},
                    "Generated Outputs": eval_batch.outputs,
                    "Feedback": "ok",
                }
            ]
            for component in components_to_update
        }

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Generate mock text proposals.

        Args:
            candidate: Current candidate components.
            reflective_dataset: Reflective examples.
            components_to_update: Components to propose updates for.

        Returns:
            Mock proposals with improved text for each component.
        """
        if self._config.custom_propose is not None:
            return await self._config.custom_propose(
                candidate, reflective_dataset, components_to_update
            )

        if self._config.track_calls:
            self._propose_calls.append(
                (candidate, reflective_dataset, components_to_update)
            )

        return {
            component: f"Improved: {candidate.get(component, '')}"
            for component in components_to_update
        }


def create_mock_adapter(
    *,
    scores: list[float] | None = None,
    default_score: float = 0.5,
    objective_scores: dict[str, float] | None = None,
    output_mode: OutputMode = OutputMode.NONE,
    output_component: str = "instruction",
    track_calls: bool = True,
    custom_evaluate: (
        Callable[
            [list[Any], dict[str, str], bool],
            Awaitable[EvaluationBatch[Any, Any]],
        ]
        | None
    ) = None,
    custom_propose: (
        Callable[
            [dict[str, str], Mapping[str, Sequence[Mapping[str, Any]]], list[str]],
            Awaitable[dict[str, str]],
        ]
        | None
    ) = None,
    custom_reflective_dataset: (
        Callable[
            [dict[str, str], EvaluationBatch[Any, Any], list[str]],
            Awaitable[Mapping[str, Sequence[Mapping[str, Any]]]],
        ]
        | None
    ) = None,
) -> ConfigurableMockAdapter:
    """Factory for creating mock adapters with configurable behavior.

    Args:
        scores: List of scores to return sequentially. Defaults to [0.5].
        default_score: Score to return when scores list is exhausted.
        objective_scores: Optional objective scores dict per example.
        output_mode: How to generate output values.
        output_component: Component name for CANDIDATE_TEXT output mode.
        track_calls: Whether to record evaluate calls for inspection.
        custom_evaluate: Optional custom evaluate implementation.
        custom_propose: Optional custom propose implementation.
        custom_reflective_dataset: Optional custom reflective dataset implementation.

    Returns:
        Configured mock adapter instance.

    Examples:
        Basic adapter with scores:

        ```python
        adapter = create_mock_adapter(scores=[0.5, 0.6, 0.7])
        ```

        Adapter with objective scores:

        ```python
        adapter = create_mock_adapter(
            scores=[0.5, 0.6],
            objective_scores={"accuracy": 0.9, "latency": 0.8},
        )
        ```

        Adapter returning candidate text as output:

        ```python
        adapter = create_mock_adapter(
            scores=[0.5],
            output_mode=OutputMode.CANDIDATE_TEXT,
            output_component="instruction",
        )
        ```

    Note:
        This factory replaces multiple MockAdapter variants across the test suite.
        See AdapterConfig for all available options.
    """
    config = AdapterConfig(
        scores=scores if scores is not None else [0.5],
        default_score=default_score,
        objective_scores=objective_scores,
        output_mode=output_mode,
        output_component=output_component,
        track_calls=track_calls,
        custom_evaluate=custom_evaluate,
        custom_propose=custom_propose,
        custom_reflective_dataset=custom_reflective_dataset,
    )
    return ConfigurableMockAdapter(config)

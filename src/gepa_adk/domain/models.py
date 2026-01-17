"""Domain models for the gepa-adk evolution engine.

This module contains the core domain models used throughout the evolution
engine. All models are dataclasses following hexagonal architecture principles
with no external dependencies.

Attributes:
    EvolutionConfig (class): Configuration parameters for evolution runs.
    IterationRecord (class): Immutable record of a single iteration.
    EvolutionResult (class): Immutable outcome of a completed evolution run.
    Candidate (class): Mutable instruction candidate being evolved.

Note:
    These models are pure data containers with validation logic. They have
    no knowledge of infrastructure concerns like databases or APIs.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.types import FrontierType


@dataclass(slots=True, kw_only=True)
class EvolutionConfig:
    """Configuration parameters for an evolution run.

    Defines the parameters that control how evolution proceeds, including
    iteration limits, concurrency settings, and stopping criteria.

    Attributes:
        max_iterations (int): Maximum number of evolution iterations. 0 means
            just evaluate baseline without evolving.
        max_concurrent_evals (int): Number of concurrent batch evaluations.
            Must be at least 1.
        min_improvement_threshold (float): Minimum score improvement to accept
            a new candidate. Set to 0.0 to accept any improvement.
        patience (int): Number of iterations without improvement before stopping
            early. Set to 0 to disable early stopping.
        reflection_model (str): Model identifier for reflection/mutation
            operations.
        frontier_type (FrontierType): Frontier tracking strategy for Pareto
            selection (default: INSTANCE).
        acceptance_metric (Literal["sum", "mean"]): Aggregation method for
            acceptance decisions on iteration evaluation batches. "sum" uses
            sum of scores (default, aligns with upstream GEPA). "mean" uses
            mean of scores (legacy behavior).
        use_merge (bool): Enable merge proposals for genetic crossover.
            Defaults to False.
        max_merge_invocations (int): Maximum number of merge attempts per run.
            Defaults to 10. Must be non-negative.

    Examples:
        Creating a configuration with defaults:

        ```python
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(max_iterations=100, patience=10)
        print(config.max_iterations)  # 100
        print(config.reflection_model)  # ollama_chat/gpt-oss:20b
        ```

    Note:
        All numeric parameters are validated in __post_init__ to ensure
        they meet their constraints. Invalid values raise ConfigurationError.
    """

    max_iterations: int = 50
    max_concurrent_evals: int = 5
    min_improvement_threshold: float = 0.01
    patience: int = 5
    reflection_model: str = "ollama_chat/gpt-oss:20b"
    frontier_type: FrontierType = FrontierType.INSTANCE
    acceptance_metric: Literal["sum", "mean"] = "sum"
    use_merge: bool = False
    max_merge_invocations: int = 10

    def __post_init__(self) -> None:
        """Validate configuration parameters after initialization.

        Raises:
            ConfigurationError: If any parameter violates its constraints.

        Note:
            Called automatically by dataclass after __init__. Validates
            all fields and raises ConfigurationError with context on failure.
        """
        if self.max_iterations < 0:
            raise ConfigurationError(
                "max_iterations must be non-negative",
                field="max_iterations",
                value=self.max_iterations,
                constraint=">= 0",
            )

        if self.max_concurrent_evals < 1:
            raise ConfigurationError(
                "max_concurrent_evals must be at least 1",
                field="max_concurrent_evals",
                value=self.max_concurrent_evals,
                constraint=">= 1",
            )

        if self.min_improvement_threshold < 0.0:
            raise ConfigurationError(
                "min_improvement_threshold must be non-negative",
                field="min_improvement_threshold",
                value=self.min_improvement_threshold,
                constraint=">= 0.0",
            )

        if self.patience < 0:
            raise ConfigurationError(
                "patience must be non-negative",
                field="patience",
                value=self.patience,
                constraint=">= 0",
            )

        if not self.reflection_model:
            raise ConfigurationError(
                "reflection_model must be a non-empty string",
                field="reflection_model",
                value=self.reflection_model,
                constraint="non-empty string",
            )

        if not isinstance(self.frontier_type, FrontierType):
            try:
                self.frontier_type = FrontierType(self.frontier_type)
            except ValueError as exc:
                raise ConfigurationError(
                    "frontier_type must be a supported FrontierType value",
                    field="frontier_type",
                    value=self.frontier_type,
                    constraint=", ".join(t.value for t in FrontierType),
                ) from exc

        if self.acceptance_metric not in ("sum", "mean"):
            raise ConfigurationError(
                "acceptance_metric must be 'sum' or 'mean'",
                field="acceptance_metric",
                value=self.acceptance_metric,
                constraint="sum|mean",
            )

        if self.max_merge_invocations < 0:
            raise ConfigurationError(
                "max_merge_invocations must be non-negative",
                field="max_merge_invocations",
                value=self.max_merge_invocations,
                constraint=">= 0",
            )


@dataclass(slots=True, frozen=True, kw_only=True)
class IterationRecord:
    """Captures metrics for a single evolution iteration.

    This is an immutable record of what happened during one iteration
    of the evolution process. Records are created by the engine and
    stored in EvolutionResult.iteration_history.

    Attributes:
        iteration_number (int): 1-indexed iteration number for human
            readability.
        score (float): Score achieved in this iteration (typically in
            [0.0, 1.0]).
        instruction (str): The instruction text that was evaluated.
        accepted (bool): Whether this proposal was accepted as the new best.
        objective_scores (list[dict[str, float]] | None): Optional per-example
            multi-objective scores from the valset evaluation. None when adapter
            does not provide objective scores. Each dict maps objective name to
            score value. Index-aligned with evaluation batch examples.

    Examples:
        Creating an iteration record:

        ```python
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1, score=0.85, instruction="Be helpful", accepted=True
        )
        print(record.score)  # 0.85
        print(record.accepted)  # True
        ```

    Note:
        An immutable record that captures iteration metrics. Once created,
        IterationRecord instances cannot be modified, ensuring historical
        accuracy of the evolution trace.
    """

    iteration_number: int
    score: float
    instruction: str
    accepted: bool
    objective_scores: list[dict[str, float]] | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class EvolutionResult:
    """Outcome of a completed evolution run.

    Contains the final results after evolution completes, including
    the best instruction found, performance metrics, and full history.

    Attributes:
        original_score (float): Starting performance score (baseline).
        final_score (float): Ending performance score (best achieved).
        evolved_instruction (str): The optimized instruction text.
        iteration_history (list[IterationRecord]): Chronological list of
            iteration records.
        total_iterations (int): Number of iterations performed.
        valset_score (float | None): Score on validation set used for
            acceptance decisions. None if no validation set was used.
        trainset_score (float | None): Score on trainset used for reflection
            diagnostics. None if not computed.
        objective_scores (list[dict[str, float]] | None): Optional per-example
            multi-objective scores from the best candidate's final evaluation.
            None when no objective scores were tracked. Each dict maps objective
            name to score value. Index-aligned with evaluation batch examples.

    Examples:
        Creating and analyzing a result:

        ```python
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_instruction="Be helpful and concise",
            iteration_history=[],
            total_iterations=10,
        )
        print(result.improvement)  # 0.25
        print(result.improved)  # True
        ```

    Note:
        As a frozen dataclass, EvolutionResult instances cannot be modified.
    """

    original_score: float
    final_score: float
    evolved_instruction: str
    iteration_history: list[IterationRecord]
    total_iterations: int
    valset_score: float | None = None
    trainset_score: float | None = None
    objective_scores: list[dict[str, float]] | None = None

    @property
    def improvement(self) -> float:
        """Calculate the score improvement from original to final.

        Returns:
            The difference between final_score and original_score.
            Positive values indicate improvement, negative indicates degradation.

        Note:
            Override is not needed since frozen dataclasses support properties.
        """
        return self.final_score - self.original_score

    @property
    def improved(self) -> bool:
        """Check if the final score is better than the original.

        Returns:
            True if final_score > original_score, False otherwise.

        Note:
            Only returns True for strict improvement, not equal scores.
        """
        return self.final_score > self.original_score


@dataclass(slots=True, kw_only=True)
class Candidate:
    """Represents an instruction candidate being evolved.

    Unlike GEPA's simple `dict[str, str]` type alias, this class provides
    richer state tracking for async scenarios including lineage and metadata.

    Attributes:
        components (dict[str, str]): Component name to text value mapping.
            Common keys include 'instruction' (main agent prompt) and
            'output_schema'.
        generation (int): Generation number in the evolution lineage
            (0 = initial).
        parent_id (str | None): ID of the parent candidate for lineage
            tracking (legacy field, retained for compatibility).
        parent_ids (list[int] | None): Multi-parent indices for merge operations.
            None for seed candidates, [single_idx] for mutations, [idx1, idx2] for merges.
        metadata (dict[str, Any]): Extensible metadata dict for async tracking
            and debugging.

    Examples:
        Creating a candidate:

        ```python
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(
            components={"instruction": "Be helpful"},
            generation=0,
        )
        print(candidate.components["instruction"])  # Be helpful
        print(candidate.generation)  # 0
        ```

    Note:
        A mutable candidate representation with richer state tracking than
        GEPA's simple dict. Components and metadata can be modified during
        the evolution process. Use generation and parent_id to track lineage.
    """

    components: dict[str, str] = field(default_factory=dict)
    generation: int = 0
    parent_id: str | None = None
    parent_ids: list[int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class MultiAgentEvolutionResult:
    """Outcome of a completed multi-agent evolution run.

    Contains evolved instructions for all agents in the group,
    along with performance metrics and evolution history.

    Attributes:
        evolved_instructions (dict[str, str]): Mapping of agent name to evolved instruction.
        original_score (float): Starting performance score (baseline).
        final_score (float): Ending performance score (best achieved).
        primary_agent (str): Name of the agent whose output was used for scoring.
        iteration_history (list[IterationRecord]): Chronological list of iteration records.
        total_iterations (int): Number of iterations performed.

    Examples:
        Creating and analyzing a multi-agent result:

        ```python
        from gepa_adk.domain.models import MultiAgentEvolutionResult, IterationRecord

        result = MultiAgentEvolutionResult(
            evolved_instructions={
                "generator": "Generate high-quality code",
                "critic": "Review code thoroughly",
            },
            original_score=0.60,
            final_score=0.85,
            primary_agent="generator",
            iteration_history=[],
            total_iterations=10,
        )
        print(result.improvement)  # 0.25
        print(result.improved)  # True
        print(result.agent_names)  # ["critic", "generator"]
        ```

    Note:
        An immutable result container for multi-agent evolution. Once created,
        MultiAgentEvolutionResult instances cannot be modified. Use computed
        properties like `improvement`, `improved`, and `agent_names` to analyze
        results without modifying the underlying data.
    """

    evolved_instructions: dict[str, str]
    original_score: float
    final_score: float
    primary_agent: str
    iteration_history: list[IterationRecord]
    total_iterations: int

    @property
    def improvement(self) -> float:
        """Calculate the score improvement from original to final.

        Returns:
            The difference between final_score and original_score.
            Positive values indicate improvement, negative indicates degradation.

        Note:
            Override is not needed since frozen dataclasses support properties.
        """
        return self.final_score - self.original_score

    @property
    def improved(self) -> bool:
        """Check if the final score is better than the original.

        Returns:
            True if final_score > original_score, False otherwise.

        Note:
            Only returns True for strict improvement, not equal scores.
        """
        return self.final_score > self.original_score

    @property
    def agent_names(self) -> list[str]:
        """Get sorted list of evolved agent names.

        Returns:
            Sorted list of agent names from evolved_instructions keys.

        Note:
            Outputs a new list each time, sorted alphabetically for
            consistent ordering regardless of insertion order.
        """
        return sorted(self.evolved_instructions.keys())


__all__ = [
    "EvolutionConfig",
    "IterationRecord",
    "EvolutionResult",
    "Candidate",
    "MultiAgentEvolutionResult",
]

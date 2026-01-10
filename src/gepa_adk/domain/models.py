"""Domain models for the gepa-adk evolution engine.

This module contains the core domain models used throughout the evolution
engine. All models are dataclasses following hexagonal architecture principles
with no external dependencies.

Note:
    These models are pure data containers with validation logic. They have
    no knowledge of infrastructure concerns like databases or APIs.
"""

from dataclasses import dataclass, field
from typing import Any

from gepa_adk.domain.exceptions import ConfigurationError


@dataclass(slots=True, kw_only=True)
class EvolutionConfig:
    """Configuration parameters for an evolution run.

    Defines the parameters that control how evolution proceeds, including
    iteration limits, concurrency settings, and stopping criteria.

    Attributes:
        max_iterations: Maximum number of evolution iterations. 0 means
            just evaluate baseline without evolving.
        max_concurrent_evals: Number of concurrent batch evaluations.
            Must be at least 1.
        min_improvement_threshold: Minimum score improvement to accept
            a new candidate. Set to 0.0 to accept any improvement.
        patience: Number of iterations without improvement before stopping
            early. Set to 0 to disable early stopping.
        reflection_model: Model identifier for reflection/mutation operations.

    Note:
        All numeric parameters are validated in __post_init__ to ensure
        they meet their constraints. Invalid values raise ConfigurationError.
    """

    max_iterations: int = 50
    max_concurrent_evals: int = 5
    min_improvement_threshold: float = 0.01
    patience: int = 5
    reflection_model: str = "gemini-2.0-flash"

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


@dataclass(slots=True, frozen=True, kw_only=True)
class IterationRecord:
    """Captures metrics for a single evolution iteration.

    This is an immutable record of what happened during one iteration
    of the evolution process. Records are created by the engine and
    stored in EvolutionResult.iteration_history.

    Attributes:
        iteration_number: 1-indexed iteration number for human readability.
        score: Score achieved in this iteration (typically in [0.0, 1.0]).
        instruction: The instruction text that was evaluated.
        accepted: Whether this proposal was accepted as the new best.

    Note:
        Once created, IterationRecord instances cannot be modified.
        This ensures historical accuracy of the evolution trace.
    """

    iteration_number: int
    score: float
    instruction: str
    accepted: bool


@dataclass(slots=True, frozen=True, kw_only=True)
class EvolutionResult:
    """Outcome of a completed evolution run.

    Contains the final results after evolution completes, including
    the best instruction found, performance metrics, and full history.

    Attributes:
        original_score: Starting performance score (baseline).
        final_score: Ending performance score (best achieved).
        evolved_instruction: The optimized instruction text.
        iteration_history: Chronological list of iteration records.
        total_iterations: Number of iterations performed.

    Note:
        Once created, EvolutionResult instances cannot be modified.
        Use computed properties like `improvement` and `improved` to
        analyze results without modifying the underlying data.
    """

    original_score: float
    final_score: float
    evolved_instruction: str
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


@dataclass(slots=True, kw_only=True)
class Candidate:
    """Represents an instruction candidate being evolved.

    Unlike GEPA's simple `dict[str, str]` type alias, this class provides
    richer state tracking for async scenarios including lineage and metadata.

    Attributes:
        components: Component name to text value mapping. Common keys include
            'instruction' (main agent prompt) and 'output_schema'.
        generation: Generation number in the evolution lineage (0 = initial).
        parent_id: ID of the parent candidate for lineage tracking.
        metadata: Extensible metadata dict for async tracking and debugging.

    Note:
        Candidates are mutable - components and metadata can be modified
        during the evolution process. Use generation and parent_id to
        track the evolution lineage.
    """

    components: dict[str, str] = field(default_factory=dict)
    generation: int = 0
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["EvolutionConfig", "IterationRecord", "EvolutionResult", "Candidate"]

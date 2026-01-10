"""Domain models for evolution engine.

This module contains the core domain models for configuring and tracking
evolution runs.

Note: These models follow dataclass patterns with validation and immutability.
"""

from dataclasses import dataclass, field
from typing import Any

from gepa_adk.domain.exceptions import ConfigurationError


@dataclass(slots=True, kw_only=True)
class EvolutionConfig:
    """Configuration parameters for an evolution run.

    This dataclass provides sensible defaults for all evolution parameters
    while allowing customization for specific use cases.

    Attributes:
        max_iterations: Maximum number of evolution iterations. Default: 50.
            Set to 0 to skip evolution and only evaluate baseline.
        max_concurrent_evals: Number of concurrent evaluations in a batch.
            Default: 5. Must be >= 1.
        min_improvement_threshold: Minimum score improvement to accept a
            proposal. Default: 0.01. Must be >= 0.0.
        patience: Number of iterations without improvement before early
            stopping. Default: 5. Set to 0 to never stop early.
        reflection_model: Model identifier for reflection and mutation.
            Default: "gemini-2.0-flash". Must be non-empty.

    Raises:
        ConfigurationError: If validation fails during __post_init__.

    Example:
        >>> config = EvolutionConfig()
        >>> config.max_iterations
        50
        >>> config = EvolutionConfig(max_iterations=100, patience=10)
        >>> config.max_iterations
        100

    Note: This class validates all parameters in __post_init__.
    """

    max_iterations: int = 50
    max_concurrent_evals: int = 5
    min_improvement_threshold: float = 0.01
    patience: int = 5
    reflection_model: str = "gemini-2.0-flash"

    def __post_init__(self):
        """Validate configuration parameters.

        Raises:
            ConfigurationError: If any validation constraint is violated.

        Note: This method is called automatically after initialization.
        """
        if self.max_iterations < 0:
            raise ConfigurationError(
                message=f"max_iterations must be >= 0, got {self.max_iterations}",
                field="max_iterations",
                value=self.max_iterations,
                constraint=">= 0",
            )

        if self.max_concurrent_evals < 1:
            raise ConfigurationError(
                message=f"max_concurrent_evals must be >= 1, got {self.max_concurrent_evals}",
                field="max_concurrent_evals",
                value=self.max_concurrent_evals,
                constraint=">= 1",
            )

        if self.min_improvement_threshold < 0.0:
            raise ConfigurationError(
                message=(
                    f"min_improvement_threshold must be >= 0.0, "
                    f"got {self.min_improvement_threshold}"
                ),
                field="min_improvement_threshold",
                value=self.min_improvement_threshold,
                constraint=">= 0.0",
            )

        if self.patience < 0:
            raise ConfigurationError(
                message=f"patience must be >= 0, got {self.patience}",
                field="patience",
                value=self.patience,
                constraint=">= 0",
            )

        if not self.reflection_model or not self.reflection_model.strip():
            raise ConfigurationError(
                message="reflection_model must be a non-empty string",
                field="reflection_model",
                value=self.reflection_model,
                constraint="non-empty string",
            )


@dataclass(slots=True, frozen=True, kw_only=True)
class IterationRecord:
    """Captures metrics for a single evolution iteration.

    This immutable dataclass records the outcome of evaluating a candidate
    instruction during evolution.

    Attributes:
        iteration_number: 1-indexed iteration number (1, 2, 3, ...).
        score: Score achieved in this iteration. Typically in [0.0, 1.0]
            but not enforced.
        instruction: Instruction text that was evaluated.
        accepted: Whether the proposal was accepted for the next iteration.

    Example:
        >>> record = IterationRecord(
        ...     iteration_number=1,
        ...     score=0.75,
        ...     instruction="You are a helpful assistant.",
        ...     accepted=True,
        ... )
        >>> record.score
        0.75
        >>> record.iteration_number
        1

    Note: This dataclass is frozen to ensure iteration history integrity.
    """

    iteration_number: int
    score: float
    instruction: str
    accepted: bool


@dataclass(slots=True, frozen=True, kw_only=True)
class EvolutionResult:
    """Outcome of a completed evolution run.

    This immutable dataclass captures the complete results of an evolution
    session, including the performance improvement and iteration history.

    Attributes:
        original_score: Starting performance (baseline score).
        final_score: Ending performance (best achieved score).
        evolved_instruction: The optimized instruction text.
        iteration_history: Chronological list of iteration records.
        total_iterations: Number of iterations performed.

    Properties:
        improvement: Computed as final_score - original_score.
        improved: True if final_score > original_score, False otherwise.

    Example:
        >>> result = EvolutionResult(
        ...     original_score=0.60,
        ...     final_score=0.85,
        ...     evolved_instruction="You are an expert.",
        ...     iteration_history=[],
        ...     total_iterations=3,
        ... )
        >>> result.improvement
        0.25
        >>> result.improved
        True

    Note: This dataclass is frozen to ensure result integrity.
    """

    original_score: float
    final_score: float
    evolved_instruction: str
    iteration_history: list["IterationRecord"]
    total_iterations: int

    @property
    def improvement(self) -> float:
        """Compute the score improvement from original to final.

        Returns:
            The difference between final_score and original_score.
            Positive values indicate improvement, negative values
            indicate degradation.

        Note: This is a computed property for convenience.
        """
        return self.final_score - self.original_score

    @property
    def improved(self) -> bool:
        """Check if evolution resulted in improvement.

        Returns:
            True if final_score > original_score, False otherwise.

        Note: Returns False when scores are equal (no improvement).
        """
        return self.final_score > self.original_score


@dataclass(slots=True, kw_only=True)
class Candidate:
    """Represents an instruction candidate being evolved.

    Unlike GEPA's `dict[str, str]` type alias, this class provides richer
    state tracking for async evolution scenarios, including lineage tracking
    and extensible metadata.

    Attributes:
        components: Component name → text value mapping (GEPA-compatible).
            Standard keys: "instruction", "output_schema".
        generation: Generation number in evolution lineage (default: 0).
        parent_id: Optional ID of parent candidate for lineage tracking.
        metadata: Extensible metadata dict for async tracking and diagnostics.

    Example:
        >>> candidate = Candidate(
        ...     components={"instruction": "You are a helpful assistant."}
        ... )
        >>> candidate.components["instruction"]
        'You are a helpful assistant.'
        >>> candidate.generation
        0
        >>> candidate.components["instruction"] = "You are an expert."
        >>> candidate.components["output_schema"] = "..."

    Note: This class uses field(default_factory=dict) for mutable defaults.
    """

    components: dict[str, str] = field(default_factory=dict)
    generation: int = 0
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

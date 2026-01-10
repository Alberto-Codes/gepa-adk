"""Domain models for evolution engine.

This module contains the core domain models for configuring and tracking
evolution runs.

Note: These models follow dataclass patterns with validation and immutability.
"""

from dataclasses import dataclass, field

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

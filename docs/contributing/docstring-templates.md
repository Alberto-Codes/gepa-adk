# Docstring Templates

These templates show the preferred Google-style docstrings for this repo and
are optimized for mkdocstrings rendering. Copy and adapt them for new modules,
classes, functions, and interfaces.

## Quick Guidance

- Use **Examples** (plural) for code samples with fenced code blocks (` ```python `).
- Use **Example** (singular) only for admonition-style callouts.
- **Prefer fenced code blocks** over doctest format (`>>>`) - they copy cleanly
  without prompt characters and render better in mkdocs-material.
- Include types in **Attributes** (e.g., `name (str): Description`) since types
  aren't visible from class/module-level attributes like they are in function Args.
- Use `Note:` and `Warning:` sections for short admonitions.
- Use `Warns:` for `warnings.warn(...)` emissions.
- Use `Other Parameters:` for optional keyword-only or `**kwargs` arguments (include types!).
- Keep the first line as a concise summary (imperative tone).
- Prefer relative cross-references like `[.name][]` or `[..module.Name][]`.

## Module Template (__init__.py)

Use this template for all package `__init__.py` files. **Required sections**: Attributes (all exports), Examples (import usage), See Also (related modules).

```python
"""Domain models and entities for gepa-adk.

This package contains the core domain models that represent the fundamental
concepts in genetic algorithm evolution, including configuration, iteration
records, results, and candidate solutions.

Attributes:
    EvolutionConfig (class): Configuration for evolution parameters.
    IterationRecord (class): Record of a single iteration's metrics.
    EvolutionResult (class): Complete evolution run results.
    Candidate (class): Individual solution candidate.

Examples:
    Basic usage with configuration:

    ```python
    from gepa_adk.domain import EvolutionConfig

    config = EvolutionConfig(
        max_iterations=100,
        population_size=50,
        mutation_rate=0.15
    )
    ```

See Also:
    - :mod:`gepa_adk.domain.exceptions`: Exception hierarchy.
    - :mod:`gepa_adk.domain.types`: Type aliases and constants.

Note:
    All models are immutable by default (frozen dataclasses) for thread safety.
"""
```

**Guidelines for Module Docstrings**:
- List **all** exported symbols in Attributes with their type: `(class)`, `(function)`, `(constant)`
- Include at least one practical Examples section showing import patterns
- Use `:mod:` syntax for cross-references to other packages (e.g., `:mod:`gepa_adk.domain``)

## Class Template

```python
class EvolutionEngine:
    """Execute genetic algorithm evolution runs.

    Attributes:
        config (EvolutionConfig): Evolution configuration parameters.
        population (list[Candidate]): Current population of candidates.

    Examples:
        Run evolution:

        ```python
        engine = EvolutionEngine(config)
        result = engine.run()
        assert result.best_score > 0
        ```

    See Also:
        - [`EvolutionConfig`][gepa_adk.domain.models.EvolutionConfig]:
          Configuration parameters.

    Note:
        Engine maintains population state across iterations for efficiency.
    """
```

## __init__ Method Template

```python
def __init__(
    self,
    config: EvolutionConfig,
    *,
    seed: int | None = None,
) -> None:
    """Initialize the evolution engine.

    Args:
        config: Evolution configuration parameters.

    Other Parameters:
        seed (int | None): Random seed for reproducibility.

    Raises:
        ConfigurationError: If configuration is invalid.

    Note:
        Random seed ensures reproducible evolution runs when provided.
    """
```

## Method Template

```python
def evolve_population(
    self,
    iterations: int,
) -> EvolutionResult:
    """Evolve the population for specified iterations.

    Args:
        iterations: Number of generations to evolve.

    Returns:
        EvolutionResult with best candidate and metrics.

    Raises:
        EvolutionError: If evolution fails.

    Examples:
        Evolve for 100 generations:

        ```python
        result = engine.evolve_population(100)
        print(f"Best score: {result.best_score}")
        ```

    Note:
        Each iteration applies selection, crossover, and mutation in sequence.
    """
```

## Helper Function Template

```python
def _calculate_fitness(candidate: Candidate) -> float:
    """Calculate fitness score for a candidate.

    Args:
        candidate: Solution candidate to evaluate.

    Returns:
        Fitness score (higher is better).

    Note:
        Uses weighted sum of objective functions for multi-criteria optimization.
    """
```

## Protocol / Interface Template

```python
from typing import Protocol


class FitnessFunction(Protocol):
    """Protocol for fitness evaluation functions.

    Examples:
        Implement a fitness function:

        ```python
        def my_fitness(candidate: Candidate) -> float:
            return sum(candidate.genes)
        ```
    """

    def __call__(self, candidate: Candidate) -> float:
        """Evaluate candidate fitness.

        Args:
            candidate: Solution candidate to evaluate.

        Returns:
            Fitness score (higher is better).
        """
```

## Dataclass Model Template

```python
from dataclasses import dataclass


@dataclass(slots=True)
class IterationRecord:
    """Record of a single evolution iteration.

    Attributes:
        iteration (int): Iteration number (0-indexed).
        best_score (float): Best fitness score in this iteration.
        avg_score (float): Average fitness score across population.
        diversity (float): Population diversity metric.

    Examples:
        Create a record:

        ```python
        record = IterationRecord(
            iteration=0,
            best_score=0.95,
            avg_score=0.67,
            diversity=0.42
        )
        assert record.best_score > record.avg_score
        ```
    """

    iteration: int
    best_score: float
    avg_score: float
    diversity: float
```

## Enum Template

```python
from enum import Enum


class SelectionStrategy(str, Enum):
    """Selection strategies for parent selection.

    Examples:
        Access enum value:

        ```python
        assert SelectionStrategy.TOURNAMENT.value == "tournament"
        ```
    """

    TOURNAMENT = "tournament"
    ROULETTE = "roulette"
    RANK = "rank"
```

## NamedTuple Template

```python
from typing import NamedTuple


class ScoreRange(NamedTuple):
    """Min and max fitness scores.

    Attributes:
        min_score (float): Minimum observed fitness.
        max_score (float): Maximum observed fitness.
    """

    min_score: float
    max_score: float
```

## TypedDict Template

```python
from typing import TypedDict


class EvolutionMetrics(TypedDict, total=False):
    """Serialized evolution metrics.

    Attributes:
        generations (int): Number of generations completed.
        best_score (float): Best fitness achieved.
        convergence (float): Convergence metric.
    """

    generations: int
    best_score: float
    convergence: float
```

## Exception Template

```python
class EvolutionError(Exception):
    """Base exception for evolution errors.

    Args:
        message: Human-readable error message.
        cause: Optional underlying exception.

    Note:
        All domain exceptions inherit from this base for consistent handling.
    """
```

## Function Template

```python
def create_population(
    size: int,
    *,
    gene_length: int = 10,
) -> list[Candidate]:
    """Create initial random population.

    Args:
        size: Number of candidates to generate.

    Other Parameters:
        gene_length (int): Number of genes per candidate.

    Returns:
        List of randomly initialized candidates.

    Examples:
        Create population:

        ```python
        population = create_population(50, gene_length=20)
        assert len(population) == 50
        ```
    """
```

## Generator Function Template

```python
from typing import Generator


def evolve_generations(
    config: EvolutionConfig,
) -> Generator[IterationRecord, None, None]:
    """Stream evolution progress by generation.

    Args:
        config: Evolution configuration.

    Yields:
        IterationRecord for each generation.

    Examples:
        Stream evolution:

        ```python
        for record in evolve_generations(config):
            print(f"Gen {record.iteration}: {record.best_score}")
        ```
    """
```

## Function That Emits Warnings

```python
def validate_config(config: EvolutionConfig) -> None:
    """Validate evolution configuration.

    Args:
        config: Configuration to validate.

    Warns:
        UserWarning: If configuration values are suboptimal.
    """
```

## Deprecated Function Template (PEP 702)

```python
from warnings import deprecated


@deprecated("Use `evolve_population()` instead. Will be removed in v2.0.")
def run_evolution(config: EvolutionConfig) -> EvolutionResult:
    """Run evolution with legacy algorithm.

    Args:
        config: Evolution configuration.

    Returns:
        Evolution results.

    See Also:
        - [`evolve_population()`][gepa_adk.core.evolve_population]:
          Preferred replacement API.
    """
```

## Supported Sections (Quick Reference)

These are the primary sections recognized by Griffe/mkdocstrings for Google
style docstrings. Aliases are shown in parentheses.

| Section | Purpose | Aliases |
| --- | --- | --- |
| `Args` | Parameters for functions/methods | `Arguments`, `Params` |
| `Other Parameters` | Secondary `**kwargs` (include types!) | `Keyword Args`, `Keyword Arguments`, `Other Args`, `Other Arguments`, `Other Params` |
| `Returns` | Return values | |
| `Yields` | Generator yields | |
| `Receives` | Generator `.send()` values | |
| `Raises` | Exceptions raised | |
| `Warns` | Warnings emitted | `Warnings` |
| `Attributes` | Module/class attributes | |
| `Examples` | Fenced code block examples (prefer ` ```python `) | |
| `See Also` | Related APIs | |
| `Note` | Brief admonitions | |
| `Warning` | Important warnings | |
| `Deprecated` | Manual deprecation notice (use `@deprecated` decorator instead) | |

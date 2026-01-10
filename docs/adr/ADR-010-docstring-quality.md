# ADR-010: Docstring Quality Standards

> **Status**: Accepted
> **Date**: 2026-01-10
> **Deciders**: gepa-adk maintainers

## Context

Documentation serves multiple audiences:
- **Users**: Understanding gepa-adk's public APIs through rendered documentation
- **Developers**: Inline context while reading/modifying code
- **Tooling**: Type checkers, linters, IDE autocomplete

We use [mkdocs-material](https://squidfunk.github.io/mkdocs-material/) with [mkdocstrings-python](https://mkdocstrings.github.io/python/) which parses Google-style docstrings to generate API documentation.

**Problem**: Docstrings can be:
- Present but **incorrect** (Args don't match code)
- Accurate but **stale** (code changed, docstring didn't)
- Compliant but **minimal** (missing Examples, Attributes)

## Decision

### Convention: Google-Style Docstrings

Follow [Google's Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) exclusively.

### Supported Sections

**Core Sections** (validated by tools):

| Section | Purpose |
|---------|---------|
| **Args** | Function/method parameters |
| **Returns** | Return value type and description |
| **Yields** | Values yielded by generators |
| **Raises** | Exceptions that may be raised |
| **Attributes** | Class attributes |
| **Examples** | Usage examples with fenced code blocks |

**Admonition Sections** (rendered as callout boxes):

| Section | Rendering | Use Case |
|---------|-----------|----------|
| **Note** | Blue info box | Implementation details, caveats |
| **Warning** | Orange warning box | Critical warnings about misuse |
| **Tip** | Green tip box | Best practices, suggestions |
| **See Also** | Bullet list with links | Cross-references to related modules |

### Quality Dimensions

```
+---------------------------------------------------------------+
|                    Docstring Quality Model                     |
+---------------------------------------------------------------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
+----------------------+           +----------------------+
|   1. COMPLIANCE      |           |    2. COVERAGE       |
|   Do sections match  |           |   Does it exist?     |
|   the code?          |           |                      |
|                      |           |                      |
|   Tool: ruff D rules |           |   Tool: interrogate  |
|                      |           |   Target: 95%+       |
+----------------------+           +----------------------+
```

---

## Enforcement Tools

### 1. Coverage: interrogate

**What it checks**: Docstring presence (modules, classes, functions)

```toml
# pyproject.toml (already configured)
[tool.interrogate]
verbose = 1
fail-under = 95
ignore-init-method = true
ignore-init-module = true
ignore-magic = true
ignore-private = true
exclude = ["tests", "scripts"]
```

### 2. Style: ruff pydocstyle

**What it checks**: Google-style compliance

```toml
# pyproject.toml (already configured)
[tool.ruff.lint]
extend-select = ["D"]  # pydocstyle

[tool.ruff.lint.pydocstyle]
convention = "google"
```

---

## Usage Guidelines

### Public Functions

**Required sections**:
- Summary (first line)
- Args (if has parameters)
- Returns (if returns non-None)
- Raises (if raises exceptions)

```python
async def evolve(
    agent: LlmAgent,
    trainset: list[dict],
    *,
    critic: LlmAgent | None = None,
    config: EvolutionConfig | None = None,
) -> EvolutionResult:
    """Evolve agent instructions using GEPA algorithm.

    Args:
        agent: ADK agent to evolve.
        trainset: Training examples with input/expected pairs.
        critic: Optional critic agent for scoring.
        config: Evolution configuration.

    Returns:
        EvolutionResult with evolved instruction and metrics.

    Raises:
        EvaluationError: If agent execution fails.
        ConfigurationError: If config is invalid.

    Examples:
        Basic evolution:

        ```python
        result = await evolve(agent, trainset, critic=critic)
        print(result.evolved_instruction)
        ```
    """
```

### Public Classes

**Required sections**:
- Summary (first line)
- Attributes (if has instance attributes)
- Examples (for complex classes)

```python
class AsyncGEPAEngine:
    """Async-first evolution engine implementing GEPA algorithm.

    This engine orchestrates the evolution loop: evaluate, propose,
    accept/reject, repeat until convergence or max iterations.

    Attributes:
        adapter: AsyncGEPAAdapter for agent evaluation.
        config: Evolution configuration.
        proposer: Mutation proposer for generating candidates.

    Examples:
        Using with mock adapter:

        ```python
        engine = AsyncGEPAEngine(adapter=mock_adapter, config=config)
        result = await engine.run()
        ```
    """
```

### Protocol Definitions

Document the contract clearly:

```python
class AsyncGEPAAdapter(Protocol):
    """Protocol for async GEPA adapters.

    Implementations must provide async methods for evaluation,
    reflective dataset creation, and proposal generation.

    All methods are coroutines to enable concurrent execution.
    """

    async def evaluate(
        self,
        batch: list[DataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Execute candidate on batch.

        Args:
            batch: Input examples to evaluate.
            candidate: Candidate instruction texts.
            capture_traces: Whether to capture execution traces.

        Returns:
            EvaluationBatch with outputs, scores, and trajectories.
        """
        ...
```

---

## When to Use Admonitions

**Note** (Blue): Implementation details, performance characteristics

```python
async def evaluate_batch(self, batch: list[DataInst]) -> EvaluationBatch:
    """Evaluate batch with controlled concurrency.

    Note:
        Concurrency is limited by `config.max_concurrent_evals`.
        Default is 5 parallel evaluations.
    """
```

**Warning** (Orange): Critical warnings, common pitfalls

```python
def evolve_sync(agent: LlmAgent, trainset: list[dict], **kwargs) -> EvolutionResult:
    """Synchronous wrapper for evolve().

    Warning:
        Creates new event loop internally. Do NOT call from
        existing async context - use `evolve()` directly instead.
    """
```

**See Also** (Bullet list): Cross-references to related modules

```python
"""Package docstring.

See Also:
    - [`gepa_adk.domain`][gepa_adk.domain]: Core domain models.
    - [`gepa_adk.ports`][gepa_adk.ports]: Port interfaces.
"""
```

> **Syntax**: Use `` [`display.text`][target.identifier] `` for mkdocstrings cross-references.
> Sphinx-style `:mod:` syntax is **not supported** by mkdocstrings.

---

## What NOT to Document

| Don't Document | Why | Alternative |
|----------------|-----|-------------|
| Private functions (`_helper`) | Internal implementation | Inline comments if complex |
| Self-evident parameters | Noise without value | Skip obvious Args |
| Type info in docstrings | Duplicates type hints | Use type hints in signature |

**Example of over-documentation**:

```python
# Don't do this
def add(a: int, b: int) -> int:
    """Add two numbers.

    Args:
        a: The first integer to add.
        b: The second integer to add.

    Returns:
        The sum of a and b as an integer.
    """
    return a + b
```

**Better**:

```python
# Do this
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

---

## Workflow

### Development

1. Write code with docstrings following Google style
2. Run `uv run ruff check --fix` to check style
3. Run `uv run interrogate -v src/` to check coverage
4. Commit

### CI/CD

- **Pre-commit**: ruff D rules (blocks if style violations)
- **Pre-commit**: interrogate (blocks if coverage <95%)

---

## Consequences

### Positive

- Consistent docstring style across codebase
- Automated enforcement via existing tools
- Beautiful rendered documentation via mkdocs-material
- Clear guidelines for contributors

### Negative

- Learning curve for Google-style sections
- Time investment to document existing code

### Neutral

- Documentation quality is measurable and trackable

---

## References

- [Google Python Style Guide: Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [mkdocstrings-python: Google Style](https://mkdocstrings.github.io/python/usage/docstrings/google/)
- [interrogate Documentation](https://interrogate.readthedocs.io/)
- **ADR-005**: Three-Layer Testing Strategy

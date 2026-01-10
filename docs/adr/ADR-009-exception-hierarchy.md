# ADR-009: Exception Hierarchy

> **Status**: Accepted
> **Date**: 2026-01-10
> **Deciders**: gepa-adk maintainers

## Context

gepa-adk needs a consistent exception handling strategy for:

1. **Evolution failures**: Batch evaluation errors, proposal generation failures
2. **Scoring failures**: Critic agent errors, malformed output
3. **External library errors**: ADK exceptions, LiteLLM errors
4. **User errors**: Invalid configuration, missing agents

We need exceptions that:
- Provide clear error messages
- Preserve the original cause for debugging
- Enable specific error handling by callers
- Follow Python best practices

## Decision

Adopt a **hierarchical exception pattern** with:
1. Base `EvolutionError` exception
2. Specific subclasses for different failure modes
3. `cause` attribute for exception chaining
4. Keyword-only arguments after `message`

### Exception Hierarchy

```python
# domain/exceptions.py
from typing import Any

class EvolutionError(Exception):
    """Base exception for all gepa-adk evolution operations.

    Attributes:
        message: Human-readable error description.
        cause: Original exception that caused this error (for chaining).
        context: Additional context dict for debugging.
    """

    def __init__(
        self,
        message: str,
        *,  # Force keyword arguments after message
        cause: Exception | None = None,
        **context: Any,
    ) -> None:
        """Initialize EvolutionError.

        Args:
            message: Human-readable error description.
            cause: Original exception that caused this error.
            **context: Additional context for debugging (e.g., agent_name, iteration).
        """
        self.message = message
        self.cause = cause
        self.context = context
        super().__init__(message)

    def __str__(self) -> str:
        """Format error with cause chain if present."""
        base = self.message
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            base = f"{base} [{ctx_str}]"
        if self.cause:
            base = f"{base} (caused by: {self.cause})"
        return base


class EvaluationError(EvolutionError):
    """Raised when batch evaluation fails.

    Examples:
        - Agent execution timeout
        - ADK runner error
        - Malformed agent output
    """
    pass


class ProposalError(EvolutionError):
    """Raised when instruction proposal fails.

    Examples:
        - Reflection model error
        - Invalid proposal format
        - State key validation failure
    """
    pass


class ScoringError(EvolutionError):
    """Raised when critic scoring fails.

    Examples:
        - Critic agent error
        - Missing score field in output
        - Score out of valid range
    """
    pass


class ConfigurationError(EvolutionError):
    """Raised for invalid evolution configuration.

    Examples:
        - Invalid max_iterations value
        - Missing required agent
        - Incompatible settings
    """
    pass
```

### Usage Pattern

#### Wrapping External Exceptions

```python
from google.adk.errors import ADKError
from gepa_adk.domain.exceptions import EvaluationError

async def evaluate_agent(agent_name: str, input_text: str) -> str:
    try:
        result = await self.runner.run_async(
            agent_name=agent_name,
            input_text=input_text,
        )
        return result.output
    except ADKError as e:
        raise EvaluationError(
            "Agent execution failed",
            cause=e,
            agent_name=agent_name,
            input_text=input_text[:100],  # Truncate for logging
        ) from e  # Use both cause attribute AND from e
```

#### Handling Specific Exceptions

```python
from gepa_adk import evolve
from gepa_adk.domain.exceptions import (
    EvolutionError,
    EvaluationError,
    ScoringError,
)

async def run_evolution_with_retry():
    try:
        result = await evolve(agent, trainset, critic=critic)
        return result
    except ScoringError as e:
        # Critic agent issue - maybe retry with different critic
        logger.warning(f"Scoring failed: {e}")
        return await evolve(agent, trainset, critic=backup_critic)
    except EvaluationError as e:
        # Agent execution issue - log and fail
        logger.error(f"Agent failed: {e}")
        raise
    except EvolutionError as e:
        # Catch-all for other evolution errors
        logger.error(f"Evolution error: {e}")
        raise
```

#### Accessing Cause Chain

```python
try:
    result = await evolve(agent, trainset)
except EvolutionError as e:
    print(f"Error: {e.message}")
    print(f"Context: {e.context}")
    if e.cause:
        print(f"Caused by: {type(e.cause).__name__}: {e.cause}")
```

### Key Design Decisions

#### 1. Keyword-Only Arguments

```python
# ✅ CORRECT: Forces explicit naming
raise EvaluationError("Agent failed", cause=e, agent_name="my_agent")

# ❌ WRONG: Positional args are ambiguous
raise EvaluationError("Agent failed", e, "my_agent")  # TypeError
```

#### 2. Both `cause` Attribute AND `from e`

```python
# Use BOTH for full compatibility
raise EvaluationError(..., cause=e) from e
```

- `cause` attribute: Custom attribute for programmatic access
- `from e`: Python's standard exception chaining (`__cause__`)

#### 3. Context Dict for Debugging

```python
raise ScoringError(
    "Score out of range",
    cause=None,
    score=1.5,           # Captured in context
    valid_range=(0, 1),  # Captured in context
    agent_name="critic",
)
# Output: Score out of range [score=1.5, valid_range=(0, 1), agent_name='critic']
```

### Exception → HTTP Status Mapping (for API consumers)

If exposing gepa-adk via HTTP API:

| Exception | HTTP Status | Reason |
|-----------|-------------|--------|
| `ConfigurationError` | 400 Bad Request | User error |
| `EvaluationError` | 502 Bad Gateway | Upstream (ADK) error |
| `ScoringError` | 502 Bad Gateway | Upstream (critic) error |
| `ProposalError` | 502 Bad Gateway | Upstream (reflection) error |
| `EvolutionError` | 500 Internal Error | Generic failure |

## Consequences

### Positive

- **Clear error types**: Callers can handle specific failures
- **Debuggable**: Cause chain preserved for troubleshooting
- **Consistent**: All exceptions follow same pattern
- **Extensible**: Easy to add new exception types

### Negative

- **More code**: Multiple exception classes to maintain
- **Learning curve**: Users must understand hierarchy
- **Overhead**: Creating exception objects has (minimal) cost

### Neutral

- **Testing**: Need to test exception raising and chaining
- **Documentation**: Each exception type needs clear docstring

## Alternatives Considered

### 1. Single Exception Class

```python
class EvolutionError(Exception):
    def __init__(self, message, error_type="unknown"):
        self.error_type = error_type
```

**Rejected**: Requires string matching instead of `except` clauses.

### 2. Error Codes

```python
class EvolutionError(Exception):
    EVALUATION_FAILED = 1001
    SCORING_FAILED = 1002
```

**Rejected**: Unidiomatic Python; exception hierarchy is standard.

### 3. No Custom Exceptions

```python
# Just use built-in exceptions
raise ValueError("Invalid configuration")
raise RuntimeError("Evaluation failed")
```

**Rejected**: Loses domain-specific semantics; hard to catch gepa-adk errors specifically.

### 4. Result Type Instead of Exceptions

```python
from dataclasses import dataclass

@dataclass
class EvolutionResult:
    success: bool
    value: Any | None
    error: str | None
```

**Rejected**: Unidiomatic Python; exceptions are the standard error mechanism.

## References

- [Python Exception Handling Best Practices](https://docs.python.org/3/tutorial/errors.html)
- [PEP 3134 – Exception Chaining](https://peps.python.org/pep-3134/)
- **ADR-008**: Structured Logging Pattern (log exceptions with context)
- [ADR Index](README.md) - All architectural decisions

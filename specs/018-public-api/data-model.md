# Data Model: Public API (evolve, evolve_sync)

**Feature**: 018-public-api  
**Date**: 2026-01-12  
**Phase**: 1 - Design

## Entities

### Existing Entities (No Changes)

| Entity | Location | Description |
|--------|----------|-------------|
| `EvolutionResult` | `domain/models.py` | Immutable evolution outcome |
| `EvolutionConfig` | `domain/models.py` | Evolution parameters |
| `TrajectoryConfig` | `domain/types.py` | Trace capture settings |
| `Candidate` | `domain/models.py` | Instruction being evolved |
| `IterationRecord` | `domain/models.py` | Single iteration metrics |

### Input Data Format

**Trainset/Valset Structure**:
```python
# Type: list[dict[str, Any]]
# Required key: "input"
# Optional key: "expected"

trainset = [
    {"input": "What is 2+2?", "expected": "4"},
    {"input": "Summarize this text...", "expected": "A brief summary..."},
]
```

### Return Type

**EvolutionResult** (existing, immutable):
```python
@dataclass(frozen=True)
class EvolutionResult:
    original_score: float      # Baseline score
    final_score: float         # Best achieved score
    evolved_instruction: str   # Optimized instruction
    iteration_history: list[IterationRecord]
    total_iterations: int
    
    @property
    def improvement(self) -> float: ...
    
    @property
    def improved(self) -> bool: ...
```

## API Signatures

### `evolve()` - Async Entry Point

```python
async def evolve(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    valset: list[dict[str, Any]] | None = None,
    critic: LlmAgent | None = None,
    reflection_agent: LlmAgent | None = None,
    config: EvolutionConfig | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    state_guard: StateGuard | None = None,
) -> EvolutionResult:
    """Evolve an ADK agent's instruction.

    Args:
        agent: The ADK LlmAgent to evolve.
        trainset: Training examples [{"input": "...", "expected": "..."}].
        valset: Optional validation examples for held-out evaluation.
        critic: Optional ADK agent for scoring (uses schema scoring if None).
        reflection_agent: Optional ADK agent for proposals (uses LiteLLM if None).
        config: Evolution configuration (uses defaults if None).
        trajectory_config: Trajectory capture settings (uses defaults if None).
        state_guard: Optional state token preservation settings.

    Returns:
        EvolutionResult with evolved_instruction and metrics.

    Raises:
        ConfigurationError: If invalid parameters provided.
        EvolutionError: If evolution fails during execution.
    """
```

### `evolve_sync()` - Synchronous Wrapper

```python
def evolve_sync(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    **kwargs: Any,
) -> EvolutionResult:
    """Synchronous wrapper for evolve().

    Runs the async evolve() function in a blocking manner.
    Handles nested event loops automatically (Jupyter compatible).

    Args:
        agent: The ADK LlmAgent to evolve.
        trainset: Training examples.
        **kwargs: Additional arguments passed to evolve().

    Returns:
        EvolutionResult with evolved_instruction and metrics.
    """
```

## State Transitions

```
┌─────────────────┐
│  User Call      │
│  evolve(agent,  │
│  trainset)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Build Scorer   │
│  (CriticScorer  │
│  or Schema)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Create Adapter │
│  (ADKAdapter)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Create Engine  │
│  (AsyncGEPA     │
│  Engine)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Run Evolution  │
│  Loop           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Apply State    │
│  Guard (if any) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Return         │
│  EvolutionResult│
└─────────────────┘
```

## Validation Rules

| Field | Rule | Error |
|-------|------|-------|
| `agent` | Must be LlmAgent instance | `ConfigurationError` |
| `trainset` | Must be non-empty list | `ConfigurationError` |
| `trainset[*]` | Must have "input" key | `ConfigurationError` |
| `config` | If provided, must be valid EvolutionConfig | Underlying validation |
| `critic` | If provided, should have output_schema | Warning logged |

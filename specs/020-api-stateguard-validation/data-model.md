# Data Model: API StateGuard Validation

**Feature**: 020-api-stateguard-validation  
**Date**: January 13, 2026

## Overview

This feature does not introduce new data models. It wires the existing `StateGuard` utility into the public API functions.

## Existing Entities (No Changes Required)

### StateGuard

**Location**: `src/gepa_adk/utils/state_guard.py`

```python
class StateGuard:
    """Validates and repairs mutated instructions to preserve ADK state tokens."""
    
    # Attributes
    required_tokens: list[str]      # Tokens that must be preserved, e.g., ["{user_id}"]
    repair_missing: bool            # Whether to re-append missing tokens (default: True)
    escape_unauthorized: bool       # Whether to escape new tokens (default: True)
    
    # Methods
    def validate(self, original: str, mutated: str) -> str:
        """Validate and repair mutated instruction."""
```

### EvolutionResult

**Location**: `src/gepa_adk/domain/models.py`

```python
@dataclass(frozen=True)
class EvolutionResult:
    """Result of evolving a single agent's instruction."""
    
    original_score: float
    final_score: float
    evolved_instruction: str      # <-- StateGuard validates this field
    iteration_history: list[IterationRecord]
    total_iterations: int
    valset_score: float | None = None
```

### MultiAgentEvolutionResult

**Location**: `src/gepa_adk/domain/models.py`

```python
@dataclass(frozen=True)
class MultiAgentEvolutionResult:
    """Result of evolving multiple agents together."""
    
    evolved_instructions: dict[str, str]  # <-- StateGuard validates each value
    original_score: float
    final_score: float
    iteration_history: list[IterationRecord]
    total_iterations: int
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        evolve() function                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Capture original_instruction = agent.instruction            │
│                                                                 │
│  2. Run evolution loop → EvolutionResult                        │
│                                                                 │
│  3. If state_guard is not None:                                 │
│     validated = state_guard.validate(                           │
│         original_instruction,                                   │
│         result.evolved_instruction                              │
│     )                                                           │
│                                                                 │
│  4. Return EvolutionResult with validated evolved_instruction   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Validation Rules

StateGuard applies these validation rules to `evolved_instruction`:

| Rule | Condition | Action |
|------|-----------|--------|
| Missing Token Repair | Token in original AND required_tokens BUT NOT in evolved | Append `\n\n{token}` |
| Unauthorized Token Escape | Token in evolved BUT NOT in original AND NOT in required_tokens | Replace `{x}` with `{{x}}` |
| No Change | Token properly preserved or no state_guard provided | Return unchanged |

## State Transitions

N/A - StateGuard is stateless and operates on immutable string inputs.

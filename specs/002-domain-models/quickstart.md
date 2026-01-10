# Quickstart: Domain Models for Evolution Engine

**Feature**: 002-domain-models  
**Date**: 2026-01-10

## Installation

Domain models are included in the `gepa-adk` package:

```bash
uv add gepa-adk
```

## Basic Usage

### Creating an Evolution Configuration

```python
from gepa_adk.domain import EvolutionConfig

# Use all defaults
config = EvolutionConfig()
print(config.max_iterations)  # 50
print(config.max_concurrent_evals)  # 5

# Customize specific parameters
config = EvolutionConfig(
    max_iterations=100,
    patience=10,
    reflection_model="gemini-1.5-pro",
)
```

### Working with Candidates

```python
from gepa_adk.domain import Candidate

# Create a candidate with initial instruction
candidate = Candidate(components={"instruction": "You are a helpful assistant."})

# Access components
instruction = candidate.components["instruction"]

# Modify components (candidates are mutable)
candidate.components["instruction"] = "You are an expert data analyst."
candidate.components["output_schema"] = '{"type": "object", "properties": {...}}'

# List all components
print(list(candidate.components.keys()))  # ['instruction', 'output_schema']

# Candidates track lineage for async evolution
print(candidate.generation)  # 0 (initial generation)
print(candidate.parent_id)   # None (no parent)

# Create a child candidate with lineage
child = Candidate(
    components={"instruction": "You are an expert analyst."},
    generation=1,
    parent_id="parent-uuid-here",
    metadata={"mutation_type": "reflective"},
)
```

### Recording Iteration History

```python
from gepa_adk.domain import IterationRecord

# Created by the engine during evolution (shown here for illustration)
record = IterationRecord(
    iteration_number=1,
    score=0.75,
    instruction="You are a helpful assistant.",
    accepted=True,
)

# Iteration records are immutable
# record.score = 0.8  # TypeError: frozen dataclass
```

### Examining Evolution Results

```python
from gepa_adk.domain import EvolutionResult, IterationRecord

# Created by the engine after evolution completes
result = EvolutionResult(
    original_score=0.60,
    final_score=0.85,
    evolved_instruction="You are an expert analyst who provides detailed insights.",
    iteration_history=[
        IterationRecord(iteration_number=1, score=0.60, instruction="...", accepted=True),
        IterationRecord(iteration_number=2, score=0.72, instruction="...", accepted=True),
        IterationRecord(iteration_number=3, score=0.85, instruction="...", accepted=True),
    ],
    total_iterations=3,
)

# Access metrics
print(f"Improved from {result.original_score} to {result.final_score}")
print(f"Improvement: {result.improvement:.2f}")  # 0.25
print(f"Did improve: {result.improved}")  # True

# Results are immutable
# result.final_score = 0.90  # TypeError: frozen dataclass
```

## Validation

Configuration parameters are validated on creation:

```python
from gepa_adk.domain import EvolutionConfig
from gepa_adk.domain.exceptions import ConfigurationError

try:
    config = EvolutionConfig(max_iterations=-1)
except ConfigurationError as e:
    print(e)  # max_iterations must be non-negative [field='max_iterations', value=-1]
```

## Type Aliases

For type hints in your own code:

```python
from gepa_adk.domain.types import Score, ComponentName, ModelName

def calculate_improvement(original: Score, final: Score) -> Score:
    return final - original

def get_component(candidate: Candidate, name: ComponentName) -> str:
    return candidate.components[name]
```

## Common Patterns

### Creating a Candidate from Existing Agent

```python
def candidate_from_agent(agent_instruction: str) -> Candidate:
    """Create a candidate from an existing agent's instruction."""
    return Candidate(components={"instruction": agent_instruction})


def create_child_candidate(
    parent: Candidate, 
    new_instruction: str,
    parent_id: str,
) -> Candidate:
    """Create a mutated child candidate with lineage tracking."""
    return Candidate(
        components={"instruction": new_instruction},
        generation=parent.generation + 1,
        parent_id=parent_id,
    )
```

### Checking Evolution Success

```python
def was_evolution_successful(result: EvolutionResult, threshold: float = 0.05) -> bool:
    """Check if evolution achieved meaningful improvement."""
    return result.improved and result.improvement >= threshold
```

### Extracting Best Iteration

```python
def best_iteration(result: EvolutionResult) -> IterationRecord:
    """Find the iteration with the highest score."""
    return max(result.iteration_history, key=lambda r: r.score)
```

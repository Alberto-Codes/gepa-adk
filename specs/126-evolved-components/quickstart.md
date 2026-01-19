# Quickstart: Evolved Components Dictionary

**Feature**: 126-evolved-components
**Date**: 2026-01-19

## Overview

This feature replaces `EvolutionResult.evolved_component_text` with `evolved_components: dict[str, str]`, enabling access to all evolved component values (instruction, output_schema, etc.) from a single result object.

## Basic Usage

### Default Instruction Evolution

The default behavior remains instruction-only evolution. Access the evolved instruction via dictionary key:

```python
from gepa_adk import evolve

# Run evolution (defaults to instruction component)
result = await evolve(agent, trainset)

# Access evolved instruction
evolved_instruction = result.evolved_components["instruction"]
print(f"Evolved instruction: {evolved_instruction}")

# Check improvement
if result.improved:
    print(f"Score improved by {result.improvement:.2%}")
```

### Multi-Component Evolution

When evolving multiple components (e.g., instruction and output_schema), all values are accessible:

```python
from gepa_adk import evolve

# Run multi-component evolution
result = await evolve(
    agent,
    trainset,
    component_selector=alternating_selector,  # Round-robin selector
)

# Access all evolved components
for component_name, component_value in result.evolved_components.items():
    print(f"{component_name}: {component_value[:50]}...")

# Access specific components
instruction = result.evolved_components["instruction"]
schema = result.evolved_components.get("output_schema", "Not evolved")
```

### Tracking Evolution History

Each iteration record now includes which component was evolved:

```python
result = await evolve(agent, trainset)

# Analyze evolution history
for record in result.iteration_history:
    status = "✓" if record.accepted else "✗"
    print(f"Iteration {record.iteration_number}: "
          f"evolved {record.evolved_component} "
          f"(score: {record.score:.3f}) {status}")
```

## Migration Guide

### Before (v0.x)

```python
result = await evolve(agent, trainset)
instruction = result.evolved_component_text
```

### After (v1.x)

```python
result = await evolve(agent, trainset)
instruction = result.evolved_components["instruction"]
```

### Full Migration Checklist

1. **Replace field access**:
   ```python
   # Find and replace all occurrences
   .evolved_component_text  →  .evolved_components["instruction"]
   ```

2. **Update IterationRecord construction** (if any):
   ```python
   # Add evolved_component parameter
   record = IterationRecord(
       iteration_number=1,
       score=0.85,
       component_text="test",
       evolved_component="instruction",  # NEW: required
       accepted=True,
   )
   ```

3. **Update assertions in tests**:
   ```python
   # Before
   assert result.evolved_component_text == expected

   # After
   assert result.evolved_components["instruction"] == expected
   ```

## Error Handling

```python
result = await evolve(agent, trainset)

# Safe access for optional components
schema = result.evolved_components.get("output_schema")
if schema:
    print(f"Schema was evolved: {schema}")
else:
    print("Schema was not part of this evolution")

# Explicit check before access
if "output_schema" in result.evolved_components:
    process_schema(result.evolved_components["output_schema"])
```

## Type Hints

```python
from gepa_adk.domain.models import EvolutionResult, IterationRecord

def process_result(result: EvolutionResult) -> str:
    # IDE autocomplete works with dict[str, str] type
    components: dict[str, str] = result.evolved_components
    return components["instruction"]

def analyze_history(result: EvolutionResult) -> list[str]:
    # evolved_component field is typed as str
    return [record.evolved_component for record in result.iteration_history]
```

## Common Patterns

### Apply Evolved Components to Agent

```python
result = await evolve(agent, trainset)

# Update agent with evolved instruction
agent.instruction = result.evolved_components["instruction"]

# If schema was evolved, update it too
if "output_schema" in result.evolved_components:
    agent.output_schema = result.evolved_components["output_schema"]
```

### Export Evolution Results

```python
import json

result = await evolve(agent, trainset)

# Export all evolved components as JSON
output = {
    "evolved_components": result.evolved_components,
    "original_score": result.original_score,
    "final_score": result.final_score,
    "improvement": result.improvement,
}
json.dump(output, open("evolution_result.json", "w"), indent=2)
```

### Compare Before/After

```python
original_instruction = agent.instruction
result = await evolve(agent, trainset)
evolved_instruction = result.evolved_components["instruction"]

print("=== Original ===")
print(original_instruction)
print("\n=== Evolved ===")
print(evolved_instruction)
print(f"\nImprovement: {result.improvement:.2%}")
```

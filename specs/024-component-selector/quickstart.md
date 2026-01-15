# Quickstart: Multi-Component Evolution with Component Selectors

**Feature**: 024-component-selector
**Date**: 2026-01-14

## Overview

Component selectors control which parts of your agent (instruction, output_schema, per-agent prompts) get mutated during each evolution iteration. This enables balanced evolution across all components.

## Installation

No additional dependencies required - component selectors are built into gepa-adk.

## Basic Usage

### 1. Round-Robin Selection (Default)

Round-robin cycles through components one at a time, ensuring balanced coverage:

```python
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from gepa_adk import evolve

class OutputSchema(BaseModel):
    answer: str
    score: float = Field(ge=0.0, le=1.0)

agent = LlmAgent(
    name="assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant.",
    output_schema=OutputSchema,
)

trainset = [
    {"input": "What is 2+2?", "expected": "4"},
    {"input": "What is the capital of France?", "expected": "Paris"},
]

# Default behavior - round-robin selection
result = await evolve(
    agent=agent,
    trainset=trainset,
    # component_selector defaults to "round_robin"
)

print(f"Evolved instruction: {result.evolved_instruction}")
```

### 2. All-Components Selection

When you want to evolve all components simultaneously each iteration:

```python
result = await evolve(
    agent=agent,
    trainset=trainset,
    component_selector="all",  # Mutate all components each iteration
)
```

### 3. Multi-Agent Evolution

For workflows with multiple agents, component selection cycles through all agents' instructions:

```python
from gepa_adk import evolve_group

generator = LlmAgent(
    name="generator",
    model="gemini-2.0-flash",
    instruction="Generate Python code based on the requirement.",
)

critic = LlmAgent(
    name="critic",
    model="gemini-2.0-flash",
    instruction="Review the code in {generator_output} for correctness.",
)

validator = LlmAgent(
    name="validator",
    model="gemini-2.0-flash",
    instruction="Validate the reviewed code and score it.",
    output_schema=ValidationResult,
)

result = await evolve_group(
    agents=[generator, critic, validator],
    primary="validator",
    trainset=training_data,
    component_selector="round_robin",  # Cycles: generator → critic → validator
)

# Access evolved instructions for each agent
print(f"Generator: {result.evolved_instructions['generator']}")
print(f"Critic: {result.evolved_instructions['critic']}")
print(f"Validator: {result.evolved_instructions['validator']}")
```

## Selector Types

| Selector | Behavior | Best For |
|----------|----------|----------|
| `"round_robin"` | One component per iteration, cycles through all | Balanced evolution, long runs |
| `"all"` | All components every iteration | Fast exploration, coupled components |

## Custom Selectors

Implement `ComponentSelectorProtocol` for custom selection strategies:

```python
from gepa_adk.ports.selector import ComponentSelectorProtocol

class InstructionFirstSelector:
    """Always evolve instruction, then cycle through others."""

    def __init__(self) -> None:
        self._other_idx: dict[int, int] = {}

    async def select_components(
        self,
        components: list[str],
        iteration: int,
        candidate_idx: int,
    ) -> list[str]:
        # Always include instruction
        if "instruction" in components and iteration % 2 == 1:
            return ["instruction"]

        # Cycle through other components on even iterations
        others = [c for c in components if c != "instruction"]
        if not others:
            return ["instruction"]

        idx = self._other_idx.get(candidate_idx, 0)
        self._other_idx[candidate_idx] = (idx + 1) % len(others)
        return [others[idx]]

# Use the custom selector
result = await evolve(
    agent=agent,
    trainset=trainset,
    component_selector=InstructionFirstSelector(),
)
```

## Common Patterns

### Pattern 1: Schema Evolution

When your agent has an output_schema that needs refinement:

```python
# Round-robin will alternate between instruction and output_schema
result = await evolve(
    agent=agent_with_schema,
    trainset=trainset,
    component_selector="round_robin",
)
```

### Pattern 2: Fast Multi-Agent Exploration

When you want aggressive evolution of all agents simultaneously:

```python
result = await evolve_group(
    agents=[agent1, agent2, agent3],
    primary="agent3",
    trainset=trainset,
    component_selector="all",  # All agents mutated each iteration
)
```

### Pattern 3: Workflow Evolution

For complex workflows with nested agents:

```python
from google.adk.agents import SequentialAgent
from gepa_adk import evolve_workflow

pipeline = SequentialAgent(
    name="Pipeline",
    sub_agents=[preprocessor, analyzer, formatter],
)

result = await evolve_workflow(
    workflow=pipeline,
    trainset=trainset,
    component_selector="round_robin",
)
```

## Troubleshooting

### Q: My single-component agent behaves the same with any selector

**A**: Expected. With only one component (instruction), both selectors return `["instruction"]` every iteration.

### Q: Round-robin isn't cycling through all my components

**A**: Check that your candidate has multiple components. For multi-agent, ensure you're using `evolve_group()` or `evolve_workflow()` which create per-agent component keys.

### Q: How do I see which components were selected each iteration?

**A**: Enable debug logging:

```python
import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
)
```

Look for `component_selection` log events during evolution.

## Next Steps

- See [research.md](./research.md) for design decisions
- See [data-model.md](./data-model.md) for entity definitions
- See [contracts/api_extensions.md](./contracts/api_extensions.md) for full API reference

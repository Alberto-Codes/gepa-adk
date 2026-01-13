# Quickstart: Wire Adapters to AsyncReflectiveMutationProposer

**Feature**: 016-wire-adapters-proposer  
**Date**: 2026-01-12

## Overview

This feature enables ADKAdapter and MultiAgentAdapter to generate actual instruction mutations via LLM, replacing stub/heuristic implementations with proper delegation to `AsyncReflectiveMutationProposer`.

## Basic Usage

### ADKAdapter with Default Proposer

```python
from google.adk.agents import LlmAgent
from gepa_adk.adapters import ADKAdapter

# Create agent and scorer
agent = LlmAgent(
    name="helper",
    model="gemini-2.0-flash",
    instruction="Be helpful and concise",
)
scorer = MyScorer()

# Adapter automatically creates default proposer
adapter = ADKAdapter(agent=agent, scorer=scorer)

# Evaluate and generate reflective dataset
batch = [{"input": "What is 2+2?", "expected": "4"}]
candidate = {"instruction": "Be very precise with math"}
result = await adapter.evaluate(batch, candidate, capture_traces=True)
dataset = await adapter.make_reflective_dataset(candidate, result, ["instruction"])

# Propose improved instruction via LLM
new_texts = await adapter.propose_new_texts(candidate, dataset, ["instruction"])
print(new_texts["instruction"])  # LLM-generated improved instruction
```

### MultiAgentAdapter with Default Proposer

```python
from google.adk.agents import LlmAgent
from gepa_adk.adapters import MultiAgentAdapter

# Create agents
generator = LlmAgent(name="generator", model="gemini-2.0-flash", output_key="code")
critic = LlmAgent(name="critic", model="gemini-2.0-flash")

# Adapter automatically creates default proposer
adapter = MultiAgentAdapter(
    agents=[generator, critic],
    primary="generator",
    scorer=scorer,
)

# Propose improved instructions for both agents
candidate = {
    "generator_instruction": "Generate Python code",
    "critic_instruction": "Review code thoroughly",
}
new_texts = await adapter.propose_new_texts(
    candidate, 
    dataset, 
    ["generator_instruction", "critic_instruction"]
)
```

## Custom Proposer

### Using Different Model

```python
from gepa_adk.engine import AsyncReflectiveMutationProposer

# Custom proposer with production model
custom_proposer = AsyncReflectiveMutationProposer(
    model="gemini/gemini-2.5-flash",
    temperature=0.5,  # More deterministic
    max_tokens=4096,
)

adapter = ADKAdapter(
    agent=agent,
    scorer=scorer,
    proposer=custom_proposer,  # Inject custom proposer
)
```

### Using Custom Prompt Template

```python
custom_template = """You are optimizing agent instructions.

Current instruction:
{current_instruction}

Performance data:
{feedback_examples}

Suggest an improved instruction that addresses the feedback.
Return ONLY the improved instruction text."""

custom_proposer = AsyncReflectiveMutationProposer(
    model="ollama/llama3.2:3b",
    prompt_template=custom_template,
    temperature=0.8,
)

adapter = MultiAgentAdapter(
    agents=[generator, critic],
    primary="generator",
    scorer=scorer,
    proposer=custom_proposer,
)
```

### Using ADK Reflection Agent

```python
from google.adk.agents import LlmAgent
from gepa_adk.engine import AsyncReflectiveMutationProposer, create_adk_reflection_fn

# Create ADK agent for reflection
reflection_agent = LlmAgent(
    name="InstructionReflector",
    model="gemini-2.0-flash",
    instruction="""Improve this instruction:
    {current_instruction}
    
    Based on feedback:
    {execution_feedback}
    
    Return improved instruction only."""
)

# Create reflection function
reflection_fn = create_adk_reflection_fn(reflection_agent)

# Use with proposer
custom_proposer = AsyncReflectiveMutationProposer(
    adk_reflection_fn=reflection_fn,
)

adapter = ADKAdapter(agent=agent, scorer=scorer, proposer=custom_proposer)
```

## Handling Empty Datasets

```python
# Empty dataset returns unchanged values (graceful fallback)
empty_dataset = {}
result = await adapter.propose_new_texts(
    candidate={"instruction": "Original"},
    reflective_dataset=empty_dataset,
    components_to_update=["instruction"],
)
assert result["instruction"] == "Original"  # Unchanged
```

## Full Evolution Loop Example

```python
async def evolution_step(adapter, batch, candidate, components):
    """Single evolution step with LLM-based mutation."""
    
    # 1. Evaluate current candidate
    result = await adapter.evaluate(batch, candidate, capture_traces=True)
    
    # 2. Build reflective dataset from results
    dataset = await adapter.make_reflective_dataset(candidate, result, components)
    
    # 3. Propose improved instructions via LLM
    new_candidate = await adapter.propose_new_texts(candidate, dataset, components)
    
    return new_candidate, result.scores

# Run evolution
candidate = {"instruction": "Be helpful"}
for iteration in range(10):
    candidate, scores = await evolution_step(adapter, batch, candidate, ["instruction"])
    print(f"Iteration {iteration}: avg_score={sum(scores)/len(scores):.3f}")
```

## Testing with Mock Proposer

```python
from unittest.mock import AsyncMock

# Create mock proposer for unit tests
mock_proposer = AsyncMock()
mock_proposer.propose = AsyncMock(return_value={"instruction": "mocked improvement"})

adapter = ADKAdapter(agent=agent, scorer=scorer, proposer=mock_proposer)

# Verify delegation
result = await adapter.propose_new_texts(
    {"instruction": "original"},
    {"instruction": [{"feedback": "needs work"}]},
    ["instruction"],
)
assert result["instruction"] == "mocked improvement"
mock_proposer.propose.assert_called_once()
```

## Configuration Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `proposer` | `AsyncReflectiveMutationProposer \| None` | `None` | Custom proposer instance |

### Default Proposer Settings

When `proposer=None`, these defaults are used:
| Setting | Value |
|---------|-------|
| `model` | `"ollama/gpt-oss:20b"` |
| `temperature` | `0.7` |
| `max_tokens` | `2048` |
| `prompt_template` | Built-in reflection template |
| `adk_reflection_fn` | `None` (uses LiteLLM) |

# Quickstart: Multi-Agent Co-Evolution

**Feature**: 014-multi-agent-coevolution  
**Date**: January 11, 2026

## Overview

This guide shows how to use `evolve_group()` to optimize multiple ADK agents together.

---

## Installation

```bash
pip install gepa-adk
```

---

## Basic Usage

### 1. Define Your Agent Pipeline

```python
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field


# Define output schema for validation
class CodeValidation(BaseModel):
    """Structured output for code validation."""
    is_valid: bool = Field(description="Whether the code is valid")
    issues: list[str] = Field(default_factory=list, description="List of issues found")
    score: float = Field(ge=0.0, le=1.0, description="Overall quality score")


# Create your agent pipeline
generator = LlmAgent(
    name="generator",
    model="gemini-2.0-flash",
    instruction="Generate Python code based on the user requirement.",
    output_key="generated_code",  # Saves output to session state
)

critic = LlmAgent(
    name="critic",
    model="gemini-2.0-flash",
    instruction="Review the Python code in {generated_code}. Provide feedback.",
    output_key="code_review",
)

validator = LlmAgent(
    name="validator",
    model="gemini-2.0-flash",
    instruction="Validate the code based on review: {code_review}. Return structured assessment.",
    output_schema=CodeValidation,  # Enables schema-based scoring
)
```

### 2. Prepare Training Data

```python
trainset = [
    {
        "input": "Create a function to calculate factorial",
        "expected": "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
    },
    {
        "input": "Write a function to check if a number is prime",
        "expected": "def is_prime(n): ...",
    },
    {
        "input": "Create a class for a binary search tree",
        "expected": "class BST: ...",
    },
]
```

### 3. Run Evolution

```python
import asyncio
from gepa_adk import evolve_group
from gepa_adk.domain.models import EvolutionConfig


async def main():
    # Configure evolution
    config = EvolutionConfig(
        max_iterations=20,
        patience=5,
        min_improvement_threshold=0.01,
    )
    
    # Evolve all agents together
    result = await evolve_group(
        agents=[generator, critic, validator],
        primary="validator",  # Score based on validator's output
        trainset=trainset,
        config=config,
    )
    
    # Print results
    print(f"Original score: {result.original_score:.3f}")
    print(f"Final score: {result.final_score:.3f}")
    print(f"Improvement: {result.improvement:.3f}")
    
    # Access evolved instructions
    for agent_name, instruction in result.evolved_instructions.items():
        print(f"\n--- {agent_name} ---")
        print(instruction[:200] + "..." if len(instruction) > 200 else instruction)


asyncio.run(main())
```

---

## Using a Custom Critic

If your primary agent doesn't have an `output_schema`, provide a critic for scoring:

```python
from gepa_adk.adapters.critic_scorer import CriticOutput


# Create a scoring critic
scoring_critic = LlmAgent(
    name="quality_scorer",
    model="gemini-2.0-flash",
    instruction="""
    Evaluate the quality of the generated code.
    Consider:
    - Correctness
    - Readability
    - Efficiency
    - Best practices
    
    Provide a score from 0.0 to 1.0.
    """,
    output_schema=CriticOutput,
)

# Agents without output_schema
generator = LlmAgent(
    name="generator",
    model="gemini-2.0-flash",
    instruction="Generate Python code.",
)

# Pass critic to evolve_group
result = await evolve_group(
    agents=[generator],
    primary="generator",
    trainset=trainset,
    critic=scoring_critic,  # Provides scoring
)
```

---

## Session State Sharing

By default, agents share session state (`share_session=True`). This enables:

```python
# Agent A saves output to state
agent_a = LlmAgent(
    name="agent_a",
    instruction="Process input",
    output_key="agent_a_output",  # Saved to session.state["agent_a_output"]
)

# Agent B reads from state
agent_b = LlmAgent(
    name="agent_b",
    instruction="Use {agent_a_output} to continue processing",  # Template substitution
)
```

To disable session sharing:

```python
result = await evolve_group(
    agents=[agent_a, agent_b],
    primary="agent_b",
    trainset=trainset,
    share_session=False,  # Each agent gets isolated session
)
```

---

## Applying Evolved Instructions

After evolution, update your agents with the optimized instructions:

```python
# Get evolved instructions
evolved = result.evolved_instructions

# Option 1: Create new agents
new_generator = LlmAgent(
    name="generator",
    model="gemini-2.0-flash",
    instruction=evolved["generator"],
    output_key="generated_code",
)

# Option 2: Update existing agents (mutates original)
generator.instruction = evolved["generator"]
critic.instruction = evolved["critic"]
validator.instruction = evolved["validator"]
```

---

## Configuration Options

```python
from gepa_adk.domain.models import EvolutionConfig

config = EvolutionConfig(
    # Evolution parameters
    max_iterations=50,          # Maximum iterations (default: 50)
    patience=5,                 # Stop after N iterations without improvement
    min_improvement_threshold=0.01,  # Minimum score increase to accept
    
    # Concurrency
    max_concurrent_evals=5,     # Parallel evaluations per iteration
    
    # Model for mutations
    reflection_model="gemini-2.0-flash",
)
```

---

## Error Handling

```python
from gepa_adk.domain.exceptions import (
    MultiAgentValidationError,
    EvolutionError,
)

try:
    result = await evolve_group(
        agents=agents,
        primary="unknown_agent",  # Will raise error
        trainset=trainset,
    )
except MultiAgentValidationError as e:
    print(f"Validation error: {e.message}")
    print(f"Field: {e.field}, Value: {e.value}")
except EvolutionError as e:
    print(f"Evolution failed: {e}")
```

---

## Common Patterns

### Generator-Critic-Validator Pipeline

```python
agents = [
    LlmAgent(name="generator", instruction="Generate...", output_key="output"),
    LlmAgent(name="critic", instruction="Review {output}...", output_key="feedback"),
    LlmAgent(name="validator", instruction="Validate based on {feedback}...", output_schema=...),
]

result = await evolve_group(agents, primary="validator", trainset=data)
```

### Two-Agent Refinement

```python
agents = [
    LlmAgent(name="drafter", instruction="Write initial draft...", output_key="draft"),
    LlmAgent(name="editor", instruction="Improve {draft}...", output_schema=...),
]

result = await evolve_group(agents, primary="editor", trainset=data)
```

### Single Agent with External Critic

```python
agent = LlmAgent(name="assistant", instruction="Help the user...")
critic = LlmAgent(name="scorer", instruction="Rate helpfulness...", output_schema=CriticOutput)

result = await evolve_group(
    agents=[agent],
    primary="assistant",
    critic=critic,
    trainset=data,
)
```

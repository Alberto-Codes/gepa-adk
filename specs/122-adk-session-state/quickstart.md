# Quickstart: ADK Session State for Reflection Agent

**Feature**: 122-adk-session-state
**Date**: 2026-01-18

## Overview

This guide shows how to configure the reflection agent to use ADK session state management for input injection and output storage.

## Basic Usage

### Configure Reflection Agent with output_key

```python
from google.adk.agents import LlmAgent
from gepa_adk.engine.adk_reflection import (
    create_adk_reflection_fn,
    REFLECTION_INSTRUCTION,
)

# Create reflection agent with output_key for automatic state storage
reflection_agent = LlmAgent(
    name="InstructionReflector",
    model="gemini-2.0-flash",
    instruction=REFLECTION_INSTRUCTION,
    output_key="proposed_instruction",  # ADK stores output here
)

# Create reflection function
reflection_fn = create_adk_reflection_fn(
    reflection_agent,
    output_key="proposed_instruction",  # Must match agent's output_key
)
```

### Use with AsyncReflectiveMutationProposer

```python
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

# Create proposer with ADK reflection
proposer = AsyncReflectiveMutationProposer(
    model="gemini/gemini-2.0-flash",  # LiteLLM fallback model
    adk_reflection_fn=reflection_fn,   # Uses ADK session state
)

# Propose mutations
result = await proposer.propose(
    candidate={"instruction": "Be helpful and concise"},
    reflective_dataset={
        "instruction": [
            {
                "input": "Hello",
                "output": "Hi there!",
                "feedback": {"score": 0.7, "feedback_text": "Good but could be warmer"},
            }
        ]
    },
    components_to_update=["instruction"],
)
```

## Custom Instruction with State Templates

```python
# Use {component_text} and {trials} placeholders
custom_instruction = """You are an expert at improving agent instructions.

## Current Instruction
{component_text}

## Performance Data
{trials}

## Your Task
Analyze the trials to understand what works. Propose an improved instruction
that will produce better-scoring outputs.

Return ONLY the improved instruction, nothing else."""

reflection_agent = LlmAgent(
    name="CustomReflector",
    model="gemini-2.0-flash",
    instruction=custom_instruction,
    output_key="proposed_instruction",
)
```

## State Flow Visualization

```
┌─────────────────────────────────────┐
│ 1. Create Session                   │
│    state = {                        │
│      component_text: "Be helpful",  │
│      trials: "[{...}]"              │
│    }                                │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 2. Template Substitution (ADK)      │
│    {component_text} → "Be helpful"  │
│    {trials} → "[{...}]"             │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 3. Agent Execution                  │
│    LLM generates improved text      │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 4. Output Storage (ADK)             │
│    state[output_key] = response     │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 5. Retrieve Output                  │
│    return state["proposed_instr..."]│
└─────────────────────────────────────┘
```

## Multi-Agent Workflow (Future)

```python
from google.adk.agents import LlmAgent, SequentialAgent

# Critic agent writes feedback to state
critic_agent = LlmAgent(
    name="Critic",
    model="gemini-2.0-flash",
    instruction="Evaluate the output and provide feedback.",
    output_key="critic_feedback",  # Stored in state
)

# Reflection agent reads critic feedback from state
reflection_agent = LlmAgent(
    name="Reflector",
    model="gemini-2.0-flash",
    instruction="""Improve the instruction based on critic feedback.

Critic feedback: {critic_feedback}
Current instruction: {component_text}

Return improved instruction only.""",
    output_key="proposed_instruction",
)

# Sequential workflow - state flows automatically
workflow = SequentialAgent(
    name="CriticReflectionWorkflow",
    sub_agents=[critic_agent, reflection_agent],
)
```

## Error Handling

```python
from gepa_adk.domain.exceptions import EvolutionError

try:
    proposed = await reflection_fn(component_text, trials)
except EvolutionError as e:
    # Handle reflection failure
    print(f"Reflection failed: {e}")
    # Fallback: keep original text
    proposed = component_text
```

## Testing

### Unit Test with Mock

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_reflection_with_output_key():
    """Verify output retrieved from session state."""
    # Mock session service
    mock_session_service = MagicMock()
    mock_session = MagicMock()
    mock_session.state = {"proposed_instruction": "Improved instruction"}

    mock_session_service.create_session = AsyncMock(return_value=mock_session)
    mock_session_service.get_session = AsyncMock(return_value=mock_session)

    # Create reflection function with mocked service
    reflection_fn = create_adk_reflection_fn(
        reflection_agent,
        session_service=mock_session_service,
        output_key="proposed_instruction",
    )

    result = await reflection_fn("Be helpful", [{"input": "hi", "output": "hello", "feedback": {"score": 0.5}}])

    assert result == "Improved instruction"
```

## Configuration Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `reflection_agent` | `LlmAgent` | Required | ADK agent for reflection |
| `session_service` | `BaseSessionService` | `InMemorySessionService()` | Session state storage |
| `output_key` | `str` | `"proposed_instruction"` | State key for output storage |

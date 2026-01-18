# Quickstart: ADK Reflection Agents

**Feature**: 034-adk-ollama-reflection
**Date**: 2026-01-17

## Overview

Use ADK LlmAgents as reflection agents for instruction evolution. This provides consistent ADK patterns throughout the evolution pipeline.

## Basic Usage

```python
import asyncio
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from gepa_adk import EvolutionConfig, evolve

# Target agent to evolve
agent = LlmAgent(
    name="greeter",
    model=LiteLlm(model="ollama_chat/llama3.1:latest"),
    instruction="Greet the user appropriately.",
)

# Critic agent for scoring
critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.1:latest"),
    instruction="Evaluate the greeting quality. Score 0.0-1.0.",
    output_schema=CriticOutput,  # Pydantic model with score field
)

# Reflection agent for improvement
reflection_agent = LlmAgent(
    name="reflector",
    model=LiteLlm(model="ollama_chat/llama3.1:latest"),
    instruction="""You are an expert at improving AI agent instructions.
    Analyze the component text and trial data, then propose improvements.
    Return ONLY the improved instruction text.""",
)

# Training data
trainset = [
    {"input": "I am His Majesty, the King."},
    {"input": "I am your mother."},
    {"input": "I am a close friend."},
]

# Run evolution
async def main():
    result = await evolve(
        agent,
        trainset,
        critic=critic,
        reflection_agent=reflection_agent,
        config=EvolutionConfig(max_iterations=3),
    )
    print(f"Improvement: {result.improvement:.2%}")
    print(f"Evolved instruction: {result.evolved_instruction}")

asyncio.run(main())
```

## How It Works

1. **Evaluation**: Agent runs on training examples, critic scores outputs
2. **Trial Building**: Results packaged as trials with `{feedback, trajectory}`
3. **Reflection**: ADK reflection agent receives component_text and trials
4. **Proposal**: Agent returns improved instruction text
5. **Iteration**: Process repeats until convergence or max iterations

## Trial Data Structure

The reflection agent receives trials in this format:

```json
{
  "feedback": {
    "score": 0.75,
    "feedback_text": "Good but could be more formal"
  },
  "trajectory": {
    "input": "I am His Majesty, the King.",
    "output": "Hello, Your Majesty!"
  }
}
```

## Tips

1. **Simple Instructions**: The reflection agent instruction should be focused and clear
2. **Return Only Text**: Instruct the agent to return ONLY the improved text
3. **Any Model**: Works with any LiteLLM-supported model (Ollama, Gemini, OpenAI, etc.)

## Complete Example

See `examples/basic_evolution_adk_reflection.py` for a full working example with Charles Dickens-style greeting evolution.

# Quickstart: ADK Reflection Agents with Ollama

**Feature**: 034-adk-ollama-reflection
**Date**: 2026-01-17

## Overview

This guide shows how to use ADK LlmAgents as reflection agents for instruction evolution with Ollama models.

---

## Basic Usage

### Simple Reflection Agent (Recommended)

For most use cases, don't use `output_schema` - just give clear instructions:

```python
from google.adk import LlmAgent
from gepa_adk import ADKAdapter

# Reflection agent with clear instruction
reflection_agent = LlmAgent(
    name="reflector",
    model="ollama_chat/llama3.1:latest",
    instruction="""Improve the instruction based on the feedback provided.

Return ONLY the improved instruction text, nothing else.""",
)

adapter = ADKAdapter(
    agent=target_agent,
    scorer=scorer,
    reflection_agent=reflection_agent,
)
```

### With Output Schema (Automatic Guidance Injection)

If you want structured output, the system will inject schema guidance for Ollama:

```python
from pydantic import BaseModel, Field

class ReflectionOutput(BaseModel):
    improved_instruction: str = Field(description="The improved instruction")

reflection_agent = LlmAgent(
    name="reflector",
    model="ollama_chat/llama3.1:latest",
    instruction="Improve the instruction based on feedback.",
    output_schema=ReflectionOutput,  # Schema guidance auto-injected for Ollama
)

adapter = ADKAdapter(
    agent=target_agent,
    scorer=scorer,
    reflection_agent=reflection_agent,
)
```

---

## How It Works

1. **ADK event extraction** uses `extract_final_output()` which filters `part.thought=True` reasoning
2. **Schema guidance** is automatically injected into the session state for Ollama models
3. **Text extraction** uses existing pattern matching and paragraph analysis

---

## Troubleshooting

### Problem: Poor Quality Extractions

**First step:** Check the logs to see which extraction method was used:

```python
import structlog
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG))
```

Look for:
```
reflection.extracted_instruction method=longest_paragraph
```

**If `longest_paragraph` is picking wrong content:**
1. Make your reflection instruction more explicit about output format
2. Add "Return ONLY..." guidance to the instruction

### Problem: Empty Extractions

Check if the reflection agent is returning content:

```
reflection.complete response_length=0
```

If response is empty, the model may not be understanding the task.

---

## Model Recommendations

| Model | Notes |
|-------|-------|
| llama3.1 | Works well with clear instructions |
| mistral | Good for concise responses |
| llama2 | May need more explicit formatting guidance |

---

## Complete Example

```python
import asyncio
from google.adk import LlmAgent
from gepa_adk import ADKAdapter, EvolutionConfig, evolve_async

# Target agent
target_agent = LlmAgent(
    name="summarizer",
    model="ollama_chat/llama3.1:latest",
    instruction="Summarize the input text.",
)

# Reflection agent
reflection_agent = LlmAgent(
    name="reflector",
    model="ollama_chat/llama3.1:latest",
    instruction="""Improve the instruction based on the feedback.
Return ONLY the improved instruction text.""",
)

# Scorer
def score_output(input_data, output):
    return 0.8  # Your scoring logic

# Adapter
adapter = ADKAdapter(
    agent=target_agent,
    scorer=score_output,
    reflection_agent=reflection_agent,
)

# Run evolution
async def main():
    result = await evolve_async(
        adapter=adapter,
        dataset=[{"text": "Sample document..."}],
        config=EvolutionConfig(population_size=3, num_iterations=5),
    )
    print(f"Best: {result.best_candidate}")

asyncio.run(main())
```

---

## Next Steps

- See [Multi-Agent Guide](../../../docs/guides/multi-agent.md) for advanced configurations
- See [research.md](./research.md) for technical details

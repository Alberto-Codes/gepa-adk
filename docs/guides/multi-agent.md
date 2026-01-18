# Multi-Agent Evolution

!!! warning "Coming Soon"
    This guide is under development. Multi-agent evolution support is available in the API but documentation is in progress.

In the meantime:

- See the [Getting Started Guide](../getting-started.md) for basic usage with single agents
- Check the [Single-Agent Guide](single-agent.md) for foundational patterns
- Check the [Critic Agents Guide](critic-agents.md) for scoring patterns
- Review the [API Reference](../reference/) for `evolve_group()` documentation

## Reflection Agents with Ollama

When using a reflection agent with Ollama, add explicit output guidance so the
extracted instruction is clean.

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve_group

reflection_agent = LlmAgent(
    name="reflector",
    model="ollama_chat/llama3.1:latest",
    instruction=(
        "Improve the instruction using the feedback.\n"
        "Return ONLY the improved instruction."
    ),
)

result = await evolve_group(
    agents=[generator, reviewer, validator],
    primary="validator",
    trainset=trainset,
    reflection_agent=reflection_agent,
)
```

## Troubleshooting Reflection Output

- If the reflection output still includes reasoning, add a stronger instruction
  like "Return ONLY the improved instruction."

## ADK vs LiteLLM Reflection Paths

GEPA uses the ADK reflection path when a `reflection_agent` is provided. If no
reflection agent is configured, it falls back to LiteLLM-based reflection.

## Logging Guide for Reflection Debugging

Look for these structured logs:

- `proposer.reflection_path` with `method=adk` or `method=litellm`
- `reflection.schema_guidance` to confirm schema guidance injection
- `reflection.extracted_instruction` to see which extraction method was used

## What is Multi-Agent Evolution?

Multi-agent evolution optimizes multiple agents working together in a pipeline, allowing them to co-evolve and improve their coordination.

**Status**: API available, full documentation coming soon.

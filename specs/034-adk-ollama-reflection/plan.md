# Implementation Plan: ADK Reflection Agents

**Branch**: `034-adk-ollama-reflection` | **Date**: 2026-01-17 | **Status**: Implemented

## Summary

Enable ADK LlmAgents as reflection agents for instruction evolution, providing consistent ADK patterns throughout the pipeline. The implementation uses a simple approach: pass data in the user message and use `extract_final_output()` for response extraction.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0, litellm >= 1.80.13, structlog >= 25.5.0
**Testing**: pytest with three-layer strategy (contracts, unit, integration)

## Implementation Approach

### Core Pattern

```python
# Factory creates a ReflectionFn from ADK agent
reflection_fn = create_adk_reflection_fn(reflection_agent)

# ReflectionFn signature
async def reflect(component_text: str, trials: list[dict]) -> str:
    # Send data in user message
    # Extract response with extract_final_output()
    return proposed_text
```

### Key Design Decisions

1. **User Message for Data** - Send `component_text` and `trials` directly in user message, not via session state templating
2. **Leverage Existing Utilities** - Use `extract_final_output()` for ADK event extraction
3. **Consistent Terminology** - Use `component_text`, `trials`, `feedback`, `trajectory` throughout

## Files Changed

### New Files

| File | Purpose |
|------|---------|
| `src/gepa_adk/engine/adk_reflection.py` | `create_adk_reflection_fn()` factory |
| `examples/basic_evolution_adk_reflection.py` | Example with ADK reflection agent |

### Modified Files

| File | Changes |
|------|---------|
| `src/gepa_adk/adapters/adk_adapter.py` | Updated `_build_trial()` with `{feedback, trajectory}` structure |
| `src/gepa_adk/engine/proposer.py` | Wire `adk_reflection_fn` through proposer |
| `docs/guides/reflection-prompts.md` | Updated terminology |

### Test Files

| File | Purpose |
|------|---------|
| `tests/unit/engine/test_proposer.py` | Unit tests for ADK reflection path |
| `tests/integration/engine/test_adk_reflection.py` | Integration tests |
| `tests/contracts/test_reflection_example_metadata.py` | Contract tests for trial structure |

## Trial Data Structure

```python
trial = {
    "feedback": {
        "score": float,
        "feedback_text": str,
        "feedback_guidance": str | None,
        "feedback_dimensions": dict | None,
    },
    "trajectory": {
        "input": str,
        "output": str,
        "trace": {  # optional
            "tool_calls": int,
            "tokens": int,
            "error": str | None,
        } | None,
    },
}
```

## Example Usage

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve, EvolutionConfig

# Create reflection agent
reflection_agent = LlmAgent(
    name="reflector",
    model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
    instruction="""You are an expert at improving AI agent instructions.
    Analyze the component text and trial data, then propose improvements.
    Return ONLY the improved text.""",
)

# Run evolution with ADK reflection
result = await evolve(
    agent,
    trainset,
    critic=critic,
    reflection_agent=reflection_agent,
    config=EvolutionConfig(max_iterations=3),
)
```

## Verification

- [x] All tests pass (816 passed)
- [x] Code quality checks pass
- [x] Example runs successfully with 172% improvement
- [x] Documentation updated

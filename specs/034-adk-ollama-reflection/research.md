# Research: ADK Reflection Agents

**Date**: 2026-01-17
**Branch**: `034-adk-ollama-reflection`
**Objective**: Enable ADK LlmAgents as reflection agents for instruction evolution

## Research Summary

### Problem

Users wanted to use ADK LlmAgents as reflection agents instead of the default LiteLLM-based reflection. This enables consistent ADK patterns throughout the evolution pipeline.

### Solution

Create a factory function `create_adk_reflection_fn()` that wraps an ADK LlmAgent and returns a function matching the `ReflectionFn` protocol.

## Research Task 1: Data Passing Strategy

### Question
How should we pass component_text and trials data to the ADK reflection agent?

### Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| Session State Templating | Use `{component_text}` placeholders in agent instruction | Cleaner instruction | May not work with all models; undocumented behavior |
| User Message | Include data directly in user message | Works reliably; explicit | More verbose messages |
| Hybrid | Try session state, fall back to user message | Flexibility | Complexity |

### Decision

**User Message approach selected.** The implementation sends component_text and trials directly in the user message:

```python
user_message = f"""## Component Text to Improve
{component_text}

## Trials
{json.dumps(trials, indent=2)}

Propose an improved version of the component text based on the trials above.
Return ONLY the improved component text, nothing else."""
```

**Rationale:**
- Works reliably with all models (Ollama, Gemini, OpenAI, etc.)
- No dependency on undocumented ADK session state templating
- Explicit data flow that's easy to debug
- Agent instruction can be simple and focused

### Future Exploration

GitHub Issue #99 tracks exploration of ADK session state templating patterns (`{state.key}` syntax) for potential future enhancement.

---

## Research Task 2: Response Extraction

### Question
How should we extract the proposed instruction from ADK agent responses?

### Decision

**Use `extract_final_output()` utility.** This utility (from `utils/events.py`) already handles:
- ADK event extraction
- Filtering of `part.thought=True` content
- Graceful handling of empty responses

No additional extraction logic needed for ADK reflection agents.

---

## Research Task 3: Trial Data Structure

### Question
What structure should trials have for reflection?

### Decision

Trials follow the `{feedback, trajectory}` structure:

```python
trial = {
    "feedback": {
        "score": 0.75,
        "feedback_text": "Good but could be more formal",
        "feedback_guidance": "Use Dickensian language",  # optional
        "feedback_dimensions": {...},  # optional
    },
    "trajectory": {
        "input": "I am His Majesty, the King.",
        "output": "Hello, Your Majesty!",
        "trace": {  # optional
            "tool_calls": 0,
            "tokens": 150,
            "error": None,
        },
    },
}
```

**Terminology:**
- `component_text`: The text being evolved
- `trial`: A single performance record
- `trials`: Collection of trial records
- `feedback`: Critic evaluation results
- `trajectory`: Execution journey with input/output
- `trace`: Execution metadata (optional)

---

## Implementation Summary

### Files Created/Modified

| File | Change |
|------|--------|
| `src/gepa_adk/engine/adk_reflection.py` | New module with `create_adk_reflection_fn()` |
| `src/gepa_adk/adapters/adk_adapter.py` | Updated `_build_trial()` with new structure |
| `examples/basic_evolution_adk_reflection.py` | New example demonstrating ADK reflection |
| `docs/guides/reflection-prompts.md` | Updated with new terminology |

### Key Design Decisions

1. **User message for data passing** - Reliable across all models
2. **Leverage `extract_final_output()`** - Reuse existing extraction utility
3. **Consistent terminology** - `component_text`, `trials`, `feedback`, `trajectory`
4. **Optional trace** - Only include when available via `_build_trace()` helper

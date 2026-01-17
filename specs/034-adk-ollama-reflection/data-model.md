# Data Model: ADK Ollama Reflection

**Date**: 2026-01-17
**Branch**: `034-adk-ollama-reflection`
**Source**: [spec.md](./spec.md), [research.md](./research.md)

## Overview

This feature focuses on enabling ADK reflection agents with Ollama models. The primary change is **schema-in-prompt injection** when the model doesn't support native structured output. We leverage existing infrastructure where possible.

**Key principle:** Minimal changes. Test first, add complexity only if needed.

---

## Existing Infrastructure (No Changes)

### extract_final_output() (utils/events.py)

Already handles ADK event-level extraction with `part.thought=True` filtering (PR #96).

```python
def extract_final_output(events: list[Any], *, prefer_concatenated: bool = False) -> str:
    """Extract final output text from ADK event stream.

    Filters out reasoning/thought content marked with part.thought=True.
    """
```

**Usage:** The reflection function will use this utility for event extraction.

---

### Existing Extraction Logic (proposer.py lines 283-382)

The current text-level extraction in `create_adk_reflection_fn()` includes:
1. Short response handling (<200 chars)
2. Pattern matching (instruction markers, code blocks, quotes)
3. Longest paragraph with reasoning word filtering
4. Truncation fallback

**Status:** Test with Ollama first. Only enhance if needed.

---

## New/Modified Entities

### 1. SchemaGuidance (New - Internal Helper)

Simple helper to build prompt guidance from output_schema.

| Field | Type | Description |
|-------|------|-------------|
| `field_name` | `str` | Primary field to extract (e.g., "improved_instruction") |
| `json_example` | `str` | Example JSON string |

**Implementation:** Simple function, not a class:

```python
def build_schema_guidance(schema: type[BaseModel]) -> str:
    """Build prompt guidance from Pydantic schema.

    Returns string like:
    'Return your response as JSON: {"improved_instruction": "your text here"}'
    """
```

---

### 2. create_adk_reflection_fn() (Modified Signature)

Add optional parameter for schema injection control.

**Current signature:**
```python
def create_adk_reflection_fn(
    reflection_agent: LlmAgent,
    session_service: BaseSessionService | None = None,
) -> ReflectionFn:
```

**Proposed signature:**
```python
def create_adk_reflection_fn(
    reflection_agent: LlmAgent,
    session_service: BaseSessionService | None = None,
    *,
    inject_schema_guidance: bool = True,  # New
) -> ReflectionFn:
```

**Behavior:**
- If `inject_schema_guidance=True` and `reflection_agent.output_schema` exists:
  - Check if model name suggests Ollama (starts with "ollama")
  - If so, inject schema guidance into session state
- Default `True` for backward-compatible improvement

---

### 3. Session State Changes

When schema guidance is injected, add to session state:

**Before:**
```python
{
    "current_instruction": "Original instruction",
    "execution_feedback": '{"examples": [...]}',
}
```

**After (when injected):**
```python
{
    "current_instruction": "Original instruction",
    "execution_feedback": '{"examples": [...]}',
    "output_format": 'Return as JSON: {"improved_instruction": "..."}',  # New
}
```

The reflection agent's instruction can reference `{output_format}` if desired.

---

## Optional Enhancements (Only If Testing Reveals Need)

### JSON Extraction Attempt

If testing shows Ollama models return JSON-like responses but current extraction doesn't handle them:

```python
def _try_json_extraction(text: str, field_name: str) -> str | None:
    """Try to extract field from JSON response.

    Returns extracted value or None if not valid JSON.
    """
    try:
        data = json.loads(text.strip())
        return data.get(field_name)
    except json.JSONDecodeError:
        return None
```

**Integration point:** Add as first step in extraction logic (before pattern matching).

---

### Enhanced Reasoning Filtering

If testing shows text-level reasoning extraction is a problem:

```python
EXTENDED_REASONING_INDICATORS = [
    # Existing (proposer.py lines 329-338)
    "current", "feedback", "shows", "scores", "however", "therefore", "analysis", "summary",
    # Add only if needed
    "we need to", "let me", "based on",
]
```

**Note:** Only add if testing confirms the existing list is insufficient.

---

## Logging Additions

Add structured logging for observability:

```python
logger.info(
    "reflection.schema_guidance",
    session_id=session_id,
    injected=True,
    model=reflection_agent.model,
    field_name=field_name,
)
```

---

## Backward Compatibility

| Change | Impact |
|--------|--------|
| New `inject_schema_guidance` parameter | Optional with default `True`, fully backward compatible |
| Schema guidance in session state | Additive, no impact on existing flows |
| JSON extraction (if added) | Falls back to existing logic, no breaking change |

---

## Test Strategy

1. **Test first:** Run existing integration tests with Ollama reflection agents
2. **Observe:** Check logs for extraction method and result quality
3. **Iterate:** Only add enhancements where tests reveal actual problems
4. **Avoid:** Over-engineering based on assumptions

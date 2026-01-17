# Contract: ADK Reflection Agent Extraction

**Date**: 2026-01-17
**Feature**: 034-adk-ollama-reflection

## Purpose

Defines the contract for extracting instruction text from ADK reflection agent responses when using Ollama models.

**Note:** ADK event-level `part.thought=True` filtering is already handled by `extract_final_output()` (PR #96). This contract focuses on the text-level extraction in `create_adk_reflection_fn()`.

---

## Existing Contract (Unchanged)

The current extraction in `proposer.py` (lines 283-382) follows this priority:

| Priority | Method | Condition |
|----------|--------|-----------|
| 1 | Return as-is | Response < 200 chars |
| 2 | Pattern: `IMPROVED INSTRUCTION:` | Explicit marker found |
| 3 | Pattern: `improved instruction:` | Case-insensitive marker |
| 4 | Pattern: Code blocks | Triple backticks with content |
| 5 | Pattern: Quoted text | Quoted string >= 30 chars |
| 6 | Longest paragraph | Non-reasoning paragraph > 500 chars total |
| 7 | Truncation | First 500 chars at sentence boundary |

**Status:** Test with Ollama reflection agents. Only modify if testing reveals problems.

---

## New Contract: Schema Guidance Injection

### When to Inject

Schema guidance SHOULD be injected when:
1. `inject_schema_guidance=True` (default)
2. `reflection_agent.output_schema` is defined
3. Model name starts with "ollama" (heuristic for non-compliant models)

### Injection Behavior

```python
def should_inject_schema_guidance(
    reflection_agent: LlmAgent,
    inject_schema_guidance: bool,
) -> bool:
    """Determine if schema guidance should be injected.

    Contract:
    - Return False if inject_schema_guidance is False
    - Return False if reflection_agent has no output_schema
    - Return True if model name starts with "ollama"
    - Return False otherwise (assume model supports native JSON)
    """
```

### Session State Contract

When schema guidance is injected:

```python
session_state["output_format"] = build_schema_guidance(output_schema)
```

The `build_schema_guidance()` function MUST:
1. Identify the primary output field from the schema
2. Generate a simple JSON example
3. Return a concise format instruction

**Example output:**
```
Return as JSON: {"improved_instruction": "your improved instruction here"}
```

---

## Test Cases

### TC-001: Schema Guidance Injection for Ollama

**Setup:**
```python
reflection_agent = LlmAgent(
    model="ollama_chat/llama3.1:latest",
    output_schema=ReflectionOutput,
)
```

**Expected:**
- `should_inject_schema_guidance()` returns `True`
- Session state includes `output_format` key
- Guidance references "improved_instruction" field

---

### TC-002: No Injection for Gemini

**Setup:**
```python
reflection_agent = LlmAgent(
    model="gemini/gemini-2.5-flash",
    output_schema=ReflectionOutput,
)
```

**Expected:**
- `should_inject_schema_guidance()` returns `False`
- Session state does NOT include `output_format` key
- Native JSON mode is trusted

---

### TC-003: No Injection When Disabled

**Setup:**
```python
create_adk_reflection_fn(
    reflection_agent,
    inject_schema_guidance=False,  # Explicitly disabled
)
```

**Expected:**
- `should_inject_schema_guidance()` returns `False`
- Session state unchanged from current behavior

---

### TC-004: No Injection Without Schema

**Setup:**
```python
reflection_agent = LlmAgent(
    model="ollama_chat/llama3.1:latest",
    # No output_schema
)
```

**Expected:**
- `should_inject_schema_guidance()` returns `False`
- No guidance to inject

---

## Optional Enhancement: JSON Extraction

**Only implement if testing reveals Ollama returns JSON but extraction fails.**

If added, JSON extraction SHOULD:
1. Be tried FIRST, before existing pattern matching
2. Use simple `json.loads()` without complex parsing
3. Extract the expected field name from schema
4. Fall back to existing logic if JSON parsing fails

```python
def _try_json_extraction(text: str, field_name: str) -> str | None:
    """Try to extract field from JSON response.

    Contract:
    - Return extracted value if valid JSON with field
    - Return None otherwise (no exceptions)
    - Do NOT try complex JSON extraction (code blocks, brace matching)
    """
```

---

## Logging Contract

Schema injection MUST log:

```python
logger.debug(
    "reflection.schema_guidance",
    session_id=session_id,
    injected=bool,
    model=model_name,
    reason=str,  # "ollama_model", "disabled", "no_schema", "native_supported"
)
```

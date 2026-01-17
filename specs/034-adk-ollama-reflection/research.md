# Research: ADK Ollama Reflection

**Date**: 2026-01-17
**Branch**: `034-adk-ollama-reflection`
**Objective**: Understand how to implement ADK reflection agents with Ollama models, given that `output_schema` may not be enforced.

## Important Context: Issue 82 / PR #96

**Already solved by PR #96:** ADK event-level `part.thought=True` filtering is now handled by `extract_final_output()` in `utils/events.py`. This utility filters reasoning content at the ADK Part object level and is used across all adapters.

**This feature (034) focuses on:** Implementing ADK reflection agents with Ollama. The text-level reasoning filtering in `proposer.py` is a **separate concern** that may or may not be affected. We will test first and only address if needed.

## Research Task 1: ADK Output Schema Handling with LiteLLM

### Question
How does ADK pass output_schema to LiteLLM? Does it use response_format or function calling? What happens when models don't support it?

### Findings

**ADK uses response_format, NOT function calling.**

ADK's `_to_litellm_response_format()` function (in ADK's `lite_llm.py`) converts schemas:

1. **For Gemini models**: `{"type": "json_object", "response_schema": schema_dict}`
2. **For OpenAI/Ollama**: `{"type": "json_schema", "json_schema": {"name": ..., "strict": True, "schema": schema_dict}}`

**Critical finding**: ADK has NO built-in fallback for models that don't support JSON mode. If a model doesn't support `response_format`, ADK passes `response_format=None` and relies entirely on the model's native behavior.

**The current problem**: When `output_schema` is set on an ADK agent used with Ollama:
1. ADK sends the JSON schema format to LiteLLM
2. Ollama models may ignore or partially comply with the constraint
3. The response may contain free-form reasoning mixed with the instruction
4. ADK's output_key never populates because JSON parsing fails
5. Current extraction falls back to `longest_paragraph` which captures reasoning text

### Decision
**Schema-in-prompt injection** is the recommended approach for non-compliant models. ADK/LiteLLM won't enforce JSON natively, so we must guide the model via prompt.

### Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| Rely on ADK native support | ADK has no fallback for non-compliant models |
| Function calling | Not all Ollama models support it; adds complexity |
| Retry with parsing | Wasteful; doesn't address root cause |

---

## Research Task 2: LiteLLM JSON Mode for Ollama

### Question
Does LiteLLM support structured output for Ollama? What configuration options exist?

### Findings

**LiteLLM support is partial with known issues:**

1. **JSON Schema format works**: `response_format: {"type": "json_schema", "json_schema": {...}}`
2. **Simple json_object fails**: Using `response_format={"type": "json_object"}` causes post-processing errors (documented bug in LiteLLM issue #17807, December 2025)
3. **Model-dependent**: Not all Ollama models support JSON mode equally; `llama3.1` works better than `llama2`

**Available fallback mechanisms:**

1. **Prompt injection**: `litellm.add_function_to_prompt = True` injects function definitions into the prompt
2. **Model fallbacks**: LiteLLM can route to backup models
3. **Client-side validation**: `litellm.enable_json_schema_validation = True`

**Workaround for Ollama**: Use `format="json"` parameter directly, or implement prompt-based guidance.

### Decision
**Implement schema-in-prompt injection** at the gepa-adk level rather than relying on LiteLLM's response_format. This provides consistent behavior across all Ollama models.

### Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| Upgrade LiteLLM | Bug may persist; doesn't solve model limitations |
| Use only JSON-capable models | Limits user choice; violates project goals |
| Model-specific handling | Complex; hard to maintain |

---

## Research Task 3: Extraction Patterns for Mixed Content

### Question
What are best practices for extracting structured content from unstructured LLM responses?

### Findings

**Current extraction in proposer.py (lines 283-382):**

1. **Short response (<200 chars)**: Return as-is
2. **Pattern matching**: Try regex patterns in order:
   - `IMPROVED INSTRUCTION:` marker
   - `improved instruction:` (case-insensitive)
   - Code blocks (```text ... ```)
   - Quoted text (substantial length)
3. **Longest paragraph fallback**: For responses >500 chars, find longest paragraph that doesn't start with reasoning words (`current`, `feedback`, `shows`, `however`, etc.)
4. **Last resort**: Return first 500 chars, ending at sentence boundary

**Problems identified:**

1. **Insufficient reasoning filtering**: The current `reasoning_words` list misses common patterns like:
   - "We need to..." (seen in bug report)
   - "Let me think..."
   - "First, let's analyze..."
   - "Based on the feedback..."

2. **No JSON extraction**: Current code doesn't try to parse JSON from responses that might include structured data

3. **Longest paragraph picks wrong content**: When reasoning is the longest paragraph, it gets selected

**Best practice from CriticScorer** (`critic_scorer.py:373-426`):
- Try direct JSON parse first
- Extract from markdown code blocks
- Use brace-matching for embedded JSON
- Only fall back to text extraction if JSON fails

### Decision
**Enhance extraction with:**
1. **Expanded reasoning word list** including phrases like "We need to", "Let me", "Based on"
2. **JSON extraction attempt before paragraph fallback** to capture schema-guided responses
3. **Instruction-indicator detection** to find paragraphs that look like instructions (imperative voice, second person, action verbs)

### Alternatives Considered
| Alternative | Why Rejected |
|-------------|--------------|
| Force strict JSON-only | Would break non-compliant models entirely |
| Regex-only extraction | Too fragile; misses JSON responses |
| No fallback (fail on parse error) | User experience too poor; evolution stops |

---

## Research Task 4: Thought/Reasoning Filtering

### Question
How should we handle LLM "thinking" content in responses?

### Findings

**Already solved by PR #96 (issue 82):**

ADK event-level `part.thought=True` filtering is now handled by `extract_final_output()` in `utils/events.py`:

```python
# Already implemented in utils/events.py (lines 520-528)
def _extract_text_from_parts(parts: Any) -> str:
    for part in parts:
        if getattr(part, "thought", False):  # Skip thinking content
            continue
        text = getattr(part, "text", None)
        if text:
            return text
    return ""
```

**For ADK reflection agents:**
- The `extract_final_output()` utility already handles ADK thought parts
- Text-level reasoning filtering in `proposer.py` is existing logic (lines 329-364)
- We should **test first** before assuming it's broken

### Decision
**Leverage existing infrastructure:**
1. Use `extract_final_output()` for ADK event extraction (already filters `thought=True`)
2. Test with Ollama reflection agents to see if text-level filtering is needed
3. Only enhance text-level filtering if testing shows it's a problem

---

## Implementation Strategy Summary

### Approach: Schema-in-Prompt Injection (Minimal Changes)

**Core Problem:** `output_schema` is ignored by Ollama → `output_key` never populates

**Solution:** Inject schema guidance into the prompt so Ollama returns JSON-like structure

**Phase 1 - Schema Guidance Injection:**
When `create_adk_reflection_fn()` receives a reflection agent with `output_schema`:
1. Detect if model likely doesn't support native JSON (Ollama models)
2. Inject schema as text guidance into session state or prompt
3. Include explicit format instructions

**Proposed schema guidance (simple):**
```text
Return your response as JSON: {"improved_instruction": "your improved instruction here"}
```

**Phase 2 - JSON Extraction (if needed):**
Add JSON extraction attempt before existing text fallbacks:
1. Try `json.loads()` on response
2. Extract expected field (e.g., `improved_instruction`)
3. Fall back to existing text extraction if JSON fails

**Phase 3 - Test and Iterate:**
1. Test with actual Ollama models
2. If text-level reasoning filtering is a problem, enhance `proposer.py`
3. If not, leave existing logic unchanged

**Key Principle:** Don't over-engineer. Test first, fix what's actually broken.

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/gepa_adk/engine/proposer.py` | Schema-in-prompt injection in `create_adk_reflection_fn()`; enhanced extraction patterns |
| `src/gepa_adk/adapters/adk_adapter.py` | Pass output_schema info to reflection function |
| `tests/unit/engine/test_proposer.py` | Unit tests for new extraction patterns |
| `tests/integration/engine/test_proposer_integration.py` | Integration tests with Ollama models |
| `examples/multi_agent.py` | Update example with Ollama reflection agent |
| `docs/guides/multi-agent.md` | Document reflection_agent configuration |

---

## Key Decisions Summary

| Decision | Rationale |
|----------|-----------|
| Schema-in-prompt for Ollama models | ADK/LiteLLM don't have reliable fallback for models without native JSON support |
| Leverage existing `extract_final_output()` | PR #96 already solved ADK-level thought filtering - don't re-implement |
| JSON extraction before text fallback | Captures schema-guided responses when models comply |
| Test before enhancing text filtering | Existing logic in proposer.py may work fine - don't assume it's broken |
| No breaking changes to API | Keep ProposerProtocol interface stable |
| Minimal changes first | Only add complexity if testing reveals actual problems |

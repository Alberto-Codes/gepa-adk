# Research: AsyncReflectiveMutationProposer

**Feature**: 007-async-mutation-proposer  
**Date**: 2026-01-10  
**Status**: Complete  
**LiteLLM Version**: 1.80.13 (verified via `uv add litellm`)

## Research Tasks

### 1. LiteLLM Async API Usage

**Question**: How to properly use `litellm.acompletion()` for async LLM calls?

**Findings** (verified against installed package):
- LiteLLM provides `acompletion()` as the async version of `completion()`
- Import: `from litellm import acompletion`
- Key function signature parameters:
  - `model` (required): Model identifier string
  - `messages` (default `[]`): List of message dicts
  - `temperature` (optional): Sampling temperature
  - `max_tokens` (optional): Maximum response tokens
- Usage pattern:
  ```python
  from litellm import acompletion
  import asyncio

  async def call_llm():
      response = await acompletion(
          model="gemini/gemini-2.5-flash",
          messages=[{"role": "user", "content": "Hello!"}],
          temperature=0.7,
          max_tokens=2048,
      )
      return response.choices[0].message.content
  ```
- Response structure (verified via `litellm.types.utils`):
  - `ModelResponse.choices: List[Choices]`
  - `Choices.message: Message`
  - `Message.content: Optional[str]` ← **Note: content can be None!**
  - `Message.role: Literal['assistant', 'user', 'system', 'tool', 'function']`

**Decision**: Use `litellm.acompletion()` directly in the proposer. Handle `None` content gracefully.

**Rationale**: LiteLLM's unified interface simplifies multi-provider support. The async API integrates naturally with our async-first architecture. Google ADK also uses LiteLLM internally (`google.adk.models.lite_llm`).

**Alternatives Considered**:
1. Direct provider SDKs (google-generativeai, openai) - Rejected: Would require multiple implementations
2. LangChain - Rejected: Heavier dependency, unnecessary abstraction layer
3. Google ADK's LiteLLM wrapper - Rejected: Adds coupling to ADK internals

---

### 2. Gemini Model Naming in LiteLLM

**Question**: What is the correct model identifier for Gemini 2.0 Flash in LiteLLM?

**Findings**:
- LiteLLM uses provider prefixes for model identification
- Gemini models use the `gemini/` prefix
- Correct format: `"gemini/gemini-2.5-flash"`
- Alternative: Can also use `"google/gemini-2.5-flash"` or just `"gemini-2.5-flash"` (LiteLLM will infer)
- Environment variable: `GEMINI_API_KEY` or `GOOGLE_API_KEY`

**Decision**: Default model for local development is `"ollama/gpt-oss:20b"` (zero API cost). For production, use `"gemini/gemini-2.5-flash"` (best price-performance as of Jan 2026).

**Rationale**: Local-first development reduces costs during testing. Explicit provider prefix prevents ambiguity and makes configuration clearer.

---

### 3. Reflective Dataset Structure

**Question**: What is the expected structure of the reflective dataset?

**Findings**:
- From `AsyncGEPAAdapter.make_reflective_dataset()` return type:
  ```python
  Mapping[str, Sequence[Mapping[str, Any]]]
  # Example: {"instruction": [{"input": "...", "output": "...", "feedback": "..."}]}
  ```
- Each component name maps to a list of feedback examples
- Each example is a dict with context about what worked/didn't work
- The exact structure depends on the adapter implementation

**Decision**: Proposer will be flexible about the inner dict structure. It will format examples into the prompt using a configurable template.

**Rationale**: Different adapters may produce different feedback structures. The proposer should handle this variably.

---

### 4. Prompt Template Design

**Question**: What should the default reflection prompt look like?

**Findings**:
- GEPA paper uses reflection to analyze successes/failures and propose improvements
- Key elements for effective prompts:
  1. Current instruction text
  2. Feedback examples (what worked, what didn't)
  3. Clear instruction to improve
  4. Format guidance for output

**Decision**: Default prompt template:
```text
You are an expert at improving AI agent instructions based on performance feedback.

Current Instruction:
{current_instruction}

Performance Feedback:
{feedback_examples}

Based on this feedback, propose an improved instruction that addresses the issues while preserving what works well. Return ONLY the improved instruction text, nothing else.
```

**Rationale**: Simple, focused prompt that gives the LLM clear context and output expectations.

---

### 5. Error Handling Strategy

**Question**: How should the proposer handle LLM errors?

**Findings** (verified against installed package):
- LiteLLM exception types available:
  - `litellm.AuthenticationError` ✅
  - `litellm.RateLimitError` ✅
  - `litellm.APIError` ✅
  - `litellm.Timeout` ✅
  - `litellm.BadRequestError` ✅
  - `litellm.APIConnectionError` ✅
- All inherit from OpenAI-compatible exception base classes
- AsyncGEPAEngine uses fail-fast: exceptions propagate to caller

**Decision**: Follow fail-fast pattern. Let LiteLLM exceptions propagate unchanged. The caller (engine) decides retry logic.

**Rationale**: Consistent with existing engine behavior. Keeps proposer simple and composable.

**Alternatives Considered**:
1. Retry logic in proposer - Rejected: Violates single responsibility, engine should handle retries
2. Return original text on error - Rejected: Hides failures, could lead to stagnant evolution

---

### 6. Empty Response Handling

**Question**: What to do when LLM returns empty or whitespace-only content?

**Findings**:
- Some models occasionally return empty responses
- Could indicate context issues or safety filters
- `Message.content` is `Optional[str]` - can be `None`

**Decision**: Return the original instruction text unchanged when response is empty/whitespace/None.

**Rationale**: Safe fallback that prevents data loss. Stagnation counter in engine handles repeated non-improvements.

---

### 7. Google ADK Integration Discovery

**Question**: How does google-adk relate to LiteLLM?

**Findings** (from exploring `.venv/lib/python3.12/site-packages/google/adk/models/`):
- google-adk has its own LiteLLM wrapper at `google.adk.models.lite_llm`
- LiteLLM is an **optional dependency** of google-adk:
  - `Requires-Dist: litellm>=1.75.5 ; extra == "extensions"`
  - `Requires-Dist: litellm>=1.75.5, <2.0.0 ; extra == "test"`
- google-adk's `lite_llm.py` imports:
  ```python
  from litellm import acompletion
  from litellm import completion
  from litellm import ModelResponse
  # ... many other litellm types
  ```
- google-adk supports multiple model backends: `google_llm.py`, `anthropic_llm.py`, `gemma_llm.py`, `lite_llm.py`

**Decision**: Use LiteLLM directly (not via google-adk wrapper) to avoid tight coupling to ADK internals.

**Rationale**: Direct LiteLLM usage:
1. Provides cleaner dependency graph
2. Avoids breaking if ADK restructures internals
3. Aligns with hexagonal architecture (adapter layer handles ADK)

---

### 8. Ollama Integration for Local Testing

**Question**: How to use Ollama for cost-free local testing?

**Findings**:
- LiteLLM routes requests based on **model prefix** (`gemini/`, `ollama/`, `openai/`, etc.)
- Simply setting `OPENAI_API_BASE` to Ollama endpoint **won't work** - wrong API format
- Must use the `ollama/` prefix on model names:
  ```python
  # Correct - uses Ollama provider
  model="ollama/llama3.1"
  
  # Wrong - would try OpenAI API format
  model="llama3.1"  # with OPENAI_API_BASE=ollama:11434
  ```
- Environment variable: `OLLAMA_API_BASE` auto-detected for `ollama/*` models
- LiteLLM recommends `ollama_chat/` prefix for better chat responses

**Configuration**:
```bash
# .env
OLLAMA_API_BASE=http://192.168.87.58:11434  # Or host.docker.internal:11434
```

```python
# Usage - LiteLLM auto-detects OLLAMA_API_BASE
proposer = AsyncReflectiveMutationProposer(model="ollama/llama3.1")

# Or explicit api_base (not recommended, prefer env var)
await acompletion(
    model="ollama/llama3.1",
    api_base="http://192.168.87.58:11434",
    messages=[...]
)
```

**Decision**: Support Ollama via model parameter. Document as recommended testing approach.

**Rationale**: 
- Zero API cost for development/testing
- Same LiteLLM interface - just change model string
- Already have `OLLAMA_API_BASE` in project `.env`

---

## Summary of Decisions

| Topic | Decision |
|-------|----------|
| Async API | Use `litellm.acompletion()` directly |
| Default Model | `"gemini/gemini-2.5-flash"` |
| Error Handling | Fail-fast (propagate exceptions) |
| Empty Response | Return original text (handle `None`) |
| Prompt Template | Configurable with sensible default |
| Dataset Structure | Flexible inner dict, formatted via template |
| ADK Coupling | Avoid; use LiteLLM directly |
| Local Testing | Use `ollama/*` models with `OLLAMA_API_BASE` |

## Verified Types

```python
# Response access path (verified):
response: ModelResponse = await acompletion(...)
content: str | None = response.choices[0].message.content

# Exception types (all verified present):
litellm.AuthenticationError
litellm.RateLimitError
litellm.APIError
litellm.Timeout
litellm.BadRequestError
litellm.APIConnectionError
```

## Open Questions

None - all clarifications resolved.

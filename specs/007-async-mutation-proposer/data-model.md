# Data Model: AsyncReflectiveMutationProposer

**Feature**: 007-async-mutation-proposer  
**Date**: 2026-01-10  
**Status**: Complete

## Entities

### AsyncReflectiveMutationProposer

**Purpose**: Generates instruction mutations via LLM reflection.

**Attributes**:

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `str` | `"gemini/gemini-2.5-flash"` | LiteLLM model identifier for reflection calls |
| `prompt_template` | `str \| None` | `None` | Custom prompt template (uses default if None) |
| `temperature` | `float` | `0.7` | LLM temperature for creative variation |
| `max_tokens` | `int` | `2048` | Maximum tokens for LLM response |

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `__init__` | `(model: str = ..., prompt_template: str \| None = None, temperature: float = 0.7, max_tokens: int = 2048)` | Initialize proposer with configuration |
| `propose` | `async def propose(candidate: dict[str, str], reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]], components_to_update: list[str]) -> dict[str, str] \| None` | Generate mutation proposals |
| `_build_messages` | `def _build_messages(current_text: str, feedback: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]` | Build LLM message list from inputs |
| `_format_feedback` | `def _format_feedback(feedback: Sequence[Mapping[str, Any]]) -> str` | Format feedback examples as text |

**Invariants**:
- `model` must be a non-empty string
- `temperature` must be in range [0.0, 2.0]
- `max_tokens` must be positive

---

### Type Aliases

```python
# From existing types
ReflectiveDataset = Mapping[str, Sequence[Mapping[str, Any]]]
ProposalResult = dict[str, str] | None
```

---

## Data Flow

```
                              ┌─────────────────────────────────────┐
                              │   AsyncReflectiveMutationProposer   │
                              │                                     │
candidate: dict[str, str] ───►│  1. Check reflective_dataset empty  │
                              │     └─► Return None if empty        │
reflective_dataset ──────────►│                                     │
                              │  2. For each component_to_update:   │
components_to_update ────────►│     a. Get current text             │
                              │     b. Get feedback examples        │
                              │     c. Build LLM messages           │
                              │     d. Call litellm.acompletion()   │
                              │     e. Extract response content     │
                              │                                     │
                              │  3. Return proposals dict           │
                              └─────────────────────────────────────┘
                                              │
                                              ▼
                              ┌─────────────────────────────────────┐
                              │  dict[str, str] | None              │
                              │  e.g., {"instruction": "improved"}  │
                              └─────────────────────────────────────┘
```

---

## Default Prompt Template

```text
You are an expert at improving AI agent instructions based on performance feedback.

## Current Instruction
{current_instruction}

## Performance Feedback
{feedback_examples}

## Task
Based on the feedback above, propose an improved instruction that:
1. Addresses the issues identified in negative feedback
2. Preserves elements that worked well in positive feedback
3. Maintains clarity and specificity

Return ONLY the improved instruction text, with no additional commentary.
```

**Placeholders**:
- `{current_instruction}`: The current instruction text being mutated
- `{feedback_examples}`: Formatted feedback from the reflective dataset

---

## Relationship to Existing Entities

```
┌──────────────────────┐     uses      ┌─────────────────────────────┐
│   AsyncGEPAEngine    │──────────────►│   AsyncGEPAAdapter          │
│                      │               │                             │
│  - adapter           │               │  + make_reflective_dataset()│
│  - config            │               │  + propose_new_texts()      │
│  - _propose_mutation │               └─────────────────────────────┘
└──────────────────────┘                            │
         │                                          │
         │ can delegate to                          │ can use internally
         ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              AsyncReflectiveMutationProposer                        │
│                                                                     │
│  Standalone proposer that adapters can use for the                  │
│  propose_new_texts() implementation, or engine can use directly     │
└─────────────────────────────────────────────────────────────────────┘
```

**Integration Options**:
1. **Adapter uses proposer**: ADKAdapter's `propose_new_texts()` delegates to `AsyncReflectiveMutationProposer`
2. **Engine uses proposer**: Engine calls proposer directly instead of adapter (future refactor)
3. **Standalone usage**: Developer uses proposer independently for experimentation

---

## Validation Rules

| Field | Validation | Error |
|-------|------------|-------|
| `model` | Non-empty string | `ValueError("model must be non-empty")` |
| `temperature` | 0.0 <= value <= 2.0 | `ValueError("temperature must be between 0.0 and 2.0")` |
| `max_tokens` | value > 0 | `ValueError("max_tokens must be positive")` |
| `reflective_dataset` (runtime) | Not None | N/A (type system enforces) |

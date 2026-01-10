# AsyncReflectiveMutationProposer API Contract

**Feature**: 007-async-mutation-proposer  
**Date**: 2026-01-10  
**Version**: 1.0.0

## Overview

This document defines the API contract for `AsyncReflectiveMutationProposer`, specifying its constructor signature, method signatures, return types, and behavioral guarantees.

---

## Class: AsyncReflectiveMutationProposer

### Constructor

```python
def __init__(
    self,
    model: str = "gemini/gemini-2.5-flash",
    prompt_template: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> None:
    """Initialize the mutation proposer.

    Args:
        model: LiteLLM model identifier for reflection calls.
            Examples: "gemini/gemini-2.0-flash", "openai/gpt-4", "anthropic/claude-3-sonnet"
        prompt_template: Custom prompt template with {current_instruction} and
            {feedback_examples} placeholders. Uses default if None.
        temperature: LLM sampling temperature (0.0 = deterministic, 2.0 = creative).
        max_tokens: Maximum tokens in LLM response.

    Raises:
        ValueError: If model is empty, temperature out of range, or max_tokens <= 0.
    """
```

**Validation**:
- `model`: Must be non-empty string
- `temperature`: Must be in range [0.0, 2.0]
- `max_tokens`: Must be > 0

---

### Method: propose

```python
async def propose(
    self,
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components_to_update: list[str],
) -> dict[str, str] | None:
    """Propose mutated instruction text via LLM reflection.

    Args:
        candidate: Current candidate component texts.
            Example: {"instruction": "Be helpful and concise"}
        reflective_dataset: Feedback examples per component.
            Example: {"instruction": [{"input": "...", "feedback": "..."}]}
        components_to_update: Component names to generate proposals for.
            Example: ["instruction"]

    Returns:
        Dictionary mapping component names to proposed new text,
        or None if the reflective dataset is empty or has no entries
        for the requested components.

        Example: {"instruction": "Be helpful, concise, and specific"}

    Raises:
        litellm.AuthenticationError: If API key is invalid.
        litellm.RateLimitError: If rate limit exceeded.
        litellm.APIError: If API call fails.
        Exception: Any other LiteLLM exception propagates unchanged.

    Notes:
        - Components not in candidate are skipped silently.
        - Empty LLM responses return original text for that component.
        - No LLM calls made when returning None (cost optimization).
    """
```

---

## Behavioral Guarantees

### Empty Dataset Handling

| Condition | Behavior | LLM Calls |
|-----------|----------|-----------|
| `reflective_dataset == {}` | Returns `None` | 0 |
| `reflective_dataset["instruction"] == []` | Returns `None` | 0 |
| Component not in reflective_dataset | Skips that component | 0 for that component |

### Error Propagation

| Exception Type | Source | Behavior |
|----------------|--------|----------|
| `litellm.AuthenticationError` | Invalid API key | Propagates unchanged |
| `litellm.RateLimitError` | Rate limit hit | Propagates unchanged |
| `litellm.APIError` | API failure | Propagates unchanged |
| `litellm.Timeout` | Request timeout | Propagates unchanged |

### Response Handling

| LLM Response | Behavior |
|--------------|----------|
| Valid content | Returns extracted text |
| Empty string `""` | Returns original candidate text |
| Whitespace only | Returns original candidate text |
| `None` content | Returns original candidate text |

---

## Type Definitions

```python
from typing import Any, Mapping, Sequence

# Input types
CandidateComponents = dict[str, str]
ReflectiveDataset = Mapping[str, Sequence[Mapping[str, Any]]]
ComponentsToUpdate = list[str]

# Output type
ProposalResult = dict[str, str] | None
```

---

## Usage Examples

### Basic Usage

```python
from gepa_adk.engine import AsyncReflectiveMutationProposer

proposer = AsyncReflectiveMutationProposer()

candidate = {"instruction": "Be helpful"}
reflective_dataset = {
    "instruction": [
        {"input": "What is 2+2?", "output": "4", "feedback": "Good, but needs explanation"},
        {"input": "Explain gravity", "output": "...", "feedback": "Too verbose"},
    ]
}

result = await proposer.propose(
    candidate=candidate,
    reflective_dataset=reflective_dataset,
    components_to_update=["instruction"],
)
# result: {"instruction": "Be helpful and explain your reasoning concisely"}
```

### Empty Dataset (No LLM Call)

```python
result = await proposer.propose(
    candidate={"instruction": "Be helpful"},
    reflective_dataset={},  # Empty
    components_to_update=["instruction"],
)
# result: None (no LLM call made)
```

### Custom Model and Template

```python
proposer = AsyncReflectiveMutationProposer(
    model="openai/gpt-4",
    prompt_template="Improve this: {current_instruction}\n\nFeedback: {feedback_examples}",
    temperature=0.5,
)
```

---

## Protocol (Optional)

For testing and dependency injection, the proposer conforms to this protocol:

```python
from typing import Any, Mapping, Protocol, Sequence

class MutationProposer(Protocol):
    """Protocol for mutation proposers."""

    async def propose(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str] | None:
        """Propose mutated component texts."""
        ...
```

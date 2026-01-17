# Data Model: Reflection Prompt Configuration

**Feature**: 032-reflection-prompt-config
**Date**: 2026-01-17

## EvolutionConfig Extension

### New Field

```python
@dataclass(slots=True, kw_only=True)
class EvolutionConfig:
    # ... existing fields ...

    reflection_prompt: str | None = None
    """Custom reflection/mutation prompt template.

    If provided, this template is used instead of the default when the
    reflection model proposes improved instructions.

    Required placeholders:
    - {current_instruction}: The current agent instruction being evolved
    - {feedback_examples}: Formatted evaluation feedback from test cases

    If None or empty string, the default prompt template is used.

    Example:
        config = EvolutionConfig(
            reflection_prompt='''Analyze this instruction:
            {current_instruction}

            Based on these results:
            {feedback_examples}

            Suggest one specific improvement.'''
        )
    """
```

### Validation Rules

| Rule | Behavior | Rationale |
|------|----------|-----------|
| None value | Use default template | Backward compatible |
| Empty string | Use default template + info log | Graceful fallback |
| Missing `{current_instruction}` | Warning log | Allow experimentation |
| Missing `{feedback_examples}` | Warning log | Allow experimentation |
| Valid template | Pass through | Normal operation |

### Field Dependencies

```text
reflection_prompt (optional)
    └── Used only when:
        - No custom proposer is provided
        - No reflection_agent is provided
        - LiteLLM path is taken (not ADK reflection)
```

## Placeholder Definitions

### `{current_instruction}`

**Type**: str
**Content**: The full text of the agent's current instruction being evolved
**Source**: `candidate.agent.instruction` (GenericAgent) or workflow instruction

**Example Value**:
```text
You are a helpful assistant that answers questions about Python programming.
Be concise and provide code examples when relevant.
```

### `{feedback_examples}`

**Type**: str
**Content**: Formatted string containing evaluation results from the batch
**Source**: `_format_feedback()` method in proposer.py

**Example Value**:
```text
Example 1:
  Input: "How do I read a file?"
  Expected: "Use open() with 'r' mode"
  Actual: "Files can be read using Python"
  Score: 0.3
  Feedback: Response too vague, missing code example

Example 2:
  Input: "What is a list?"
  Expected: "A mutable sequence type"
  Actual: "A list is a mutable sequence type in Python"
  Score: 0.9
  Feedback: Good explanation
```

## Data Flow

```text
User Config Input                    Runtime Values
─────────────────                    ──────────────

EvolutionConfig(                     candidate.agent.instruction
  reflection_prompt="..."                    │
)                                            ▼
        │                            ┌──────────────────┐
        ▼                            │ current_text     │
┌─────────────────┐                  └────────┬─────────┘
│ validation      │                           │
│ (warn on        │                           │
│  missing        │                  evaluation_results
│  placeholders)  │                           │
└────────┬────────┘                           ▼
         │                           ┌──────────────────┐
         ▼                           │ _format_feedback │
┌─────────────────┐                  └────────┬─────────┘
│ api.evolve()    │                           │
└────────┬────────┘                           │
         │                                    │
         ▼                                    ▼
┌─────────────────┐                  ┌──────────────────┐
│ ADKAdapter      │                  │ feedback_text    │
│ .__init__()     │                  └────────┬─────────┘
└────────┬────────┘                           │
         │                                    │
         ▼                                    │
┌─────────────────┐                           │
│ Proposer        │◄──────────────────────────┘
│ .__init__()     │
│ (prompt_template)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ _build_messages │
│                 │
│ prompt_template │
│   .format(      │
│     current_... │
│     feedback_.. │
│   )             │
└─────────────────┘
```

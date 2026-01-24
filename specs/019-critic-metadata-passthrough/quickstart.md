# Quickstart: CriticScorer Metadata Passthrough

**Feature**: 019-critic-metadata-passthrough
**Status**: Implementation Guide

## Overview

This feature enables CriticScorer metadata (feedback, actionable_guidance, dimension_scores) to flow through to the reflection agent, providing richer context for instruction improvement.

## Before This Feature

The reflection agent only received numeric scores:

```python
# Reflection example feedback (before)
{
    "Inputs": {"instruction": "Be helpful"},
    "Generated Outputs": "Here is the answer...",
    "Feedback": "score: 0.650, tool_calls: 2, tokens: 150"
}
```

## After This Feature

The reflection agent receives rich critic feedback:

```python
# Reflection example feedback (after)
{
    "Inputs": {"instruction": "Be helpful"},
    "Generated Outputs": "Here is the answer...",
    "Feedback": """score: 0.650, tool_calls: 2, tokens: 150
Feedback: Good response but could be more concise
Guidance: Reduce response length by 30%
Dimensions: accuracy=0.9, clarity=0.6"""
}
```

## Usage

### No Code Changes Required for Users

If you're using `ADKAdapter` with `CriticScorer`, the metadata passthrough is automatic:

```python
from google.adk.agents import LlmAgent
from gepa_adk.adapters import ADKAdapter
from gepa_adk.adapters.critic_scorer import CriticScorer, CriticOutput

# Create your agent
agent = LlmAgent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="Be helpful and concise",
)

# Create a critic scorer (metadata is captured automatically)
critic = LlmAgent(
    name="critic",
    model="gemini-2.5-flash",
    instruction="Evaluate the response quality...",
    output_schema=CriticOutput,
)
scorer = CriticScorer(critic_agent=critic)

# Create adapter - metadata flows through automatically
adapter = ADKAdapter(agent=agent, scorer=scorer)

# Evaluate with trace capture (for reflection)
result = await adapter.evaluate(batch, candidate, capture_traces=True)

# result.metadata now contains critic feedback for each example
# This metadata is used in make_reflective_dataset()
```

### Accessing Metadata Directly

If you need to access the metadata programmatically:

```python
result = await adapter.evaluate(batch, candidate, capture_traces=True)

if result.metadata:
    for i, meta in enumerate(result.metadata):
        feedback = meta.get("feedback", "")
        guidance = meta.get("actionable_guidance", "")
        dimensions = meta.get("dimension_scores", {})

        print(f"Example {i}:")
        print(f"  Score: {result.scores[i]:.3f}")
        print(f"  Feedback: {feedback}")
        print(f"  Guidance: {guidance}")
        print(f"  Dimensions: {dimensions}")
```

### Custom Scorers

Custom scorers automatically benefit if they return metadata in the tuple:

```python
class MyCustomScorer:
    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        # Your scoring logic
        score = 0.75

        # Return metadata alongside score (will flow to reflection)
        return score, {
            "feedback": "Custom feedback for reflection",
            "my_custom_field": "Any additional data",
        }
```

## Backward Compatibility

- Scorers that return only `float` continue to work
- Scorers that return `tuple[float, dict]` with empty dict work
- `EvaluationBatch` without `metadata` field works (defaults to `None`)
- Existing tests don't require modification

## Verification

Check that metadata is flowing through:

```python
import asyncio

async def verify_metadata_passthrough():
    # ... setup adapter with CriticScorer ...

    result = await adapter.evaluate(batch, candidate, capture_traces=True)

    # Verify metadata is captured
    assert result.metadata is not None, "Metadata not captured!"
    assert len(result.metadata) == len(result.scores), "Metadata count mismatch!"

    # Verify critic fields are present
    for meta in result.metadata:
        if meta:  # May be empty for non-critic scorers
            print(f"Feedback: {meta.get('feedback', 'N/A')}")
            print(f"Guidance: {meta.get('actionable_guidance', 'N/A')}")
            print(f"Dimensions: {meta.get('dimension_scores', {})}")

asyncio.run(verify_metadata_passthrough())
```

## Related Documentation

- [CriticScorer Spec](../009-critic-scorer/spec.md)
- [ADK Reflection Agent Spec](../010-adk-reflection-agent/spec.md)
- [GitHub Issue #45](https://github.com/Alberto-Codes/gepa-adk/issues/45)

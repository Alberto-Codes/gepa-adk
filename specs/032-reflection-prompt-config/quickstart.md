# Quickstart: Reflection Prompt Configuration

**Feature**: 032-reflection-prompt-config
**Date**: 2026-01-17

## Basic Usage

### Using a Custom Reflection Prompt

```python
from gepa_adk import evolve, EvolutionConfig

config = EvolutionConfig(
    reflection_prompt="""You are improving an AI agent's instructions.

## Current Instruction
{current_instruction}

## Evaluation Results
{feedback_examples}

## Your Task
Based on the feedback, propose ONE specific improvement to the instruction.
Focus on the most impactful change.

Return ONLY the improved instruction text."""
)

result = await evolve(
    agent=my_agent,
    scorer=my_scorer,
    test_inputs=test_cases,
    config=config,
)
```

### Extending the Default Prompt

```python
from gepa_adk import evolve, EvolutionConfig
from gepa_adk.engine.proposer import DEFAULT_PROMPT_TEMPLATE

# Add domain-specific context to the default
custom_prompt = DEFAULT_PROMPT_TEMPLATE + """

Additional Guidelines:
- Focus on clarity and conciseness
- Preserve any safety constraints in the original
- Consider edge cases mentioned in feedback
"""

config = EvolutionConfig(reflection_prompt=custom_prompt)
```

### Using Default (No Configuration)

```python
from gepa_adk import evolve

# reflection_prompt defaults to None → uses DEFAULT_PROMPT_TEMPLATE
result = await evolve(
    agent=my_agent,
    scorer=my_scorer,
    test_inputs=test_cases,
)
```

## Example Prompts

### JSON Output Format

```python
json_prompt = """Analyze the agent instruction and feedback, then respond with JSON.

## Current Instruction
{current_instruction}

## Feedback
{feedback_examples}

Respond with exactly this JSON structure:
{
  "analysis": "Brief analysis of what's working and what isn't",
  "improved_instruction": "The complete improved instruction text"
}
"""
```

### Minimal/Fast Prompt

```python
minimal_prompt = """Instruction:
{current_instruction}

Feedback:
{feedback_examples}

Improved instruction:"""
```

### Chain-of-Thought Prompt

```python
cot_prompt = """You are an expert at improving AI instructions.

## Current Instruction
{current_instruction}

## Performance Feedback
{feedback_examples}

## Analysis Process
1. What patterns appear in successful examples?
2. What patterns appear in failed examples?
3. What specific changes would address the failures while preserving successes?

Think through each step, then provide the improved instruction.

## Improved Instruction
"""
```

## Validation Warnings

The system warns if your prompt is missing required placeholders:

```python
# This will log a warning about missing {feedback_examples}
config = EvolutionConfig(
    reflection_prompt="Improve this: {current_instruction}"
)
# WARNING: reflection_prompt missing {feedback_examples} placeholder
```

## Placeholder Reference

| Placeholder | Content | Example |
|-------------|---------|---------|
| `{current_instruction}` | Agent's current instruction text | "You are a helpful assistant..." |
| `{feedback_examples}` | Formatted evaluation results | "Example 1: Input: ... Score: 0.8..." |

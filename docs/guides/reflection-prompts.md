# Customizing Reflection Prompts

This guide covers how to customize the reflection prompt used during evolution to improve instruction mutations.

## Overview

The reflection prompt is the template sent to the reflection model (e.g., `ollama_chat/gpt-oss:20b`) to generate improved agent instructions. By customizing this prompt, you can:

- Tailor the mutation strategy to your specific use case
- Request specific output formats (e.g., JSON)
- Add domain-specific guidelines
- Optimize for different model capabilities

## Available Placeholders

The reflection prompt template supports two placeholders that are filled at runtime:

| Placeholder | Content | Description |
|-------------|---------|-------------|
| `{component_text}` | Component being evolved | The text content of the component (e.g., instruction) |
| `{trials}` | Trial data | Collection of trials with feedback and trajectory for each test |

### Example Placeholder Values

**`{component_text}`:**
```text
You are a helpful assistant that answers questions about Python programming.
Be concise and provide code examples when relevant.
```

**`{trials}`:**
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

## ADK Template Syntax

When using ADK reflection agents, placeholders use ADK's native template substitution syntax. This section covers the syntax details and advanced features.

### Template Syntax Format

ADK uses `{key}` syntax (not `{state.key}`) for template placeholders. The framework automatically looks up values in `session.state[key]` and substitutes them during agent execution.

| Syntax | Behavior | Use Case |
|--------|----------|----------|
| `{key}` | Substitute value, raise `KeyError` if missing | Required data |
| `{key?}` | Substitute value, return empty string if missing | Optional data |
| `{app:key}` | App-scoped state lookup | Shared configuration |
| `{user:key}` | User-scoped state lookup | User preferences |
| `{temp:key}` | Temporary session state | Scratch data |

### Using Optional Placeholders

The `{key?}` syntax (with trailing `?`) allows graceful handling of missing keys:

```python
from google.adk.agents import LlmAgent

agent = LlmAgent(
    name="FlexibleReflector",
    model="gemini-2.0-flash",
    instruction="""Improve this instruction:
{component_text}

Trials:
{trials}

Additional context (if available):
{context?}

Return the improved instruction.""",
)
```

If `context` is not in session state, it will be replaced with an empty string instead of raising an error.

### Session State Setup with ADK Agents

When using `create_adk_reflection_fn()`, session state is populated automatically:

```python
from google.adk.agents import LlmAgent
from gepa_adk.engine.adk_reflection import (
    create_adk_reflection_fn,
    REFLECTION_INSTRUCTION,
)

# Use the default instruction template
agent = LlmAgent(
    name="Reflector",
    model="gemini-2.0-flash",
    instruction=REFLECTION_INSTRUCTION,
)

# Factory handles session state setup
reflection_fn = create_adk_reflection_fn(agent)

# Call with data - it gets injected via template substitution
improved = await reflection_fn(
    component_text="Be helpful",
    trials=[{"score": 0.5, "feedback": "Too vague"}],
)
```

The factory automatically:
1. Creates a session with `component_text` and `trials` in state
2. Serializes `trials` to JSON for the template
3. Runs the agent with a simple trigger message
4. Lets ADK's `inject_session_state()` handle placeholder substitution

### Type Handling

ADK converts all session state values to strings using `str()`. For complex types like dictionaries or lists, pre-serialize them to JSON:

```python
import json

# Good: Pre-serialize complex types
session_state = {
    "component_text": "Be helpful",
    "trials": json.dumps(trials, indent=2),  # JSON string
}

# Bad: ADK will use repr() which may not be readable
session_state = {
    "trials": trials,  # dict → "{'feedback': 'Too vague', ...}"
}
```

The `create_adk_reflection_fn()` factory handles this serialization automatically.

### Error Handling

| Scenario | `{key}` Behavior | `{key?}` Behavior |
|----------|------------------|-------------------|
| Key exists | Substitute value | Substitute value |
| Key missing | Raise `KeyError` | Return empty string |
| Invalid key name | Leave placeholder unchanged | Leave placeholder unchanged |
| Value is `None` | Replace with empty string | Replace with empty string |

Invalid key names (e.g., `{my-invalid-key}` with hyphens) are silently left unchanged since they don't match valid Python identifiers.

### Migration from f-string Workaround

Prior to ADK template substitution support, data was passed via manual f-string construction in user messages. The new approach uses ADK's native template system.

**Before (f-string workaround):**

```python
# Data embedded in user message
user_message = f"""## Component Text
{component_text}

## Trials
{json.dumps(trials, indent=2)}

Improve the component text."""

# Agent instruction was static
agent = LlmAgent(
    name="Reflector",
    model="gemini-2.0-flash",
    instruction="You are a reflection agent.",
)
```

**After (ADK templates):**

```python
# Data in session state, templates in instruction
agent = LlmAgent(
    name="Reflector",
    model="gemini-2.0-flash",
    instruction="""## Component Text
{component_text}

## Trials
{trials}

Improve the component text.""",
)

# Simple trigger message - data injected via template substitution
trigger_message = "Please improve the component text."
```

**Benefits of template approach:**
- Uses ADK's documented patterns
- Cleaner separation of data and task
- Session state can be inspected and tested independently
- Consistent with other ADK agents

## Basic Usage

### Using a Custom Prompt

```python
from gepa_adk import evolve, EvolutionConfig

config = EvolutionConfig(
    reflection_prompt="""You are improving an AI agent's instructions.

## Current Instruction
{component_text}

## Evaluation Results
{trials}

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

You can import and extend the default prompt template:

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

### Using the Default (No Configuration)

```python
from gepa_adk import evolve

# reflection_prompt defaults to None → uses DEFAULT_PROMPT_TEMPLATE
result = await evolve(
    agent=my_agent,
    scorer=my_scorer,
    test_inputs=test_cases,
)
```

## Prompt Design Guidelines

### 1. Include Both Placeholders

Always include `{component_text}` and `{trials}` in your prompt. The system will warn (but not error) if either is missing:

```python
# This will log a warning about missing {trials}
config = EvolutionConfig(
    reflection_prompt="Improve this: {component_text}"
)
```

### 2. Request Clear Output Format

Specify exactly what format you want the response in:

```python
# Good: Clear output expectation
prompt = """...
Return ONLY the improved instruction text, with no additional commentary.
"""

# Also good: Structured output
prompt = """...
Respond with exactly this JSON structure:
{
  "analysis": "Brief analysis",
  "improved_instruction": "The improved text"
}
"""
```

### 3. Be Specific About the Task

Tell the model exactly what kind of improvements to make:

```python
prompt = """...
## Your Task
1. Address the issues identified in negative feedback
2. Preserve elements that worked well in positive feedback
3. Maintain clarity and specificity
4. Keep the instruction concise (under 200 words)
"""
```

### 4. Consider Model Capabilities

Adjust prompt complexity based on your reflection model:

- **Smaller models** (7B-13B): Use simpler, more direct prompts
- **Larger models** (70B+): Can handle chain-of-thought, structured reasoning

## Example Prompts

### Minimal/Fast Prompt

For quick iterations with capable models:

```python
minimal_prompt = """Instruction:
{component_text}

Feedback:
{trials}

Improved instruction:"""
```

### Chain-of-Thought Prompt

For more thoughtful improvements:

```python
cot_prompt = """You are an expert at improving AI instructions.

## Current Instruction
{component_text}

## Performance Feedback
{trials}

## Analysis Process
1. What patterns appear in successful examples?
2. What patterns appear in failed examples?
3. What specific changes would address the failures while preserving successes?

Think through each step, then provide the improved instruction.

## Improved Instruction
"""
```

### JSON Output Format

For structured responses:

```python
json_prompt = """Analyze the agent instruction and feedback, then respond with JSON.

## Current Instruction
{component_text}

## Feedback
{trials}

Respond with exactly this JSON structure:
{
  "analysis": "Brief analysis of what's working and what isn't",
  "improved_instruction": "The complete improved instruction text"
}
"""
```

### Domain-Specific Prompt

For specialized use cases:

```python
code_review_prompt = """You are improving a code review agent's instructions.

## Current Instruction
{component_text}

## Evaluation Feedback
{trials}

## Domain Guidelines
- The agent should identify bugs, security issues, and style problems
- Feedback should be actionable and specific
- Code examples should be provided when suggesting fixes
- Tone should be constructive, not critical

Provide an improved instruction that addresses the feedback while
following these domain guidelines.

## Improved Instruction
"""
```

## Model Selection Guidance

The reflection model processes your custom prompt to generate improved instructions. Choosing the right model affects quality, speed, and cost.

### Token Budget Considerations

Your reflection prompt plus placeholders consume context tokens:

| Component | Typical Size |
|-----------|-------------|
| Custom prompt template | 100-500 tokens |
| `{component_text}` | 50-500 tokens |
| `{trials}` | 200-2000 tokens (depends on trial count) |
| Response | 50-500 tokens |

**Recommendation**: Keep your prompt template under 500 tokens. For larger instruction sets, consider reducing batch size or using a model with larger context.

### Model Capability vs Task Complexity

| Task Complexity | Recommended Model Tier | Examples |
|----------------|----------------------|----------|
| Simple rewording | Local (7B-13B) | Ollama gpt-oss:7b |
| Structured improvements | Local (20B+) | Ollama gpt-oss:20b (default) |
| Complex reasoning | Cloud (cheap) | GPT-4o-mini, Claude Haiku |
| Domain expertise | Cloud (premium) | GPT-4o, Claude Sonnet |

### Cost vs Quality Tradeoffs

| Model Tier | Cost | Quality | Speed | When to Use |
|-----------|------|---------|-------|-------------|
| **Local (Ollama)** | Free | Good | Medium | Development, iteration, cost-sensitive production |
| **Cloud Cheap** | ~$0.15/1M tokens | Better | Fast | Production with budget constraints |
| **Cloud Premium** | ~$5-15/1M tokens | Best | Fast | High-stakes applications, complex domains |

### Configuring the Reflection Model

```python
from gepa_adk import evolve, EvolutionConfig

# Local model (default)
config = EvolutionConfig(
    reflection_model="ollama_chat/gpt-oss:20b",
)

# Cloud model (OpenAI)
config = EvolutionConfig(
    reflection_model="gpt-4o-mini",
)

# Cloud model (Anthropic)
config = EvolutionConfig(
    reflection_model="claude-3-haiku-20240307",
)
```

## Validation and Debugging

### Check for Missing Placeholders

The system logs warnings if placeholders are missing:

```
WARNING: reflection_prompt is missing {trials} placeholder
```

### Test Your Prompt

Before running evolution, test your prompt manually:

```python
from gepa_adk.engine.proposer import DEFAULT_PROMPT_TEMPLATE

# See what the default looks like
print(DEFAULT_PROMPT_TEMPLATE)

# Test your custom prompt with sample values
my_prompt = "..."
formatted = my_prompt.format(
    component_text="Be helpful",
    trials="Example 1: Score 0.5..."
)
print(formatted)
```

## Related Resources

- [Custom Reflection Prompt Example](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/custom_reflection_prompt.py) - Complete working example
- [Single-Agent Evolution](single-agent.md) - Basic evolution patterns
- [Multi-Agent Evolution](multi-agent.md) - Multi-agent pipelines
- [Critic Agents](critic-agents.md) - Using critic agents for scoring

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

# Quickstart: AsyncReflectiveMutationProposer

**Feature**: 007-async-mutation-proposer  
**Date**: 2026-01-10

## Installation

The proposer requires LiteLLM as a dependency:

```bash
uv add litellm
```

Set up your API key (example for Gemini):

```bash
export GEMINI_API_KEY="your-api-key-here"
```

## Basic Usage

```python
import asyncio
from gepa_adk.engine import AsyncReflectiveMutationProposer

async def main():
    # Create proposer with default settings
    proposer = AsyncReflectiveMutationProposer()

    # Define current candidate
    candidate = {
        "instruction": "You are a helpful assistant. Answer questions clearly."
    }

    # Provide feedback from evaluation
    reflective_dataset = {
        "instruction": [
            {
                "input": "What is machine learning?",
                "output": "Machine learning is a subset of AI...",
                "score": 0.6,
                "feedback": "Answer was too long and technical for a beginner question",
            },
            {
                "input": "Summarize this article",
                "output": "The article discusses...",
                "score": 0.9,
                "feedback": "Good concise summary, well-structured",
            },
        ]
    }

    # Generate mutation proposal
    result = await proposer.propose(
        candidate=candidate,
        reflective_dataset=reflective_dataset,
        components_to_update=["instruction"],
    )

    if result:
        print("Proposed instruction:")
        print(result["instruction"])
    else:
        print("No proposal generated (empty dataset)")

asyncio.run(main())
```

## Configuration Options

### Custom Model

```python
# Use OpenAI GPT-4
proposer = AsyncReflectiveMutationProposer(
    model="openai/gpt-4",
)

# Use Anthropic Claude
proposer = AsyncReflectiveMutationProposer(
    model="anthropic/claude-3-sonnet-20240229",
)
```

### Local Testing with Ollama (Free)

**Recommended for development** - zero API cost!

```bash
# Set in .env (already configured in project)
OLLAMA_API_BASE=http://192.168.87.58:11434  # Your Ollama host

# Or for Docker/Podman containers:
# OLLAMA_API_BASE=http://host.docker.internal:11434
```

```python
# Use ollama/ prefix - LiteLLM auto-detects OLLAMA_API_BASE
proposer = AsyncReflectiveMutationProposer(
    model="ollama/llama3.1",  # Must have ollama/ prefix!
)

# Or for better chat responses:
proposer = AsyncReflectiveMutationProposer(
    model="ollama_chat/llama3.1",
)
```

**Important**: The `ollama/` prefix is required! Setting `OPENAI_API_BASE` to your Ollama endpoint won't work - LiteLLM routes based on model prefix.

| Environment | Model | Cost |
|-------------|-------|------|
| Local dev | `ollama/llama3.1` | Free |
| CI/Integration | `gemini/gemini-2.0-flash` | Minimal |
| Production | `vertex_ai/gemini-2.0-flash` | API cost |

### Temperature Control

```python
# More deterministic (lower creativity)
proposer = AsyncReflectiveMutationProposer(temperature=0.3)

# More creative variations
proposer = AsyncReflectiveMutationProposer(temperature=1.0)
```

### Custom Prompt Template

```python
custom_template = """
Analyze this agent instruction and the feedback provided.

## Current Instruction
{current_instruction}

## User Feedback
{feedback_examples}

## Your Task
Write an improved instruction that addresses the feedback.
Output ONLY the new instruction.
"""

proposer = AsyncReflectiveMutationProposer(
    prompt_template=custom_template,
)
```

## Handling Empty Datasets

The proposer returns `None` when there's no feedback to work with:

```python
result = await proposer.propose(
    candidate={"instruction": "Be helpful"},
    reflective_dataset={},  # Empty - no feedback available
    components_to_update=["instruction"],
)

if result is None:
    print("Skipping mutation - no feedback data")
```

## Error Handling

```python
import litellm

try:
    result = await proposer.propose(candidate, dataset, ["instruction"])
except litellm.AuthenticationError:
    print("Check your API key")
except litellm.RateLimitError:
    print("Rate limited - try again later")
except litellm.APIError as e:
    print(f"API error: {e}")
```

## Integration with AsyncGEPAEngine

The proposer can be used by adapter implementations:

```python
from gepa_adk.engine import AsyncReflectiveMutationProposer
from gepa_adk.ports import AsyncGEPAAdapter

class MyAdapter(AsyncGEPAAdapter):
    def __init__(self):
        self._proposer = AsyncReflectiveMutationProposer()

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset,
        components_to_update: list[str],
    ) -> dict[str, str]:
        result = await self._proposer.propose(
            candidate, reflective_dataset, components_to_update
        )
        # Return original if no proposal generated
        if result is None:
            return {k: candidate[k] for k in components_to_update}
        return result
```

## Testing with Mocks

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_proposer_calls_litellm():
    proposer = AsyncReflectiveMutationProposer()

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "Improved instruction"

    with patch("litellm.acompletion", return_value=mock_response) as mock_llm:
        result = await proposer.propose(
            candidate={"instruction": "Original"},
            reflective_dataset={"instruction": [{"feedback": "Needs work"}]},
            components_to_update=["instruction"],
        )

        mock_llm.assert_called_once()
        assert result == {"instruction": "Improved instruction"}
```

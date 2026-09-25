# Single-Agent Evolution

This guide covers basic agent evolution patterns for optimizing a single LlmAgent.

!!! tip "Working Examples"
    Complete runnable examples:

    - **[examples/basic_evolution.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/basic_evolution.py)** — Greeting agent with critic
    - **[examples/critic_agent.py](https://github.com/Alberto-Codes/gepa-adk/blob/HEAD/examples/critic_agent.py)** — Story generation with critic

## When to Use This Pattern

Use single-agent evolution when:

- You have one agent that needs instruction optimization
- You can define clear scoring criteria via a critic agent
- You want straightforward instruction improvement

## Prerequisites

- Python 3.12+
- gepa-adk installed (`uv add gepa-adk`)
- Ollama running locally with a model (e.g., `llama3.2:latest`)
- `OLLAMA_API_BASE` environment variable set

```bash
export OLLAMA_API_BASE=http://localhost:11434
```

## Basic Evolution with Critic

The standard pattern uses a **critic agent** to score the evolved agent's outputs.

### Step 1: Create the Agent to Evolve

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

agent = LlmAgent(
    name="greeter",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Greet the user appropriately based on their introduction.",
)
```

### Step 2: Create a Critic Agent

The critic evaluates outputs and provides scores. Use `SimpleCriticOutput` for basic scoring:

```python
from gepa_adk import SimpleCriticOutput

critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Score for formal, Dickens-style greetings. 0.0-1.0.",
    output_schema=SimpleCriticOutput,
)
```

Or define a custom critic schema for richer feedback:

```python
from pydantic import BaseModel, Field

class CriticOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str

critic = LlmAgent(
    name="critic",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="""Evaluate greeting quality. Look for formal, elaborate,
Dickens-style greetings appropriate for the social context.
Score 0.0-1.0 where 1.0 is a perfect formal greeting.""",
    output_schema=CriticOutput,
)
```

### Step 3: Prepare Training Data

```python
trainset = [
    {"input": "I am His Majesty, the King."},
    {"input": "I am your mother."},
    {"input": "I am a close friend."},
]
```

### Step 4: Run Evolution

```python
from gepa_adk import evolve, run_sync, EvolutionConfig

config = EvolutionConfig(
    max_iterations=5,
    patience=2,
    reflection_model="ollama_chat/llama3.2:latest",
)

result = run_sync(evolve(agent, trainset, critic=critic, config=config))

print(f"Original score: {result.original_score:.3f}")
print(f"Final score: {result.final_score:.3f}")
print(f"Improvement: {result.improvement:.2%}")
print(f"Evolved instruction:\n{result.evolved_components['instruction']}")
```

### Read the Iteration History

`result.iteration_history` holds one `IterationRecord` per iteration. Each
record's `failed_evaluations` counts the rows whose agent run or scorer
raised, or whose run returned a failed execution, in that iteration, across
every evaluation the iteration made. `result.baseline_failed_evaluations` counts them for the
initial candidate, and `result.total_failed_evaluations` is the baseline plus
the sum over the history.

A row that fails is scored 0.0 and counts toward the aggregate, the same as
a wrong answer. The count tells the two apart: a score of 0 with
`failed_evaluations == 0` means the agent answered and the scorer rejected
the answer, while a nonzero count means that many rows got their 0.0 because
the run or the scorer raised, not because of what the agent said. A run whose
low scores come from failures points at the model, tools, network or scorer,
not the instruction.

```python
for record in result.iteration_history:
    print(
        record.iteration_number,
        f"score={record.score:.3f}",
        f"failed={record.failed_evaluations}",
        record.skip_reason or "",
    )
print(f"Failed rows in total: {result.total_failed_evaluations}")
```

Results saved with `to_dict()` before these counts existed (schema version 1)
still load with `EvolutionResult.from_dict()`; their counts read as 0.

## Complete Working Example

```python
"""Single-agent evolution with critic scoring."""

import asyncio
import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from pydantic import BaseModel, Field

from gepa_adk import evolve, EvolutionConfig


class CriticOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str


async def main() -> None:
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("Set OLLAMA_API_BASE environment variable")

    agent = LlmAgent(
        name="greeter",
        model=LiteLlm(model="ollama_chat/llama3.2:latest"),
        instruction="Greet the user appropriately.",
    )

    critic = LlmAgent(
        name="critic",
        model=LiteLlm(model="ollama_chat/llama3.2:latest"),
        instruction="""Evaluate greeting quality. Look for formal, Dickens-style
greetings appropriate for the social context. Score 0.0-1.0.""",
        output_schema=CriticOutput,
    )

    trainset = [
        {"input": "I am His Majesty, the King."},
        {"input": "I am your mother."},
        {"input": "I am a close friend."},
    ]

    config = EvolutionConfig(
        max_iterations=5,
        patience=2,
        reflection_model="ollama_chat/llama3.2:latest",
    )

    result = await evolve(agent, trainset, critic=critic, config=config)

    print(f"Original: {result.original_score:.3f}")
    print(f"Final: {result.final_score:.3f}")
    print(f"Improvement: {result.improvement:.2%}")
    print(f"\nEvolved instruction:\n{result.evolved_components['instruction']}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration Options

### EvolutionConfig Parameters

```python
from gepa_adk import EvolutionConfig

config = EvolutionConfig(
    max_iterations=20,          # Maximum evolution iterations
    patience=5,                 # Stop after N iterations without improvement
    reflection_model="ollama_chat/llama3.2:latest",  # Model for generating improvements
    min_improvement_threshold=0.01,  # Minimum score gain to accept
    reflection_minibatch_size=None,  # Trainset rows a proposal must win on first
)
```

### Reflection Minibatch

By default every proposal is evaluated on the full trainset. Set
`reflection_minibatch_size` to gate each proposal on a sample first, as the
GEPA reference does:

```python
config = EvolutionConfig(
    max_iterations=30,
    reflection_minibatch_size=4,  # Sample 4 trainset rows per iteration
    seed=42,                      # Makes the sampled rows reproducible
)
```

Each iteration draws a fresh seeded sample of `k` trainset rows, where `k` is
the smaller of the setting and the trainset size. The proposal runs on those
rows, and its mean score is compared with its parent's cached scores on the
same rows. Only a strictly higher mean earns the full evaluation. A proposal
that loses or ties is recorded with `skip_reason="minibatch_rejected"` and
counts toward `patience`. Its record's `score` covers the sampled rows only.

Cost per iteration, with a trainset of `n` rows:

- A rejected proposal costs `k` rows.
- An accepted proposal costs `k + n` rows, plus the valset pass when you pass
  a separate valset. When the valset is the trainset, the full trainset batch
  is reused for scoring, as without the gate.

A setting of `None`, or one at least the trainset size, keeps the full
evaluation for every proposal.

The minibatch works alongside two other settings:

- `reflection_max_trials` caps how many trials the reflection prompt reads
  from the parent's cached full trainset batch. It does not change what is
  evaluated.
- `SubsetEvaluationPolicy` trims the valset scoring pass when a
  `candidate_selector` is set (see [Evaluation Policies](#evaluation-policies)).
  It is independent of the minibatch, which gates the trainset pass.

### Using Validation Sets

Split data for more robust optimization:

```python
# Given a larger dataset of examples
examples = [
    {"input": "I am the Mayor."},
    {"input": "I am your neighbor."},
    {"input": "I am a stranger."},
    {"input": "I am the postman."},
    {"input": "I am a visiting dignitary."},
    {"input": "I am your teacher."},
    {"input": "I am the shopkeeper."},
    {"input": "I am a lost traveler."},
    {"input": "I am your cousin."},
    {"input": "I am the village elder."},
]

trainset = examples[:8]   # 80% for training
valset = examples[8:]     # 20% for validation

result = run_sync(evolve(agent, trainset, valset=valset, critic=critic, config=config))
```

### Stop Callbacks

Add custom stopping conditions:

```python
from gepa_adk.adapters.stoppers import ScoreThresholdStopper

config = EvolutionConfig(
    max_iterations=50,
    patience=10,
    reflection_model="ollama_chat/llama3.2:latest",
    stop_callbacks=[ScoreThresholdStopper(0.95)],  # Stop at 95% score
)
```

See the [Stop Callbacks Guide](stoppers.md) for more options.

### Evaluation Policies

`AsyncGEPAEngine` accepts an `evaluation_policy` that picks which validation
examples to score each iteration, such as `SubsetEvaluationPolicy` for large
validation sets. A policy takes effect only through the Pareto state that a
`candidate_selector` creates, so a policy must be paired with a selector.
`evolve()` does not expose this parameter; build the engine directly.

```python
from gepa_adk.adapters.selection import (
    ParetoCandidateSelector,
    SubsetEvaluationPolicy,
)
from gepa_adk.engine import AsyncGEPAEngine

engine = AsyncGEPAEngine(
    adapter=my_adapter,
    config=config,
    initial_candidate=candidate,
    batch=trainset,
    valset=valset,
    candidate_selector=ParetoCandidateSelector(),
    evaluation_policy=SubsetEvaluationPolicy(subset_size=0.2),
)
```

#### Valid combinations

| `candidate_selector` | `evaluation_policy` | Result |
|---|---|---|
| none | none | Full evaluation |
| set | none | Full evaluation over the Pareto state |
| set | set | The policy decides which examples are scored |
| none | set | `ConfigurationError` at engine construction |

The last row applies to every explicit policy, including
`FullEvaluationPolicy()`.

### Async vs Sync

Use `evolve()` for async contexts, `run_sync(evolve(...))` for scripts:

```python
# Async
result = await evolve(agent, trainset, critic=critic, config=config)

# Sync (wraps async internally)
result = run_sync(evolve(agent, trainset, critic=critic, config=config))
```

## Advanced: Output Schema Evolution

You can evolve the agent's **output schema** in addition to instructions.

### When to Use

- Optimize field definitions and descriptions
- Refine data structure for better outputs
- Co-evolve instruction and schema together

### Example

```python
from pydantic import BaseModel, Field

class TaskOutput(BaseModel):
    result: str
    confidence: float = Field(ge=0.0, le=1.0)

agent = LlmAgent(
    name="task-agent",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Complete the task.",
    output_schema=TaskOutput,
)

# Evolve just the output schema
result = run_sync(evolve(
    agent,
    trainset,
    critic=critic,
    components=["output_schema"],
    config=config,
))

print(result.evolved_components["output_schema"])
```

### Evolving Both

```python
result = run_sync(evolve(
    agent,
    trainset,
    critic=critic,
    components=["instruction", "output_schema"],
    config=config,
))
```

### Using Evolved Schemas

```python
from gepa_adk.utils.schema_utils import deserialize_schema

EvolvedSchema = deserialize_schema(result.evolved_components["output_schema"])

evolved_agent = LlmAgent(
    name="evolved-agent",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction=result.evolved_components["instruction"],
    output_schema=EvolvedSchema,
)
```

## Advanced: Generation Config Evolution

Evolve LLM parameters like temperature and top_p.

### Example

```python
from google.genai.types import GenerateContentConfig

agent = LlmAgent(
    name="creative-agent",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Write creatively.",
    generate_content_config=GenerateContentConfig(
        temperature=0.7,
        top_p=0.9,
    ),
)

result = run_sync(evolve(
    agent,
    trainset,
    critic=critic,
    components=["generate_content_config"],
    config=config,
))

print(result.evolved_components["generate_content_config"])
```

## Advanced: Evolving Prompts Held by a Tool

Evolve prompt strings that a tool owns, such as the prompts it sends to an
external service, instead of the agent's own instruction.

### Example

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from gepa_adk import (
    EvolutionConfig,
    LabelAgreementScorer,
    evolve,
    register_mapping_components,
    run_sync,
)

prompts = {
    "summarize": "Summarize the ticket in one sentence.",
    "classify": "Label the ticket as bug, feature or question.",
}


def triage(ticket: str) -> str:
    """Send the ticket to the triage service with the current prompts."""
    return call_triage_service(ticket, prompts["summarize"], prompts["classify"])


agent = LlmAgent(
    name="triager",
    model=LiteLlm(model="ollama_chat/llama3.2:latest"),
    instruction="Pass the user's ticket to the triage tool and return its answer.",
    tools=[FunctionTool(triage)],
)

names = register_mapping_components(prompts)  # each key becomes a component
config = EvolutionConfig(max_iterations=10, acceptance_metric="mean")

result = run_sync(evolve(
    agent,
    trainset,
    scorer=LabelAgreementScorer(),
    components=names,
    component_selector="round_robin",
    config=config,
))

# Evaluation restores `prompts` after each run; apply the result yourself.
prompts.update({name: result.evolved_components[name] for name in names})
```

The round-robin selector rotates across the keys, so each iteration reflects on
one prompt. During evaluation the candidate text is written into `prompts` before
each run and restored afterwards, so the dict holds the original text when
`evolve()` returns.

### How trainset input reaches the tool

The trainset `input` string is the user message the agent receives. The agent
decides to call the tool and passes it whatever arguments it chooses, usually
that text. When the tool needs structured state, serialize it into the `input`
string as JSON and let the agent or the tool parse it:

```python
import json

row = {
    "input": json.dumps({"ticket": "App crashes on login", "priority": "high"}),
    "expected": "bug",
}
```

gepa-adk does not pass a dict through to the tool.

## Related Guides

- [Critic Agents](critic-agents.md) — Detailed critic patterns
- [Multi-Agent](multi-agent.md) — Evolve multiple agents together
- [Workflows](workflows.md) — Optimize agent pipelines

## API Reference

- [`evolve()`][gepa_adk.api.evolve] — Async evolution
- [`run_sync()`][gepa_adk.api.run_sync] — Sync wrapper for async evolution
- [`EvolutionConfig`][gepa_adk.domain.models.EvolutionConfig] — Configuration
- [`EvolutionResult`][gepa_adk.domain.models.EvolutionResult] — Results
- [`register_mapping_components()`][gepa_adk.adapters.components.mapping_handler.register_mapping_components] — Register a caller-owned mapping

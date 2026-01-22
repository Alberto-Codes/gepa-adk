# Workflow Agent Design Questions

## GEPA Fundamentals

### What is GEPA?

**GEPA = Genetic-Pareto prompt optimizer**

An evolutionary algorithm that optimizes **text components** of any system using:
1. **Evaluation** - Run the system, get scores
2. **Reflection** - Analyze what worked/didn't work
3. **Mutation** - Propose improved text based on reflection
4. **Selection** - Accept improvements, track Pareto frontier

### What Does GEPA Do?

GEPA takes a **candidate** (`dict[str, str]` mapping component names to text) and iteratively improves it:

```
Loop:
  1. EVALUATE: Run candidate on batch → outputs, scores, trajectories
  2. REFLECT: Build reflective dataset from trajectories
  3. PROPOSE: LLM analyzes dataset → proposes new component text
  4. ACCEPT/REJECT: If score improves → accept mutation
```

**Key insight**: GEPA doesn't care what the "system" is. It just needs:
- A way to **run** the system and get scores
- A way to **capture execution context** (trajectories)
- A way to **surface that context** for reflection

### What Does GEPA Need? (The Adapter Contract)

From `GEPAAdapter`, GEPA needs exactly **3 things**:

#### 1. `evaluate(batch, candidate) → EvaluationBatch`
- **Inputs**: batch of examples + candidate (component texts)
- **Outputs**:
  - `outputs` - what the system produced (opaque to GEPA)
  - `scores` - per-example numeric scores (higher = better)
  - `trajectories` - execution context for reflection (opaque to GEPA)

#### 2. `make_reflective_dataset(candidate, eval_batch, components_to_update) → dict`
- **Purpose**: Transform trajectories into a JSON-serializable dataset for the reflection LLM
- **Output format** (recommended):
  ```python
  {
    "component_name": [
      {
        "Inputs": {...},           # What went in
        "Generated Outputs": {...}, # What came out
        "Feedback": "..."          # What was wrong/right
      },
      ...
    ]
  }
  ```

#### 3. (Optional) `propose_new_texts(candidate, reflective_dataset, components_to_update) → dict[str, str]`
- Custom proposal logic (GEPA has a default)

---

## The Key Realization

GEPA doesn't need "the output" - it needs **trajectories** that can be transformed into a **reflective dataset**.

For workflow agents, the question isn't "which output do we score?" but rather:

> **What execution context (trajectories) should we capture, and how do we transform that into a reflective dataset that helps the reflection LLM propose better component text?**

- The **scorer** sees ONE thing (whatever we decide is "the output")
- The **reflection** sees EVERYTHING we capture in trajectories

---

## Current GEPA-ADK Support Inventory

### Single Agent (`evolve()`)
| Feature | How It Works |
|---------|--------------|
| **Evolvable Components** | `instruction`, `output_schema`, `generate_content_config` |
| **Scorer Input** | Agent's output text |
| **Trajectory Capture** | Tool calls, state deltas, token usage from single execution |
| **Reflective Dataset** | Trials with input, output, feedback |

### Agent Groups (`evolve_group()`)
| Feature | How It Works |
|---------|--------------|
| **Evolvable Components** | Per-agent via qualified names (`generator.instruction`, `critic.output_schema`) |
| **Primary Agent** | Designated agent whose output is scored |
| **Session Sharing** | Optional `share_session=True` wraps in `SequentialAgent` |
| **Scorer Input** | Primary agent's output |
| **Trajectory Capture** | Per-agent trajectories via `partition_events_by_agent()` |

### Workflow Agents (`evolve_workflow()`)
| Feature | Current Status |
|---------|----------------|
| **Discovery** | `find_llm_agents()` traverses nested workflows |
| **Delegation** | Converts to dict, calls `evolve_group(share_session=True)` |
| **Primary** | Defaults to **last discovered** agent |
| **Output Extraction** | ⚠️ **Gets FIRST final response, not last** |

---

## What We Do Well: Single Agent Evolution

This section documents the defaults and requirements for critic and reflection agents that make single agent evolution work smoothly.

### Critic Agent Defaults and Requirements

#### Output Schemas (choose one)

**SimpleCriticOutput** - KISS schema for basic evaluation:
```python
class SimpleCriticOutput(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)  # Required
    feedback: str = Field(...)                  # Required
```

**CriticOutput** - Advanced schema with dimensions:
```python
class CriticOutput(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)  # Required
    feedback: str = Field(default="")           # Optional
    dimension_scores: dict[str, float] = Field(default_factory=dict)  # Optional
    actionable_guidance: str = Field(default="")  # Optional
```

#### Default Instructions

**SIMPLE_CRITIC_INSTRUCTION**:
```
Evaluate the quality of the output.

Provide:
- A score from 0.0 (poor) to 1.0 (excellent)
- Feedback explaining what works and what doesn't

Focus on clarity, accuracy, and completeness in your evaluation.
```

**ADVANCED_CRITIC_INSTRUCTION**:
```
Evaluate the quality of the output across multiple dimensions.

Provide:
- An overall score from 0.0 (poor) to 1.0 (excellent)
- Feedback explaining what works and what doesn't
- Dimension scores for specific quality aspects you identify
- Actionable guidance for concrete improvement steps
```

#### Critic Requirements Summary
| Requirement | Details |
|------------|---------|
| **Output Format** | JSON with `score` field (required) |
| **Score Range** | 0.0 to 1.0 (float) |
| **Feedback** | Recommended for reflection quality |
| **Normalization** | `normalize_feedback()` converts to trial format |

### Reflection Agent Defaults and Requirements

#### Default Instruction (REFLECTION_INSTRUCTION)
```
## Component Text to Improve
{component_text}

## Trials
{trials}

Propose an improved version of the component text based on the trials above.
Return ONLY the improved component text, nothing else.
```

#### Component-Aware Instructions

**SCHEMA_REFLECTION_INSTRUCTION** (for `output_schema`):
- Includes validation tool guidance
- Instructs to use `validate_output_schema` before returning
- Returns Pydantic class definition only

**CONFIG_REFLECTION_INSTRUCTION** (for `generate_content_config`):
- Includes parameter guidelines table (temperature, top_p, top_k, etc.)
- Guides analysis of trial patterns
- Returns YAML configuration only

#### Component Registry (Auto-Selection)
| Component Name | Factory | Special Tools |
|---------------|---------|---------------|
| `output_schema` | `create_schema_reflection_agent` | `validate_output_schema` tool |
| `generate_content_config` | `create_config_reflection_agent` | None (validation in handler) |
| *default* | `create_text_reflection_agent` | None |

#### Reflection Requirements Summary
| Requirement | Details |
|------------|---------|
| **Placeholders** | Must accept `{component_text}` and `{trials}` |
| **Output Key** | Must use `output_key="proposed_component_text"` |
| **Return Format** | Plain text (the improved component) |
| **Session State** | Receives `component_text` (str) and `trials` (JSON string) |

### Trial Structure (What Reflection Sees)

Each trial record passed to reflection contains:
```python
{
    "feedback": {
        "score": 0.85,           # From critic
        "feedback_text": "...",   # From critic
        "dimension_scores": {...}, # Optional
        "actionable_guidance": "..." # Optional
    },
    "trajectory": {
        "input": "...",          # Original task input
        "output": "...",         # Agent's generated output
        "trace": {...}           # ADK execution trace (tool calls, etc.)
    }
}
```

### How Critic + Reflection Work Together

```
┌─────────────┐    output    ┌─────────────┐    score,     ┌─────────────────┐
│  Agent      │─────────────>│  Critic     │───feedback───>│  Trial Builder  │
│  (evolving) │              │  (scoring)  │               │                 │
└─────────────┘              └─────────────┘               └────────┬────────┘
                                                                    │
                                                                    │ trials
                                                                    ▼
┌─────────────┐    proposed   ┌─────────────────┐                   │
│  Component  │<─────text─────│  Reflection     │<──────────────────┘
│  Handler    │               │  Agent          │
└─────────────┘               └─────────────────┘
```

1. **Agent** produces output from input
2. **Critic** scores output → `{score, feedback, dimensions, guidance}`
3. **Trial Builder** combines into `{feedback, trajectory}`
4. **Reflection Agent** receives `{component_text, trials}` → proposes improvement
5. **Component Handler** applies proposed text to candidate

---

## What We Do Well: Multi-Agent Evolution

This section documents the patterns and requirements for multi-agent instruction evolution via `evolve_group()`.

### Qualified Component Names (ADR-012)

Multi-agent evolution uses **dot-separated qualified names** to address components:

```
{agent_name}.{component_name}
```

**Examples:**
- `generator.instruction`
- `critic.output_schema`
- `refiner.generate_content_config`

**Why dot separator?** ADK agent names are Python identifiers (no dots allowed), so parsing is always unambiguous.

```python
from gepa_adk.domain.types import ComponentSpec

# Construction
spec = ComponentSpec(agent="generator", component="instruction")
name = spec.qualified  # "generator.instruction"

# Parsing
spec = ComponentSpec.parse("critic.output_schema")
print(spec.agent)      # "critic"
print(spec.component)  # "output_schema"
```

### Per-Agent Component Configuration

The `components` parameter controls which components evolve for each agent:

```python
result = await evolve_group(
    agents={"generator": gen, "reviewer": rev, "validator": val},
    primary="reviewer",
    trainset=trainset,
    components={
        "generator": ["instruction"],           # Evolve instruction only
        "reviewer": ["instruction", "output_schema"],  # Evolve both
        "validator": [],                        # Exclude from evolution
    },
)
```

| Configuration | Effect |
|--------------|--------|
| `["instruction"]` | Evolve only the instruction |
| `["instruction", "output_schema"]` | Evolve both components |
| `[]` | Agent participates but is NOT evolved |

### Session State Sharing via output_key

Agents share state through ADK's `output_key` mechanism:

```python
# Generator 1 saves output to session state
generator1 = LlmAgent(
    name="generator1",
    instruction="Generate initial content...",
    output_key="gen1_output",  # Saves to session.state["gen1_output"]
)

# Generator 2 references it via template
generator2 = LlmAgent(
    name="generator2",
    instruction=(
        "You received this initial response:\n"
        "{gen1_output}\n\n"  # ADK substitutes from session state
        "Expand and improve this response..."
    ),
    output_key="gen2_output",
)
```

**Flow:**
```
┌─────────────┐   output_key    ┌─────────────────┐   {gen1_output}   ┌─────────────┐
│ Generator 1 │───────────────> │  session.state  │ ────────────────> │ Generator 2 │
└─────────────┘                 │ ["gen1_output"] │                   └─────────────┘
```

### Round-Robin Iteration

The engine cycles through components each iteration:

```python
result = await evolve_group(
    agents={"generator": gen, "reviewer": rev},
    primary="reviewer",
    trainset=trainset,
    config=EvolutionConfig(max_iterations=4),
)

# Inspect which component was evolved each iteration
for record in result.iteration_history:
    print(f"Iteration {record.iteration_number}: {record.evolved_component}")
```

Output:
```
Iteration 1: generator.instruction
Iteration 2: reviewer.instruction
Iteration 3: generator.instruction
Iteration 4: reviewer.instruction
```

### Reflection Agent (Same Requirements)

Multi-agent reflection uses the **same placeholders and output key** as single-agent:

```python
reflection_agent = LlmAgent(
    name="reflector",
    model="gemini-2.0-flash",
    instruction=(
        "## Current Instruction\n"
        "{component_text}\n\n"          # Same placeholder
        "## Trial Results\n"
        "{trials}\n\n"                  # Same placeholder
        "Based on the trial results above, write an improved instruction.\n"
        "Return ONLY the improved instruction text."
    ),
    output_key="proposed_component_text",  # Same output key
)
```

### Trial Structure (Extended for Multi-Agent)

Multi-agent trials include additional component context:

```python
{
    "feedback": {
        "score": 0.7,
        "feedback_text": "...",
        "dimension_scores": {...},      # Optional
        "actionable_guidance": "..."    # Optional
    },
    "trajectory": {
        "input": "...",
        "output": "...",
        "component": "generator.instruction",  # Which component
        "component_value": "current instruction text...",
        "tokens": 1234                  # Optional: total token usage
    }
}
```

### How Multi-Agent Evolution Works

```
┌─────────────┐  output_key  ┌─────────────┐  output_key  ┌─────────────┐
│ Generator 1 │─────────────>│ Generator 2 │─────────────>│   Critic    │
│  (evolving) │              │  (evolving) │              │  (scoring)  │
└─────────────┘              └─────────────┘              └──────┬──────┘
                                                                 │
                                   score, feedback               │
                    ┌────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│         Trial Builder               │
│  - Builds trial per example         │
│  - Adds component context           │
└──────────────────┬──────────────────┘
                   │ trials
                   ▼
┌─────────────────────────────────────┐
│       Reflection Agent              │
│  - Receives {component_text, trials}│
│  - Proposes improved instruction    │
└──────────────────┬──────────────────┘
                   │ proposed text
                   ▼
┌─────────────────────────────────────┐
│       Round-Robin Selector          │
│  - Iter 1: generator1.instruction   │
│  - Iter 2: generator2.instruction   │
│  - Iter 3: generator1.instruction   │
└─────────────────────────────────────┘
```

### Key Differences from Single Agent

| Aspect | Single Agent | Multi-Agent |
|--------|--------------|-------------|
| **Component Names** | `instruction` | `generator.instruction` |
| **Configuration** | `components=["instruction"]` | `components={"gen": ["instruction"]}` |
| **Session State** | Isolated | Shared via `output_key` |
| **Iteration** | Same component each time | Round-robin across agents |
| **Trajectory** | Single agent trace | Per-agent via `partition_events_by_agent()` |

---

## Proposed Workflow Evolution Design

### Core Principle: Separation of Concerns

**Scoring** and **Evolution** are independent:

| Concern | Question | Default |
|---------|----------|---------|
| **Scoring** | What does the critic evaluate? | Last agent's output (final result) |
| **Evolution** | Which agent(s) get mutated? | First agent only |

These don't affect each other. Even when evolving multiple agents, the critic always scores the final output to answer: "did the pipeline as a whole get better?"

### Default Behavior

```python
# Zero config: sensible defaults
result = await evolve_workflow(workflow, trainset)
```

| Aspect | Default | Rationale |
|--------|---------|-----------|
| **Score** | Last agent's output | Final result is what matters |
| **Evolve** | First agent only | Improve the source, downstream benefits |
| **Trajectories** | All agents captured | Rich context for reflection |

### Easy Options

```python
# Round-robin: evolve all agents in rotation
result = await evolve_workflow(workflow, trainset, round_robin=True)

# Iteration 1: evolve generator.instruction, score final output
# Iteration 2: evolve addendumer.instruction, score final output
# Iteration 3: evolve refiner.instruction, score final output
# Iteration 4: evolve generator.instruction, score final output
# ...
```

### Full Control

```python
# Explicit component configuration
result = await evolve_workflow(
    workflow,
    trainset,
    components={
        "generator": ["instruction"],      # Evolve
        "addendumer": ["instruction"],     # Evolve
        "refiner": [],                     # Exclude from evolution
    },
)
```

### Custom Critics

Default critic sees final output. Custom critics can access any intermediate state:

```python
critic = LlmAgent(
    instruction="""
    Generator produced: {generator_output}
    Addendumer added: {addendumer_output}
    Final result: {refiner_output}

    Evaluate the quality of the final result considering
    how well each stage contributed...
    """,
    output_schema=CriticOutput,
)

result = await evolve_workflow(workflow, trainset, critic=critic)
```

### API Summary

```python
await evolve_workflow(
    workflow,                    # SequentialAgent, LoopAgent, etc.
    trainset,                    # List of examples
    # Scoring
    critic=None,                 # Default: use last output, custom: any LlmAgent
    # Evolution
    round_robin=False,           # True: cycle all agents, False: first only
    components=None,             # None: auto, dict: explicit per-agent control
    # Standard options
    config=EvolutionConfig(...),
    reflection_agent=None,       # Same requirements as single/multi-agent
)
```

---

## Workflow Scenarios (Resolved)

### Scenario 1: Pipeline `[A] → [B] → [C]`
```
[Generator] → [Addendumer] → [Refiner] → final output
```
- **Score**: Refiner's output (last)
- **Evolve (default)**: Generator only (first)
- **Evolve (round_robin)**: All three in rotation
- **Trajectories**: All captured for reflection context

### Scenario 2: Generator → Critic Pipeline
```
[Generator] → output → [Critic] → feedback
```
- **Score**: Critic's output (last) - contains the score
- **Evolve**: Generator (first) - what we're improving
- **Note**: Critic is part of workflow, provides score AND feedback

### Scenario 3: Loop Agent
```
[Refiner] loops N times → progressive output
```
- **Score**: Final iteration output
- **Evolve**: Refiner instruction (only one agent)
- **Trajectories**: All iterations captured

### Scenario 4: Nested Workflows
```
SequentialAgent([
    ParallelAgent([ResearcherA, ResearcherB]),
    Synthesizer,
    Writer,
])
```
- **Score**: Writer's output (last)
- **Evolve (default)**: First discovered LlmAgent
- **Evolve (round_robin)**: All discovered LlmAgents
- **Discovery**: `find_llm_agents()` traverses nested structure

---

## Implementation Tasks

### Task 1: Fix Output Extraction (#212)
- Current: gets FIRST final response
- Needed: get LAST agent's output for scoring
- Location: `extract_final_output()` in `utils/events.py`

### Task 2: Wire Up Defaults
- Auto-detect first/last agents from workflow structure
- Default `primary` to last agent (for scoring)
- Default `evolve` to first agent (for mutation)
- Implement `round_robin=True` flag

### Task 3: Trajectory Context
- Already have `partition_events_by_agent()`
- Ensure all agent outputs available in session state
- Include intermediate outputs in trial trajectory for reflection

---

## Related Issues

- #212 - Workflow critic output extraction bug
- #184 - SessionNotFoundError fix (completed)

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

## Architectural Analysis

### Current Implementation Status

#### What We Have (Solid Foundation)

| Component | Status | Location |
|-----------|--------|----------|
| `find_llm_agents()` | ✅ Works | `adapters/workflow.py:84-204` |
| SequentialAgent discovery | ✅ Works | Traverses `sub_agents` |
| LoopAgent discovery | ✅ Works | Traverses inner agent |
| ParallelAgent discovery | ✅ Works | Traverses `sub_agents` |
| Nested workflow traversal | ✅ Works | Up to `max_depth` (default 5) |
| Delegation to `evolve_group()` | ✅ Works | `api.py:957-966` |
| Per-agent component config | ✅ Works | `components={...}` pattern |
| Session sharing | ✅ Works | Hardcoded `share_session=True` |
| `partition_events_by_agent()` | ✅ Works | `utils/events.py:737-791` |

#### Identified Gaps

| Gap | Priority | Impact | Location |
|-----|----------|--------|----------|
| Output extraction returns FIRST not LAST | 🔴 High | Scoring broken for pipelines | `utils/events.py:438-439` |
| No "evolve first only" default | 🟡 Medium | All agents round-robin | `api.py:618-620` |
| No `round_robin=True` flag | 🟡 Medium | Missing easy option | `api.py` |
| LoopAgent config lost | 🟡 Medium | `max_iterations` discarded | `multi_agent.py:530` |
| ParallelAgent semantics lost | 🟡 Medium | Becomes sequential | `multi_agent.py:530` |
| Workflow structure not preserved | 🟠 Low | Can't reconstruct original | N/A |

### The Sticky Parts

#### LoopAgent Semantics

```python
LoopAgent(agent=Refiner, max_iterations=3)
```

| Aspect | Current | Needed |
|--------|---------|--------|
| Discovery | ✅ Returns `[Refiner]` | Works |
| Execution | ❌ Flattened to sequential | Preserve loop structure |
| Config | ❌ `max_iterations=3` lost | Preserve and use |
| Output | ? | Final iteration output |
| Trajectories | ? | All iterations for reflection |

**Question**: During evolution, should the loop execute N times or 1 time?
**Proposal**: Execute the LoopAgent as-is (N iterations), score final output, capture all iterations in trajectory.

#### ParallelAgent Semantics

```python
ParallelAgent(sub_agents=[ResearcherA, ResearcherB, ResearcherC])
```

| Aspect | Current | Needed |
|--------|---------|--------|
| Discovery | ✅ Returns all 3 agents | Works |
| Execution | ❌ Becomes sequential | Preserve parallel execution |
| Output | ? Unclear | Define aggregation strategy |
| Trajectories | ? | All agent outputs |

**Question**: What's the "output" to score when agents run in parallel?
**Options**:
1. Last agent by discovery order
2. Concatenate all outputs
3. Require user to specify primary
4. Use session state aggregation

**Proposal**: Default to last discovered agent's output, allow `primary="agent_name"` override.

#### Nested Workflows

```python
SequentialAgent([
    ParallelAgent([ResearcherA, ResearcherB]),  # Both run in parallel
    Synthesizer,                                  # Gets both outputs via state
    Writer,                                       # Final output
])
```

| Question | Answer |
|----------|--------|
| What's "first" agent? | First discovered LlmAgent (ResearcherA) |
| What's "last" agent? | Last in outermost sequence (Writer) |
| Parallel outputs? | Available via `{researcherA_output}`, `{researcherB_output}` |
| Scoring | Writer's output (final) |

**Key insight**: Discovery order determines first/last, but execution preserves workflow structure.

### Workflow Type Comparison

| Workflow Type | Sub-agents | Execution | Output | First/Last |
|---------------|------------|-----------|--------|------------|
| **SequentialAgent** | Ordered list | One after another | Last agent | Clear |
| **LoopAgent** | Single agent | N iterations | Final iteration | Same agent |
| **ParallelAgent** | Unordered list | All at once | Aggregated? | Ambiguous |

---

## Proposed GitHub Issues

### Phase 1: Fix Fundamentals (Blockers)

#### Issue: Fix output extraction to return LAST agent output
- **Priority**: 🔴 High (blocks correct scoring)
- **File**: `src/gepa_adk/utils/events.py`
- **Function**: `extract_final_output()`
- **Current**: Returns FIRST `is_final_response()` event
- **Needed**: Return LAST `is_final_response()` event
- **Tests**: Update existing, add pipeline-specific tests
- **Labels**: `bug`, `workflow-agents`, `priority-high`

#### Issue: Add `round_robin` flag to `evolve_workflow()`
- **Priority**: 🟡 Medium
- **File**: `src/gepa_adk/api.py`
- **Function**: `evolve_workflow()`
- **Changes**:
  - Add `round_robin: bool = False` parameter
  - When `False`: evolve first discovered agent only
  - When `True`: cycle all discovered agents
- **Labels**: `enhancement`, `workflow-agents`

### Phase 2: Preserve Workflow Semantics

#### Issue: Execute workflows as-is instead of flattening
- **Priority**: 🟡 Medium
- **File**: `src/gepa_adk/adapters/multi_agent.py`
- **Function**: `_build_pipeline()`
- **Current**: Creates flat `SequentialAgent` with all agents
- **Needed**: Execute original workflow structure with instruction overrides
- **Impact**:
  - LoopAgent executes N iterations
  - ParallelAgent runs agents in parallel
  - Nested workflows preserve structure
- **Labels**: `enhancement`, `workflow-agents`, `breaking-change`

#### Issue: Define ParallelAgent output semantics
- **Priority**: 🟡 Medium
- **Scope**: Design decision + implementation
- **Options to document**:
  1. Last discovered agent's output (default)
  2. Concatenate all outputs
  3. Require explicit `primary` parameter
  4. Session state with all outputs
- **Deliverable**: ADR + implementation
- **Labels**: `enhancement`, `workflow-agents`, `needs-design`

### Phase 3: Edge Cases & Polish

#### Issue: Document nested workflow first/last rules
- **Priority**: 🟠 Low
- **Scope**: Documentation + validation
- **Rules to codify**:
  - First = first LlmAgent in depth-first traversal
  - Last = last LlmAgent in outermost workflow
  - Parallel = all agents, primary selectable
- **Labels**: `documentation`, `workflow-agents`

#### Issue: Trajectory capture for parallel execution
- **Priority**: 🟠 Low
- **File**: `src/gepa_adk/utils/events.py`
- **Scope**: Ensure parallel agent outputs captured correctly
- **Current**: `partition_events_by_agent()` exists
- **Needed**: Verify works for parallel execution, expose in trial
- **Labels**: `enhancement`, `workflow-agents`

---

## Implementation Order

```
Phase 1: Foundation (Do First)
│
├── #1 Fix extract_final_output()     [BLOCKER - nothing works without this]
│   └── Change iteration to collect LAST final response
│
└── #2 Add round_robin flag           [Enables proposed defaults]
    ├── Default False = evolve first only
    └── True = cycle all agents

Phase 2: Semantics (Core Value)
│
├── #3 Preserve workflow structure    [Major improvement]
│   ├── Don't flatten to SequentialAgent
│   ├── LoopAgent loops N times
│   └── ParallelAgent runs parallel
│
└── #4 ParallelAgent output strategy  [Design decision needed]
    └── ADR + implementation

Phase 3: Polish (Nice to Have)
│
├── #5 Document first/last rules      [Clarity for users]
│
└── #6 Parallel trajectory capture    [Better reflection context]
```

### Dependencies

```
#1 ─────────────────────────────────────────────┐
                                                │
#2 ─────────────────────────────────────────────┼──► Phase 1 Complete
                                                │
#3 ◄──────────────────────────────── depends on #1
                                                │
#4 ◄──────────────────────────────── depends on #3
                                                │
#5 ◄──────────────────────────────── depends on #4
                                                │
#6 ◄──────────────────────────────── depends on #3
```

---

## Related Issues

- #212 - Workflow critic output extraction bug (same as Issue #1 above)
- #184 - SessionNotFoundError fix (completed)

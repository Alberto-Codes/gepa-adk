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

## Design Questions (Reframed)

### 1. Scoring: What Output Do We Score?

For the scorer/critic that produces the evaluation score:

| Scenario | What to Score? |
|----------|----------------|
| `[A] → [B] → [C]` pipeline | C's output (final result)? |
| `[Generator] → [Critic]` | Generator's output (what we're improving)? |
| `[Refiner] loops N times` | Final iteration output? |

**Current behavior**: Primary agent's output (defaults to last discovered)
**Problem**: Output extraction gets first final response, not last

### 2. Trajectories: What Context Do We Capture?

For building the reflective dataset that drives mutation:

| Scenario | What to Capture? |
|----------|------------------|
| `[A] → [B] → [C]` pipeline | All agent outputs? Just relevant ones? |
| `[Generator] → [Critic]` | Both outputs + critic's feedback? |
| `[Refiner] loops N times` | All iterations? Just final? |

**Current capability**: `partition_events_by_agent()` can split events per agent
**Question**: How do we transform multi-agent trajectories into useful reflective datasets?

### 3. Reflective Dataset: What Does the Reflection LLM Need?

For each component being evolved, what context helps the reflection LLM propose better text?

| Component Being Evolved | Useful Context |
|------------------------|----------------|
| Generator instruction | Generator's output + final score/feedback |
| Critic instruction | Critic's evaluation + whether it was accurate |
| Intermediate agent | Its output + downstream impact |

**Question**: Should reflective dataset include outputs from ALL agents or just the one being evolved?

### 4. Component Evolution: Which Agents Can Evolve?

| Question | Options |
|----------|---------|
| Evolve all discovered LlmAgents? | Yes (current) / Configurable subset |
| What about "infrastructure" agents? | Maybe exclude from evolution |
| Coupled updates? | Some components may need to evolve together |

---

## Workflow Scenarios to Support

### Scenario 1: Pipeline Critic
```
[Validator] → plain text → [Scorer] → JSON score
```
- **Score**: Scorer's JSON output
- **Trajectory**: Both agent outputs
- **Evolve**: Probably just Scorer's instruction

### Scenario 2: Generator → Critic Pipeline
```
[Generator] → output → [Critic] → feedback
```
- **Score**: Could be Critic's score OR external evaluation of Generator
- **Trajectory**: Generator output + Critic feedback
- **Evolve**: Generator instruction (using Critic feedback in reflection)

### Scenario 3: Multi-Stage Processing
```
[Researcher] → [Analyzer] → [Writer] → final output
```
- **Score**: Final output quality
- **Trajectory**: All intermediate outputs (rich context)
- **Evolve**: All agents? Just Writer? Configurable?

### Scenario 4: Loop Agent
```
[Refiner] loops N times → progressive output
```
- **Score**: Final iteration output
- **Trajectory**: All iterations (shows improvement trajectory)
- **Evolve**: Refiner instruction

---

## Next Steps

1. Decide on default behaviors for each scenario
2. Determine what configuration options are needed
3. Fix output extraction to get correct agent's output
4. Enhance trajectory capture for multi-agent workflows
5. Design reflective dataset transformation for workflows

---

## Related Issues

- #212 - Workflow critic output extraction bug
- #184 - SessionNotFoundError fix (completed)

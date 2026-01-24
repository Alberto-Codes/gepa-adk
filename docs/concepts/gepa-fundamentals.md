# GEPA Fundamentals

This document explains what GEPA is, how the evolution loop works, and what the adapter contract requires.

## What is GEPA?

**GEPA = Genetic-Pareto prompt optimizer**

GEPA is an evolutionary algorithm that optimizes **text components** of any system. It treats prompts, instructions, and configurations as evolvable "genes" that can be improved through iteration.

The core loop:

1. **Evaluation** - Run the system, get scores
2. **Reflection** - Analyze what worked and what didn't
3. **Mutation** - Propose improved text based on reflection
4. **Selection** - Accept improvements, track Pareto frontier

## How the Evolution Loop Works

GEPA takes a **candidate** (`dict[str, str]` mapping component names to text) and iteratively improves it:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Evolution Loop                              │
│                                                                  │
│   ┌──────────────┐         ┌──────────────┐                     │
│   │   EVALUATE   │────────▶│   REFLECT    │                     │
│   │              │         │              │                     │
│   │ Run on batch │         │ Build trials │                     │
│   │ Get scores   │         │ from results │                     │
│   └──────────────┘         └──────┬───────┘                     │
│          ▲                        │                              │
│          │                        ▼                              │
│   ┌──────┴───────┐         ┌──────────────┐                     │
│   │ ACCEPT/REJECT│◀────────│   PROPOSE    │                     │
│   │              │         │              │                     │
│   │ Score better?│         │ LLM suggests │                     │
│   │ Keep change  │         │ improvements │                     │
│   └──────────────┘         └──────────────┘                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

Each iteration:

1. **EVALUATE**: Run the candidate on a batch of examples → outputs, scores, trajectories
2. **REFLECT**: Transform trajectories into a dataset the reflection LLM can analyze
3. **PROPOSE**: LLM analyzes the dataset → proposes improved component text
4. **ACCEPT/REJECT**: If the new score is better → accept the mutation

## The Key Insight

GEPA doesn't care what "the system" is. It just needs:

- A way to **run** the system and get scores
- A way to **capture execution context** (trajectories)
- A way to **surface that context** for reflection

This abstraction is powerful: the same evolution loop works for single agents, multi-agent pipelines, and complex workflow structures.

## The Adapter Contract

The `AsyncGEPAAdapter` protocol defines exactly **3 things** GEPA needs from any system:

### 1. `evaluate(batch, candidate) → EvaluationBatch`

Runs the system and returns results.

**Inputs:**
- `batch` - List of examples to run
- `candidate` - Current component texts (`dict[str, str]`)

**Outputs:**
- `outputs` - What the system produced (opaque to GEPA)
- `scores` - Per-example numeric scores (higher = better)
- `trajectories` - Execution context for reflection (opaque to GEPA)

### 2. `make_reflective_dataset(candidate, eval_batch, components_to_update) → dict`

Transforms trajectories into a JSON-serializable dataset for the reflection LLM.

**Recommended output format:**
```python
{
    "component_name": [
        {
            "Inputs": {...},            # What went in
            "Generated Outputs": {...}, # What came out
            "Feedback": "..."           # What was wrong/right
        },
        ...
    ]
}
```

### 3. `propose_new_texts(candidate, reflective_dataset, components_to_update) → dict[str, str]`

*(Optional)* Custom proposal logic. GEPA provides a default reflection agent.

## Trajectories vs Outputs

A critical distinction:

| Concept | Who Sees It | Purpose |
|---------|-------------|---------|
| **Output** | Scorer/Critic | Single result to evaluate |
| **Trajectory** | Reflection Agent | Full execution context |

The **scorer** sees ONE thing—whatever we decide is "the output."

The **reflection** sees EVERYTHING we capture in trajectories—tool calls, intermediate states, token usage, reasoning chains.

This separation is powerful:

> **What execution context (trajectories) should we capture, and how do we transform that into a reflective dataset that helps the reflection LLM propose better component text?**

For workflow agents with multiple steps, the question isn't "which output do we score?" but rather "what context helps the reflection agent understand what went wrong and how to fix it?"

## Pareto Frontier

GEPA tracks a **Pareto frontier** of candidates when optimizing multiple objectives. A candidate is Pareto-optimal if no other candidate is better on ALL objectives.

```
Score B
    ▲
    │     ○ Pareto-optimal
    │    ╱
    │   ○
    │  ╱
    │ ○
    │╱
    └──────────────▶ Score A
```

This enables multi-objective optimization without forcing a single "best" solution.

## Next Steps

- [Single-Agent Evolution](single-agent-evolution.md) - How evolution works for one agent
- [Multi-Agent Evolution](multi-agent-evolution.md) - How multiple agents evolve together
- [Workflow Agents](workflow-agents.md) - How workflow structures evolve

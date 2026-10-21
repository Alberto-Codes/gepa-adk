# GEPA Fundamentals

This document explains what GEPA is, how the evolution loop works, and what the adapter contract requires.

## What is GEPA?

**GEPA = Genetic-Pareto prompt optimizer**

GEPA is an evolutionary algorithm that optimizes **text components** of any system. It treats prompts, instructions, and configurations as evolvable "genes" that can be improved through iteration.

The core loop:

1. **Evaluation** - Run the system, get scores
2. **Reflection** - Analyze what worked and what didn't
3. **Mutation** - Propose improved text based on reflection
4. **Selection** - Keep a proposal only when it beats the best score by a margin; with a `candidate_selector`, also track a Pareto frontier and draw parents from it

## How the Evolution Loop Works

GEPA takes a <core:candidate> (component names mapped to text) and iteratively improves it. The engine is `AsyncGEPAEngine` in `gepa_adk.engine.async_engine`; `run()` drives the steps below in this order.

```
 resume or baseline ──▶ stop? ──no──▶ select parent ──▶ reflect ──▶ propose
                          ▲                                            │
                          │                                            ▼
                 record + checkpoint                 validator ─▶ schema check ─▶ duplicate?
                          ▲                                            │
                          │                                            ▼
            (opt-in) merge ◀── accept / reject ◀── evaluate ◀── minibatch gate
```

**Before the first iteration:**

1. **Resume or baseline.** With `EvolutionConfig(resume=True)` the engine restores its state from `checkpoint_path` and skips the baseline. Otherwise it evaluates the seed candidate on the trainset with traces (the reflection batch) and on the valset without traces (the scoring batch, reused when no valset was given), and writes a checkpoint (see the [glossary](../reference/glossary.md#evolution-process)) when `checkpoint_path` is set.
2. **Stop check.** The run can end before any iteration (for example `max_iterations=0`).

**Each iteration:**

1. **Select the parent.** Without a `candidate_selector` the parent is always the current best candidate. With one, the selector draws the parent from the Pareto state (see [Pareto Frontier](#pareto-frontier)).
2. **Reflect.** A component selector (round-robin by default) picks the components to update, and the adapter's `make_reflective_dataset` turns the parent's cached reflection batch into <trial:trials>. The parent is not evaluated again.
3. **Propose.** The adapter's `propose_new_texts` returns new text for those components. An empty, truncated or timed-out reflection, or a provider error that survived retries, is recorded as a skipped iteration and the loop goes to the stop check. A non-retryable reflection error aborts the run, and so do `max_consecutive_reflection_errors` (default 3) consecutive retryable errors with the same cause: the engine raises `ReflectionError` with the partial result attached.
4. **Validate the proposal.** When `EvolutionConfig.proposal_validator` is set, it sees each proposed text; a returned reason records the iteration with `skip_reason="proposal_rejected"` and no evaluation.
5. **Validate the schema.** A proposed `output_schema` must parse as a safe Pydantic model; otherwise the iteration is recorded with `skip_reason="schema_validation_failed"`.
6. **Skip duplicates.** A proposal whose candidate id was already scored this run is recorded with its stored score and `skip_reason="duplicate"`, without evaluation.
7. **Minibatch gate.** With `reflection_minibatch_size` smaller than the trainset, the proposal is first evaluated on a sample of rows (drawn from `EvolutionConfig.seed` when set) and continues only when its mean beats the parent's on the same rows; otherwise `skip_reason="minibatch_rejected"`. See <evolution:minibatch>.
8. **Evaluate.** The proposal is evaluated on the trainset with `capture_traces=True` (its future reflection batch) and on the valset with `capture_traces=False` (its scoring batch; with a Pareto state, only the rows the evaluation policy selects). When the valset is the trainset, one pass serves both. With the gate active and a separate valset, the gate's batch is the reflection batch and only the valset is evaluated.
9. **Accept or reject.** See [Acceptance Rule](#acceptance-rule). An accepted proposal becomes the best candidate and resets the stagnation counter; a rejected one increments it.
10. **Merge (opt-in).** With `use_merge=True` and a `candidate_selector`, each acceptance schedules a merge of two Pareto candidates, up to `max_merge_invocations`. A merge candidate with an invalid schema or an already scored id is skipped; otherwise it is evaluated on the full trainset, scored on the valset rows the evaluation policy selects, and goes through the same acceptance rule.
11. **Record and checkpoint.** The iteration is recorded, `on_iteration` is called, and a checkpoint is written when `checkpoint_path` is set. Skipped iterations (steps 3 to 7) are recorded the same way and count toward stagnation.
12. **Stop check.** The loop ends with the first <evolution:stop_reason> that holds: `MAX_ITERATIONS` (`max_iterations`, default 50), `PATIENCE` (`patience` iterations in a row without an acceptance, default 5; 0 turns it off), or `STOPPER_TRIGGERED` (a <evolution:stopper> in `stop_callbacks` returned `True`). A `KeyboardInterrupt` or cancellation after the baseline returns a partial result instead.

### Acceptance Rule

A proposal is accepted only when its score beats the current best by more than a margin:

```
proposal_score > best_score + min_improvement_threshold
```

- `proposal_score` and `best_score` are aggregates of the valset scoring batch, chosen by <evolution:acceptance_metric>: `"sum"` by default, or `"mean"`.
- `min_improvement_threshold` defaults to `0.01`. An equal or marginally better score is rejected.

### Reviewer Map

Each step above maps to one method of `AsyncGEPAEngine` in `src/gepa_adk/engine/async_engine.py`:

| Step | Method |
|------|--------|
| Resume from checkpoint | `_resume_from_checkpoint` |
| Baseline evaluation | `_initialize_baseline` |
| Iteration loop | `_run_evolution_loop` |
| Stop check | `_should_stop` |
| Select parent, reflect and propose | `_propose_mutation` |
| Proposal validator | `_record_if_rejected` |
| Schema validation | `_validate_schema_component` |
| Duplicate skip | `_record_if_duplicate` |
| Minibatch gate | `_gate_on_minibatch` |
| Trainset (reflection) evaluation | `_evaluate_passed_proposal` |
| Valset (scoring) evaluation | `_evaluate_scoring` |
| Score aggregation | `_aggregate_acceptance_score` |
| Acceptance decision | `_should_accept` |
| Apply an accepted proposal | `_accept_proposal` |
| Start a scheduled merge | `_start_merge` |
| Skip an invalid or duplicate merge | `_skip_merge_candidate` |
| Record iteration and call `on_iteration` | `_record_iteration` |
| Write checkpoint | `_write_checkpoint` |

## The Key Insight

GEPA doesn't care what "the system" is. It just needs:

- A way to **run** the system and get scores
- A way to **capture execution context** (trajectories)
- A way to **surface that context** for reflection

This abstraction is powerful: the same evolution loop works for single agents, multi-agent pipelines, and complex workflow structures.

## The Adapter Contract

The `AsyncGEPAAdapter` protocol (`gepa_adk.ports.adapter`) defines **3 async methods**. All three are required, and the engine calls each of them.

### 1. `evaluate(batch, candidate, capture_traces=False) → EvaluationBatch`

Runs the system and returns results.

**Inputs:**
- `batch` - List of examples to run
- `candidate` - Current component texts (`dict[str, str]`)
- `capture_traces` - `True` when the engine needs trajectories for reflection (trainset and minibatch passes), `False` for valset scoring

**Outputs:**
- `outputs` - What the system produced (opaque to GEPA)
- `scores` - Per-example numeric scores (higher = better)
- `trajectories` - Execution context for reflection (opaque to GEPA; expected when `capture_traces=True`)
- Optional `objective_scores`, `metadata`, `inputs` and `failed_indices`

### 2. `make_reflective_dataset(candidate, eval_batch, components_to_update) → Mapping`

Transforms a traced evaluation batch into a JSON-serializable dataset for the reflection LLM: one list of records per component to update.

The ADK adapters return <trial:trial> records, each holding <trial:feedback> and a <trial:trajectory>:

```python
{
    "instruction": [
        {
            "feedback": {"score": 0.4, "feedback_text": "..."},
            "trajectory": {"input": "...", "output": "...", "trace": {...}},
        },
        ...
    ]
}
```

### 3. `propose_new_texts(candidate, reflective_dataset, components_to_update) → dict[str, str]`

Required. The engine calls it once per iteration with the reflective dataset and expects new text for each requested component. The ADK adapters implement it by running a reflection agent; see [Single-Agent Evolution](single-agent-evolution.md#the-reflection-agent).

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

The <evolution:pareto_frontier> is opt-in. The engine keeps a `ParetoState` only when `evolve()` receives a `candidate_selector`; without one, every mutation starts from the current best candidate and no frontier exists.

With a selector, every evaluated candidate is added to the Pareto state with its valset scores, and the selector draws each iteration's parent from it. `EvolutionConfig.frontier_type` picks which scores are tracked:

- `INSTANCE` (default): one score per valset example. The frontier holds the candidates that lead, or tie for the lead, on at least one example, so a candidate that is best on a few hard examples stays available as a parent even when its total is lower.
- `OBJECTIVE` (aggregated objective scores), `HYBRID` (per-example and objective scores) and `CARTESIAN` (per-example objective scores): for adapters that return `objective_scores`.

The frontier also supplies the parents for merges (`use_merge=True`). Acceptance still uses the single aggregate score: the frontier widens the choice of parents, not the acceptance rule.

## Next Steps

- [Single-Agent Evolution](single-agent-evolution.md) - How evolution works for one agent
- [Multi-Agent Evolution](multi-agent-evolution.md) - How multiple agents evolve together
- [Workflow Agents](workflow-agents.md) - How workflow structures evolve

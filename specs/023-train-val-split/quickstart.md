# Quickstart: Train/Val Split for Evolution Scoring

**Feature**: 023-train-val-split
**Date**: 2026-01-14

## Overview

This guide shows how to run evolution with separate trainset and valset datasets so reflection uses the trainset while scoring and acceptance decisions use the valset.

---

## Basic Usage

### Default Behavior (Backward Compatible)

If you provide only a trainset, gepa-adk uses it for both reflection and scoring:

```python
from gepa_adk import evolve
from google.adk import LlmAgent

agent = LlmAgent(
    name="my_agent",
    model="gemini-2.0-flash",
    instruction="Help users with their questions.",
)

trainset = [
    {"input": "Q1", "expected": "A1"},
    {"input": "Q2", "expected": "A2"},
]

result = await evolve(agent, trainset)
print(f"Final score: {result.final_score}")
```

---

## Using a Separate Valset

Provide a valset to drive scoring and acceptance decisions:

```python
from gepa_adk import evolve

trainset = [
    {"input": "Train Q1", "expected": "Train A1"},
    {"input": "Train Q2", "expected": "Train A2"},
]

valset = [
    {"input": "Val Q1", "expected": "Val A1"},
    {"input": "Val Q2", "expected": "Val A2"},
    {"input": "Val Q3", "expected": "Val A3"},
]

result = await evolve(agent, trainset, valset=valset)
print(f"Valset score: {result.valset_score}")
```

With a valset provided:
- Reflection and trace capture use the trainset only
- Scoring, acceptance, and selection use the valset only

---

## Evolution Workflow Example

```python
from gepa_adk import evolve_workflow
from gepa_adk.adapters import AdkAdapter

adapter = AdkAdapter(agent)

result = await evolve_workflow(
    workflow=adapter,
    trainset=trainset,
    valset=valset,
)

print(f"Accepted score (valset): {result.final_score}")
```

---

## Troubleshooting

### Valset Provided but Empty

If the valset is empty, evolution should raise a validation error. Ensure your valset has at least one example.

### Incompatible Example Schema

Trainset and valset must share the same schema (for example, `input` and `expected`). If they differ, update your valset to match trainset fields.

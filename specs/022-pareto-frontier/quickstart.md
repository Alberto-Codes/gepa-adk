# Quickstart: Pareto Frontier Tracking and Candidate Selection

**Feature**: 022-pareto-frontier
**Date**: 2026-01-14

## Overview

This guide shows how to use Pareto frontier tracking and candidate selection strategies in gepa-adk to enable diverse exploration during prompt evolution.

---

## Basic Usage

### Default Behavior (Greedy Selection)

The default behavior remains unchanged—greedy selection of the best average candidate:

```python
from gepa_adk import evolve
from google.adk import LlmAgent

agent = LlmAgent(
    name="my_agent",
    model="gemini-2.5-flash",
    instruction="Help users with their questions.",
)

result = await evolve(agent, trainset)
print(f"Evolved instruction: {result.evolved_instruction}")
```

---

## Enabling Pareto Selection

### Using ParetoCandidateSelector

To enable Pareto-aware candidate selection, pass a selector to the evolution:

```python
import random
from gepa_adk import evolve
from gepa_adk.adapters import ParetoCandidateSelector

# Create selector with reproducible RNG
selector = ParetoCandidateSelector(rng=random.Random(42))

result = await evolve(
    agent,
    trainset,
    candidate_selector=selector,
)
```

With Pareto selection:
- Candidates that excel on different validation examples are preserved
- Selection probability is proportional to how many examples a candidate leads
- Evolution explores more diverse solutions

---

## Candidate Selection Strategies

### 1. Pareto Selection (Recommended for Diverse Tasks)

```python
from gepa_adk.adapters import ParetoCandidateSelector

selector = ParetoCandidateSelector(rng=random.Random(42))
```

**Best for**: Tasks with diverse validation examples where specialized prompts may work better for different inputs.

**Behavior**: Samples from the Pareto front—candidates that are best on at least one validation example. Candidates leading more examples have higher selection probability.

### 2. Greedy Selection (Default)

```python
from gepa_adk.adapters import CurrentBestCandidateSelector

selector = CurrentBestCandidateSelector()
```

**Best for**: Simple optimization where you want the single best average performer.

**Behavior**: Always selects the candidate with the highest average score across all examples.

### 3. Epsilon-Greedy Selection

```python
from gepa_adk.adapters import EpsilonGreedyCandidateSelector

selector = EpsilonGreedyCandidateSelector(
    epsilon=0.1,  # 10% exploration
    rng=random.Random(42),
)
```

**Best for**: Balancing exploitation of best candidates with random exploration.

**Behavior**: With probability ε, selects a random candidate; otherwise selects the best.

---

## Understanding Pareto Frontiers

### What is a Pareto Frontier?

A Pareto frontier contains all "non-dominated" candidates—those that are best on at least one dimension (validation example).

```
Example Scores:
                Example 1    Example 2    Example 3
Candidate A:      0.9          0.5          0.6
Candidate B:      0.6          0.9          0.6
Candidate C:      0.5          0.5          0.9

All three are on the Pareto front because each is best on one example.
Candidate A leads Example 1, B leads Example 2, C leads Example 3.
```

### Why Use Pareto Selection?

Traditional greedy optimization averages scores:
- Candidate A average: 0.67
- Candidate B average: 0.70 ← Greedy selects this
- Candidate C average: 0.63

But Pareto selection preserves specialists:
- A might be perfect for math questions
- B might be perfect for coding questions
- C might be perfect for creative writing

Pareto selection explores all three, potentially discovering that specialization outperforms generalization.

---

## Checking Pareto Frontier Results

After evolution, you can inspect which candidates were discovered:

```python
result = await evolve(
    agent,
    trainset,
    candidate_selector=ParetoCandidateSelector(),
)

# Access evolution metrics
print(f"Total iterations: {result.total_iterations}")
print(f"Final score: {result.final_score}")
print(f"Improvement: {result.improvement}")

# Iteration history shows accepted candidates
for record in result.iteration_history:
    if record.accepted:
        print(f"Iteration {record.iteration_number}: score={record.score:.3f}")
```

---

## Configuration Reference

### EvolutionConfig Options

```python
from gepa_adk.domain.models import EvolutionConfig

config = EvolutionConfig(
    max_iterations=50,           # Maximum evolution iterations
    patience=5,                  # Stop after N iterations without improvement
    min_improvement_threshold=0.01,  # Minimum improvement to accept
)

result = await evolve(agent, trainset, config=config)
```

### Selector Factory Pattern

For convenience, you can use string identifiers:

```python
# Using selector type string
result = await evolve(
    agent,
    trainset,
    candidate_selector="pareto",  # or "greedy", "epsilon_greedy"
)
```

---

## Best Practices

### 1. Use Pareto Selection with Diverse Datasets

Pareto selection shines when your training set contains diverse examples:

```python
trainset = [
    {"query": "Write Python code...", "expected": "..."},  # Coding
    {"query": "Explain quantum physics...", "expected": "..."},  # Science
    {"query": "Write a poem about...", "expected": "..."},  # Creative
]
```

### 2. Set Seeds for Reproducibility

Always use seeded random number generators for reproducible results:

```python
import random

selector = ParetoCandidateSelector(rng=random.Random(42))
```

### 3. Monitor Exploration vs. Exploitation

Use epsilon-greedy to control the exploration rate:

```python
# High exploration for initial discovery
selector = EpsilonGreedyCandidateSelector(epsilon=0.3, rng=random.Random(42))

# Low exploration for fine-tuning
selector = EpsilonGreedyCandidateSelector(epsilon=0.05, rng=random.Random(42))
```

---

## Troubleshooting

### All Candidates Have Similar Scores

If your training examples are very similar, Pareto selection behaves like greedy selection. This is expected—diversify your training set for better results.

### Evolution Seems Random

Check that you're using a seeded RNG. Without a seed, results vary between runs:

```python
# Non-deterministic (different each run)
selector = ParetoCandidateSelector()

# Deterministic (same results each run)
selector = ParetoCandidateSelector(rng=random.Random(42))
```

### Performance Concerns

Pareto frontier operations are O(n × m) where n is candidates and m is examples. For typical evolution (< 100 candidates, < 50 examples), this is negligible.

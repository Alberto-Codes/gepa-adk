# Quickstart: MergeProposer

## Overview

The MergeProposer enables genetic crossover in evolution by combining instruction components from two Pareto-optimal candidates that share a common ancestor. This complements the existing mutation-based evolution with a recombination strategy.

## Basic Usage

```python
import random
from gepa_adk.engine.merge_proposer import MergeProposer
from gepa_adk.domain.state import ParetoState

# Create merge proposer with random seed
proposer = MergeProposer(rng=random.Random(42))

# Propose a merge from current evolution state
result = await proposer.propose(state)

if result:
    print(f"Merged candidate from parents {result.parent_indices}")
    print(f"Ancestor: {result.metadata['ancestor_idx']}")
    new_candidate = result.candidate
else:
    print("No suitable merge candidates found")
```

## Integration with Evolution Engine

```python
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.domain.models import EvolutionConfig, Candidate

# Configure evolution with merge enabled
config = EvolutionConfig(
    max_iterations=100,
    use_merge=True,  # Enable merge proposals
    max_merge_invocations=20,  # Limit merge attempts
)

# Create engine with merge proposer
engine = AsyncGEPAEngine(
    adapter=my_adapter,
    config=config,
    initial_candidate=Candidate(components={"instruction": "Be helpful"}),
    batch=training_data,
)

# Run evolution with both mutation and merge
result = await engine.run()
```

## How Merging Works

1. **Find Candidates**: Select two candidates from the Pareto frontier
2. **Find Ancestor**: Identify their most recent common ancestor
3. **Compare Components**: Determine which components each candidate changed
4. **Combine**: Create new candidate taking innovations from both parents

### Example Scenario

```
Ancestor (Gen 0):
  instruction: "Answer questions helpfully"
  output_schema: "plain text"

Parent A (Gen 3, improved from ancestor):
  instruction: "Answer questions helpfully with examples"  ← Changed
  output_schema: "plain text"                              ← Same

Parent B (Gen 4, improved from ancestor):
  instruction: "Answer questions helpfully"                ← Same
  output_schema: "JSON with reasoning field"               ← Changed

Merged Result:
  instruction: "Answer questions helpfully with examples"  ← From A
  output_schema: "JSON with reasoning field"               ← From B
```

## Key Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `use_merge` | `False` | Enable merge proposals in evolution |
| `max_merge_invocations` | `10` | Maximum merge attempts per run |
| `val_overlap_floor` | `5` | Minimum overlapping validation examples |

## When Merge Is Attempted

Merge is only attempted when:
1. `use_merge=True` in config
2. A mutation was just accepted (found new best candidate)
3. Merge quota not exhausted
4. At least 2 candidates on frontier with common ancestor

## Logging

MergeProposer uses structlog for observability:

```python
# Successful merge
logger.info(
    "merge_proposer.merge_success",
    parent1_idx=5,
    parent2_idx=8,
    ancestor_idx=2,
    components_merged=["instruction", "output_schema"],
)

# No merge possible
logger.info(
    "merge_proposer.no_candidates",
    reason="no_common_ancestor",
    frontier_size=3,
)
```

## Testing

```python
import pytest
from gepa_adk.engine.merge_proposer import MergeProposer

@pytest.mark.asyncio
async def test_merge_complementary_candidates():
    """Test merging candidates with complementary improvements."""
    state = create_test_state_with_complementary_candidates()
    proposer = MergeProposer(rng=random.Random(42))

    result = await proposer.propose(state)

    assert result is not None
    assert result.tag == "merge"
    assert len(result.parent_indices) == 2
    assert "ancestor_idx" in result.metadata
```

## Troubleshooting

### Merge Never Happens

1. Check `use_merge=True` in config
2. Verify mutations are finding new candidates (merge scheduled after success)
3. Ensure frontier has 2+ candidates with shared ancestry

### Merge Always Returns None

1. Check frontier size (need 2+ candidates)
2. Verify candidates have common ancestor
3. Check validation overlap (`val_overlap_floor`)
4. Review logs for specific failure reason

### Performance Concerns

Merge attempts are bounded by `max_merge_invocations` to prevent excessive computation. Each merge involves:
- Ancestor traversal: O(depth) per candidate
- Component comparison: O(num_components)
- No additional model calls (unlike mutation)

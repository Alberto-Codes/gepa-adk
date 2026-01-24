# Quickstart: ADKAdapter

**Feature**: 008-adk-adapter  
**Date**: 2026-01-10

## Overview

This guide shows how to use `ADKAdapter` to evaluate Google ADK agents with evolutionary optimization support.

---

## Installation

The ADKAdapter is part of `gepa-adk`. Ensure you have the required dependencies:

```bash
uv add google-adk  # Already included in gepa-adk
```

---

## Basic Usage

### 1. Create an ADK Agent

```python
from google.adk.agents import LlmAgent

agent = LlmAgent(
    name="helpful_assistant",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant.",
    description="Answers user questions helpfully.",
)
```

### 2. Create a Scorer

The ADKAdapter uses a simplified scorer interface:

```python
class SimpleScorer:
    """Simple scorer for ADKAdapter.
    
    Note: ADKAdapter uses a simplified scorer interface with just
    (output, expected) -> float signature.
    """
    
    def score(
        self,
        output: str,
        expected: str | None = None,
    ) -> float:
        if expected is None:
            return 0.5  # Neutral score when no expected value
        match = expected.lower() in output.lower()
        return 1.0 if match else 0.0
    
    async def async_score(
        self,
        output: str,
        expected: str | None = None,
    ) -> float:
        return self.score(output, expected)


scorer = SimpleScorer()
```

### 3. Create the ADKAdapter

```python
from gepa_adk.adapters import ADKAdapter

adapter = ADKAdapter(
    agent=agent,
    scorer=scorer,
)
```

### 4. Evaluate with a Candidate

```python
import asyncio


async def main():
    # Define test batch
    batch = [
        {"input": "What is 2+2?", "expected": "4"},
        {"input": "What is the capital of France?", "expected": "Paris"},
    ]
    
    # Define candidate instruction to test
    candidate = {
        "instruction": "You are a helpful assistant. Answer questions concisely and accurately."
    }
    
    # Run evaluation
    result = await adapter.evaluate(
        batch=batch,
        candidate=candidate,
        capture_traces=False,
    )
    
    # Print results
    for i, (output, score) in enumerate(zip(result.outputs, result.scores)):
        print(f"Example {i+1}:")
        print(f"  Output: {output[:100]}...")
        print(f"  Score: {score:.2f}")
    
    print(f"\nAverage score: {sum(result.scores) / len(result.scores):.2f}")


asyncio.run(main())
```

---

## With Trace Capture

Capture detailed execution traces for debugging:

```python
async def evaluate_with_traces():
    batch = [{"input": "Calculate 5 * 7", "expected": "35"}]
    candidate = {"instruction": "You are a calculator."}
    
    result = await adapter.evaluate(
        batch=batch,
        candidate=candidate,
        capture_traces=True,  # Enable trace capture
    )
    
    # Inspect trajectories
    if result.trajectories:
        for i, trajectory in enumerate(result.trajectories):
            print(f"Example {i+1} trajectory:")
            print(f"  Tool calls: {len(trajectory.tool_calls)}")
            print(f"  State changes: {len(trajectory.state_deltas)}")
            if trajectory.token_usage:
                print(f"  Tokens: {trajectory.token_usage.total_tokens}")
            if trajectory.error:
                print(f"  Error: {trajectory.error}")
```

---

## Building Reflective Datasets

Generate reflection data for evolutionary improvement:

```python
async def create_reflection_data():
    batch = [
        {"input": "Explain photosynthesis", "expected": "process"},
        {"input": "What is gravity?", "expected": "force"},
    ]
    candidate = {"instruction": "You are a science tutor."}
    
    # First, evaluate with traces
    result = await adapter.evaluate(
        batch=batch,
        candidate=candidate,
        capture_traces=True,
    )
    
    # Build reflective dataset
    dataset = await adapter.make_reflective_dataset(
        candidate=candidate,
        eval_batch=result,
        components_to_update=["instruction"],
    )
    
    # Dataset is ready for mutation proposer
    print(f"Reflective examples for 'instruction': {len(dataset['instruction'])}")
```

---

## Integration with AsyncGEPAEngine

The ADKAdapter is designed to work with the `AsyncGEPAEngine` (Issue #6):

```python
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.domain.models import EvolutionConfig, Candidate

# Create engine with adapter
engine = AsyncGEPAEngine(adapter=adapter)

# Initial candidate
initial = Candidate(
    components={"instruction": "You are a helpful assistant."},
    generation=0,
)

# Configure evolution
config = EvolutionConfig(
    max_iterations=10,
    patience=3,
)

# Run evolution (future implementation)
# result = await engine.evolve(initial, batch, config)
```

---

## Custom Session Service

Use a custom session service for persistent sessions:

```python
from google.adk.sessions import DatabaseSessionService

# Use database-backed sessions
db_session_service = DatabaseSessionService(
    db_url="sqlite+aiosqlite:///./eval_sessions.db"
)

adapter = ADKAdapter(
    agent=agent,
    scorer=scorer,
    session_service=db_session_service,
    app_name="my_evolution_app",
)
```

---

## Error Handling

The adapter handles errors gracefully:

```python
async def handle_errors():
    # Even if some examples fail, evaluation continues
    batch = [
        {"input": "Valid question"},
        {"input": "This might cause an error"},
    ]
    
    result = await adapter.evaluate(batch, candidate)
    
    # Check for errors in trajectories
    if result.trajectories:
        for i, traj in enumerate(result.trajectories):
            if traj.error:
                print(f"Example {i} failed: {traj.error}")
                print(f"Score assigned: {result.scores[i]}")  # Will be 0.0
```

---

## Best Practices

1. **Use appropriate scorers**: Match your scorer to your task (exact match, semantic similarity, LLM-based grading)

2. **Capture traces for debugging**: Enable `capture_traces=True` when troubleshooting

3. **Batch appropriately**: Larger batches provide better signal but take longer

4. **Handle rate limits**: ADK may have rate limits; consider adding delays between examples

5. **Clean up sessions**: For long-running evaluations, ensure sessions are cleaned up

---

## Next Steps

- See [Scorer Protocol](../../005-scorer-protocol/quickstart.md) for custom scorers
- See [AsyncGEPAEngine](../../006-async-gepa-engine/quickstart.md) for full evolution loop
- See [MutationProposer](../../007-async-mutation-proposer/quickstart.md) for proposal generation

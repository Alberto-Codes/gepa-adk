# ADKAdapter API Contract

**Feature**: 008-adk-adapter  
**Version**: 1.0.0  
**Date**: 2026-01-10

## Overview

This contract defines the public interface of `ADKAdapter`, the concrete implementation of `AsyncGEPAAdapter` protocol for Google ADK agents.

---

## Class: ADKAdapter

### Module
`gepa_adk.adapters.adk_adapter`

### Protocol Compliance
Implements `AsyncGEPAAdapter[dict[str, Any], ADKTrajectory, str]`

---

## Constructor

### Signature

```python
def __init__(
    self,
    agent: LlmAgent,
    scorer: Scorer,
    session_service: BaseSessionService | None = None,
    app_name: str = "gepa_adk_eval",
) -> None
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `agent` | `google.adk.agents.LlmAgent` | Yes | - | The ADK agent to evaluate |
| `scorer` | `gepa_adk.ports.scorer.Scorer` | Yes | - | Scorer for evaluating outputs |
| `session_service` | `BaseSessionService \| None` | No | `None` | Session service (creates InMemory if None) |
| `app_name` | `str` | No | `"gepa_adk_eval"` | Application name for sessions |

### Raises

| Exception | Condition |
|-----------|-----------|
| `TypeError` | `agent` is not an `LlmAgent` instance |
| `TypeError` | `scorer` does not satisfy `Scorer` protocol |
| `ValueError` | `app_name` is empty string |

### Example

```python
from google.adk.agents import LlmAgent
from gepa_adk.adapters import ADKAdapter
from gepa_adk.ports.scorer import Scorer

# Create agent and scorer
agent = LlmAgent(name="my_agent", model="gemini-2.5-flash", instruction="Be helpful")
scorer = MyScorer()  # Implements Scorer protocol

# Create adapter
adapter = ADKAdapter(agent=agent, scorer=scorer)
```

---

## Method: evaluate

### Signature

```python
async def evaluate(
    self,
    batch: list[dict[str, Any]],
    candidate: dict[str, str],
    capture_traces: bool = False,
) -> EvaluationBatch[ADKTrajectory, str]
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `batch` | `list[dict[str, Any]]` | Yes | - | Input examples with "input" key |
| `candidate` | `dict[str, str]` | Yes | - | Component values (e.g., `{"instruction": "..."}`) |
| `capture_traces` | `bool` | No | `False` | Whether to capture execution traces |

### Returns

`EvaluationBatch[ADKTrajectory, str]` containing:
- `outputs: list[str]` - Agent output for each example
- `scores: list[float]` - Normalized score for each example
- `trajectories: list[ADKTrajectory] | None` - Traces (if `capture_traces=True`)

### Invariants

- `len(result.outputs) == len(batch)`
- `len(result.scores) == len(batch)`
- `result.trajectories is None` when `capture_traces=False`
- `len(result.trajectories) == len(batch)` when `capture_traces=True`

### Example

```python
batch = [
    {"input": "What is 2+2?", "expected": "4"},
    {"input": "What is the capital of France?", "expected": "Paris"},
]
candidate = {"instruction": "Be concise and accurate"}

result = await adapter.evaluate(batch, candidate, capture_traces=True)

assert len(result.outputs) == 2
assert len(result.scores) == 2
assert result.trajectories is not None
```

---

## Method: make_reflective_dataset

### Signature

```python
async def make_reflective_dataset(
    self,
    candidate: dict[str, str],
    eval_batch: EvaluationBatch[ADKTrajectory, str],
    components_to_update: list[str],
) -> Mapping[str, Sequence[Mapping[str, Any]]]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `candidate` | `dict[str, str]` | Yes | Current candidate components |
| `eval_batch` | `EvaluationBatch` | Yes | Evaluation results with traces |
| `components_to_update` | `list[str]` | Yes | Components to generate datasets for |

### Returns

`Mapping[str, Sequence[Mapping[str, Any]]]` where:
- Keys are component names from `components_to_update`
- Values are sequences of reflection examples

### Example

```python
result = await adapter.evaluate(batch, candidate, capture_traces=True)

dataset = await adapter.make_reflective_dataset(
    candidate=candidate,
    eval_batch=result,
    components_to_update=["instruction"],
)

# dataset["instruction"] contains reflection examples
assert "instruction" in dataset
```

---

## Method: propose_new_texts

### Signature

```python
async def propose_new_texts(
    self,
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components_to_update: list[str],
) -> dict[str, str]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `candidate` | `dict[str, str]` | Yes | Current candidate components |
| `reflective_dataset` | `Mapping[str, Sequence[...]]` | Yes | Dataset from `make_reflective_dataset` |
| `components_to_update` | `list[str]` | Yes | Components to generate proposals for |

### Returns

`dict[str, str]` with proposed new text for each component.

### Note

This method delegates to the mutation proposer (implemented in Issue #7). For MVP, returns unchanged candidate values.

---

## Supporting Types

### ADKTrajectory

```python
@dataclass(frozen=True, slots=True)
class ADKTrajectory:
    tool_calls: tuple[ToolCallRecord, ...]
    state_deltas: tuple[dict[str, Any], ...]
    token_usage: TokenUsage | None
    final_output: str
    error: str | None
```

### ToolCallRecord

```python
@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    name: str
    arguments: dict[str, Any]
    result: Any
    timestamp: float
```

### TokenUsage

```python
@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
```

---

## Error Handling

### Evaluation Errors

When agent execution fails for an example:
- `output` is set to empty string `""`
- `score` is set to `0.0`
- `trajectory.error` contains error message
- Batch processing continues to next example

### Session Errors

When session service is unavailable:
- Raises `AdapterError` with clear message
- Does not attempt partial evaluation

---

## Logging

The adapter uses `structlog` with bound context:

```python
logger = structlog.get_logger(__name__).bind(
    adapter="ADKAdapter",
    agent_name=self.agent.name,
)
```

Log events:
- `adapter.evaluate.start` - Batch evaluation begins
- `adapter.evaluate.example` - Per-example progress
- `adapter.evaluate.complete` - Batch evaluation ends
- `adapter.evaluate.error` - Example-level errors

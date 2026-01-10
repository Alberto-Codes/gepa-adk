# Contract: AsyncGEPAAdapter Protocol

**Feature**: 004-async-gepa-adapter
**Date**: 2026-01-10
**Type**: Protocol Interface Contract

## Overview

This contract defines the behavioral expectations for any class implementing the `AsyncGEPAAdapter` protocol. Implementations are verified through contract tests in `tests/contracts/test_adapter_protocol.py`.

## Protocol Signature

```python
from typing import Protocol, TypeVar, Mapping, Sequence, Any, runtime_checkable
from gepa_adk.ports.adapter import EvaluationBatch

DataInst = TypeVar("DataInst")
Trajectory = TypeVar("Trajectory")
RolloutOutput = TypeVar("RolloutOutput")

@runtime_checkable
class AsyncGEPAAdapter(Protocol[DataInst, Trajectory, RolloutOutput]):
    async def evaluate(
        self,
        batch: list[DataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Trajectory, RolloutOutput]: ...

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[Trajectory, RolloutOutput],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]: ...

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]: ...
```

## Contract Requirements

### CR-001: Runtime Checkable

**Requirement**: Protocol must support `isinstance()` checks.

**Verification**:
```python
def test_runtime_checkable():
    adapter = ConcreteAdapter()
    assert isinstance(adapter, AsyncGEPAAdapter)
```

**Negative Test**:
```python
def test_incomplete_implementation_not_recognized():
    class IncompleteAdapter:
        async def evaluate(self, ...): ...
        # Missing other methods

    adapter = IncompleteAdapter()
    assert not isinstance(adapter, AsyncGEPAAdapter)
```

### CR-002: Async Method Signatures

**Requirement**: All three methods must be coroutines.

**Verification**:
```python
import asyncio

def test_methods_are_coroutines():
    adapter = ConcreteAdapter()

    assert asyncio.iscoroutinefunction(adapter.evaluate)
    assert asyncio.iscoroutinefunction(adapter.make_reflective_dataset)
    assert asyncio.iscoroutinefunction(adapter.propose_new_texts)
```

### CR-003: Evaluate Method Contract

**Requirement**: `evaluate()` must return an `EvaluationBatch` with correct structure.

**Preconditions**:
- `batch` is a non-empty list
- `candidate` contains required component keys

**Postconditions**:
- `len(result.outputs) == len(batch)`
- `len(result.scores) == len(batch)`
- If `capture_traces=True`: `result.trajectories is not None` and `len(result.trajectories) == len(batch)`
- If `capture_traces=False`: `result.trajectories` may be None

**Verification**:
```python
async def test_evaluate_returns_correct_structure():
    adapter = ConcreteAdapter()
    batch = [{"input": "test1"}, {"input": "test2"}]
    candidate = {"instruction": "Be helpful"}

    result = await adapter.evaluate(batch, candidate, capture_traces=True)

    assert len(result.outputs) == 2
    assert len(result.scores) == 2
    assert result.trajectories is not None
    assert len(result.trajectories) == 2
```

### CR-004: Make Reflective Dataset Contract

**Requirement**: `make_reflective_dataset()` must return a mapping with entries for requested components.

**Preconditions**:
- `eval_batch.trajectories is not None` (traces required for reflection)
- `components_to_update` contains valid component names from `candidate`

**Postconditions**:
- Result contains key for each component in `components_to_update`
- Each value is a sequence of mappings (reflective examples)

**Verification**:
```python
async def test_make_reflective_dataset_structure():
    adapter = ConcreteAdapter()
    candidate = {"instruction": "Be helpful", "format": "JSON"}
    eval_batch = EvaluationBatch(
        outputs=["out1", "out2"],
        scores=[0.8, 0.9],
        trajectories=[trace1, trace2],
    )
    components = ["instruction"]

    result = await adapter.make_reflective_dataset(candidate, eval_batch, components)

    assert "instruction" in result
    assert isinstance(result["instruction"], Sequence)
    for example in result["instruction"]:
        assert isinstance(example, Mapping)
```

### CR-005: Propose New Texts Contract

**Requirement**: `propose_new_texts()` must return updated text for requested components.

**Preconditions**:
- `reflective_dataset` contains entries for `components_to_update`
- `candidate` contains current text for those components

**Postconditions**:
- Result contains key for each component in `components_to_update`
- Each value is a string (the proposed new text)

**Verification**:
```python
async def test_propose_new_texts_structure():
    adapter = ConcreteAdapter()
    candidate = {"instruction": "Be helpful"}
    reflective_dataset = {
        "instruction": [
            {"Inputs": {...}, "Generated Outputs": "...", "Feedback": "..."}
        ]
    }
    components = ["instruction"]

    result = await adapter.propose_new_texts(candidate, reflective_dataset, components)

    assert "instruction" in result
    assert isinstance(result["instruction"], str)
```

## Error Handling Contracts

### CR-006: Graceful Degradation in Evaluate

**Requirement**: Individual example failures should not raise exceptions.

**Contract**:
- Return valid `EvaluationBatch` even when some examples fail
- Use fallback scores (e.g., 0.0) for failed examples
- Reserve exceptions for systemic/unrecoverable failures only

**Verification**:
```python
async def test_evaluate_handles_individual_failures():
    adapter = ConcreteAdapter()
    batch = [{"input": "valid"}, {"input": "TRIGGER_ERROR"}]
    candidate = {"instruction": "Be helpful"}

    # Should NOT raise, even with one bad input
    result = await adapter.evaluate(batch, candidate)

    assert len(result.scores) == 2
    # Bad input should have fallback score
    assert result.scores[1] == 0.0
```

## Test File Structure

```python
# tests/contracts/test_adapter_protocol.py

import pytest
from typing import Any, Mapping, Sequence
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch


class MockAdapter:
    """Minimal mock implementation for contract testing."""

    async def evaluate(
        self,
        batch: list[dict],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        outputs = [f"output_{i}" for i in range(len(batch))]
        scores = [1.0] * len(batch)
        trajectories = [{"trace": i} for i in range(len(batch))] if capture_traces else None
        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            trajectories=trajectories,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        return {
            comp: [{"Inputs": {}, "Generated Outputs": "", "Feedback": ""}]
            for comp in components_to_update
        }

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        return {comp: f"Improved {comp}" for comp in components_to_update}


@pytest.mark.contract
class TestAsyncGEPAAdapterProtocol:
    """Contract tests for AsyncGEPAAdapter protocol compliance."""

    # Tests for CR-001 through CR-006 go here
    ...
```

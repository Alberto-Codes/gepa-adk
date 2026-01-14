# API Contract: evolve() and evolve_sync()

**Feature**: 018-public-api  
**Date**: 2026-01-12

## Function Contracts

### `evolve()`

**Location**: `gepa_adk.api.evolve`

**Signature**:
```python
async def evolve(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    valset: list[dict[str, Any]] | None = None,
    critic: LlmAgent | None = None,
    reflection_agent: LlmAgent | None = None,
    config: EvolutionConfig | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    state_guard: StateGuard | None = None,
) -> EvolutionResult
```

**Preconditions**:
- `agent` MUST be a `google.adk.agents.LlmAgent` instance
- `trainset` MUST be a non-empty list
- Each item in `trainset` MUST be a dict with at least an "input" key
- If `critic` provided, SHOULD have `output_schema` for structured scoring

**Postconditions**:
- Returns `EvolutionResult` instance
- `result.evolved_instruction` is a non-empty string
- `result.original_score` and `result.final_score` are floats
- `result.total_iterations >= 0`
- `len(result.iteration_history) == result.total_iterations`

**Error Conditions**:
- `ConfigurationError` if `trainset` is empty
- `ConfigurationError` if `agent` is invalid
- `EvolutionError` on evolution failure

---

### `evolve_sync()`

**Location**: `gepa_adk.api.evolve_sync`

**Signature**:
```python
def evolve_sync(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    **kwargs: Any,
) -> EvolutionResult
```

**Preconditions**:
- Same as `evolve()` for `agent` and `trainset`
- `**kwargs` must be valid `evolve()` parameters

**Postconditions**:
- Returns `EvolutionResult` (same guarantees as `evolve()`)
- Function blocks until evolution completes
- Works in both sync contexts and Jupyter notebooks

**Error Conditions**:
- Same as `evolve()`

---

## Export Contract

**Location**: `gepa_adk.__init__`

The following MUST be exported from the package root:
- `evolve` - async evolution function
- `evolve_sync` - sync wrapper function

## Test Contract Verification

```python
# tests/contracts/test_api_contract.py

import inspect
from gepa_adk import evolve, evolve_sync
from gepa_adk.domain.models import EvolutionResult

class TestEvolveContract:
    """Contract tests for evolve() function."""

    def test_evolve_exists(self):
        """evolve must be importable from gepa_adk."""
        from gepa_adk import evolve
        assert evolve is not None

    def test_evolve_is_async(self):
        """evolve must be an async function."""
        assert inspect.iscoroutinefunction(evolve)

    def test_evolve_signature_has_required_params(self):
        """evolve must have agent and trainset as required."""
        sig = inspect.signature(evolve)
        params = sig.parameters
        
        assert "agent" in params
        assert "trainset" in params
        assert params["agent"].default is inspect.Parameter.empty
        assert params["trainset"].default is inspect.Parameter.empty

    def test_evolve_signature_has_optional_params(self):
        """evolve must have optional config parameters."""
        sig = inspect.signature(evolve)
        params = sig.parameters
        
        optional = ["valset", "critic", "config", "trajectory_config"]
        for param in optional:
            assert param in params
            assert params[param].default is None

    def test_evolve_return_annotation(self):
        """evolve must return EvolutionResult."""
        sig = inspect.signature(evolve)
        assert sig.return_annotation == EvolutionResult


class TestEvolveSyncContract:
    """Contract tests for evolve_sync() function."""

    def test_evolve_sync_exists(self):
        """evolve_sync must be importable from gepa_adk."""
        from gepa_adk import evolve_sync
        assert evolve_sync is not None

    def test_evolve_sync_is_not_async(self):
        """evolve_sync must NOT be an async function."""
        assert not inspect.iscoroutinefunction(evolve_sync)

    def test_evolve_sync_has_kwargs(self):
        """evolve_sync must accept **kwargs for evolve params."""
        sig = inspect.signature(evolve_sync)
        # Check for VAR_KEYWORD parameter
        has_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD 
            for p in sig.parameters.values()
        )
        assert has_kwargs

    def test_evolve_sync_return_annotation(self):
        """evolve_sync must return EvolutionResult."""
        sig = inspect.signature(evolve_sync)
        assert sig.return_annotation == EvolutionResult
```
